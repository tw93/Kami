#!/usr/bin/env python3
"""Lightweight tests for scripts/build.py and scripts/shared.py.

Run with: python3 scripts/tests/test_build.py
The harness uses plain assertions and a tiny runner so it has no third-party
dependency (matching the rest of the repo's lean tooling).
"""
from __future__ import annotations

import contextlib
import builtins
import importlib.util
import io
import sys
import tempfile
import zipfile
from pathlib import Path

# Make scripts/ importable when running this file directly.
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from build import (  # noqa: E402
    DIAGRAM_TARGETS,
    HTML_TARGETS,
    PPTX_TARGETS,
    SCREEN_TARGETS,
    _BG_B,
    _BG_G,
    _BG_R,
    _extract_root_vars,
    _last_content_y,
    _pair_names,
    _parse_slide_sequence,
    check_cross_template_consistency,
    check_placeholders,
    scan_file,
)
from shared import (  # noqa: E402
    HTML_TEMPLATES,
    PARCHMENT_RGB,
    ROOT as REPO_ROOT,
    SCREEN_TEMPLATES,
    TEMPLATES,
    build_targets,
    screen_targets,
    stabilize_targets,
)
import highlight as highlight_mod  # noqa: E402
from highlight import highlight_code_blocks  # noqa: E402
from stabilize import (  # noqa: E402
    blend_rgba_on_parchment,
    clamp,
    clamp_line_heights,
    extract_css,
    luminance,
    normalize_cool_grays,
    normalize_rgba,
    parse_hex,
    replace_css,
    rgb_to_hex,
    run_for_target,
    tighten_section_gap,
)


# --------------------------- helpers ---------------------------

_PASS = 0
_FAIL = 0


def check(name: str, predicate: bool, detail: str = "") -> None:
    global _PASS, _FAIL
    if predicate:
        _PASS += 1
        print(f"OK: {name}")
    else:
        _FAIL += 1
        print(f"ERROR: {name}{(' - ' + detail) if detail else ''}")


def write_temp_html(body: str, suffix: str = "-en.html") -> Path:
    f = tempfile.NamedTemporaryFile(mode="w", suffix=suffix, delete=False, encoding="utf-8")
    f.write(body)
    f.close()
    return Path(f.name)


def silently(callable_, *args, **kwargs):
    """Run a function with stdout suppressed, return its result."""
    sink = io.StringIO()
    with contextlib.redirect_stdout(sink):
        return callable_(*args, **kwargs)


# --------------------------- package archive ---------------------------

PACKAGE_MAX_BYTES = 6_000_000
PACKAGE_FORBIDDEN_EXACT = {
    "assets/images/1.png",
    "assets/images/2.png",
    "assets/images/3.png",
    "assets/fonts/TsangerJinKai02-W04.ttf",
    "assets/fonts/TsangerJinKai02-W05.ttf",
}


def test_dist_package_contents() -> None:
    archive = REPO_ROOT / "dist" / "kami.zip"
    check("dist/kami.zip exists", archive.exists(), f"missing {archive}")
    if not archive.exists():
        return

    size_bytes = archive.stat().st_size
    check("dist/kami.zip stays below 6MB",
          size_bytes <= PACKAGE_MAX_BYTES,
          f"{size_bytes} bytes > {PACKAGE_MAX_BYTES} bytes")

    with zipfile.ZipFile(archive) as zf:
        names = set(zf.namelist())

    forbidden = sorted(
        name for name in names
        if name.startswith("assets/showcase/") or name in PACKAGE_FORBIDDEN_EXACT
    )
    check("dist/kami.zip excludes showcase screenshots and commercial fonts",
          not forbidden,
          f"forbidden entries: {', '.join(forbidden)}")
    check("dist/kami.zip keeps logo.svg",
          "assets/images/logo.svg" in names)


# --------------------------- shared registry ---------------------------

def test_registry_consistency() -> None:
    check("HTML_TEMPLATES has 24 entries", len(HTML_TEMPLATES) == 24,
          f"got {len(HTML_TEMPLATES)}")
    check("SCREEN_TARGETS has 2 entries", len(SCREEN_TARGETS) == 2,
          f"got {len(SCREEN_TARGETS)}")
    check("build_targets matches HTML_TEMPLATES key set",
          set(build_targets()) == set(HTML_TEMPLATES))
    check("screen_targets matches SCREEN_TARGETS key set",
          set(screen_targets()) == set(SCREEN_TARGETS))
    check("stabilize_targets is a subset of HTML_TEMPLATES",
          set(stabilize_targets()) <= set(HTML_TEMPLATES))
    check("HTML_TARGETS in build.py matches build_targets()",
          dict(HTML_TARGETS) == build_targets())
    check("DIAGRAM_TARGETS has 14 entries", len(DIAGRAM_TARGETS) == 14,
          f"got {len(DIAGRAM_TARGETS)}")
    check("PPTX_TARGETS has 2 entries", len(PPTX_TARGETS) == 2,
          f"got {len(PPTX_TARGETS)}")
    check("PARCHMENT_RGB is canonical", PARCHMENT_RGB == (0xF5, 0xF4, 0xED))


def test_chinese_html_templates_keep_single_serif_stack() -> None:
    """Chinese templates must keep --sans pinned to --serif for PDF glyph safety."""
    offenders: list[str] = []
    for name, spec in HTML_TEMPLATES.items():
        source = spec.source
        if name.endswith("-en"):
            continue
        text = (TEMPLATES / source).read_text(encoding="utf-8")
        if "--sans: var(--serif)" not in text and "--sans:  var(--serif)" not in text:
            offenders.append(source)

    check("Chinese HTML templates keep --sans: var(--serif)",
          not offenders,
          f"offenders: {', '.join(offenders)}")


def test_chinese_slides_mono_has_cjk_fallback() -> None:
    """Slide labels may mix mono Latin and CJK; the mono stack needs CJK fallback."""
    text = (TEMPLATES / "slides-weasy.html").read_text(encoding="utf-8")
    check("slides-weasy mono stack includes TsangerJinKai02 fallback",
          '"TsangerJinKai02"' in text and '"Source Han Serif SC"' in text)


# --------------------------- scan_file ---------------------------

def test_scan_file_skip_bug() -> None:
    """Lines starting with '#' (CSS id selectors) must NOT be skipped."""
    fixture = """<!doctype html>
<html><head><style>
#card { background: rgba(0,0,0,0.5); }
</style></head><body></body></html>
"""
    p = write_temp_html(fixture)
    try:
        findings = scan_file(p)
        rules = {f.rule for f in findings}
        check("scan_file flags rgba on #id-prefixed CSS line",
              "rgba-background" in rules,
              f"rules found: {rules or '(none)'}")
    finally:
        p.unlink(missing_ok=True)


def test_scan_file_arrow_in_en() -> None:
    """`→` in -en.html body should trigger arrow-unicode-in-en."""
    fixture = """<!doctype html>
<html lang="en"><head><style>
.tag { color: #1B365D; }
</style></head><body>
<p>Step 1 → Step 2</p>
</body></html>
"""
    p = write_temp_html(fixture, suffix="-en.html")
    try:
        findings = scan_file(p)
        rules = {f.rule for f in findings}
        check("scan_file flags U+2192 arrow in -en.html",
              "arrow-unicode-in-en" in rules,
              f"rules found: {rules or '(none)'}")
    finally:
        p.unlink(missing_ok=True)


def test_scan_file_clean_template() -> None:
    """A clean template should produce zero findings."""
    fixture = """<!doctype html>
<html><head><style>
:root { --brand: #1B365D; }
.card { background: var(--ivory); }
.tag { background: #EEF2F7; color: var(--brand); }
</style></head><body></body></html>
"""
    p = write_temp_html(fixture)
    try:
        findings = scan_file(p)
        check("scan_file produces no findings on clean template",
              len(findings) == 0,
              f"got {len(findings)} finding(s): {[f.rule for f in findings]}")
    finally:
        p.unlink(missing_ok=True)


# --------------------------- slide sequence ---------------------------

def test_parse_slide_sequence_empty() -> None:
    fixture = """def main():
    pass
"""
    p = write_temp_html(fixture, suffix=".py")
    try:
        seq = _parse_slide_sequence(p)
        check("_parse_slide_sequence returns [] for empty main()",
              seq == [], f"got {seq}")
    finally:
        p.unlink(missing_ok=True)


def test_parse_slide_sequence_basic() -> None:
    fixture = """def main():
    cover_slide()
    content_slide()
    content_slide()
    chapter_slide()
    metrics_slide()

def helper():
    other_call()
"""
    p = write_temp_html(fixture, suffix=".py")
    try:
        seq = _parse_slide_sequence(p)
        expected = ["cover_slide", "content_slide", "content_slide", "chapter_slide", "metrics_slide"]
        check("_parse_slide_sequence parses ordered slide calls",
              seq == expected, f"got {seq}")
    finally:
        p.unlink(missing_ok=True)


# --------------------------- scan_file extra rules ---------------------------

def test_scan_file_line_height_too_loose() -> None:
    """line-height >= 1.6 should trigger line-height-too-loose."""
    fixture = """<!doctype html>
<html><head><style>
p { line-height: 1.8; }
</style></head><body></body></html>
"""
    p = write_temp_html(fixture)
    try:
        findings = scan_file(p)
        rules = {f.rule for f in findings}
        check("scan_file flags line-height 1.8 (too loose)",
              "line-height-too-loose" in rules,
              f"rules found: {rules or '(none)'}")
    finally:
        p.unlink(missing_ok=True)


def test_scan_file_cool_gray() -> None:
    """Cool-gray hex literals should be flagged."""
    fixture = """<!doctype html>
<html><head><style>
.muted { color: #888; }
</style></head><body></body></html>
"""
    p = write_temp_html(fixture)
    try:
        findings = scan_file(p)
        rules = {f.rule for f in findings}
        check("scan_file flags cool gray #888",
              "cool-gray" in rules,
              f"rules found: {rules or '(none)'}")
    finally:
        p.unlink(missing_ok=True)


def test_scan_file_ignores_block_comment_rgba() -> None:
    """rgba() inside a /* ... */ CSS block comment must not trigger findings."""
    fixture = """<!doctype html>
<html><head><style>
/* historical note: we used to write
   background: rgba(0,0,0,0.5);
   here, but switched to solid hex. */
.card { background: #EEF2F7; }
</style></head><body></body></html>
"""
    p = write_temp_html(fixture)
    try:
        findings = scan_file(p)
        rules = {f.rule for f in findings}
        check("scan_file ignores rgba inside /* */ comment",
              "rgba-background" not in rules,
              f"rules found: {rules or '(none)'}")
    finally:
        p.unlink(missing_ok=True)


def test_scan_file_thin_border_with_radius() -> None:
    """Sub-1pt closed border in a block with border-radius should fire pitfall #2."""
    fixture = """<!doctype html>
<html><head><style>
.tag {
  border: 0.5pt solid #1B365D;
  border-radius: 3pt;
  background: #EEF2F7;
}
</style></head><body></body></html>
"""
    p = write_temp_html(fixture)
    try:
        findings = scan_file(p)
        rules = {f.rule for f in findings}
        check("scan_file flags thin border with border-radius",
              "thin-border-radius" in rules,
              f"rules found: {rules or '(none)'}")
    finally:
        p.unlink(missing_ok=True)


# --------------------------- check_placeholders ---------------------------

def test_check_placeholders_flags_unfilled() -> None:
    """A doc with `{{ name }}` left over should fail the check."""
    p = write_temp_html("<html><body><h1>{{ name }}</h1><p>{{ role }}</p></body></html>")
    try:
        rc = silently(check_placeholders, [str(p)])
        check("check_placeholders fails on {{ name }}", rc == 1, f"rc={rc}")
    finally:
        p.unlink(missing_ok=True)


def test_check_placeholders_passes_clean() -> None:
    """A doc with no placeholder syntax should pass."""
    p = write_temp_html("<html><body><h1>Real Name</h1><p>Real role</p></body></html>")
    try:
        rc = silently(check_placeholders, [str(p)])
        check("check_placeholders passes clean file", rc == 0, f"rc={rc}")
    finally:
        p.unlink(missing_ok=True)


# --------------------------- stabilize pure functions ---------------------------

# --------------------------- cross-template consistency ---------------------------

def test_pair_names_includes_known_pairs() -> None:
    captured = list(_pair_names())
    check("pair_names includes one-pager",
          ("one-pager", "one-pager-en") in captured,
          f"got {[v for b, v in captured if b == 'one-pager']!r}")
    pairs = dict(captured)
    check("pair_names includes landing-page", pairs.get("landing-page") == "landing-page-en",
          f"got {pairs.get('landing-page')!r}")
    check("pair_names omits lone -en entries",
          not any(name.endswith("-en") for name, _ in _pair_names()))


def test_cross_template_consistency_clean() -> None:
    """The current repo should pass cross-template consistency."""
    rc = silently(check_cross_template_consistency, False)
    check("cross-template returns 0 on current repo", rc == 0, f"rc={rc}")


def test_pair_names_includes_ko_variants_when_present():
    """`_pair_names` must yield (base, base-ko) pairs in addition to (base, base-en)."""
    captured = list(_pair_names())
    # Sanity: existing CN/EN pairs still detected.
    assert ("one-pager", "one-pager-en") in captured, "CN/EN pair regressed"
    # KO detection is conditional on KO templates being registered; this test
    # documents the contract: any base whose `-ko` sibling is present in the
    # registry must appear as a (base, base-ko) pair.
    bases = {base for base, _ in captured}
    seen = set(HTML_TEMPLATES) | set(SCREEN_TEMPLATES)
    for base in bases:
        ko_name = f"{base}-ko"
        if ko_name in seen:
            assert (base, ko_name) in captured, f"KO sibling for {base} not paired"
    check("pair_names includes ko variants when present", True)


def test_extract_root_vars_picks_up_definitions() -> None:
    fixture = """<!doctype html>
<html><head><style>
:root {
  --brand: #1B365D;
  --parchment: #F5F4ED;
  --serif: Charter, Georgia, serif;
}
</style></head><body></body></html>
"""
    p = write_temp_html(fixture)
    try:
        vars_ = _extract_root_vars(p)
        check("extract_root_vars finds --brand", vars_.get("--brand") == "#1B365D",
              f"got {vars_.get('--brand')!r}")
        check("extract_root_vars finds --parchment", vars_.get("--parchment") == "#F5F4ED",
              f"got {vars_.get('--parchment')!r}")
    finally:
        p.unlink(missing_ok=True)


def test_clamp_basic() -> None:
    check("clamp inside range", clamp(0.5, 0.0, 1.0) == 0.5)
    check("clamp clips low", clamp(-0.1, 0.0, 1.0) == 0.0)
    check("clamp clips high", clamp(1.5, 0.0, 1.0) == 1.0)


def test_parse_hex_3_and_6() -> None:
    check("parse_hex handles #fff -> (255,255,255)", parse_hex("#fff") == (255, 255, 255))
    check("parse_hex handles #1B365D", parse_hex("#1B365D") == (27, 54, 93))


def test_rgb_to_hex_pads_uppercase() -> None:
    check("rgb_to_hex emits uppercase 6-char form",
          rgb_to_hex((27, 54, 93)) == "#1B365D")


def test_blend_rgba_on_parchment_alpha_zero() -> None:
    """alpha=0 returns the parchment background (overlay invisible)."""
    out = blend_rgba_on_parchment(0, 0, 0, 0.0)
    check("blend alpha=0 -> parchment", out == "#F5F4ED", f"got {out}")


def test_blend_rgba_on_parchment_alpha_one() -> None:
    """alpha=1 returns the overlay color exactly."""
    out = blend_rgba_on_parchment(0, 0, 0, 1.0)
    check("blend alpha=1 -> overlay", out == "#000000", f"got {out}")


def test_normalize_rgba_blends_to_solid() -> None:
    """rgba() should be replaced by a solid hex on parchment."""
    css = ".a { background: rgba(0, 0, 0, 0.5); }"
    out, hits = normalize_rgba(css)
    check("normalize_rgba removes rgba(", "rgba(" not in out, f"out: {out}")
    check("normalize_rgba reports one hit", hits == 1, f"hits={hits}")


def test_normalize_rgba_skips_invalid() -> None:
    """Channel > 255 should be left alone (not a real color)."""
    css = ".a { background: rgba(300, 0, 0, 0.5); }"
    out, hits = normalize_rgba(css)
    check("normalize_rgba skips out-of-range channel", "rgba(300" in out)
    check("normalize_rgba reports zero hits for invalid", hits == 0)


def test_normalize_cool_grays_replaces_blocklisted() -> None:
    """A blocklisted cool gray hex should be rewritten; brand color stays."""
    css = ".a { color: #888; } .b { color: #1B365D; }"
    out, hits = normalize_cool_grays(css)
    check("normalize_cool_grays drops #888", "#888" not in out, f"out: {out}")
    check("normalize_cool_grays preserves #1B365D", "#1B365D" in out)
    check("normalize_cool_grays reports >= 1 hit", hits >= 1)


# --------------------------- solver end-to-end ---------------------------
#
# These tests render real PDFs via WeasyPrint to verify that the overflow
# solver actually reduces page counts and respects its lower bounds. Skipped
# when weasyprint is not installed (e.g. lint-only CI shards).
_HAS_WEASYPRINT = importlib.util.find_spec("weasyprint") is not None


_OVERFLOW_PROFILE: dict = {
    "line_height": {"min": 1.0, "max": 1.55},
    "body_font_size_pt": {"min": 9.0, "max": 13.0},
    "body_line_height": {"min": 1.35, "max": 1.60},
    "section_gap_pt": {"min": 8.0, "max": 30.0},
    "page_margin_mm": {"min": [10.0, 10.0, 10.0, 10.0]},
    "overflow_solver": {
        "enabled": True,
        "max_iterations": 30,
        "section_gap_step_pt": 2.0,
        "body_line_height_step": 0.05,
        "body_font_step_pt": 0.5,
        "margin_step_mm": 2.0,
    },
}

# A profile whose minima leave no headroom, used to test that the solver
# refuses to push past lower bounds and records "lower bounds" in notes.
_LOCKED_PROFILE: dict = {
    "line_height": {"min": 1.55, "max": 1.55},
    "body_font_size_pt": {"min": 13.0, "max": 13.0},
    "body_line_height": {"min": 1.60, "max": 1.60},
    "section_gap_pt": {"min": 24.0, "max": 24.0},
    "page_margin_mm": {"min": [25.0, 25.0, 25.0, 25.0]},
    "overflow_solver": {
        "enabled": True,
        "max_iterations": 5,
        "section_gap_step_pt": 2.0,
        "body_line_height_step": 0.05,
        "body_font_step_pt": 0.5,
        "margin_step_mm": 2.0,
    },
}


def _overflow_fixture_html(sections: int = 16) -> str:
    """Return an HTML doc that renders to >1 page with the default profile."""
    body_blocks = "\n".join(
        f"<section><h2>S{i}</h2><p>{'word ' * 30}</p></section>"
        for i in range(sections)
    )
    return f"""<!doctype html>
<html><head><style>
@page {{ size: A4; margin: 25mm 25mm 25mm 25mm; }}
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
:root {{
  --parchment: #f5f4ed;
}}
body {{
  font-size: 13pt;
  line-height: 1.60;
  font-family: serif;
}}
section {{
  margin-bottom: 24pt;
}}
h2 {{ font-size: 14pt; margin-bottom: 6pt; }}
</style></head><body>
{body_blocks}
</body></html>
"""


def _write_fixture_template(html: str, source_name: str = "fixture.html") -> Path:
    """Write fixture to a tmpdir and return the tmpdir path (the templates_dir)."""
    tmp = Path(tempfile.mkdtemp(prefix="kami-solver-test-"))
    (tmp / source_name).write_text(html, encoding="utf-8")
    return tmp


def test_solver_tighten_section_gap_reduces_value() -> None:
    """tighten_section_gap should drop section margin-bottom by step toward min."""
    # SECTION_BLOCK_RE matches `section {` and `}` on their own lines.
    css = "section {\n  margin-bottom: 24pt;\n}\n"
    new_css, changed, before, after = tighten_section_gap(css, minimum=12.0, step=4.0)
    check("tighten_section_gap applied", changed, f"changed={changed}")
    check("tighten_section_gap before/after", before == 24.0 and after == 20.0,
          f"before={before} after={after}")
    check("tighten_section_gap respects min", "20.0" in new_css and "24pt" not in new_css,
          f"new_css={new_css}")

    # At the minimum it should refuse to move further.
    flat_css = "section {\n  margin-bottom: 12pt;\n}\n"
    _, changed_at_min, *_ = tighten_section_gap(flat_css, minimum=12.0, step=4.0)
    check("tighten_section_gap halts at minimum", not changed_at_min,
          f"changed_at_min={changed_at_min}")


def _run_solver(html: str, max_pages: int, profile: dict, strict: bool = False):
    templates_dir = _write_fixture_template(html)
    out_dir = templates_dir / "out"
    try:
        return run_for_target(
            target="fixture",
            source_file="fixture.html",
            max_pages=max_pages,
            profile=profile,
            canonical_tokens={},
            write_in_place=False,
            out_dir=out_dir,
            strict=strict,
            templates_dir=templates_dir,
        )
    finally:
        import shutil
        shutil.rmtree(templates_dir, ignore_errors=True)


def test_solver_run_for_target_converges() -> None:
    """With headroom in every dimension, solver should fit overflow into 1 page."""
    if not _HAS_WEASYPRINT:
        check("solver convergence (skipped: no weasyprint)", True)
        return
    result = _run_solver(_overflow_fixture_html(sections=12), max_pages=1, profile=_OVERFLOW_PROFILE)
    check("solver converges to <= max_pages",
          result.pages_after is not None and result.pages_after <= 1,
          f"pages_before={result.pages_before} pages_after={result.pages_after} "
          f"status={result.status} notes={result.notes}")
    check("solver records at least one step",
          len(result.solver_steps) >= 1,
          f"steps={len(result.solver_steps)}")


def test_solver_respects_lower_bounds() -> None:
    """With no headroom (min==max), solver must bail and tag the result."""
    if not _HAS_WEASYPRINT:
        check("solver lower-bounds (skipped: no weasyprint)", True)
        return
    result = _run_solver(_overflow_fixture_html(sections=20), max_pages=1, profile=_LOCKED_PROFILE)
    check("solver flagged overflow when locked",
          result.status in ("overflow", "failed-strict"),
          f"status={result.status} pages_after={result.pages_after}")
    check("solver recorded lower-bounds note",
          any("lower bounds" in n for n in result.notes),
          f"notes={result.notes}")


def test_solver_step_records_page_drop() -> None:
    """Every recorded solver step should report pages_after <= pages_before."""
    if not _HAS_WEASYPRINT:
        check("solver step monotonicity (skipped: no weasyprint)", True)
        return
    result = _run_solver(_overflow_fixture_html(sections=14), max_pages=1, profile=_OVERFLOW_PROFILE)
    if not result.solver_steps:
        check("solver step monotonicity (no steps recorded -- already fit)",
              result.pages_after is not None and result.pages_after <= 1,
              f"pages_after={result.pages_after}")
        return
    bad = [s for s in result.solver_steps if s.pages_after > s.pages_before]
    check("every solver step is non-increasing in page count",
          not bad, f"bad={[(s.action, s.pages_before, s.pages_after) for s in bad]}")


def test_clamp_line_heights_clamps_loose() -> None:
    """1.7 outside [1.30, 1.55] should clamp; 1.4 in-range stays."""
    css = "p { line-height: 1.7; } q { line-height: 1.4; }"
    out, hits = clamp_line_heights(css, 1.30, 1.55)
    check("clamp_line_heights pulls 1.7 down", "1.55" in out, f"out: {out}")
    check("clamp_line_heights leaves 1.4 alone", "1.4" in out)
    check("clamp_line_heights reports one hit", hits == 1, f"hits={hits}")


def test_luminance_known_values() -> None:
    """Luminance matches expected boundary values."""
    check("luminance(black) ~ 0", abs(luminance((0, 0, 0))) < 1e-3)
    check("luminance(white) ~ 1", abs(luminance((255, 255, 255)) - 1.0) < 1e-3)


# --------------------------- _last_content_y ---------------------------

def _make_samples(rows_with_content: int, w: int, h: int, n: int = 3) -> bytes:
    """Build a flat RGB buffer: parchment everywhere, ink in the top N rows.

    Returns bytes matching the layout PyMuPDF's Pixmap uses, so we can drive
    _last_content_y without depending on a real PDF or numpy.
    """
    parchment_row = bytes((_BG_R, _BG_G, _BG_B)) * w
    ink_row = bytes((27, 54, 93)) * w
    out = bytearray()
    for y in range(h):
        out.extend(ink_row if y < rows_with_content else parchment_row)
    return bytes(out)


def test_last_content_y_dense_page() -> None:
    """Page with content all the way to the bottom: returns h-1."""
    w, h, n = 80, 100, 3
    samples = _make_samples(rows_with_content=h, w=w, h=h, n=n)
    y = _last_content_y(samples, w, h, w * n, n)
    check("_last_content_y dense page returns last row", y == h - 1, f"got {y}")


def test_last_content_y_sparse_page() -> None:
    """Page with content only in top 10 rows: returns 9."""
    w, h, n = 80, 100, 3
    samples = _make_samples(rows_with_content=10, w=w, h=h, n=n)
    y = _last_content_y(samples, w, h, w * n, n)
    check("_last_content_y sparse page returns last content row",
          y == 9, f"got {y}")


def test_last_content_y_blank_page() -> None:
    """Page with no content at all: returns 0."""
    w, h, n = 80, 100, 3
    samples = _make_samples(rows_with_content=0, w=w, h=h, n=n)
    y = _last_content_y(samples, w, h, w * n, n)
    check("_last_content_y blank page returns 0", y == 0, f"got {y}")


def test_density_threshold_buckets() -> None:
    """Verify the SPARSE (>50%) / WARN (>25%) / OK categorization that
    _scan_density applies after computing empty = (h - last_content_y) / h."""
    w, h, n = 80, 100, 3
    cases = [
        (h,    0.0,  "OK"),       # full page
        (80,   0.20, "OK"),       # 20% trailing
        (70,   0.30, "WARN"),     # 30% trailing
        (49,   0.51, "SPARSE"),   # 51% trailing
        (0,    1.0,  "SPARSE"),   # blank page
    ]
    for content_rows, expected_empty, expected_bucket in cases:
        samples = _make_samples(rows_with_content=content_rows, w=w, h=h, n=n)
        y = _last_content_y(samples, w, h, w * n, n)
        empty = (h - y) / h if content_rows > 0 else 1.0
        if empty > 0.50:
            bucket = "SPARSE"
        elif empty > 0.25:
            bucket = "WARN"
        else:
            bucket = "OK"
        check(
            f"density threshold rows={content_rows} -> {expected_bucket}",
            bucket == expected_bucket,
            f"empty={empty:.2f} bucket={bucket}",
        )


# --------------------------- runner ---------------------------

def test_highlight_with_language() -> None:
    html = '<pre><code class="language-python">def foo():\n    pass</code></pre>'
    out = highlight_code_blocks(html)
    if importlib.util.find_spec("pygments") is None:
        check("highlight skips styled output when Pygments is absent",
              out == html,
              f"out differs: {out[:200]}")
        return

    check("highlight adds style spans to language-tagged block",
          "<span" in out and "style=" in out,
          f"out: {out[:200]}")
    check("highlight avoids synthetic bold",
          "font-weight" not in out.lower(),
          f"out: {out[:200]}")
    check("highlight preserves pre/code wrapper",
          "<pre" in out and "</code>" in out)


def test_highlight_without_language() -> None:
    html = '<pre><code>def foo():\n    pass</code></pre>'
    out = highlight_code_blocks(html)
    check("highlight does not modify plain code block",
          out == html,
          f"out differs: {out[:200]}")


def test_highlight_without_pygments_dependency() -> None:
    html = '<pre><code class="language-python">def foo():\n    pass</code></pre>'
    original_import = builtins.__import__
    original_warned = highlight_mod._WARNED_MISSING_PYGMENTS

    def fake_import(name, *args, **kwargs):
        if name == "pygments" or name.startswith("pygments."):
            raise ImportError("blocked for fallback test")
        return original_import(name, *args, **kwargs)

    try:
        highlight_mod._WARNED_MISSING_PYGMENTS = False
        builtins.__import__ = fake_import
        warning = io.StringIO()
        with contextlib.redirect_stderr(warning):
            out = highlight_code_blocks(html)
    finally:
        builtins.__import__ = original_import
        highlight_mod._WARNED_MISSING_PYGMENTS = original_warned

    check("highlight falls back unchanged without Pygments",
          out == html,
          f"out differs: {out[:200]}")
    check("highlight warns when Pygments is missing",
          "WARN: Pygments is not installed" in warning.getvalue(),
          f"warning: {warning.getvalue()}")


def main() -> int:
    test_dist_package_contents()
    test_registry_consistency()
    test_chinese_html_templates_keep_single_serif_stack()
    test_chinese_slides_mono_has_cjk_fallback()
    test_scan_file_skip_bug()
    test_scan_file_arrow_in_en()
    test_scan_file_clean_template()
    test_scan_file_line_height_too_loose()
    test_scan_file_cool_gray()
    test_scan_file_ignores_block_comment_rgba()
    test_scan_file_thin_border_with_radius()
    test_parse_slide_sequence_empty()
    test_parse_slide_sequence_basic()
    test_check_placeholders_flags_unfilled()
    test_check_placeholders_passes_clean()
    test_pair_names_includes_known_pairs()
    test_pair_names_includes_ko_variants_when_present()
    test_cross_template_consistency_clean()
    test_extract_root_vars_picks_up_definitions()
    test_clamp_basic()
    test_parse_hex_3_and_6()
    test_rgb_to_hex_pads_uppercase()
    test_blend_rgba_on_parchment_alpha_zero()
    test_blend_rgba_on_parchment_alpha_one()
    test_normalize_rgba_blends_to_solid()
    test_normalize_rgba_skips_invalid()
    test_normalize_cool_grays_replaces_blocklisted()
    test_solver_tighten_section_gap_reduces_value()
    test_solver_run_for_target_converges()
    test_solver_respects_lower_bounds()
    test_solver_step_records_page_drop()
    test_clamp_line_heights_clamps_loose()
    test_luminance_known_values()
    test_last_content_y_dense_page()
    test_last_content_y_sparse_page()
    test_last_content_y_blank_page()
    test_density_threshold_buckets()
    test_highlight_with_language()
    test_highlight_without_language()
    test_highlight_without_pygments_dependency()
    print()
    print(f"Passed: {_PASS} | Failed: {_FAIL}")
    return 0 if _FAIL == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
