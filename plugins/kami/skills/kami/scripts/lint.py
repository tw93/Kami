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
    SCREEN_TEMPLATES,
    TEMPLATES,
    TOKENS_FILE,
    iter_template_files,
)
from tokens import ROOT_BLOCK, parse_root_vars

# Font-stack vars legitimately differ between a base template and its locale
# variants (-en, -ko); every other :root var must match across the pair.
CROSS_TEMPLATE_ALLOWED_VARS = {"--serif", "--sans", "--mono", "--latin-ui"}

RGBA_BG_DIRECT = re.compile(r"background(?:-color)?\s*:\s*[^;]*rgba\s*\(", re.IGNORECASE)
RGBA_VAR_DEF = re.compile(r"--([\w-]+)\s*:\s*[^;]*rgba\s*\(", re.IGNORECASE)
BG_VAR_USE = re.compile(r"background(?:-color)?\s*:\s*[^;]*var\s*\(\s*--([\w-]+)", re.IGNORECASE)
RGBA_BORDER_DIRECT = re.compile(r"border(?:-\w+)?\s*:\s*[^;]*rgba\s*\(", re.IGNORECASE)
BORDER_VAR_USE = re.compile(r"border(?:-\w+)?\s*:\s*[^;]*var\s*\(\s*--([\w-]+)", re.IGNORECASE)
LINE_HEIGHT_LOOSE = re.compile(r"line-height\s*:\s*1\.[6-9]\d*", re.IGNORECASE)
UNICODE_ARROW = re.compile(r"→")  # U+2192; should not appear in EN template body
HEX_ANY = re.compile(r"#[0-9a-fA-F]{3,6}\b")
# Thin closed border: border shorthand (not single-side) with sub-1pt width -- pitfall #2
THIN_CLOSED_BORDER = re.compile(
    r"border(?!-(?:left|right|top|bottom))\s*:\s*[^;]*0\.\d+pt",
    re.IGNORECASE,
)
BORDER_RADIUS_PROP = re.compile(r"border-radius\s*:", re.IGNORECASE)
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


def scan_file(path: Path) -> list[Finding]:
    findings: list[Finding] = []
    raw_text = path.read_text(encoding="utf-8", errors="replace")
    text = _strip_css_block_comments(raw_text)
    lines = text.splitlines()

    # Pass 1: collect variable names that hold rgba(...) so the tag-background
    # bug can be detected through one level of indirection.
    rgba_vars: set[str] = set()
    for raw in lines:
        m = RGBA_VAR_DEF.search(raw)
        if m:
            rgba_vars.add(m.group(1))

    is_en = path.name.endswith("-en.html")
    # Screen-only templates (landing pages) never go through WeasyPrint, so the
    # Mermaid-unsafe-SVG rule does not apply to them.
    is_screen = path.name in set(SCREEN_TEMPLATES.values())

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

        if RGBA_BG_DIRECT.search(raw):
            findings.append(Finding(path, i, "rgba-background",
                                    "rgba() used directly on background (tag double-rectangle bug)"))

        bg_var = BG_VAR_USE.search(raw)
        if bg_var and bg_var.group(1) in rgba_vars:
            findings.append(Finding(path, i, "rgba-background",
                                    f"background: var(--{bg_var.group(1)}) resolves to rgba() (tag double-rectangle bug)"))

        if RGBA_BORDER_DIRECT.search(raw):
            findings.append(Finding(path, i, "rgba-border",
                                    "rgba() used on border (violates solid-color invariant)"))

        border_var = BORDER_VAR_USE.search(raw)
        if border_var and border_var.group(1) in rgba_vars:
            findings.append(Finding(path, i, "rgba-border",
                                    f"border: var(--{border_var.group(1)}) resolves to rgba() (solid-color invariant)"))

        if is_en and UNICODE_ARROW.search(raw):
            # skip CSS comment lines (/* ... */) and the arrow-in-CSS-content patterns
            stripped = raw.lstrip()
            if not stripped.startswith("/*") and not stripped.startswith("*") and "content:" not in raw:
                findings.append(Finding(path, i, "arrow-unicode-in-en",
                                        "to (U+2192) in English template; use 'to' or '->' per patterns Section 2"))

        m = LINE_HEIGHT_LOOSE.search(raw)
        if m:
            findings.append(Finding(path, i, "line-height-too-loose",
                                    f"{m.group(0)} exceeds 1.55 ceiling"))

        for hex_match in HEX_ANY.finditer(raw):
            h = hex_match.group(0).lower()
            if h in COOL_GRAY_BLOCKLIST:
                findings.append(Finding(path, i, "cool-gray",
                                        f"{h} is a cool / neutral gray, use warm undertone"))

        if not is_screen and not is_python:
            for rule, pattern in MERMAID_UNSAFE.items():
                if pattern.search(raw):
                    findings.append(Finding(path, i, rule,
                        "un-normalized Mermaid SVG (run scripts/mermaid_normalize.py before embedding)"))

    # Pass 3: thin-border-radius block scan (pitfall #2 double-ring).
    # For each thin closed border line, scan backward to the block open and
    # forward to the block close, checking for border-radius in the same block.
    for i, raw in enumerate(lines):
        if not THIN_CLOSED_BORDER.search(raw):
            continue
        if "skip-thin-border-radius" in raw:
            continue
        found = False
        # Scan backward; stop at { or } (entering/leaving a block).
        for j in range(i - 1, max(0, i - 6) - 1, -1):
            if "{" in lines[j] or "}" in lines[j]:
                break
            if BORDER_RADIUS_PROP.search(lines[j]):
                found = True
                break
        # Scan forward; stop at } (leaving the block).
        if not found:
            for j in range(i + 1, min(len(lines), i + 6)):
                if "}" in lines[j]:
                    break
                if BORDER_RADIUS_PROP.search(lines[j]):
                    found = True
                    break
        if found:
            findings.append(Finding(path, i + 1, "thin-border-radius",
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
# Scope covers editorial HTML templates and the self-contained Marp theme CSS.
# Diagrams use warm-gray chart ramps that are intentionally not tokens, and
# inline <svg> charts carry their own fills -- both are skipped (diagrams by
# directory, svg by block). :root definitions are checked separately below.


def _blank_block(text: str, regex: re.Pattern[str]) -> str:
    """Replace each match with same-length whitespace (newlines preserved) so
    line numbers stay accurate after a block is masked out."""
    def repl(m: re.Match[str]) -> str:
        return "".join(ch if ch == "\n" else " " for ch in m.group(0))
    return regex.sub(repl, text)


def _load_token_values() -> set[str]:
    """Return the set of canonical token hex values (lowercased)."""
    if not TOKENS_FILE.exists():
        return set()
    try:
        data = json.loads(TOKENS_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return set()
    return {v.lower() for v in data.values() if isinstance(v, str) and v.startswith("#")}


def _off_palette_findings(path: Path, allowed: set[str]) -> list[Finding]:
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
            findings.append(Finding(path, i, "off-palette",
                                    f"{h} is not a registered token; single-accent palette violated"))
    return findings


ROOT_TOKEN_DEF = re.compile(r"(--[\w-]+)\s*:\s*(#[0-9a-fA-F]{3,6})\b")


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


def check_off_palette(verbose: bool = False) -> int:
    allowed = _load_token_values()
    screen_names = set(SCREEN_TEMPLATES.values())
    targets = iter_template_files(include_marp_css=True)
    if not targets:
        print("ERROR: no templates found for off-palette scan (bad checkout?)")
        return 2
    findings: list[Finding] = []
    for p in targets:
        file_findings = _off_palette_findings(p, allowed)
        if p.name not in screen_names:
            file_findings.extend(_root_token_findings(p, allowed))
        findings.extend(file_findings)
        if verbose:
            print(f"scanned {p.relative_to(ROOT)}: {len(file_findings)} off-palette finding(s)")

    if not findings:
        print(f"OK: no off-palette colors across {len(targets)} template(s)")
        return 0

    print(f"\nERROR: [off-palette] {len(findings)}")
    for f in findings:
        print(f"  {f.file.relative_to(ROOT)}:{f.line}  {f.excerpt}")
    return 1


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


def _source_for(name: str) -> tuple[Path, Path]:
    """Return (source path, directory) for a template name across registries."""
    if name in HTML_TEMPLATES:
        return TEMPLATES / HTML_TEMPLATES[name].source, TEMPLATES
    if name in SCREEN_TEMPLATES:
        return TEMPLATES / SCREEN_TEMPLATES[name], TEMPLATES
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
            base_path, _ = _source_for(base_name)
            variant_path, _ = _source_for(variant_name)
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
