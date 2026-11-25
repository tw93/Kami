"""Set Simplified Chinese documents in Source Han Serif SC instead of TsangerJinKai02.

Simplified Chinese defaults to TsangerJinKai02 (a Kai face). For a company,
commercial or public-facing document, SKILL.md has the agent mark the root
element: `<html lang="zh-CN" data-serif="source-han">`. This is the one switch.
The marker is explicit because only the agent sees the request and the brand
profile; the render cannot guess "commercial" from the text.

Like `hant.py`, it runs once inside `render.render_pdf` and rewrites every font
stack that names TsangerJinKai02 so Source Han Serif SC leads it, TsangerJinKai02
stays behind it as a fallback, and inline SVG (which never sees the document
stylesheet) follows. The inserted names are unquoted for the same WeasyPrint
reason documented in `hant.py`.

`_tune` rewrites the tracking inside every `<style>` block. TsangerJinKai02 is a
narrow Kai face whose 0.3pt body tracking was tuned for it; Source Han Serif SC
fills the em box and sets full-width punctuation, so the same tracking pushes
the resume contact row and summary onto an extra line. Body tracking drops to
0.1pt (the dense-layout value in CHEATSHEET.md), and so does every other 0.3pt
in the same stylesheet (a few headings and tags share that value); Chinese lede
tracking in em units goes to 0; other label, overline and Latin tracking stays. Leading
is untouched: the resume's page 2 measured identical in both faces at 1.40-1.42.
Only a Simplified Chinese root honours the marker (`lang` zh, zh-CN, zh-Hans,
zh-SG, or no `lang`): a Traditional Chinese document belongs to `hant.py`, and
a Japanese or Korean one would otherwise get SC glyphs.
"""
from __future__ import annotations

import re

from hant import _ATTR_PART, _TOKEN, is_traditional, lead_stacks, root_attrs, root_lang

HANS_FAMILIES = (
    "Source Han Serif SC",
    "Noto Serif CJK SC",
    "Noto Serif SC",
    "Songti SC",
    "STSong",
    "SimSun",
)

HANS_STACK = ", ".join((*HANS_FAMILIES, "TsangerJinKai02"))
_MARK = re.compile(r"^source-?han(?:-serif)?(?:-sc)?$", re.I)

_BODY_TRACKING = re.compile(r"letter-spacing\s*:\s*0?\.3pt")
_LEDE_TRACKING = re.compile(r"letter-spacing\s*:\s*0?\.0[3-6]em")


def _tune(style: str) -> str:
    style = _BODY_TRACKING.sub("letter-spacing: 0.1pt", style)
    return _LEDE_TRACKING.sub("letter-spacing: 0", style)


def is_source_han(html_text: str) -> bool:
    attrs = root_attrs(html_text)
    value = attrs.get("data-serif")
    if not (value and _MARK.match(value.strip())) or is_traditional(html_text):
        return False
    lang = (root_lang(html_text) or "").strip().lower().replace("_", "-")
    return lang == "" or lang == "zh" or lang.startswith(("zh-cn", "zh-hans", "zh-sg"))


def use_source_han_fonts(html_text: str) -> str:
    """Lead TsangerJinKai02 stacks with Source Han Serif SC when the root asks for it."""
    if not is_source_han(html_text):
        return html_text
    return lead_stacks(html_text, HANS_STACK, _tune)
