---
name: kami
description: 'Typeset professional documents and product landing pages: resumes, one-pagers, white papers, letters, portfolios, slide decks, landing pages. Warm parchment, ink-blue accent, serif-led hierarchy. CN uses TsangerJinKai02, EN uses Charter, JA uses YuMincho (best-effort). Triggers on "做 PDF / 排版 / 一页纸 / 白皮书 / 作品集 / 简历 / PPT / slides / Marp / markdown slides / マークダウンのスライド / 落地页 / 官网 / landing page / product page", or "build me a resume / make a one-pager / design a slide deck / turn this into a PDF / make this presentable / create a landing page".'
---

# kami · 紙

**紙 · かみ** - the paper your deliverables land on.

Good content deserves good paper. One design language across eight document types: warm parchment canvas, ink-blue accent, serif-led hierarchy, tight editorial rhythm.

Part of `Kaku · Waza · Kami` - Kaku writes code, Waza drills habits, **Kami delivers documents**.

**Update check (non-blocking).** At the start of a task, run `bash scripts/check-update.sh`. It does a read-only version check at most once per day and prints one line when a newer kami is available; relay that line to the user, then continue. It sends no data, and fails silently when offline, sandboxed, or without `curl`. Never let it block the work.

## Step 0 · Load brand profile (if exists)

Check `~/.config/kami/brand.md` (preferred) or `~/.kami/brand.md` (legacy fallback). If found, read `references/brand-profile.md` for the full four-layer application spec (placeholder substitution, session defaults, visual customization, habit notes) and its six guardrails. If no profile exists, continue without interruption.

Key rule: explicit prompt > editorial judgment > habit notes > frontmatter defaults > built-in defaults. Profile fills gaps silently; it never overrides the current conversation.

## Step 0.5 · User project style scan (opt-in)

Run this only when the user explicitly references a sibling project as a visual reference: "like my <project> site", "match the style of <repo>", "use the look from <directory>". Skip silently when no such reference exists.

When triggered, before generating:

1. Locate the referenced project's style files:
   ```bash
   find <referenced-path> -maxdepth 4 \( -name "*.css" -o -name "tailwind.config.*" -o -name "theme.*" -o -name "tokens.*" \) | head -20
   ```
2. Extract: dominant color values (hex / hsl), font stack, spacing scale, border-radius scale. Prefer values declared in CSS variables or design tokens over inline literals.
3. Merge into the in-session brand profile as Layer C (visual customization), not Layer B (session defaults). Do not override an explicit `--brand` flag or values that the user typed in this turn.
4. Report back in one line before continuing: "scanned <project>, extracted N colors / M fonts; using as visual reference."

Skip and fall back to the brand profile defaults if the referenced path does not exist, no CSS-like files are found, or the extraction would conflict with the user's explicit values in the current message.

---

## Step 1 · Decide the language

**Match the user's language.** Chinese -> `*.html` / `slides-weasy.html`. English -> `*-en.html` / `slides-weasy-en.html`. Japanese -> CJK path (`.html` / `slides-weasy.html`) as best-effort, JP Mincho first, visual QA before shipping. Korean -> dedicated `*-ko.html` / `slides-weasy-ko.html` family as best-effort, visual QA before shipping. Reference docs are shared English specs.

When ambiguous (e.g. a one-word command like "resume"), ask a one-liner rather than guess.

| User language | HTML templates | Slides (PDF default) | Slides (PPTX fallback) |
|---|---|---|---|
| Chinese (primary) | `*.html` | `slides-weasy.html` | `slides.py` |
| English | `*-en.html` | `slides-weasy-en.html` | `slides-en.py` |
| Japanese (best-effort) | `*.html` | `slides-weasy.html` | `slides.py` |
| Korean (best-effort) | `*-ko.html` | `slides-weasy-ko.html` | n/a (use `slides-en.py` only if PPTX is required) |
| Other languages (best-effort) | choose CJK or EN path by script coverage, then verify manually | choose `slides-weasy.html` or `slides-weasy-en.html`, then verify manually | use `slides.py` / `slides-en.py` only if PPTX is required |

> Default to the WeasyPrint HTML path; fall back to PPTX (`slides*.py`) only when the user explicitly needs an editable deck.

Always use `CHEATSHEET.md` and `references/*.md` for design, writing, production, and diagram guidance.

Code blocks with `class="language-*"` are highlighted only when optional `Pygments` is installed in the build environment. Without it, PDFs still render and code blocks stay monochrome.

## Step 1.5 · Intent extraction (silent checklist)

Before choosing a template, verify these four dimensions are clear. Do not ask unless 2+ are missing and cannot be inferred from context.

| Dimension | What to extract | Example |
|---|---|---|
| **Purpose** | Why this document exists | Persuade investor vs. align internal team vs. close a candidate |
| **Audience** | Who reads it, what they already know | Technical CTO (skip basics) vs. non-technical board (explain terms) |
| **Constraint** | Hard limits on length, format, tone, or delivery | "One page max", "formal English", "print-ready A4" |
| **Success** | What outcome counts as success | They schedule a meeting / they approve the budget / they understand the architecture |

Rules:
- If the conversation already answered a dimension, skip it silently.
- If a dimension can be inferred from the document type (e.g. resume purpose is always "get an interview"), skip it.
- If 2+ dimensions are genuinely unclear, ask in a single compact question (max 2 sub-questions).
- Never ask all four as a checklist. This is a background verification, not a form.

## Execution contract

Before creating or modifying an output, lock the contract: language, template, output format, page or length target, visual acceptance check, and verification command. Infer from the user's request when clear; ask only when missing fields materially change the deliverable.

Use the nearest existing template and verification path. Do not add a new template, shared CSS layer, dependency, script flag, or optional mode unless the current request cannot be satisfied without it.

If a change touches `SKILL.md`, templates, scripts, references, or package inputs, decide whether `dist/kami.zip` must be refreshed before handoff. Shipped behavior is not ready until the package contains the changed files.

---

## Step 2 · Pick the document type

| User says | Document | CN template | EN template | KO template |
|---|---|---|---|---|
| "one-pager / 方案 / 执行摘要 / exec summary" | One-Pager | `one-pager.html` | `one-pager-en.html` | `one-pager-ko.html` |
| "white paper / 白皮书 / 长文 / 年度总结 / technical report" | Long Doc | `long-doc.html` | `long-doc-en.html` | `long-doc-ko.html` |
| "formal letter / 信件 / 辞职信 / 推荐信 / memo" | Letter | `letter.html` | `letter-en.html` | `letter-ko.html` |
| "portfolio / 作品集 / case studies" | Portfolio | `portfolio.html` | `portfolio-en.html` | `portfolio-ko.html` |
| "resume / CV / 简历 / 履歴書" | Resume | `resume.html` | `resume-en.html` | `resume-ko.html` |
| "slides / PPT / deck / 演示" | Slides | `slides-weasy.html` | `slides-weasy-en.html` | `slides-weasy-ko.html` |
| "个股研报 / equity report / 估值分析 / investment memo / 股票分析" | Equity Report | `equity-report.html` | `equity-report-en.html` | `equity-report-ko.html` |
| "更新日志 / changelog / release notes / 版本记录" | Changelog | `changelog.html` | `changelog-en.html` | `changelog-ko.html` |
| "landing page / 落地页 / 官网 / product page / 产品页" | Landing Page | `landing-page.html` | `landing-page-en.html` | `landing-page-ko.html` |

> **Changelog vs. release notes**: The changelog template above is for styled document output. GitHub release notes are a separate deliverable; use `/write` with Release Note Template Mode.

> **Landing Page**: Screen-first interactive template. No PDF output. Includes gallery carousel with auto-rotate, hero entrance animation, responsive breakpoints (880px / 480px), and prefers-reduced-motion support. Deploy as static HTML to Vercel / Netlify / any host. The agent fills {{PLACEHOLDER}} values and HTML comment blocks, then saves as a ready-to-serve `.html` file.

> **Landing Page companion files**: For a production multilingual deploy, copy the five `landing-page-*.example` files alongside the main HTML, remove the `.example` suffix, and fill the placeholders. They cover Vercel rewrites and headers, sitemap hreflang, robots AI allowlist, and llms.txt + llms-full.txt for AI assistants. The main HTML already ships matching hreflang and og:locale in `<head>`; an Accept-Language redirect at the end of `landing-page-en.html` is commented out for opt-in. `{{SITE_ORIGIN}}` is the scheme + host of your `{{CANONICAL_URL}}` (e.g. `https://example.com`). See `references/design.md` Section 11 «Companion assets».

> **Production product site mode**: If the user needs docs, help, releases, changelog, roadmap, legal pages, or more than two locales, treat it as a site system. Lock product category, real screenshot slots, locale list, companion files, long-content pages, and generator/check needs before filling templates. Keep project-specific release artifacts, payment providers, appcast rules, and private local paths out of Kami. See `references/design.md` Section 11 «Product site system».

> **Documentation pages**: When a landing page grows into a docs or help site, use the doc shell in `references/design.md` Section 11 «Documentation site»: a sticky sidebar nav with a 2px brand rail (not a dark underline), an on-this-page TOC hidden below the tablet breakpoint, a constrained prose measure, and a quiet borderless prev/next pager (text links, not bordered cards). Highlight code at build time with zero runtime JS on a dark code surface; plain code stays the source of truth.

> Slides: default to `slides-weasy.html` / `slides-weasy-en.html` / `slides-weasy-ko.html` (WeasyPrint HTML → PDF). Use `slides.py` / `slides-en.py` only when the user explicitly requires an editable PPTX file. Use `assets/templates/marp/slides-marp(.md|.css)` only when the user explicitly asks for Marp / markdown slides / a deck that lives in a `.md` file.

> Deck recipe: read design.md Section 8 before drafting slides. Sketch title sequence, evidence shape, and image slot before generating or cropping visuals. Keep audience copy separate from visual briefs. Marp-specific constraints live in design.md §8 «Marp variant».

### Decision tree (use before asking)

Walk this tree before reaching for a one-liner question. Ask only when two cells genuinely both fit.

| Signal | Document |
|---|---|
| Length target unknown | Ask "how many pages" before classifying |
| ≤ 1 page + investor / recruiter / exec summary audience | one-pager |
| ≤ 1 page + formal correspondence (sales, hiring, resignation, memo) | letter |
| 1.5-2 pages + career narrative + project bullets | resume |
| 3-6 pages + project showcase + visual heavy | portfolio |
| 6-15 pages + sustained argument + low visual density | long-doc |
| Presentation flow + speaker support + per-slide assertion | slides |
| Financial / metrics dashboard + thesis + price or risk view | equity-report |
| Version-by-version log + release facts | changelog |
| Product showcase + pricing + screenshots + FAQ for browser | landing-page |

Ambiguity examples that justify a one-liner:
- "1.5 page career story with heavy visuals" -> ask "resume or portfolio?"
- "2 page exec summary with metric tiles" -> ask "one-pager or equity-report?"
- "5 page argument with several charts" -> ask "long-doc or portfolio?"

Pick from the tree first. Ask only when the tree is genuinely silent.

### Diagrams (primitives, not a separate template type)

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

**Auto-select charts from data.** When content contains numerical data, choose the chart type and embed it without waiting for the user to specify. Decision tree (first match wins):

| Data shape | Chart |
|---|---|
| Has open/high/low/close fields, or per-day price | Candlestick |
| Has + and - contributions that sum to a total (bridge, waterfall, P&L) | Waterfall |
| One series, values sum to ~100%, items ≤ 6 | Donut |
| One series, values sum to ~100%, items ≥ 7 | Horizontal bar |
| Two or more series across time (months, quarters, years) | Line |
| One series across time, large count changes dominate (not rate) | Bar |
| Multiple categories, same time snapshot, 2+ series | Grouped bar |
| 2×2 strategic or priority positioning | Quadrant |
| Hierarchical data with depth ≥ 2 | Tree |
| Process with decision branches | Flowchart |
| Cross-team or cross-role process with ≥ 3 actors | Swimlane |
| Set overlaps or shared attributes between 2-3 groups | Venn |
| Category comparison, single series, no time axis | Bar |

When data fits multiple types, prefer the one that shows variance most clearly. Always embed inside a `<figure>` with a caption that states the insight, not just the data range.

### Illustrations (host image model, not inline SVG)

Inline diagrams above are vector SVGs you assemble by hand. For a standalone raster illustration, or a redraw of a figure, photo, or screenshot in the Kami look, delegate the drawing to the host's own image generation. Never call an external image API or require a key; rendering is the host's job.

- If the running host can generate images (for example ChatGPT), apply the brief below and render the image directly.
- If it cannot (Claude, Codex, most coding agents), output the brief as text so the user can paste it into any image model.

Brief: warm parchment (`#f5f4ed`) background, never pure white; one accent only, ink blue (`#1B365D`); all else warm gray with a yellow-brown undertone, no other colors; thin single-line geometric strokes and simple flat icons; no gradients, drop shadows, or 3D; serif labels; generous whitespace, composed like a figure in a well-typeset report.

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

Logo fallback: when the request names no logo but the brand profile has a `logo` path, fill the commented `.brand-logo` slot in `one-pager` / `portfolio` / `slides-weasy` per `references/brand-profile.md` Layer C. Expand `~` to an absolute path, and if the file is missing or the template has no slot, leave it commented and render without a logo (never insert a broken image). An explicit logo in the current request always wins.

### Materials status block

After the material check, output a structured status block before continuing. This is a one-shot transparency display, not a question:

```
Materials status:
- Logo: OK assets/client-logo.svg
- Brand colors: OK #1B365D mapped to --brand
- Product screenshot: MISSING (proceeding with kami default placeholder)
- UI screenshot: not required for this doc type
```

Use `OK`, `MISSING`, or `not required`. If a required item is missing and no user input arrived, ask once with the gap table; otherwise continue silently.

## Step 2.5 · Distill raw content (if applicable)

**Auto-detect whether to distill.** Do not ask the user; judge from the input:

| Skip distill (fill directly) | Run distill |
|---|---|
| Content has explicit section labels matching template structure | Raw prose without section structure |
| Metrics already quantified with units in place | Numbers scattered or implied, not extracted |
| User wrote "use this as-is" / "直接用这个" / "原封不动" | User pasted multi-source dump (chat / email thread / multiple docs) |
| Content count matches template (e.g. 4 metrics for 4 metric cards) | Content count mismatches template (too many or too few items) |
| One coherent voice with consistent claims | Conflicting claims or duplicate facts across sources |

When in doubt, run distill. Distill is cheap; rebuilding a misaligned doc is not.

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

Then proceed to Step 2.6 (slides) or the layout note (all other doc types) with structured, distilled content.

## Step 2.6 · Deck pre-flight (slides only)

Skip this step for every doc type except slides.

### Path selection

Default to the WeasyPrint HTML path. Switch to pptx only if the user explicitly requires an editable PPTX file. Switch to Marp only when the user explicitly asks for Marp / markdown slides.

| Path | Template | When |
|---|---|---|
| WeasyPrint HTML → PDF (default) | `slides-weasy.html` / `slides-weasy-en.html` / `slides-weasy-ko.html` | All cases unless PPTX or Marp is required |
| python-pptx → PPTX (fallback) | `slides.py` / `slides-en.py` | User explicitly requires editable PPTX |
| Marp Markdown (variant) | `assets/templates/marp/slides-marp.md` (+ `slides-marp.css`) / `slides-marp-en.md` (+ `slides-marp-en.css`) | User explicitly asks for Marp, "markdown slides", or a `.md` deck. Shipped `.md` is a working demo of Kami Marp itself; copy it, swap content, keep the structure. Renders via local `marp` CLI; not bundled. |

### Page size

Default is `280mm 158mm`. Ask only if the user has mentioned length or density constraints.

| Size | When |
|---|---|
| `280mm 158mm` | Default; fits most decks |
| `297mm 167mm` | User wants a bit more room |
| `338mm 190mm` | Heavy content slide or many data points per page |

### Content pre-flight

Before drafting any slide, confirm these points with the user. Ask all at once, skip any already answered:

| # | Question |
|---|---|
| 1 | **Audience + venue** - who is in the room, and is it live keynote, investor 1:1, or async share link? |
| 2 | **Length target** - presentation time or slide count? (15 min: ~10 slides / 30 min: ~20 slides / 45 min: ~25-30 slides) |
| 3 | **Source material** - what content is already ready: outline, doc, notes, data? |
| 4 | **Images** - are screenshots, charts, logos, or product images available; which slides need real evidence slots; and is a separate visual brief needed? |
| 5 | **Hard constraints** - brand colors, required logo, PPTX required, any slides that must exist? |
| 6 | **Format confirmation** - slides deck, or a one-pager that looks like a deck? |

Before drafting any landing page or product site, lock these points from the source material. Ask once only when a missing item would change the deliverable:

| # | Lock |
|---|---|
| 1 | **Product category** - first-viewport category: app, CLI, terminal, utility, skill, template system, or another user-provided label. |
| 2 | **Real assets** - available product screenshots, logo, icon, or UI captures, mapped to hero/gallery/feature/social slots. Missing assets must stay marked, not replaced with stock imagery. |
| 3 | **Site shape** - single page, or home plus docs/help/releases/changelog/roadmap/legal pages? |
| 4 | **Locales** - exact locale list, canonical paths, and whether a generator/check mode is needed. |
| 5 | **Truth surfaces** - install path, price, version, support route, FAQ, `llms.txt`, and `llms-full.txt` that must stay synchronized. |

### Content rules for slides

- Ghost deck test: read only the slide titles in order. They must tell the argument; if not, fix titles or structure before styling
- One evidence shape per slide: chart, table, screenshot, code, quote, or conclusion. Split mixed evidence instead of crowding one slide
- Audience copy stays clean: titles, body, and captions never contain image prompts, crop instructions, or generation notes
- No section divider slides: use `.eyebrow` for section numbering, not a dedicated blue-background page
- No CJK parentheses: replace `（...）` with `·` or `,`
- Each bullet fits one line: trim until it does
- 2×2 layouts: use `table.t2x2`, not CSS Grid
- Pinned conclusions: use `.co` at `position: absolute; bottom: 12mm`

These rules apply identically to Marp decks. Marp-specific syntax: see `references/design.md` §8 «Marp variant».

## Step 2.7 · Layout note (transparent, non-blocking)

Before loading specs and filling the template, write a short editor-style note stating the layout intent: template choice, length target, narrative arc, embedded diagrams, material status, and output formats. Match the document's language. Keep it under 80 words, written as prose, not a status panel. Continue immediately after; do not wait.

Example (CN):

> 排版意图：Equity Report 中文版，2 页 A4。先立论与目标价，进入估值 (DCF 与可比公司)，落于催化剂与风险。中段嵌一张营收趋势折线和 FY26 收入桥瀑布。Logo 已就位，产品图暂缺，header 改走纯文字。输出 HTML 与 PDF。

Example (EN):

> Layout intent: Equity Report (EN), two pages A4. Open with thesis and price target, run through valuation (DCF and comparables), close on catalysts and risks. A revenue line chart and an FY26 waterfall sit mid-doc. Logo is in hand; product image is absent, so the header stays text-only. Output: HTML and PDF.

The note is for transparency, not approval. If the user pushes back, adjust; otherwise proceed to Step 3.

---

## Step 3 · Load the right amount of spec

Pick the tier that matches the task. Default to the lowest tier that covers the work.

| Tier | When | Read |
|---|---|---|
| **Content-only** | Updating text, swapping bullets, translating an existing doc. CSS stays untouched. | `CHEATSHEET.md` only |
| **Layout tweak** | Adjusting spacing, moving sections, changing font size within spec. CSS touched. | `CHEATSHEET.md` + template (tokens already inline) |
| **New document** | Building from scratch or from raw content. | Full design spec + writing spec + template |
| **Resume content** | Resume-specific bullet structure, project framing, scope-result-outcome rules. | `resume-writing.md` + template |
| **Sources / materials** | Company, product, market, launch, funding, specs, or branded subject. | `writing.md` source rules + user/source material |
| **Deck (>20 slides)** | Long presentation needing Part Divider, Code Cards, section headers. | Full design spec + Deck Recipe (design.md section 8) |
| **Troubleshoot** | Rendering bug, font issue, page overflow. | `production.md` (+ design spec if CSS is the cause) |
| **Anti-patterns** | Reviewing AI-generated drafts before shipping. | `anti-patterns.md` (six-category checklist) |
| **Diagram** | Embedding SVG in a doc. | `diagrams.md` only (has its own token map) |

You can always escalate mid-task if the work turns out to need more than the initial tier.

The full spec files for reference:
- Design: `references/design.md`
- Writing (general): `references/writing.md`
- Writing (resume-specific): `references/resume-writing.md`
- Production: `references/production.md`
- Diagrams: `references/diagrams.md`
- Anti-patterns: `references/anti-patterns.md`

## Step 4 · Fill content into the template

- Copy the template into your working directory; don't write HTML from scratch
- **CSS stays untouched**, only edit the body
- Content follows `writing.md`: data over adjectives, distinctive phrasing over industry clichés
- Avoid patterns listed in `references/anti-patterns.md`: emptiness, fabrication, mimicry, excess, source gaps, tone contamination
- **Before filling, read the quality bar for your document type** in `writing.md` section "Quality bars by document type". Structure is necessary but not sufficient: a resume bullet needs Action + Scope + Result + Business Outcome; an equity report needs variant perception + quantified catalysts; slides need assertion-evidence titles. Meeting the quality bar is as important as filling every placeholder.

### Do not generate

These are the most common AI document failures. Cross-reference `references/anti-patterns.md` for the full list.

- Do not leave placeholder text in the final document ("Lorem ipsum", "[Insert here]", "TBD")
- Do not invent metrics, financial data, or statistics; mark gaps with `[DATA NEEDED: description]`
- Do not use stock-image descriptions as image placeholders ("A diverse team collaborating in a modern office")
- Do not pad content to fill template slots (a resume with 3 real projects does not need 5 fabricated ones)
- Do not write a paragraph that merely restates its own heading in sentence form

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

## Step 4.1 · Per-page density target (multi-page templates only)

适用：slides-weasy / long-doc / portfolio / equity-report / changelog。不适用 resume / one-pager / letter（这些有独立的长度合约）。

正文页填充率目标 60-80%。封面 / 目录 / 末尾署名页豁免。这条规则解决的是 AI 生成多页文档时最常见的 draft 缺陷：把内容拆得太散，结果几页都填不满。

### Items-per-page contract

| Template | Typical body page | Hard floor (merge if below) |
|---|---|---|
| slides-weasy | 1 assertion title + 3-5 supporting items, or 1 chart + 2-3 callouts | <3 items and no chart → merge into adjacent slide |
| long-doc | 1 chapter heading + 2-4 paragraphs + at most 1 figure | Chapter renders to <40% page → merge into neighbor chapter |
| portfolio | 1 project header + 1 hero image + 3-5 outcome bullets | No image and <3 outcomes → merge with adjacent project |
| equity-report | 1 section + 1 table/chart + supporting prose | Only a 2-row table on the page → combine sections |
| changelog | 1 version block + 4-8 entries | Version has <4 entries → place on the same page as the prior version |

### Sparse-page merge rule

Before finalizing, scan the draft. Any body page that would render under 50% full → apply one of, in order:

1. Merge upward into the previous section.
2. Merge downward into the next section.
3. Promote a list to a small diagram or table that earns the space.
4. Pin a `.co` callout to bottom (slides-weasy only). Whitespace above a pinned callout is intentional, not sparse.

Forbidden ways to "fill" a sparse page: padding with filler prose, repeating the heading as a sentence, inventing statistics, restating the prior page in different words. If the merge options don't apply, the page itself shouldn't exist.

### Last-page exemption

The last body page is allowed to run 40-60% fill. Forcing balance on the last page usually means padding. The colophon / closing slide may have any fill level.

### Verify after build

```bash
python3 scripts/build.py --check-density   # flags >25% (WARN) / >50% (SPARSE) trailing whitespace
```

If a body page (not cover, not last page) gets a SPARSE warning, treat it as a draft defect and re-author with the merge rule.

## Step 4.5 · Auto-select output format

Do not ask the user which format to export. Decide from context:

| Signal | Output | Why |
|---|---|---|
| Any document request | HTML + PDF | PDF is the default deliverable, HTML is the source |
| Slides / PPT / deck | HTML + PDF + PPTX | Presentations need a projectable format |
| "分享" / "发朋友圈" / "share" / "post" / "preview" | + PNG | Social platforms and messaging need images |
| "嵌入" / "插图" / "embed in another doc" | PNG only | Used as material inside other documents |
| User explicitly says a format | Follow the user | Explicit request overrides auto-selection |

PDF always ships for document templates. Landing pages ship as a ready-to-serve static HTML file. PPTX follows slides. PNG follows sharing context. The user should never need to think about formats.

## Step 5 · Build & verify

```bash
python3 scripts/build.py --verify           # build all templates + page count + font check + slides
python3 scripts/build.py --verify resume-en # single target full verification
python3 scripts/build.py landing-page        # screen-first static HTML template check
python3 scripts/build.py --verify slides    # single slide deck verification
python3 scripts/build.py --check-placeholders path/to/filled.html
python3 scripts/build.py --check-resume-balance path/to/resume.pdf
python3 scripts/build.py --check-density              # page whitespace scanner (skips cover)
python3 scripts/build.py --check            # CSS rule violations only (fast, no build)
python3 scripts/build_metadata.py --check   # Codex plugin mirror + marketplace drift check
```

> **Screen verify**: `--check-density` is a print gate. For screen output (landing or docs pages) instead screenshot the rendered page at 375px and 1280px in every locale and scan for line widows before shipping. See `references/design.md` Section 11 «Responsive screenshot verification».

Source templates intentionally keep `{{...}}` fields. Run placeholder checks on completed documents, not on the template library.

Visual anomalies (tag double rectangle, font fallback, page break issues) -> `production.md` Part 4.

### Maintainer-mode checks

Use these only when maintaining this repository or release package, not for ordinary document generation.

- If marketplace metadata, generated plugin mirrors, version selection, or install paths change, run `python3 scripts/build_metadata.py --check`; for Codex install behavior, also smoke with an isolated `CODEX_HOME=/tmp/...` using `codex plugin marketplace add <path>`, `codex plugin add kami@kami`, and `codex plugin list`.
- If `SKILL.md`, templates, scripts, references, or other package inputs change and the behavior ships through the skill package, run `bash scripts/package-skill.sh` and inspect `dist/kami.zip` before handoff.
- If a GitHub release asset is refreshed, download the uploaded `kami.zip` and compare ZIP entry names plus per-entry SHA-256 digests against local `dist/kami.zip`; page text, file size, and the container hash are not enough.

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

**Korean (best-effort)**
- Dedicated `-ko` templates use Source Han Serif K Regular / Medium, with the real OTF family name `Source Han Serif KR` kept in every fallback stack
- Fallback: Noto Serif KR / Apple SD Gothic Neo / AppleMyungjo / Charter / Georgia
- The OTFs are OFL-licensed and tracked for local preview / CDN fallback, but excluded from Claude Desktop skill ZIPs to keep the package small

**English**
- Single serif: Charter (system-bundled, macOS/iOS), used for both headlines and body
- No separate sans: `--sans: var(--serif)`, one font per page
- Fallback: Georgia (cross-platform) / Palatino / Times New Roman

Font files next to HTML with relative `@font-face` paths is the most stable setup. `scripts/package-skill.sh` excludes large CJK font files from the Claude Desktop ZIP, so the uploaded package stays under the 6MB package ceiling. Always upload that `package-skill.sh` output, never a hand-zipped checkout (the tracked CJK fonts make it too large and Claude Desktop rejects the upload).

**Font auto-recovery (Claude Desktop)**

Before building Chinese or Korean documents, ensure fonts are present. The script tries multiple CDN sources with retry and size validation:

```bash
bash scripts/ensure-fonts.sh
```

It downloads to the XDG user font dir (`${XDG_DATA_HOME:-~/.local/share}/fonts/kami`, override with `KAMI_FONT_DIR`), **not** into the skill's `assets/fonts` -- that keeps the installed skill small so Claude Desktop never trips its size limit. fontconfig scans that dir by default, so WeasyPrint finds `TsangerJinKai02` and `Source Han Serif K` there; online renders fall back to the jsDelivr `@font-face` URL. Run once before building. If all sources fail, the script prints per-language alternatives.

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
