"""Traditional Chinese rendering: zh-Hant documents lead with a Ming face, not TsangerJinKai02."""
from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

from support import check, skip

from hant import HANT_FAMILIES, is_traditional, use_traditional_fonts
from verify import _classify_cjk_font

FACE = '@font-face { font-family: "TsangerJinKai02"; src: url("x.ttf"); }'
STACK = '--serif: "TsangerJinKai02", "Source Han Serif SC", Georgia, serif;'
LEAD = ", ".join((*HANT_FAMILIES, "TsangerJinKai02"))


def _doc(lang: str, body: str) -> str:
    return f'<!doctype html><html lang="{lang}"><head><style>{body}</style></head><body></body></html>'


def test_traditional_lang_detection() -> None:
    for lang in ("zh-TW", "zh-Hant", "zh-Hant-TW", "zh-HK", "zh-MO", "ZH-tw"):
        check(f"{lang} is Traditional", is_traditional(_doc(lang, "")))
    for lang in ("zh-CN", "zh", "zh-Hans", "ja", "en"):
        check(f"{lang} is not Traditional", not is_traditional(_doc(lang, "")))
    check("no lang is not Traditional", not is_traditional("<html><body></body></html>"))
    for root in ('<html data-lang="zh-TW" lang="zh-CN">', '<html xml:lang="zh-TW" lang="zh-CN">',
                 '<!-- <html lang="zh-TW"> --><html lang="zh-CN">'):
        check(f"only the root lang attribute counts: {root}", not is_traditional(root))
    check("lang= inside another attribute value is ignored",
          not is_traditional('<html data-x="lang=zh-TW" lang="zh-CN">'))
    check("a > inside an attribute value does not end the tag",
          is_traditional('<html title="a>b" lang="zh-TW">'))


def test_traditional_rewrites_stacks_only() -> None:
    out = use_traditional_fonts(_doc("zh-TW", FACE + STACK))
    check("@font-face family is kept", FACE in out, out)
    check("stack leads with unquoted Ming faces",
          f'--serif: {LEAD}, "Source Han Serif SC", Georgia, serif;' in out, out)

    attr = "font-family=\"&#x27;TsangerJinKai02&#x27;, &#x27;Source Han Serif SC&#x27;, serif\""
    out = use_traditional_fonts(_doc("zh-Hant", "") + f"<svg><text {attr}>標籤</text></svg>")
    check("entity-quoted SVG attribute is rewritten",
          f"font-family=\"{LEAD}, &#x27;Source Han Serif SC&#x27;, serif\"" in out, out)

    unquoted = '<svg><text font-family="TsangerJinKai02, Songti SC, serif">標籤</text></svg>'
    out = use_traditional_fonts(_doc("zh-TW", "") + unquoted)
    check("unquoted SVG stack is rewritten", f'font-family="{LEAD}, Songti SC, serif"' in out, out)

    samples = (
        '<pre><code>font-family: "TsangerJinKai02", serif;</code></pre>',
        '<code>&lt;text font-family="TsangerJinKai02, serif"&gt;</code>',
        '<p>style="font-family: TsangerJinKai02, serif"</p>',
        "<p title='style=\"font-family: TsangerJinKai02, serif\"'>x</p>",
        "<script>var a = '<p style=\"font-family: TsangerJinKai02, serif\">';</script>",
        '<!-- <p style="font-family: TsangerJinKai02, serif"> -->',
    )
    for sample in samples:
        out = use_traditional_fonts(_doc("zh-TW", "") + sample)
        check(f"left alone outside font declarations: {sample[:40]}", sample in out, out)

    real = '<p style="font-family: \'TsangerJinKai02\', serif">x</p>'
    once = use_traditional_fonts(_doc("zh-TW", FACE + STACK) + real)
    check("a real style attribute is rewritten", f'style="font-family: {LEAD}, serif"' in once, once)
    check("a second pass changes nothing", use_traditional_fonts(once) == once)

    simplified = _doc("zh-CN", FACE + STACK)
    check("zh-CN document is untouched", use_traditional_fonts(simplified) == simplified)


def test_font_gate_reads_traditional_from_lang() -> None:
    cases = [
        ("ABCDEF+TsangerJinKai02-W04", False, "primary"),
        ("ABCDEF+TsangerJinKai02-W04", True, "mainland"),
        ("SourceHanSerifTC-Regular", True, "primary"),
        ("SourceHanSerifTC-Regular", False, "serif"),
        ("Songti-TC", True, "serif"),
        ("PingFang-TC", True, "other"),
    ]
    for name, traditional, want in cases:
        got = _classify_cjk_font(name, traditional)
        check(f"{name} in a {'Traditional' if traditional else 'Simplified'} document is {want}",
              got == want, got)


def test_font_gate_reads_pdf_lang() -> None:
    try:
        import fitz
        from verify import _pdf_lang
    except Exception as exc:
        skip(f"pymupdf unavailable: {exc}")
        return
    with tempfile.TemporaryDirectory() as tmp:
        for lang in ("zh-TW", "zh-CN"):
            pdf = Path(tmp) / f"{lang}.pdf"
            with fitz.open() as doc:
                doc.new_page()
                doc.xref_set_key(doc.pdf_catalog(), "Lang", f"({lang})")
                doc.save(str(pdf))
            check(f"_pdf_lang reads /Lang {lang}", _pdf_lang(pdf) == lang, str(_pdf_lang(pdf)))
        bare = Path(tmp) / "bare.pdf"
        with fitz.open() as doc:
            doc.new_page()
            doc.save(str(bare))
        check("_pdf_lang is None without /Lang", _pdf_lang(bare) is None, str(_pdf_lang(bare)))


def _tc_family_installed() -> bool:
    if not shutil.which("fc-list"):
        return False
    listed = subprocess.run(["fc-list", ":", "family"], capture_output=True, text=True).stdout
    return any(name in listed for name in HANT_FAMILIES)


def test_traditional_render_draws_body_and_svg_in_ming() -> None:
    if not _tc_family_installed():
        skip("no Traditional Chinese Ming face installed")
        return
    try:
        import fitz
        from render import render_pdf
    except Exception as exc:  # weasyprint / pymupdf missing
        skip(f"render deps unavailable: {exc}")
        return

    html = _doc("zh-TW", 'p, text { font-family: "TsangerJinKai02", "Source Han Serif SC", Georgia, serif; }')
    html = html.replace(
        "<body></body>",
        "<body><p>繁體中文內文，標點符號應在字身正中。</p>"
        '<svg width="300" height="40"><text x="4" y="24" font-size="12" '
        "font-family=\"&#x27;TsangerJinKai02&#x27;, &#x27;Source Han Serif SC&#x27;, serif\">"
        "圖表標籤，營收成長。</text></svg></body>",
    )
    markers = ("sourcehanseriftc", "notoserifcjktc", "notoseriftc", "songtitc", "pmingliu")
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / "hant.html"
        src.write_text(html, encoding="utf-8")
        pdf = Path(tmp) / "hant.pdf"
        render_pdf(src, pdf)
        fonts: dict[str, str] = {}
        with fitz.open(str(pdf)) as doc:
            for block in doc[0].get_text("dict")["blocks"]:
                for line in block.get("lines", []):
                    for span in line["spans"]:
                        if span["text"].strip():
                            fonts[span["text"]] = span["font"]
    for text, font in fonts.items():
        key = "".join(ch for ch in font.lower() if ch.isalnum())
        check(f"'{text}' drawn by a Traditional Ming face", any(m in key for m in markers), font)
