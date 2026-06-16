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
import json
import os
import re
import shutil
import subprocess
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
    _off_palette_findings,
    _pair_names,
    _parse_slide_sequence,
    _resume_balance_issues,
    check_all,
    check_cross_template_consistency,
    check_off_palette,
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
)
import highlight as highlight_mod  # noqa: E402
from highlight import highlight_code_blocks  # noqa: E402
from verify import RECOGNIZABLE_FALLBACK_FONT_MARKERS  # noqa: E402


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
    "assets/fonts/SourceHanSerifKR-Regular.otf",
    "assets/fonts/SourceHanSerifKR-Medium.otf",
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
        if name.startswith("assets/showcase/")
        or name.startswith("assets/demos/")
        or name in PACKAGE_FORBIDDEN_EXACT
    )
    check("dist/kami.zip excludes showcase screenshots, demos, and large bundled fonts",
          not forbidden,
          f"forbidden entries: {', '.join(forbidden)}")
    check("dist/kami.zip keeps logo.svg",
          "assets/images/logo.svg" in names)


def test_codex_plugin_metadata_generated() -> None:
    """Codex marketplace and plugin mirror must stay generated from source."""
    script = REPO_ROOT / "scripts" / "build_metadata.py"
    check("build_metadata.py exists", script.exists(), f"missing {script}")
    if not script.exists():
        return

    result = subprocess.run(
        [sys.executable, str(script), "--check"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    detail = (result.stdout + result.stderr).strip()
    check("Codex plugin metadata matches generator", result.returncode == 0, detail)


def test_claude_plugin_marketplace_version_matches_version_file() -> None:
    """Claude Code uses this version instead of falling back to a commit hash."""
    version = (REPO_ROOT / "VERSION").read_text(encoding="utf-8").strip()
    marketplace_file = REPO_ROOT / ".claude-plugin" / "marketplace.json"
    check("Claude plugin marketplace metadata exists", marketplace_file.exists())
    if not marketplace_file.exists():
        return

    marketplace = json.loads(marketplace_file.read_text(encoding="utf-8"))
    plugins = marketplace.get("plugins", [])
    kami_plugin = next((plugin for plugin in plugins if plugin.get("name") == "kami"), None)
    check("Claude plugin marketplace includes kami", kami_plugin is not None)
    if not kami_plugin:
        return

    check("Claude plugin marketplace version matches VERSION",
          kami_plugin.get("version") == version,
          f"marketplace={kami_plugin.get('version')!r}, VERSION={version!r}")


# --------------------------- shared registry ---------------------------

def test_registry_consistency() -> None:
    check("HTML_TEMPLATES has 24 entries", len(HTML_TEMPLATES) == 24,
          f"got {len(HTML_TEMPLATES)}")
    check("SCREEN_TARGETS has 3 entries", len(SCREEN_TARGETS) == 3,
          f"got {len(SCREEN_TARGETS)}")
    check("build_targets matches HTML_TEMPLATES key set",
          set(build_targets()) == set(HTML_TEMPLATES))
    check("screen_targets matches SCREEN_TARGETS key set",
          set(screen_targets()) == set(SCREEN_TARGETS))
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


def _ko_stack_offenders(text: str) -> list[str]:
    """Return CSS declarations that reference the bare `"Source Han Serif K"`
    family inside a multi-name fallback stack but omit the real OTF family
    name `"Source Han Serif KR"`.

    The bare name `"Source Han Serif K"` is legitimate on its own only as the
    `@font-face` declared alias (a single-name `font-family: "Source Han Serif K";`
    with no comma, which loads via the file/CDN `src`). Anywhere it appears as a
    fallback item in a comma-separated stack (`--serif`, `--mono`, `@page`
    margin boxes, `code`/`pre`, ...), `"Source Han Serif KR"` MUST sit alongside
    it, or an offline Linux skill install cannot resolve the
    ensure-fonts.sh-downloaded font by name.

    Detection: scan only `font-family` / `--serif` / `--sans` / `--mono`
    declaration values (up to the next `;`, never crossing `{`/`}`). The token
    `"Source Han Serif K"` (closing quote after `K`) never matches
    `"Source Han Serif KR"`, so a value that contains the bare token AND a comma
    (i.e. a fallback stack, not a bare `@font-face` alias) must also contain KR.
    """
    bare = '"Source Han Serif K"'
    kr = '"Source Han Serif KR"'
    decl_re = re.compile(r"(?:font-family|--serif|--sans|--mono)\s*:\s*([^;{}]*)", re.IGNORECASE)
    offenders: list[str] = []
    for m in decl_re.finditer(text):
        value = m.group(1)
        if bare in value and "," in value and kr not in value:
            offenders.append(" ".join(value.split()))
    return offenders


def test_korean_templates_carry_resolvable_serif_name() -> None:
    """Every KO fallback stack that names `Source Han Serif K` must also name
    `Source Han Serif KR` (the actual family of the bundled OTFs), so the font
    resolves by name on an offline Linux skill install. Checks per-declaration,
    not just per-file, so a complete `--serif` cannot mask an incomplete local
    stack (page-margin header/footer, code/pre, mono).
    """
    offenders: list[str] = []
    ko_sources = [spec.source for name, spec in HTML_TEMPLATES.items() if name.endswith("-ko")]
    ko_sources += [source for name, source in SCREEN_TEMPLATES.items() if name.endswith("-ko")]
    for source in ko_sources:
        text = (TEMPLATES / source).read_text(encoding="utf-8")
        for bad in _ko_stack_offenders(text):
            offenders.append(f"{source}: {bad}")

    check("Korean fallback stacks all carry Source Han Serif KR",
          not offenders,
          f"offenders: {'; '.join(offenders)}")


def test_font_fallback_markers_recognize_pt_serif() -> None:
    """macOS without Charter may render English fallbacks as PT Serif."""
    embedded = {"DROIWJ+PT-Serif", "ZBEAAE+JetBrains-Mono"}
    fallback_present = any(
        marker in font for font in embedded
        for marker in RECOGNIZABLE_FALLBACK_FONT_MARKERS
    )
    check("font fallback markers recognize PT-Serif",
          fallback_present,
          f"markers: {RECOGNIZABLE_FALLBACK_FONT_MARKERS}")


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


def test_off_palette_flags_non_token_hex() -> None:
    """A non-token, non-cool-gray hex in a component rule is off-palette."""
    fixture = """<!doctype html>
<html><head><style>
.x { color: #ff00aa; }
</style></head><body></body></html>
"""
    p = write_temp_html(fixture)
    try:
        findings = _off_palette_findings(p, {"#1b365d"})
        rules = {f.rule for f in findings}
        check("_off_palette_findings flags non-token hex #ff00aa",
              "off-palette" in rules,
              f"rules found: {rules or '(none)'}")
    finally:
        p.unlink(missing_ok=True)


def test_off_palette_ignores_root_and_svg() -> None:
    """Hex inside :root token defs and inside <svg> blocks must be skipped."""
    fixture = """<!doctype html>
<html><head><style>
:root { --brand: #1B365D; --accent: #ff00aa; }
</style></head><body>
<svg viewBox="0 0 10 10"><rect fill="#ff0000" /></svg>
</body></html>
"""
    p = write_temp_html(fixture)
    try:
        findings = _off_palette_findings(p, {"#1b365d"})
        check("_off_palette_findings skips :root defs and <svg> fills",
              findings == [],
              f"unexpected findings: {[(f.line, f.excerpt) for f in findings]}")
    finally:
        p.unlink(missing_ok=True)


def test_off_palette_repo_clean() -> None:
    """The real editorial templates must carry no off-palette colors."""
    rc = silently(check_off_palette)
    check("check_off_palette passes on the real templates",
          rc == 0,
          f"check_off_palette returned {rc}")


def test_check_update_script() -> None:
    """check-update.sh notifies on a newer remote, stays silent when current,
    throttles to once per day, and fails silently offline. It only reads a
    version file and sends no data; KAMI_UPDATE_URL points it at a fixture."""
    script = REPO_ROOT / "scripts" / "check-update.sh"
    check("check-update.sh exists", script.exists())
    if not script.exists():
        return
    if shutil.which("bash") is None or shutil.which("curl") is None:
        check("check-update.sh behavior (skipped: bash/curl unavailable)", True)
        return
    local_ver = (REPO_ROOT / "VERSION").read_text(encoding="utf-8").strip()

    def run(cache: str, url: str) -> tuple[int, str]:
        env = dict(os.environ, XDG_CACHE_HOME=cache, KAMI_UPDATE_URL=url)
        r = subprocess.run(["bash", str(script)], capture_output=True, text=True, env=env)
        return r.returncode, r.stdout.strip()

    with tempfile.TemporaryDirectory() as d:
        dp = Path(d)
        newer = dp / "newer"; newer.write_text("9.9.9\n")
        same = dp / "same"; same.write_text(local_ver + "\n")

        rc, out = run(str(dp / "c1"), newer.as_uri())
        check("check-update notifies on a newer remote", rc == 0 and "9.9.9" in out, out)

        rc, out = run(str(dp / "c2"), same.as_uri())
        check("check-update is silent when current", rc == 0 and out == "", out)

        c3 = str(dp / "c3")
        run(c3, newer.as_uri())
        _, out2 = run(c3, newer.as_uri())
        check("check-update throttles to once per day", out2 == "", out2)

        rc, out = run(str(dp / "c4"), (dp / "nope").as_uri())
        check("check-update fails silently when offline", rc == 0 and out == "", out)


def test_check_update_uses_codex_plugin_update_command() -> None:
    """When installed through Codex plugin cache, the update hint should use
    plugin marketplace refresh commands instead of the legacy npx skill update.
    """
    script = REPO_ROOT / "scripts" / "check-update.sh"
    check("check-update.sh exists for Codex command test", script.exists())
    if not script.exists():
        return
    if shutil.which("bash") is None or shutil.which("curl") is None:
        check("check-update Codex command (skipped: bash/curl unavailable)", True)
        return

    with tempfile.TemporaryDirectory() as d:
        dp = Path(d)
        install_root = (
            dp / ".codex" / "plugins" / "cache" / "kami" / "kami" / "1.7.4" / "skills" / "kami"
        )
        (install_root / "scripts").mkdir(parents=True)
        shutil.copy2(script, install_root / "scripts" / "check-update.sh")
        (install_root / "VERSION").write_text("1.7.4\n")
        newer = dp / "newer"
        newer.write_text("9.9.9\n")

        env = dict(os.environ, XDG_CACHE_HOME=str(dp / "cache"), KAMI_UPDATE_URL=newer.as_uri())
        result = subprocess.run(
            ["bash", str(install_root / "scripts" / "check-update.sh")],
            capture_output=True,
            text=True,
            env=env,
        )
        out = result.stdout.strip()
        check("check-update uses Codex plugin update command",
              result.returncode == 0 and "codex plugin marketplace upgrade kami" in out,
              out)


def test_lint_repo_clean() -> None:
    """The full CSS lint (scan_file across every template) must pass. This is
    what `build.py --check` runs; covering it here means a rule violation such
    as thin-border-radius cannot reach main behind an otherwise green suite."""
    rc = silently(check_all, False)
    check("check_all (full CSS lint) passes on the real templates",
          rc == 0,
          f"check_all returned {rc}")


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


# --------------------------- cross-template consistency ---------------------------

def test_pair_names_includes_known_pairs() -> None:
    captured = list(_pair_names())
    check("pair_names includes one-pager",
          ("one-pager", "one-pager-en") in captured,
          f"got {[v for b, v in captured if b == 'one-pager']!r}")
    check("pair_names includes landing-page (CN/EN)",
          ("landing-page", "landing-page-en") in captured,
          f"got {[v for b, v in captured if b == 'landing-page']!r}")
    check("pair_names omits lone -en entries",
          not any(name.endswith("-en") for name, _ in _pair_names()))


def test_pair_names_includes_ko_variants_when_present() -> None:
    """`_pair_names` must yield (base, base-ko) pairs in addition to (base, base-en)."""
    captured = list(_pair_names())
    # Sanity: existing CN/EN pairs still detected.
    check("CN/EN pair still detected", ("one-pager", "one-pager-en") in captured)
    # Any base whose `-ko` sibling is registered must appear as a (base, base-ko) pair.
    bases = {base for base, _ in captured}
    seen = set(HTML_TEMPLATES) | set(SCREEN_TEMPLATES)
    missing = [
        base for base in bases
        if f"{base}-ko" in seen and (base, f"{base}-ko") not in captured
    ]
    check("pair_names includes ko variants when present", not missing,
          f"unpaired KO bases: {missing}")


def test_cross_template_consistency_clean() -> None:
    """The current repo should pass cross-template consistency."""
    rc = silently(check_cross_template_consistency, False)
    check("cross-template returns 0 on current repo", rc == 0, f"rc={rc}")


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


def test_resume_balance_issues() -> None:
    min_fill, max_fill, max_gap = 0.83, 0.95, 0.12
    check("resume balance accepts two filled pages",
          _resume_balance_issues([0.88, 0.92], 2, min_fill, max_fill, max_gap) == [])

    issues = _resume_balance_issues([0.92, 0.74], 2, min_fill, max_fill, max_gap)
    check("resume balance flags low second page",
          any("p2 fill" in issue for issue in issues),
          f"issues={issues}")
    check("resume balance flags page gap",
          any("gap" in issue for issue in issues),
          f"issues={issues}")

    issues = _resume_balance_issues([0.90, 0.89, 0.50], 3, min_fill, max_fill, max_gap)
    check("resume balance requires two pages",
          any("expected 2" in issue for issue in issues),
          f"issues={issues}")


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


def test_marp_themes_token_synced() -> None:
    """Marp theme CSS keeps its :root tokens in sync with tokens.json.

    Locks the invariant AGENTS.md documents (tokens.py globs marp/*.css), so the
    Marp decks cannot silently drift even if that glob is later refactored away.
    """
    from shared import TOKENS_FILE
    from tokens import CSS_VAR, ROOT_BLOCK

    canonical = {k.lstrip("-"): v.strip().lower()
                 for k, v in json.loads(TOKENS_FILE.read_text(encoding="utf-8")).items()}
    marp_files = sorted((TEMPLATES / "marp").glob("*.css"))
    check("marp theme CSS present", len(marp_files) >= 1, f"found {len(marp_files)} file(s)")

    drift: list[str] = []
    checked = 0
    for path in marp_files:
        block = ROOT_BLOCK.search(path.read_text(encoding="utf-8", errors="replace"))
        if not block:
            continue
        checked += 1
        found = {m.group(1): m.group(2).strip().lower()
                 for m in CSS_VAR.finditer(block.group(1))}
        for name, expected in canonical.items():
            actual = found.get(name)
            if actual is not None and actual != expected:
                drift.append(f"{path.name}: --{name} expected {expected}, got {actual}")
    check("marp theme :root tokens match tokens.json",
          checked >= 1 and not drift,
          "; ".join(drift) if drift else f"checked {checked}, no :root block found")


def main() -> int:
    test_dist_package_contents()
    test_codex_plugin_metadata_generated()
    test_claude_plugin_marketplace_version_matches_version_file()
    test_registry_consistency()
    test_chinese_html_templates_keep_single_serif_stack()
    test_korean_templates_carry_resolvable_serif_name()
    test_font_fallback_markers_recognize_pt_serif()
    test_chinese_slides_mono_has_cjk_fallback()
    test_scan_file_skip_bug()
    test_scan_file_arrow_in_en()
    test_scan_file_clean_template()
    test_scan_file_line_height_too_loose()
    test_scan_file_cool_gray()
    test_off_palette_flags_non_token_hex()
    test_off_palette_ignores_root_and_svg()
    test_off_palette_repo_clean()
    test_lint_repo_clean()
    test_check_update_script()
    test_scan_file_ignores_block_comment_rgba()
    test_scan_file_thin_border_with_radius()
    test_parse_slide_sequence_empty()
    test_parse_slide_sequence_basic()
    test_check_placeholders_flags_unfilled()
    test_check_placeholders_passes_clean()
    test_pair_names_includes_known_pairs()
    test_pair_names_includes_ko_variants_when_present()
    test_cross_template_consistency_clean()
    test_marp_themes_token_synced()
    test_extract_root_vars_picks_up_definitions()
    test_last_content_y_dense_page()
    test_last_content_y_sparse_page()
    test_last_content_y_blank_page()
    test_density_threshold_buckets()
    test_resume_balance_issues()
    test_highlight_with_language()
    test_highlight_without_language()
    test_highlight_without_pygments_dependency()
    print()
    print(f"Passed: {_PASS} | Failed: {_FAIL}")
    return 0 if _FAIL == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
