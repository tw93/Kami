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
import inspect
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
    _density_bucket,
    _extract_root_vars,
    _last_content_y,
    _markdown_residue_issues,
    _off_palette_findings,
    _orphan_last_line,
    _pair_names,
    _parse_slide_sequence,
    _resume_balance_issues,
    _rhythm_issues,
    _root_token_findings,
    check_all,
    check_cross_template_consistency,
    check_markdown_residue,
    check_off_palette,
    check_placeholders,
    main as build_main,
    scan_file,
)
from shared import (  # noqa: E402
    DIAGRAM_TEMPLATES,
    HTML_TEMPLATES,
    PARCHMENT_RGB,
    ROOT as REPO_ROOT,
    SCREEN_TEMPLATES,
    TEMPLATES,
    build_targets,
    diagram_targets,
    load_checks_thresholds,
    screen_targets,
)
import highlight as highlight_mod  # noqa: E402
import lint as lint_mod  # noqa: E402
from highlight import highlight_code_blocks  # noqa: E402
from site_facts import (  # noqa: E402
    FULL_PUBLIC_FACT_FILES,
    REDIRECT_SITE_FILE,
    check_site_facts,
    site_fact_issues,
    site_structure_issues,
)
from tokens import _mermaid_theme_drift  # noqa: E402
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


def run_build_args(args: list[str]) -> tuple[int, str]:
    sink = io.StringIO()
    with contextlib.redirect_stdout(sink):
        rc = build_main(["build.py", *args])
    return rc, sink.getvalue()


def site_fact_file_map() -> dict[str, str]:
    rels = (*FULL_PUBLIC_FACT_FILES, REDIRECT_SITE_FILE)
    return {
        rel: (REPO_ROOT / rel).read_text(encoding="utf-8", errors="replace")
        for rel in rels
    }


# --------------------------- package archive ---------------------------

PACKAGE_MAX_BYTES = 6_000_000
PACKAGE_ROOT_NAME = "kami"
PACKAGE_FORBIDDEN_EXACT = {
    ".claude-plugin/marketplace.json",
    ".gitignore",
    "AGENTS.md",
    "CLAUDE.md",
    "README.md",
    "assets/images/1.png",
    "assets/images/2.png",
    "assets/images/3.png",
    "assets/fonts/TsangerJinKai02-W04.ttf",
    "assets/fonts/TsangerJinKai02-W05.ttf",
    "assets/fonts/SourceHanSerifKR-Regular.otf",
    "assets/fonts/SourceHanSerifKR-Medium.otf",
    "index.html",
    "index-en.html",
    "index-ja.html",
    "index-ko.html",
    "index-tw.html",
    "index-zh.html",
    "llms.txt",
    "robots.txt",
    "scripts/build_metadata.py",
    "scripts/draft-release-notes.py",
    "scripts/package-skill.sh",
    "sitemap.xml",
    "styles.css",
    "vercel.json",
}
PACKAGE_FORBIDDEN_PREFIXES = (
    ".agents/",
    ".claude/",
    ".github/",
    "assets/demos/",
    "assets/examples/",
    "assets/illustrations/",
    "assets/showcase/",
    "plugins/",
    "scripts/tests/",
)
PACKAGE_REQUIRED_ENTRIES = {
    "SKILL.md",
    "CHEATSHEET.md",
    "VERSION",
    "LICENSE",
    "assets/images/logo.svg",
    "assets/fonts/JetBrainsMono.woff2",
    "assets/templates/resume.html",
    "assets/templates/landing-page.html",
    "assets/diagrams/sequence.html",
    "references/design.md",
    "scripts/build.py",
    "scripts/ensure-fonts.sh",
    "scripts/site_facts.py",
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

    bad_root = sorted(name for name in names if not name.startswith(f"{PACKAGE_ROOT_NAME}/"))
    check("dist/kami.zip uses a Claude-friendly top-level skill folder",
          not bad_root,
          f"entries outside {PACKAGE_ROOT_NAME}/: {', '.join(bad_root)}")

    payload_names = {
        name.removeprefix(f"{PACKAGE_ROOT_NAME}/")
        for name in names
        if name.startswith(f"{PACKAGE_ROOT_NAME}/")
    }
    forbidden = sorted(
        name for name in payload_names
        if name.startswith(PACKAGE_FORBIDDEN_PREFIXES)
        or name in PACKAGE_FORBIDDEN_EXACT
    )
    check("dist/kami.zip excludes site, CI, tests, demos, generated mirrors, and large bundled fonts",
          not forbidden,
          f"forbidden entries: {', '.join(forbidden)}")
    missing_required = sorted(PACKAGE_REQUIRED_ENTRIES - payload_names)
    check("dist/kami.zip keeps required runtime skill files",
          not missing_required,
          f"missing entries: {', '.join(missing_required)}")


def test_plugin_metadata_generated() -> None:
    """Claude Code / Codex marketplaces and plugin mirrors must stay generated."""
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
    check("plugin metadata matches generator", result.returncode == 0, detail)


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
    check("Claude plugin marketplace installs the lightweight plugin directory",
          kami_plugin.get("source") == "./plugins/kami",
          f"source={kami_plugin.get('source')!r}")

    plugin_file = REPO_ROOT / "plugins" / "kami" / ".claude-plugin" / "plugin.json"
    check("Claude plugin manifest exists in generated plugin tree", plugin_file.exists())
    if not plugin_file.exists():
        return

    plugin = json.loads(plugin_file.read_text(encoding="utf-8"))
    check("Claude plugin manifest version matches VERSION",
          plugin.get("version") == version,
          f"plugin={plugin.get('version')!r}, VERSION={version!r}")
    check("Claude plugin manifest exposes skills directory",
          plugin.get("skills") == "./skills/",
          f"skills={plugin.get('skills')!r}")


def test_build_metadata_reads_tokens_from_root_argument() -> None:
    from build_metadata import build_codex_plugin, read_token_value

    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        (root / "references").mkdir()
        (root / "references" / "tokens.json").write_text('{"--brand":"#123456"}\n', encoding="utf-8")

        brand_color = read_token_value(root, "brand")
        plugin = build_codex_plugin("9.9.9", brand_color)
        check("build_metadata reads brand token from provided root",
              plugin["interface"]["brandColor"] == "#123456",
              f"brandColor={plugin['interface']['brandColor']}")


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
    check("DIAGRAM_TARGETS has 18 entries", len(DIAGRAM_TARGETS) == 18,
          f"got {len(DIAGRAM_TARGETS)}")
    check("DIAGRAM_TARGETS in build.py matches shared.diagram_targets()",
          dict(DIAGRAM_TARGETS) == diagram_targets() == dict(DIAGRAM_TEMPLATES))
    check("PPTX_TARGETS has 2 entries", len(PPTX_TARGETS) == 2,
          f"got {len(PPTX_TARGETS)}")
    check("PARCHMENT_RGB is canonical", PARCHMENT_RGB == (0xF5, 0xF4, 0xED))


def test_runner_auto_discovers_tests() -> None:
    names = [name for name, _ in _test_functions()]
    check("test runner auto-discovers Codex update command test",
          "test_check_update_uses_codex_plugin_update_command" in names)
    check("test runner auto-discovers this test",
          "test_runner_auto_discovers_tests" in names)


def test_build_cli_rejects_unexpected_flags() -> None:
    rc, out = run_build_args(["resume", "--verify"])
    check("build.py rejects flags after target",
          rc == 2 and "ERROR: unexpected argument: --verify" in out,
          out.strip())

    rc, out = run_build_args(["--check-density", "-v"])
    check("build.py rejects unknown flags for path-based checks",
          rc == 2 and "ERROR: unexpected argument: -v" in out,
          out.strip())

    rc, out = run_build_args(["--verify", "-v"])
    check("build.py rejects unknown --verify flags",
          rc == 2 and "ERROR: unexpected argument: -v" in out,
          out.strip())

    rc, out = run_build_args(["--check-markdown", "-v"])
    check("build.py rejects unknown --check-markdown flags",
          rc == 2 and "ERROR: unexpected argument: -v" in out,
          out.strip())


def test_long_doc_templates_use_rendered_toc_pages_and_chapter_headers() -> None:
    """Long-doc TOCs must use WeasyPrint target-counter, and running headers
    must follow chapter h1 titles instead of getting stuck on the TOC h2.
    """
    sources = ("long-doc.html", "long-doc-en.html", "long-doc-ko.html")
    required_ids = {
        "#ch-executive-summary",
        "#ch-background",
        "#ch-methodology",
        "#ch-conclusions",
        "#ch-appendix",
    }
    offenders: list[str] = []
    for source in sources:
        text = (TEMPLATES / source).read_text(encoding="utf-8")
        if "target-counter(attr(href), page)" not in text:
            offenders.append(f"{source}: missing target-counter")
        if ".toc-page" in text:
            offenders.append(f"{source}: still has obsolete toc-page wiring")
        missing_ids = sorted(href for href in required_ids if f'href="{href}"' not in text or f'id="{href[1:]}"' not in text)
        if missing_ids:
            offenders.append(f"{source}: missing TOC href/id pairs {missing_ids}")
        h1_block = re.search(r"(?m)^  h1\s*\{(?P<body>.*?)^  \}", text, re.S)
        if not h1_block or "string-set: section-title content();" not in h1_block.group("body"):
            offenders.append(f"{source}: h1 does not set running header")
        h2_block = re.search(r"(?m)^  h2\s*\{(?P<body>.*?)^  \}", text, re.S)
        if h2_block and "string-set:" in h2_block.group("body"):
            offenders.append(f"{source}: h2 still sets running header")

    check("long-doc templates use rendered TOC pages and chapter headers",
          not offenders,
          "; ".join(offenders))


def test_site_facts_repo_clean() -> None:
    rc = silently(check_site_facts, False)
    check("public site facts match shared constants and registries", rc == 0,
          f"check_site_facts returned {rc}")


def test_site_facts_flags_bad_diagram_count() -> None:
    files = site_fact_file_map()
    bad = files["index.html"]
    bad = bad.replace("18 inline SVG diagram types", "17 inline SVG diagram types")
    bad = bad.replace("Eighteen inline SVG diagram types", "Seventeen inline SVG diagram types")
    files["index.html"] = bad

    issues = site_fact_issues(files)
    check("public site facts flag stale diagram counts",
          any("index.html: missing diagram count 18" in issue for issue in issues),
          f"issues: {issues}")


def test_site_structure_repo_clean() -> None:
    """Locale pages match index.html's DOM skeleton (redirect script exempt)."""
    issues = site_structure_issues()
    check("locale page structure matches index.html", not issues,
          f"issues: {issues}")


def test_site_structure_flags_locale_drift() -> None:
    files = site_fact_file_map()
    files["index-zh.html"] = files["index-zh.html"].replace(
        '<h2 class="section-title">', '<h3 class="section-title">', 1)

    issues = site_structure_issues(files)
    check("locale structure check flags a drifted heading",
          any("index-zh.html: DOM skeleton drifted" in issue for issue in issues),
          f"issues: {issues}")


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
    # Guard against vacuous green: with zero -ko templates the offender loop
    # never runs and the check below would pass while enforcing nothing.
    check("Korean template set is non-empty", bool(ko_sources),
          "no -ko templates found in the registries")
    for source in ko_sources:
        text = (TEMPLATES / source).read_text(encoding="utf-8")
        for bad in _ko_stack_offenders(text):
            offenders.append(f"{source}: {bad}")

    check("Korean fallback stacks all carry Source Han Serif KR",
          not offenders,
          f"offenders: {'; '.join(offenders)}")


# ---------- sibling placeholder parity (issue #38 class) ----------

# Repeated template structures whose placeholder hints must repeat the first
# block verbatim. Hint richness degrading from block 1 to later siblings makes
# fillers (human or agent) produce degraded copy; see issue #38. Cycle length N
# means placeholders repeat in groups of N (e.g. Role/Actions/Impact rows).
_SIBLING_PARITY_SPECS = (
    ("resume*.html", r'class="proj-text">(\{\{.*?\}\})', 3),
    ("resume*.html", r'class="proj-role">(\{\{.*?\}\})', 1),
    ("resume*.html", r'class="conv-body">\s*(\{\{.*?\}\})', 1),
    ("resume*.html", r'class="os-desc">(\{\{.*?\}\})', 1),
    ("resume*.html", r'class="art-stats">(\{\{.*?\}\})', 1),
    ("portfolio*.html", r'class="project-block">\s*<h3>[^<]*</h3>\s*<p>(\{\{.*?\}\})</p>', 3),
    ("portfolio*.html", r'class="project-type">(\{\{.*?\}\})', 1),
    ("portfolio*.html", r'class="project-date">(\{\{.*?\}\})', 1),
    ("one-pager*.html", r'<li>(\{\{(?:短 bullet|Short bullet|짧은 bullet).*?\}\})</li>', 3),
    ("long-doc*.html", r'(\{\{(?:一段论述|A paragraph|한 단락 논술).*?\}\})', 1),
)


def test_sibling_placeholder_hints_stay_in_parity() -> None:
    """Same-structure sibling blocks must carry identical placeholder hints."""
    matched = 0
    offenders: list[str] = []
    for glob_pattern, regex, cycle in _SIBLING_PARITY_SPECS:
        rx = re.compile(regex, re.DOTALL)
        for path in sorted(TEMPLATES.glob(glob_pattern)):
            hits = rx.findall(path.read_text(encoding="utf-8"))
            if not hits:
                offenders.append(f"{path.name}: no match for {regex[:40]!r} (stale spec?)")
                continue
            matched += 1
            if len(hits) % cycle != 0:
                offenders.append(f"{path.name}: {len(hits)} hint(s) not divisible by cycle {cycle}")
                continue
            first = hits[:cycle]
            for start in range(cycle, len(hits), cycle):
                block = hits[start:start + cycle]
                if block != first:
                    offenders.append(
                        f"{path.name}: block {start // cycle + 1} diverges from block 1: "
                        f"{block} != {first}")
    check("sibling parity specs matched across template families", matched >= 30,
          f"only {matched} template/spec matches; spec table may be stale")
    check("repeated blocks carry identical placeholder hints", not offenders,
          "; ".join(offenders[:6]))


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


def test_root_token_findings_flags_off_palette_definition() -> None:
    """An off-palette hex *defined* in :root (never used as a literal property
    hex) escapes _off_palette_findings, which blanks :root. _root_token_findings
    closes that gap: a stray `--brand-deep: #a64f33` second accent is flagged,
    while a registered token and cool-gray (reported elsewhere) are not."""
    fixture = """<!doctype html>
<html><head><style>
:root {
  --brand: #1B365D;
  --brand-deep: #a64f33;
}
</style></head><body></body></html>
"""
    p = write_temp_html(fixture)
    try:
        findings = _root_token_findings(p, {"#1b365d"})
        rules = {f.rule for f in findings}
        excerpts = " ".join(f.excerpt for f in findings)
        check("_root_token_findings flags off-palette :root token #a64f33",
              "off-palette-token" in rules and "#a64f33" in excerpts,
              f"rules={rules or '(none)'} excerpts={excerpts or '(none)'}")
        check("_root_token_findings does not flag the registered --brand token",
              "#1b365d" not in excerpts,
              f"unexpectedly flagged brand token: {excerpts}")
    finally:
        p.unlink(missing_ok=True)


def test_off_palette_repo_clean() -> None:
    """The real editorial templates and Marp themes must stay on-palette."""
    rc = silently(check_off_palette)
    check("check_off_palette passes on the real templates",
          rc == 0,
          f"check_off_palette returned {rc}")


def test_check_off_palette_includes_marp_css() -> None:
    """The repository-level guard must scan Marp CSS, not only HTML files."""
    fixture = tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".css",
        dir=TEMPLATES / "marp",
        delete=False,
        encoding="utf-8",
    )
    fixture.write(".accent { color: #ff00aa; }\n")
    fixture.close()
    p = Path(fixture.name)
    original_iter = lint_mod.iter_template_files
    call_args: dict[str, bool] = {}

    def fake_iter_template_files(**kwargs: bool) -> list[Path]:
        call_args.update(kwargs)
        return [p]

    try:
        lint_mod.iter_template_files = fake_iter_template_files
        rc = silently(lint_mod.check_off_palette)
        check("check_off_palette requests Marp CSS targets",
              call_args == {"include_marp_css": True},
              f"iterator arguments: {call_args}")
        check("check_off_palette flags an off-palette color in Marp CSS",
              rc == 1,
              f"check_off_palette returned {rc}")
    finally:
        lint_mod.iter_template_files = original_iter
        p.unlink(missing_ok=True)


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
        check("check-update default command uses plugin bundle path",
              "npx skills add tw93/kami/plugins/kami -a universal -g -y" in out and "skills update" not in out,
              out)

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
        newer = dp / "newer"
        newer.write_text("9.9.9\n")

        roots = [
            dp / ".codex" / "plugins" / "cache" / "kami" / "kami" / "1.7.4" / "skills" / "kami",
            dp / "custom-codex-home" / "plugins" / "cache" / "kami" / "kami" / "1.7.4" / "skills" / "kami",
        ]
        for index, install_root in enumerate(roots, start=1):
            (install_root / "scripts").mkdir(parents=True)
            shutil.copy2(script, install_root / "scripts" / "check-update.sh")
            (install_root / "VERSION").write_text("1.7.4\n")

            env = dict(os.environ, XDG_CACHE_HOME=str(dp / f"cache-{index}"), KAMI_UPDATE_URL=newer.as_uri())
            result = subprocess.run(
                ["bash", str(install_root / "scripts" / "check-update.sh")],
                capture_output=True,
                text=True,
                env=env,
            )
            out = result.stdout.strip()
            check(f"check-update uses Codex plugin update command ({install_root.parent.parent.parent.name})",
                  result.returncode == 0 and "codex plugin marketplace upgrade kami" in out,
                  out)


def test_check_update_uses_claude_plugin_update_command() -> None:
    """When installed through Claude Code's plugin cache, the update hint should
    use Claude's plugin updater instead of generic npx skill install.
    """
    script = REPO_ROOT / "scripts" / "check-update.sh"
    check("check-update.sh exists for Claude command test", script.exists())
    if not script.exists():
        return
    if shutil.which("bash") is None or shutil.which("curl") is None:
        check("check-update Claude command (skipped: bash/curl unavailable)", True)
        return

    with tempfile.TemporaryDirectory() as d:
        dp = Path(d)
        newer = dp / "newer"
        newer.write_text("9.9.9\n")
        install_root = dp / ".claude" / "plugins" / "cache" / "kami" / "kami" / "1.9.1" / "skills" / "kami"
        (install_root / "scripts").mkdir(parents=True)
        shutil.copy2(script, install_root / "scripts" / "check-update.sh")
        (install_root / "VERSION").write_text("1.9.1\n")

        env = dict(os.environ, XDG_CACHE_HOME=str(dp / "cache"), KAMI_UPDATE_URL=newer.as_uri())
        result = subprocess.run(
            ["bash", str(install_root / "scripts" / "check-update.sh")],
            capture_output=True,
            text=True,
            env=env,
        )
        out = result.stdout.strip()
        check("check-update uses Claude plugin update command",
              result.returncode == 0 and "claude plugin update kami" in out and "npx skills" not in out,
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


def test_markdown_residue_flags_raw_markers() -> None:
    issues = _markdown_residue_issues("Intro\n---\nThis has **raw bold** and `raw code`.")
    check("markdown residue flags thematic breaks",
          any("thematic break" in issue for issue in issues),
          f"issues={issues}")
    check("markdown residue flags raw bold markers",
          any("bold marker" in issue for issue in issues),
          f"issues={issues}")
    check("markdown residue flags raw inline-code markers",
          any("inline-code marker" in issue for issue in issues),
          f"issues={issues}")

    check("markdown residue ignores clean text",
          _markdown_residue_issues("Clean paragraph with converted emphasis.") == [])


def test_check_markdown_residue_skips_html_code_blocks() -> None:
    dirty = write_temp_html("<html><body><p>Visible **raw bold**</p></body></html>", suffix=".html")
    clean_code = write_temp_html(
        "<html><body><p>Visible text</p><pre><code>**example** `cmd`</code></pre></body></html>",
        suffix=".html",
    )
    try:
        rc = silently(check_markdown_residue, [str(dirty)])
        check("check_markdown_residue fails visible raw markdown", rc == 1, f"rc={rc}")
        rc = silently(check_markdown_residue, [str(clean_code)])
        check("check_markdown_residue skips code/pre blocks", rc == 0, f"rc={rc}")
    finally:
        dirty.unlink(missing_ok=True)
        clean_code.unlink(missing_ok=True)


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
    # Sanity: existing CN/EN and CN/KO pairs still detected, so the sweep
    # below cannot pass vacuously on an empty or EN-only pair list.
    check("CN/EN pair still detected", ("one-pager", "one-pager-en") in captured)
    check("CN/KO pair still detected", ("one-pager", "one-pager-ko") in captured)
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
    """Drive the real `_density_bucket` seam so the SPARSE (>50%) / WARN (>25%)
    / OK categorization is asserted against production logic, not a reimplemented
    copy. A `>`->`>=` slip or a warn/sparse swap in checks.py fails here."""
    density_cfg = load_checks_thresholds()["density"]
    warn_pct = float(density_cfg["warn_pct"])
    sparse_pct = float(density_cfg["sparse_pct"])
    cases = [
        (0.0,        "OK"),      # full page
        (warn_pct,   "OK"),      # exactly at warn threshold -> not yet WARN (strict >)
        (0.30,       "WARN"),    # 30% trailing
        (sparse_pct, "WARN"),    # exactly at sparse threshold -> still WARN (strict >)
        (0.51,       "SPARSE"),  # 51% trailing
        (1.0,        "SPARSE"),  # blank page
    ]
    for empty, expected_bucket in cases:
        bucket = _density_bucket(empty, warn_pct, sparse_pct)
        check(
            f"_density_bucket empty={empty:.2f} -> {expected_bucket}",
            bucket == expected_bucket,
            f"got {bucket}",
        )


def test_rhythm_issues_rules() -> None:
    """Drive the three monotony rules in `_rhythm_issues` directly, without
    rendering a deck. Covers content-run limit, missing divider, and missing
    density-variation slide, plus the clean case."""
    max_run, min_deck = 4, 8

    healthy = [
        "title_slide", "content_slide", "content_slide", "quote_slide",
        "chapter_slide", "content_slide", "metrics_slide", "closing_slide",
    ]
    check("rhythm: balanced deck has no issues",
          _rhythm_issues(healthy, max_run, min_deck) == [],
          f"got {_rhythm_issues(healthy, max_run, min_deck)}")

    long_run = ["quote_slide"] + ["content_slide"] * (max_run + 1)
    issues = _rhythm_issues(long_run, max_run, min_deck)
    check("rhythm: over-long content run flagged",
          any("content_slide run" in i for i in issues), f"got {issues}")

    no_divider = ["title_slide"] + ["content_slide", "quote_slide"] * 5
    issues = _rhythm_issues(no_divider, max_run, min_deck)
    check("rhythm: large deck without divider flagged",
          any("no chapter_slide divider" in i for i in issues), f"got {issues}")

    no_variation = ["title_slide", "content_slide", "chapter_slide", "content_slide"]
    issues = _rhythm_issues(no_variation, max_run, min_deck)
    check("rhythm: deck without quote/metrics flagged",
          any("density variation" in i for i in issues), f"got {issues}")


def test_orphan_last_line_predicate() -> None:
    """Drive `_orphan_last_line`: a short trailing line on a multi-line block
    is an orphan; single-line blocks and long trailing lines are not."""
    max_words, max_chars = 3, 30

    orphan = "This is a full sentence that wraps\nword"
    check("orphan: short trailing line detected",
          _orphan_last_line(orphan, max_words, max_chars) == "word",
          f"got {_orphan_last_line(orphan, max_words, max_chars)!r}")

    single = "Only one line here"
    check("orphan: single-line block is not an orphan",
          _orphan_last_line(single, max_words, max_chars) is None,
          "single line flagged")

    long_tail = "First line of the block\n" + "x" * (max_chars + 5)
    check("orphan: long trailing line is not an orphan",
          _orphan_last_line(long_tail, max_words, max_chars) is None,
          "long tail flagged")

    many_words = "First line here\none two three four five"
    check("orphan: wordy trailing line is not an orphan",
          _orphan_last_line(many_words, max_words, max_chars) is None,
          "wordy tail flagged")


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


def test_mermaid_theme_matches_tokens() -> None:
    from shared import TOKENS_FILE
    canonical = json.loads(TOKENS_FILE.read_text(encoding="utf-8"))
    issues = _mermaid_theme_drift(canonical)
    check("mermaid theme colors and role docs match tokens.json",
          issues == [],
          f"issues: {issues}")


def test_mermaid_theme_drift_flags_token_mismatch() -> None:
    from shared import TOKENS_FILE
    canonical = json.loads(TOKENS_FILE.read_text(encoding="utf-8"))
    canonical["--brand"] = "#000000"
    issues = _mermaid_theme_drift(canonical)
    check("mermaid theme drift flags accent token mismatch",
          any("accent" in issue and "--brand" in issue for issue in issues),
          f"issues: {issues}")


def test_mermaid_normalize_defaults_match_theme() -> None:
    import mermaid_normalize as mermaid_mod
    theme = json.loads((REPO_ROOT / "references" / "mermaid-theme.json").read_text(encoding="utf-8"))
    expected_colors = {f"--{key}": value for key, value in theme["colors"].items()}
    check("mermaid normalizer fallback colors mirror mermaid-theme.json",
          mermaid_mod._DEFAULT_COLORS == expected_colors,
          f"default={mermaid_mod._DEFAULT_COLORS}, theme={expected_colors}")
    check("mermaid normalizer fallback font mirrors mermaid-theme.json",
          mermaid_mod._DEFAULT_FONT_STACK == theme["cssFontStack"],
          f"default={mermaid_mod._DEFAULT_FONT_STACK}, theme={theme['cssFontStack']}")


# --------------------------- mermaid normalize ---------------------------

def test_mermaid_color_mix_srgb_single_pct() -> None:
    from mermaid_normalize import _Resolver
    r = _Resolver({"--fg": "#141413", "--bg": "#f5f4ed"})
    # color-mix(in srgb, fg 12%, bg) == 0.12*fg + 0.88*bg
    got = r.hex_of("color-mix(in srgb, var(--fg) 12%, var(--bg))")
    check("color-mix(in srgb, fg 12%, bg) resolves to warm gray",
          got == "#dad9d3", f"got {got}")


def test_mermaid_color_mix_both_pct() -> None:
    from mermaid_normalize import _Resolver
    r = _Resolver({"--bg": "#ffffff", "--c": "#000000"})
    got = r.hex_of("color-mix(in srgb, var(--bg) 75%, var(--c) 25%)")
    check("color-mix honors both explicit percentages", got == "#bfbfbf", f"got {got}")


def test_mermaid_normalize_strips_unsafe_features() -> None:
    from mermaid_normalize import normalize
    # Root carries a deliberately NON-Kami theme (red accent, white bg) to prove
    # the normalizer re-themes to the Kami palette regardless of source theme.
    raw = (
        '<svg xmlns="http://www.w3.org/2000/svg" '
        'style="--bg:#ffffff;--fg:#000000;--accent:#ff0000;background:var(--bg)">'
        "<style>@import url('https://fonts.googleapis.com/css2?family=Charter');\n"
        "  text { font-family: 'Charter', system-ui, sans-serif; }\n"
        "  svg { --_t: color-mix(in srgb, var(--fg) 25%, var(--bg)); }</style>"
        '<rect fill="var(--accent)" stroke="var(--fg)"/></svg>'
    )
    out = normalize(raw)
    check("normalize removes color-mix()", "color-mix(" not in out, out)
    check("normalize removes var()", "var(" not in out, out)
    check("normalize removes google-fonts import", "googleapis" not in out, out)
    check("normalize drops the quoted single-family bug", "'Charter'" not in out, out)
    check("normalize keeps the Kami CJK serif stack", "TsangerJinKai02" in out, out)
    check("normalize resolves fill to a static hex", 'fill="#' in out, out)
    check("normalize re-themes accent to Kami ink-blue",
          "#1b365d" in out.lower(), out)
    check("normalize drops the source theme's red accent",
          "#ff0000" not in out.lower(), out)


def test_mermaid_lint_flags_unnormalized_svg() -> None:
    body = '<svg><rect fill="color-mix(in srgb, #000000 50%, #ffffff)"/></svg>'
    path = write_temp_html(body, suffix=".html")  # not a screen-template name
    try:
        rules = {f.rule for f in scan_file(path)}
        check("scan_file flags un-normalized mermaid color-mix",
              "mermaid-color-mix" in rules, f"rules={rules}")
    finally:
        path.unlink(missing_ok=True)


def test_mermaid_diagram_templates_normalized() -> None:
    for name in ("sequence.html", "class.html", "er.html"):
        path = REPO_ROOT / "assets" / "diagrams" / name
        check(f"diagram {name} exists", path.exists(), f"missing {path}")
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        check(f"{name} carries no color-mix()", "color-mix(" not in text)
        check(f"{name} carries no <foreignObject>", "<foreignObject" not in text)
        check(f"{name} carries no runtime web-font import", "googleapis" not in text)


def test_mermaid_diagrams_match_their_mmd_sources() -> None:
    """The committed diagram HTML must still carry every node/participant/entity
    label from its .mmd source. No Node regenerates these, so this guards against
    a .mmd edit that silently leaves the committed SVG stale."""
    src_dir = REPO_ROOT / "assets" / "diagrams" / "src"
    sources = sorted(src_dir.glob("*.mmd"))
    check("diagram .mmd sources present", len(sources) >= 1, f"found {len(sources)}")
    for mmd in sources:
        html_path = REPO_ROOT / "assets" / "diagrams" / f"{mmd.stem}.html"
        check(f"{mmd.stem}.html exists for {mmd.name}", html_path.exists())
        if not html_path.exists():
            continue
        labels: set[str] = set()
        for line in mmd.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            m = re.match(r"participant\s+\S+\s+as\s+(.+)", line)
            if m:
                labels.add(m.group(1).strip())
            m = re.match(r"class\s+(\w+)", line)
            if m:
                labels.add(m.group(1))
            labels.update(re.findall(r"\b([A-Z][A-Z_]{2,})\b", line))  # ER entities
        body = html_path.read_text(encoding="utf-8")
        missing = sorted(label for label in labels if label not in body)
        check(f"{mmd.stem}.html carries all {mmd.name} labels",
              not missing, f"missing labels (regenerate the diagram): {missing}")


def test_mermaid_normalize_rejects_non_beautiful_mermaid() -> None:
    """A non-beautiful-mermaid SVG (no --bg/--fg roles) must raise, not silently
    emit unresolved colors."""
    from mermaid_normalize import normalize
    raised = False
    try:
        normalize('<svg xmlns="http://www.w3.org/2000/svg"><rect fill="#000"/></svg>')
    except ValueError:
        raised = True
    check("normalize rejects input lacking --bg/--fg color roles", raised)


def test_mermaid_normalize_cli_accepts_output_before_input() -> None:
    """CLI parsing should accept both `input -o out` and `-o out input`."""
    script = REPO_ROOT / "scripts" / "mermaid_normalize.py"
    raw = (
        '<svg xmlns="http://www.w3.org/2000/svg" '
        'style="--bg:#ffffff;--fg:#000000;--accent:#ff0000">'
        '<rect fill="var(--accent)" /></svg>'
    )
    with tempfile.TemporaryDirectory() as d:
        dp = Path(d)
        src = dp / "raw.svg"
        out = dp / "clean.svg"
        src.write_text(raw, encoding="utf-8")
        result = subprocess.run(
            [sys.executable, str(script), "-o", str(out), str(src)],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )
        body = out.read_text(encoding="utf-8") if out.exists() else ""
        check("mermaid_normalize CLI supports -o before input",
              result.returncode == 0 and out.exists() and "color-mix(" not in body and "var(" not in body,
              (result.stdout + result.stderr).strip())


def test_mermaid_normalize_cli_reports_missing_input() -> None:
    """Missing input should be a concise ERROR, not a Python traceback."""
    script = REPO_ROOT / "scripts" / "mermaid_normalize.py"
    with tempfile.TemporaryDirectory() as d:
        result = subprocess.run(
            [sys.executable, str(script), str(Path(d) / "missing.svg")],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )
        combined = result.stdout + result.stderr
        check("mermaid_normalize CLI reports missing input without traceback",
              result.returncode == 1 and "ERROR:" in combined and "Traceback" not in combined,
              combined.strip())


def _test_functions():
    tests = []
    for name, func in globals().items():
        if not name.startswith("test_") or not callable(func):
            continue
        if getattr(func, "__module__", None) != __name__:
            continue
        code = getattr(func, "__code__", None)
        if code is None:
            continue
        tests.append((code.co_firstlineno, name, func))
    return [(name, func) for _, name, func in sorted(tests)]


def main() -> int:
    for name, func in _test_functions():
        signature = inspect.signature(func)
        if signature.parameters:
            params = ", ".join(signature.parameters)
            check(f"{name} has no parameters", False, f"parameters: {params}")
            continue
        func()
    print()
    print(f"Passed: {_PASS} | Failed: {_FAIL}")
    return 0 if _FAIL == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
