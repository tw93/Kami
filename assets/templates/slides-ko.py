#!/usr/bin/env python3
"""slides-ko.py - Korean parchment slide deck generator.

Usage:
  pip install python-pptx --break-system-packages
  python3 slides-ko.py

Output:
  output.pptx
"""

from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR

PARCHMENT = RGBColor(0xF5, 0xF4, 0xED)
IVORY = RGBColor(0xFA, 0xF9, 0xF5)
BRAND = RGBColor(0x1B, 0x36, 0x5D)
NEAR_BLACK = RGBColor(0x14, 0x14, 0x13)
DARK_WARM = RGBColor(0x3D, 0x3D, 0x3A)
OLIVE = RGBColor(0x50, 0x4E, 0x49)
STONE = RGBColor(0x6B, 0x6A, 0x64)
BORDER = RGBColor(0xE8, 0xE6, 0xDC)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)

DISPLAY = "BM DoHyeon"
SANS = "Pretendard"
SERIF = "Noto Serif KR"

SLIDE_W = Inches(13.33)
SLIDE_H = Inches(7.5)


def blank_slide(prs, bg_color=PARCHMENT):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    bg = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, prs.slide_height)
    bg.fill.solid()
    bg.fill.fore_color.rgb = bg_color
    bg.line.fill.background()
    bg.shadow.inherit = False
    return slide


def add_text(slide, text, left, top, width, height, font=SANS, size=18,
             bold=False, color=NEAR_BLACK, align=PP_ALIGN.LEFT,
             vanchor=MSO_ANCHOR.TOP):
    tb = slide.shapes.add_textbox(left, top, width, height)
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = 0
    tf.margin_top = tf.margin_bottom = 0
    tf.vertical_anchor = vanchor
    p = tf.paragraphs[0]
    p.alignment = align
    run = p.add_run()
    run.text = text
    run.font.name = font
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.italic = False
    run.font.color.rgb = color
    return tb


def add_line(slide, left, top, width, color=BRAND, weight_pt=1):
    line = slide.shapes.add_connector(1, left, top, left + width, top)
    line.line.color.rgb = color
    line.line.width = Pt(weight_pt)
    return line


def add_card(slide, left, top, width, height, fill=IVORY, border=BORDER):
    card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
    card.fill.solid()
    card.fill.fore_color.rgb = fill
    card.line.color.rgb = border
    card.line.width = Pt(0.5)
    card.shadow.inherit = False
    return card


def cover_slide(prs, title, subtitle, author, date):
    s = blank_slide(prs)
    add_text(s, title, Inches(0.9), Inches(2.35), Inches(11.6), Inches(1.3),
             font=DISPLAY, size=46, color=NEAR_BLACK, align=PP_ALIGN.CENTER)
    add_line(s, Inches(6.17), Inches(4.15), Inches(1), weight_pt=1.5)
    add_text(s, subtitle, Inches(1.4), Inches(4.45), Inches(10.5), Inches(0.7),
             font=SANS, size=19, color=OLIVE, align=PP_ALIGN.CENTER)
    add_text(s, f"{author} · {date}", Inches(1), Inches(6.45), Inches(11.33), Inches(0.4),
             font=SANS, size=13, color=STONE, align=PP_ALIGN.CENTER)


def toc_slide(prs, items):
    s = blank_slide(prs)
    add_text(s, "목차", Inches(1.2), Inches(0.8), Inches(10), Inches(0.8),
             font=DISPLAY, size=34, color=NEAR_BLACK)
    add_line(s, Inches(1.2), Inches(1.75), Inches(11), weight_pt=1)
    for i, item in enumerate(items):
        y = Inches(2.35 + i * 0.88)
        add_text(s, f"0{i + 1}", Inches(1.2), y, Inches(1), Inches(0.6),
                 font=DISPLAY, size=26, color=BRAND)
        add_text(s, item, Inches(2.35), y, Inches(9.5), Inches(0.6),
                 font=SANS, size=22, color=NEAR_BLACK, bold=True,
                 vanchor=MSO_ANCHOR.MIDDLE)


def chapter_slide(prs, number, title):
    s = blank_slide(prs, bg_color=BRAND)
    add_text(s, f"0{number}", Inches(0.8), Inches(0.5), Inches(2), Inches(0.8),
             font=DISPLAY, size=28, color=WHITE)
    add_text(s, title, Inches(1), Inches(2.9), Inches(11.33), Inches(1.5),
             font=DISPLAY, size=54, color=WHITE, align=PP_ALIGN.CENTER)


def content_slide(prs, eyebrow, title, body, page_num=None):
    s = blank_slide(prs)
    add_text(s, eyebrow, Inches(1.2), Inches(0.6), Inches(10), Inches(0.4),
             font=SANS, size=11, color=STONE, bold=True)
    add_text(s, title, Inches(1.2), Inches(1.25), Inches(11), Inches(1.15),
             font=SANS, size=32, color=NEAR_BLACK, bold=True)
    add_line(s, Inches(1.2), Inches(2.65), Inches(1.1), weight_pt=1.5)
    add_text(s, body, Inches(1.2), Inches(3.05), Inches(10.8), Inches(3.2),
             font=SANS, size=20, color=DARK_WARM)
    if page_num is not None:
        add_text(s, f"{page_num:02d}", Inches(11.7), Inches(6.88), Inches(1), Inches(0.3),
                 font=SANS, size=11, color=STONE, align=PP_ALIGN.RIGHT)


def metrics_slide(prs, title, metrics):
    s = blank_slide(prs)
    add_text(s, title, Inches(1.2), Inches(0.85), Inches(11), Inches(1),
             font=SANS, size=30, color=NEAR_BLACK, bold=True, align=PP_ALIGN.CENTER)
    add_line(s, Inches(6.17), Inches(2.0), Inches(1), weight_pt=1.4)
    n = len(metrics)
    card_w = Inches(2.75)
    gap = Inches(0.32)
    start = (SLIDE_W - (card_w * n + gap * (n - 1))) / 2
    for i, (value, label) in enumerate(metrics):
        x = start + (card_w + gap) * i
        add_card(s, x, Inches(3.0), card_w, Inches(1.9))
        add_text(s, value, x, Inches(3.25), card_w, Inches(0.8),
                 font=DISPLAY, size=42, color=BRAND, align=PP_ALIGN.CENTER)
        add_text(s, label, x + Inches(0.16), Inches(4.15), card_w - Inches(0.32), Inches(0.55),
                 font=SANS, size=13, color=OLIVE, align=PP_ALIGN.CENTER)


def ending_slide(prs, message, contact):
    s = blank_slide(prs)
    add_text(s, message, Inches(1), Inches(3.0), Inches(11.33), Inches(1.1),
             font=DISPLAY, size=42, color=NEAR_BLACK, align=PP_ALIGN.CENTER)
    add_line(s, Inches(6.17), Inches(4.45), Inches(1), weight_pt=1.5)
    add_text(s, contact, Inches(1), Inches(4.75), Inches(11.33), Inches(0.55),
             font=SANS, size=15, color=OLIVE, align=PP_ALIGN.CENTER)


def main():
    prs = Presentation()
    prs.slide_width = SLIDE_W
    prs.slide_height = SLIDE_H

    cover_slide(prs, "{{문서 제목}}", "{{핵심 주장을 한 문장으로}}", "{{작성자}}", "2026.04")
    toc_slide(prs, ["{{문제의 본질}}", "{{핵심 판단}}", "{{실행 계획}}", "Q&A"])
    chapter_slide(prs, 1, "{{챕터 제목}}")
    content_slide(
        prs,
        eyebrow="{{챕터 · 페이지 주제}}",
        title="{{명사구가 아니라 주장문으로 제목을 쓴다}}",
        body="{{본문은 세 줄을 넘기지 않는다. 한국어 슬라이드는 설명보다 결론, 결론보다 숫자가 먼저다.}}",
        page_num=4,
    )
    metrics_slide(prs, "핵심 지표", [("+42%", "전환율 개선"), ("3.8M", "월간 사용자"), ("99.9%", "가용성"), ("18일", "도입 기간")])
    ending_slide(prs, "감사합니다", "{{email@example.com}} · {{website}}")

    prs.save("output.pptx")
    print("OK: Saved output.pptx")


if __name__ == "__main__":
    main()
