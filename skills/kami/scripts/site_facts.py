"""Public-site fact drift checks for Kami.

The hosted pages, README, and llms.txt intentionally repeat install and product
facts in multiple languages. This module keeps those facts tied to the shared
registry and public constants so `build.py --check` catches drift before CI.
"""
from __future__ import annotations

import difflib
import html
import re
from collections.abc import Mapping
from html.parser import HTMLParser
from pathlib import Path

from shared import (
    CLAUDE_CODE_INSTALL_COMMANDS,
    CLAUDE_CODE_MIN_VERSION,
    CLAUDE_DESKTOP_PACKAGE_URL,
    CODEX_PLUGIN_INSTALL_COMMANDS,
    DIAGRAM_TEMPLATES,
    GENERIC_AGENT_INSTALL_COMMAND,
    PUBLIC_DOCUMENT_TEMPLATE_KINDS,
    REPO_ROOT,
    ROOT,
    SITE_ROOT,
    kami_version,
    public_document_template_count,
    public_document_template_kinds,
)

# Locale pages are hand-maintained forks of index.html. Their DOM skeletons
# must stay identical; the only allowed divergence is the language-redirect
# <script> that exists solely on the default page.
SITE_BASE_PAGE = "index.html"
SITE_LOCALE_PAGES = (
    "index-zh.html",
    "index-ja.html",
    "index-ko.html",
    "index-tw.html",
)

# Every surface that must carry the full public fact set. Derived from the
# locale-page tuple so adding a locale automatically joins both checks.
# index.md is the Markdown twin agents read instead of the homepage, so it
# carries the same install and product facts.
DEVELOPER_FACT_FILES = (
    "developers.html",
    "developers.md",
)
FULL_PUBLIC_FACT_FILES = (
    "README.md",
    "llms.txt",
    "index.md",
    SITE_BASE_PAGE,
    *SITE_LOCALE_PAGES,
    *DEVELOPER_FACT_FILES,
)
SITE_VERSION_BADGE_FILES = (SITE_BASE_PAGE, *SITE_LOCALE_PAGES)
# Anchored on the badge's own copy rather than a bare version pattern: these
# pages also print the Claude Code minimum as "v2.1.142+", which a generic
# `v\d+\.\d+\.\d+` judge would read as a stale Kami badge on every page.
# The label is translated on each locale page, so the pattern lists every copy.
SITE_VERSION_BADGE = re.compile(r"(?:Design System|设计系统|設計系統|デザインシステム|디자인 시스템)\s*·\s*v(\d+\.\d+\.\d+)")
REDIRECT_SITE_FILE = "index-en.html"
SITE_SURFACE_ABSENT = "__site_surface_absent__"

_SKELETON_TAGS = frozenset({
    "article", "aside", "dl", "figure", "footer", "form", "header",
    "h1", "h2", "h3", "h4", "h5", "h6",
    "main", "nav", "ol", "section", "script", "svg", "table", "ul",
})

# Spelled-out numerals per template count. Digit patterns below are derived
# from the live registry count, so a registry change keeps the check honest;
# only the localized number words need a new entry here when the count moves.
_TEMPLATE_COUNT_WORDS = {
    8: (
        r"\bEight document template",
        r"八种文档模板",
        r"八種文件範本",
    ),
}

def _normalize(text: str) -> str:
    return html.unescape(text)


def _contains_template_count(text: str, expected: int) -> bool:
    patterns = [
        rf"\b{expected} document template",
        rf"{expected}种文档模板",
        rf"{expected}種文件範本",
        rf"{expected}種類のドキュメントテンプレート",
        rf"{expected}가지 문서 템플릿",
        *_TEMPLATE_COUNT_WORDS.get(expected, ()),
    ]
    return any(re.search(pattern, text, re.IGNORECASE) for pattern in patterns)


def _contains_diagram_count(text: str, expected: int) -> bool:
    patterns = [
        rf"\b{expected}\s+(?:inline\s+SVG\s+)?diagram",
        rf"{expected}\s*(?:种|種).*?(?:图表|圖表)",
        rf"{expected}種.*?図表",
        rf"{expected}가지.*?다이어그램",
    ]
    if expected == 18:
        patterns.append(r"\bEighteen\s+inline\s+SVG")
    return any(re.search(pattern, text, re.IGNORECASE) for pattern in patterns)


def public_path(rel: str) -> Path:
    """Where a public fact file lives: README at the repo root, pages under site/."""
    if SITE_ROOT is None:
        return ROOT / rel
    if rel == "README.md":
        return REPO_ROOT / rel
    return SITE_ROOT / rel


def _file_texts(files: Mapping[str, str] | None) -> tuple[dict[str, str], list[str]]:
    if files is not None:
        return dict(files), []

    texts: dict[str, str] = {}
    issues: list[str] = []
    site_files = (*FULL_PUBLIC_FACT_FILES, REDIRECT_SITE_FILE)
    if not any(public_path(rel).exists() for rel in site_files):
        return {SITE_SURFACE_ABSENT: ""}, []
    for rel in site_files:
        path = public_path(rel)
        if not path.exists():
            issues.append(f"{rel}: missing public fact file")
            continue
        texts[rel] = path.read_text(encoding="utf-8", errors="replace")
    return texts, issues


class _SkeletonParser(HTMLParser):
    """Collect the structural tag sequence of a page, annotated enough to
    catch real drift (class identity, script type) without tracking text."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.rows: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag not in _SKELETON_TAGS:
            return
        attr_map = dict(attrs)
        row = tag
        css_class = (attr_map.get("class") or "").strip()
        if css_class:
            row += f".{css_class}"
        if tag == "script":
            script_type = (attr_map.get("type") or "").strip()
            if script_type:
                row += f"[{script_type}]"
        self.rows.append(row)


def _page_skeleton(text: str) -> list[str]:
    parser = _SkeletonParser()
    parser.feed(text)
    return parser.rows


def _drop_language_redirect_script(rows: list[str]) -> list[str]:
    """Return rows minus the first bare <script> (the default page's
    language redirect), which locale pages intentionally omit."""
    for index, row in enumerate(rows):
        if row == "script":
            return rows[:index] + rows[index + 1:]
    return rows


def site_structure_issues(files: Mapping[str, str] | None = None) -> list[str]:
    """Compare each locale page's DOM skeleton against index.html."""
    texts, issues = _file_texts(files)
    if SITE_SURFACE_ABSENT in texts:
        return []

    base_raw = texts.get(SITE_BASE_PAGE)
    if base_raw is None:
        return issues
    expected = _drop_language_redirect_script(_page_skeleton(base_raw))

    for rel in SITE_LOCALE_PAGES:
        raw = texts.get(rel)
        if raw is None:
            continue
        rows = _page_skeleton(raw)
        if rows == expected:
            continue
        delta = [
            line for line in difflib.unified_diff(expected, rows, lineterm="", n=0)
            if line[:1] in "+-" and line[:3] not in ("+++", "---")
        ]
        preview = "; ".join(delta[:6]) + (" ..." if len(delta) > 6 else "")
        issues.append(
            f"{rel}: DOM skeleton drifted from {SITE_BASE_PAGE} "
            f"({len(delta)} row(s): {preview})"
        )

    return issues


def site_fact_issues(files: Mapping[str, str] | None = None) -> list[str]:
    texts, issues = _file_texts(files)
    if SITE_SURFACE_ABSENT in texts:
        return []

    kinds = public_document_template_kinds()
    if kinds != PUBLIC_DOCUMENT_TEMPLATE_KINDS:
        missing = sorted(PUBLIC_DOCUMENT_TEMPLATE_KINDS - kinds)
        extra = sorted(kinds - PUBLIC_DOCUMENT_TEMPLATE_KINDS)
        detail = []
        if missing:
            detail.append(f"missing public kinds: {', '.join(missing)}")
        if extra:
            detail.append(f"extra public kinds: {', '.join(extra)}")
        issues.append("registry: public document template kinds drifted" + (f" ({'; '.join(detail)})" if detail else ""))

    template_count = public_document_template_count()
    diagram_count = len(DIAGRAM_TEMPLATES)

    for rel in FULL_PUBLIC_FACT_FILES:
        raw = texts.get(rel)
        if raw is None:
            if files is not None:
                issues.append(f"{rel}: missing public fact file")
            continue
        text = _normalize(raw)

        if CLAUDE_CODE_MIN_VERSION not in text:
            issues.append(f"{rel}: missing Claude Code minimum version {CLAUDE_CODE_MIN_VERSION}")
        for command in CLAUDE_CODE_INSTALL_COMMANDS:
            if command not in text:
                issues.append(f"{rel}: missing Claude Code install command `{command}`")
        for command in CODEX_PLUGIN_INSTALL_COMMANDS:
            if command not in text:
                issues.append(f"{rel}: missing Codex install command `{command}`")
        if GENERIC_AGENT_INSTALL_COMMAND not in text:
            issues.append(f"{rel}: missing generic agent install command `{GENERIC_AGENT_INSTALL_COMMAND}`")

        if "kami.zip" not in text:
            issues.append(f"{rel}: missing Claude Desktop package name kami.zip")
        if rel != "llms.txt" and CLAUDE_DESKTOP_PACKAGE_URL not in text:
            issues.append(f"{rel}: missing Claude Desktop package URL {CLAUDE_DESKTOP_PACKAGE_URL}")

        # The homepage HTML pages carry a hand-written Kami version badge; tie
        # those pages to VERSION without forcing the prose/developer files to
        # repeat a badge they do not display.
        # Each page writes the badge twice, in the eyebrow and in the type
        # sample. Check every occurrence: a presence-only test passed while a
        # stale second badge sat next to a freshly bumped first one.
        if rel in SITE_VERSION_BADGE_FILES:
            badges = SITE_VERSION_BADGE.findall(text)
            stale = sorted({badge for badge in badges if badge != kami_version()})
            if not badges:
                issues.append(f"{rel}: missing Kami version badge v{kami_version()}")
            elif stale:
                found = ", ".join(f"v{badge}" for badge in stale)
                issues.append(
                    f"{rel}: stale Kami version badge {found} (VERSION is {kami_version()})"
                )

        if not _contains_template_count(text, template_count):
            issues.append(f"{rel}: missing public document template count {template_count}")
        if not _contains_diagram_count(text, diagram_count):
            issues.append(f"{rel}: missing diagram count {diagram_count}")

    redirect = texts.get(REDIRECT_SITE_FILE)
    if redirect is None:
        if files is not None:
            issues.append(f"{REDIRECT_SITE_FILE}: missing redirect page")
    else:
        text = _normalize(redirect)
        for required in ('http-equiv="refresh"', "url=./", 'content="noindex"', 'rel="canonical"'):
            if required not in text:
                issues.append(f"{REDIRECT_SITE_FILE}: missing redirect marker `{required}`")
        if CLAUDE_CODE_MIN_VERSION in text or "kami.zip" in text:
            issues.append(f"{REDIRECT_SITE_FILE}: redirect page should not carry product fact copy")

    return issues


# The site teaches CSS recipes in prose, outside any code fence, so
# `--check-docs` (which reads Markdown fences) cannot see them. That is how the
# homepage kept advertising a 0.5pt closed border with a radius long after the
# linter started failing templates for it, in five locales at once. This guard
# reads the rendered copy of every locale page and fails on the combinations the
# design system forbids outright, so the public surface cannot drift past the
# rules the repository enforces on itself.
FORBIDDEN_SITE_RECIPES = (
    (
        re.compile(r"0\.5pt\s*(?:border|枠線|邊框|边框)[^.。]{0,40}(?:radius|圆角|圓角|角丸)", re.I),
        "sub-1pt closed border paired with a radius (production.md pitfall #2)",
    ),
    (
        re.compile(r"border:\s*0\.5pt\s+solid\s+var\(--brand\)", re.I),
        "closed 0.5pt brand border; mark one edge with border-left instead",
    ),
)


def site_recipe_issues(files: Mapping[str, str] | None = None) -> list[str]:
    """Flag CSS recipes on the public pages that the design system forbids."""
    texts, issues = _file_texts(files)
    if SITE_SURFACE_ABSENT in texts:
        return []
    for rel in (SITE_BASE_PAGE, *SITE_LOCALE_PAGES):
        raw = texts.get(rel)
        if raw is None:
            continue
        visible = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", raw))
        for pattern, why in FORBIDDEN_SITE_RECIPES:
            if pattern.search(visible):
                issues.append(f"{rel}: teaches {why}")
    return issues


def check_site_facts(verbose: bool = False) -> int:
    if not any(public_path(rel).exists() for rel in (*FULL_PUBLIC_FACT_FILES, REDIRECT_SITE_FILE)):
        print("OK: public site facts skipped (site files absent)")
        return 0

    result = 0

    issues = site_fact_issues()
    if not issues:
        scanned = len(FULL_PUBLIC_FACT_FILES) + 1
        print(f"OK: public site facts in sync across {scanned} file(s)")
    else:
        print(f"\nERROR: [site-fact-drift] {len(issues)}")
        for issue in issues:
            print(f"  {issue}")
        if verbose:
            print("  source: shared public constants and template registries")
        result = 1

    recipe_issues = site_recipe_issues()
    if not recipe_issues:
        print(f"OK: no forbidden CSS recipes across {len(SITE_LOCALE_PAGES) + 1} public page(s)")
    else:
        print(f"\nERROR: [site-recipe-drift] {len(recipe_issues)}")
        for issue in recipe_issues:
            print(f"  {issue}")
        if verbose:
            print("  source: references/design.md and production.md pitfall #2")
        result = 1

    structure_issues = site_structure_issues()
    if not structure_issues:
        print(f"OK: locale page structure matches {SITE_BASE_PAGE} across {len(SITE_LOCALE_PAGES)} page(s)")
    else:
        print(f"\nERROR: [site-structure-drift] {len(structure_issues)}")
        for issue in structure_issues:
            print(f"  {issue}")
        if verbose:
            print(f"  source: DOM skeleton comparison against {SITE_BASE_PAGE}")
        result = 1

    return result
