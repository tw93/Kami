#!/usr/bin/env python3
"""kami build & check

Usage:
    python3 scripts/build.py                      # build all 24 examples (10 HTML + 12 diagrams + 2 PPTX)
    python3 scripts/build.py resume               # build one template, print pages + fonts
    python3 scripts/build.py --check              # scan templates for CSS rule violations
    python3 scripts/build.py --check -v           # verbose (show each scanned file)
    python3 scripts/build.py --sync               # check CSS token drift across templates
    python3 scripts/build.py --verify             # build all + page count + font checks
    python3 scripts/build.py --verify resume-en   # single target full verification
    python3 scripts/build.py --check-placeholders path/to/doc.html
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEMPLATES = ROOT / "assets" / "templates"
DIAGRAMS = ROOT / "assets" / "diagrams"
EXAMPLES = ROOT / "assets" / "examples"

# name -> (source, max_pages). max_pages=0 means no hard check.
HTML_TARGETS: dict[str, tuple[str, int]] = {
    # Chinese
    "one-pager":    ("one-pager.html", 1),
    "letter":       ("letter.html", 1),
    "long-doc":     ("long-doc.html", 0),
    "portfolio":    ("portfolio.html", 0),
    "resume":       ("resume.html", 2),
    # English
    "one-pager-en": ("one-pager-en.html", 1),
    "letter-en":    ("letter-en.html", 1),
    "long-doc-en":  ("long-doc-en.html", 0),
    "portfolio-en": ("portfolio-en.html", 0),
    "resume-en":    ("resume-en.html", 2),
}
PPTX_TARGETS: dict[str, str] = {
    "slides":    "slides.py",
    "slides-en": "slides-en.py",
}

# Diagram HTMLs live in a separate directory and have no page-count contract.
DIAGRAM_TARGETS: dict[str, str] = {
    "diagram-architecture": "architecture.html",
    "diagram-flowchart":    "flowchart.html",
    "diagram-quadrant":     "quadrant.html",
    "diagram-bar-chart":    "bar-chart.html",
    "diagram-line-chart":   "line-chart.html",
    "diagram-donut-chart":  "donut-chart.html",
    "diagram-state-machine": "state-machine.html",
    "diagram-timeline":      "timeline.html",
    "diagram-swimlane":      "swimlane.html",
    "diagram-tree":          "tree.html",
    "diagram-layer-stack":   "layer-stack.html",
    "diagram-venn":          "venn.html",
}


# ------------------------- build -------------------------

def build_html(name: str, source: str, max_pages: int,
               src_dir: Path = TEMPLATES) -> bool:
    try:
        from weasyprint import HTML
        from pypdf import PdfReader
    except ImportError:
        print("ERROR: missing deps: pip install weasyprint pypdf --break-system-packages")
        return False

    src = src_dir / source
    if not src.exists():
        print(f"ERROR: {name}: source not found ({src})")
        return False

    EXAMPLES.mkdir(parents=True, exist_ok=True)
    out = EXAMPLES / f"{name}.pdf"

    # weasyprint resolves @font-face relative to CWD. Run from the source dir
    # so fonts placed next to the HTML are found.
    HTML(str(src), base_url=str(src.parent)).write_pdf(str(out))
    n = len(PdfReader(str(out)).pages)
    msg = f"OK: {name}: {n} pages"
    if max_pages and n > max_pages:
        msg = f"ERROR: {name}: {n} pages (limit {max_pages})"
        print(msg)
        return False
    print(msg)
    return True


def build_slides(name: str = "slides") -> bool:
    source = PPTX_TARGETS.get(name)
    if source is None:
        print(f"ERROR: {name}: unknown slides target")
        return False
    src = TEMPLATES / source
    if not src.exists():
        print(f"ERROR: {name}: source not found ({src})")
        return False

    EXAMPLES.mkdir(parents=True, exist_ok=True)
    out = EXAMPLES / f"{name}.pptx"
    result = subprocess.run(
        [sys.executable, str(src)],
        cwd=str(src.parent),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"ERROR: {name}: {result.stderr.strip() or 'script failed'}")
        return False
    # The script writes output.pptx in cwd; move to examples/ under our name.
    generated = src.parent / "output.pptx"
    if generated.exists():
        generated.replace(out)
        print(f"OK: {name}: generated {out.name}")
        return True
    print(f"ERROR: {name}: output.pptx not produced")
    return False


def build_all() -> int:
    failures = 0
    for name, (source, max_pages) in HTML_TARGETS.items():
        if not build_html(name, source, max_pages):
            failures += 1
    for name, source in DIAGRAM_TARGETS.items():
        if not build_html(name, source, 0, src_dir=DIAGRAMS):
            failures += 1
    for name in PPTX_TARGETS:
        if not build_slides(name):
            failures += 1
    return failures


def build_single(name: str) -> int:
    if name in HTML_TARGETS:
        source, max_pages = HTML_TARGETS[name]
        ok = build_html(name, source, max_pages)
        if ok:
            show_fonts(EXAMPLES / f"{name}.pdf")
        return 0 if ok else 1
    if name in DIAGRAM_TARGETS:
        source = DIAGRAM_TARGETS[name]
        ok = build_html(name, source, 0, src_dir=DIAGRAMS)
        return 0 if ok else 1
    if name in PPTX_TARGETS:
        return 0 if build_slides(name) else 1
    known = list(HTML_TARGETS) + list(DIAGRAM_TARGETS) + list(PPTX_TARGETS)
    print(f"ERROR: unknown target: {name}. Known: {', '.join(known)}")
    return 2


def show_fonts(pdf: Path) -> None:
    if not pdf.exists():
        return
    try:
        out = subprocess.run(["pdffonts", str(pdf)], capture_output=True, text=True, check=False)
        if out.returncode == 0:
            print("--- pdffonts ---")
            print(out.stdout.rstrip())
    except FileNotFoundError:
        pass  # pdffonts not installed; silent


# ------------------------- sync -------------------------

ROOT_BLOCK = re.compile(r":root\s*\{([^}]*)\}", re.DOTALL)
CSS_VAR = re.compile(r"--([\w-]+)\s*:\s*([^;]+);")
TOKENS_FILE = ROOT / "references" / "tokens.json"


def sync_check(verbose: bool = False) -> int:
    if not TOKENS_FILE.exists():
        print(f"ERROR: tokens.json not found at {TOKENS_FILE.relative_to(ROOT)}")
        return 1

    canonical: dict[str, str] = json.loads(TOKENS_FILE.read_text())

    targets: list[Path] = list(TEMPLATES.glob("*.html"))
    if DIAGRAMS.exists():
        targets.extend(DIAGRAMS.glob("*.html"))

    drift: list[tuple[str, str, str, str]] = []  # (file, token, expected, actual)

    for path in sorted(targets):
        text = path.read_text(encoding="utf-8", errors="replace")
        block_match = ROOT_BLOCK.search(text)
        if not block_match:
            if verbose:
                print(f"  (skip {path.name}: no :root block)")
            continue
        root_block = block_match.group(1)
        found: dict[str, str] = {
            m.group(1): m.group(2).strip()
            for m in CSS_VAR.finditer(root_block)
        }
        rel = path.relative_to(ROOT)
        for token, expected in canonical.items():
            name = token.lstrip("-")
            actual = found.get(name)
            # Only flag if the template defines the token but with a wrong value.
            # Templates that don't use a token don't need to define it.
            if actual is not None and actual.lower() != expected.lower():
                drift.append((str(rel), token, expected, actual))

    if not drift:
        print(f"OK: tokens in sync across {len(targets)} template(s)")
        return 0

    print(f"\n[token-drift] {len(drift)}")
    for file, token, expected, actual in drift:
        print(f"  {file}: {token} expected {expected}, got {actual}")

    return 1


# ------------------------- verify -------------------------

PLACEHOLDER = re.compile(r"\{\{[^}]+\}\}")

# Primary fonts expected in embedded PDF font names
CN_PRIMARY_FONTS = {"TsangerJinKai02"}
EN_PRIMARY_FONTS = {"Newsreader", "Inter"}


def _pdf_font_names(pdf_path: Path) -> set[str]:
    def _resolve_pdf_obj(obj):
        if obj is None:
            return None
        try:
            return obj.get_object() if hasattr(obj, "get_object") else obj
        except Exception:
            return obj

    try:
        from pypdf import PdfReader
        reader = PdfReader(str(pdf_path))
        fonts: set[str] = set()
        for page in reader.pages:
            resources = _resolve_pdf_obj(page.get("/Resources"))
            if resources is None or not hasattr(resources, "get"):
                continue
            font_dict = _resolve_pdf_obj(resources.get("/Font"))
            if font_dict is None or not hasattr(font_dict, "values"):
                continue
            for obj in font_dict.values():
                resolved = _resolve_pdf_obj(obj)
                if resolved is None or not hasattr(resolved, "get"):
                    continue
                base = resolved.get("/BaseFont")
                if base:
                    fonts.add(str(base).lstrip("/"))
        return fonts
    except Exception:
        return set()


def verify_target(name: str, source: str, max_pages: int, src_dir: Path) -> list[str]:
    issues: list[str] = []
    src = src_dir / source
    if not src.exists():
        issues.append(f"source not found: {src}")
        return issues

    try:
        from weasyprint import HTML
        from pypdf import PdfReader
    except ImportError:
        issues.append("missing deps: pip install weasyprint pypdf --break-system-packages")
        return issues

    EXAMPLES.mkdir(parents=True, exist_ok=True)
    out = EXAMPLES / f"{name}.pdf"
    HTML(str(src), base_url=str(src_dir)).write_pdf(str(out))

    # page count check
    n = len(PdfReader(str(out)).pages)
    if max_pages and n > max_pages:
        issues.append(f"page overflow: {n} pages (limit {max_pages})")

    # font check
    embedded = _pdf_font_names(out)
    fallback_present = any(
        kw in font for font in embedded
        for kw in ("Newsreader", "Inter", "TsangerJinKai", "SourceHan", "Noto", "Georgia", "Charter", "Songti")
    )

    # Diagram templates are language-neutral and often rely on fallback stacks,
    # so only enforce that at least one recognizable serif/sans fallback exists.
    is_diagram = src_dir == DIAGRAMS
    if is_diagram:
        if not fallback_present:
            issues.append(f"no recognizable font embedded in {out.name}")
        return issues

    is_en = name.endswith("-en")
    expected = EN_PRIMARY_FONTS if is_en else CN_PRIMARY_FONTS
    if not any(exp in font_name for exp in expected for font_name in embedded):
        primary = next(iter(expected))
        if not fallback_present:
            issues.append(f"no recognizable font embedded in {out.name}")
        else:
            issues.append(f"primary font ({primary}) not embedded; using fallback")

    return issues


def verify_slides_target(name: str) -> list[str]:
    return [] if build_slides(name) else ["slides build failed"]


def verify_all(target: str | None = None) -> int:
    targets_to_run: dict[str, tuple[str, int, Path] | None] = {}
    if target:
        if target in HTML_TARGETS:
            src, mp = HTML_TARGETS[target]
            targets_to_run[target] = (src, mp, TEMPLATES)
        elif target in DIAGRAM_TARGETS:
            targets_to_run[target] = (DIAGRAM_TARGETS[target], 0, DIAGRAMS)
        elif target in PPTX_TARGETS:
            targets_to_run[target] = None
        else:
            print(f"ERROR: unknown target: {target}")
            return 2
    else:
        for name, (src, mp) in HTML_TARGETS.items():
            targets_to_run[name] = (src, mp, TEMPLATES)
        for name, src in DIAGRAM_TARGETS.items():
            targets_to_run[name] = (src, 0, DIAGRAMS)
        for name in PPTX_TARGETS:
            targets_to_run[name] = None

    failures = 0
    rows: list[tuple[str, str]] = []
    for name, config in targets_to_run.items():
        if config is None:
            issues = verify_slides_target(name)
        else:
            source, max_pages, src_dir = config
            issues = verify_target(name, source, max_pages, src_dir)
        if issues:
            rows.append((f"ERROR: {name}", "; ".join(issues)))
            failures += 1
        else:
            rows.append((f"OK: {name}", "ok"))

    for status, detail in rows:
        print(f"{status}: {detail}")

    return 0 if failures == 0 else 1


def check_placeholders(paths: list[str]) -> int:
    if not paths:
        print("ERROR: provide at least one HTML file to scan")
        return 2

    failures = 0
    for raw in paths:
        path = Path(raw)
        if not path.is_absolute():
            path = ROOT / path
        if not path.exists():
            print(f"ERROR: {raw}: file not found")
            failures += 1
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        hits = list(dict.fromkeys(PLACEHOLDER.findall(text)))
        rel = path.relative_to(ROOT) if path.is_relative_to(ROOT) else path
        if hits:
            print(f"ERROR: {rel}: unfilled placeholder(s): {', '.join(hits)}")
            failures += 1
        else:
            print(f"OK: {rel}: no placeholders")

    return 0 if failures == 0 else 1


# ------------------------- check -------------------------

# Cool / neutral gray hex values that violate the "warm undertone only" rule.
COOL_GRAY_BLOCKLIST = {
    "#888", "#888888", "#666", "#666666", "#999", "#999999",
    "#ccc", "#cccccc", "#ddd", "#dddddd", "#eee", "#eeeeee",
    "#111", "#111111", "#222", "#222222", "#333", "#333333",
    "#444", "#444444", "#555", "#555555", "#777", "#777777",
    "#aaa", "#aaaaaa", "#bbb", "#bbbbbb",
    # Tailwind cool grays
    "#6b7280", "#9ca3af", "#d1d5db", "#e5e7eb", "#f3f4f6",
    "#4b5563", "#374151", "#1f2937", "#111827",
    # Bootstrap-like neutrals
    "#f8f9fa", "#e9ecef", "#dee2e6", "#ced4da", "#adb5bd",
    "#6c757d", "#495057", "#343a40", "#212529",
}

RGBA_BG_DIRECT = re.compile(r"background(?:-color)?\s*:\s*[^;]*rgba\s*\(", re.IGNORECASE)
RGBA_VAR_DEF = re.compile(r"--([\w-]+)\s*:\s*[^;]*rgba\s*\(", re.IGNORECASE)
BG_VAR_USE = re.compile(r"background(?:-color)?\s*:\s*[^;]*var\s*\(\s*--([\w-]+)", re.IGNORECASE)
RGBA_BORDER_DIRECT = re.compile(r"border(?:-\w+)?\s*:\s*[^;]*rgba\s*\(", re.IGNORECASE)
BORDER_VAR_USE = re.compile(r"border(?:-\w+)?\s*:\s*[^;]*var\s*\(\s*--([\w-]+)", re.IGNORECASE)
LINE_HEIGHT_LOOSE = re.compile(r"line-height\s*:\s*1\.[6-9]\d*", re.IGNORECASE)
UNICODE_ARROW = re.compile(r"→")  # U+2192; should not appear in EN template body
HEX_ANY = re.compile(r"#[0-9a-fA-F]{3,6}\b")


@dataclass
class Finding:
    file: Path
    line: int
    rule: str
    excerpt: str


def scan_file(path: Path) -> list[Finding]:
    findings: list[Finding] = []
    text = path.read_text(encoding="utf-8", errors="replace")
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
    for i, raw in enumerate(lines, start=1):
        line = raw.strip()
        if not line or line.startswith("//") or line.startswith("#"):
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
                                        "→ (U+2192) in English template; use 'to' or '->' per patterns §2"))

        m = LINE_HEIGHT_LOOSE.search(raw)
        if m:
            findings.append(Finding(path, i, "line-height-too-loose",
                                    f"{m.group(0)} exceeds 1.55 ceiling"))

        for hex_match in HEX_ANY.finditer(raw):
            h = hex_match.group(0).lower()
            if h in COOL_GRAY_BLOCKLIST:
                findings.append(Finding(path, i, "cool-gray",
                                        f"{h} is a cool / neutral gray, use warm undertone"))
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


# ------------------------- entry -------------------------

def main(argv: list[str]) -> int:
    args = argv[1:]
    if not args:
        return build_all()
    if args[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    if args[0] == "--check":
        verbose = "-v" in args[1:] or "--verbose" in args[1:]
        css_result = check_all(verbose)
        sync_result = sync_check(verbose)
        return max(css_result, sync_result)
    if args[0] == "--sync":
        verbose = "-v" in args[1:] or "--verbose" in args[1:]
        return sync_check(verbose)
    if args[0] == "--verify":
        target = args[1] if len(args) > 1 and not args[1].startswith("-") else None
        return verify_all(target)
    if args[0] in ("--check-placeholders", "--verify-filled"):
        return check_placeholders(args[1:])
    return build_single(args[0])


if __name__ == "__main__":
    sys.exit(main(sys.argv))
