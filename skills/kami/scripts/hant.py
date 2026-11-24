"""Set Traditional Chinese documents in a Ming face instead of TsangerJinKai02.

TsangerJinKai02 draws mainland punctuation: the comma and full stop sit in the
lower-left corner of a cell about 0.68em wide, and the font has no `locl`
forms for Taiwan or Hong Kong, where those marks are centered in a full-width
cell. For a document whose root `lang` is zh-Hant, zh-TW, zh-HK or zh-MO (the
same set `landing-page.html` matches with `:lang()`), this rewrites every font
stack that names TsangerJinKai02 so Traditional Chinese Ming faces lead it, and
keeps TsangerJinKai02 behind them as the last CJK serif before the stack's own
fallbacks.

It runs once inside `render.render_pdf` instead of as template CSS because
WeasyPrint draws inline SVG (diagrams, generated charts, normalized Mermaid)
without the document stylesheet, so a `:lang()` rule never reaches their
labels. Only font declarations are touched: `<style>` blocks and the `style`
and `font-family` attributes of real tags. Text, comments and `<script>` are
skipped, so a code sample that shows a stack keeps it. A
stack entry is rewritten only when a comma follows it, which leaves the
`@font-face` declarations (`font-family: "TsangerJinKai02";`) intact.

The inserted names are unquoted on purpose. WeasyPrint's SVG renderer tries
only the first family of a quoted list (verified on 68.1 and 70.0), so
`"Source Han Serif TC", "Songti TC"` on a machine without Source Han Serif TC
skips Songti TC and lets fontconfig pick per glyph. An unquoted list is walked
in order; HTML text accepts either form.
"""
from __future__ import annotations

import re

HANT_FAMILIES = (
    "Source Han Serif TC",
    "Noto Serif CJK TC",
    "Noto Serif TC",
    "Songti TC",
    "PMingLiU",
)

_HANT_STACK = ", ".join((*HANT_FAMILIES, "TsangerJinKai02"))
_HANT_TAG = re.compile(r"zh-(?:hant|tw|hk|mo)(?:-|$)", re.I)
# Plain quotes in CSS, entity quotes in attributes written through html.escape
# (chart.py serializes its stacks that way), or no quotes at all.
_QUOTE = r"""(?:"|'|&quot;|&#0*39;|&#x0*27;)"""
_STACK_ENTRY = re.compile(
    rf"""(?P<q>{_QUOTE})TsangerJinKai02(?P=q)(?=\s*,)"""
    r"""|(?<![\w"'&;-])TsangerJinKai02(?![\w"'&-])(?=\s*,)""",
    re.I,
)
_ATTR = r"""[^\s"'<>/=]+(?:\s*=\s*(?:"[^"]*"|'[^']*'|[^\s"'<>`=]+))?"""
# One pass over the document. Unclosed comments and raw-text blocks run to the
# end in a single match instead of rescanning from every opener.
_TOKEN = re.compile(
    r"<!--.*?(?:-->|\Z)"
    r"|<(?P<raw>script|style)\b(?P<open>(?:\s+" + _ATTR + r")*)\s*>(?P<body>.*?)(?P<close></(?P=raw)\s*>|\Z)"
    r"|<(?P<name>[A-Za-z][\w:-]*)(?P<attrs>(?:\s+" + _ATTR + r")*)\s*/?>",
    re.I | re.S,
)
_ATTR_PART = re.compile(
    r"""(?P<key>[^\s"'<>/=]+)(?:(?P<eq>\s*=\s*)(?:(?P<q>["'])(?P<qv>.*?)(?P=q)|(?P<bare>[^\s"'<>`=]+)))?""",
    re.S,
)


def is_traditional_tag(tag: str | None) -> bool:
    return bool(tag and _HANT_TAG.match(tag.strip()))


def root_lang(html_text: str) -> str | None:
    for token in _TOKEN.finditer(html_text):
        if (token.group("name") or "").lower() != "html":
            continue
        for attr in _ATTR_PART.finditer(token.group("attrs")):
            if attr.group("key").lower() == "lang":
                return attr.group("qv") if attr.group("q") else attr.group("bare")
        return None
    return None


def root_attrs(html_text: str) -> dict[str, str]:
    """Lowercased attribute names of the root `<html>` tag mapped to their values."""
    for token in _TOKEN.finditer(html_text):
        if (token.group("name") or "").lower() != "html":
            continue
        found: dict[str, str] = {}
        for attr in _ATTR_PART.finditer(token.group("attrs")):
            value = attr.group("qv") if attr.group("q") else attr.group("bare")
            found[attr.group("key").lower()] = value or ""
        return found
    return {}


def is_traditional(html_text: str) -> bool:
    return is_traditional_tag(root_lang(html_text))


def _lead(text: str, stack: str = _HANT_STACK) -> str:
    # Keep the pass idempotent: a stack that already leads with the replacement
    # faces (its trailing TsangerJinKai02 is unquoted) is protected from a second swap.
    marker = "\0hant\0"
    text = text.replace(stack, marker)
    return _STACK_ENTRY.sub(stack, text).replace(marker, stack)


def _lead_attrs(attrs: str, stack: str = _HANT_STACK) -> str:
    def one(attr: re.Match[str]) -> str:
        if attr.group("key").lower() not in ("style", "font-family") or not attr.group("eq"):
            return attr.group(0)
        if attr.group("q"):
            q = attr.group("q")
            return f"{attr.group('key')}{attr.group('eq')}{q}{_lead(attr.group('qv'), stack)}{q}"
        return attr.group(0)
    return _ATTR_PART.sub(one, attrs)


def use_traditional_fonts(html_text: str) -> str:
    """Lead TsangerJinKai02 stacks with Traditional Chinese Ming faces."""
    if not is_traditional(html_text):
        return html_text
    return lead_stacks(html_text, _HANT_STACK)


def lead_stacks(html_text: str, stack: str, style_tune=None) -> str:
    """Put `stack` in front of every TsangerJinKai02 entry in font declarations.

    `style_tune`, when given, maps each `<style>` body (after the swap) to a
    retuned body, for the few non-font values a replacement face needs.
    """
    def token(match: re.Match[str]) -> str:
        if match.group("raw"):
            if match.group("raw").lower() != "style":
                return match.group(0)
            whole = match.group(0)
            start, end = match.start("body") - match.start(), match.end("body") - match.start()
            return whole[:start] + (style_tune or str)(_lead(match.group("body"), stack)) + whole[end:]
        if match.group("name"):
            whole = match.group(0)
            attrs = match.group("attrs")
            start = match.start("attrs") - match.start()
            return whole[:start] + _lead_attrs(attrs, stack) + whole[start + len(attrs):]
        return match.group(0)

    return _TOKEN.sub(token, html_text)
