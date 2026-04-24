---
name: kami
description: 'Typeset professional documents: resumes, one-pagers, white papers, letters, portfolios, slide decks. Warm parchment, ink-blue accent, serif-led hierarchy. CN uses TsangerJinKai02, EN uses Charter, JA uses YuMincho (best-effort). Triggers on "做 PDF / 排版 / 一页纸 / 白皮书 / 作品集 / 简历 / PPT / slides", or "build me a resume / make a one-pager / design a slide deck / turn this into a PDF / make this presentable".'
---

# kami · 紙

**紙 · かみ** - the paper your deliverables land on.

Good content deserves good paper. One design language across eight document types: warm parchment canvas, ink-blue accent, serif-led hierarchy, tight editorial rhythm.

Part of `Kaku · Waza · Kami` - Kaku writes code, Waza drills habits, **Kami delivers documents**.

## Step 1 · Decide the language

**Match the user's language.** Chinese -> `*.html` / `slides.py`. English -> `*-en.html` / `slides-en.py`. Japanese -> CJK path (`.html` / `slides.py`) as best-effort, JP Mincho first, visual QA before shipping. Reference docs are shared English specs.

When ambiguous (e.g. a one-word command like "resume"), ask a one-liner rather than guess.

| User language | HTML templates | Slides template |
|---|---|---|
| Chinese (primary) | `*.html` | `slides.py` |
| English | `*-en.html` | `slides-en.py` |
| Japanese (best-effort) | `*.html` | `slides.py` |
| Other languages (best-effort) | choose CJK or EN path by script coverage, then verify manually | choose `slides.py` or `slides-en.py`, then verify manually |

Always use `CHEATSHEET.md` and `references/*.md` for design, writing, production, and diagram guidance.

## Step 2 · Pick the document type

| User says | Document | CN template | EN template |
|---|---|---|---|
| "one-pager / 方案 / 执行摘要 / exec summary" | One-Pager | `one-pager.html` | `one-pager-en.html` |
| "white paper / 白皮书 / 长文 / 年度总结 / technical report" | Long Doc | `long-doc.html` | `long-doc-en.html` |
| "formal letter / 信件 / 辞职信 / 推荐信 / memo" | Letter | `letter.html` | `letter-en.html` |
| "portfolio / 作品集 / case studies" | Portfolio | `portfolio.html` | `portfolio-en.html` |
| "resume / resume / CV / 简历" | Resume | `resume.html` | `resume-en.html` |
| "slides / PPT / deck / 演示" | Slides | `slides.py` | `slides-en.py` |
| "个股研报 / equity report / 估值分析 / investment memo / 股票分析" | Equity Report | `equity-report.html` | `equity-report-en.html` |
| "更新日志 / changelog / release notes / 版本记录" | Changelog | `changelog.html` | `changelog-en.html` |

> Long deck (>20 slides): also read Deck Recipe (design.md section 8).

If unsure, ask a one-liner about the scenario rather than guess.

### Diagrams (primitives, not a 7th doc type)

When the user asks for **a diagram inside** a long-doc / portfolio / slide (not a standalone document), route to `assets/diagrams/` rather than a template:

| User says | Diagram | Template |
|---|---|---|
| "架构图 / architecture / 系统图 / components diagram" | Architecture | `assets/diagrams/architecture.html` |
| "流程图 / flowchart / 决策流 / branching logic" | Flowchart | `assets/diagrams/flowchart.html` |
| "象限图 / quadrant / 优先级矩阵 / 2×2 matrix" | Quadrant | `assets/diagrams/quadrant.html` |
| "柱状图 / bar chart / 分类对比 / grouped bars" | Bar Chart | `assets/diagrams/bar-chart.html` |
| "折线图 / line chart / 趋势 / 股价 / time series" | Line Chart | `assets/diagrams/line-chart.html` |
| "环形图 / donut / pie / 占比 / 分布结构" | Donut Chart | `assets/diagrams/donut-chart.html` |
| "状态机 / state machine / 状态图 / lifecycle" | State Machine | `assets/diagrams/state-machine.html` |
| "时间线 / timeline / 里程碑 / milestones / roadmap" | Timeline | `assets/diagrams/timeline.html` |
| "泳道图 / swimlane / 跨角色流程 / cross-team flow" | Swimlane | `assets/diagrams/swimlane.html` |
| "树状图 / tree / hierarchy / 层级 / 组织架构" | Tree | `assets/diagrams/tree.html` |
| "分层图 / layer stack / 分层架构 / OSI / stack" | Layer Stack | `assets/diagrams/layer-stack.html` |
| "维恩图 / venn / 交集 / overlap / 集合关系" | Venn | `assets/diagrams/venn.html` |
| "K 线 / candlestick / OHLC / 股价走势 / price history" | Candlestick | `assets/diagrams/candlestick.html` |
| "瀑布图 / waterfall / 收入桥 / revenue bridge / decomposition" | Waterfall | `assets/diagrams/waterfall.html` |

Read `references/diagrams.md` before drawing - it has the selection guide, kami token map, and the AI-slop anti-pattern table. Extract the `<svg>` block from the template and drop it into a `<figure>` inside long-doc / portfolio.

Before drawing, always ask: **would a well-written paragraph teach the reader less than this diagram?** If no, don't draw.

**Auto-select charts from data.** When the content contains numerical data (revenue splits, trends over time, category comparisons), choose the appropriate chart type and embed it. Do not wait for the user to request a specific chart. Selection guide: proportional breakdown -> donut, time series -> line, category comparison -> bar, price history -> candlestick, value decomposition -> waterfall.

## Step 2.1 · Source and material pass

Run this before distilling or filling content when the document depends on facts or materials outside the user's draft. Skip it only for personal drafts where the user already supplied everything needed.

### Source check

Trigger when the document mentions a specific company, product, person, release date, version, funding round, metric, market fact, technical spec, or any current fact likely to change.

- Use primary sources before writing: user-provided material, official site, docs, filings, press release, app store page, or repo release
- Keep a short note of source names and dates for facts that drive the document
- If sources conflict or a fact cannot be checked quickly, ask the user instead of choosing silently
- Avoid current-sounding claims such as "latest", "recent", "new", version numbers, launch dates, or financial figures unless they are checked

### Material check

Trigger when the document is about a company, product, project, venue, or personal brand.

Confirm the materials that make the subject recognizable before layout:

| Need | Required when | Accept |
|---|---|---|
| Logo | Any branded document | User file or official SVG/PNG |
| Product image | Physical product / venue / object | Official image, user image, or marked gap |
| UI screenshot | App / SaaS / website / tool | Current screenshot, official product image, or user capture |
| Brand colors | Branded one-pager / portfolio / deck | Official value, extracted asset value, or keep kami ink-blue |
| Fonts | Only if brand typography matters | Official font, close system fallback, or kami default |

If a required item is missing, use a compact gap table and ask once. Do not replace missing material with generic imagery, approximate logo drawings, or invented values.

## Step 2.5 · Distill raw content (if applicable)

Skip this step if the user already provides structured content (clear sections, bullet points, metrics in place).

When the user hands over **raw material** (meeting notes, brain dump, existing doc in different format, chat transcript, scattered points):

1. **Extract**: pull out every factual claim, number, date, name, source, material reference, and action item
2. **Classify**: map each extract to the target template's sections (see `references/writing.md` for section structure per doc type)
3. **Gap-check**: list what the template needs but the raw content doesn't have - include missing facts, missing proof, and missing materials
4. **Ask once**: share the gap table with the user. Do not guess to fill gaps.

Example gap-check:

| Template needs | Found | Missing |
|---|---|---|
| 4 metric cards | "8 years", "50-person team" | 2 more quantifiable results |
| 3-5 core projects | 2 mentioned | at least 1 more with outcome |
| Materials | logo file provided | product screenshot source |

Then proceed to Step 3 with structured, distilled content.

---

## Step 3 · Load the right amount of spec

Pick the tier that matches the task. Default to the lowest tier that covers the work.

| Tier | When | Read |
|---|---|---|
| **Content-only** | Updating text, swapping bullets, translating an existing doc. CSS stays untouched. | `CHEATSHEET.md` only |
| **Layout tweak** | Adjusting spacing, moving sections, changing font size within spec. CSS touched. | `CHEATSHEET.md` + template (tokens already inline) |
| **New document** | Building from scratch or from raw content. | Full design spec + writing spec + template |
| **Sources / materials** | Company, product, market, launch, funding, specs, or branded subject. | `writing.md` source rules + user/source material |
| **Deck (>20 slides)** | Long presentation needing Part Divider, Code Cards, section headers. | Full design spec + Deck Recipe (design.md section 8) |
| **Troubleshoot** | Rendering bug, font issue, page overflow. | `production.md` (+ design spec if CSS is the cause) |
| **Diagram** | Embedding SVG in a doc. | `diagrams.md` only (has its own token map) |

You can always escalate mid-task if the work turns out to need more than the initial tier.

The full spec files for reference:
- Design: `references/design.md`
- Writing: `references/writing.md`
- Production: `references/production.md`
- Diagrams: `references/diagrams.md`

## Step 4 · Fill content into the template

- Copy the template into your working directory; don't write HTML from scratch
- **CSS stays untouched**, only edit the body
- Content follows `writing.md`: data over adjectives, distinctive phrasing over industry clichés
- **Before filling, read the quality bar for your document type** in `writing.md` section "Quality bars by document type". Structure is necessary but not sufficient: a resume bullet needs Action + Scope + Result + Business Outcome; an equity report needs variant perception + quantified catalysts; slides need assertion-evidence titles. Meeting the quality bar is as important as filling every placeholder.

### Fill PDF metadata (WeasyPrint reads these into the PDF)

Every template has meta placeholders in `<head>`. Fill all four before building:

| Placeholder (CN) | Placeholder (EN) | Rule |
|---|---|---|
| `{{作者}}` | `{{AUTHOR}}` | Resume/letter/portfolio: use the person's name from the doc. All others: leave as-is (build script infers from git config or env) |
| `{{摘要}}` | `{{DESCRIPTION}}` | Extract one sentence (≤150 chars) from the first 2 paragraphs |
| `{{关键词}}` | `{{KEYWORDS}}` | 3-5 keywords from the title + section headings, comma-separated |
| `{{文档标题}}` / `{{信件主题}}` etc. | `{{DOC_TITLE}}` / `{{LETTER_SUBJECT}}` etc. | Infer from the H1 or `.header .title` text |

`<meta name="generator" content="Kami">` is already fixed in the template; do not change it.

**Author inference**: `build.py` automatically sets PDF `/Author` metadata from:
1. `git config user.name` (primary)
2. `KAMI_AUTHOR` environment variable (fallback)
3. `"Kami"` (final fallback)

For personal documents (resume/letter/portfolio), the HTML `<meta name="author">` should match the person's name in the content. For non-personal documents (one-pager/long-doc), leave the placeholder as-is and let the build script infer it.

## Step 5 · Build & verify

```bash
python3 scripts/build.py --verify           # build all templates + page count + font check + slides
python3 scripts/build.py --verify resume-en # single target full verification
python3 scripts/build.py --verify slides    # single slide deck verification
python3 scripts/build.py --check-placeholders path/to/filled.html
python3 scripts/build.py --check            # CSS rule violations only (fast, no build)
```

Source templates intentionally keep `{{...}}` fields. Run placeholder checks on completed documents, not on the template library.

Visual anomalies (tag double rectangle, font fallback, page break issues) -> `production.md` Part 4.

## Fonts

**Chinese**
- Main serif: TsangerJinKai02-W04.ttf (400 weight) + TsangerJinKai02-W05.ttf (500 weight, real bold)
- Templates use dual @font-face declarations: W04 for body text, W05 for headings
- Both files are commercial fonts. Keep them available in the repository for local preview and CDN fallback, but do not bundle them inside Claude Desktop skill ZIPs
- Fallback chain baked into templates: Source Han Serif SC -> Noto Serif CJK SC -> Songti SC -> STSong -> Georgia

**Japanese (best-effort)**
- Uses CJK template path, no dedicated `-ja` templates yet
- JP Mincho-first stack: YuMincho -> Hiragino Mincho ProN -> Noto Serif CJK JP -> Source Han Serif JP -> TsangerJinKai02 -> serif
- Visually verify line breaks, punctuation rhythm, and emphasis weight before shipping

**English**
- Single serif: Charter (system-bundled, macOS/iOS), used for both headlines and body
- No separate sans: `--sans: var(--serif)`, one font per page
- Fallback: Georgia (cross-platform) / Palatino / Times New Roman

Font files next to HTML with relative `@font-face` paths is the most stable setup. `scripts/package-skill.sh` excludes TsangerJinKai TTFs from the Claude Desktop ZIP.

**Font auto-recovery (Claude Desktop)**

Before building Chinese documents, check font files. If missing, download into `assets/fonts/`:

```bash
# Check
test -f assets/fonts/TsangerJinKai02-W04.ttf || {
  curl -fsSL "https://cdn.jsdelivr.net/gh/tw93/Kami@main/assets/fonts/TsangerJinKai02-W04.ttf" \
    -o assets/fonts/TsangerJinKai02-W04.ttf
  curl -fsSL "https://cdn.jsdelivr.net/gh/tw93/Kami@main/assets/fonts/TsangerJinKai02-W05.ttf" \
    -o assets/fonts/TsangerJinKai02-W05.ttf
}
```

Run once before building. If network is unavailable, WeasyPrint falls back to Source Han Serif SC.

## Feedback protocol

When the user gives **vague visual feedback** ("looks off", "太挤了", "not elegant"), do not guess. Ask back with current values:

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
