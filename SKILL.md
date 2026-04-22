---
name: kami
description: 'Typeset any professional document: resumes, one-pagers, white papers, letters, portfolios, slide decks. Warm parchment design system with ink-blue accent, serif-led hierarchy, and tight editorial spacing. Full bilingual support: Chinese docs use TsangerJinKai02 + Source Han, English docs use Newsreader + Inter. Triggers on "做 PDF / 排版 / 生成报告 / 一页纸 / 白皮书 / 作品集 / 正式信件 / 简历 / PPT / slides / 高质量文档 / 好看的排版", or "build me a resume / make a one-pager / design a slide deck / turn this into a PDF / make this presentable / polish typography", and when raw content is handed over to be "typeset, designed, made presentable".'
---

# kami · 紙

**紙 · かみ** - the paper your deliverables land on.

Good content deserves good paper. One design language across six document types: warm parchment canvas, ink-blue accent, serif-led hierarchy, tight editorial rhythm.

Part of `Kaku · Waza · Kami` - Kaku writes code, Waza drills habits, **Kami delivers documents**.

## Step 1 · Decide the language

**Match the user's language**. If they write in Chinese -> use the Chinese templates (`.html`, Chinese references). If they write in English -> use the English templates (`-en.html`, `.en.md` references).

When ambiguous (e.g. a one-word command like "resume"), ask a one-liner rather than guess.

| User language | Templates | References | Cheatsheet |
|---|---|---|---|
| Chinese (primary) | `*.html` / `slides.py` | `references/*.md` | `CHEATSHEET.md` |
| English | `*-en.html` / `slides-en.py` | `references/*.en.md` | `CHEATSHEET.en.md` |

## Step 2 · Pick the document type

| User says | Document | CN template | EN template |
|---|---|---|---|
| "one-pager / 方案 / 执行摘要 / exec summary" | One-Pager | `one-pager.html` | `one-pager-en.html` |
| "white paper / 白皮书 / 长文 / 年度总结 / technical report" | Long Doc | `long-doc.html` | `long-doc-en.html` |
| "formal letter / 信件 / 辞职信 / 推荐信 / memo" | Letter | `letter.html` | `letter-en.html` |
| "portfolio / 作品集 / case studies" | Portfolio | `portfolio.html` | `portfolio-en.html` |
| "resume / resume / CV / 简历" | Resume | `resume.html` | `resume-en.html` |
| "slides / PPT / deck / 演示" | Slides | `slides.py` | `slides-en.py` | Long deck (>20 slides): also read Deck Recipe (design.md section 8) |

If unsure, ask a one-liner about the scenario rather than guess.

### Diagrams (primitives, not a 7th doc type)

When the user asks for **a diagram inside** a long-doc / portfolio / slide (not a standalone document), route to `assets/diagrams/` rather than a template:

| User says | Diagram | Template |
|---|---|---|
| "架构图 / architecture / 系统图 / components diagram" | Architecture | `assets/diagrams/architecture.html` |
| "流程图 / flowchart / 决策流 / branching logic" | Flowchart | `assets/diagrams/flowchart.html` |
| "象限图 / quadrant / 优先级矩阵 / 2×2 matrix" | Quadrant | `assets/diagrams/quadrant.html` |

Read `references/diagrams.md` / `diagrams.en.md` before drawing - it has the selection guide, kami token map, and the AI-slop anti-pattern table. Extract the `<svg>` block from the template and drop it into a `<figure>` inside long-doc / portfolio.

Before drawing, always ask: **would a well-written paragraph teach the reader less than this diagram?** If no, don't draw.

## Step 2.5 · Distill raw content (if applicable)

Skip this step if the user already provides structured content (clear sections, bullet points, metrics in place).

When the user hands over **raw material** (meeting notes, brain dump, existing doc in different format, chat transcript, scattered points):

1. **Extract**: pull out every factual claim, number, date, name, and action item
2. **Classify**: map each extract to the target template's sections (see `references/writing.md` for section structure per doc type)
3. **Gap-check**: list what the template needs but the raw content doesn't have - present as a compact table
4. **Ask once**: share the gap table with the user. Do not guess to fill gaps.

Example gap-check:

| Template needs | Found | Missing |
|---|---|---|
| 4 metric cards | "8 years", "50-person team" | 2 more quantifiable results |
| 3-5 core projects | 2 mentioned | at least 1 more with outcome |

Then proceed to Step 3 with structured, distilled content.

---

## Step 3 · Load the right amount of spec

Pick the tier that matches the task. Default to the lowest tier that covers the work.

| Tier | When | Read |
|---|---|---|
| **Content-only** | Updating text, swapping bullets, translating an existing doc. CSS stays untouched. | `CHEATSHEET.md` only (170 lines) |
| **Layout tweak** | Adjusting spacing, moving sections, changing font size within spec. CSS touched. | `CHEATSHEET.md` + template (tokens already inline) |
| **New document** | Building from scratch or from raw content. | Full design spec + writing spec + template |
| **Deck (>20 slides)** | Long presentation needing Part Divider, Code Cards, section headers. | Full design spec + Deck Recipe (design.md section 8) |
| **Troubleshoot** | Rendering bug, font issue, page overflow. | `production.md` (+ design spec if CSS is the cause) |
| **Diagram** | Embedding SVG in a doc. | `diagrams.md` only (has its own token map) |

You can always escalate mid-task if the work turns out to need more than the initial tier.

The full spec files for reference:
- Design: `references/design.md` (CN) / `references/design.en.md` (EN)
- Writing: `references/writing.md` / `writing.en.md`
- Production: `references/production.md` / `production.en.md`
- Diagrams: `references/diagrams.md` / `diagrams.en.md`

## Step 4 · Fill content into the template

- Copy the template into your working directory; don't write HTML from scratch
- **CSS stays untouched**, only edit the body
- Content follows `writing.md` / `writing.en.md`: data over adjectives, distinctive phrasing over industry clichés

## Step 5 · Build & verify

```bash
python3 scripts/build.py --verify           # build all + page count + font check + placeholder check
python3 scripts/build.py --verify resume-en # single target full verification
python3 scripts/build.py --check            # CSS rule violations only (fast, no build)
```

Visual anomalies (tag double rectangle, font fallback, page break issues) -> `production.md` / `production.en.md` Part 4.

## Fonts

**Chinese**
- Main serif: TsangerJinKai02-W04.ttf (400 weight) + TsangerJinKai02-W05.ttf (500 weight, real bold)
- Both files are commercial fonts, included in repo
- Templates use dual @font-face declarations: W04 for body text, W05 for headings
- Fallback chain baked into templates: Source Han Serif SC -> Noto Serif CJK SC -> Songti SC -> Georgia

**English**
- Main serif: Newsreader (Google Fonts, open source) - used for both headlines and body
- Sans: Inter (open source) - used for UI elements only (labels, eyebrows, meta)
- Fallback: Charter (macOS) / Georgia (cross-platform), Helvetica Neue / system-ui

Font files next to HTML and `@font-face` relative paths is the most stable setup.

## Feedback protocol

When the user gives **vague visual feedback** ("looks off", "不对劲", "spacing weird", "too cramped", "not elegant"):

Do not guess. Ask back using kami vocabulary, with current values included.

| User says | Ask about |
|---|---|
| "太挤了" / "too cramped" | Which element? Line-height (current: X)? Padding (current: Y)? Page margin? |
| "太松了" / "too loose" | Same direction, reversed |
| "颜色不对" / "color feels wrong" | Which element? Brand blue overused? A gray reading too cool? |
| "不够好看" / "not polished" | Font rendering? Alignment? Whitespace distribution? Hierarchy unclear? |
| "看着不专业" / "unprofessional" | Content wording? Or layout (alignment, consistency)? |

Template response: "X is currently set to Y. Would you like (a) [specific alternative within spec] or (b) [another option]?"

Never say "I'll adjust the spacing" without naming the exact property and its new value.

---

## When not to use this skill

- User explicitly wants Material / Fluent / Tailwind default - different design language
- Need dark / cyberpunk / futurist aesthetic (this is deliberately anti-future)
- Need saturated multi-color (this has one accent)
- Need cartoon / animation / illustration style (this is editorial)
- Web dynamic app UI (this is for print / static documents)

---

Next: **apply Step 3's tier table to decide what to read**, then copy the matching template and start filling.
