"""PDF-side and content-shape checks for kami documents.

Splits out from build.py:
  - check_placeholders: scan filled HTML for unreplaced `{{...}}` tokens.
  - check_orphans:      scan rendered PDFs for short trailing lines (typographic orphans).
  - check_density:      scan rendered PDFs for pages with too much trailing whitespace.
  - check_resume_balance: scan resume PDFs for exact two-page balance.
  - check_rhythm:       scan slides Python source for monotonous deck sequences.
  - check_card_fit:     scan social-card PDFs for text running into the footer or photo.
  - check_card_orphans: scan social-card PDFs for paragraphs ending on 1-3 characters.

Density scanning uses a parchment-aware pixel sweep. The hot path is
vectorized with NumPy when available and falls back to a pure-Python loop.
Thresholds and DPI live in `references/checks_thresholds.json`.
"""
from __future__ import annotations

import re
from pathlib import Path

from html_visibility import visible_html_text
from optional_deps import MissingDepError, require_pymupdf, require_pypdf_reader
from shared import (
    PARCHMENT_RGB,
    TEMPLATES,
    default_example_pdfs,
    load_checks_thresholds,
    pptx_targets,
    rel_to_root,
    resolve_input,
)

PLACEHOLDER = re.compile(r"\{\{[^}]+\}\}")
# The author meta tag may keep its placeholder: render.py stamps the PDF /Author
# from git config or KAMI_AUTHOR exactly when it is still unfilled (SKILL.md
# metadata table), so leaving it is the documented path, not a miss.
AUTHOR_META_PLACEHOLDER = re.compile(
    r"""<meta\s+name=["']author["']\s+content=["']\{\{[^}]+\}\}["']\s*/?>""", re.I)
MARKDOWN_THEMATIC_BREAK = re.compile(r"^\s*[-*_]{3,}\s*$")
MARKDOWN_RESIDUE_MARKERS = (
    ("markdown thematic break", MARKDOWN_THEMATIC_BREAK),
    ("unconverted bold marker", re.compile(r"\*\*")),
    ("unconverted inline-code marker", re.compile(r"`")),
    # Em dash is banned in every deliverable (writing.md, anti-patterns #28).
    # It keeps leaking past the prose-level rule, so it is a machine gate here.
    ("em dash (banned punctuation)", re.compile("\u2014")),
)

# Parchment background RGB for pixel comparison (sourced from shared.PARCHMENT_RGB).
_BG_R, _BG_G, _BG_B = PARCHMENT_RGB
_BG_TOLERANCE = 10


def check_placeholders(paths: list[str]) -> int:
    if not paths:
        print("ERROR: provide at least one HTML file to scan")
        return 2

    failures = 0
    for raw in paths:
        path = resolve_input(raw)
        if not path.exists():
            print(f"ERROR: {raw}: file not found")
            failures += 1
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        hits = list(dict.fromkeys(PLACEHOLDER.findall(AUTHOR_META_PLACEHOLDER.sub("", text))))
        rel = rel_to_root(path)
        if hits:
            print(f"ERROR: {rel}: unfilled placeholder(s): {', '.join(hits)}")
            failures += 1
        else:
            print(f"OK: {rel}: no placeholders")

    return 0 if failures == 0 else 1


# ---------- markdown residue check ----------

def _markdown_residue_issues(text: str, *, page: int | None = None) -> list[str]:
    issues: list[str] = []
    for line_no, line in enumerate(text.splitlines(), start=1):
        for label, pattern in MARKDOWN_RESIDUE_MARKERS:
            if pattern.search(line):
                where = f"p{page}" if page is not None else f"line {line_no}"
                sample = " ".join(line.strip().split())[:80]
                issues.append(f"{where}: {label}: {sample!r}")
    return issues


def _markdown_text_chunks(path: Path) -> tuple[list[tuple[int | None, str]], str | None]:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        try:
            PdfReader = require_pypdf_reader()
        except MissingDepError as exc:
            return [], str(exc)
        try:
            reader = PdfReader(str(path))
        except Exception as exc:
            return [], f"could not read PDF text: {exc}"
        if not reader.pages:
            return [], "PDF has no pages"

        def page_text(page) -> str:
            parts: list[str] = []

            def visit_text(text, _cm, _tm, font_dict, _font_size) -> None:
                base_font = str((font_dict or {}).get("/BaseFont", "")).casefold()
                if any(
                    marker in base_font
                    for marker in ("mono", "courier", "consolas", "menlo")
                ):
                    return
                parts.append(text)

            page.extract_text(visitor_text=visit_text)
            return "".join(parts)

        return [
            (index, page_text(page))
            for index, page in enumerate(reader.pages, start=1)
        ], None

    raw = path.read_text(encoding="utf-8", errors="replace")
    if suffix in {".html", ".htm"}:
        return [(None, visible_html_text(raw, residue_mode=True))], None
    return [(None, raw)], None


def check_markdown_residue(paths: list[str]) -> int:
    """Scan filled HTML/PDF outputs for visible raw Markdown markers.

    This catches common hand-conversion misses such as literal `---`, `**bold**`,
    and inline-code backticks leaking into the final PDF.
    """
    if not paths:
        paths = default_example_pdfs()
        if not paths:
            print("ERROR: no files to scan")
            return 2

    failures = 0
    scanned = 0
    for raw in paths:
        path = resolve_input(raw)
        rel = rel_to_root(path)
        if not path.exists():
            print(f"ERROR: {raw}: file not found")
            failures += 1
            continue

        chunks, error = _markdown_text_chunks(path)
        if error:
            print(f"ERROR: {rel}: {error}")
            failures += 1
            continue

        scanned += 1
        issues: list[str] = []
        for page, text in chunks:
            issues.extend(_markdown_residue_issues(text, page=page))
        if issues:
            failures += 1
            print(f"ERROR: {rel}: markdown residue found")
            for issue in issues:
                print(f"  {issue}")
        else:
            print(f"OK: {rel}: no markdown residue")

    if scanned == 0:
        print("ERROR: no files scanned")
        return 2
    return 0 if failures == 0 else 1


# ---------- orphan check ----------

def _orphan_last_line(text: str, max_words: int, max_chars: int) -> str | None:
    """Return a block's last line if it is an orphan, else None.

    A block orphans when it has 2+ lines and the trailing line is short by
    both word count (<= max_words) and length (< max_chars). Pure so the
    predicate is unit-testable without a rendered PDF.
    """
    lines = text.strip().splitlines()
    if len(lines) < 2:
        return None
    last = lines[-1].strip()
    if len(last.split()) <= max_words and len(last) < max_chars:
        return last
    return None


def check_orphans(paths: list[str]) -> int:
    """Scan PDF for text blocks whose last line has <= max_words and < max_chars."""
    try:
        fitz = require_pymupdf()
    except MissingDepError as exc:
        print(f"ERROR: {exc}")
        return 2

    if not paths:
        paths = default_example_pdfs()
        if not paths:
            print("ERROR: no PDF files to scan")
            return 2

    orphan_cfg = load_checks_thresholds()["orphan"]
    max_words = int(orphan_cfg["max_words"])
    max_chars = int(orphan_cfg["max_chars"])

    total = 0
    missing = 0
    scanned = 0
    for raw in paths:
        path = resolve_input(raw)
        if not path.exists():
            print(f"ERROR: {raw}: not found")
            missing += 1
            continue
        try:
            doc = fitz.open(str(path))
        except Exception as exc:
            print(f"ERROR: {raw}: could not read PDF: {exc}")
            missing += 1
            continue
        if len(doc) == 0:
            print(f"ERROR: {raw}: PDF has no pages")
            doc.close()
            missing += 1
            continue
        scanned += 1
        rel = rel_to_root(path)
        for page_num in range(len(doc)):
            page = doc[page_num]
            blocks = page.get_text("blocks")
            for bx0, by0, bx1, by1, text, block_no, block_type in blocks:
                if block_type != 0:  # text blocks only
                    continue
                last = _orphan_last_line(text, max_words, max_chars)
                if last is not None:
                    total += 1
                    print(f"  {rel} p{page_num + 1}: orphan: \"{last}\" ({len(last.split())} word(s), {len(last)} chars)")
        doc.close()

    if scanned == 0:
        print(f"ERROR: no PDFs scanned ({missing} missing)")
        return 2

    if total == 0 and missing == 0:
        print(f"OK: no orphans found across {scanned} PDF(s)")
        return 0

    if total:
        print(f"\n{total} orphan(s) found across {scanned} PDF(s)")
    if missing:
        print(f"{missing} input(s) missing")
    return 1


# ---------- density check ----------

def _last_content_y(samples: bytes, w: int, h: int, stride: int, n: int) -> int:
    """Return the highest y row index that contains non-parchment content.

    Uses numpy when available (vectorized scan, ~50-100x faster on multi-page
    PDFs); falls back to a pure Python loop otherwise. Both paths sample every
    fourth column for parity, so the result is identical.
    """
    try:
        import numpy as np
    except ImportError:
        last_y = 0
        for y in range(h - 1, -1, -1):
            row_start = y * stride
            is_bg = True
            for x in range(0, w, 4):
                offset = row_start + x * n
                if (abs(samples[offset] - _BG_R) > _BG_TOLERANCE
                        or abs(samples[offset + 1] - _BG_G) > _BG_TOLERANCE
                        or abs(samples[offset + 2] - _BG_B) > _BG_TOLERANCE):
                    is_bg = False
                    break
            if not is_bg:
                last_y = y
                break
        return last_y

    arr = np.frombuffer(samples, dtype=np.uint8).reshape((h, stride))
    pixels = arr[:, : w * n].reshape((h, w, n))
    rgb = pixels[:, ::4, :3].astype(np.int16)
    bg = np.array([_BG_R, _BG_G, _BG_B], dtype=np.int16)
    row_is_bg = (np.abs(rgb - bg).max(axis=2) <= _BG_TOLERANCE).all(axis=1)
    non_bg = np.where(~row_is_bg)[0]
    return int(non_bg[-1]) if non_bg.size else 0


def _density_bucket(empty: float, warn_pct: float, sparse_pct: float) -> str:
    """Categorize a page by its trailing-whitespace fraction.

    Pure so `scan_density` and its tests share one decision. A test that
    reimplements these comparisons would stay green if the real operators
    drifted (`>` to `>=`, or warn/sparse swapped); calling this keeps the
    assertion anchored to production logic.
    """
    if empty > sparse_pct:
        return "SPARSE"
    if empty > warn_pct:
        return "WARN"
    return "OK"


def scan_density(paths: list[str], scan_single_page: bool = False) -> tuple[int, int, int, int] | None:
    """Scan PDFs and print SPARSE/WARN lines.

    Returns (sparse, warn, missing, scanned), or None if PyMuPDF is missing.
    Thresholds (warn_pct, sparse_pct, dpi) come from
    references/checks_thresholds.json. Public: verify.py runs the same scan
    as its advisory pass.

    The last page of a multi-page PDF is judged only against `last_page_pct`.

    Page 1 is skipped as a cover exemption, which left a one-page document with
    no scanned page at all: the single-page templates (one-pager, letter) were
    silently exempt from the only layout gate that reads a rendered page. When
    `scan_single_page` is set, a one-page PDF has that page scanned instead.
    It stays opt-in because the no-arg repo sweep reads example PDFs built from
    unfilled placeholder skeletons, which are sparse by construction and would
    turn the sweep permanently red without describing a real defect.
    """
    try:
        fitz = require_pymupdf()
    except MissingDepError as exc:
        print(f"ERROR: {exc}")
        return None

    density_cfg = load_checks_thresholds()["density"]
    warn_pct = float(density_cfg["warn_pct"])
    sparse_pct = float(density_cfg["sparse_pct"])
    # The last page of a multi-page document may close short (writing.md «Page
    # density»: the last body page runs 40-60% full), so it is
    # only reported once it passes this looser ceiling.
    last_page_pct = float(density_cfg.get("last_page_pct", 0.60))
    dpi = int(density_cfg["dpi"])

    sparse = 0
    warn = 0
    missing = 0
    scanned = 0
    for raw in paths:
        path = resolve_input(raw)
        if not path.exists():
            print(f"ERROR: {raw}: not found")
            missing += 1
            continue
        try:
            doc = fitz.open(str(path))
        except Exception as exc:
            print(f"ERROR: {raw}: could not read PDF: {exc}")
            missing += 1
            continue
        if len(doc) == 0:
            print(f"ERROR: {raw}: PDF has no pages")
            doc.close()
            missing += 1
            continue
        scanned += 1
        rel = rel_to_root(path)
        single_page = len(doc) == 1
        for page_num in range(len(doc)):
            if page_num == 0 and not (single_page and scan_single_page):
                continue
            page = doc[page_num]
            pix = page.get_pixmap(dpi=dpi)
            w, h = pix.width, pix.height
            if h == 0:
                continue
            last_content_y = _last_content_y(pix.samples, w, h, pix.stride, pix.n)

            empty = (h - last_content_y) / h
            if not single_page and page_num == len(doc) - 1:
                bucket = "SPARSE" if empty > last_page_pct else "OK"
            else:
                bucket = _density_bucket(empty, warn_pct, sparse_pct)
            if bucket == "SPARSE":
                print(f"  SPARSE: {rel} p{page_num + 1}: {empty:.0%} trailing whitespace")
                sparse += 1
            elif bucket == "WARN":
                print(f"  WARN: {rel} p{page_num + 1}: {empty:.0%} trailing whitespace")
                warn += 1
        doc.close()
    return sparse, warn, missing, scanned


def check_density(paths: list[str]) -> int:
    """Scan PDF pages for sparse content (large trailing whitespace from
    break-inside:avoid pushing content to the next page)."""
    explicit = bool(paths)
    if not paths:
        paths = default_example_pdfs()
        if not paths:
            print("ERROR: no PDF files to scan")
            return 2

    result = scan_density(paths, scan_single_page=explicit)
    if result is None:
        return 2
    sparse, warn, missing, scanned = result

    if scanned == 0:
        print(f"ERROR: no PDFs scanned ({missing} missing)")
        return 2

    total = sparse + warn
    if total == 0 and missing == 0:
        print(f"OK: no density issues across {scanned} PDF(s)")
        return 0

    if total:
        print(f"\n{total} density warning(s) across {scanned} PDF(s)")
    if missing:
        print(f"{missing} input(s) missing")
    return 1


# ---------- resume balance check ----------

def _resume_balance_issues(
    fills: list[float],
    page_count: int,
    min_fill: float,
    max_fill: float,
    max_gap: float,
) -> list[str]:
    """Return human-readable resume balance failures for unit tests and CLI."""
    issues: list[str] = []
    if page_count != 2:
        issues.append(f"{page_count} pages (expected 2)")

    for index, fill in enumerate(fills[:2], start=1):
        if fill < min_fill:
            issues.append(f"p{index} fill {fill:.0%} below {min_fill:.0%}")
        elif fill > max_fill:
            issues.append(f"p{index} fill {fill:.0%} above {max_fill:.0%}")

    if len(fills) >= 2:
        gap = abs(fills[0] - fills[1])
        if gap > max_gap:
            issues.append(f"page fill gap {gap:.0%} above {max_gap:.0%}")

    return issues


def resume_thin_source(path: Path) -> str | None:
    """Explain a balance shortfall no layout can close, else None.

    Two pages that each stay under the ceiling but together hold less than two
    floors' worth of ink are short of material, not badly laid out: moving a
    break or loosening type only trades one sparse page for another. The
    delivery gate reports that as a data gap instead of a layout error.
    """
    cfg = load_checks_thresholds()["resume_balance"]
    min_fill, max_fill = float(cfg["min_fill_pct"]), float(cfg["max_fill_pct"])
    result = _resume_page_fills(path, int(cfg["dpi"]))
    if result is None:
        return None
    fills, page_count = result
    if page_count != 2 or len(fills) < 2 or any(f > max_fill for f in fills[:2]):
        return None
    total = fills[0] + fills[1]
    if total >= 2 * min_fill:
        return None
    return (f"{fills[0]:.0%} / {fills[1]:.0%}, {total:.0%} in total against the "
            f"{2 * min_fill:.0%} two balanced pages need: the source is too thin, so list the "
            "missing material as [DATA NEEDED] gaps (resume-writing.md «Thin source»)")


def _resume_page_fills(path: Path, dpi: int) -> tuple[list[float], int] | None:
    try:
        fitz = require_pymupdf()
    except MissingDepError as exc:
        print(f"ERROR: {exc}")
        return None

    try:
        doc = fitz.open(str(path))
    except Exception as exc:
        print(f"ERROR: {path}: could not read PDF: {exc}")
        return None
    fills: list[float] = []
    for page in doc:
        pix = page.get_pixmap(dpi=dpi)
        if pix.height == 0:
            fills.append(0.0)
            continue
        last_content_y = _last_content_y(pix.samples, pix.width, pix.height, pix.stride, pix.n)
        fills.append((last_content_y + 1) / pix.height)
    page_count = len(doc)
    doc.close()
    return fills, page_count


def check_resume_balance(paths: list[str]) -> int:
    """Require resume PDFs to be exactly 2 pages with balanced content fill."""
    if not paths:
        print("ERROR: provide at least one filled resume PDF to scan")
        return 2

    # Resolve the dependency once up front so a missing PyMuPDF stays a
    # tooling error (exit 2) while a single unreadable PDF inside the loop
    # tallies as missing and lets the remaining files still get scanned.
    try:
        require_pymupdf()
    except MissingDepError as exc:
        print(f"ERROR: {exc}")
        return 2

    cfg = load_checks_thresholds()["resume_balance"]
    min_fill = float(cfg["min_fill_pct"])
    max_fill = float(cfg["max_fill_pct"])
    max_gap = float(cfg["max_gap_pct"])
    dpi = int(cfg["dpi"])

    failures = 0
    missing = 0
    scanned = 0
    for raw in paths:
        path = resolve_input(raw)
        if not path.exists():
            print(f"ERROR: {raw}: not found")
            missing += 1
            continue

        result = _resume_page_fills(path, dpi)
        if result is None:
            missing += 1
            continue

        fills, page_count = result
        scanned += 1
        rel = rel_to_root(path)
        fill_text = " / ".join(f"{fill:.0%}" for fill in fills)
        issues = _resume_balance_issues(fills, page_count, min_fill, max_fill, max_gap)
        if issues:
            failures += 1
            print(f"ERROR: {rel}: {fill_text} ({'; '.join(issues)})")
        else:
            gap = abs(fills[0] - fills[1])
            print(f"OK: {rel}: 2 pages, fill {fill_text}, gap {gap:.0%}")

    if scanned == 0:
        print(f"ERROR: no PDFs scanned ({missing} missing)")
        return 2
    if missing:
        print(f"{missing} input(s) missing")
    return 0 if failures == 0 and missing == 0 else 1


# ---------- rhythm check ----------

# Layout functions that count as "divider" slides (break monotony).
_DIVIDER_FUNCS = {"chapter_slide"}
# Layout functions that count as "density variation" slides.
_DENSITY_VARIATION_FUNCS = {"quote_slide", "metrics_slide"}
# Layout function call pattern in slides.py source.
_SLIDE_CALL = re.compile(r"^\s*(\w+_slide)\s*\(")


def _parse_slide_sequence(src: Path) -> list[str]:
    """Return the ordered list of slide-function names called in main()."""
    text = src.read_text(encoding="utf-8", errors="replace")
    in_main = False
    sequence: list[str] = []
    for line in text.splitlines():
        if re.match(r"^def main\s*\(", line):
            in_main = True
            continue
        if in_main and re.match(r"^def \w", line):
            break
        if in_main:
            m = _SLIDE_CALL.match(line)
            if m:
                sequence.append(m.group(1))
    return sequence


def _rhythm_issues(seq: list[str], max_content_run: int, divider_min_deck_size: int) -> list[str]:
    """Return the rhythm warnings for one parsed slide sequence.

    Pure so the three monotony rules are unit-testable without rendering a
    deck, matching the `_resume_balance_issues` seam.
    """
    issues: list[str] = []

    # Rule 1: no run of more than `max_content_run` consecutive content_slides.
    run = 0
    max_run = 0
    for fn in seq:
        if fn == "content_slide":
            run += 1
            max_run = max(max_run, run)
        else:
            run = 0
    if max_run > max_content_run:
        issues.append(f"longest content_slide run is {max_run} (limit {max_content_run})")

    # Rule 2: large decks need at least one chapter_slide divider.
    if len(seq) >= divider_min_deck_size and not any(fn in _DIVIDER_FUNCS for fn in seq):
        issues.append(f"{len(seq)} slides with no chapter_slide divider")

    # Rule 3: deck must contain at least one density-variation slide.
    if not any(fn in _DENSITY_VARIATION_FUNCS for fn in seq):
        issues.append("no quote_slide or metrics_slide for density variation")

    return issues


def check_rhythm(targets: list[str]) -> int:
    """Scan slide templates for monotony: too many consecutive content_slides,
    missing dividers, and missing density variation.

    Targets come from the shared PPTX registry; thresholds from
    references/checks_thresholds.json.
    """
    slide_sources = pptx_targets()
    names = targets if targets else list(slide_sources)
    failures = 0
    rhythm_cfg = load_checks_thresholds()["rhythm"]
    max_content_run = int(rhythm_cfg["max_content_run"])
    divider_min_deck_size = int(rhythm_cfg["divider_min_deck_size"])

    for name in names:
        source = slide_sources.get(name)
        if source is None:
            print(f"ERROR: {name}: not a known slides target")
            failures += 1
            continue
        src = TEMPLATES / source
        if not src.exists():
            print(f"ERROR: {name}: source not found ({src})")
            failures += 1
            continue

        seq = _parse_slide_sequence(src)
        if not seq:
            print(f"ERROR: {name}: no slide calls found in main() (deck unparseable)")
            failures += 1
            continue

        issues = _rhythm_issues(seq, max_content_run, divider_min_deck_size)

        if issues:
            # These fail the run (exit 1), so label them ERROR; WARN is
            # reserved for advisory output that does not gate the build.
            for issue in issues:
                print(f"ERROR: {name}: {issue}")
            failures += 1
        else:
            content_run = 0
            max_run = 0
            for fn in seq:
                content_run = content_run + 1 if fn == "content_slide" else 0
                max_run = max(max_run, content_run)
            print(f"OK: {name}: rhythm ok ({len(seq)} slides, max run {max_run})")

    return 0 if failures == 0 else 1


# ---------- social cards ----------
#
# A social card is one fixed 1242x1660 page. Content that outgrows it either
# runs under the footer or spills onto an extra page (which --deliver also
# counts against the cards); nothing else in the pipeline notices either.
# These read the PDF geometry: the footer rule is the wide filled box near the
# bottom of the page (WeasyPrint draws the border-top as a filled rectangle),
# the cover photo is the image block. The generic orphan gate misses CJK
# paragraphs split into one text block per line and flags a two-line cover
# headline, so card sets get their own paragraph-aware check.

_PX = 0.75  # PDF points per CSS px


def _card_lines(page) -> list[tuple[float, float, float, float, str, float]]:
    """Every text line on the page as (x0, y0, y1, size, text, x1), in px, top to bottom."""
    lines = []
    for block in page.get_text("dict")["blocks"]:
        for line in block.get("lines", []):
            spans = [s for s in line["spans"] if s["text"].strip()]
            if not spans:
                continue
            x0, y0, x1, y1 = line["bbox"]
            lines.append((x0 / _PX, y0 / _PX, y1 / _PX, round(spans[-1]["size"] / _PX),
                          "".join(s["text"] for s in spans).strip(), x1 / _PX))
    return sorted(lines, key=lambda ln: (ln[1], ln[0]))


def _card_images(page) -> list[tuple[float, float]]:
    """Top and bottom (px) of every image block on the page."""
    return [(b["bbox"][1] / _PX, b["bbox"][3] / _PX)
            for b in page.get_text("dict")["blocks"] if b.get("type") == 1]


def _card_footer_y(page) -> float | None:
    """Top of the footer rule in px, or None on a card without a footer (the cover)."""
    width, height = page.rect.width, page.rect.height
    tops = [d["rect"].y0 for d in page.get_drawings()
            if d.get("fill") is not None
            and d["rect"].width > width * 0.6
            and d["rect"].y0 > height * 0.7
            and d["rect"].height < height * 0.2]
    return min(tops) / _PX if tops else None


def card_fit_issues(page, gap_px: int, photo_gap_px: int, *, cover: bool = False) -> list[str]:
    """`cover` is the first card, which may be a text-only cover without a footer."""
    lines = _card_lines(page)
    footer = _card_footer_y(page)
    issues: list[str] = []
    if footer is not None:
        above = [ln for ln in lines if ln[1] < footer]
        below = [ln for ln in lines if ln[1] >= footer]
        foot_size = min((ln[3] for ln in below), default=0)
        runover = [ln for ln in below if ln[3] > foot_size]
        if runover:
            issues.append(f"text runs under the footer: \"{runover[0][4][:16]}\"")
        bottoms = [ln[2] for ln in above] + [bottom for top, bottom in _card_images(page) if top < footer]
        if bottoms and not runover:
            gap = footer - max(bottoms)
            if gap < gap_px:
                issues.append(f"{gap:.0f}px between the content and the footer, needs {gap_px}px")
    images = _card_images(page)
    if footer is None and not images and not cover:
        issues.append("no footer and no photo: the card spilled onto a second page, split it")
    for top, bottom in images:
        # Text running into the photo, or set inside it, within photo_gap_px of its top.
        over = [ln for ln in lines if ln[1] < bottom and ln[2] + photo_gap_px > top]
        if over:
            issues.append(f"text sits on the photo: \"{over[0][4][:16]}\"")
    return issues


_CARD_CJK = re.compile(r"[\u3040-\u30ff\u3400-\u9fff\uac00-\ud7af\uf900-\ufaff]")


def card_orphans(page, max_chars: int, max_words: int = 1) -> list[str]:
    """Last lines of 1-3 characters (CJK) or a single word (Latin), paragraph by paragraph.

    MuPDF splits a wrapped CJK paragraph into one block per line, so lines are
    regrouped: the same type size and left edge, at most 1.9 line heights apart,
    and the line before ran wide (a wrapped line fills the measure; the list
    numbers 01, 02 stacked one above the other do not).
    """
    paragraphs: list[list[tuple[float, float, float, float, str, float]]] = []
    for ln in _card_lines(page):
        for para in reversed(paragraphs):
            last = para[-1]
            if (last[3] == ln[3] and abs(last[0] - ln[0]) < 4
                    and 0 < ln[1] - last[1] < ln[3] * 1.9
                    and last[5] - last[0] > ln[3] * 4):
                para.append(ln)
                break
        else:
            paragraphs.append([ln])
    found = []
    for para in paragraphs:
        tail = re.sub(r"\s", "", para[-1][4])
        short = (len(tail) <= max_chars if _CARD_CJK.search(tail)
                 else len(para[-1][4].split()) <= max_words)
        if len(para) > 1 and short:
            found.append(f"\"{tail}\" ends \"{para[0][4][:12]}\"")
    return found


def _scan_cards(paths: list[str], label: str, scan) -> int:
    try:
        fitz = require_pymupdf()
    except MissingDepError as exc:
        print(f"ERROR: {exc}")
        return 2
    if not paths:
        print(f"ERROR: usage: {label} cards.pdf [more.pdf ...]")
        return 2
    total = failed = 0
    for raw in paths:
        path = resolve_input(raw)
        if not path.exists():
            print(f"ERROR: {raw}: not found")
            failed += 1
            continue
        with fitz.open(str(path)) as doc:
            for index, page in enumerate(doc, start=1):
                for issue in scan(page, index == 1):
                    print(f"  {rel_to_root(path)} card {index}: {issue}")
                    total += 1
    if failed:
        return 2
    if total:
        print(f"\n{total} finding(s)")
        return 1
    print(f"OK: {len(paths)} card set(s), nothing to fix")
    return 0


def check_card_fit(paths: list[str]) -> int:
    """CLI: --check-card-fit cards.pdf. Text under the footer or on the photo."""
    cfg = load_checks_thresholds()["social_cards"]
    return _scan_cards(paths, "--check-card-fit", lambda page, first: card_fit_issues(
        page, int(cfg["footer_gap_px"]), int(cfg["photo_gap_px"]), cover=first))


def check_card_orphans(paths: list[str]) -> int:
    """CLI: --check-card-orphans cards.pdf. Fix with padding-right, never by rewording."""
    cfg = load_checks_thresholds()["social_cards"]
    return _scan_cards(paths, "--check-card-orphans",
                       lambda page, first: card_orphans(page, int(cfg["orphan_max_chars"]),
                                                        int(cfg["orphan_max_words"])))
