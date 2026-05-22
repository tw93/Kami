"""PDF-side and content-shape checks for kami documents.

Splits out from build.py:
  - check_placeholders: scan filled HTML for unreplaced `{{...}}` tokens.
  - check_orphans:      scan rendered PDFs for short trailing lines (typographic orphans).
  - check_density:      scan rendered PDFs for pages with too much trailing whitespace.
  - check_rhythm:       scan slides Python source for monotonous deck sequences.

Density scanning uses a parchment-aware pixel sweep. The hot path is
vectorized with NumPy when available and falls back to a pure-Python loop.
Thresholds and DPI live in `references/checks_thresholds.json`.
"""
from __future__ import annotations

import re
from pathlib import Path

from optional_deps import MissingDepError, require_pymupdf
from shared import EXAMPLES, PARCHMENT_RGB, ROOT, load_checks_thresholds

PLACEHOLDER = re.compile(r"\{\{[^}]+\}\}")

# Parchment background RGB for pixel comparison (sourced from shared.PARCHMENT_RGB).
_BG_R, _BG_G, _BG_B = PARCHMENT_RGB
_BG_TOLERANCE = 10


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


# ---------- orphan check ----------

def check_orphans(paths: list[str]) -> int:
    """Scan PDF for text blocks whose last line has <= max_words and < max_chars."""
    try:
        fitz = require_pymupdf()
    except MissingDepError as exc:
        print(f"ERROR: {exc}")
        return 2

    if not paths:
        if EXAMPLES.exists():
            paths = [str(p) for p in sorted(EXAMPLES.glob("*.pdf"))]
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
        path = Path(raw)
        if not path.exists():
            print(f"ERROR: {raw}: not found")
            missing += 1
            continue
        scanned += 1
        doc = fitz.open(str(path))
        rel = path.relative_to(ROOT) if path.is_relative_to(ROOT) else path
        for page_num in range(len(doc)):
            page = doc[page_num]
            blocks = page.get_text("blocks")
            for bx0, by0, bx1, by1, text, block_no, block_type in blocks:
                if block_type != 0:  # text blocks only
                    continue
                lines = text.strip().splitlines()
                if len(lines) < 2:
                    continue
                last = lines[-1].strip()
                words = last.split()
                if len(words) <= max_words and len(last) < max_chars:
                    total += 1
                    print(f"  {rel} p{page_num + 1}: orphan: \"{last}\" ({len(words)} word(s), {len(last)} chars)")
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


def _scan_density(paths: list[str]) -> tuple[int, int, int, int] | None:
    """Scan PDFs and print SPARSE/WARN lines.

    Returns (sparse, warn, missing, scanned), or None if PyMuPDF is missing.
    Thresholds (warn_pct, sparse_pct, dpi) come from
    references/checks_thresholds.json.
    """
    try:
        fitz = require_pymupdf()
    except MissingDepError as exc:
        print(f"ERROR: {exc}")
        return None

    density_cfg = load_checks_thresholds()["density"]
    warn_pct = float(density_cfg["warn_pct"])
    sparse_pct = float(density_cfg["sparse_pct"])
    dpi = int(density_cfg["dpi"])

    sparse = 0
    warn = 0
    missing = 0
    scanned = 0
    for raw in paths:
        path = Path(raw)
        if not path.exists():
            print(f"ERROR: {raw}: not found")
            missing += 1
            continue
        scanned += 1
        doc = fitz.open(str(path))
        rel = path.relative_to(ROOT) if path.is_relative_to(ROOT) else path
        for page_num in range(len(doc)):
            if page_num == 0:
                continue
            page = doc[page_num]
            pix = page.get_pixmap(dpi=dpi)
            w, h = pix.width, pix.height
            if h == 0:
                continue
            last_content_y = _last_content_y(pix.samples, w, h, pix.stride, pix.n)

            empty = (h - last_content_y) / h
            if empty > sparse_pct:
                print(f"  SPARSE: {rel} p{page_num + 1}: {empty:.0%} trailing whitespace")
                sparse += 1
            elif empty > warn_pct:
                print(f"  WARN: {rel} p{page_num + 1}: {empty:.0%} trailing whitespace")
                warn += 1
        doc.close()
    return sparse, warn, missing, scanned


def check_density(paths: list[str]) -> int:
    """Scan PDF pages for sparse content (large trailing whitespace from
    break-inside:avoid pushing content to the next page)."""
    if not paths:
        if EXAMPLES.exists():
            paths = [str(p) for p in sorted(EXAMPLES.glob("*.pdf"))]
        if not paths:
            print("ERROR: no PDF files to scan")
            return 2

    result = _scan_density(paths)
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


def check_rhythm(targets: list[str], pptx_targets: dict[str, str], templates_dir: Path) -> int:
    """Scan slide templates for monotony: too many consecutive content_slides,
    missing dividers, and missing density variation.

    Thresholds come from references/checks_thresholds.json.
    """
    names = targets if targets else list(pptx_targets.keys())
    failures = 0
    rhythm_cfg = load_checks_thresholds()["rhythm"]
    max_content_run = int(rhythm_cfg["max_content_run"])
    divider_min_deck_size = int(rhythm_cfg["divider_min_deck_size"])

    for name in names:
        source = pptx_targets.get(name)
        if source is None:
            print(f"ERROR: {name}: not a known slides target")
            failures += 1
            continue
        src = templates_dir / source
        if not src.exists():
            print(f"ERROR: {name}: source not found ({src})")
            failures += 1
            continue

        seq = _parse_slide_sequence(src)
        if not seq:
            print(f"ERROR: {name}: no slide calls found in main() (deck unparseable)")
            failures += 1
            continue

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

        if issues:
            for issue in issues:
                print(f"WARN: {name}: {issue}")
            failures += 1
        else:
            print(f"OK: {name}: rhythm ok ({len(seq)} slides, max run {max_run})")

    return 0 if failures == 0 else 1
