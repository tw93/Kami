"""PDF-side and content-shape checks for kami documents.

Splits out from build.py:
  - check_placeholders: scan filled HTML for unreplaced `{{...}}` tokens.
  - check_orphans:      scan rendered PDFs for short trailing lines (typographic orphans).
  - check_density:      scan rendered PDFs for pages with too much trailing whitespace.
  - check_resume_balance: scan resume PDFs for exact two-page balance.
  - check_rhythm:       scan slides Python source for monotonous deck sequences.

Density scanning uses a parchment-aware pixel sweep. The hot path is
vectorized with NumPy when available and falls back to a pure-Python loop.
Thresholds and DPI live in `references/checks_thresholds.json`.
"""
from __future__ import annotations

import re
from html import unescape
from html.parser import HTMLParser
from pathlib import Path

from optional_deps import MissingDepError, require_pymupdf, require_pypdf_reader
from shared import (
    PARCHMENT_RGB,
    ROOT,
    TEMPLATES,
    default_example_pdfs,
    load_checks_thresholds,
    pptx_targets,
    rel_to_root,
)

PLACEHOLDER = re.compile(r"\{\{[^}]+\}\}")
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
        path = Path(raw)
        if not path.is_absolute():
            path = ROOT / path
        if not path.exists():
            print(f"ERROR: {raw}: file not found")
            failures += 1
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        hits = list(dict.fromkeys(PLACEHOLDER.findall(text)))
        rel = rel_to_root(path)
        if hits:
            print(f"ERROR: {rel}: unfilled placeholder(s): {', '.join(hits)}")
            failures += 1
        else:
            print(f"OK: {rel}: no placeholders")

    return 0 if failures == 0 else 1


# ---------- markdown residue check ----------

def _decode_css_escapes(text: str) -> str:
    """Decode the CSS escapes needed to recognize property names and values."""
    def replace_hex(match: re.Match) -> str:
        try:
            return chr(int(match.group(1), 16))
        except (ValueError, OverflowError):
            return ""

    text = re.sub(r"\\([0-9a-fA-F]{1,6})\s?", replace_hex, text)
    return re.sub(r"\\([^\r\n])", r"\1", text)


def _css_numeric_value(value: str) -> tuple[float, str] | None:
    """Parse a small, deterministic subset of CSS numeric expressions."""
    value = re.sub(r"\s+", "", value.lower())
    direct = re.fullmatch(r"([-+]?(?:\d+(?:\.\d*)?|\.\d+))(%|[a-z]+)?", value)
    if direct:
        return float(direct.group(1)), direct.group(2) or ""
    function = re.fullmatch(r"(calc|min|max|clamp)\((.*)\)", value)
    if not function:
        return None
    name, body = function.groups()
    if name == "calc":
        return _css_numeric_value(body)
    parts = [_css_numeric_value(part) for part in body.split(",")]
    if not parts or any(part is None for part in parts):
        return None
    parsed = [part for part in parts if part is not None]
    units = {unit for number, unit in parsed if number != 0 and unit}
    if len(units) > 1:
        return None
    unit = next(iter(units), next((u for _, u in parsed if u), ""))
    values = [number for number, _ in parsed]
    if name == "min":
        return min(values), unit
    if name == "max":
        return max(values), unit
    if len(values) == 3:
        lower, preferred, upper = values
        return max(lower, min(preferred, upper)), unit
    return None


def _is_zero_css_value(value: str) -> bool:
    parsed = _css_numeric_value(value)
    return parsed is not None and parsed[0] == 0


def _is_extreme_css_offset(value: str) -> bool:
    parsed = _css_numeric_value(value)
    if parsed is None:
        return False
    number, unit = parsed
    threshold = 100 if unit in {"%", "em", "rem"} else 2000
    return abs(number) >= threshold


class _DocumentStyleCollector(HTMLParser):
    """Collect stylesheet bodies and decoded inline style attributes."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.style_blocks: list[str] = []
        self.inline_styles: list[str] = []
        self._style_parts: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() == "style":
            self._style_parts = []
        self.inline_styles.extend(
            value
            for name, value in attrs
            if name.lower() == "style" and value is not None
        )

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "style" and self._style_parts is not None:
            self.style_blocks.append("".join(self._style_parts))
            self._style_parts = None

    def handle_data(self, data: str) -> None:
        if self._style_parts is not None:
            self._style_parts.append(data)

    def close(self) -> None:
        super().close()
        if self._style_parts is not None:
            self.style_blocks.append("".join(self._style_parts))
            self._style_parts = None


def _custom_property_names(css: str) -> list[str]:
    """Return custom-property declarations while ignoring quoted text.

    This intentionally over-collects declarations from selectors and at-rules:
    any declaration outside an unconditional root rule makes cross-rule
    resolution unsafe. False positives therefore disable an optimization
    instead of admitting hidden evidence.
    """
    names: list[str] = []
    quote = ""
    escaped = False
    index = 0
    while index < len(css):
        char = css[index]
        if escaped:
            escaped = False
            index += 1
            continue
        if char == "\\":
            escaped = True
            index += 1
            continue
        if quote:
            if char == quote:
                quote = ""
            index += 1
            continue
        if char in {'"', "'"}:
            quote = char
            index += 1
            continue
        if css.startswith("--", index):
            match = re.match(r"--[\w-]+", css[index:])
            if match:
                name = match.group(0)
                end = index + len(name)
                cursor = end
                while cursor < len(css) and css[cursor].isspace():
                    cursor += 1
                if cursor < len(css) and css[cursor] == ":":
                    names.append(name)
                index = end
                continue
        index += 1
    return names


def _top_level_css_rules(css: str) -> list[tuple[str, str]] | None:
    """Split a stylesheet into balanced top-level ``(prelude, body)`` rules."""
    rules: list[tuple[str, str]] = []
    start = 0
    index = 0
    quote = ""
    escaped = False
    paren_depth = 0
    bracket_depth = 0
    while index < len(css):
        char = css[index]
        if escaped:
            escaped = False
            index += 1
            continue
        if char == "\\":
            escaped = True
            index += 1
            continue
        if quote:
            if char == quote:
                quote = ""
            index += 1
            continue
        if char in {'"', "'"}:
            quote = char
            index += 1
            continue
        if char == "(":
            paren_depth += 1
        elif char == ")":
            if paren_depth == 0:
                return None
            paren_depth -= 1
        elif char == "[":
            bracket_depth += 1
        elif char == "]":
            if bracket_depth == 0:
                return None
            bracket_depth -= 1
        elif char == ";" and paren_depth == 0 and bracket_depth == 0:
            start = index + 1
        elif char == "{" and paren_depth == 0 and bracket_depth == 0:
            prelude = css[start:index].strip()
            body_start = index + 1
            depth = 1
            inner_quote = ""
            inner_escaped = False
            index += 1
            while index < len(css) and depth:
                inner = css[index]
                if inner_escaped:
                    inner_escaped = False
                elif inner == "\\":
                    inner_escaped = True
                elif inner_quote:
                    if inner == inner_quote:
                        inner_quote = ""
                elif inner in {'"', "'"}:
                    inner_quote = inner
                elif inner == "{":
                    depth += 1
                elif inner == "}":
                    depth -= 1
                index += 1
            if depth or inner_quote:
                return None
            rules.append((prelude, css[body_start:index - 1]))
            start = index
            paren_depth = 0
            bracket_depth = 0
            continue
        elif char == "}" and paren_depth == 0 and bracket_depth == 0:
            return None
        index += 1
    if quote or escaped or paren_depth or bracket_depth:
        return None
    return rules


def _css_declarations(body: str) -> list[tuple[str, str]] | None:
    """Parse a declaration block without splitting quoted or functional values."""
    if "{" in body or "}" in body:
        return None
    parts: list[str] = []
    start = 0
    quote = ""
    escaped = False
    paren_depth = 0
    bracket_depth = 0
    for index, char in enumerate(body):
        if escaped:
            escaped = False
            continue
        if char == "\\":
            escaped = True
            continue
        if quote:
            if char == quote:
                quote = ""
            continue
        if char in {'"', "'"}:
            quote = char
        elif char == "(":
            paren_depth += 1
        elif char == ")":
            if paren_depth == 0:
                return None
            paren_depth -= 1
        elif char == "[":
            bracket_depth += 1
        elif char == "]":
            if bracket_depth == 0:
                return None
            bracket_depth -= 1
        elif char == ";" and paren_depth == 0 and bracket_depth == 0:
            parts.append(body[start:index])
            start = index + 1
    if quote or escaped or paren_depth or bracket_depth:
        return None
    parts.append(body[start:])

    declarations: list[tuple[str, str]] = []
    for part in parts:
        name, separator, value = part.partition(":")
        if not separator:
            continue
        declarations.append((re.sub(r"\s+", "", name), value.strip()))
    return declarations


def _document_custom_properties(raw: str) -> dict[str, str]:
    """Return unconditional root properties safe to resolve across rules.

    The checker has no CSS cascade. A property is reusable only when every
    declaration is on an unconditional ``:root`` or ``html`` rule and every
    value is identical. Scoped, conditional, inline, registered, or malformed
    declarations disable that property instead of weakening fail-closed checks.
    """
    collector = _DocumentStyleCollector()
    collector.feed(raw)
    collector.close()

    all_names: list[str] = []
    root_values: dict[str, list[str]] = {}
    for block in collector.style_blocks:
        clean = re.sub(r"/\*.*?\*/", "", block, flags=re.S)
        clean = _decode_css_escapes(clean)
        if re.search(r"@property\b", clean, flags=re.I):
            return {}
        all_names.extend(_custom_property_names(clean))
        rules = _top_level_css_rules(clean)
        if rules is None:
            return {}
        for selectors, body in rules:
            roots = [selector.strip().lower() for selector in selectors.split(",")]
            if not roots or any(selector not in {":root", "html"} for selector in roots):
                continue
            declarations = _css_declarations(body)
            if declarations is None:
                return {}
            for name, value in declarations:
                if not name.startswith("--"):
                    continue
                value = re.sub(r"!\s*important\s*$", "", value, flags=re.I).strip()
                root_values.setdefault(name, []).append(value)
    for inline in collector.inline_styles:
        clean = re.sub(r"/\*.*?\*/", "", inline, flags=re.S)
        all_names.extend(_custom_property_names(_decode_css_escapes(clean)))

    counts: dict[str, int] = {}
    for name in all_names:
        counts[name] = counts.get(name, 0) + 1
    return {
        name: values[0]
        for name, values in root_values.items()
        if counts.get(name) == len(values) and len(set(values)) == 1
    }


def _style_state(
    style: str,
    *,
    fail_closed: bool,
    replaced_element: bool = False,
    custom_properties: dict[str, str] | None = None,
) -> tuple[bool, bool]:
    """Return ``(hidden, ambiguous)`` for a declaration block.

    CSS comments are removed first because browsers accept declarations such
    as ``display/**/: none``. The coverage gate must not treat those elements
    as visible merely because the declaration was split by a comment.
    """
    clean = re.sub(r"/\*.*?\*/", "", style, flags=re.S)
    clean = _decode_css_escapes(clean)
    declarations = _css_declarations(clean)
    if declarations is None:
        return False, fail_closed
    properties: dict[str, tuple[str, bool]] = {
        name: (value, False) for name, value in (custom_properties or {}).items()
    }
    for name, value in declarations:
        name = re.sub(r"\s+", "", name)
        if not name.startswith("--"):
            name = name.lower()
        important = re.search(r"!\s*important\s*$", value, flags=re.I) is not None
        value = re.sub(r"!\s*important\s*$", "", value, flags=re.I)
        value = re.sub(r"\s+", "", value)
        previous = properties.get(name)
        if previous is None or important or not previous[1]:
            properties[name] = (value, important)

    def resolved(name: str, depth: int = 0) -> tuple[str, bool]:
        if name not in properties:
            return "", False
        if depth > 8:
            return "", True
        value = properties[name][0]
        match = re.fullmatch(r"(?i:var)\((--[\w-]+)(?:,(.*))?\)", value)
        if not match:
            return value, False
        custom_name, fallback = match.groups()
        if custom_name in properties:
            return resolved(custom_name, depth + 1)
        if fallback is None:
            return "", True
        temporary_name = f"--kami-fallback-{depth}"
        properties[temporary_name] = (fallback, False)
        try:
            return resolved(temporary_name, depth + 1)
        finally:
            properties.pop(temporary_name, None)

    def resolved_css(name: str) -> tuple[str, bool]:
        value, ambiguous = resolved(name)
        return value.lower(), ambiguous

    display, display_ambiguous = resolved_css("display")
    visibility, visibility_ambiguous = resolved_css("visibility")
    if fail_closed and (
        (display_ambiguous and "display" in properties)
        or (visibility_ambiguous and "visibility" in properties)
    ):
        return False, True
    if display == "none" or display.startswith("var("):
        return True, False
    if visibility in {"hidden", "collapse"} or visibility.startswith("var("):
        return True, False
    opacity, opacity_ambiguous = resolved_css("opacity")
    if opacity_ambiguous and "opacity" in properties and fail_closed:
        return False, True
    if _is_zero_css_value(opacity):
        return True, False
    font_size, font_size_ambiguous = resolved_css("font-size")
    if font_size_ambiguous and "font-size" in properties and fail_closed:
        return False, True
    if _is_zero_css_value(font_size):
        return True, False
    color, color_ambiguous = resolved_css("color")
    if color_ambiguous and "color" in properties and fail_closed:
        return False, True
    if color == "transparent":
        return True, False
    transform, transform_ambiguous = resolved_css("transform")
    if transform_ambiguous and "transform" in properties and fail_closed:
        return False, True
    if (
        re.search(r"scale(?:x|y)?\([-+]?(?:0+(?:\.0*)?|\.0+)\)", transform)
        or re.search(
            r"scale\([-+]?(?:0+(?:\.0*)?|\.0+),"
            r"[-+]?(?:0+(?:\.0*)?|\.0+)\)",
            transform,
        )
    ):
        return True, False
    matrix = re.search(r"matrix\(([^)]*)\)", transform)
    if matrix:
        try:
            values = [float(value) for value in matrix.group(1).split(",")]
        except ValueError:
            values = []
        if len(values) == 6 and all(value == 0 for value in values[:4]):
            return True, False
    if re.search(r"translate(?:x|y)?\([^)]*(?:-[2-9]\d{3,}|-[1-9]\d{4,})", transform):
        return True, False
    if fail_closed and "transform" in properties and "var(" in transform:
        return False, True
    for property_name in ("scale", "zoom"):
        value, ambiguous = resolved_css(property_name)
        if ambiguous and property_name in properties and fail_closed:
            return False, True
        if _is_zero_css_value(value):
            return True, False
    content_visibility, content_visibility_ambiguous = resolved_css("content-visibility")
    if content_visibility_ambiguous and "content-visibility" in properties and fail_closed:
        return False, True
    if content_visibility == "hidden":
        return True, False
    filter_value, filter_ambiguous = resolved_css("filter")
    if filter_ambiguous and "filter" in properties and fail_closed:
        return False, True
    if re.search(r"opacity\((?:0+(?:\.0*)?|\.0+)(?:%)?\)", filter_value):
        return True, False
    if fail_closed and "filter" in properties and "url(" in filter_value:
        return False, True
    if fail_closed:
        for property_name in ("mask", "mask-image", "-webkit-mask", "-webkit-mask-image"):
            value, ambiguous = resolved_css(property_name)
            if property_name in properties and (ambiguous or value not in {"", "none"}):
                return False, True
    if fail_closed:
        for property_name in (
            "top", "right", "bottom", "left", "inset", "inset-inline",
            "inset-block", "margin-top", "margin-right", "margin-bottom",
            "margin-left",
        ):
            value, ambiguous = resolved_css(property_name)
            if property_name not in properties:
                continue
            if ambiguous:
                return False, True
            if _is_extreme_css_offset(value):
                return True, False
    text_indent, text_indent_ambiguous = resolved_css("text-indent")
    if text_indent_ambiguous and "text-indent" in properties and fail_closed:
        return False, True
    if _is_extreme_css_offset(text_indent):
        return True, False
    clip, clip_ambiguous = resolved_css("clip")
    clip_path, clip_path_ambiguous = resolved_css("clip-path")
    if fail_closed and (
        (clip_ambiguous and "clip" in properties)
        or (clip_path_ambiguous and "clip-path" in properties)
    ):
        return False, True
    if clip in {"rect(0,0,0,0)", "rect(0px,0px,0px,0px)"}:
        return True, False
    if clip_path in {"inset(50%)", "inset(100%)", "circle(0)", "circle(0px)"}:
        return True, False
    if fail_closed and "clip" in properties and clip not in {"", "auto"}:
        return False, True
    if fail_closed and "clip-path" in properties and clip_path not in {"", "none"}:
        return False, True
    width, width_ambiguous = resolved_css("width")
    max_width, max_width_ambiguous = resolved_css("max-width")
    height, height_ambiguous = resolved_css("height")
    max_height, max_height_ambiguous = resolved_css("max-height")
    overflow, overflow_ambiguous = resolved_css("overflow")
    if fail_closed and (
        (width_ambiguous and "width" in properties)
        or (max_width_ambiguous and "max-width" in properties)
        or (height_ambiguous and "height" in properties)
        or (max_height_ambiguous and "max-height" in properties)
    ):
        return False, True
    if overflow_ambiguous and "overflow" in properties and fail_closed:
        return False, True
    zero_width = _is_zero_css_value(width) or _is_zero_css_value(max_width)
    zero_height = _is_zero_css_value(height) or _is_zero_css_value(max_height)
    if (zero_width or zero_height) and (
        replaced_element or overflow in {"hidden", "clip"}
    ):
        return True, False
    if fail_closed:
        for property_name, value, ambiguous in (
            ("opacity", opacity, opacity_ambiguous),
            ("font-size", font_size, font_size_ambiguous),
            ("width", width, width_ambiguous),
            ("max-width", max_width, max_width_ambiguous),
            ("height", height, height_ambiguous),
            ("max-height", max_height, max_height_ambiguous),
        ):
            if property_name in properties and (
                ambiguous or ("(" in value and _css_numeric_value(value) is None)
            ):
                return False, True
    return False, False


def _style_hides(
    style: str,
    *,
    fail_closed: bool,
    replaced_element: bool = False,
    custom_properties: dict[str, str] | None = None,
) -> bool:
    return _style_state(
        style,
        custom_properties=custom_properties,
        fail_closed=fail_closed,
        replaced_element=replaced_element,
    )[0]


def _css_hidden_filters(
    raw: str,
    *,
    fail_closed: bool,
    custom_properties: dict[str, str] | None = None,
) -> tuple[
    set[str], set[str], set[str], set[tuple[str, str | None]],
    set[str], set[str], set[str], set[tuple[str, str | None]], bool,
]:
    """Return conservative class, id, and tag filters for hidden CSS rules.

    The stdlib parser does not implement the CSS cascade. For compound
    selectors, it marks the target class/id when available; for a bare target
    such as ``.concealed img``, it marks the nearest ancestor class/id. This
    can reject an ambiguous document, but it cannot turn hidden evidence into
    a coverage pass. Pseudo-elements are ignored because they do not hide the
    underlying element.
    """
    hidden_classes: set[str] = set()
    hidden_ids: set[str] = set()
    hidden_tags: set[str] = set()
    hidden_attrs: set[tuple[str, str | None]] = set()
    ambiguous_classes: set[str] = set()
    ambiguous_ids: set[str] = set()
    ambiguous_tags: set[str] = set()
    ambiguous_attrs: set[tuple[str, str | None]] = set()
    globally_ambiguous = False
    decoded_markup = unescape(raw)
    if fail_closed and re.search(
        r"<link\b[^>]*\bstylesheet\b[^>]*>",
        decoded_markup,
        flags=re.I,
    ):
        ambiguous_tags.add("*")
        globally_ambiguous = True
    style_blocks = re.findall(r"<style\b[^>]*>(.*?)</style\s*>", raw, flags=re.I | re.S)
    for block in style_blocks:
        clean = re.sub(r"/\*.*?\*/", "", block, flags=re.S)
        clean = _decode_css_escapes(clean)
        if fail_closed and re.search(r"@import\b", clean, flags=re.I):
            ambiguous_tags.add("*")
            globally_ambiguous = True
        for selectors, body in re.findall(r"([^{}]+)\{([^{}]*)\}", clean, flags=re.S):
            hides, body_ambiguous = _style_state(
                body,
                fail_closed=fail_closed,
                custom_properties=custom_properties,
            )
            if not hides and not body_ambiguous:
                continue
            class_store = ambiguous_classes if body_ambiguous else hidden_classes
            id_store = ambiguous_ids if body_ambiguous else hidden_ids
            tag_store = ambiguous_tags if body_ambiguous else hidden_tags
            attr_store = ambiguous_attrs if body_ambiguous else hidden_attrs
            selectors = _decode_css_escapes(selectors)
            if (
                re.search(r":[\w-]+\s*\(", selectors)
                or re.search(r"[+~]", selectors)
                or re.search(r"\[[^\]]*(?:[~|^$*]=)", selectors)
                or re.search(r"\[[^\]]*,[^\]]*\]", selectors)
            ):
                if fail_closed:
                    ambiguous_tags.add("*")
                    globally_ambiguous = True
                continue
            for selector in selectors.split(","):
                selector = selector.strip()
                if not selector or "::" in selector:
                    continue
                compounds = [
                    part for part in re.split(r"\s+|[>+~]", selector) if part
                ]
                if not compounds:
                    continue
                target = compounds[-1]
                target_classes = set(re.findall(r"\.([\w-]+)", target))
                target_ids = set(re.findall(r"#([\w-]+)", target))
                target_attrs = {
                    (
                        match.group(1).lower(),
                        next(
                            (value for value in match.groups()[1:] if value is not None),
                            None,
                        ),
                    )
                    for match in re.finditer(
                        r"\[\s*([\w-]+)(?:\s*=\s*(?:\"([^\"]*)\"|'([^']*)'|([^\]\s]+)))?\s*\]",
                        target,
                    )
                }
                if ":not(" not in target and (target_classes or target_ids):
                    class_store.update(target_classes)
                    id_store.update(target_ids)
                    continue
                if target_attrs:
                    attr_store.update(target_attrs)
                    continue
                if target.startswith(":root"):
                    tag_store.add("html")
                    continue
                ancestors = " ".join(compounds[:-1])
                ancestor_classes = set(re.findall(r"\.([\w-]+)", ancestors))
                ancestor_ids = set(re.findall(r"#([\w-]+)", ancestors))
                if ancestor_classes or ancestor_ids:
                    class_store.update(ancestor_classes)
                    id_store.update(ancestor_ids)
                    continue
                tag_match = re.match(r"(?:\*|[a-zA-Z][\w-]*)", target)
                if tag_match:
                    tag_store.add(tag_match.group(0).lower())
                else:
                    ambiguous_tags.add("*")
                    globally_ambiguous = True
    return (
        hidden_classes,
        hidden_ids,
        hidden_tags,
        hidden_attrs,
        ambiguous_classes,
        ambiguous_ids,
        ambiguous_tags,
        ambiguous_attrs,
        globally_ambiguous,
    )


def css_hidden_selectors(raw: str) -> tuple[set[str], set[str]]:
    """Return class and id filters hidden by inline stylesheet rules."""
    hidden_classes, hidden_ids, _, _, _, _, _, _, _ = _css_hidden_filters(
        raw,
        fail_closed=False,
    )
    return hidden_classes, hidden_ids


class _HtmlVisibilityParser(HTMLParser):
    """Shared fail-closed visibility state for text and resource parsers."""

    _VOID_TAGS = {
        "area", "base", "br", "col", "embed", "hr", "img", "input",
        "link", "meta", "param", "source", "track", "wbr",
    }
    _P_IMPLICIT_CLOSE_STARTS = {
        "address", "article", "aside", "blockquote", "details", "div",
        "dl", "fieldset", "figcaption", "figure", "footer", "form",
        "h1", "h2", "h3", "h4", "h5", "h6", "header", "hgroup", "hr",
        "main", "menu", "nav", "ol", "p", "pre", "section", "table", "ul",
    }
    _OPTIONAL_REPEAT_TAGS = {
        "dd", "dt", "li", "option", "tbody", "td", "tfoot", "th", "thead", "tr",
    }
    _REPLACED_TAGS = {"audio", "embed", "iframe", "image", "img", "object", "svg", "video"}
    _PRESENTATION_STYLE_ATTRS = {
        "clip", "clip-path", "color", "display", "filter", "font-size", "height",
        "mask", "mask-image", "max-height", "max-width", "opacity", "overflow",
        "transform", "visibility", "width",
    }
    _SVG_POSITIONED_TAGS = {
        "circle", "ellipse", "foreignobject", "image", "rect", "svg", "text", "tspan", "use",
    }

    def __init__(
        self,
        hidden_classes: set[str],
        hidden_ids: set[str],
        hidden_tags: set[str],
        hidden_attrs: set[tuple[str, str | None]],
        ambiguous_classes: set[str],
        ambiguous_ids: set[str],
        ambiguous_tags: set[str],
        ambiguous_attrs: set[tuple[str, str | None]],
        visibility_ambiguous: bool,
        *,
        skip_tags: set[str],
        fail_closed: bool,
        custom_properties: dict[str, str] | None = None,
    ) -> None:
        super().__init__(convert_charrefs=True)
        self._custom_properties = custom_properties
        self._hidden_classes = hidden_classes
        self._hidden_ids = hidden_ids
        self._hidden_tags = hidden_tags
        self._hidden_attrs = hidden_attrs
        self._ambiguous_classes = ambiguous_classes
        self._ambiguous_ids = ambiguous_ids
        self._ambiguous_tags = ambiguous_tags
        self._ambiguous_attrs = ambiguous_attrs
        self._skip_tags = skip_tags
        self._fail_closed = fail_closed
        self._visibility_ambiguous = visibility_ambiguous
        self._skip_depth = 0
        self._ambiguous_depth = 0
        self._skip_stack: list[tuple[str, bool, bool]] = []
        self._svg_viewports: list[tuple[float, float, float, float]] = []
        self._ambiguous_markup = False

    def _mark_ambiguous(self) -> None:
        self._ambiguous_markup = True
        self._skip_stack.clear()
        self._svg_viewports.clear()
        self._skip_depth = 1 if self._fail_closed else 0
        self._ambiguous_depth = 1 if self._fail_closed else 0

    def _pop_top(self) -> None:
        tag, hidden, ambiguous = self._skip_stack.pop()
        if tag == "svg" and self._svg_viewports:
            self._svg_viewports.pop()
        if hidden:
            self._skip_depth = max(0, self._skip_depth - 1)
        if ambiguous:
            self._ambiguous_depth = max(0, self._ambiguous_depth - 1)

    @staticmethod
    def _svg_viewport(attrs_map: dict[str, str]) -> tuple[float, float, float, float] | None:
        raw = attrs_map.get("viewbox", "")
        if raw:
            try:
                values = [float(value) for value in re.split(r"[\s,]+", raw.strip())]
            except ValueError:
                values = []
            if len(values) == 4 and values[2] > 0 and values[3] > 0:
                return values[0], values[1], values[2], values[3]
        width = _css_numeric_value(attrs_map.get("width", ""))
        height = _css_numeric_value(attrs_map.get("height", ""))
        if width and height and width[0] > 0 and height[0] > 0:
            return 0.0, 0.0, width[0], height[0]
        return None

    def _svg_position_state(
        self,
        tag: str,
        attrs_map: dict[str, str],
    ) -> tuple[bool, bool]:
        if tag not in self._SVG_POSITIONED_TAGS:
            return False, False
        viewport = self._svg_viewports[-1] if self._svg_viewports else None
        if viewport is not None and tag in {"foreignobject", "text", "tspan"}:
            # A coordinate point does not prove that the complete glyph or
            # foreign-object box intersects the viewport. Renderer box data is
            # required, so SVG text cannot be deterministic atomic evidence.
            return False, True
        parsed_positions: dict[str, float] = {}
        for name in ("x", "y", "dx", "dy"):
            if name not in attrs_map:
                continue
            parsed = _css_numeric_value(attrs_map[name])
            if parsed is None or parsed[1] not in {"", "px", "pt"}:
                return False, True
            parsed_positions[name] = parsed[0]
        if tag == "svg" and viewport is not None and parsed_positions:
            # Nested SVG establishes another viewport. Proving its transformed
            # overlap requires the renderer, so do not accept facts from it as
            # deterministic static evidence.
            return False, True
        if any(parsed_positions.get(name, 0) != 0 for name in ("dx", "dy")):
            return False, True
        if viewport is None:
            if any(abs(value) >= 10000 for value in parsed_positions.values()):
                return True, False
            return False, False
        min_x, min_y, view_width, view_height = viewport
        x = parsed_positions.get("x", min_x)
        y = parsed_positions.get("y", min_y)
        max_x = min_x + view_width
        max_y = min_y + view_height
        if tag == "image":
            image_width = _css_numeric_value(attrs_map.get("width", ""))
            image_height = _css_numeric_value(attrs_map.get("height", ""))
            if (
                image_width is None
                or image_height is None
                or image_width[1] not in {"", "px", "pt"}
                or image_height[1] not in {"", "px", "pt"}
                or image_width[0] <= 0
                or image_height[0] <= 0
            ):
                return False, True
            right = x + image_width[0]
            bottom = y + image_height[0]
            if right <= min_x or x >= max_x or bottom <= min_y or y >= max_y:
                return True, False
            if x < min_x or right > max_x or y < min_y or bottom > max_y:
                return False, True
        elif x < min_x or x > max_x or y < min_y or y > max_y:
            return False, True
        return False, False

    @staticmethod
    def _implicitly_closed_by_start(open_tag: str, new_tag: str) -> bool:
        if open_tag == "p" and new_tag in _HtmlVisibilityParser._P_IMPLICIT_CLOSE_STARTS:
            return True
        if open_tag == "li" and new_tag == "li":
            return True
        if open_tag in {"dd", "dt"} and new_tag in {"dd", "dt"}:
            return True
        if open_tag in {"rp", "rt"} and new_tag in {"rp", "rt"}:
            return True
        if open_tag == "option" and new_tag in {"option", "optgroup"}:
            return True
        if open_tag == "optgroup" and new_tag == "optgroup":
            return True
        if open_tag in {"td", "th"} and new_tag in {
            "td", "th", "tr", "tbody", "thead", "tfoot",
        }:
            return True
        if open_tag == "tr" and new_tag in {"tr", "tbody", "thead", "tfoot"}:
            return True
        if open_tag in {"tbody", "thead", "tfoot"} and new_tag in {
            "tbody", "thead", "tfoot",
        }:
            return True
        return False

    @staticmethod
    def _implicitly_closed_by_end(open_tag: str, end_tag: str) -> bool:
        return (
            (open_tag == "p" and end_tag in {"address", "article", "aside", "blockquote", "body", "div", "footer", "form", "header", "main", "nav", "section"})
            or (open_tag == "li" and end_tag in {"menu", "ol", "ul"})
            or (open_tag in {"dd", "dt"} and end_tag == "dl")
            or (open_tag in {"rp", "rt"} and end_tag == "ruby")
            or (open_tag == "option" and end_tag in {"optgroup", "select"})
            or (open_tag == "optgroup" and end_tag == "select")
            or (open_tag in {"td", "th"} and end_tag in {"tr", "tbody", "thead", "tfoot", "table"})
            or (open_tag == "tr" and end_tag in {"tbody", "thead", "tfoot", "table"})
            or (open_tag in {"tbody", "thead", "tfoot"} and end_tag == "table")
        )

    @staticmethod
    def _implicit_start_boundaries(new_tag: str) -> set[str]:
        if new_tag == "li":
            return {"menu", "ol", "ul"}
        if new_tag in {"dd", "dt"}:
            return {"dl"}
        if new_tag in {"option", "optgroup"}:
            return {"datalist", "select"}
        if new_tag in {"rp", "rt"}:
            return {"ruby"}
        if new_tag in {"td", "th"}:
            return {"table", "tr"}
        if new_tag in {"tr", "tbody", "thead", "tfoot"}:
            return {"table"}
        return set()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if self._ambiguous_markup:
            return
        boundaries = self._implicit_start_boundaries(tag)
        boundary = max(
            (
                index
                for index, (open_tag, _, _) in enumerate(self._skip_stack)
                if open_tag in boundaries
            ),
            default=-1,
        )
        implicit_match = next(
            (
                index
                for index in range(len(self._skip_stack) - 1, boundary, -1)
                if self._implicitly_closed_by_start(self._skip_stack[index][0], tag)
            ),
            None,
        )
        if implicit_match is not None:
            while len(self._skip_stack) > implicit_match:
                self._pop_top()
        attrs_map = {name.lower(): (value or "") for name, value in attrs}
        classes = set(attrs_map.get("class", "").split())
        presentation_style = ";".join(
            f"{name}:{value}"
            for name, value in attrs_map.items()
            if name in self._PRESENTATION_STYLE_ATTRS
        )
        inline_hidden, inline_ambiguous = _style_state(
            attrs_map.get("style", ""),
            fail_closed=self._fail_closed,
            replaced_element=tag in self._REPLACED_TAGS,
            custom_properties=self._custom_properties,
        )
        presentation_hidden, presentation_ambiguous = _style_state(
            presentation_style,
            fail_closed=self._fail_closed,
            replaced_element=tag in self._REPLACED_TAGS,
        )
        svg_position_hidden, svg_position_ambiguous = self._svg_position_state(
            tag,
            attrs_map,
        )
        known_hidden = (
            tag in self._skip_tags
            or tag in self._hidden_tags
            or "*" in self._hidden_tags
            or any(
                name in attrs_map
                and (expected is None or attrs_map[name] == expected)
                for name, expected in self._hidden_attrs
            )
            or "hidden" in attrs_map
            or attrs_map.get("aria-hidden", "").lower() == "true"
            or bool(classes & self._hidden_classes)
            or attrs_map.get("id", "") in self._hidden_ids
            or inline_hidden
            or (self._fail_closed and presentation_hidden)
            or (self._fail_closed and svg_position_hidden)
            or (
                self._fail_closed
                and attrs_map.get("fill", "").strip().lower() == "none"
            )
            or (
                self._fail_closed
                and _is_zero_css_value(attrs_map.get("fill-opacity", ""))
            )
        )
        css_ambiguous = (
            tag in self._ambiguous_tags
            or "*" in self._ambiguous_tags
            or any(
                name in attrs_map
                and (expected is None or attrs_map[name] == expected)
                for name, expected in self._ambiguous_attrs
            )
            or bool(classes & self._ambiguous_classes)
            or attrs_map.get("id", "") in self._ambiguous_ids
        )
        if known_hidden or (self._skip_depth and not self._ambiguous_depth):
            inline_ambiguous = False
            presentation_ambiguous = False
            svg_position_ambiguous = False
            css_ambiguous = False
        current_ambiguous = self._fail_closed and (
            css_ambiguous
            or inline_ambiguous
            or presentation_ambiguous
            or svg_position_ambiguous
        )
        ambiguous_hidden = (
            current_ambiguous and not known_hidden and self._skip_depth == 0
        )
        if not known_hidden and (self._ambiguous_depth or ambiguous_hidden):
            self._handle_ambiguous_starttag(tag, attrs)
        hidden = known_hidden or current_ambiguous
        is_void = tag in self._VOID_TAGS
        if not is_void:
            self._skip_stack.append((tag, hidden, ambiguous_hidden))
            if tag == "svg":
                self._svg_viewports.append(
                    self._svg_viewport(attrs_map) or (0.0, 0.0, 4096.0, 4096.0)
                )
            if hidden:
                self._skip_depth += 1
            if ambiguous_hidden:
                self._ambiguous_depth += 1
        if hidden or self._skip_depth:
            return
        self._handle_visible_starttag(tag, attrs)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if self._ambiguous_markup:
            return
        if tag in self._VOID_TAGS:
            return
        match = next(
            (index for index in range(len(self._skip_stack) - 1, -1, -1)
             if self._skip_stack[index][0] == tag),
            None,
        )
        if match is None:
            return
        if match != len(self._skip_stack) - 1:
            intervening = self._skip_stack[match + 1:]
            if not intervening or not self._implicitly_closed_by_end(
                intervening[0][0],
                tag,
            ):
                self._mark_ambiguous()
                return
        closing = self._skip_stack[match:]
        del self._skip_stack[match:]
        for open_tag, _, _ in reversed(closing):
            if open_tag == "svg" and self._svg_viewports:
                self._svg_viewports.pop()
        self._skip_depth = max(
            0,
            self._skip_depth - sum(1 for _, hidden, _ in closing if hidden),
        )
        self._ambiguous_depth = max(
            0,
            self._ambiguous_depth
            - sum(1 for _, _, ambiguous in closing if ambiguous),
        )

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        # In HTML, a trailing slash is ignored on non-void elements. Treating
        # <div hidden/> as closed would expose everything that follows even
        # though browsers and WeasyPrint keep it inside the hidden div.
        foreign_svg = tag.lower() == "svg" or bool(self._svg_viewports)
        self.handle_starttag(tag, attrs)
        if foreign_svg and tag.lower() not in self._VOID_TAGS:
            self.handle_endtag(tag)

    def handle_data(self, data: str) -> None:
        if self._ambiguous_markup:
            if not self._fail_closed:
                self._handle_visible_data(data)
        elif self._ambiguous_depth:
            self._handle_ambiguous_data(data)
        elif self._skip_depth == 0:
            self._handle_visible_data(data)

    def _handle_visible_starttag(
        self, _tag: str, _attrs: list[tuple[str, str | None]],
    ) -> None:
        return

    def _handle_ambiguous_starttag(
        self,
        _tag: str,
        _attrs: list[tuple[str, str | None]],
    ) -> None:
        return

    def _handle_ambiguous_data(self, _data: str) -> None:
        return

    def _handle_visible_data(self, _data: str) -> None:
        return


class _VisibleTextParser(_HtmlVisibilityParser):
    """Extract visible text from filled HTML while skipping code-like blocks."""

    _SKIP_TAGS = {
        "clippath", "code", "datalist", "defs", "desc", "head", "mask",
        "metadata", "noembed", "noframes", "noscript", "pattern", "pre", "rp",
        "script", "style", "symbol", "template", "title",
    }
    def __init__(
        self,
        hidden_classes: set[str],
        hidden_ids: set[str],
        hidden_tags: set[str],
        hidden_attrs: set[tuple[str, str | None]],
        ambiguous_classes: set[str],
        ambiguous_ids: set[str],
        ambiguous_tags: set[str],
        ambiguous_attrs: set[tuple[str, str | None]],
        visibility_ambiguous: bool,
        *,
        fail_closed: bool,
        custom_properties: dict[str, str] | None = None,
    ) -> None:
        super().__init__(
            hidden_classes,
            hidden_ids,
            hidden_tags,
            hidden_attrs,
            ambiguous_classes,
            ambiguous_ids,
            ambiguous_tags,
            ambiguous_attrs,
            visibility_ambiguous,
            skip_tags=self._SKIP_TAGS,
            fail_closed=fail_closed,
            custom_properties=custom_properties,
        )
        self.parts: list[str] = []

    def _handle_visible_data(self, data: str) -> None:
        self.parts.append(data)

    def _handle_ambiguous_data(self, data: str) -> None:
        if data.strip():
            self._visibility_ambiguous = True


def visible_html_evidence(
    raw: str,
    *,
    fail_closed: bool = False,
) -> tuple[str, bool]:
    custom_properties = _document_custom_properties(raw)
    parser = _VisibleTextParser(
        *_css_hidden_filters(
            raw,
            fail_closed=fail_closed,
            custom_properties=custom_properties,
        ),
        fail_closed=fail_closed,
        custom_properties=custom_properties,
    )
    parser.feed(raw)
    if fail_closed and parser._ambiguous_markup:
        return "", True
    return "\n".join(parser.parts), parser._visibility_ambiguous


def visible_html_text(raw: str, *, fail_closed: bool = False) -> str:
    return visible_html_evidence(raw, fail_closed=fail_closed)[0]


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
        return [
            (index, page.extract_text() or "")
            for index, page in enumerate(reader.pages, start=1)
        ], None

    raw = path.read_text(encoding="utf-8", errors="replace")
    if suffix in {".html", ".htm"}:
        return [(None, visible_html_text(raw))], None
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
        path = Path(raw)
        if not path.is_absolute():
            path = ROOT / path
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
        path = Path(raw)
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
        try:
            doc = fitz.open(str(path))
        except Exception as exc:
            print(f"ERROR: {raw}: could not read PDF: {exc}")
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
        path = Path(raw)
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
