"""Shared constants and helpers for kami build and stabilize scripts."""
from __future__ import annotations

import functools
import json
import os
import sys
from pathlib import Path
from typing import Any, NamedTuple


class TemplateSpec(NamedTuple):
    """Per-template configuration.

    build_max_pages: hard ceiling enforced by `build.py --verify`. 0 = no limit.
    stabilize_max_pages: target pages for the overflow solver in `stabilize.py`.
        0 = solver disabled. The two values can differ because stabilize aims
        to keep doc-style targets within an editorial range while build only
        catches gross overflow.
    """
    source: str
    build_max_pages: int
    stabilize_max_pages: int

ROOT = Path(__file__).resolve().parent.parent
TEMPLATES = ROOT / "assets" / "templates"
DIAGRAMS = ROOT / "assets" / "diagrams"
EXAMPLES = ROOT / "assets" / "examples"
TOKENS_FILE = ROOT / "references" / "tokens.json"
CHECKS_THRESHOLDS_FILE = ROOT / "references" / "checks_thresholds.json"
COOL_GRAY_BUCKETS_FILE = ROOT / "references" / "cool_gray_buckets.json"
CROSS_TEMPLATE_ALLOWLIST_FILE = ROOT / "references" / "cross_template_diff_allowlist.json"

# Canonical parchment background color, kept here so build/stabilize/density
# checks share one source of truth instead of redefining the RGB triple.
PARCHMENT_HEX = "#f5f4ed"
PARCHMENT_RGB = (0xF5, 0xF4, 0xED)

_HOMEBREW_PREFIXES = (Path("/opt/homebrew"), Path("/usr/local"))


def _default_cache_dir() -> Path:
    """Return a sensible per-platform fontconfig cache directory."""
    if sys.platform == "darwin":
        return Path("/private/tmp/kami-fontconfig-cache")
    xdg = os.environ.get("XDG_CACHE_HOME")
    if xdg:
        return Path(xdg) / "kami"
    return Path.home() / ".cache" / "kami"


def configure_weasyprint_runtime() -> None:
    """Make platform-native libraries discoverable before importing WeasyPrint.

    On macOS, also surface Homebrew's gobject lib so cairo/pango can load.
    On Linux/other, only the fontconfig cache hint is set; the system loader
    is expected to find the libraries.
    """
    os.environ.setdefault("XDG_CACHE_HOME", str(_default_cache_dir()))

    if sys.platform != "darwin":
        return

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
# Single source of truth for HTML targets across build.py and stabilize.py.
# See TemplateSpec for field meanings.
# ---------------------------------------------------------------------------
HTML_TEMPLATES: dict[str, TemplateSpec] = {
    # Core six
    "one-pager":    TemplateSpec("one-pager.html",    1, 1),
    "letter":       TemplateSpec("letter.html",       1, 1),
    "long-doc":     TemplateSpec("long-doc.html",     0, 9),
    "portfolio":    TemplateSpec("portfolio.html",    0, 8),
    "resume":       TemplateSpec("resume.html",       2, 2),
    "one-pager-en": TemplateSpec("one-pager-en.html", 1, 1),
    "letter-en":    TemplateSpec("letter-en.html",    1, 1),
    "long-doc-en":  TemplateSpec("long-doc-en.html",  0, 9),
    "portfolio-en": TemplateSpec("portfolio-en.html", 0, 8),
    "resume-en":    TemplateSpec("resume-en.html",    2, 2),
    # Equity report
    "equity-report":    TemplateSpec("equity-report.html",    3, 0),
    "equity-report-en": TemplateSpec("equity-report-en.html", 3, 0),
    # Changelog
    "changelog":    TemplateSpec("changelog.html",    2, 0),
    "changelog-en": TemplateSpec("changelog-en.html", 2, 0),
    # Slides (WeasyPrint default)
    "slides-weasy":    TemplateSpec("slides-weasy.html",    0, 0),
    "slides-weasy-en": TemplateSpec("slides-weasy-en.html", 0, 0),
}

SCREEN_TEMPLATES: dict[str, str] = {
    "landing-page":    "landing-page.html",
    "landing-page-en": "landing-page-en.html",
}


def build_targets() -> dict[str, tuple[str, int]]:
    """Return target -> (source, max_pages) mapping for build.py."""
    return {name: (spec.source, spec.build_max_pages) for name, spec in HTML_TEMPLATES.items()}


def screen_targets() -> dict[str, str]:
    """Return target -> source mapping for browser-only HTML templates."""
    return dict(SCREEN_TEMPLATES)


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
        "density": {"warn_pct": 0.25, "sparse_pct": 0.50, "dpi": 36},
        "orphan": {"max_words": 2, "max_chars": 15},
    }


@functools.lru_cache(maxsize=1)
def load_cross_template_allowlist() -> dict[str, Any]:
    """Return the CN/EN drift allowlist. Missing file -> empty allowlist."""
    if CROSS_TEMPLATE_ALLOWLIST_FILE.exists():
        return json.loads(CROSS_TEMPLATE_ALLOWLIST_FILE.read_text(encoding="utf-8"))
    return {"always_allowed": [], "per_pair_allowed": {}}


@functools.lru_cache(maxsize=1)
def load_cool_gray_buckets() -> list[dict[str, Any]]:
    """Return luminance buckets used to remap cool-gray hex literals."""
    if COOL_GRAY_BUCKETS_FILE.exists():
        return json.loads(COOL_GRAY_BUCKETS_FILE.read_text(encoding="utf-8"))["buckets"]
    return [
        {"lum_max": 0.35, "replacement": "#4D4C48"},
        {"lum_max": 0.72, "replacement": "#87867F"},
        {"lum_max": 1.00, "replacement": "#E8E6DC"},
    ]


def stabilize_targets() -> dict[str, tuple[str, int]]:
    """Return target -> (source, max_pages) mapping for stabilize.py.

    Only includes templates with a non-zero stabilize ceiling (the ones the
    overflow solver should constrain).
    """
    return {
        name: (spec.source, spec.stabilize_max_pages)
        for name, spec in HTML_TEMPLATES.items()
        if spec.stabilize_max_pages > 0
    }
