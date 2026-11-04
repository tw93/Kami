"""Shared constants and helpers for kami build scripts."""
from __future__ import annotations

import functools
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, NamedTuple


class TemplateSpec(NamedTuple):
    """Per-template configuration.

    build_max_pages: hard ceiling enforced by `build.py --verify`. 0 = no limit.
    """
    source: str
    build_max_pages: int

ROOT = Path(__file__).resolve().parent.parent
# In a repository checkout the skill lives at <repo>/skills/kami and the
# website at <repo>/site; an installed skill has neither. Use repository tooling
# as the marker so a missing site cannot silently disable repository checks.
REPO_ROOT = (
    ROOT.parent.parent
    if ROOT.parent.name == "skills"
    and (ROOT.parent.parent / "scripts" / "package-skill.sh").is_file()
    else None
)
SITE_ROOT = REPO_ROOT / "site" if REPO_ROOT else None
TEMPLATES = ROOT / "assets" / "templates"
DIAGRAMS = ROOT / "assets" / "diagrams"
EXAMPLES = ROOT / "assets" / "examples"
TOKENS_FILE = ROOT / "references" / "tokens.json"
SOCIAL_PALETTES_FILE = ROOT / "references" / "social-palettes.json"
CHECKS_THRESHOLDS_FILE = ROOT / "references" / "checks_thresholds.json"
SCHEMAS_DIR = ROOT / "references" / "schemas"

PUBLIC_REPO = "tw93/kami"
CLAUDE_CODE_MIN_VERSION = "2.1.142"
CLAUDE_CODE_INSTALL_COMMANDS = (
    f"/plugin marketplace add {PUBLIC_REPO}",
    "/plugin install kami@kami",
)
CODEX_PLUGIN_INSTALL_COMMANDS = (
    f"codex plugin marketplace add {PUBLIC_REPO}",
    "codex plugin add kami@kami",
)
GENERIC_AGENT_INSTALL_COMMAND = f"npx skills add {PUBLIC_REPO} -a claude-code codex cursor -g -y"
CLAUDE_DESKTOP_PACKAGE_URL = "https://github.com/tw93/kami/releases/latest/download/kami.zip"

# Canonical parchment background color, kept here so build/density
# checks share one source of truth instead of redefining the RGB triple.
PARCHMENT_RGB = (0xF5, 0xF4, 0xED)

_HOMEBREW_PREFIXES = (Path("/opt/homebrew"), Path("/usr/local"))


# macOS-only fontconfig cache base; Linux keeps the caller's XDG_CACHE_HOME.
_DARWIN_CACHE_DIR = Path("/private/tmp/kami-fontconfig-cache")


def configure_weasyprint_runtime() -> None:
    """Make platform-native libraries discoverable before importing WeasyPrint.

    On macOS, also surface Homebrew's gobject lib so cairo/pango can load.
    Linux and other platforms keep the caller's XDG cache base unchanged; the
    system loader and fontconfig already follow the platform default.
    """
    if sys.platform != "darwin":
        return

    os.environ.setdefault("XDG_CACHE_HOME", str(_DARWIN_CACHE_DIR))

    brew_lib = next(
        (p / "lib" for p in _HOMEBREW_PREFIXES if (p / "lib" / "libgobject-2.0.dylib").exists()),
        None,
    )
    if brew_lib is None:
        return

    existing = os.environ.get("DYLD_FALLBACK_LIBRARY_PATH", "")
    paths = [path for path in existing.split(":") if path]
    brew_lib_str = str(brew_lib)
    if brew_lib_str in paths:
        return

    os.environ["DYLD_FALLBACK_LIBRARY_PATH"] = ":".join([brew_lib_str, *paths])

# Cool / neutral gray hex values that violate the "warm undertone only" rule.
COOL_GRAY_BLOCKLIST = {
    "#888", "#888888", "#666", "#666666", "#999", "#999999",
    "#ccc", "#cccccc", "#ddd", "#dddddd", "#eee", "#eeeeee",
    "#111", "#111111", "#222", "#222222", "#333", "#333333",
    "#444", "#444444", "#555", "#555555", "#777", "#777777",
    "#aaa", "#aaaaaa", "#bbb", "#bbbbbb",
    # Tailwind cool grays
    "#6b7280", "#9ca3af", "#d1d5db", "#e5e7eb", "#f3f4f6",
    "#4b5563", "#374151", "#1f2937", "#111827",
    # Bootstrap-like neutrals
    "#f8f9fa", "#e9ecef", "#dee2e6", "#ced4da", "#adb5bd",
    "#6c757d", "#495057", "#343a40", "#212529",
}


# ---------------------------------------------------------------------------
# Template registry
#
# Single source of truth for HTML targets used by build.py.
# See TemplateSpec for field meanings.
# ---------------------------------------------------------------------------
HTML_TEMPLATES: dict[str, TemplateSpec] = {
    # Core six
    "one-pager":    TemplateSpec("one-pager.html",    1),
    "letter":       TemplateSpec("letter.html",       1),
    "long-doc":     TemplateSpec("long-doc.html",     0),
    "portfolio":    TemplateSpec("portfolio.html",    0),
    "resume":       TemplateSpec("resume.html",       2),
    "one-pager-en": TemplateSpec("one-pager-en.html", 1),
    "letter-en":    TemplateSpec("letter-en.html",    1),
    "long-doc-en":  TemplateSpec("long-doc-en.html",  0),
    "portfolio-en": TemplateSpec("portfolio-en.html", 0),
    "resume-en":    TemplateSpec("resume-en.html",    2),
    # Korean
    "one-pager-ko":     TemplateSpec("one-pager-ko.html",     1),
    "letter-ko":        TemplateSpec("letter-ko.html",        1),
    "long-doc-ko":      TemplateSpec("long-doc-ko.html",      0),
    "portfolio-ko":     TemplateSpec("portfolio-ko.html",     0),
    "resume-ko":        TemplateSpec("resume-ko.html",        2),
    "equity-report-ko": TemplateSpec("equity-report-ko.html", 3),
    "changelog-ko":     TemplateSpec("changelog-ko.html",     2),
    "slides-weasy-ko":  TemplateSpec("slides-weasy-ko.html",  0),
    # Equity report
    "equity-report":    TemplateSpec("equity-report.html",    3),
    "equity-report-en": TemplateSpec("equity-report-en.html", 3),
    # Changelog
    "changelog":    TemplateSpec("changelog.html",    2),
    "changelog-en": TemplateSpec("changelog-en.html", 2),
    # Slides (WeasyPrint default)
    "slides-weasy":    TemplateSpec("slides-weasy.html",    0),
    "slides-weasy-en": TemplateSpec("slides-weasy-en.html", 0),
    # Social cards: one 1242x1660 page per image; 18 is Xiaohongshu's image cap
    "social-cards":    TemplateSpec("social-cards.html",    18),
    "social-cards-en": TemplateSpec("social-cards-en.html", 18),
    "social-cards-ko": TemplateSpec("social-cards-ko.html", 18),
}

SCREEN_TEMPLATES: dict[str, str] = {
    "landing-page":    "landing-page.html",
    "landing-page-en": "landing-page-en.html",
    "landing-page-ko": "landing-page-ko.html",
}

# Editable PPTX fallback decks, generated by python-pptx scripts.
PPTX_TEMPLATES: dict[str, str] = {
    "slides":    "slides.py",
    "slides-en": "slides-en.py",
}

# Markdown-first Marp slide variants. The Markdown files are the authoring
# entry points; their sibling CSS themes stay self-contained for the Marp CLI.
MARP_TEMPLATES: dict[str, str] = {
    "slides-marp":    "marp/slides-marp.md",
    "slides-marp-en": "marp/slides-marp-en.md",
}

# Diagram HTMLs live in assets/diagrams and have no page-count contract.
# Registered here (not in build.py) so all template registries share one home.
# The Mermaid-sourced ones are produced via scripts/mermaid_normalize.py.
DIAGRAM_TEMPLATES: dict[str, str] = {
    "diagram-architecture":       "architecture.html",
    "diagram-architecture-board": "architecture-board.html",
    "diagram-flowchart":     "flowchart.html",
    "diagram-quadrant":      "quadrant.html",
    "diagram-bar-chart":     "bar-chart.html",
    "diagram-line-chart":    "line-chart.html",
    "diagram-donut-chart":   "donut-chart.html",
    "diagram-state-machine": "state-machine.html",
    "diagram-timeline":      "timeline.html",
    "diagram-swimlane":      "swimlane.html",
    "diagram-tree":          "tree.html",
    "diagram-layer-stack":   "layer-stack.html",
    "diagram-venn":          "venn.html",
    "diagram-candlestick":   "candlestick.html",
    "diagram-waterfall":     "waterfall.html",
    # Mermaid-sourced (beautiful-mermaid + scripts/mermaid_normalize.py)
    "diagram-sequence":      "sequence.html",
    "diagram-class":         "class.html",
    "diagram-er":            "er.html",
}


PUBLIC_DOCUMENT_TEMPLATE_KINDS = {
    "one-pager",
    "letter",
    "long-doc",
    "portfolio",
    "resume",
    "slides",
    "equity-report",
    "changelog",
    "social-cards",
}


def public_template_kind(name: str) -> str:
    """Map a registry template name to the public kind it belongs to."""
    for suffix in ("-en", "-ko"):
        if name.endswith(suffix):
            name = name[: -len(suffix)]
            break
    if name.startswith("slides-weasy"):
        return "slides"
    return name


def public_document_template_kinds() -> set[str]:
    """Return every normalized document kind represented by HTML_TEMPLATES.

    Do not filter through ``PUBLIC_DOCUMENT_TEMPLATE_KINDS`` here. Callers use
    this derived set to detect a newly registered document kind whose public
    facts or content schema have not been added yet.
    """
    return {
        public_template_kind(name)
        for name in HTML_TEMPLATES
    }


def public_document_template_count() -> int:
    return len(public_document_template_kinds())


def rel_to_root(path: Path) -> Path:
    """Return `path` relative to ROOT when possible, else the path unchanged."""
    return path.relative_to(ROOT) if path.is_relative_to(ROOT) else path


def resolve_input(raw: str | Path) -> Path:
    """Resolve a user-supplied file argument.

    Agents call the checks from the directory holding their document, so a
    relative path means the caller's working directory first. Skill-relative
    paths (`assets/examples/resume.pdf`) keep working as the fallback.
    """
    path = Path(raw).expanduser()
    if path.is_absolute():
        return path
    from_cwd = Path.cwd() / path
    if from_cwd.exists():
        return from_cwd
    return ROOT / path


def default_example_pdfs() -> list[str]:
    """Return every rendered example PDF, the default scan set for PDF checks."""
    return [str(p) for p in sorted(EXAMPLES.glob("*.pdf"))]


def iter_template_files(
    *,
    include_py: bool = False,
    include_diagrams: bool = False,
    include_marp_css: bool = False,
) -> list[Path]:
    """Collect template-family files for scanning.

    One shared walker so lint, token-sync, and future checks cannot silently
    diverge in coverage (a divergence is how the Marp CSS family once slipped
    out of the lint scan while staying in the token scan).
    """
    targets: list[Path] = list(TEMPLATES.glob("*.html"))
    if include_py:
        targets.extend(TEMPLATES.glob("*.py"))
    if include_diagrams and DIAGRAMS.exists():
        targets.extend(DIAGRAMS.glob("*.html"))
    if include_marp_css:
        marp_dir = TEMPLATES / "marp"
        if marp_dir.exists():
            targets.extend(marp_dir.glob("*.css"))
    return sorted(targets)


@functools.lru_cache(maxsize=1)
def kami_version() -> str:
    """Return the canonical Kami version from the tracked VERSION file."""
    return (ROOT / "VERSION").read_text(encoding="utf-8").strip()


# Social cards are images, not print pages: their papers live in
# references/social-palettes.json and are allowed only in social-card files.
# A filled card set keeps the template's --social-* tokens, which is how
# a renamed output is still recognised.
SOCIAL_PAPER_ROLES = ("bg", "fg", "accent", "muted", "line")
SOCIAL_FINGERPRINT = re.compile(r"--social-[a-z]+-(?:bg|fg|accent|muted|line)\s*:")


@functools.lru_cache(maxsize=1)
def load_social_palettes() -> dict[str, dict[str, str]]:
    data = json.loads(SOCIAL_PALETTES_FILE.read_text(encoding="utf-8"))
    return {name: paper for name, paper in data.items() if not name.startswith("$")}


def social_palette_values() -> set[str]:
    return {
        paper[role].lower()
        for paper in load_social_palettes().values()
        for role in SOCIAL_PAPER_ROLES
    }


def is_social_cards(path: Path, text: str | None = None) -> bool:
    """True for the social-cards templates, their demos, and filled card sets."""
    if path.name.startswith(("social-cards", "demo-social-cards")):
        return True
    if text is None:
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return False
    return bool(SOCIAL_FINGERPRINT.search(text))


@functools.lru_cache(maxsize=1)
def load_tokens() -> dict[str, str]:
    return json.loads(TOKENS_FILE.read_text(encoding="utf-8"))


def token_value(name: str) -> str:
    key = name if name.startswith("--") else f"--{name}"
    return load_tokens()[key]


def build_targets() -> dict[str, tuple[str, int]]:
    """Return target -> (source, max_pages) mapping for build.py."""
    return {name: (spec.source, spec.build_max_pages) for name, spec in HTML_TEMPLATES.items()}


def screen_targets() -> dict[str, str]:
    """Return target -> source mapping for browser-only HTML templates."""
    return dict(SCREEN_TEMPLATES)


def pptx_targets() -> dict[str, str]:
    """Return target -> source mapping for python-pptx slide scripts."""
    return dict(PPTX_TEMPLATES)


def marp_targets() -> dict[str, str]:
    """Return target -> source mapping for Markdown-first Marp decks."""
    return dict(MARP_TEMPLATES)


def diagram_targets() -> dict[str, str]:
    """Return target -> source mapping for assets/diagrams HTML templates."""
    return dict(DIAGRAM_TEMPLATES)


@functools.lru_cache(maxsize=1)
def load_checks_thresholds() -> dict[str, Any]:
    """Return rhythm / density / orphan thresholds.

    Falls back to baked-in defaults if the JSON is missing so build.py works
    on a half-installed checkout.
    """
    if CHECKS_THRESHOLDS_FILE.exists():
        return json.loads(CHECKS_THRESHOLDS_FILE.read_text(encoding="utf-8"))
    return {
        "rhythm": {"max_content_run": 5, "divider_min_deck_size": 12},
        "density": {"warn_pct": 0.25, "sparse_pct": 0.50, "last_page_pct": 0.60, "dpi": 36},
        "resume_balance": {
            "min_fill_pct": 0.83,
            "max_fill_pct": 0.95,
            "max_gap_pct": 0.12,
            "dpi": 36,
        },
        "orphan": {"max_words": 2, "max_chars": 15},
        "visual": {"dpi": 110},
    }


def content_schema_types() -> list[str]:
    """Return doc types that have a content schema in references/schemas."""
    if not SCHEMAS_DIR.exists():
        return []
    return sorted(p.stem for p in SCHEMAS_DIR.glob("*.json"))
