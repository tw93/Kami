#!/usr/bin/env python3
"""kami build & check

Thin CLI shell. Implementation lives in:
  - lint.py    (scan_file, check_all, check_cross_template_consistency)
  - tokens.py  (sync_check)
  - verify.py  (verify_target, verify_all, show_fonts, font checks)
  - checks.py  (check_placeholders, check_orphans, check_density, check_rhythm)

Usage:
    python3 scripts/build.py                      # build all examples (HTML + diagrams + PPTX)
    python3 scripts/build.py resume               # build one template, print pages + fonts
    python3 scripts/build.py landing-page         # check one browser-only static template
    python3 scripts/build.py --check              # scan templates for CSS rule violations
    python3 scripts/build.py --check -v           # verbose (show each scanned file)
    python3 scripts/build.py --sync               # check CSS token drift across templates
    python3 scripts/build.py --verify             # build all + page count + font checks
    python3 scripts/build.py --verify resume-en   # single target full verification
    python3 scripts/build.py --check-placeholders path/to/doc.html
    python3 scripts/build.py --check-orphans      # scan example PDFs for orphan text
    python3 scripts/build.py --check-orphans path/to/doc.pdf
    python3 scripts/build.py --check-density       # warn on pages with >25% trailing whitespace
    python3 scripts/build.py --check-density path/to/doc.pdf
    python3 scripts/build.py --check-rhythm       # warn on monotonous slide sequences
    python3 scripts/build.py --check-rhythm slides slides-en
"""
from __future__ import annotations

import functools
import os
import subprocess
import sys
from pathlib import Path

from highlight import highlight_code_blocks
from optional_deps import (
    MissingDepError,
    require_pypdf_reader,
    require_pypdf_writer,
    require_weasyprint_html,
)
from shared import (
    DIAGRAMS,
    EXAMPLES,
    TEMPLATES,
    build_targets,
    screen_targets,
)

# Implementation modules (also re-exported for tests / external callers).
from checks import (  # noqa: F401  re-exported for test_build.py
    _BG_B,
    _BG_G,
    _BG_R,
    _last_content_y,
    _parse_slide_sequence,
    _scan_density,
    check_density,
    check_orphans,
    check_placeholders,
    check_rhythm,
)
from lint import (  # noqa: F401  re-exported for test_build.py
    _extract_root_vars,
    _pair_names,
    check_all,
    check_cross_template_consistency,
    scan_file,
)
from tokens import sync_check
from verify import (
    show_fonts,
    verify_all,
    verify_target as _verify_target_impl,
)

# name -> (source, max_pages). max_pages=0 means no hard check.
# Sourced from shared.HTML_TEMPLATES so build.py and stabilize.py never drift.
HTML_TARGETS: dict[str, tuple[str, int]] = build_targets()
SCREEN_TARGETS: dict[str, str] = screen_targets()
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
    "diagram-candlestick":   "candlestick.html",
    "diagram-waterfall":     "waterfall.html",
}


# ------------------------- build helpers -------------------------

@functools.lru_cache(maxsize=1)
def infer_author() -> str:
    """Infer author name from git config or environment.

    Priority:
    1. git config user.name
    2. KAMI_AUTHOR env var
    3. fallback to "Kami"

    Cached so a full build doesn't shell out for every PDF target.
    """
    try:
        result = subprocess.run(
            ["git", "config", "user.name"],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except FileNotFoundError:
        pass

    if env_author := os.environ.get("KAMI_AUTHOR"):
        return env_author

    return "Kami"


def set_pdf_metadata(pdf_path: Path, author: str | None = None) -> None:
    """Set PDF metadata using pypdf, only if placeholders are still present."""
    try:
        PdfReader = require_pypdf_reader()
        PdfWriter = require_pypdf_writer()
    except MissingDepError:
        return

    if not pdf_path.exists():
        return

    reader = PdfReader(str(pdf_path))

    existing = reader.metadata or {}
    needs_update = False
    metadata = dict(existing)

    if author and existing.get("/Author"):
        author_value = str(existing["/Author"])
        if "{{" in author_value and "}}" in author_value:
            metadata["/Author"] = author
            needs_update = True

    if metadata.get("/Producer") != "Kami":
        metadata["/Producer"] = "Kami"
        needs_update = True
    if metadata.get("/Creator") != "Kami":
        metadata["/Creator"] = "Kami"
        needs_update = True

    if not needs_update:
        return

    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)

    writer.add_metadata(metadata)

    with open(pdf_path, "wb") as f:
        writer.write(f)


# ------------------------- build -------------------------

def build_html(name: str, source: str, max_pages: int,
               src_dir: Path = TEMPLATES) -> bool:
    try:
        HTML = require_weasyprint_html()
        PdfReader = require_pypdf_reader()
    except MissingDepError as exc:
        print(f"ERROR: {exc}")
        return False

    src = src_dir / source
    if not src.exists():
        print(f"ERROR: {name}: source not found ({src})")
        return False

    EXAMPLES.mkdir(parents=True, exist_ok=True)
    out = EXAMPLES / f"{name}.pdf"

    html_text = src.read_text(encoding="utf-8")
    html_text = highlight_code_blocks(html_text)
    HTML(string=html_text, base_url=str(src.parent)).write_pdf(str(out))

    set_pdf_metadata(out, author=infer_author())

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
    # Pass --out so the slides script writes directly to the target path. Older
    # slides.py defaults to 'output.pptx' in cwd; new copies accept --out.
    result = subprocess.run(
        [sys.executable, str(src), "--out", str(out)],
        cwd=str(src.parent),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"ERROR: {name}: {result.stderr.strip() or 'script failed'}")
        return False
    if out.exists():
        print(f"OK: {name}: generated {out.name}")
        return True
    print(f"ERROR: {name}: {out.name} not produced")
    return False


def build_screen_template(name: str, source: str) -> bool:
    src = TEMPLATES / source
    if not src.exists():
        print(f"ERROR: {name}: source not found ({src})")
        return False

    findings = scan_file(src)
    if findings:
        print(f"ERROR: {name}: {len(findings)} template violation(s)")
        return False

    print(f"OK: {name}: static HTML template")
    return True


def build_all() -> int:
    failures = 0
    for name, (source, max_pages) in HTML_TARGETS.items():
        if not build_html(name, source, max_pages):
            failures += 1
    for name, source in SCREEN_TARGETS.items():
        if not build_screen_template(name, source):
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
    if name in SCREEN_TARGETS:
        ok = build_screen_template(name, SCREEN_TARGETS[name])
        return 0 if ok else 1
    if name in DIAGRAM_TARGETS:
        source = DIAGRAM_TARGETS[name]
        ok = build_html(name, source, 0, src_dir=DIAGRAMS)
        return 0 if ok else 1
    if name in PPTX_TARGETS:
        return 0 if build_slides(name) else 1
    known = list(HTML_TARGETS) + list(SCREEN_TARGETS) + list(DIAGRAM_TARGETS) + list(PPTX_TARGETS)
    print(f"ERROR: unknown target: {name}. Known: {', '.join(known)}")
    return 2


# ------------------------- verify glue -------------------------

def verify_slides_target(name: str) -> list[str]:
    return [] if build_slides(name) else ["slides build failed"]


def verify_target(name: str, source: str, max_pages: int, src_dir: Path) -> list[str]:
    """Compat wrapper that injects build.py's metadata helpers."""
    return _verify_target_impl(
        name, source, max_pages, src_dir,
        infer_author_fn=infer_author,
        set_pdf_metadata_fn=set_pdf_metadata,
    )


def _verify_all(target: str | None) -> int:
    return verify_all(
        target,
        html_targets=HTML_TARGETS,
        screen_targets=SCREEN_TARGETS,
        diagram_targets=DIAGRAM_TARGETS,
        pptx_targets=PPTX_TARGETS,
        verify_slides_fn=verify_slides_target,
        scan_file_fn=scan_file,
        scan_density_fn=_scan_density,
        infer_author_fn=infer_author,
        set_pdf_metadata_fn=set_pdf_metadata,
    )


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
        cross_result = check_cross_template_consistency(verbose)
        return max(css_result, sync_result, cross_result)
    if args[0] == "--sync":
        verbose = "-v" in args[1:] or "--verbose" in args[1:]
        return sync_check(verbose)
    if args[0] == "--verify":
        target = args[1] if len(args) > 1 and not args[1].startswith("-") else None
        return _verify_all(target)
    if args[0] == "--check-orphans":
        return check_orphans(args[1:])
    if args[0] == "--check-density":
        return check_density(args[1:])
    if args[0] in ("--check-placeholders", "--verify-filled"):
        return check_placeholders(args[1:])
    if args[0] == "--check-rhythm":
        slide_targets = [a for a in args[1:] if not a.startswith("-")]
        return check_rhythm(slide_targets, PPTX_TARGETS, TEMPLATES)
    return build_single(args[0])


if __name__ == "__main__":
    sys.exit(main(sys.argv))
