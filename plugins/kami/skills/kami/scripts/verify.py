"""End-to-end render verification for kami templates.

Renders each template through render.render_pdf, validates page-count against
per-template ceilings, inspects embedded PDF fonts to warn when only a
fallback is used, and runs an advisory density scan over the rendered
examples when invoked for the full suite. Self-sufficient: registries come
from shared, the render pipeline from render, the density scan from checks.
"""
from __future__ import annotations

import os
import re
import subprocess
import unicodedata
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote

from checks import _resume_balance_issues, scan_density
from hans import is_source_han
from hant import is_traditional_tag
from lint import scan_file
from math_render import MathRenderError
from optional_deps import MissingDepError, require_pymupdf, require_pypdf_reader
from render import build_slides, render_pdf
from shared import (
    DIAGRAMS,
    EXAMPLES,
    TEMPLATES,
    build_targets,
    default_example_pdfs,
    diagram_targets,
    load_checks_thresholds,
    pptx_targets,
    rel_to_root,
    resolve_input,
    screen_targets,
)

# Primary fonts expected in embedded PDF font names
CN_PRIMARY_FONTS = {"TsangerJinKai02"}
EN_PRIMARY_FONTS = {"Charter"}
KO_PRIMARY_FONTS = {"Source-Han-Serif-K", "SourceHanSerifK"}
# Traditional Chinese documents lead with Source Han Serif TC (hant.py); for
# them TsangerJinKai02 is a defect, since it sets mainland punctuation.
HANT_PRIMARY_FONTS = {"SourceHanSerifTC"}
# Simplified Chinese commercial / public-facing documents ask for Source Han
# Serif SC (hans.py); it is a legitimate primary beside TsangerJinKai02.
HANS_PRIMARY_FONTS = {"SourceHanSerifSC"}
# Noto Serif CJK SC is the same design under Google's name (what `fonts-noto-cjk`
# installs on Linux), so a marked document set in it is the reference rendering.
HANS_MARKED_PRIMARY_FONTS = HANS_PRIMARY_FONTS | {"NotoSerifCJKsc", "NotoSerifSC"}

# Serif families that keep a CJK page readable when the primary is unavailable.
# Falling through to one of these is a degradation, not a defect: the page still
# carries the serif texture every size, tracking and leading value was tuned for.
CJK_SERIF_MARKERS = (
    "TsangerJinKai",
    "SourceHanSerif",
    "NotoSerifCJK",
    "NotoSerifSC",
    "NotoSerifTC",
    "NotoSerifJP",
    "NotoSerifKR",
    "Songti",
    "STSong",
    "SimSun",
    "STZhongsong",
    "STKaiti",
    "KaiTi",
    "MSung",
    "MingLiU",
    "HiraginoMincho",
    "HiraMinPro",
    "YuMincho",
    "Myeongjo",
    "Myungjo",
    "Batang",
)
# A CJK run needs at least this many ideographs before its dominant font is
# worth judging: a stray glyph in an otherwise Latin document proves nothing.
MIN_CJK_CHARS_TO_JUDGE = 20
RECOGNIZABLE_FALLBACK_FONT_MARKERS = (
    "Georgia",
    "Palatino",
    "PT-Serif",
    "PTSerif",
    "TsangerJinKai",
    "YuMincho",
    "Hiragino",
    "SourceHan",
    "Noto",
    "Charter",
    "Songti",
    "DejaVu",
    "Liberation",
)


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


def _pdf_font_names(pdf_path: Path) -> set[str]:
    def _resolve_pdf_obj(obj):
        if obj is None:
            return None
        try:
            return obj.get_object() if hasattr(obj, "get_object") else obj
        except Exception:
            return obj

    try:
        PdfReader = require_pypdf_reader()
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
    except Exception as exc:
        print(f"  WARN: could not read font names from PDF: {exc}")
        return set()


def _normalize_font_name(name: str) -> str:
    """Reduce a PDF BaseFont entry to comparable letters and digits.

    Embedded names arrive subset-prefixed and punctuated in every combination
    ('ABCDEF+NotoSerifCJKsc-Regular', 'Noto Serif CJK SC'), so markers are
    matched against a stripped, lowercased form instead of the raw string.
    """
    return re.sub(r"[^a-z0-9]", "", name.lower())


def _classify_cjk_font(font_name: str, traditional: bool = False, source_han: bool | None = None) -> str:
    """Return 'primary', 'serif', 'mainland' or 'other' for one font name.

    `traditional` comes from the PDF's /Lang: a Traditional Chinese document
    has its own primary, and TsangerJinKai02 there is 'mainland', not primary.

    'other' covers both a system sans substitution and a family nobody here
    recognizes. Naming which of the two it is would need a second marker table
    to maintain, and would change nothing: both fail, both take the same fix,
    and the message already prints the family that drew the text.

    `source_han` is the source HTML's `data-serif` marker when the HTML sits beside
    the PDF: True makes Source Han Serif SC the only Simplified primary (a
    fallback to TsangerJinKai02 is then a serif fallback), False makes
    TsangerJinKai02 the only one, and None (no source found) accepts either.
    """
    normalized = _normalize_font_name(font_name)
    if traditional:
        primaries = HANT_PRIMARY_FONTS
    elif source_han is True:
        primaries = HANS_MARKED_PRIMARY_FONTS | KO_PRIMARY_FONTS
    elif source_han is False:
        primaries = CN_PRIMARY_FONTS | KO_PRIMARY_FONTS
    else:
        primaries = CN_PRIMARY_FONTS | HANS_PRIMARY_FONTS | KO_PRIMARY_FONTS
    if any(_normalize_font_name(m) in normalized for m in primaries):
        return "primary"
    if traditional and any(_normalize_font_name(m) in normalized for m in CN_PRIMARY_FONTS):
        return "mainland"
    if any(_normalize_font_name(m) in normalized for m in CJK_SERIF_MARKERS):
        return "serif"
    return "other"


def _pdf_lang(pdf_path: Path) -> str | None:
    """Return the PDF catalog /Lang, which WeasyPrint copies from <html lang>."""
    fitz = require_pymupdf()
    try:
        with fitz.open(str(pdf_path)) as doc:
            kind, value = doc.xref_get_key(doc.pdf_catalog(), "Lang")
    except Exception:
        return None
    return value if kind == "string" else None


class EmptyPdfError(ValueError):
    pass


def _cjk_font_usage(pdf_path: Path) -> dict[str, int]:
    """Return {font name: ideographs it drew} across the whole document.

    Judging the font table alone cannot tell which family actually set the body
    text: a document can embed a serif for two glyphs and a sans for the other
    three thousand. Walking spans attributes every ideograph to the font that
    drew it, so the verdict is about the text a reader sees.
    """
    fitz = require_pymupdf()
    per_font: dict[str, int] = {}
    with fitz.open(str(pdf_path)) as doc:
        if doc.page_count == 0:
            raise EmptyPdfError("PDF has no pages")
        for page in doc:
            for block in page.get_text("dict").get("blocks", []):
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        ideographs = sum(
                            1 for ch in span.get("text", "")
                            if "㐀" <= ch <= "鿿" or "가" <= ch <= "힯"
                        )
                        if ideographs:
                            font = span.get("font", "") or "(unnamed)"
                            per_font[font] = per_font.get(font, 0) + ideographs
    return per_font


# A second CJK family this far into the text is per-glyph fontconfig fallback,
# not a design decision: it splits single words down the middle. Below it, a
# stray symbol picked up elsewhere is not worth a failure.
MIXED_FAMILY_MIN_SHARE = 0.05
MIXED_FAMILY_MIN_CHARS = 3

# Weight and style words a PDF appends to the family it subsets. Bold body text
# is a second BaseFont entry off one family (TsangerJinKai02 plus
# TsangerJinKai02-Medium), which the mixed-family rule must not read as two
# typefaces. Longest first so 'semibold' strips before 'bold'.
# Two-letter abbreviations (Md, Rg, Bd) are deliberately absent: no font seen
# here uses them, and they are short enough to bite a real family name.
_FONT_STYLE_SUFFIXES = (
    "extralight", "semibold", "demibold", "oblique", "regular", "medium",
    "italic", "mediu", "medi", "light", "black", "heavy", "roman", "book", "bold",
    "thin", "lig",
)


# Numeric weight markers: TsangerJinKai ships W04/W05, other foundries use a
# three-digit CSS weight. Both name one family at two weights.
_FONT_WEIGHT_CODE = re.compile(r"(?:w\d{2}|\d{3})$")


def _font_family_key(name: str) -> str:
    """Reduce a font name to its family, dropping trailing weight/style words."""
    key = _normalize_font_name(name)
    changed = True
    while changed:
        changed = False
        for suffix in _FONT_STYLE_SUFFIXES:
            if key.endswith(suffix) and len(key) > len(suffix):
                key = key[: -len(suffix)]
                changed = True
                break
        stripped = _FONT_WEIGHT_CODE.sub("", key)
        if stripped != key and stripped:
            key = stripped
            changed = True
    return key


HANT_RECOVERY_HINT = (
    "  fix: install a Traditional Chinese Ming face (macOS ships Songti TC, Windows "
    "PMingLiU, `apt-get install fonts-noto-cjk` on Linux), then render again"
)
FONT_RECOVERY_HINT = (
    "  fix: bash scripts/ensure-fonts.sh (installs a CJK serif into the user font dir), "
    "or `brew install --cask font-source-han-serif-sc` on macOS, "
    "or `apt-get install fonts-noto-cjk` on Linux, then render again"
)


def check_fonts(paths: list[str]) -> int:
    """CLI: --check-fonts doc.pdf [more.pdf ...]

    Deterministic gate on the one failure a perceptual pass reliably misses.
    A missing CJK serif does not produce fallback boxes; it silently swaps in a
    sans that still reads, so both the agent and the author sign off on a page
    whose typography is no longer the system's. The rendered PDF's own span
    table settles it: whichever font drew the body ideographs is the verdict.
    """
    files = [p for p in paths if not p.startswith("-")]
    if not files:
        print("ERROR: usage: --check-fonts path/to/doc.pdf [more.pdf ...]")
        return 2

    failures = 0
    empty = 0
    for raw in files:
        pdf = resolve_input(raw)
        rel = rel_to_root(pdf)
        if not pdf.exists():
            print(f"ERROR: {raw}: file not found")
            failures += 1
            continue
        try:
            usage = _cjk_font_usage(pdf)
        except MissingDepError as exc:
            print(f"ERROR: {exc}")
            return 2
        except EmptyPdfError:
            # Same verdict as the other PDF gates: nothing was checked.
            print(f"ERROR: {raw}: PDF has no pages")
            empty += 1
            continue
        except Exception as exc:
            print(f"ERROR: {rel}: could not read text spans: {exc}")
            failures += 1
            continue

        count = sum(usage.values())
        if not usage or count < MIN_CJK_CHARS_TO_JUDGE:
            print(f"OK: {rel}: no CJK body text to judge ({count} ideograph(s))")
            continue

        traditional = is_traditional_tag(_pdf_lang(pdf))
        # Collapse weight variants into their family before counting families.
        families: dict[str, tuple[str, int]] = {}
        for name, chars in usage.items():
            key = _font_family_key(name)
            label, total = families.get(key, (name, 0))
            if chars > usage.get(label, 0):
                label = name
            families[key] = (label, total + chars)

        dominant = max(families, key=lambda k: families[k][1])
        font, font_chars = families[dominant]
        others = [
            (label, chars) for key, (label, chars) in families.items()
            if key != dominant
            and chars >= MIXED_FAMILY_MIN_CHARS
            and chars / count >= MIXED_FAMILY_MIN_SHARE
        ]
        if others:
            detail = ", ".join(f"{name} ({chars})" for name, chars in sorted(others))
            print(f"ERROR: {rel}: CJK text split across families: {font} ({font_chars}), {detail}")
            print("  per-glyph fallback breaks single words across two typefaces; "
                  "one page carries one serif")
            print(HANT_RECOVERY_HINT if traditional else FONT_RECOVERY_HINT)
            failures += 1
            continue

        source = pdf.with_suffix(".html")
        source_han = (is_source_han(source.read_text(encoding="utf-8", errors="replace"))
                      if source.is_file() else None)
        verdict = _classify_cjk_font(font, traditional, source_han)
        if verdict == "primary":
            print(f"OK: {rel}: CJK body text in {font} ({count} ideographs)")
        elif verdict == "serif":
            print(f"WARN: {rel}: CJK body text in {font}, a serif fallback, not the kami primary")
            print("  acceptable, but the page is not the reference rendering")
        elif verdict == "mainland":
            print(f"ERROR: {rel}: Traditional Chinese body text in {font}, which sets mainland punctuation")
            print("  its comma and full stop sit bottom-left in a narrow cell; Traditional "
                  "Chinese centers them in a full-width cell")
            print(HANT_RECOVERY_HINT)
            failures += 1
        else:
            print(f"ERROR: {rel}: CJK body text in {font}, not a CJK serif")
            print("  the parchment metrics are tuned for serif stroke density; a sans "
                  "substitution reads heavier and flatter at the same size, with no "
                  "fallback box to make it obvious")
            print(FONT_RECOVERY_HINT)
            failures += 1

    if empty:
        return 2
    return 0 if failures == 0 else 1


def _check_font_sources(html_path: Path) -> list[str]:
    """Return list of local @font-face src files that are missing on disk."""
    text = html_path.read_text(encoding="utf-8", errors="replace")
    missing: list[str] = []
    for url in re.findall(r"""url\(["']?([^"')]+)["']?\)""", text):
        if url.startswith(("http://", "https://", "data:", "#")):
            continue
        resolved = (html_path.parent / url).resolve()
        if not resolved.exists():
            missing.append(url)
    return missing


TOC_TARGET_COUNTER = "target-counter(attr(href), page)"


class _TocTitles(HTMLParser):
    """Read the long-doc template's actual TOC entries, including inline markup."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.rows: list[tuple[str, str]] = []
        self.target: str | None = None
        self.parts: list[str] = []

    def handle_starttag(self, tag, attributes):
        attrs = dict(attributes)
        if tag == "a" and "toc-title" in (attrs.get("class") or "").split():
            href = attrs.get("href") or ""
            if href.startswith("#"):
                self.target = unquote(href[1:])
                self.parts = []

    def handle_data(self, data):
        if self.target is not None:
            self.parts.append(data)

    def handle_endtag(self, tag):
        if tag == "a" and self.target is not None:
            self.rows.append((self.target, "".join(self.parts)))
            self.target = None


def _toc_page_number_issues(pdf_path: Path, source_html: str) -> list[str]:
    """Cross-check every rendered TOC page number against the page its row links to.

    WeasyPrint resolves `target-counter` at render time, so a failed resolution
    still prints a well-formed numeral and every text-level gate accepts it.
    WeasyPrint 70.0 does exactly that when the TOC anchor is a flex container:
    each row renders `0`. Comparing the glyph against the link destination
    catches both that failure and ordinary page-number drift.
    """
    try:
        fitz = require_pymupdf()
    except MissingDepError as exc:
        print(f"  WARN: TOC page-number check skipped: {exc}")
        return []

    parser = _TocTitles()
    parser.feed(source_html)
    parser.close()
    if not parser.rows:
        return []

    def normalized(text):
        # An unused discretionary hyphen is present in HTML but absent in PDF text.
        return "".join(unicodedata.normalize("NFKC", text).replace("\u00ad", "").split())

    candidates: list[tuple[str, str, str, int]] = []
    with fitz.open(str(pdf_path)) as doc:
        for page in doc:
            destinations: dict[str, list] = {}
            for link in page.get_links():
                dest = link.get("nameddest")
                if dest:
                    destinations.setdefault(dest, []).append(link)
            for dest, links in sorted(destinations.items()):
                for numeral in links:
                    rect = numeral["from"]
                    # A block TOC anchor emits a row-sized link and a contained
                    # right-floated numeral. Styled inline links can also nest,
                    # so geometry alone is not enough: match authored titles below.
                    containers = [
                        outer for outer in links
                        if outer["from"].width > rect.width
                        and rect in outer["from"]
                        and abs(outer["from"].x1 - rect.x1) < 0.01
                    ]
                    if not containers:
                        continue
                    outer = min(containers, key=lambda link: link["from"].get_area())
                    candidates.append((
                        dest, normalized(page.get_textbox(outer["from"])),
                        normalized(page.get_textbox(rect)), numeral["page"] + 1,
                    ))

    issues: list[str] = []
    for dest, title in parser.rows:
        title = normalized(title)
        match = next((i for i, (target, row, number, _) in enumerate(candidates)
                      if target == dest and row in (number + title, title + number)), None)
        if match is None:
            issues.append(f"TOC row '{dest}' has no rendered page-number link")
            continue
        _, _, number, expected = candidates.pop(match)
        if not number.isdecimal():
            issues.append(f"TOC row '{dest}' renders no page number (links to page {expected})")
        elif int(number) != expected:
            issues.append(f"TOC row '{dest}' renders page {number} but links to page {expected}")
    return issues


def verify_target(name: str, source: str, max_pages: int, src_dir: Path) -> list[str]:
    """Render `source` to a PDF, then run page-count and font checks."""
    issues: list[str] = []
    src = src_dir / source
    if not src.exists():
        issues.append(f"source not found: {src}")
        return issues

    # Warn about missing local font files before rendering
    missing_fonts = _check_font_sources(src)
    if missing_fonts:
        for mf in missing_fonts:
            print(f"  [FONT MISS] {name}: {mf} not found")
        print(f"  [FONT MISS] Repo checkout fix: bash scripts/ensure-fonts.sh (copies the tracked fonts from the repository root into assets/fonts)")
        print(f"  [FONT MISS] Skill recovery (downloads to the user font dir, not the skill): bash scripts/ensure-fonts.sh")
        print(f"  [FONT MISS] Fallback: brew install --cask font-source-han-serif-sc")

    out = EXAMPLES / f"{name}.pdf"
    try:
        n = render_pdf(src, out)
    except (MissingDepError, MathRenderError) as exc:
        issues.append(str(exc))
        return issues
    except Exception as exc:  # WeasyPrint / pypdf / OS errors: report, keep the sweep going
        issues.append(f"render failed: {exc}")
        return issues

    # Resume templates share the balance gate's exact two-page contract. Keep
    # fill and gap checks in the filled-document flow: source templates contain
    # placeholder copy, so their rendered density is not an authoring signal.
    if "resume" in name:
        cfg = load_checks_thresholds()["resume_balance"]
        page_issues = _resume_balance_issues(
            [],
            n,
            float(cfg["min_fill_pct"]),
            float(cfg["max_fill_pct"]),
            float(cfg["max_gap_pct"]),
        )
        hint = ""
        if n == 3:
            hint = '; add class="resume--dense" to <body> or tighten .proj-text line-height to 1.38'
        issues.extend(f"page count: {issue}{hint}" for issue in page_issues)
    elif max_pages and n > max_pages:
        issues.append(f"page overflow: {n} pages (limit {max_pages})")

    # Rendered TOC page numbers (long-doc family)
    source_html = src.read_text(encoding="utf-8")
    if TOC_TARGET_COUNTER in source_html:
        issues.extend(_toc_page_number_issues(out, source_html))

    # font check
    embedded = _pdf_font_names(out)
    fallback_present = any(
        kw in font for font in embedded
        for kw in RECOGNIZABLE_FALLBACK_FONT_MARKERS
    )

    # Diagram templates are language-neutral and often rely on fallback stacks,
    # so only enforce that at least one recognizable serif/sans fallback exists.
    is_diagram = src_dir == DIAGRAMS
    if is_diagram:
        if not fallback_present:
            issues.append(f"no recognizable font embedded in {out.name}")
        return issues

    is_en = name.endswith("-en")
    is_ko = name.endswith("-ko")
    expected = EN_PRIMARY_FONTS if is_en else (KO_PRIMARY_FONTS if is_ko else CN_PRIMARY_FONTS)
    if not any(exp in font_name for exp in expected for font_name in embedded):
        primary = next(iter(expected))
        if not fallback_present:
            issues.append(f"no recognizable font embedded in {out.name}")
        elif os.environ.get("KAMI_ALLOW_FALLBACK_ONLY"):
            # CI / headless boxes never have commercial fonts (TsangerJinKai02,
            # Charter). Treat "primary missing, fallback present" as a warning
            # there so CI can still gate page-count regressions.
            print(f"  WARN: {name}: primary font ({primary}) not embedded; using fallback")
        else:
            issues.append(f"primary font ({primary}) not embedded; using fallback")

    return issues


def verify_screen_target(name: str, source: str) -> list[str]:
    """Lint a browser-only template via lint.scan_file."""
    src = TEMPLATES / source
    if not src.exists():
        return [f"source not found: {src}"]
    findings = scan_file(src)
    if findings:
        return [f"{len(findings)} template violation(s)"]
    return []


def verify_all(target: str | None) -> int:
    """Drive verification across the requested target set."""
    html_targets = build_targets()
    screen_targets_map = screen_targets()
    diagram_targets_map = diagram_targets()
    pptx_targets_map = pptx_targets()

    targets_to_run: dict[str, tuple[str, int, Path] | None] = {}
    screen_targets_to_run: dict[str, str] = {}
    if target:
        if target in html_targets:
            src, mp = html_targets[target]
            targets_to_run[target] = (src, mp, TEMPLATES)
        elif target in screen_targets_map:
            screen_targets_to_run[target] = screen_targets_map[target]
        elif target in diagram_targets_map:
            targets_to_run[target] = (diagram_targets_map[target], 0, DIAGRAMS)
        elif target in pptx_targets_map:
            targets_to_run[target] = None
        else:
            print(f"ERROR: unknown target: {target}")
            return 2
    else:
        for name, (src, mp) in html_targets.items():
            targets_to_run[name] = (src, mp, TEMPLATES)
        for name, src in screen_targets_map.items():
            screen_targets_to_run[name] = src
        for name, src in diagram_targets_map.items():
            targets_to_run[name] = (src, 0, DIAGRAMS)
        for name in pptx_targets_map:
            targets_to_run[name] = None

    failures = 0
    rows: list[tuple[str, str]] = []
    for name, config in targets_to_run.items():
        if config is None:
            issues = [] if build_slides(name) else ["slides build failed"]
        else:
            source, max_pages, src_dir = config
            issues = verify_target(name, source, max_pages, src_dir)
        if issues:
            rows.append((f"ERROR: {name}", "; ".join(issues)))
            failures += 1
        else:
            rows.append((f"OK: {name}", "ok"))

    for name, source in screen_targets_to_run.items():
        issues = verify_screen_target(name, source)
        if issues:
            rows.append((f"ERROR: {name}", "; ".join(issues)))
            failures += 1
        else:
            rows.append((f"OK: {name}", "static HTML template"))

    for status, detail in rows:
        print(f"{status}: {detail}")

    if target is None:
        pdfs = default_example_pdfs()
        if pdfs:
            print()
            print("Density scan (advisory):")
            scan = scan_density(pdfs)
            if scan is not None:
                sparse, warn, _, scanned = scan
                if sparse + warn == 0:
                    print(f"  OK: no density issues across {scanned} PDF(s)")
                else:
                    density_cfg = load_checks_thresholds()["density"]
                    sparse_pct_disp = int(round(float(density_cfg["sparse_pct"]) * 100))
                    warn_pct_disp = int(round(float(density_cfg["warn_pct"]) * 100))
                    if sparse:
                        print(f"  {sparse} SPARSE page(s) (>{sparse_pct_disp}% trailing whitespace) across {scanned} PDF(s)")
                    if warn:
                        print(f"  {warn} WARN page(s) (>{warn_pct_disp}%) across {scanned} PDF(s)")
                    print("  (advisory: re-author with the writing.md «Page density» merge rule. Does not fail --verify.)")

    return 0 if failures == 0 else 1
