#!/usr/bin/env python3
"""kami build & check

Thin CLI shell. Implementation lives in:
  - render.py  (render_pdf, build_slides, PDF metadata)
  - lint.py    (scan_file, check_all, check_cross_template_consistency)
  - tokens.py  (sync_check)
  - site_facts.py (check_site_facts)
  - verify.py  (verify_all, show_fonts, font checks)
  - checks.py  (check_placeholders, check_markdown_residue, check_orphans, check_density, check_resume_balance, check_rhythm, check_card_fit, check_card_orphans)
  - content.py (check_content)
  - html_visibility.py (shared HTML/CSS evidence for content and residue checks)
  - visual.py  (check_visual)
  - deliver.py (deliver: every document gate in order, one verdict)
  - chart.py   (render_chart, check_charts: data spec to SVG and drift check)

Usage:
    python3 scripts/build.py --deliver filled.html [content.json]  # finish a document: all gates, one verdict
    python3 scripts/build.py                      # build all examples (HTML + diagrams + PPTX)
    python3 scripts/build.py resume               # build one template, print pages + fonts
    python3 scripts/build.py landing-page         # check one browser-only static template
    python3 scripts/build.py --check              # lint + token/theme + doc-snippet + public-site fact checks
    python3 scripts/build.py --check -v           # verbose (show each scanned file)
    python3 scripts/build.py --sync               # check CSS token drift across templates
    python3 scripts/build.py --verify             # build all + page count + font checks
    python3 scripts/build.py --verify resume-en   # single target full verification
    python3 scripts/build.py --check-placeholders path/to/doc.html
    python3 scripts/build.py --check-markdown path/to/doc.pdf
    python3 scripts/build.py --check-orphans      # scan example PDFs for orphan text
    python3 scripts/build.py --check-orphans path/to/doc.pdf
    python3 scripts/build.py --check-density       # warn on pages with >25% trailing whitespace
    python3 scripts/build.py --check-density path/to/doc.pdf
    python3 scripts/build.py --check-resume-balance path/to/resume.pdf
    python3 scripts/build.py --check-card-fit path/to/cards.pdf      # social cards: text under the footer or on the photo
    python3 scripts/build.py --check-card-orphans path/to/cards.pdf  # social cards: paragraphs ending on 1-3 characters
    python3 scripts/build.py --check-rhythm       # warn on monotonous slide sequences
    python3 scripts/build.py --check-rhythm slides slides-en
    python3 scripts/build.py --check-content content.json            # content IR schema validation
    python3 scripts/build.py --check-content content.json filled.html # + coverage into the document
    python3 scripts/build.py --check-visual path/to/doc.pdf          # page PNGs + perceptual checklist
    python3 scripts/build.py --check-fonts path/to/doc.pdf           # which family actually drew the CJK text
    python3 scripts/build.py --check-style path/to/filled.html       # template rules against a produced document
    python3 scripts/build.py --check-docs                            # lint the CSS snippets the reference docs teach from
    python3 scripts/build.py --doctor                                # installed render/check/font capabilities
    python3 scripts/build.py --chart spec.json -o chart.svg          # data chart from a JSON spec (bar/line/hbar/donut/candlestick/waterfall)
    python3 scripts/build.py --check-charts path/to/doc.html         # every generated chart still matches its embedded data
"""
from __future__ import annotations

import sys
from pathlib import Path

from chart import check_charts
from chart import main as chart_main
from checks import (
    check_card_fit,
    check_card_orphans,
    check_density,
    check_markdown_residue,
    check_orphans,
    check_placeholders,
    check_resume_balance,
    check_rhythm,
)
from content import check_content
from deliver import deliver
from lint import (
    check_all,
    check_cross_template_consistency,
    check_docs,
    check_off_palette,
    check_style,
    scan_file,
)
from math_render import MathRenderError
from optional_deps import MissingDepError, run_doctor
from render import build_slides, render_pdf
from shared import (
    DIAGRAMS,
    EXAMPLES,
    TEMPLATES,
    build_targets,
    diagram_targets,
    pptx_targets,
    screen_targets,
)
from site_facts import check_site_facts
from tokens import sync_check
from verify import check_fonts, show_fonts, verify_all
from visual import check_visual

# name -> (source, max_pages). max_pages=0 means no hard check.
# All four dicts derive from the shared registries (single source of truth).
HTML_TARGETS: dict[str, tuple[str, int]] = build_targets()
SCREEN_TARGETS: dict[str, str] = screen_targets()
PPTX_TARGETS: dict[str, str] = pptx_targets()
DIAGRAM_TARGETS: dict[str, str] = diagram_targets()


# ------------------------- build -------------------------

def build_html(name: str, source: str, max_pages: int,
               src_dir: Path = TEMPLATES) -> bool:
    src = src_dir / source
    if not src.exists():
        print(f"ERROR: {name}: source not found ({src})")
        return False

    try:
        n = render_pdf(src, EXAMPLES / f"{name}.pdf")
    except (MissingDepError, MathRenderError) as exc:
        print(f"ERROR: {exc}")
        return False
    except Exception as exc:  # WeasyPrint / pypdf / OS errors: report, keep the sweep going
        print(f"ERROR: {name}: render failed: {exc}")
        return False

    if max_pages and n > max_pages:
        print(f"ERROR: {name}: {n} pages (limit {max_pages})")
        return False
    print(f"OK: {name}: {n} pages")
    return True


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


# ------------------------- entry -------------------------

def _unexpected_arg(args: list[str], allowed: set[str] | None = None) -> str | None:
    for arg in args:
        if allowed is not None:
            if arg not in allowed:
                return arg
        elif arg.startswith("-"):
            return arg
    return None


def _error_unexpected(arg: str) -> int:
    print(f"ERROR: unexpected argument: {arg}")
    return 2


def main(argv: list[str]) -> int:
    args = argv[1:]
    if not args:
        return build_all()
    if args[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    if args[0] == "--check":
        unexpected = _unexpected_arg(args[1:], {"-v", "--verbose"})
        if unexpected:
            return _error_unexpected(unexpected)
        verbose = "-v" in args[1:] or "--verbose" in args[1:]
        css_result = check_all(verbose)
        sync_result = sync_check(verbose)
        cross_result = check_cross_template_consistency(verbose)
        palette_result = check_off_palette(verbose)
        docs_result = check_docs([])
        site_result = check_site_facts(verbose)
        chart_files = [str(p) for p in sorted(DIAGRAMS.glob("*.html")) if "data-kami-chart" in p.read_text(encoding="utf-8")]
        chart_result = check_charts(chart_files)
        return max(css_result, sync_result, cross_result, palette_result, docs_result, site_result,
                   chart_result)
    if args[0] == "--sync":
        unexpected = _unexpected_arg(args[1:], {"-v", "--verbose"})
        if unexpected:
            return _error_unexpected(unexpected)
        verbose = "-v" in args[1:] or "--verbose" in args[1:]
        return sync_check(verbose)
    if args[0] == "--verify":
        if len(args) > 2:
            return _error_unexpected(args[2])
        if len(args) == 2 and args[1].startswith("-"):
            return _error_unexpected(args[1])
        target = args[1] if len(args) > 1 else None
        return verify_all(target)
    if args[0] == "--doctor":
        if len(args) > 1:
            return _error_unexpected(args[1])
        return run_doctor()
    if args[0] == "--chart":
        return chart_main(args[1:])
    # Path-taking check subcommands share one guard + dispatch table.
    path_checks = {
        "--check-orphans": check_orphans,
        "--check-density": check_density,
        "--check-resume-balance": check_resume_balance,
        "--check-card-fit": check_card_fit,
        "--check-card-orphans": check_card_orphans,
        "--check-placeholders": check_placeholders,
        "--check-markdown": check_markdown_residue,
        "--check-content": check_content,
        "--check-visual": check_visual,
        "--check-fonts": check_fonts,
        "--check-style": check_style,
        "--check-docs": check_docs,
        "--check-charts": check_charts,
        "--deliver": deliver,
    }
    handler = path_checks.get(args[0])
    if handler is not None:
        unexpected = _unexpected_arg(args[1:])
        if unexpected:
            return _error_unexpected(unexpected)
        return handler(args[1:])
    if args[0] == "--check-rhythm":
        unexpected = _unexpected_arg(args[1:])
        if unexpected:
            return _error_unexpected(unexpected)
        slide_targets = [a for a in args[1:] if not a.startswith("-")]
        return check_rhythm(slide_targets)
    if args[0].startswith("-"):
        print(f"ERROR: unknown option: {args[0]}")
        return 2
    if len(args) > 1:
        return _error_unexpected(args[1])
    return build_single(args[0])


if __name__ == "__main__":
    sys.exit(main(sys.argv))
