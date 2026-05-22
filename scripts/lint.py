"""Template lint rules and cross-template consistency checks.

Splits out from build.py:
  - scan_file: per-line + per-block lint for HTML/CSS/PPTX templates.
  - check_all: scan every template and aggregate findings by rule.
  - check_cross_template_consistency: pair CN/EN templates and report :root
    variable drift outside the allowlist.

Each `Finding` is anchored to a file path + line number so editors can jump
straight to the violation. Rules encode real WeasyPrint pitfalls (rgba on
background, thin border with border-radius, etc.) — not style preferences.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from shared import (
    COOL_GRAY_BLOCKLIST,
    DIAGRAMS,
    HTML_TEMPLATES,
    ROOT,
    SCREEN_TEMPLATES,
    TEMPLATES,
    load_cross_template_allowlist,
)
from tokens import CSS_VAR, ROOT_BLOCK

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
    targets: list[Path] = []
    for p in TEMPLATES.glob("*.html"):
        targets.append(p)
    for p in TEMPLATES.glob("*.py"):
        targets.append(p)
    if DIAGRAMS.exists():
        for p in DIAGRAMS.glob("*.html"):
            targets.append(p)

    findings: list[Finding] = []
    for p in sorted(targets):
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


# ---------- cross-template consistency ----------
#
# The project intentionally ships CN/EN templates as forked single-file HTML
# (no shared partials). The price of that decision is drift: a maintainer
# updating one side of a pair can silently leave the other behind. This check
# pairs each `foo.html` with its `foo-en.html`, parses the `:root { ... }`
# block of both, and flags variables that differ. Font-stack variables
# (`--serif`, `--sans`, `--mono`, `--latin-ui`) are allowlisted because CN/EN
# deliberately use different fonts.

def _pair_names() -> list[tuple[str, str]]:
    """Return [(cn_name, en_name), ...] for every CN template that has an -en sibling."""
    pairs: list[tuple[str, str]] = []
    seen = set(HTML_TEMPLATES) | set(SCREEN_TEMPLATES)
    for name in sorted(seen):
        if name.endswith("-en"):
            continue
        en_name = f"{name}-en"
        if en_name in seen:
            pairs.append((name, en_name))
    return pairs


def _source_for(name: str) -> tuple[Path, Path]:
    """Return (source path, directory) for a template name across registries."""
    if name in HTML_TEMPLATES:
        return TEMPLATES / HTML_TEMPLATES[name].source, TEMPLATES
    if name in SCREEN_TEMPLATES:
        return TEMPLATES / SCREEN_TEMPLATES[name], TEMPLATES
    raise KeyError(f"unknown template name: {name}")


def _extract_root_vars(html_path: Path) -> dict[str, str]:
    """Return {var_name: value} for the first `:root { ... }` block in the file."""
    text = html_path.read_text(encoding="utf-8", errors="replace")
    match = ROOT_BLOCK.search(text)
    if not match:
        return {}
    block = match.group(1)
    return {
        f"--{m.group(1)}": m.group(2).strip()
        for m in CSS_VAR.finditer(block)
    }


def check_cross_template_consistency(verbose: bool = False) -> int:
    allowlist = load_cross_template_allowlist()
    always_allowed = set(allowlist.get("always_allowed", []))
    per_pair = allowlist.get("per_pair_allowed", {}) or {}

    pairs = _pair_names()
    drift: list[tuple[str, str, str, str]] = []  # (pair, var, cn_value, en_value)

    for cn_name, en_name in pairs:
        try:
            cn_path, _ = _source_for(cn_name)
            en_path, _ = _source_for(en_name)
        except KeyError:
            continue
        if not cn_path.exists() or not en_path.exists():
            continue

        cn_vars = _extract_root_vars(cn_path)
        en_vars = _extract_root_vars(en_path)
        allowed_for_pair = always_allowed | set(per_pair.get(cn_name, []) or [])

        shared_keys = set(cn_vars) & set(en_vars)
        for key in sorted(shared_keys):
            if key in allowed_for_pair:
                continue
            if cn_vars[key].lower() != en_vars[key].lower():
                drift.append((cn_name, key, cn_vars[key], en_vars[key]))

        if verbose:
            print(f"  pair {cn_name}/{en_name}: checked {len(shared_keys)} shared vars")

    if not drift:
        print(f"OK: cross-template :root vars in sync across {len(pairs)} CN/EN pair(s)")
        return 0

    print(f"\n[cross-template-drift] {len(drift)}")
    for pair, var, cn_val, en_val in drift:
        print(f"  {pair}: {var} CN={cn_val} EN={en_val}")
    return 1
