"""Simplified Chinese serif switch: data-serif="source-han" leads stacks with Source Han Serif SC."""
from __future__ import annotations

from support import check

from hans import HANS_STACK, is_source_han, use_source_han_fonts

FACE = '@font-face { font-family: "TsangerJinKai02"; src: url("x.ttf"); }'
STACK = '--serif: "TsangerJinKai02", "Source Han Serif SC", Georgia, serif;'
BODY = "body { letter-spacing: 0.3pt; } .lede { letter-spacing: 0.04em; } .tag { letter-spacing: 1pt; }"


def _doc(root: str, css: str) -> str:
    return f"<!doctype html><html {root}><head><style>{css}</style></head><body></body></html>"


def test_source_han_marker() -> None:
    check("marker on zh-CN enables", is_source_han(_doc('lang="zh-CN" data-serif="source-han"', "")))
    check("no marker keeps Kai", not is_source_han(_doc('lang="zh-CN"', "")))
    check("zh-Hant ignores the marker", not is_source_han(_doc('lang="zh-TW" data-serif="source-han"', "")))
    check("marker outside the root is ignored",
          not is_source_han('<html lang="zh-CN"><body data-serif="source-han"></body></html>'))
    check("ja ignores the marker", not is_source_han(_doc('lang="ja" data-serif="source-han"', "")))
    check("ko ignores the marker", not is_source_han(_doc('lang="ko" data-serif="source-han"', "")))
    check("zh-Hans honours it", is_source_han(_doc('lang="zh-Hans" data-serif="source-han"', "")))
    check("no lang honours it", is_source_han(_doc('data-serif="source-han"', "")))


def test_verify_reads_the_marker() -> None:
    from verify import _classify_cjk_font
    check("marked: Source Han is primary", _classify_cjk_font("ABCDEF+SourceHanSerifSC-Regular", False, True) == "primary")
    check("marked: Noto Serif CJK SC is primary", _classify_cjk_font("ABCDEF+NotoSerifCJKsc-Regular", False, True) == "primary")
    check("marked: falling back to Kai is not primary", _classify_cjk_font("TsangerJinKai02-W04", False, True) != "primary")
    check("unmarked: Source Han is not primary", _classify_cjk_font("SourceHanSerifSC-Regular", False, False) != "primary")
    check("unmarked: Kai is primary", _classify_cjk_font("TsangerJinKai02-W04", False, False) == "primary")
    check("no source: either is primary", _classify_cjk_font("SourceHanSerifSC-Regular") == "primary")


def test_source_han_rewrites_and_tunes() -> None:
    plain = _doc('lang="zh-CN"', FACE + STACK + BODY)
    check("unmarked document is byte-identical", use_source_han_fonts(plain) == plain)
    out = use_source_han_fonts(_doc('lang="zh-CN" data-serif="source-han"', FACE + STACK + BODY))
    check("stack led by Source Han Serif SC", f"--serif: {HANS_STACK}," in out)
    check("@font-face untouched", FACE in out)
    check("body tracking 0.3pt -> 0.1pt", "letter-spacing: 0.1pt" in out and "0.3pt" not in out)
    check("lede tracking removed, label tracking kept", "0.04em" not in out and "letter-spacing: 1pt" in out)
    check("idempotent", use_source_han_fonts(out) == out)
