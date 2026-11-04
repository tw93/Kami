"""Template lint rules and cross-template consistency checks.

Splits out from build.py:
  - scan_file: per-line + per-block lint for HTML/CSS/PPTX templates.
  - check_all: scan every template and aggregate findings by rule.
  - check_cross_template_consistency: pair CN/EN templates and report :root
    variable drift outside the allowlist.

Each `Finding` is anchored to a file path + line number so editors can jump
straight to the violation. Rules encode real WeasyPrint pitfalls (rgba on
background, thin border with border-radius, etc.), not style preferences.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from shared import (
    COOL_GRAY_BLOCKLIST,
    HTML_TEMPLATES,
    ROOT,
    SITE_ROOT,
    SCREEN_TEMPLATES,
    TEMPLATES,
    TOKENS_FILE,
    SOCIAL_PAPER_ROLES,
    is_social_cards,
    iter_template_files,
    load_social_palettes,
    rel_to_root,
    resolve_input,
    social_palette_values,
)
from tokens import ROOT_BLOCK, parse_root_vars
from diagram_geometry import scan_geometry

# Font-stack vars legitimately differ between a base template and its locale
# variants (-en, -ko); every other :root var must match across the pair.
CROSS_TEMPLATE_ALLOWED_VARS = {"--serif", "--sans", "--mono", "--latin-ui"}

RGBA_BG_DIRECT = re.compile(r"background(?:-color)?\s*:\s*[^;]*rgba\s*\(", re.IGNORECASE)
RGBA_VAR_DEF = re.compile(r"--([\w-]+)\s*:\s*[^;]*rgba\s*\(", re.IGNORECASE)
BG_VAR_USE = re.compile(r"background(?:-color)?\s*:\s*[^;]*var\s*\(\s*--([\w-]+)", re.IGNORECASE)
RGBA_BORDER_DIRECT = re.compile(r"border(?:-\w+)?\s*:\s*[^;]*rgba\s*\(", re.IGNORECASE)
BORDER_VAR_USE = re.compile(r"border(?:-\w+)?\s*:\s*[^;]*var\s*\(\s*--([\w-]+)", re.IGNORECASE)
LINE_HEIGHT_VALUE = re.compile(
    r"line-height\s*:\s*([0-9]*\.?[0-9]+)(?![\w.%])",
    re.IGNORECASE,
)
UNICODE_ARROW = re.compile(r"→")  # U+2192; should not appear in EN template body
HEX_ANY = re.compile(
    r"#(?:[0-9a-fA-F]{8}|[0-9a-fA-F]{6}|[0-9a-fA-F]{4}|[0-9a-fA-F]{3})"
    r"(?![0-9a-fA-F])"
)
# Thin closed border: border shorthand (not single-side) with sub-1pt width -- pitfall #2
THIN_CLOSED_BORDER = re.compile(
    r"border(?!-(?:left|right|top|bottom))\s*:\s*[^;{}]*(?<![\d.])0\.\d+pt",
    re.IGNORECASE,
)
BORDER_RADIUS_PROP = re.compile(r"border-radius\s*:", re.IGNORECASE)
RULE_BODY_RE = re.compile(r"\{([^{}]*)\}")
CSS_BLOCK_COMMENT_RE = re.compile(r"/\*.*?\*/", re.DOTALL)
SVG_BLOCK_RE = re.compile(r"<svg\b.*?</svg>", re.DOTALL | re.IGNORECASE)

# WeasyPrint-unsafe artifacts of un-normalized beautiful-mermaid SVG. These must
# never reach a PDF-bound template/diagram: WeasyPrint does not resolve
# color-mix(), render <foreignObject>, or fetch a runtime web font. The author
# must pipe Mermaid output through scripts/mermaid_normalize.py first. Screen-only
# landing pages are exempt (color-mix in CSS is fine in a real browser).
MERMAID_UNSAFE = {
    "mermaid-color-mix": re.compile(r"color-mix\s*\(", re.IGNORECASE),
    "mermaid-foreignobject": re.compile(r"<foreignObject\b", re.IGNORECASE),
    "mermaid-webfont-import": re.compile(r"fonts\.googleapis\.com", re.IGNORECASE),
}


@dataclass
class Finding:
    file: Path
    line: int
    rule: str
    excerpt: str


def _strip_css_block_comments(text: str) -> str:
    """Replace `/* ... */` with spaces of the same length so commented-out
    rgba()/cool-gray literals don't trip the per-line scan. Length-preserving
    so line numbers and per-line search offsets remain correct.
    """
    def repl(m: re.Match[str]) -> str:
        return "".join(ch if ch == "\n" else " " for ch in m.group(0))
    return CSS_BLOCK_COMMENT_RE.sub(repl, text)


def scan_file(path: Path, screen: bool | None = None) -> list[Finding]:
    return scan_text(path.read_text(encoding="utf-8", errors="replace"), path, screen=screen)


def scan_text(raw_text: str, path: Path, line_offset: int = 0,
              screen: bool | None = None) -> list[Finding]:
    """Run the per-line and per-block rules over `raw_text`.

    Split out of scan_file so a CSS snippet that lives inside a Markdown fence
    can be scanned with the same rules as a template, reporting line numbers
    back in the enclosing document via `line_offset`. `screen` says whether
    the file is a browser-only page; None falls back to the template file name.
    """
    findings = [Finding(path, line_offset + line, "diagram-geometry", message)
                for line, message in scan_geometry(raw_text)]
    text = _strip_css_block_comments(raw_text)
    lines = text.splitlines()
    is_en = path.name.endswith("-en.html")
    # Screen-only landing pages do not pass through WeasyPrint. Their browser
    # gradients may use alpha, and CJK screen copy has a documented 1.65
    # line-height ceiling instead of the print ceiling of 1.55.
    is_screen = path.name in set(SCREEN_TEMPLATES.values()) if screen is None else screen
    # Social cards are phone images read at 42-44px, not print pages: their
    # body type is set at 1.68-1.75, so they get their own ceiling.
    is_social = is_social_cards(path, raw_text)

    def line_for(offset: int) -> int:
        return line_offset + text.count("\n", 0, offset) + 1

    # Pass 1: scan declarations across the whole stylesheet. CSS may wrap a
    # declaration across lines or place several custom properties on one line;
    # a per-line `search` silently missed both shapes.
    rgba_vars = {m.group(1) for m in RGBA_VAR_DEF.finditer(text)}
    for match in (() if is_screen else RGBA_BG_DIRECT.finditer(text)):
        findings.append(Finding(
            path,
            line_for(match.start()),
            "rgba-background",
            "rgba() used directly on background (tag double-rectangle bug)",
        ))
    for match in (() if is_screen else BG_VAR_USE.finditer(text)):
        if match.group(1) in rgba_vars:
            findings.append(Finding(
                path,
                line_for(match.start()),
                "rgba-background",
                f"background: var(--{match.group(1)}) resolves to rgba() (tag double-rectangle bug)",
            ))
    for match in (() if is_screen else RGBA_BORDER_DIRECT.finditer(text)):
        findings.append(Finding(
            path,
            line_for(match.start()),
            "rgba-border",
            "rgba() used on border (violates solid-color invariant)",
        ))
    for match in (() if is_screen else BORDER_VAR_USE.finditer(text)):
        if match.group(1) in rgba_vars:
            findings.append(Finding(
                path,
                line_for(match.start()),
                "rgba-border",
                f"border: var(--{match.group(1)}) resolves to rgba() (solid-color invariant)",
            ))

    # Pass 2: per-line rule checks
    is_python = path.suffix == ".py"
    for i, raw in enumerate(lines, start=1):
        line = raw.strip()
        if not line:
            continue
        # Skip comment lines. Note: '#' alone is NOT a CSS or HTML comment; it
        # is the start of a CSS id selector (e.g. `#hero-bg { ... }`) or part of
        # a hex literal. Only treat '#' as a comment when scanning Python.
        if line.startswith("//"):
            continue
        if line.startswith("<!--"):
            continue
        if is_python and line.startswith("#"):
            continue

        if is_en and UNICODE_ARROW.search(raw):
            # skip CSS comment lines (/* ... */) and the arrow-in-CSS-content patterns
            stripped = raw.lstrip()
            if not stripped.startswith("/*") and not stripped.startswith("*") and "content:" not in raw:
                findings.append(Finding(path, line_offset + i, "arrow-unicode-in-en",
                                        "to (U+2192) in English template; use 'to' or '->' per patterns Section 2"))

        for match in LINE_HEIGHT_VALUE.finditer(raw):
            ceiling = 1.8 if is_social else 1.65 if is_screen and not is_en else 1.55
            if float(match.group(1)) > ceiling:
                findings.append(Finding(path, line_offset + i, "line-height-too-loose",
                                        f"{match.group(0)} exceeds {ceiling:.2f} ceiling"))

        for hex_match in HEX_ANY.finditer(raw):
            h = hex_match.group(0).lower()
            if h in COOL_GRAY_BLOCKLIST:
                findings.append(Finding(path, line_offset + i, "cool-gray",
                                        f"{h} is a cool / neutral gray, use warm undertone"))

        if not is_screen and not is_python:
            for rule, pattern in MERMAID_UNSAFE.items():
                if pattern.search(raw):
                    findings.append(Finding(path, line_offset + i, rule,
                        "un-normalized Mermaid SVG (run scripts/mermaid_normalize.py before embedding)"))

    # Pass 3: thin-border-radius block scan (pitfall #2 double-ring).
    # Judge each rule block as a whole, so a one-line rule or a radius on the
    # opening-brace line is seen the same as the expanded multi-line form.
    # Match bodies only: a selector group spanning the whole HTML makes the
    # scan quadratic on long brace-free text.
    raw_lines = raw_text.split("\n")
    for block in RULE_BODY_RE.finditer(text):
        body = block.group(1)
        if not BORDER_RADIUS_PROP.search(body):
            continue
        for border in THIN_CLOSED_BORDER.finditer(body):
            line = text.count("\n", 0, block.start(1) + border.start()) + 1
            if "skip-thin-border-radius" in raw_lines[line - 1]:
                continue
            findings.append(Finding(path, line_offset + line, "thin-border-radius",
                "thin border (<1pt) with border-radius -- pitfall #2 double-ring risk"))
    return findings


def check_all(verbose: bool) -> int:
    targets = iter_template_files(include_py=True, include_diagrams=True, include_marp_css=True)
    if not targets:
        print("ERROR: no templates found to lint (bad checkout?)")
        return 2

    findings: list[Finding] = []
    for p in targets:
        file_findings = scan_file(p)
        findings.extend(file_findings)
        if verbose:
            print(f"scanned {p.relative_to(ROOT)}: {len(file_findings)} finding(s)")

    if not findings:
        print(f"OK: no violations across {len(targets)} templates")
        return 0

    by_rule: dict[str, list[Finding]] = {}
    for f in findings:
        by_rule.setdefault(f.rule, []).append(f)

    print(f"ERROR: {len(findings)} violation(s) across {len({f.file for f in findings})} file(s)")
    for rule, items in by_rule.items():
        print(f"\n[{rule}] {len(items)}")
        for f in items:
            rel = f.file.relative_to(ROOT)
            print(f"  {rel}:{f.line}  {f.excerpt}")
    return 1


# ---------- off-palette color guard ----------
#
# design.md core invariant: a single chromatic accent (ink-blue) plus warm
# neutrals, zero cool tones. The salmon-border regression slipped past the
# token-drift guard because it was a hardcoded hex inside a component rule, not
# a :root token. This guard mechanizes the invariant: any hex literal in an
# editorial template that is neither a registered token value nor a cool-gray
# (those have their own rule) is an off-palette color. The single sanctioned
# semantic exception (the changelog breaking-change badge) is registered as the
# --breaking-* tokens, so it lands in `allowed` and passes.
#
# Scope is deliberately narrow: editorial TEMPLATES/*.html only. Diagrams use
# warm-gray chart ramps that are intentionally not tokens, and inline <svg>
# charts carry their own fills -- both are skipped (diagrams by directory, svg
# by block). :root blocks define the tokens themselves, so they are skipped too.


def _blank_block(text: str, regex: re.Pattern[str]) -> str:
    """Replace each match with same-length whitespace (newlines preserved) so
    line numbers stay accurate after a block is masked out."""
    def repl(m: re.Match[str]) -> str:
        return "".join(ch if ch == "\n" else " " for ch in m.group(0))
    return regex.sub(repl, text)


def _load_token_names() -> set[str]:
    """Return the set of registered token names (`--brand`, ...)."""
    if not TOKENS_FILE.exists():
        return set()
    try:
        return set(json.loads(TOKENS_FILE.read_text(encoding="utf-8")))
    except json.JSONDecodeError:
        return set()


def _load_token_values() -> set[str]:
    """Return the set of canonical token hex values (lowercased)."""
    if not TOKENS_FILE.exists():
        return set()
    try:
        data = json.loads(TOKENS_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return set()
    return {v.lower() for v in data.values() if isinstance(v, str) and v.startswith("#")}


def _off_palette_findings(
    path: Path, allowed: set[str], raw: str | None = None, line_offset: int = 0
) -> list[Finding]:
    """Flag hex literals outside the registered palette.

    `raw` and `line_offset` let a caller pass a snippet lifted out of a larger
    document (a Markdown fence) and still get line numbers into that document.
    """
    if raw is None:
        raw = path.read_text(encoding="utf-8", errors="replace")
    text = _strip_css_block_comments(raw)
    text = _blank_block(text, ROOT_BLOCK)
    text = _blank_block(text, SVG_BLOCK_RE)
    findings: list[Finding] = []
    for i, line in enumerate(text.splitlines(), start=1):
        for m in HEX_ANY.finditer(line):
            h = m.group(0).lower()
            if h in allowed:
                continue
            if h in COOL_GRAY_BLOCKLIST:
                continue  # reported by the cool-gray rule in scan_file
            findings.append(Finding(path, line_offset + i, "off-palette",
                                    f"{h} is not a registered token; single-accent palette violated"))
    return findings


ROOT_TOKEN_DEF = re.compile(
    r"(--[\w-]+)\s*:\s*"
    r"(#(?:[0-9a-fA-F]{8}|[0-9a-fA-F]{6}|[0-9a-fA-F]{4}|[0-9a-fA-F]{3}))"
    r"(?![0-9a-fA-F])"
)


def _root_token_findings(path: Path, allowed: set[str]) -> list[Finding]:
    """Flag `:root` token definitions whose hex is off the registered palette.

    `_off_palette_findings` blanks the `:root` block before scanning property
    values, so a dead or off-palette token *defined* in `:root` but never written
    as a literal hex in a property escapes every guard (this is how a stray
    `--brand-deep: #a64f33` second accent hid in portfolio.html). This closes that
    gap for print templates: every `:root` chromatic token must resolve to a
    registered tokens.json value. Screen templates (landing pages) keep their own
    local tokens outside the print palette, so callers exempt them.
    """
    raw = path.read_text(encoding="utf-8", errors="replace")
    text = _strip_css_block_comments(raw)
    findings: list[Finding] = []
    for block in ROOT_BLOCK.finditer(text):
        body_start = block.start(1)
        for vm in ROOT_TOKEN_DEF.finditer(block.group(1)):
            h = vm.group(2).lower()
            if h in allowed:
                continue
            if h in COOL_GRAY_BLOCKLIST:
                continue  # reported by the cool-gray rule in scan_file
            line = text.count("\n", 0, body_start + vm.start(2)) + 1
            findings.append(Finding(path, line, "off-palette-token",
                f"{vm.group(1)}: {h} is a :root token off the registered palette "
                "(single-accent invariant; register in tokens.json or remove)"))
    return findings


def _allowed_for(path: Path, allowed: set[str], text: str | None = None) -> set[str]:
    """The palette a file answers to: social-card files add the social papers."""
    return allowed | social_palette_values() if is_social_cards(path, text) else allowed


def _social_palette_findings(path: Path) -> list[Finding]:
    """A social-cards template mirrors references/social-palettes.json exactly.

    Every paper except the default parchment (which reuses the print tokens)
    needs its five --social-<paper>-<role> tokens and a `body.paper-<paper>`
    rule; parchment needs its footer line and print tokens that match.
    """
    raw = path.read_text(encoding="utf-8", errors="replace")
    found = {k: v.lower() for k, v in parse_root_vars(raw).items()}
    findings: list[Finding] = []

    def miss(message: str) -> None:
        findings.append(Finding(path, 1, "social-palette", message))

    print_roles = {"bg": "--parchment", "fg": "--near-black", "accent": "--brand", "muted": "--stone"}
    for name, paper in load_social_palettes().items():
        roles = ("line",) if name == "parchment" else SOCIAL_PAPER_ROLES
        for role in roles:
            token = f"--social-{name}-{role}"
            expected = paper[role].lower()
            if found.get(token) != expected:
                miss(f"{token} should be {expected} (social-palettes.json), got {found.get(token)}")
        if name == "parchment":
            for role, token in print_roles.items():
                if found.get(token) != paper[role].lower():
                    miss(f"parchment {role}: {token} should be {paper[role].lower()}, got {found.get(token)}")
        elif not re.search(rf"body\.paper-{name}\b", raw):
            miss(f"no body.paper-{name} rule for paper {name}")
    return findings


def check_off_palette(verbose: bool = False) -> int:
    allowed = _load_token_values()
    screen_names = set(SCREEN_TEMPLATES.values())
    targets = sorted(TEMPLATES.glob("*.html"))
    if not targets:
        print("ERROR: no templates found for off-palette scan (bad checkout?)")
        return 2
    findings: list[Finding] = []
    for p in targets:
        file_allowed = _allowed_for(p, allowed)
        file_findings = _off_palette_findings(p, file_allowed)
        if p.name not in screen_names:
            file_findings.extend(_root_token_findings(p, file_allowed))
        if p.name.startswith("social-cards"):
            file_findings.extend(_social_palette_findings(p))
        findings.extend(file_findings)
        if verbose:
            print(f"scanned {p.relative_to(ROOT)}: {len(file_findings)} off-palette finding(s)")

    # Demo HTML inherits template CSS by copy, so a token change leaves stale
    # hexes behind in site/assets/demos with no guard: that is exactly how demos
    # kept shipping old colors after palette edits. Scan property values only
    # (demos carry local :root copies on purpose). Pure white is sanctioned:
    # deliberate white-paper print variants document it in their header.
    demo_allowed = allowed | {"#ffffff", "#fff"}
    demo_targets = sorted((SITE_ROOT / "assets" / "demos").glob("*.html")) if SITE_ROOT else []
    if SITE_ROOT is not None and not demo_targets:
        print("ERROR: no demo HTML found under site/assets/demos (incomplete repository scan)")
        return 2
    for p in demo_targets:
        file_findings = _off_palette_findings(p, _allowed_for(p, demo_allowed))
        if p.name.startswith("demo-social-cards"):
            file_findings.extend(_social_palette_findings(p))
        findings.extend(file_findings)
        if verbose:
            print(f"scanned {p.relative_to(SITE_ROOT.parent)}: {len(file_findings)} off-palette finding(s)")

    if not findings:
        print(f"OK: no off-palette colors across {len(targets)} template(s) "
              f"and {len(demo_targets)} demo(s)")
        return 0

    print(f"\nERROR: [off-palette] {len(findings)}")
    for f in findings:
        base = SITE_ROOT.parent if SITE_ROOT and f.file.is_relative_to(SITE_ROOT) else ROOT
        print(f"  {f.file.relative_to(base)}:{f.line}  {f.excerpt}")
    return 1


# ---------- filled-document style drift ----------
#
# check_all and check_off_palette scan assets/templates: the shapes the project
# ships. Nothing scanned the other half of the workflow, the document an agent
# produces by copying a template and editing it. That copy is where the design
# system actually erodes, because every rule the template encodes lives in CSS
# comments an editing pass is free to ignore. These checks read a filled file
# with the template rules applied.

STYLE_BLOCK_RE = re.compile(r"<style\b[^>]*>(.*?)</style>", re.DOTALL | re.IGNORECASE)
CSS_RULE_RE = re.compile(r"([^{}]+)\{([^{}]*)\}", re.DOTALL)
BACKGROUND_DECL = re.compile(r"background(?:-color)?\s*:\s*([^;]+)", re.IGNORECASE)
PADDING_DECL = re.compile(r"padding\s*:", re.IGNORECASE)
RADIUS_DECL = re.compile(r"border-radius\s*:", re.IGNORECASE)
EMPTY_BACKGROUNDS = ("transparent", "none", "inherit", "initial", "unset")
INLINE_OR_FLOAT_DECL = re.compile(r"float\s*:\s*(left|right)|display\s*:\s*inline", re.IGNORECASE)

# Two component classes are filled and rounded by definition and say nothing
# about how the page raises a passage: chips and code. Scanning the shipped
# templates with no exemptions at all, these are the only selectors that need
# one; every other hit (.callout, .takeaway, .exec-summary, .analyst-box,
# .risk-item, .team-culture, .os-highlight) is a real emphasis container and
# must be counted. Keep this list at what that scan justified.
EMPHASIS_EXEMPT_SELECTORS = ("tag", "chip", "badge", "code", "pre", "kbd")


def _css_source(path: Path) -> str:
    """Return the CSS to analyze: <style> blocks for HTML, whole file for CSS."""
    raw = _strip_css_block_comments(path.read_text(encoding="utf-8", errors="replace"))
    if path.suffix.lower() == ".css":
        return raw
    blocks = STYLE_BLOCK_RE.findall(raw)
    return "\n".join(blocks)


def _resolve_css_value(value: str, root_vars: dict[str, str]) -> str:
    """Resolve one level of var() against the document's own :root, normalized.

    Two selectors reaching the same fill through different spellings
    (`var(--ivory)` and `#faf9f5`) are one design decision, not two, so the
    count must compare resolved colors rather than source text.
    """
    resolved = value.strip().lower()
    match = re.search(r"var\(\s*(--[\w-]+)", resolved)
    if match:
        resolved = root_vars.get(match.group(1), match.group(1)).strip().lower()
    return re.sub(r"\s+", "", resolved)


def _emphasis_container_findings(path: Path) -> list[Finding]:
    """Flag a document that fills its emphasis blocks in more than one color.

    A template reuses one fill across every raised block (long-doc runs three
    components off `--ivory`; resume runs `.team-culture` and `.os-highlight`
    off the same `--ivory`), so the page
    reads as one system used repeatedly. Drift looks different: a generated
    document invents a white rounded card for the question, then a tinted
    rounded block for the caveat, and the page now carries two unrelated
    container languages plus the template's own left-rule callout. Counting
    distinct resolved fills separates "one form, used often" from "several
    forms, invented as the document went along".

    Inline and floated rules are chips (tags, role pills), not block emphasis.
    """
    css = _css_source(path)
    if not css.strip():
        return []
    root_vars = parse_root_vars(css)
    fills: dict[str, tuple[str, int]] = {}
    for match in CSS_RULE_RE.finditer(css):
        selector = " ".join(match.group(1).split())
        body = match.group(2)
        if any(name == token or name.startswith(token + "-")
               for name in re.findall(r"[\w-]+", selector.lower())
               for token in EMPHASIS_EXEMPT_SELECTORS):
            continue
        if INLINE_OR_FLOAT_DECL.search(body):
            continue
        bg = BACKGROUND_DECL.search(body)
        if not bg:
            continue
        value = bg.group(1).strip().lower()
        if any(empty in value for empty in EMPTY_BACKGROUNDS):
            continue
        if not (PADDING_DECL.search(body) and RADIUS_DECL.search(body)):
            continue
        resolved = _resolve_css_value(value, root_vars)
        line = css.count("\n", 0, match.start(1)) + 1
        fills.setdefault(resolved, (selector, line))

    if len(fills) < 2:
        return []
    detail = ", ".join(f"{sel} ({fill})" for fill, (sel, _) in fills.items())
    last_line = max(line for _, line in fills.values())
    return [Finding(path, last_line, "emphasis-container-mix",
                    f"{len(fills)} different emphasis fills in one document ({detail}); "
                    "a page raises passages one way, reused, not a new container per idea")]


def check_style(paths: list[str], screen: bool | None = None) -> int:
    """CLI: --check-style filled.html [more.html ...]

    Applies the template rule set to a produced document. Same rules, other end
    of the pipeline.
    """
    files = [p for p in paths if not p.startswith("-")]
    if not files:
        print("ERROR: usage: --check-style path/to/filled.html [more.html ...]")
        return 2

    allowed = _load_token_values()
    failures = 0
    scanned = 0
    for raw in files:
        path = resolve_input(raw)
        if not path.exists():
            print(f"ERROR: {raw}: file not found")
            failures += 1
            continue
        scanned += 1
        rel = rel_to_root(path)
        findings = scan_file(path, screen=screen)
        findings.extend(_off_palette_findings(path, _allowed_for(path, allowed)))
        findings.extend(_emphasis_container_findings(path))
        if not findings:
            print(f"OK: {rel}: no style drift")
            continue
        failures += 1
        print(f"ERROR: {rel}: {len(findings)} style finding(s)")
        for f in findings:
            print(f"  {rel}:{f.line}  [{f.rule}] {f.excerpt}")

    if scanned == 0:
        print("ERROR: no documents scanned")
        return 2
    return 0 if failures == 0 else 1


# ---------- documented-snippet drift ----------
#
# The reference docs teach by example, and an agent copies those examples more
# readily than it reads the templates. Nothing checked them, so CHEATSHEET.md
# shipped a `.card` recipe that pairs a 0.5pt border with an 8pt radius (the
# double-ring pitfall the linter fails templates for) against `--border-cream`,
# a token that no longer exists. Every snippet the docs hand out is scanned
# with the same rules the templates answer to, and every var() it names must
# resolve to something real.

FENCE_RE = re.compile(r"^```(css|html)\s*$(.*?)^```\s*$", re.DOTALL | re.MULTILINE)
VAR_USE_RE = re.compile(r"var\(\s*(--[\w-]+)")
# A doc teaches by contrast: the wrong line sits next to the right one, tagged
# in a comment. Blank the tagged line so the rule fires on the fix, not the bug
# it is warning about.
NEGATIVE_EXAMPLE_LINE = re.compile(
    r"^.*/\*\s*(avoid|wrong|bad|never|don't|do not)\s*\*/.*$",
    re.IGNORECASE | re.MULTILINE,
)
# Any SVG markup: colors inside SVG answer to the diagram palette, not the
# print token set, and _off_palette_findings already blanks <svg> blocks in
# templates. A doc snippet showing <defs> without its <svg> wrapper gets the
# same treatment rather than a different verdict for the same markup.
SVG_MARKUP_HINT = re.compile(r"<(svg|defs|pattern|circle|path|rect|polyline|marker)\b", re.IGNORECASE)
# The white-paper variant is a documented product feature (production.md Part 1).
DOC_SANCTIONED_HEXES = {"#ffffff", "#fff"}
# A bare `--name: #hex;` line declares a token rather than spending a literal.
# Templates get the same pass: _off_palette_findings blanks their :root block.
# The palette chapter documents screen tokens too, which tokens.json (print
# only) does not own, so scanning declarations would fail the chapter for
# doing its job.
TOKEN_DECL_LINE = re.compile(r"^\s*--[\w-]+\s*:\s*[^;]+;.*$", re.MULTILINE)


def _documented_snippets(text: str) -> list[tuple[int, str]]:
    """Return [(first line number of the snippet body, snippet), ...]."""
    return [
        (text.count("\n", 0, m.start(2)) + 1, m.group(2))
        for m in FENCE_RE.finditer(text)
    ]


def _undefined_token_findings(
    path: Path, snippet: str, line_offset: int, defined: set[str]
) -> list[Finding]:
    """Flag var() references a reader cannot resolve.

    A snippet may define its own variables inline, so anything the snippet
    itself declares counts as defined.
    """
    local = set(re.findall(r"(--[\w-]+)\s*:", snippet))
    findings: list[Finding] = []
    for i, line in enumerate(snippet.splitlines(), start=1):
        for m in VAR_USE_RE.finditer(line):
            name = m.group(1)
            if name in defined or name in local:
                continue
            findings.append(Finding(path, line_offset + i, "undefined-token",
                                    f"{name} is not a registered token and is not defined in the snippet"))
    return findings


def check_docs(paths: list[str]) -> int:
    """CLI: --check-docs [doc.md ...]

    Scans the CSS and HTML snippets the reference docs teach from. With no
    arguments it walks every doc that carries snippets.
    """
    targets = [p for p in paths if not p.startswith("-")]
    if not targets:
        candidates = [ROOT / "CHEATSHEET.md", ROOT / "SKILL.md"]
        candidates += sorted((ROOT / "references").glob("*.md"))
        targets = [str(p) for p in candidates if p.exists()]

    # A snippet may legitimately name any token the shipped templates define,
    # not just the print palette: landing pages carry their own screen tokens
    # (--warm-sand, --dark-surface) that tokens.json deliberately does not own.
    defined = set(_load_token_names())
    for template in sorted(TEMPLATES.glob("*.html")):
        defined |= set(parse_root_vars(template.read_text(encoding="utf-8", errors="replace")))
    allowed = _load_token_values() | DOC_SANCTIONED_HEXES
    failures = 0
    scanned = 0
    for raw_path in targets:
        path = resolve_input(raw_path)
        if not path.exists():
            print(f"ERROR: {raw_path}: file not found")
            failures += 1
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        snippets = _documented_snippets(text)
        if not snippets:
            continue
        scanned += 1
        rel = rel_to_root(path)
        findings: list[Finding] = []
        for line_offset, raw_snippet in snippets:
            snippet = _blank_block(raw_snippet, NEGATIVE_EXAMPLE_LINE)
            findings.extend(scan_text(snippet, path, line_offset))
            if not SVG_MARKUP_HINT.search(snippet):
                spent = _blank_block(snippet, TOKEN_DECL_LINE)
                findings.extend(_off_palette_findings(path, allowed, spent, line_offset))
            findings.extend(_undefined_token_findings(path, snippet, line_offset, defined))
        if not findings:
            print(f"OK: {rel}: {len(snippets)} snippet(s) clean")
            continue
        failures += 1
        print(f"ERROR: {rel}: {len(findings)} finding(s) across {len(snippets)} snippet(s)")
        for f in sorted(findings, key=lambda f: f.line):
            print(f"  {rel}:{f.line}  [{f.rule}] {f.excerpt}")

    if scanned == 0:
        print("ERROR: no documents with snippets scanned")
        return 2
    return 0 if failures == 0 else 1


# ---------- cross-template consistency ----------
#
# The project intentionally ships CN/EN templates as forked single-file HTML
# (no shared partials). The price of that decision is drift: a maintainer
# updating one side of a pair can silently leave the other behind. This check
# pairs each base template (e.g. `foo.html`) with every recognized locale
# variant (`foo-en.html`, `foo-ko.html`), parses the `:root { ... }` block of
# each, and flags variables that differ. Font-stack variables (`--serif`,
# `--sans`, `--mono`, `--latin-ui`) are allowlisted because each locale
# deliberately uses different fonts.

_VARIANT_SUFFIXES: tuple[str, ...] = ("-en", "-ko")


def _pair_names() -> list[tuple[str, str]]:
    """Return [(base_name, variant_name), ...] for every base template that has
    one of the recognized locale-variant siblings (`-en`, `-ko`).

    A base template is any registered name that does not itself end in a
    recognized variant suffix.
    """
    pairs: list[tuple[str, str]] = []
    seen = set(HTML_TEMPLATES) | set(SCREEN_TEMPLATES)
    for name in sorted(seen):
        if any(name.endswith(s) for s in _VARIANT_SUFFIXES):
            continue
        for suffix in _VARIANT_SUFFIXES:
            variant = f"{name}{suffix}"
            if variant in seen:
                pairs.append((name, variant))
    return pairs


def _source_for(name: str) -> Path:
    """Return the source path for a template name across registries."""
    if name in HTML_TEMPLATES:
        return TEMPLATES / HTML_TEMPLATES[name].source
    if name in SCREEN_TEMPLATES:
        return TEMPLATES / SCREEN_TEMPLATES[name]
    raise KeyError(f"unknown template name: {name}")


def _extract_root_vars(html_path: Path) -> dict[str, str]:
    """Return {var_name: value} merged across every `:root { ... }` block."""
    text = html_path.read_text(encoding="utf-8", errors="replace")
    return parse_root_vars(text)


def check_cross_template_consistency(verbose: bool = False) -> int:
    pairs = _pair_names()
    if not pairs:
        print("ERROR: no base-variant template pairs found (bad checkout?)")
        return 2
    drift: list[tuple[str, str, str, str]] = []  # (pair, var, base_value, variant_value)

    for base_name, variant_name in pairs:
        try:
            base_path = _source_for(base_name)
            variant_path = _source_for(variant_name)
        except KeyError:
            continue
        if not base_path.exists() or not variant_path.exists():
            continue

        base_vars = _extract_root_vars(base_path)
        variant_vars = _extract_root_vars(variant_path)

        shared_keys = set(base_vars) & set(variant_vars)
        for key in sorted(shared_keys):
            if key in CROSS_TEMPLATE_ALLOWED_VARS:
                continue
            if base_vars[key].lower() != variant_vars[key].lower():
                drift.append((base_name, key, base_vars[key], variant_vars[key]))

        # A var defined on only one side is drift too: it usually means a
        # maintainer added or dropped a token on one side of the fork. That is
        # exactly the "left the other side behind" failure this check exists
        # to catch, so report it instead of silently comparing the overlap.
        for key in sorted((set(base_vars) ^ set(variant_vars)) - CROSS_TEMPLATE_ALLOWED_VARS):
            if key in base_vars:
                drift.append((base_name, key, base_vars[key], f"missing from {variant_name}"))
            else:
                drift.append((base_name, key, f"missing from {base_name}", variant_vars[key]))

        if verbose:
            print(f"  pair {base_name}/{variant_name}: checked {len(shared_keys)} shared vars")

    if not drift:
        print(f"OK: cross-template :root vars in sync across {len(pairs)} base-variant pair(s)")
        return 0

    print(f"\nERROR: [cross-template-drift] {len(drift)}")
    for pair, var, base_val, variant_val in drift:
        print(f"  {pair}: {var} base={base_val} variant={variant_val}")
    return 1
