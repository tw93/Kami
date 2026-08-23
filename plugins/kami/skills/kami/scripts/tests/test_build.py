#!/usr/bin/env python3
"""Lightweight tests for scripts/build.py and scripts/shared.py.

Run with: python3 scripts/tests/test_build.py
The harness uses plain assertions and a tiny runner so it has no third-party
dependency (matching the rest of the repo's lean tooling).
"""
from __future__ import annotations

import contextlib
import builtins
import hashlib
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
import warnings
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
    main as build_main,
)
from checks import (  # noqa: E402
    _BG_B,
    _BG_G,
    _BG_R,
    _density_bucket,
    _last_content_y,
    _markdown_residue_issues,
    _orphan_last_line,
    _parse_slide_sequence,
    _resume_balance_issues,
    _rhythm_issues,
    check_markdown_residue,
    check_placeholders,
    scan_density,
)
from lint import (  # noqa: E402
    NEGATIVE_EXAMPLE_LINE,
    _blank_block,
    _documented_snippets,
    _emphasis_container_findings,
    _extract_root_vars,
    _off_palette_findings,
    _pair_names,
    _root_token_findings,
    _undefined_token_findings,
    check_all,
    check_cross_template_consistency,
    check_off_palette,
    scan_file,
    scan_text,
)
from optional_deps import MissingDepError, require_pymupdf  # noqa: E402
from shared import (  # noqa: E402
    DIAGRAM_TEMPLATES,
    HTML_TEMPLATES,
    MARP_TEMPLATES,
    PARCHMENT_RGB,
    ROOT as REPO_ROOT,
    SCREEN_TEMPLATES,
    TEMPLATES,
    build_targets,
    diagram_targets,
    load_checks_thresholds,
    marp_targets,
    pptx_targets,
    screen_targets,
)
import highlight as highlight_mod  # noqa: E402
from highlight import highlight_code_blocks  # noqa: E402
from site_facts import (  # noqa: E402
    FULL_PUBLIC_FACT_FILES,
    REDIRECT_SITE_FILE,
    check_site_facts,
    site_fact_issues,
    site_structure_issues,
)
from tokens import _mermaid_theme_drift  # noqa: E402
from verify import (  # noqa: E402
    RECOGNIZABLE_FALLBACK_FONT_MARKERS,
    _classify_cjk_font,
    _font_family_key,
)


# --------------------------- helpers ---------------------------

_PASS = 0
_FAIL = 0
_SKIP = 0


def check(name: str, predicate: bool, detail: str = "") -> None:
    global _PASS, _FAIL
    if predicate:
        _PASS += 1
        print(f"OK: {name}")
    else:
        _FAIL += 1
        print(f"ERROR: {name}{(' - ' + detail) if detail else ''}")


def skip(name: str, detail: str = "", *, ci_required: bool = False) -> None:
    """Record an unavailable optional-dependency test without calling it a pass."""
    global _SKIP, _FAIL
    _SKIP += 1
    if ci_required and os.environ.get("CI"):
        _FAIL += 1
        print(f"ERROR: required CI test skipped: {name}{(' - ' + detail) if detail else ''}")
    else:
        print(f"SKIP: {name}{(' - ' + detail) if detail else ''}")


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

    # Structure alone cannot tell a current package from a stale one. The
    # plugin mirror has `build_metadata.py --check`; the ZIP had no equivalent,
    # so editing a source file and forgetting `package-skill.sh` left every
    # check green while the archive Claude Desktop users download stayed on the
    # old content. Compare what is inside against what it was built from.
    stale: list[str] = []
    absent: list[str] = []
    with zipfile.ZipFile(archive) as zf:
        for name in zf.namelist():
            if name.endswith("/"):
                continue
            source = REPO_ROOT / name.removeprefix(f"{PACKAGE_ROOT_NAME}/")
            if not source.exists():
                absent.append(name)
                continue
            if hashlib.sha256(zf.read(name)).digest() != hashlib.sha256(source.read_bytes()).digest():
                stale.append(name)
    check("dist/kami.zip matches the sources it was built from",
          not stale,
          f"{len(stale)} stale entr(ies): {', '.join(sorted(stale)[:5])}"
          " -- run `bash scripts/package-skill.sh`")
    check("dist/kami.zip carries no entry missing from the repo",
          not absent,
          f"entries with no source: {', '.join(sorted(absent)[:5])}")


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
    check("PPTX_TARGETS in build.py matches shared.pptx_targets()",
          dict(PPTX_TARGETS) == pptx_targets())
    check("Marp registry maps authoring entries with matching CSS",
          marp_targets() == MARP_TEMPLATES
          and all(
              (TEMPLATES / source).exists()
              and (TEMPLATES / source).with_suffix(".css").exists()
              for source in MARP_TEMPLATES.values()
          ),
          str(MARP_TEMPLATES))
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


def test_brand_left_rule_uses_one_of_three_weights() -> None:
    """The brand left rule is one gesture at three weights, picked by role.

    design.md «The brand left rule» assigns 2.5pt to a structural divide, 2pt
    to an aside, and 1.4pt to the edge of a filled block. A fourth value is not
    a new idea, it is drift: the same `.callout` shipping at 1.8pt in one-pager
    and 2pt in long-doc is what teaches a reader of these templates that the
    number is theirs to pick, and inventing rules is exactly the drift the
    generated documents show.
    """
    allowed = {"2.5", "2", "1.4"}
    pattern = re.compile(r"border-left:\s*([\d.]+)pt solid var\(--brand\)")
    offenders: list[str] = []
    for path in sorted(TEMPLATES.glob("*.html")):
        for weight in pattern.findall(path.read_text(encoding="utf-8")):
            if weight not in allowed:
                offenders.append(f"{path.name}: {weight}pt")
    check("brand left rule uses one of the three registered weights",
          not offenders,
          f"offenders: {', '.join(offenders)}")


def test_documented_snippets_answer_to_template_rules() -> None:
    """A doc snippet is copied more readily than a template is read.

    CHEATSHEET.md shipped a `.card` recipe pairing a 0.5pt border with an 8pt
    radius (the double-ring pitfall templates are failed for) against
    `--border-cream`, a token that no longer exists anywhere. Both survived
    because nothing scanned the docs.
    """
    bad = """```css
.card {
  background: var(--ivory);
  border: 0.5pt solid var(--border-cream);
  border-radius: 8pt;
}
```
"""
    p = write_temp_html(bad, suffix=".md")
    try:
        rules = set()
        for line_offset, snippet in _documented_snippets(p.read_text(encoding="utf-8")):
            rules |= {f.rule for f in scan_text(snippet, p, line_offset)}
            rules |= {f.rule for f in _undefined_token_findings(p, snippet, line_offset, {"--ivory"})}
        check("doc snippet scan catches the thin-border-radius recipe",
              "thin-border-radius" in rules, f"rules: {rules or '(none)'}")
        check("doc snippet scan catches a var() with no definition",
              "undefined-token" in rules, f"rules: {rules or '(none)'}")
    finally:
        p.unlink(missing_ok=True)


def test_documented_snippets_skip_tagged_counter_examples() -> None:
    """Docs teach by contrast; the line tagged `/* avoid */` is the lesson."""
    contrast = """```css
/* avoid */ .tag { background: rgba(27, 54, 93, 0.18); }
/* use   */ .tag { background: var(--tag-bg); }
```
"""
    p = write_temp_html(contrast, suffix=".md")
    try:
        rules = set()
        for line_offset, raw in _documented_snippets(p.read_text(encoding="utf-8")):
            rules |= {f.rule for f in scan_text(_blank_block(raw, NEGATIVE_EXAMPLE_LINE), p, line_offset)}
        check("a line tagged as the wrong way is not reported as a violation",
              "rgba-background" not in rules, f"rules: {rules or '(none)'}")
    finally:
        p.unlink(missing_ok=True)


def test_font_family_key_collapses_weight_variants() -> None:
    """One family at two weights must not read as two typefaces.

    Bold CJK body text is a separate BaseFont entry (TsangerJinKai02 plus
    TsangerJinKai02-Medium, or the W04/W05 pair). Without collapsing, the
    mixed-family rule would fail every correctly rendered bilingual document.
    """
    pairs = [
        ("TsangerJinKai02", "TsangerJinKai02-Medium"),
        ("TsangerJinKai02-W04", "TsangerJinKai02-W05"),
        ("Source-Han-Serif-K", "Source-Han-Serif-K-Mediu"),
        ("NotoSerifCJKsc-Regular", "NotoSerifCJKsc-Bold"),
    ]
    offenders = [f"{a} != {b}" for a, b in pairs if _font_family_key(a) != _font_family_key(b)]
    check("font family key collapses weight variants",
          not offenders,
          f"offenders: {', '.join(offenders)}")
    check("font family key still separates real families",
          _font_family_key("Songti-SC") != _font_family_key("Hiragino-Mincho-ProN-Lig"))


def test_classify_cjk_font_separates_serif_from_the_rest() -> None:
    """The gate exists because a sans substitution shows no fallback boxes.

    A missing CJK serif is invisible to an eyeball pass: the page still reads,
    just with the wrong stroke density against metrics tuned for serif. The
    classifier is what turns that into a failure.
    """
    cases = {
        "ABCDEF+TsangerJinKai02-W04": "primary",
        "Songti-SC": "serif",
        "NotoSerifCJKsc-Regular": "serif",
        "Noto Serif CJK SC": "serif",
        "PingFang-SC": "other",
        "NotoSansCJKsc-Regular": "other",
        "SourceHanSansSC-Regular": "other",
    }
    offenders = [
        f"{name} -> {_classify_cjk_font(name)} (want {want})"
        for name, want in cases.items()
        if _classify_cjk_font(name) != want
    ]
    check("CJK font classifier separates primary and serif from everything else",
          not offenders,
          f"offenders: {', '.join(offenders)}")


def test_emphasis_container_mix_counts_distinct_fills() -> None:
    """Drift is several emphasis languages on a page, not one used repeatedly.

    Templates reuse a single fill across several raised components, which must
    stay clean. A generated document that invents a white rounded card for one
    passage and a tinted rounded block for the next must fail.
    """
    one_fill = """<!doctype html>
<html><head><style>
:root { --ivory: #faf9f5; --brand: #1B365D; }
.callout { background: var(--ivory); border-radius: 3pt; padding: 10pt; }
.takeaway { background: #faf9f5; border-radius: 4pt; padding: 10pt; }
.role { background: #E4ECF5; border-radius: 2pt; padding: 1pt 5pt; float: right; }
</style></head><body></body></html>
"""
    two_fills = """<!doctype html>
<html><head><style>
:root { --ivory: #faf9f5; --tag-bg: #E4ECF5; }
.qa-card { background: var(--ivory); border-radius: 8pt; padding: 10pt 14pt; }
.boundary { background: var(--tag-bg); border-radius: 6pt; padding: 8pt 12pt; }
</style></head><body></body></html>
"""
    clean = write_temp_html(one_fill)
    drifted = write_temp_html(two_fills)
    try:
        check("one emphasis fill (plus an inline chip) is not drift",
              not _emphasis_container_findings(clean),
              f"findings: {[f.excerpt for f in _emphasis_container_findings(clean)]}")
        found = _emphasis_container_findings(drifted)
        check("two different emphasis fills are flagged",
              len(found) == 1 and found[0].rule == "emphasis-container-mix",
              f"findings: {[f.rule for f in found] or '(none)'}")
    finally:
        clean.unlink(missing_ok=True)
        drifted.unlink(missing_ok=True)


def test_density_scans_the_only_page_of_a_single_page_pdf() -> None:
    """Page 1 is cover-exempt, which left one-page documents wholly unscanned.

    one-pager and letter render to a single page, so the cover exemption meant
    the only layout gate that reads a rendered page never looked at them.

    The fixture is built here rather than read from assets/examples, which is
    gitignored build output: pointing a test at it passes locally and fails on
    a fresh checkout. Synthesising the page also pins the expected verdict,
    since the emptiness ratio is chosen rather than inherited from whatever the
    template currently renders.
    """
    try:
        fitz = require_pymupdf()
    except MissingDepError as exc:
        skip("single-page density regression", str(exc), ci_required=True)
        return

    with tempfile.TemporaryDirectory() as tmp:
        single = Path(tmp) / "one-page.pdf"
        doc = fitz.open()
        page = doc.new_page(width=595, height=842)  # A4 in points
        parchment = tuple(channel / 255 for channel in PARCHMENT_RGB)
        page.draw_rect(fitz.Rect(0, 0, 595, 842), color=parchment, fill=parchment)
        # Ink across the top third only, leaving ~64% trailing whitespace: past
        # the sparse threshold, so a scanned page must be reported.
        page.draw_rect(fitz.Rect(50, 50, 545, 300), color=(0.1, 0.1, 0.1), fill=(0.1, 0.1, 0.1))
        doc.save(str(single))
        doc.close()

        default_scan = silently(scan_density, [str(single)])
        explicit_scan = silently(scan_density, [str(single)], scan_single_page=True)

    if default_scan is None or explicit_scan is None:
        return
    check("single-page PDF is exempt in the repo-wide sweep",
          sum(default_scan[:2]) == 0,
          f"scan: {default_scan}")
    check("single-page PDF is scanned when passed explicitly",
          sum(explicit_scan[:2]) > 0,
          f"scan: {explicit_scan} (fixture leaves ~64% of the page empty)")


def test_ci_required_skip_is_a_failure_not_a_pass() -> None:
    """A missing heavy dependency in CI must turn the suite red."""
    global _FAIL, _SKIP
    original_fail, original_skip = _FAIL, _SKIP
    original_ci = os.environ.get("CI")
    try:
        os.environ["CI"] = "1"
        silently(skip, "negative-control fixture", ci_required=True)
        rejected = _FAIL == original_fail + 1 and _SKIP == original_skip + 1
    finally:
        _FAIL, _SKIP = original_fail, original_skip
        if original_ci is None:
            os.environ.pop("CI", None)
        else:
            os.environ["CI"] = original_ci
    check("CI-required skip increments failure and skip counters", rejected)


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
    """The real editorial templates must carry no off-palette colors."""
    rc = silently(check_off_palette)
    check("check_off_palette passes on the real templates",
          rc == 0,
          f"check_off_palette returned {rc}")


def test_check_update_script() -> None:
    """check-update.sh notifies on a newer remote, stays silent when current,
    throttles through a local cache marker, and fails silently offline. It GETs
    only a version file and uploads no document/task content; KAMI_UPDATE_URL
    points it at a fixture."""
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

        no_home_env = dict(os.environ, KAMI_UPDATE_URL=newer.as_uri())
        no_home_env.pop("HOME", None)
        no_home_env.pop("XDG_CACHE_HOME", None)
        result = subprocess.run(
            ["bash", str(script)], capture_output=True, text=True, env=no_home_env)
        check("check-update is silent without a cache home",
              result.returncode == 0 and result.stdout == "" and result.stderr == "",
              result.stdout + result.stderr)

        unwritable_cache_env = dict(
            os.environ,
            XDG_CACHE_HOME="/dev/null",
            KAMI_UPDATE_URL=newer.as_uri(),
        )
        result = subprocess.run(
            ["bash", str(script)], capture_output=True, text=True, env=unwritable_cache_env)
        check("check-update is silent when the cache root is unusable",
              result.returncode == 0 and result.stdout == "" and result.stderr == "",
              result.stdout + result.stderr)


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

    issues = _markdown_residue_issues("A claim\u2014with an em dash.\n中文\u2014\u2014双破折号。")
    check("markdown residue flags em dashes",
          sum("em dash" in issue for issue in issues) == 2,
          f"issues={issues}")
    check("markdown residue allows en dash and hyphen",
          _markdown_residue_issues("Ranges use 2019-2024 and 3–5 items.") == [])


def test_check_markdown_residue_skips_html_code_blocks() -> None:
    dirty = write_temp_html("<html><body><p>Visible **raw bold**</p></body></html>", suffix=".html")
    clean_code = write_temp_html(
        "<html><body><p>Visible text</p><pre><code>**example** `cmd`</code></pre></body></html>",
        suffix=".html",
    )
    ambiguous_css = write_temp_html(
        '<html><head><link rel="stylesheet" href="theme.css"></head>'
        '<body><p>Visible **raw despite CSS uncertainty**</p></body></html>',
        suffix=".html",
    )
    try:
        rc = silently(check_markdown_residue, [str(dirty)])
        check("check_markdown_residue fails visible raw markdown", rc == 1, f"rc={rc}")
        rc = silently(check_markdown_residue, [str(clean_code)])
        check("check_markdown_residue skips code/pre blocks", rc == 0, f"rc={rc}")
        rc = silently(check_markdown_residue, [str(ambiguous_css)])
        check("markdown residue includes text under ambiguous CSS",
              rc == 1, f"rc={rc}")
    finally:
        dirty.unlink(missing_ok=True)
        clean_code.unlink(missing_ok=True)
        ambiguous_css.unlink(missing_ok=True)


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


def test_render_pdf_preserves_last_good_output_on_post_render_failure() -> None:
    """A failed metadata/page validation must not replace the prior PDF."""
    import render as render_mod

    class FakeHTML:
        def __init__(self, **_kwargs):
            pass

        def write_pdf(self, path: str) -> None:
            Path(path).write_bytes(b"new-candidate")

    original_html = render_mod.require_weasyprint_html
    original_reader = render_mod.require_pypdf_reader
    original_metadata = render_mod.set_pdf_metadata
    try:
        render_mod.require_weasyprint_html = lambda: FakeHTML
        render_mod.require_pypdf_reader = lambda: object

        def fail_metadata(*_args, **_kwargs) -> None:
            raise RuntimeError("injected metadata failure")

        render_mod.set_pdf_metadata = fail_metadata
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            src = root / "source.html"
            out = root / "output.pdf"
            src.write_text("<html><body>candidate</body></html>", encoding="utf-8")
            out.write_bytes(b"last-good")
            try:
                render_mod.render_pdf(src, out)
            except RuntimeError as exc:
                failed = "metadata failure" in str(exc)
            else:
                failed = False
            staged = list(root.glob(".output.pdf-*"))
            check("render failure preserves the last good PDF",
                  failed and out.read_bytes() == b"last-good",
                  f"failed={failed} bytes={out.read_bytes()!r}")
            check("render failure cleans staged candidates", staged == [], str(staged))
    finally:
        render_mod.require_weasyprint_html = original_html
        render_mod.require_pypdf_reader = original_reader
        render_mod.set_pdf_metadata = original_metadata


def test_release_gate_rejects_identity_mismatches() -> None:
    from release_gate import release_identity_issues

    good = release_identity_issues("V1.2.3", "1.2.3", "same", "same")
    wrong_tag = release_identity_issues("V1.2.4", "1.2.3", "same", "same")
    wrong_sha = release_identity_issues("V1.2.3", "1.2.3", "head", "tag")
    check("release identity accepts an exact tag, version, and SHA", good == [], str(good))
    check("release identity rejects a tag/version mismatch",
          any("does not match VERSION" in issue for issue in wrong_tag), str(wrong_tag))
    check("release identity rejects a tag/checkout SHA mismatch",
          any("does not match checkout HEAD" in issue for issue in wrong_sha), str(wrong_sha))


def test_release_gate_resolves_only_the_tag_namespace() -> None:
    import release_gate as release_gate_mod

    calls = []
    original_git = release_gate_mod._git
    try:
        release_gate_mod._git = lambda *args: calls.append(args) or "tag-sha"
        resolved = release_gate_mod.resolve_tag_commit("V1.2.3")
    finally:
        release_gate_mod._git = original_git
    check("release gate cannot resolve a same-named branch as a tag",
          resolved == "tag-sha"
          and calls == [("rev-parse", "--verify", "refs/tags/V1.2.3^{commit}")],
          str(calls))


def test_release_gate_compares_zip_payloads_not_container_bytes() -> None:
    from release_gate import archive_payload_issues

    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        tracked = root / "tracked.zip"
        equivalent = root / "equivalent.zip"
        changed = root / "changed.zip"
        duplicated = root / "duplicated.zip"
        with zipfile.ZipFile(tracked, "w") as archive:
            archive.writestr("kami/VERSION", "1.2.3")
        with zipfile.ZipFile(equivalent, "w") as archive:
            info = zipfile.ZipInfo("kami/VERSION", date_time=(2026, 1, 2, 3, 4, 6))
            archive.writestr(info, "1.2.3")
        with zipfile.ZipFile(changed, "w") as archive:
            archive.writestr("kami/VERSION", "1.2.4")
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            with zipfile.ZipFile(duplicated, "w") as archive:
                archive.writestr("kami/VERSION", "first")
                archive.writestr("kami/VERSION", "second")

        same_issues = archive_payload_issues(tracked, equivalent)
        changed_issues = archive_payload_issues(tracked, changed)
        duplicate_issues = archive_payload_issues(duplicated, tracked)
        check("release gate ignores ZIP container timestamp differences",
              tracked.read_bytes() != equivalent.read_bytes() and same_issues == [],
              str(same_issues))
        check("release gate rejects changed entry payloads",
              changed_issues == ["candidate payload differs: kami/VERSION"],
              str(changed_issues))
        check("release gate rejects duplicate ZIP entry names",
              len(duplicate_issues) == 1
              and "duplicate ZIP entry: kami/VERSION" in duplicate_issues[0],
              str(duplicate_issues))


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


# --------------------------- content IR ---------------------------

def test_content_schemas_cover_all_public_doc_types() -> None:
    from shared import content_schema_types, public_document_template_kinds
    expected = public_document_template_kinds() | {"landing-page"}
    actual = set(content_schema_types())
    check("content schemas cover every public doc type plus landing-page",
          actual == expected,
          f"missing: {sorted(expected - actual)}, extra: {sorted(actual - expected)}")


def test_content_schemas_parse_and_are_objects() -> None:
    from shared import SCHEMAS_DIR, content_schema_types
    bad = []
    for name in content_schema_types():
        try:
            schema = json.loads((SCHEMAS_DIR / f"{name}.json").read_text(encoding="utf-8"))
            if schema.get("type") != "object" or "required" in schema and not schema["required"]:
                bad.append(name)
        except json.JSONDecodeError:
            bad.append(name)
    check("content schemas parse as object contracts", not bad, f"bad: {bad}")


def test_validate_node_flags_structural_defects() -> None:
    from content import validate_node
    schema = {
        "type": "object",
        "required": ["title", "metrics"],
        "properties": {
            "title": {"type": "string", "minLength": 2, "maxLength": 10},
            "metrics": {
                "type": "array", "minItems": 3, "maxItems": 4,
                "items": {"type": "object", "required": ["value"],
                          "properties": {"value": {"type": "string"}}},
            },
            "layout": {"type": "string", "enum": ["cover", "content"]},
        },
    }
    ok = validate_node({"title": "Hello", "metrics": [{"value": "1"}] * 3}, schema)
    check("validate_node passes a conforming object", ok == [])
    issues = validate_node(
        {"title": "way too long for the cap", "metrics": [{}], "layout": "hero"},
        schema,
    )
    text = "\n".join(issues)
    check("validate_node flags length, count, required, and enum defects",
          "too long" in text and "too few items" in text
          and "missing required field 'value'" in text and "'hero' not in" in text,
          text)
    numeric = validate_node(0, {"type": "integer", "minimum": 1, "maximum": 3}, "page")
    check("validate_node enforces numeric bounds",
          numeric == ["page: too small (0 < 1)"], str(numeric))


def test_coverage_issues_catch_dropped_values() -> None:
    from content import coverage_issues
    content = {
        "name": "Kami",
        "metric": "62%",
        "note": "p" * 120,
        "image": "shot.png",
        "cjk": "用户 2M 规模",
    }
    html_text = "Kami cut latency 62% at 用户2M规模 scale"
    issues, checked, skipped = coverage_issues(content, html_text)
    check("coverage passes present values, skips prose and images, normalizes CJK spacing",
          issues == [] and checked == 3 and skipped == 1,
          f"issues={issues} checked={checked} skipped={skipped}")
    issues, _, _ = coverage_issues({"metric": "$340K"}, html_text)
    check("coverage flags a dropped atomic value",
          len(issues) == 1 and "$340K" in issues[0], str(issues))


def test_check_content_cli_validates_and_covers() -> None:
    from content import check_content
    payload = {
        "type": "letter",
        "lang": "en",
        "content": {
            "sender": "Ada Lovelace, London",
            "date": "2026-07-13",
            "recipient": "Charles Babbage",
            "salutation": "Dear Charles,",
            "paragraphs": [
                "I write to state my purpose in one sentence: the engine deserves a program of its own.",
                "The evidence sits in the notes: fifty operations, one loop, and a table the machine can follow.",
                "My ask is specific: review the table this month so we can test it on the mill.",
            ],
            "signoff": "Sincerely,",
            "signature": "Ada",
        },
    }
    with tempfile.TemporaryDirectory() as d:
        content_path = Path(d) / "content.json"
        content_path.write_text(json.dumps(payload), encoding="utf-8")
        rc = silently(check_content, [str(content_path)])
        check("check_content accepts a valid letter IR", rc == 0)
        html = write_temp_html(
            "<html><body><p>Ada Lovelace, London 2026-07-13 Charles Babbage "
            "Dear Charles, My ask is specific: review the table this month so "
            "we can test it on the mill. Sincerely, Ada</p></body></html>"
        )
        try:
            rc = silently(check_content, [str(content_path), str(html)])
            check("check_content coverage passes when atomic values present", rc == 0)

            ambiguous_html = write_temp_html(
                html.read_text(encoding="utf-8").replace(
                    "<p>", '<p style="font-size:calc(1px - 1px)">',
                )
            )
            try:
                ambiguous_rc = silently(
                    check_content,
                    [str(content_path), str(ambiguous_html)],
                )
                check("check_content degrades indeterminate visibility evidence",
                      ambiguous_rc == 2)
            finally:
                ambiguous_html.unlink()

            missing_text_html = write_temp_html(
                html.read_text(encoding="utf-8")
                .replace("2026-07-13", "2026-07-14")
                .replace("</body>", '<img srcset="a.png 1x,b.png 2x"></body>')
            )
            try:
                missing_text_rc = silently(
                    check_content,
                    [str(content_path), str(missing_text_html)],
                )
                check("resource ambiguity cannot downgrade definite missing text",
                      missing_text_rc == 1)
            finally:
                missing_text_html.unlink()

            for style in (
                "clip-path:circle(50%)",
                "mask-image:url(#rounded)",
                "filter:url(#soften)",
            ):
                decorated_html = write_temp_html(
                    html.read_text(encoding="utf-8")
                    .replace("2026-07-13", "2026-07-14")
                    .replace(
                        "</body>",
                        f'<img style="{style}" src="decorative.svg"></body>',
                    )
                )
                try:
                    decorated_rc = silently(
                        check_content,
                        [str(content_path), str(decorated_html)],
                    )
                    check("decorative resource ambiguity cannot downgrade missing text",
                          decorated_rc == 1, style)
                finally:
                    decorated_html.unlink()

            for decoration in (
                '<svg><path filter="url(#shadow)"></path></svg>',
                '<svg><circle mask="url(#fade)"></circle></svg>',
                '<svg><g clip-path="url(#round)"></g></svg>',
                '<style>.decor { clip-path:circle(50%) }</style>'
                '<svg><path class="decor"></path></svg>',
            ):
                decorated_svg_html = write_temp_html(
                    html.read_text(encoding="utf-8")
                    .replace("2026-07-13", "2026-07-14")
                    .replace("</body>", f"{decoration}</body>")
                )
                try:
                    decorated_svg_rc = silently(
                        check_content,
                        [str(content_path), str(decorated_svg_html)],
                    )
                    check("decorative SVG ambiguity cannot downgrade missing text",
                          decorated_svg_rc == 1, decoration)
                finally:
                    decorated_svg_html.unlink()

            payload["brief"] = {
                "audience": "Technical collaborator",
                "job": "Secure review",
                "template": "letter-en",
                "formats": ["html", "pdf"],
                "page_target": 1,
                "required_assets": ["must-appear-logo.svg"],
                "acceptance_checks": ["required logo is embedded"],
            }
            content_path.write_text(json.dumps(payload), encoding="utf-8")
            missing_asset_rc = silently(check_content, [str(content_path), str(html)])
            check("check_content coverage rejects a missing required brief asset",
                  missing_asset_rc == 1)
            mixed_html = write_temp_html(
                html.read_text(encoding="utf-8")
                .replace("2026-07-13", "2026-07-14")
                .replace("</body>", '<img srcset="a.png 1x,b.png 2x"></body>')
            )
            try:
                mixed_report = io.StringIO()
                with contextlib.redirect_stdout(mixed_report):
                    mixed_rc = check_content(
                        [str(content_path), str(mixed_html)]
                    )
                report = mixed_report.getvalue()
                check("mixed coverage reports definite and indeterminate findings separately",
                      mixed_rc == 1
                      and "definitely missing" in report
                      and "NOTE:" in report
                      and report.index("content.date") < report.index("NOTE:")
                      and report.index("brief.required_assets") > report.index("NOTE:"),
                      report)
            finally:
                mixed_html.unlink()
            html.write_text(
                html.read_text(encoding="utf-8").replace(
                    "</body>", '<img src="must-appear-logo.svg" alt=""></body>'
                ),
                encoding="utf-8",
            )
            embedded_asset_rc = silently(check_content, [str(content_path), str(html)])
            check("check_content coverage accepts an embedded required brief asset",
                  embedded_asset_rc == 0)
        finally:
            html.unlink()
        del payload["content"]["signature"]
        content_path.write_text(json.dumps(payload), encoding="utf-8")
        rc = silently(check_content, [str(content_path)])
        check("check_content rejects a missing required field", rc == 1)
        rc = silently(check_content, [])
        check("check_content usage error returns 2", rc == 2)


def test_content_ir_rejects_invalid_envelope() -> None:
    from content import validate_content_file

    body = {
        "sender": "Ada Lovelace, London",
        "date": "2026-07-13",
        "recipient": "Charles Babbage",
        "salutation": "Dear Charles,",
        "paragraphs": [
            "I write to state my purpose in one sentence: the engine deserves a program of its own.",
            "The evidence sits in the notes: fifty operations, one loop, and a table the machine can follow.",
            "My ask is specific: review the table this month so we can test it on the mill.",
        ],
        "signoff": "Sincerely,",
        "signature": "Ada",
    }
    valid_type, valid_issues = validate_content_file({
        "type": "letter", "lang": "zh-TW", "content": body,
    })
    _, invalid_issues = validate_content_file({
        "type": "letter", "lang": "not_a_locale", "content": body,
        "unexpected": True,
    })
    check("content IR accepts a strict language-tagged envelope",
          valid_type == "letter" and valid_issues == [], str(valid_issues))
    check("content IR rejects invalid lang and unknown top-level fields",
          any("'lang'" in issue for issue in invalid_issues)
          and any("unknown field 'unexpected'" in issue for issue in invalid_issues),
          str(invalid_issues))


def test_content_ir_validates_optional_artifact_brief() -> None:
    from content import (
        BRIEF_SCHEMA,
        _brief_contract_issues,
        validate_content_file,
        validate_node,
    )

    body = {
        "sender": "Ada Lovelace, London",
        "date": "2026-07-13",
        "recipient": "Charles Babbage",
        "salutation": "Dear Charles,",
        "paragraphs": [
            "I write to state my purpose in one sentence: the engine deserves a program of its own.",
            "The evidence sits in the notes: fifty operations, one loop, and a table the machine can follow.",
            "My ask is specific: review the table this month so we can test it on the mill.",
        ],
        "signoff": "Sincerely,",
        "signature": "Ada",
    }
    brief = {
        "audience": "Technical collaborator",
        "job": "Secure a review of the program table",
        "template": "letter-en",
        "formats": ["html", "pdf"],
        "page_target": 1,
        "acceptance_checks": ["one page", "specific ask remains visible"],
        "target": {"surface": "letter body", "page": 1},
        "preserve": ["letterhead", "signature"],
        "evidence": ["rendered page 1"],
    }
    _, valid_issues = validate_content_file({
        "type": "letter", "lang": "en", "brief": brief, "content": body,
    })
    invalid = dict(brief)
    invalid["formats"] = ["docx"]
    invalid["page_target"] = 0
    invalid["mystery"] = True
    _, invalid_issues = validate_content_file({
        "type": "letter", "lang": "en", "brief": invalid, "content": body,
    })
    text = "\n".join(invalid_issues)
    check("content IR accepts a structured artifact brief", valid_issues == [], str(valid_issues))
    check("content IR rejects unknown brief fields, formats, and page bounds",
          "brief: unknown field 'mystery'" in text
          and "'docx' not in" in text
          and "brief.page_target: too small" in text,
          text)

    conflicting = dict(brief, template="one-pager", page_target=2)
    _, conflict_issues = validate_content_file({
        "type": "one-pager", "lang": "cn", "brief": conflicting,
        "content": {
            "title": "A concise product claim",
            "subtitle": "A subtitle long enough to explain the intended audience and outcome",
            "metrics": [
                {"value": "10x", "label": "faster"},
                {"value": "99%", "label": "coverage"},
                {"value": "2m", "label": "setup"},
            ],
            "argument": [
                "A focused paragraph that explains the user problem, the proposed change, and why it matters now in concrete terms."
            ],
            "evidence": ["Measured result", "Observed behavior", "Verified source"],
            "next_step": "Review the evidence and approve the next test.",
        },
    })
    check("content IR rejects a page target beyond the template ceiling",
          any("exceeds template 'one-pager' maximum 1" in issue for issue in conflict_issues),
          str(conflict_issues))
    one_page_resume_issues = _brief_contract_issues(
        {"template": "resume-en", "formats": ["html", "pdf"], "page_target": 1},
        "resume",
        "en",
    )
    check("brief contract enforces the two-page resume hard stop",
          any("require exactly 2 pages" in issue for issue in one_page_resume_issues),
          str(one_page_resume_issues))

    landing_issues = _brief_contract_issues(
        {"template": "landing-page", "page_target": 2}, "landing-page"
    )
    slides_issues = _brief_contract_issues(
        {"template": "slides", "page_target": 12}, "slides"
    )
    editable_slides_issues = _brief_contract_issues(
        {"template": "slides-en", "formats": ["pptx"], "page_target": 12}, "slides"
    )
    impossible_resume_issues = _brief_contract_issues(
        {"template": "resume", "formats": ["pptx"], "page_target": 2}, "resume"
    )
    wrong_language_issues = _brief_contract_issues(
        {"template": "resume-en", "formats": ["html", "pdf"], "page_target": 2},
        "resume",
        "ko",
    )
    korean_pptx_fallback_issues = _brief_contract_issues(
        {
            "template": "slides-en", "formats": ["html", "pdf", "pptx"],
            "page_target": 12,
        },
        "slides",
        "ko",
    )
    korean_pdf_wrong_variant_issues = _brief_contract_issues(
        {"template": "slides-en", "formats": ["html", "pdf"], "page_target": 12},
        "slides",
        "ko",
    )
    check("brief contract accepts screen, generic slide, and editable PPTX keys",
          landing_issues == [] and slides_issues == [] and editable_slides_issues == [],
          f"landing={landing_issues} slides={slides_issues} "
          f"editable={editable_slides_issues}")
    check("brief contract rejects a format the selected template cannot produce",
          any("does not support pptx" in issue for issue in impossible_resume_issues),
          str(impossible_resume_issues))
    check("brief contract rejects a known language/template variant mismatch",
          any("does not match language 'ko'" in issue for issue in wrong_language_issues),
          str(wrong_language_issues))
    check("brief contract keeps the documented Korean editable-PPTX fallback",
          korean_pptx_fallback_issues == [], str(korean_pptx_fallback_issues))
    check("brief contract limits the Korean slides-en fallback to editable PPTX",
          any("does not match language 'ko'" in issue
              for issue in korean_pdf_wrong_variant_issues),
          str(korean_pdf_wrong_variant_issues))

    marp_brief = dict(
        brief,
        template="slides-marp-en",
        formats=["md", "pdf"],
        page_target=12,
    )
    marp_schema_issues = validate_node(marp_brief, BRIEF_SCHEMA, "brief")
    marp_contract_issues = _brief_contract_issues(marp_brief, "slides", "en")
    korean_marp_issues = _brief_contract_issues(
        dict(marp_brief, template="slides-marp"),
        "slides",
        "ko",
    )
    check("brief contract accepts the shipped Marp authoring path",
          marp_schema_issues == []
          and marp_contract_issues == []
          and korean_marp_issues == [],
          f"schema={marp_schema_issues} contract={marp_contract_issues} "
          f"korean={korean_marp_issues}")

    no_length_contract = dict(brief)
    no_length_contract.pop("page_target")
    target_issues = _brief_contract_issues(no_length_contract, "letter", "en")
    length_only_issues = _brief_contract_issues(
        dict(no_length_contract, length_target="600 to 800 words"),
        "letter",
        "en",
    )
    check("artifact brief requires a page or length target",
          any("page_target or length_target" in issue for issue in target_issues)
          and length_only_issues == [],
          f"missing={target_issues} length_only={length_only_issues}")

    _, legacy_issues = validate_content_file({
        "type": "letter", "lang": "en", "content": body,
    })
    check("content IR keeps pre-brief files valid", legacy_issues == [], str(legacy_issues))


def test_build_cli_dispatches_new_checks() -> None:
    rc, out = run_build_args(["--check-content"])
    check("build.py --check-content without args is a usage error",
          rc == 2 and "usage" in out, out.strip()[:120])
    rc, out = run_build_args(["--check-visual"])
    check("build.py --check-visual without args is a usage error",
          rc == 2 and "usage" in out, out.strip()[:120])
    rc, out = run_build_args(["--doctor"])
    check("build.py --doctor reports capability status",
          rc in {0, 1} and "Kami doctor" in out
          and "visual verification" in out,
          out.strip()[:300])


def test_skill_routes_visual_repairs_and_generated_assets_without_losing_contracts() -> None:
    skill = (REPO_ROOT / "SKILL.md").read_text(encoding="utf-8")
    diagrams = (REPO_ROOT / "references" / "diagrams.md").read_text(encoding="utf-8")
    for mode in ("New document", "Content-only", "Visual repair", "Generated asset"):
        check(f"SKILL work mode keeps {mode}", mode in skill)
    check("visual repair locks target, preserve, evidence, and artifact matrices",
          all(term in skill for term in (
              "`target`", "`preserve`", "PDF: target page", "Screen: 1280px",
              "PPTX: editable source", "Generated asset: target slot",
          )),
          "visual feedback contract incomplete")
    check("image generation routes from observed capability",
          "Route from observed capability" in skill
          and "Claude, Codex, most coding agents" not in skill,
          "host-name capability list still present")
    check("illustration brief keeps old visual system and adds semantic anchors",
          all(term in diagrams for term in (
              "1. Claim:", "2. Placement:", "3. Reference:", "4. Exclusions:",
              "5. Canvas:", "6. Accent:", "7. Strokes and icons:",
              "8. Labels:", "9. Content spec:",
          ))
          and "After two look-based rejections" in diagrams,
          "illustration brief lost a field")


def test_visual_checklist_and_output_dir() -> None:
    from visual import REVIEW_CHECKLIST, visual_output_dir
    check("visual checklist has stable size and no em dash",
          len(REVIEW_CHECKLIST) == 8 and all("\u2014" not in line for line in REVIEW_CHECKLIST))
    out = visual_output_dir(Path("/tmp/docs/report.pdf"))
    check("visual output dir sits next to the pdf",
          out == Path("/tmp/docs/report-visual"), str(out))


def test_visual_clears_stale_page_images() -> None:
    """A re-render with fewer pages must not leave prior page PNGs behind."""
    from visual import _clear_page_images
    with tempfile.TemporaryDirectory() as d:
        target = Path(d)
        for name in ("page-01.png", "page-07.png", "notes.txt"):
            (target / name).write_bytes(b"x")
        _clear_page_images(target)
        left = sorted(p.name for p in target.iterdir())
        check("stale page PNGs removed, unrelated files kept",
              left == ["notes.txt"], str(left))


def test_coverage_survives_split_markup_values() -> None:
    """Values split across sibling nodes ("62" + "%") must still count as present."""
    from content import coverage_issues
    issues, checked, _ = coverage_issues({"metric": "62%"}, "value:\n62\n%")
    check("coverage rejoins values split by markup",
          issues == [] and checked == 1, str(issues))


def test_coverage_rejects_substrings_and_hidden_text() -> None:
    """Changed facts and hidden-only copies must not satisfy coverage."""
    from content import coverage_issues
    from checks import visible_html_evidence, visible_html_text

    cases = [
        ({"metric": "62%"}, "Revenue reached 162%"),
        ({"metric": "62"}, "Revenue reached 1962"),
        ({"metric": "12 34"}, "Revenue reached 1234"),
        ({"metric": 1.0}, "Revenue reached 1.5"),
    ]
    issues = [coverage_issues(content, text)[0] for content, text in cases]
    check("coverage rejects values embedded in larger or collapsed tokens",
          all(len(found) == 1 for found in issues), str(issues))

    hidden_html = (
        "<html><head><title>62%</title><style>.concealed { display: none }</style></head><body>"
        "<template>62%</template><p hidden>62%</p>"
        '<p aria-hidden="true">62%</p><p style="display: none">62%</p>'
        '<p class="concealed">62%</p>'
        "<p>Visible value is 61%.</p></body></html>"
    )
    text = visible_html_text(hidden_html)
    missing, _, _ = coverage_issues({"metric": "62%"}, text)
    check("coverage ignores head, template, hidden, and display-none text",
          len(missing) == 1, f"text={text!r} issues={missing}")

    malformed_hidden = (
        '<div hidden><img></img><p>SECRET-FACT</p></div>'
        '<p>VISIBLE-FACT</p>'
    )
    malformed_text = visible_html_text(malformed_hidden)
    malformed_missing, _, _ = coverage_issues(
        {"hidden": "SECRET-FACT", "visible": "VISIBLE-FACT"},
        malformed_text,
    )
    check("visible-text parser keeps hidden scope across a void closing tag",
          len(malformed_missing) == 1
          and "SECRET-FACT" in malformed_missing[0]
          and "VISIBLE-FACT" in malformed_text,
          f"text={malformed_text!r} issues={malformed_missing}")

    self_closing_hidden = (
        '<div hidden/><p>SELF-CLOSING-SECRET</p></div>'
        '<p>SELF-CLOSING-VISIBLE</p>'
    )
    self_closing_text = visible_html_text(self_closing_hidden)
    self_closing_missing, _, _ = coverage_issues(
        {
            "hidden": "SELF-CLOSING-SECRET",
            "visible": "SELF-CLOSING-VISIBLE",
        },
        self_closing_text,
    )
    check("visible-text parser follows HTML semantics for non-void self-closing tags",
          len(self_closing_missing) == 1
          and "SELF-CLOSING-SECRET" in self_closing_missing[0]
          and "SELF-CLOSING-VISIBLE" in self_closing_text,
          f"text={self_closing_text!r} issues={self_closing_missing}")

    benign_selector_text = visible_html_text(
        '<style>[hidden] { display: none } '
        '[aria-hidden="true"] { visibility: hidden } '
        ':root { --fallback-display: none }</style>'
        '<p hidden>HIDDEN-BY-ATTRIBUTE</p>'
        '<p aria-hidden="false">VISIBLE-ARIA-FALSE</p>'
        '<p>VISIBLE-AFTER-SELECTOR</p>'
    )
    check("visibility parser scopes attribute selectors and custom properties",
          "HIDDEN-BY-ATTRIBUTE" not in benign_selector_text
          and "VISIBLE-ARIA-FALSE" in benign_selector_text
          and "VISIBLE-AFTER-SELECTOR" in benign_selector_text,
          repr(benign_selector_text))

    important_hidden_text = visible_html_text(
        '<style>.important-secret {'
        'display: none !important; display: block'
        '}</style>'
        '<p class="important-secret">IMPORTANT-SECRET</p>',
        fail_closed=True,
    )
    inline_important_text = visible_html_text(
        '<p style="display:none!important;display:block">INLINE-IMPORTANT-SECRET</p>',
        fail_closed=True,
    )
    visible_var_fallback = visible_html_text(
        '<p style="display:var(--missing, block)">VISIBLE-VAR-FALLBACK</p>',
        fail_closed=True,
    )
    check("visibility parser honors important cascade and visible var fallback",
          "IMPORTANT-SECRET" not in important_hidden_text
          and "INLINE-IMPORTANT-SECRET" not in inline_important_text
          and "VISIBLE-VAR-FALLBACK" in visible_var_fallback,
          f"style={important_hidden_text!r} inline={inline_important_text!r} "
          f"fallback={visible_var_fallback!r}")

    hidden_equivalents = [
        'font-size:0%',
        'font-size:calc(0px)',
        'font-size:min(0px, 1px)',
        'transform:scale(0, 0)',
        'transform:matrix(0,0,0,0,0,0)',
        'width:0%;height:0%;overflow:hidden',
        'max-width:0;max-height:0;overflow:hidden',
        'position:absolute;left:-99999px',
        'text-indent:-99999px;overflow:hidden;white-space:nowrap',
        'clip:rect(0, 0, 0, 0)',
    ]
    equivalent_results = [
        visible_html_text(
            f'<p style="{style}">EQUIVALENT-HIDDEN</p>',
            fail_closed=True,
        )
        for style in hidden_equivalents
    ]
    check("visibility parser recognizes equivalent hidden CSS values",
          all("EQUIVALENT-HIDDEN" not in text for text in equivalent_results),
          str(equivalent_results))

    ordinary_layout_text = visible_html_text(
        '<p style="position:absolute;top:20px;left:20px">ABSOLUTE-VISIBLE</p>'
        '<p style="transform:translateX(10px)">TRANSLATED-VISIBLE</p>'
        '<p style="scale:.95">SCALED-VISIBLE</p>'
        '<p style="backdrop-filter:blur(8px)">FILTERED-VISIBLE</p>'
        '<p style="margin-top:-1px">MARGIN-VISIBLE</p>'
        '<p style="text-indent:1em">INDENTED-VISIBLE</p>',
        fail_closed=True,
    )
    check("ordinary positioned and transformed layouts remain visible",
          all(marker in ordinary_layout_text for marker in (
              "ABSOLUTE-VISIBLE", "TRANSLATED-VISIBLE", "SCALED-VISIBLE",
              "FILTERED-VISIBLE", "MARGIN-VISIBLE", "INDENTED-VISIBLE",
          )),
          repr(ordinary_layout_text))

    ambiguous_text, ambiguous_state = visible_html_evidence(
        '<p style="font-size:calc(1px - 1px)">AMBIGUOUS-VISIBILITY</p>',
        fail_closed=True,
    )
    check("unresolved functional visibility is excluded and marked ambiguous",
          ambiguous_state and "AMBIGUOUS-VISIBILITY" not in ambiguous_text,
          f"ambiguous={ambiguous_state} text={ambiguous_text!r}")

    non_rendered_html = visible_html_text(
        '<svg><title>SVG-TITLE</title><desc>SVG-DESC</desc></svg>'
        '<svg><defs><text>SVG-DEFS</text></defs>'
        '<symbol><text>SVG-SYMBOL</text></symbol>'
        '<metadata>SVG-METADATA</metadata>'
        '<clipPath><text>SVG-CLIP</text></clipPath>'
        '<mask><text>SVG-MASK</text></mask>'
        '<pattern><text>SVG-PATTERN</text></pattern>'
        '<text>SVG-RENDERED</text></svg>'
        '<noembed>NOEMBED-TEXT</noembed>'
        '<noframes>NOFRAMES-TEXT</noframes>'
        '<datalist><option>DATALIST-OPTION</option></datalist>'
        '<ruby>base<rp>RUBY-FALLBACK</rp><rt>annotation</rt></ruby>'
        '<p>RENDERED-TEXT</p>',
        fail_closed=True,
    )
    check("visible text skips non-rendered metadata and fallback containers",
          all(marker not in non_rendered_html for marker in (
              "SVG-TITLE", "SVG-DESC", "SVG-DEFS", "SVG-SYMBOL",
              "SVG-METADATA", "SVG-CLIP", "SVG-MASK", "SVG-PATTERN",
              "NOEMBED-TEXT", "NOFRAMES-TEXT", "DATALIST-OPTION",
              "RUBY-FALLBACK",
          ))
          and "SVG-RENDERED" not in non_rendered_html
          and "RENDERED-TEXT" in non_rendered_html,
          repr(non_rendered_html))

    hidden_svg_text = visible_html_text(
        '<svg><text display="none">DISPLAY-SECRET</text>'
        '<text visibility="hidden">VISIBILITY-SECRET</text>'
        '<text opacity="0">OPACITY-SECRET</text>'
        '<text>SVG-VISIBLE</text></svg>',
        fail_closed=True,
    )
    check("visible text respects SVG presentation attributes",
          all(marker not in hidden_svg_text for marker in (
              "DISPLAY-SECRET", "VISIBILITY-SECRET", "OPACITY-SECRET",
          ))
          and "SVG-VISIBLE" not in hidden_svg_text,
          repr(hidden_svg_text))

    off_viewport_svg_text = visible_html_text(
        '<svg viewBox="0 0 100 100">'
        '<text x="-99999" y="20">OFF-LEFT</text>'
        '<text x="10000" y="20">OFF-RIGHT</text>'
        '<text x="101" y="20">JUST-OFF-RIGHT</text>'
        '<text x="-99" y="20">JUST-OFF-LEFT</text>'
        '<text x="101%" y="20">PERCENT-OFF-RIGHT</text>'
        '<text x="99" y="20" dx="10">DELTA-OFF-RIGHT</text>'
        '<svg x="101" viewBox="0 0 10 10"><text x="0" y="5">NESTED-OFF</text></svg>'
        '<text x="20" y="20">SVG-IN-VIEW</text></svg>',
        fail_closed=True,
    )
    check("visible text rejects SVG coordinates outside the viewport",
          "OFF-LEFT" not in off_viewport_svg_text
          and "OFF-RIGHT" not in off_viewport_svg_text
          and "JUST-OFF-RIGHT" not in off_viewport_svg_text
          and "JUST-OFF-LEFT" not in off_viewport_svg_text
          and "PERCENT-OFF-RIGHT" not in off_viewport_svg_text
          and "DELTA-OFF-RIGHT" not in off_viewport_svg_text
          and "NESTED-OFF" not in off_viewport_svg_text
          and "SVG-IN-VIEW" not in off_viewport_svg_text,
          repr(off_viewport_svg_text))

    malformed_table = (
        '<div hidden><table></div>MALFORMED-SECRET</table></div>'
        '<p>MALFORMED-VISIBLE</p>'
    )
    malformed_coverage_text = visible_html_text(malformed_table, fail_closed=True)
    malformed_residue_text = visible_html_text(malformed_table)
    check("crossed HTML closes split coverage and residue conservatively",
          "MALFORMED-SECRET" not in malformed_coverage_text
          and "MALFORMED-SECRET" in malformed_residue_text,
          f"coverage={malformed_coverage_text!r} residue={malformed_residue_text!r}")

    optional_end_html = visible_html_text(
        '<p>PARAGRAPH-FIRST<div>PARAGRAPH-SECOND</div><p>PARAGRAPH-THIRD'
        '<ul><li>LIST-FIRST<li>LIST-SECOND</ul>'
        '<table><tr><td>CELL-FIRST<td>CELL-SECOND</tr></table>',
        fail_closed=True,
    )
    check("standard optional HTML end tags preserve visible content",
          all(marker in optional_end_html for marker in (
              "PARAGRAPH-FIRST", "PARAGRAPH-SECOND", "PARAGRAPH-THIRD",
              "LIST-FIRST", "LIST-SECOND", "CELL-FIRST", "CELL-SECOND",
          )),
          repr(optional_end_html))

    self_closing_svg_text, self_closing_svg_ambiguous = visible_html_evidence(
        '<svg viewBox="0 0 100 100"><path d="M0 0L10 10" /></svg>'
        '<p>VISIBLE-AFTER-SVG</p>',
        fail_closed=True,
    )
    check("SVG foreign-content self-closing tags close without tainting HTML",
          self_closing_svg_text.strip() == "VISIBLE-AFTER-SVG"
          and not self_closing_svg_ambiguous,
          f"text={self_closing_svg_text!r} "
          f"ambiguous={self_closing_svg_ambiguous}")


def test_visibility_resolves_document_custom_properties() -> None:
    """Resolve only unconditional custom properties inherited from the root."""
    from checks import visible_html_evidence
    from content import html_resource_evidence

    visible_text, visible_ambiguous = visible_html_evidence(
        "<style>:root { --ink: #504e49 } body { color: var(--ink) }</style>"
        "<body>VISIBLE</body>",
        fail_closed=True,
    )
    check("document custom property makes body text deterministic",
          "VISIBLE" in visible_text and not visible_ambiguous,
          f"text={visible_text!r} ambiguous={visible_ambiguous}")

    template_results = []
    for path in sorted(TEMPLATES.glob("*.html")):
        raw = path.read_text(encoding="utf-8")
        text, ambiguous = visible_html_evidence(raw, fail_closed=True)
        template_results.append((path.name, bool(text.strip()), ambiguous, "<svg" in raw.lower()))
    check("all shipped HTML templates expose visible text under fail-closed checks",
          bool(template_results) and all(result[1] for result in template_results),
          str([result for result in template_results if not result[1]]))
    check("templates without SVG have deterministic visible text",
          all(ambiguous is False for _, _, ambiguous, has_svg in template_results
              if not has_svg),
          str([result for result in template_results if not result[3] and result[2]]))

    ambiguous_cases = [
        '<style>:root{--ink:#000}.dark{--ink:transparent}p{color:var(--ink)}</style>'
        '<div class="dark"><p>SECRET</p></div>',
        '<style>:root{--ink:#000}@media print{:root{--ink:transparent}}'
        'p{color:var(--ink)}</style><p>SECRET</p>',
        '<style>@property --ink{syntax:"<color>";inherits:false;initial-value:transparent}'
        ':root{--ink:#000}p{color:var(--ink)}</style><p>SECRET</p>',
        '<style>:root{--ink:#000}p{color:var(--ink)}</style>'
        '<p style="--ink:transparent">SECRET</p>',
        '<style>:root{--ink:#000}p{color:var(--ink)}</style>'
        '<p style=--ink:transparent>SECRET</p>',
        '<style>:root{--ink:#000}p{color:var(--ink)}</style>'
        "<p style='--ink:transparent'>SECRET</p>",
        '<style>:root{--ink:#000}p{color:var(--ink)}</style>'
        '<p style="--ink:trans&#112;arent">SECRET</p>',
    ]
    ambiguous_results = [
        visible_html_evidence(raw, fail_closed=True) for raw in ambiguous_cases
    ]
    check("conflicting or registered custom properties remain fail-closed",
          all("SECRET" not in text and ambiguous
              for text, ambiguous in ambiguous_results),
          repr(ambiguous_results))

    scoped_cases = [
        '<style>.theme{--d:block}p{display:var(--d,none)}</style>'
        '<div class="theme"></div><p>SECRET</p>',
        '<style>@media screen{:root{--d:block}}p{display:var(--d,none)}</style>'
        '<p>SECRET</p>',
        '<style>p{display:var(--d,none)}</style>'
        '<div style="--d:block"></div><p>SECRET</p>',
        '<style>.noop{--payload:"x; --ink:#000"}'
        'p{color:var(--ink,transparent)}</style><p>SECRET</p>',
        '<style>:root{--d:block}.hide{--junk:{x};--d:none}'
        'p{display:var(--d)}</style><p class="hide">SECRET</p>',
        '<style>:root{--INK:#000}p{color:var(--ink,transparent)}</style>'
        '<p>SECRET</p>',
    ]
    scoped_results = [
        visible_html_evidence(raw, fail_closed=True) for raw in scoped_cases
    ]
    check("scoped and malformed custom properties cannot expose hidden text",
          all("SECRET" not in text for text, _ in scoped_results),
          repr(scoped_results))

    scoped_assets, _ = html_resource_evidence(
        '<style>.theme{--d:block}img{display:var(--d,none)}</style>'
        '<div class="theme"></div><img src="required.svg">'
    )
    check("scoped custom properties cannot expose hidden resources",
          "required.svg" not in scoped_assets, repr(scoped_assets))

    hidden_cases = [
        '<style>:root{--ink:transparent}p{color:var(--ink)}</style><p>SECRET</p>',
        '<style>:root{--d:none}p{display:var(--d, block)}</style><p>SECRET</p>',
        '<p style=\'display:none;--x:";display:block"\'>SECRET</p>',
        '<p style="--HIDE:none;--hide:block;display:var(--HIDE)">SECRET</p>',
    ]
    hidden_results = [
        visible_html_evidence(raw, fail_closed=True) for raw in hidden_cases
    ]
    check("resolved hiding custom properties exclude their text deterministically",
          all("SECRET" not in text and not ambiguous
              for text, ambiguous in hidden_results),
          repr(hidden_results))

    benign_cases = [
        '<style>:root{--ink:#000}html{--ink:#000}p{color:var(--ink)}</style>'
        '<p>SHOWN</p>',
        '<style>:root{--base:#111;--ink:var(--base)}p{color:var(--ink)}</style>'
        '<p>SHOWN</p>',
        '<style>:root{--ink:#111}</style><p style="color:var(--ink)">SHOWN</p>',
    ]
    benign_results = [
        visible_html_evidence(raw, fail_closed=True) for raw in benign_cases
    ]
    check("identical and nested custom properties remain visible",
          all("SHOWN" in text and not ambiguous
              for text, ambiguous in benign_results),
          repr(benign_results))


def test_coverage_checks_asset_attributes() -> None:
    from checks import visible_html_text
    from content import (
        coverage_issues,
        html_resource_attributes,
        html_resource_evidence,
    )

    raw = (
        '<img src="./images/product-shot.png" alt="Product">'
        '<img src="images/product-shot@2x.webp" alt="Product at high density">'
        '<template><img src="hidden-shot.png"></template>'
        '<a href="linked-only.png">not embedded</a>'
    )
    attrs = html_resource_attributes(raw)
    present, checked, _ = coverage_issues(
        {"image": "product-shot.png", "images": ["product-shot@2x.webp"]}, "", attrs
    )
    missing, _, _ = coverage_issues({"image": "missing-shot.png"}, "", attrs)
    check("coverage accepts image paths present in src and srcset",
          present == [] and checked == 2, f"issues={present} attrs={attrs}")

    hidden_svg_attrs = html_resource_attributes(
        '<svg><defs><image href="hidden-def.png"></image></defs>'
        '<symbol><image href="hidden-symbol.png"></image></symbol>'
        '<image x="0" y="0" width="10" height="10" '
        'href="visible-svg.png"></image></svg>'
    )
    check("asset coverage skips SVG definition resources",
          hidden_svg_attrs == {"visible-svg.png"}, repr(hidden_svg_attrs))

    hidden_asset_cases = [
        '<svg><image display="none" href="required.svg"></image></svg>',
        '<svg><image visibility="hidden" href="required.svg"></image></svg>',
        '<svg><image opacity="0" href="required.svg"></image></svg>',
        '<img style="width:0;height:0" src="required.svg">',
        '<img width="0" height="0" src="required.svg">',
        '<svg width="0" height="0"><image href="required.svg"></image></svg>',
        '<img style="position:absolute;left:-99999px" src="required.svg">',
        '<img style="transform:matrix(0,0,0,0,0,0)" src="required.svg">',
        '<img style="width:calc(0px);height:calc(0px)" src="required.svg">',
        '<svg viewBox="0 0 100 100"><image x="-99999" href="required.svg"></image></svg>',
        '<svg viewBox="0 0 100 100"><image x="10000" href="required.svg"></image></svg>',
        '<svg viewBox="0 0 100 100"><image x="101" y="0" width="10" height="10" href="required.svg"></image></svg>',
        '<svg viewBox="0 0 100 100"><image x="101%" y="0" width="10" height="10" href="required.svg"></image></svg>',
        '<svg viewBox="0 0 100 100"><svg x="101"><image x="0" y="0" width="10" height="10" href="required.svg"></image></svg></svg>',
        '<svg viewBox="0 0 100 100"><defs><clipPath id="empty"></clipPath></defs>'
        '<image x="0" y="0" width="20" height="20" '
        'clip-path="url(#empty)" href="required.svg"></image></svg>',
        '<svg viewBox="0 0 100 100"><defs><mask id="empty"></mask></defs>'
        '<image x="0" y="0" width="20" height="20" '
        'mask="url(#empty)" href="required.svg"></image></svg>',
        '<svg viewBox="0 0 100 100"><defs><filter id="empty"></filter></defs>'
        '<image x="0" y="0" width="20" height="20" '
        'filter="url(#empty)" href="required.svg"></image></svg>',
    ]
    check("asset coverage rejects non-rendered CSS and presentation forms",
          all(not html_resource_attributes(case) for case in hidden_asset_cases),
          str([html_resource_attributes(case) for case in hidden_asset_cases]))

    deterministic_attrs, responsive_ambiguous = html_resource_evidence(
        '<img src="required.svg">'
        '<img srcset="a.png 1x,b.png 2x">'
    )
    check("responsive ambiguity preserves unrelated deterministic resources",
          deterministic_attrs == {"required.svg"} and responsive_ambiguous,
          f"attrs={deterministic_attrs} ambiguous={responsive_ambiguous}")
    hidden_responsive_attrs, hidden_responsive_ambiguous = html_resource_evidence(
        '<div hidden><img srcset="a.png 1x,b.png 2x"></div>'
    )
    check("hidden responsive resources do not degrade asset evidence",
          hidden_responsive_attrs == set() and not hidden_responsive_ambiguous,
          f"attrs={hidden_responsive_attrs} "
          f"ambiguous={hidden_responsive_ambiguous}")
    svg_then_asset, svg_then_asset_ambiguous = html_resource_evidence(
        '<svg viewBox="0 0 100 100"><path d="M0 0L10 10" /></svg>'
        '<img src="required.svg">'
    )
    check("self-closing SVG graphics preserve following resource evidence",
          svg_then_asset == {"required.svg"} and not svg_then_asset_ambiguous,
          f"attrs={svg_then_asset} ambiguous={svg_then_asset_ambiguous}")
    check("coverage rejects omitted image assets",
          len(missing) == 1 and "missing-shot.png" in missing[0], str(missing))
    hidden, _, _ = coverage_issues(
        {"images": ["hidden-shot.png", "linked-only.png"]}, "", attrs
    )
    check("coverage ignores assets in templates and plain links",
          len(hidden) == 2, f"issues={hidden} attrs={attrs}")
    wrong_origin, _, _ = coverage_issues(
        ["https://brand.example/logo.svg"],
        "",
        html_resource_attributes('<img src="https://other.example/logo.svg">'),
        root_path="brief.required_assets",
        force_assets=True,
    )
    same_origin, _, _ = coverage_issues(
        ["https://brand.example/logo.svg?v=approved"],
        "",
        html_resource_attributes('<img src="https://brand.example/logo.svg?v=cache">'),
        root_path="brief.required_assets",
        force_assets=True,
    )
    check("required absolute assets cannot be impersonated by the same path on another host",
          len(wrong_origin) == 1, str(wrong_origin))
    check("required absolute assets tolerate cache-query changes on the same origin and path",
          same_origin == [], str(same_origin))

    local_absolute_remote_copy, _, _ = coverage_issues(
        ["/approved/brand/logo.svg"],
        "",
        html_resource_attributes(
            '<img src="https://attacker.example/approved/brand/logo.svg">'
        ),
        root_path="brief.required_assets",
        force_assets=True,
    )
    local_absolute_exact, _, _ = coverage_issues(
        ["/approved/brand/logo.svg"],
        "",
        html_resource_attributes('<img src="/approved/brand/logo.svg">'),
        root_path="brief.required_assets",
        force_assets=True,
    )
    check("required local absolute assets reject remote path impersonation",
          len(local_absolute_remote_copy) == 1 and local_absolute_exact == [],
          f"remote={local_absolute_remote_copy} exact={local_absolute_exact}")

    malformed_hidden_attrs = html_resource_attributes(
        '<div hidden><img></img><img src="hidden-after-void.svg"></div>'
        '<img hidden src="hidden-void.svg">'
        '<img src="visible.svg">'
    )
    check("resource parser keeps hidden scope across a void closing tag",
          malformed_hidden_attrs == {"visible.svg"},
          str(sorted(malformed_hidden_attrs)))

    self_closing_hidden_attrs = html_resource_attributes(
        '<div hidden/><img src="hidden-self-closing.svg"></div>'
        '<img src="visible-after-self-closing.svg">'
    )
    check("resource parser follows HTML semantics for non-void self-closing tags",
          self_closing_hidden_attrs == {"visible-after-self-closing.svg"},
          str(sorted(self_closing_hidden_attrs)))

    css_hidden_attrs = html_resource_attributes(
        '<style>.concealed img { display: none } '
        '.escaped { d\\69splay: n\\6f ne } '
        '[hidden] { display: none } '
        ':root { --fallback-display: none }</style>'
        '<div class="concealed"><img src="hidden-by-selector.svg"></div>'
        '<img style="display/**/: none" src="hidden-by-inline-comment.svg">'
        '<img class="escaped" src="hidden-by-css-escape.svg">'
        '<img hidden src="hidden-by-attribute.svg">'
        '<img src="visible-after-css.svg">'
    )
    check("resource parser fails closed on compound and comment-split hidden CSS",
          css_hidden_attrs == {"visible-after-css.svg"},
          str(sorted(css_hidden_attrs)))

    ambiguous_css_cases = [
        (
            '<style>div:not(.show) img { display: none }</style>'
            '<div><img src="hidden-by-not.svg"></div>',
            "hidden-by-not.svg",
        ),
        (
            '<style>[data-state^="hid"] { display: none }</style>'
            '<p data-state="hidden">HIDDEN-BY-ATTR-OPERATOR</p>',
            "HIDDEN-BY-ATTR-OPERATOR",
        ),
        (
            '<style>.marker + p { display: none }</style>'
            '<span class="marker"></span><p>HIDDEN-BY-SIBLING</p>',
            "HIDDEN-BY-SIBLING",
        ),
        (
            '<style>.hidden-by-var { --hide: none; display: var(--hide) }</style>'
            '<img class="hidden-by-var" src="hidden-by-var.svg">',
            "hidden-by-var.svg",
        ),
        (
            '<style>.h\\69 dden { visibility: collapse }</style>'
            '<img class="hidden" src="hidden-by-selector-escape.svg">',
            "hidden-by-selector-escape.svg",
        ),
        (
            '<link rel="style&#115;heet" '
            'href="data:text/css,.x%7Bdisplay%3Anone%7D">'
            '<img class="x" src="hidden-by-encoded-stylesheet.svg">',
            "hidden-by-encoded-stylesheet.svg",
        ),
        (
            '<style>@\\69mport url("data:text/css,.x%7Bdisplay%3Anone%7D")</style>'
            '<img class="x" src="hidden-by-escaped-import.svg">',
            "hidden-by-escaped-import.svg",
        ),
    ]
    ambiguous_results = [
        (
            marker,
            visible_html_text(raw, fail_closed=True),
            html_resource_attributes(raw),
        )
        for raw, marker in ambiguous_css_cases
    ]
    check("unsupported hiding CSS fails closed instead of partially matching",
          all(
              marker not in text and marker not in attrs
              for marker, text, attrs in ambiguous_results
          ),
          str(ambiguous_results))

    responsive_attrs = html_resource_attributes(
        '<picture>'
        '<source media="(min-width:99999px)" srcset="never-selected.svg">'
        '<img src="actual.svg" srcset="candidate-1.svg 1x, candidate-2.svg 2x">'
        '</picture>'
    )
    check("resource parser excludes unresolved responsive candidates",
          responsive_attrs == set(),
          str(sorted(responsive_attrs)))
    picture_fallback_attrs = html_resource_attributes(
        '<picture>'
        '<source media="(min-width:1px)" srcset="actual.svg">'
        '<img src="required-fallback.svg">'
        '</picture>'
    )
    bare_source_attrs = html_resource_attributes(
        '<source srcset="bare-unrendered.svg">'
    )
    check("picture fallbacks and bare sources cannot prove required assets",
          picture_fallback_attrs == set() and bare_source_attrs == set(),
          f"picture={sorted(picture_fallback_attrs)} bare={sorted(bare_source_attrs)}")

    remote_base, _, _ = coverage_issues(
        ["approved/logo.svg"],
        "",
        html_resource_attributes(
            '<base href="https://attacker.example/">'
            '<img src="approved/logo.svg">'
        ),
        root_path="brief.required_assets",
        force_assets=True,
    )
    check("required local assets reject a remote base URL",
          len(remote_base) == 1,
          str(remote_base))


def test_coverage_caps_adversarial_reports() -> None:
    from content import MAX_COVERAGE_ISSUES, MAX_COVERAGE_VALUES, coverage_issues

    missing, _, _ = coverage_issues({"values": list(range(1000))}, "")
    oversized, _, _ = coverage_issues({"values": ["present"] * (MAX_COVERAGE_VALUES + 1)}, "present")
    check("coverage caps missing-value reports",
          len(missing) == MAX_COVERAGE_ISSUES + 1
          and "issue limit" in missing[-1], f"issues={len(missing)}")
    check("coverage caps the number of atomic values",
          len(oversized) == 1 and "too many atomic values" in oversized[0], str(oversized[-2:]))


# --------------------------- MCP server ---------------------------

def test_mcp_server_stdio_protocol() -> None:
    """The server must speak newline-delimited JSON-RPC with nothing else on stdout."""
    script = REPO_ROOT / "scripts" / "mcp_server.py"
    msgs = [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize",
         "params": {"protocolVersion": "2025-03-26"}},
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
        {"jsonrpc": "2.0", "id": 3, "method": "tools/call",
         "params": {"name": "kami_templates", "arguments": {}}},
        {"jsonrpc": "2.0", "id": 4, "method": "tools/call",
         "params": {"name": "kami_doctor", "arguments": {}}},
        {"jsonrpc": "2.0", "id": 5, "method": "tools/call",
         "params": {"name": "nope", "arguments": {}}},
    ]
    stdin = "".join(json.dumps(m) + "\n" for m in msgs)
    result = subprocess.run(
        [sys.executable, str(script)],
        input=stdin, capture_output=True, text=True, cwd=REPO_ROOT, timeout=60,
    )
    try:
        replies = {m.get("id"): m for m in map(json.loads, result.stdout.strip().splitlines())}
    except json.JSONDecodeError:
        check("mcp server stdout is newline-delimited JSON", False, result.stdout[:200])
        return
    init = replies.get(1, {}).get("result", {})
    check("mcp initialize echoes protocol version and names the server",
          init.get("protocolVersion") == "2025-03-26"
          and init.get("serverInfo", {}).get("name") == "kami",
          json.dumps(init)[:200])
    tools = [t["name"] for t in replies.get(2, {}).get("result", {}).get("tools", [])]
    check("mcp tools/list exposes the five kami tools",
          tools == ["kami_templates", "kami_doctor", "kami_render", "kami_check", "kami_screenshot"],
          str(tools))
    body = replies.get(3, {}).get("result", {}).get("content", [{}])[0].get("text", "{}")
    payload = json.loads(body)
    check("mcp kami_templates returns registries and schema types",
          set(payload.get("document_templates", {})) == set(HTML_TEMPLATES)
          and set(payload.get("pptx_templates", {})) == {"slides", "slides-en"}
          and set(payload.get("marp_templates", {})) == set(MARP_TEMPLATES)
          and payload.get("content_schema_types"),
          body[:200])
    doctor_body = replies.get(4, {}).get("result", {}).get("content", [{}])[0].get("text", "{}")
    doctor = json.loads(doctor_body)
    check("mcp kami_doctor reports dependencies, fonts, and capabilities",
          isinstance(doctor.get("ok"), bool)
          and len(doctor.get("dependencies", [])) >= 3
          and len(doctor.get("fonts", [])) >= 3
          and "pdf_visual_review" in doctor.get("capabilities", {}),
          doctor_body[:300])
    check("mcp unknown tool returns a JSON-RPC error",
          "error" in replies.get(5, {}), json.dumps(replies.get(5, {}))[:200])
    check("mcp notification produced no reply", len(replies) == 5, str(sorted(replies)))


def test_mcp_check_returns_stable_findings_and_coverage() -> None:
    from mcp_server import CHECK_REGISTRY, tool_check

    with tempfile.TemporaryDirectory() as d:
        clean = Path(d) / "clean.html"
        broken = Path(d) / "broken.html"
        clean.write_text("<html><body><p>Ready</p></body></html>", encoding="utf-8")
        broken.write_text("<html><body><p>{{ missing }}</p></body></html>", encoding="utf-8")
        invalid_content = Path(d) / "invalid-content.json"
        invalid_content.write_text(
            json.dumps({"type": "letter", "lang": "en", "content": {}}),
            encoding="utf-8",
        )
        valid_content = Path(d) / "valid-content.json"
        valid_content.write_text(json.dumps({
            "type": "letter",
            "lang": "en",
            "content": {
                "sender": "Ada Lovelace, London",
                "date": "2026-07-13",
                "recipient": "Charles Babbage",
                "salutation": "Dear Charles,",
                "paragraphs": [
                    "I write to state my purpose in one sentence: the engine deserves a program of its own.",
                    "The evidence sits in the notes: fifty operations, one loop, and a table the machine can follow.",
                    "My ask is specific: review the table this month so we can test it on the mill.",
                ],
                "signoff": "Sincerely,",
                "signature": "Ada",
            },
        }), encoding="utf-8")
        clean_result = tool_check({"path": str(clean)})
        broken_result = tool_check({"path": str(broken)})
        invalid_content_result = tool_check({
            "path": str(clean), "content": str(invalid_content),
        })
        missing_coverage_result = tool_check({
            "path": str(clean), "content": str(valid_content),
        })

    check("MCP check registry carries unique stable rule IDs",
          CHECK_REGISTRY and clean_result["ruleset_version"] == 2
          and len(CHECK_REGISTRY) == len(set(CHECK_REGISTRY))
          and all({"scope", "severity", "required_engine", "explanation"} <= set(rule)
                  for rule in CHECK_REGISTRY.values()),
          str(CHECK_REGISTRY))
    check("MCP clean check returns coverage without findings",
          clean_result["ok"] is True
          and clean_result["degraded"] is False
          and clean_result["findings"] == []
          and [item["id"] for item in clean_result["coverage"]]
          == ["html.placeholders", "html.markdown-residue"]
          and clean_result["report"],
          json.dumps(clean_result)[:500])
    check("MCP failed check returns a stable finding and legacy report",
          broken_result["ok"] is False
          and broken_result["findings"][0]["id"] == "html.placeholders"
          and broken_result["findings"][0]["status"] == "failed"
          and "placeholder" in broken_result["report"].lower(),
          json.dumps(broken_result)[:500])
    invalid_ids = [item["id"] for item in invalid_content_result["findings"]]
    invalid_coverage = {
        item["id"]: item for item in invalid_content_result["coverage"]
    }
    check("MCP labels invalid content IR as contract failure before coverage",
          "content.contract" in invalid_ids
          and "content.coverage" not in invalid_ids
          and invalid_coverage["content.coverage"]["status"] == "not_run"
          and invalid_coverage["content.coverage"]["blocked_by"]
          == "content.contract",
          json.dumps(invalid_content_result)[:800])
    missing_ids = [item["id"] for item in missing_coverage_result["findings"]]
    missing_statuses = {
        item["id"]: item["status"]
        for item in missing_coverage_result["coverage"]
    }
    check("MCP runs coverage once after a valid content contract",
          missing_ids == ["content.coverage"]
          and missing_statuses["content.contract"] == "passed"
          and missing_statuses["content.coverage"] == "failed",
          json.dumps(missing_coverage_result)[:800])


def test_mcp_server_rejects_bad_frames_without_exiting() -> None:
    """Wrong-shaped JSON-RPC frames return errors and do not kill the server."""
    script = REPO_ROOT / "scripts" / "mcp_server.py"
    msgs = [
        [],
        {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": "bad"},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/call",
         "params": {"name": "kami_templates", "arguments": ["bad"]}},
        {"jsonrpc": "2.0", "id": 3, "method": "ping"},
    ]
    result = subprocess.run(
        [sys.executable, str(script)],
        input="".join(json.dumps(m) + "\n" for m in msgs),
        capture_output=True, text=True, cwd=REPO_ROOT, timeout=60,
    )
    replies = [json.loads(line) for line in result.stdout.strip().splitlines()]
    by_id = {reply.get("id"): reply for reply in replies}
    check("mcp malformed frames keep the process alive",
          result.returncode == 0 and len(replies) == 4 and "result" in by_id.get(3, {}),
          (result.stdout + result.stderr)[:400])
    check("mcp wrong params and arguments return invalid-params errors",
          by_id.get(1, {}).get("error", {}).get("code") == -32602
          and by_id.get(2, {}).get("error", {}).get("code") == -32602,
          result.stdout[:400])


def test_mcp_all_tools_succeed_over_stdio() -> None:
    """Exercise render, check, and screenshot through the installed protocol path."""
    try:
        from optional_deps import require_pypdf_reader, require_weasyprint_html
        require_weasyprint_html()
        require_pypdf_reader()
        require_pymupdf()
    except MissingDepError as exc:
        skip("MCP all-tools stdio success path", str(exc), ci_required=True)
        return

    script = REPO_ROOT / "scripts" / "mcp_server.py"
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        html = root / "source.html"
        pdf = root / "output.pdf"
        html.write_text(
            "<!doctype html><html><head><style>"
            "@page{size:A4;margin:20mm}body{font-family:serif}"
            "</style></head><body><h1>Kami MCP smoke</h1><p>Rendered.</p></body></html>",
            encoding="utf-8",
        )
        msgs = [
            {"jsonrpc": "2.0", "id": 1, "method": "initialize",
             "params": {"protocolVersion": "2025-06-18"}},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/call",
             "params": {"name": "kami_render", "arguments": {
                 "html": str(html), "out": str(pdf)}}},
            {"jsonrpc": "2.0", "id": 3, "method": "tools/call",
             "params": {"name": "kami_check", "arguments": {"path": str(html)}}},
            {"jsonrpc": "2.0", "id": 4, "method": "tools/call",
             "params": {"name": "kami_screenshot", "arguments": {"pdf": str(pdf)}}},
        ]
        result = subprocess.run(
            [sys.executable, str(script)],
            input="".join(json.dumps(m) + "\n" for m in msgs),
            capture_output=True, text=True, cwd=REPO_ROOT, timeout=120,
        )
        try:
            replies = {m.get("id"): m for m in map(json.loads, result.stdout.strip().splitlines())}
            payloads = {
                reply_id: json.loads(
                    replies[reply_id]["result"]["content"][0]["text"]
                )
                for reply_id in (2, 3, 4)
            }
        except (KeyError, json.JSONDecodeError) as exc:
            check("MCP all-tools success path returns JSON results", False,
                  f"{exc}: {(result.stdout + result.stderr)[:500]}")
            return

        render_result = payloads[2]
        check_result = payloads[3]
        screenshot_result = payloads[4]
        check("MCP render succeeds over stdio",
              result.returncode == 0 and render_result.get("pages") == 1 and pdf.is_file(),
              json.dumps(render_result)[:300])
        check("MCP check succeeds over stdio",
              check_result.get("ok") is True and check_result.get("exit_code") == 0,
              json.dumps(check_result)[:300])
        page_paths = [Path(path) for path in screenshot_result.get("pages", [])]
        check("MCP screenshot returns evidence without a false perceptual verdict",
              "ok" not in screenshot_result
              and screenshot_result.get("rasterized") is True
              and screenshot_result.get("review_pending") is True
              and screenshot_result.get("font_check", {}).get("ok") is True
              and len(page_paths) == 1 and all(path.is_file() for path in page_paths),
              json.dumps(screenshot_result)[:500])


def test_mcp_render_guards_source_and_output_types() -> None:
    from mcp_server import tool_render

    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        html = root / "source.html"
        html.write_text("<html><body>safe source</body></html>", encoding="utf-8")
        original = html.read_bytes()
        hardlink = root / "hardlink.pdf"
        hardlink.hardlink_to(html)
        victim = root / "victim.txt"
        victim.write_bytes(b"do-not-overwrite")
        symlink = root / "symlink.pdf"
        symlink.symlink_to(victim)
        rejected = 0
        for out in (html, hardlink, symlink, root / "not-pdf.txt"):
            try:
                tool_render({"html": str(html), "out": str(out)})
            except ValueError:
                rejected += 1
        check("mcp render rejects source aliases and non-PDF outputs",
              rejected == 4 and html.read_bytes() == original
              and victim.read_bytes() == b"do-not-overwrite",
              f"rejected={rejected} source_changed={html.read_bytes() != original}")


def test_visual_rejects_empty_pdf_and_bad_dpi() -> None:
    try:
        from pypdf import PdfWriter
        from visual import render_pages
    except ImportError:
        skip("visual empty-PDF guard", "pypdf unavailable", ci_required=True)
        return

    with tempfile.TemporaryDirectory() as d:
        pdf = Path(d) / "empty.pdf"
        evidence = Path(d) / "empty-visual"
        evidence.mkdir()
        old_page = evidence / "page-01.png"
        old_page.write_bytes(b"last-good-run")
        writer = PdfWriter()
        writer.write(str(pdf))
        errors = 0
        for dpi in (1, -1, 301):
            try:
                render_pages(pdf, dpi=dpi)
            except ValueError:
                errors += 1
        try:
            render_pages(pdf, dpi=110)
        except ValueError as exc:
            empty_error = "no pages" in str(exc)
        else:
            empty_error = False
        check("visual rejects empty PDFs and out-of-range DPI",
              empty_error and errors == 3,
              f"empty_error={empty_error} dpi_errors={errors}")
        check("failed visual render preserves last good evidence",
              old_page.read_bytes() == b"last-good-run")

        symlink_target = Path(d) / "elsewhere"
        symlink_target.mkdir()
        symlink_output = Path(d) / "linked-visual"
        symlink_output.symlink_to(symlink_target, target_is_directory=True)
        try:
            render_pages(pdf, out_dir=symlink_output, dpi=110)
        except ValueError as exc:
            symlink_rejected = "symbolic link" in str(exc)
        else:
            symlink_rejected = False
        check("visual rejects a symbolic-link evidence directory", symlink_rejected)

        huge_pdf = Path(d) / "huge.pdf"
        huge_writer = PdfWriter()
        huge_writer.add_blank_page(width=5000, height=5000)
        huge_writer.write(str(huge_pdf))
        try:
            render_pages(huge_pdf, dpi=300)
        except ValueError as exc:
            huge_rejected = "pixels" in str(exc)
        else:
            huge_rejected = False
        check("visual rejects an oversized raster page before rendering", huge_rejected)


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
    print(f"Passed: {_PASS} | Skipped: {_SKIP} | Failed: {_FAIL}")
    return 0 if _FAIL == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
