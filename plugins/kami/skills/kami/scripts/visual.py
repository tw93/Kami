"""Perceptual verification: rasterize a rendered PDF for an eyeball pass.

Geometric checks (density, orphans, page count) cannot see a fallback glyph,
an arrow crossing a label, or a heading stranded at a page bottom. This module
closes that gap: it renders every PDF page to PNG and prints the review
checklist the agent must walk while viewing each image. The agent (or a
vision-capable host) is the judge; this script guarantees the evidence exists
and the criteria are fixed instead of recalled from memory.

Usage:
    python3 scripts/build.py --check-visual path/to/doc.pdf
"""
from __future__ import annotations

import math
import tempfile
from pathlib import Path

from optional_deps import MissingDepError, require_pymupdf
from shared import load_checks_thresholds, rel_to_root, resolve_input
from verify import check_fonts

# Distilled from references/design.md and references/production.md Part 4.
# Keep entries stable: hosts learn to walk this list page by page.
REVIEW_CHECKLIST = (
    "fonts: no fallback boxes or mixed families; CJK bold is a real weight, not synthetic",
    "tags and chips: solid backgrounds, no double rectangle or double ring artifacts",
    "figures: no overlapping labels, arrows never touch module edges, arrowheads visible",
    "page breaks: no heading stranded at a page bottom, no card or table split mid-body",
    "emphasis: brand color only on numbers or distinctive phrases, at most 2 per line",
    "density: body pages read 60-80% full (cover and last page exempt), no orphan trailing line",
    "wraps: no line one word from wrapping, no line wrapping early before filling its container",
    "alignment: columns share baselines, margins are even, nothing crowds the page edge",
    "tables: one neutral rule color, hairline dividers, and enough vertical padding for each row to breathe",
    "subtraction: no decorative ticks, short rules, or side accents; every visible rule separates data, regions, relationships, or state",
)

# Card sets are one point per fixed-size page: the print density and page-break
# lines measure the wrong thing there, so cards get their own fill line.
CARD_REVIEW_CHECKLIST = tuple(
    item for item in REVIEW_CHECKLIST if not item.startswith(("density:", "page breaks:"))
) + (
    "cards: one point or two to five items per card, similar weight across the set, each card "
    "mostly full (more of the author's text, not padding); split a crowded card, never shrink its type",
)

MIN_DPI = 36
MAX_DPI = 300
MAX_PAGES = 200
MAX_PAGE_PIXELS = 50_000_000


def visual_output_dir(pdf: Path) -> Path:
    return pdf.parent / f"{pdf.stem}-visual"


def _clear_page_images(target: Path) -> None:
    """Drop page PNGs from a previous run.

    A re-render with fewer pages must not leave stale page-NN.png files
    behind, or the reviewer walks pages that no longer exist.
    """
    for old in target.glob("page-*.png"):
        old.unlink()


def render_pages(pdf: Path, out_dir: Path | None = None, dpi: int | None = None) -> list[Path]:
    """Render every page of `pdf` to PNG; return the image paths."""
    fitz = require_pymupdf()
    if dpi is None:
        dpi = int(load_checks_thresholds().get("visual", {}).get("dpi", 110))
    if isinstance(dpi, bool) or not isinstance(dpi, int) or not MIN_DPI <= dpi <= MAX_DPI:
        raise ValueError(f"dpi must be an integer from {MIN_DPI} to {MAX_DPI}")
    target = out_dir or visual_output_dir(pdf)
    if target.is_symlink():
        raise ValueError(f"visual output directory must not be a symbolic link: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    with fitz.open(str(pdf)) as doc:
        if len(doc) == 0:
            raise ValueError("PDF has no pages")
        if len(doc) > MAX_PAGES:
            raise ValueError(f"PDF has {len(doc)} pages (limit {MAX_PAGES})")
        scale = dpi / 72
        for index, page in enumerate(doc, start=1):
            width = math.ceil(page.rect.width * scale)
            height = math.ceil(page.rect.height * scale)
            pixels = width * height
            if pixels > MAX_PAGE_PIXELS:
                raise ValueError(
                    f"PDF page {index} would render {width}x{height} pixels "
                    f"({pixels} pixels, limit {MAX_PAGE_PIXELS})"
                )
        # Render away from the final evidence directory. A corrupt later page
        # must not erase or partially replace screenshots from the last good run.
        with tempfile.TemporaryDirectory(dir=target.parent, prefix=f".{target.name}-") as raw_tmp:
            tmp = Path(raw_tmp)
            staged: list[Path] = []
            for index, page in enumerate(doc, start=1):
                out = tmp / f"page-{index:02d}.png"
                page.get_pixmap(dpi=dpi).save(str(out))
                staged.append(out)

            target.mkdir(parents=True, exist_ok=True)
            _clear_page_images(target)
            pages: list[Path] = []
            for page in staged:
                final = target / page.name
                page.replace(final)
                pages.append(final)
            return pages


def check_visual(paths: list[str]) -> int:
    """CLI: --check-visual doc.pdf [more.pdf ...]

    Exports page images and prints the perceptual checklist. Passing this
    check means the images exist; the review itself is the caller's job:
    view every page image against the checklist before shipping.
    """
    files = [p for p in paths if not p.startswith("-")]
    if not files:
        print("ERROR: usage: --check-visual path/to/doc.pdf [more.pdf ...]")
        return 2

    failures = 0
    rendered: list[tuple[Path, list[Path]]] = []
    for raw in files:
        pdf = resolve_input(raw)
        rel = rel_to_root(pdf)
        if not pdf.exists():
            print(f"ERROR: {raw}: file not found")
            failures += 1
            continue
        try:
            pages = render_pages(pdf)
        except MissingDepError as exc:
            print(f"ERROR: {exc}")
            return 2
        except Exception as exc:
            print(f"ERROR: {rel}: could not rasterize: {exc}")
            failures += 1
            continue
        rendered.append((pdf, pages))
        print(f"OK: {rel}: {len(pages)} page image(s) -> {rel_to_root(visual_output_dir(pdf))}")
        for page in pages:
            print(f"  {rel_to_root(page)}")

    if rendered:
        # The first checklist entry ("no fallback boxes or mixed families") is the
        # one an eyeball pass fails at: a missing CJK serif substitutes a sans that
        # reads perfectly well, so nothing looks broken enough to catch. Settle it
        # mechanically here rather than leaving it to the reviewer's judgement.
        print("Font check (deterministic, settles checklist item 1):")
        if check_fonts([str(pdf) for pdf, _ in rendered]) != 0:
            failures += 1
        print("Review checklist (view every page image before shipping):")
        for item in REVIEW_CHECKLIST:
            print(f"  - {item}")

    return 0 if failures == 0 else 1
