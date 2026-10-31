# Content Strategy

How to write, not how to lay out. Good typography with bad content is just "polished mediocrity". This document covers the writing principles for both Chinese and English output. Shared rules come first; language-specific details are called out where they matter.

---

## Core principles (all documents)

### 1. Data over adjectives

- Avoid: "Delivered significant business growth"
- Use: write the specific numbers and deltas

Use verified numbers for quantitative claims. Explain mechanisms and judgments with concrete facts or examples; do not add a number just to satisfy a quota.

### 2. Judgment over execution

Junior writes "what they did". Mid writes "how they did it". **Senior writes "why they made that call, and what they predicted correctly"**.

- Avoid: "Led the platform build-out"
- Use: write what judgment you made and how it was proven right

### 3. Distinctive phrasing over industry clichés

- Avoid: "Embrace the AI era, pioneer digital transformation paradigms"
- Use: say it in your own words, skip the industry vocabulary

Use words that fit the author and the subject. Keep an established voice; do not invent a slogan to make a paragraph seem distinctive.

### 4. Honest boundaries

- If you didn't do it, don't claim it
- If you don't know the exact number, don't invent one. Write a vague but honest magnitude
- Attribute collaborators

### 5. Sources before phrasing

For companies, products, people, launch dates, versions, funding, financials, market data, or technical specs, verify the source before writing. Priority: user-provided source material > official pages / docs / press releases > filings / app stores / repo releases > credible media.

- Do not write "latest", "new", version numbers, or market figures before checking them
- If sources conflict, list the conflict and ask the user instead of choosing one
- If only the magnitude is known, write the magnitude instead of false precision
- A number you compute from supplied figures (a growth rate, a share, an "about 60% faster") stays next to its inputs ("23 to 9 minutes, about 61% less") or is marked as derived (推算 / derived) where it appears, in captions and tables too. Never round it into a standalone headline metric the source did not state

### 6. Materials serve recognition

Branded documents should first make the subject recognizable, then use decoration and atmosphere with restraint.

- Company / product / project docs should confirm logo, product image, UI screenshot, and brand color before layout
- If a key material is missing, mark the gap or ask the user. Do not fill the page with unrelated imagery
- Physical products prefer official product images; digital products prefer real UI screenshots
- If brand color is unknown, keep kami ink-blue rather than inventing a new color
- **Third-party figures**: when redrawing a paper figure, patent illustration, or official architecture diagram for visual consistency, mark the redraw as `Schematic redrawn` /「示意重绘」in the caption. Do not style a redrawn version to look like the original screenshot. If the figure carries primary evidentiary value (patent, official spec), embed the original with attribution rather than redrawing it

### 7. Term annotation half-life

术语首次出现时注解。注解在 8-10 页或 10 张 slide 后过期。超出半衰期再次使用时，用更短的提示重标，不要假设读者还记得。Cap、卡片副标题、章节摘要这类快速阅读位置尤其严格。

- 首次: "LTV (Lifetime Value, 用户在流失前贡献的总收入)"
- 超过半衰期后重现: "LTV (用户终身价值)"
- 半衰期内不要重标，读起来像在解释已知概念
- 适用于 slides、long-doc、equity report 等超过 8 页的文档。Resume 和 one-pager 太短，不触发

### 8. English term density in CJK text

中日文正文里，单句未注解英文术语 ≤ 1 个。超过就拆句或加 inline 注解。注解优先用动作词 (warmup → 升起来, rollout → 跑一遍生成, credit assignment → 把功劳分到具体哪一步)，不用概念词 (预热, 轨迹生成, 信用分配)。动作词描述发生了什么，概念词只是换个外壳。

---

## Per-document strategies

### One-Pager

**Single purpose**: the reader grasps the point in 30 seconds.

**Structure**:
1. **Headline** (serif display) + one-line subtitle (sans body)
2. **Metrics** - 3-4 cards, numbers first
3. **Core argument** (1-2 paragraphs)
4. **Key evidence / roadmap** (3-5 short bullets)
5. **Next step / contact** (footer)

**Rules**:
- Length target: English 200-350 words; Chinese 400-600 characters
- All section headlines should work as a standalone outline - reading just the headlines should deliver the gist
- Data must fill 30%+ of the body
- Company / product one-pagers must confirm logo, core screenshot or product image, and source for key metrics
- No opening ceremony ("In recent years, as technology has rapidly evolved...")

### Long Document

**Content contract**: use the template's existing cover, contents, executive summary,
body, and optional appendix slots. The executive summary fits on one page with 3-5
takeaways; each body chapter stands alone as an essay.

**Rules**:
- Every chapter opens with a "claim paragraph" (2-3 sentences summarizing the argument)
- Break long paragraphs with real evidence, an attributed quote, or a useful figure when one exists. Otherwise edit the prose or add a descriptive subhead; do not invent a component for rhythm alone
- Highlight key data / conclusions with `<span class="hl">`
- Chapters with external facts must preserve source cues so readers can distinguish fact, judgment, and inference
- Give a major section its own opener only when it improves navigation. Do not insert a ceremonial blank page

### Letter

**Content contract**: use the template's existing letterhead, date, salutation,
body, sign-off, signature, and optional enclosure slots. Keep the body to 3-5
paragraphs.

**Rules**:
- Minimal - no decorative elements
- Body prefers serif (editorial feel)
- Slightly larger type (11-12pt body) - this will be read, not scanned
- Paragraph spacing ≥ 10pt
- Signature uses serif 500

**Language notes**:
- Chinese sign-offs can use "此致 / 敬礼", "顺颂商祺", or a context-appropriate formal closing
- English sign-offs should stay simple: "Best regards," / "Sincerely," / "Warm regards,"

### Portfolio

**Structure**:
1. **Cover** (name + one-line positioning + a two or three line introduction + contact)
2. **Per-project 1-2 pages**:
 - Project title + type tag + date range
 - One-line description
 - 2-3 hero images (if applicable)
 - Role + challenge + outcome
3. **Selected works list** (additional projects as a short list)
4. **Contact** (return to contact details)

The introduction lives on the cover. Experience, skills and tools are the resume's job, so the template's About page ships commented out: uncomment it only when the user supplies enough experience, focus, skills and project index to fill a whole page. An About page that would render under half full is deleted, not padded.

**Rules**:
- Visuals first, text supports
- Support each project outcome with verified metrics or concrete qualitative evidence
- Final product screenshots / real photos > design mockups > code screenshots
- If project images are missing, mark the gap. Do not fill the layout with unrelated imagery
- Don't list every tech stack - a mono tag row is enough

### Proposal (long-doc variant)

A proposal is a long-doc whose body argues for a specific commercial engagement. Three voice rules are unique to this variant:

#### 1. Work-volume frame vs attention frame

A pricing page can be written two ways. The work-volume frame lists deliverables, hours, or session counts; readers price-anchor against market hourly rates. The attention frame describes a senior advisor's judgment allocated across a few directions; readers price-anchor against the value of the directions. Pick one frame and stay consistent.

| Dimension | Work-volume frame | Attention frame |
|---|---|---|
| What is sold | Execution of N items | Allocation of judgment |
| Pricing basis | Hours / deliverables | Total engagement |
| Workload density | Fixed commitment | Flexes with the buyer's cadence |
| Reader posture | Procurement | Hiring an advisor |
| Signals | "I can do these tasks" | "I bet on these directions" |
| Fits | Outsourced delivery | Senior advisory work |

The work-volume frame backfires for advisor pricing: the more itemized the breakdown, the more the reader divides total fee by hours and decides "this is a vendor, can it cut corners?" Avoid these patterns when writing in the attention frame:

- Rigid monthly volume: `每月 N 份 / 节 / 篇`. Replace with "by milestone" or "as the cadence requires".
- Exhaustive coverage: `每个发布节点全程参与`. Replace with "deep involvement at major milestones".
- Specific session counts: `20 节课程`. Replace with "depth of content" anchors and let scheduling adjust.
- "Full-X" totalizers: `全方位 / 全链路 / 全程`. Replace with "key X" or "core X".

#### 2. With-price vs without-price modes

Whether to print the number depends on the reader. Use these defaults and switch by audience:

| Audience | Mode | Reasoning |
|---|---|---|
| Operating founder, direct buyer | **With price** | Direct decision-makers want the number to evaluate fit |
| Intermediary, business contact | **Without price** | Leave room for the intermediary's own commercial layer |
| Investor, board reader | **Without price** | Strategy first, money second; a number breaks the register |

The without-price variant drops the large-figure hero and keeps the value anchors. Rename the chapter from "合作方案与投入" (Plan & investment) to "合作方向与价值" (Directions & value) so the title matches the content.

#### 3. Kickoff-period emphasis pattern

Twelve-month timelines fail when every month is described at equal weight: the reader cannot tell what is urgent. Surface the first 60 days as a separate beat ahead of the timeline table:

- One paragraph on time scarcity ("this window closes; recovering it later costs several times more").
- One paragraph per month: bold the date, name the module, list 2-3 concrete actions, state the outcome.
- Then the full month-by-month table, which reads as detail rather than the story.

The pattern is "story before grid": the reader leaves the timeline section knowing one thing (the kickoff is dense), not twelve things (every month).

### Resume

The most constrained document type in kami.

**Hard constraints**:
- Strictly 2 A4 pages
- Every project follows three-part: Role / Actions / Impact
- 5 core skills, each with at least one brand-color emphasis
- Team size, tech stack, narrative voice must stay consistent throughout

**Key sections**:
- Header + 4 metric cards
- Summary (~50 English words or ~80 Chinese characters)
- Timeline (3 steps - long-range evolution signal)
- 3-5 core projects
- Public work / impact (optional)
- 5 core skills
- Education

**Metric card selection rule**:
- 1 card on **time** (years, consistency)
- 1 card on **scale** (team, users, projects, or other quantifiable scope)
- 2 cards on **results** (quantifiable external proof)

---

## Quality bars by document type

Structure is necessary but not sufficient. These bars define what separates compelling content from template-filling.

### Resume

**Impact formula**: Action + Honest Scope + Observable Result. Explain the business outcome when relevant; use verified metrics when available and concrete qualitative evidence otherwise.

| Avoid | Use |
|---|---|
| "Worked on backend services" | "Redesigned order pipeline serving 2M daily txns, cut p99 latency from 800ms to 120ms, saved $340K/yr in infra costs" |
| "Led a team to deliver features" | "Led 5-engineer squad that shipped real-time collaboration (3-month timeline), adopted by 40% of enterprise accounts within one quarter" |
| "Improved performance" | "Reduced cold-start time 62% across 14 Lambda functions by replacing runtime init with pre-baked layers, cutting median API response from 1.2s to 0.45s" |

**Rules**:
1. Start every bullet with a strong past-tense verb (designed, led, reduced, migrated). Never "Responsible for" or "Helped with"
2. Use verified numbers when they explain the result or scope. If no metric is available, state the observable outcome without inventing one
3. Connect technical work to business outcomes: revenue, cost, reliability, user retention, time-to-market
4. Include before/after pairs when possible: "from X to Y" is more credible than "improved by Z%"
5. Match the source’s precision: keep a measured value exact and label an estimate as an estimate
6. Distinguish ownership: "owned" vs "contributed to" vs "coordinated". Inflating scope is the fastest way to lose credibility in an interview

**Senior vs junior**: junior resumes show execution ("built X"). Senior resumes show judgment ("evaluated 3 approaches, chose Y because of tradeoff Z") and multiplier effect ("mentored 4 engineers, 2 promoted within 12 months")

### Portfolio

**Core rule**: open every case study with the problem and its stakes, not with your role or the project name.

**Density bar**: each project page reads as a complete case study. At target font size, a body page that renders under half-full is a draft defect, not a design choice. Merge upward into the previous project or downward into the next; do not pad with filler prose. See «Page density» below for the items-per-page contract.

| Avoid | Use |
|---|---|
| "I redesigned the dashboard" | "Enterprise users abandoned the analytics dashboard at 73% rate within the first session. I led the redesign that cut abandonment to 31%." |
| "The client was happy" | "Task completion time dropped from 4.2 min to 1.8 min. NPS increased from 22 to 51 over 3 months." |

**Rules**:
1. Show 2-3 decision points where you chose between alternatives. Explain the tradeoff, not just the winner
2. Support outcomes with verified metrics or concrete qualitative evidence, and explain the business context when relevant. Include user quotes only when supplied or sourced
3. State your exact role and scope: "I designed" vs "I led" vs "I contributed to" are very different signals
4. 3-5 deep case studies beats 12 shallow ones. Depth is credibility
5. Close the loop with an observable result for each problem; state unresolved limits when the evidence does not establish a resolution
6. Prefer final product screenshots over mockups. If product images are missing, mark the gap rather than filling with unrelated imagery

### Slides

**Core rule**: every slide title should be a full declarative sentence (an assertion), not a topic label. The body provides one piece of evidence supporting the assertion.

**Density bar**: each body slide carries one assertion + 3-5 supporting items (or 1 chart + 2-3 callouts). Slides with fewer than 3 items and no chart must merge into an adjacent slide. A pinned `.co` callout is valid only when it adds a real relationship, constraint, or conclusion; never use it to fill trailing whitespace. See «Page density» below.

| Avoid | Use |
|---|---|
| Title: "Q3 Performance" | Title: "Q3 revenue grew 23% because enterprise deals closed 2x faster" |
| 7 bullet fragments per slide | One chart proving the assertion |
| "Key Takeaways" slide with 8 points | One clear ask or recommendation |

**Rules**:
1. 20-40 words per slide maximum. If a slide has more than 40 words, split it or convert text to a visual
2. 5 items per list maximum (working memory capacity)
3. Three-act arc: setup establishes stakes, evidence builds the case, and resolution delivers the payoff. Act lengths scale with deck size; reading the slide titles in sequence should tell the full argument
4. Include a "so what" moment every 3-4 slides to re-anchor the audience
5. End with one clear ask, not a bullet list of "key points"

**Eyebrow vs title non-duplication**: the eyebrow is a stable, cross-slide section label ("Growth / Q3 Results"). The title is a page-unique declarative claim ("Revenue grew 23% because enterprise deals closed 2x faster"). They must never say the same thing in different words. If removing the eyebrow would make the title ambiguous, the title is too weak. If reading the title makes the eyebrow redundant, the eyebrow is a topic label masquerading as context.

**Deck rhythm (>=12 slides)**: the layout-type sequence includes a `chapter_slide`
(ink-blue full-bleed divider) every 4-6 slides, no run exceeds 5 consecutive
`content_slides`, and the deck includes at least one `quote_slide` or
`metrics_slide` to vary density. Monotony is a structure failure, not a content one.

**Term consistency self-check**: after drafting, list every domain term that appears 3 or more times (product names, feature names, roles, metrics). Confirm there is exactly one spelling and capitalization for each. Inconsistent casing ("LLM" vs "llm" vs "large language model") signals an unreviewed draft.

**Caption quality bar**: every cap must answer "why does this slide matter": give a tradeoff, an applicability boundary, a next step, or the insight the diagram alone cannot say. Two failure modes both waste the cap's attention slot: restating the slide title in different words (anti-pattern #30), or restating the flow diagram in prose (anti-pattern #27). If removing the cap would make the slide weaker, it is doing its job; if removing it changes nothing, rewrite it.

**Term annotation half-life**: decks 超过 10 张时，跨越 10-slide 窗口再出现的术语需重标。见 core principle #7。

### Equity Report

**Core rule**: lead with the variant perception (what you see that the market doesn't) and tie every thesis driver to a measurable financial impact.

**Density bar**: a body page with only a 2-row table and a sentence is too thin. Each page should carry one section + one table/chart + supporting prose. Combine sections rather than leaving a page half-empty. See «Page density» below.

| Avoid | Use |
|---|---|
| "Strong management team" | "Management delivered 23% revenue CAGR over 5 years while keeping debt-to-equity below 0.4" |
| "Massive opportunity" | "We estimate 25% upside to $X based on DCF with 12% WACC and 3% terminal growth" |
| Vague "risks include competition" | "BYD's 35% unit cost advantage in the $20-30K segment threatens 15% of addressable volume by 2027" |

**Rules**:
1. Investment thesis on page 1, above the fold. Rating + price target (if applicable) + 3-5 bullet thesis drivers
2. Every claim backed by a number or a source. No unquantified superlatives
3. At least two valuation methods with sensitivity ranges. Single-method valuation is amateur
4. Catalysts must have dates and expected magnitude: "Robotaxi launch in Dallas, June 2025, adding estimated $X to revenue run-rate by Q4"
5. Competitive positioning with market share numbers, not narrative: "23% share of the $45B market, up from 18% in 2022"
6. Risk factors quantified and connected to the financial model, not generic disclaimers
7. Professional tone: "we estimate" / "our base case" / "we see upside to". Never "this stock will moon" or "buy the dip"
8. Acknowledge counter-arguments before dismissing them. One-sided analysis signals bias, not conviction
9. Separate GAAP from non-GAAP clearly. Flag one-time items (warranty reserves, tax benefits, restructuring charges)

### Long Document

**Core rule**: each chapter's claim paragraph must survive the "so what?" test. If the reader asks "why should I care?", the first paragraph must have the answer.

**Density bar**: each body page carries 1 chapter heading + 2-4 paragraphs + at most 1 figure. A chapter that fits in under 40% of a page must merge into the next chapter rather than claiming its own page. Trailing whitespace at the bottom of a body page is a draft defect. See «Page density» below.

After converting from Markdown, remove or convert thematic breaks, bold markers,
and inline-code backticks before delivery, then run `python3 scripts/build.py
--check-markdown path/to/filled.pdf` on the rendered PDF.

**Rules**:
1. Evidence density: support factual claims with sources, examples, or verified measurements. Do not add numbers to paragraphs that explain a mechanism or judgment
2. When dense prose needs relief, use an existing attributed quote, evidence figure, descriptive subhead, or paragraph edit. Do not manufacture a callout on a fixed cadence
3. Counter-arguments addressed before they become reader objections. If you can predict the pushback, address it proactively
4. Source cues preserved inline: "(Gartner, 2025)" or "according to the company's 10-K" so readers can distinguish fact from inference
5. Each chapter should stand alone as a mini-essay with its own arc: claim -> evidence -> conclusion

### One-Pager

**Core rule**: the reader grasps the point in 30 seconds. Every element that doesn't serve 30-second comprehension is bloat.

**Rules**:
1. Metrics are the headline, not supporting evidence. If your 4 metric cards don't tell the story, the metrics are wrong
2. The lead paragraph must contain the single sharpest claim, not context-setting
3. Bullet points should be evidence, not restated arguments. Each bullet: fact + number + "so what"
4. Footer is for contact and classification, not for squeezing in one more argument

### Letter

**Core rule**: first paragraph states purpose in one sentence. Last paragraph states the specific ask or next step. Everything in between is evidence.

**Rules**:
1. One point per middle paragraph, each with its own evidence
2. Tone calibration per use case: resignation (grateful + clear), recommendation (specific + enthusiastic), proposal (value-first + concrete), personal statement (authentic + structured)
3. Sign-off matches formality: "Sincerely" for formal, "Best regards" for professional-warm, "Warm regards" for personal
4. A letter fits on one page. If it needs two pages, it is a memo or a proposal

### Changelog

**Core rule**: one sentence per change, verb-led, user-facing language. If the user cannot understand the change from the sentence alone, rewrite it.

**Density bar**: each version block carries 4-8 entries. A version with fewer than 4 entries should sit on the same page as the prior version rather than triggering a near-empty page. See «Page density» below.

| Avoid | Use |
|---|---|
| "Refactored internal state management module" | "Fix crash when switching tabs rapidly on iPad" |
| "Updated dependencies" | "Upgrade OpenSSL to 3.2.1 (patches CVE-2026-1234)" |

**Rules**:
1. Breaking changes always first, with migration path ("Replace `config.old` with `config.new`; run `migrate.sh` to convert")
2. Group changes by user-visible outcome. Item counts do not determine release boundaries
3. Group by user impact (Breaking / Features / Fixes), not by component or file
4. No internal jargon. "Fix memory leak in image decoder" is clear. "Fix retain cycle in UIImageDecoderBridge" is not

---

## Page density (multi-page documents)

Applies to slides-weasy, long-doc, portfolio, equity-report, and changelog. Resume, one-pager, and letter have their own length contracts. The most common draft defect in a generated multi-page document is content split too thin, so several pages never fill.

Body pages target 60-80% fill; cover, table of contents, and closing colophon are exempt. The last body page may close at 40-60%; forcing balance there usually means padding.

| Template | Typical body page | Floor (merge if below) |
|---|---|---|
| slides-weasy | 1 assertion title + 3-5 supporting items, or 1 chart + 2-3 callouts | Under 3 items and no chart: merge into an adjacent slide |
| long-doc | 1 chapter heading + 2-4 paragraphs + at most 1 figure | Chapter renders under 40% of a page: merge into a neighbor |
| portfolio | 1 project header + 1 hero image + 3-5 outcome bullets | No image and under 3 outcomes: merge with an adjacent project |
| equity-report | 1 section + 1 table or chart + supporting prose | Only a 2-row table on the page: combine sections |
| changelog | 1 version block + 4-8 entries | Under 4 entries: share the page with the prior version |

A body page that renders under 50% full gets one of these, in order: merge upward into the previous section; merge downward into the next; remove the page and fold its one useful assertion or proof into a neighbor; convert existing information to a small table or diagram only when that form is clearer even without the density problem. Never fill a sparse page with filler prose, a heading restated as a sentence, invented statistics, the prior page reworded, or a callout, chart, icon, or image whose only job is to occupy space. If no merge applies, the page should not exist.

`--check-density` (inside `--deliver`) reports trailing whitespace per page; a body page flagged there is a draft defect to re-author with the merge rule above.

## Diagrams and infographics

Words inside a diagram or infographic (title, eyebrow, node label, summary line) follow tighter rules than body prose. Readers process them in seconds, so rhetorical flourish reads as noise. This applies whether the figure is a Kami SVG embedded in a long-doc or an external image rendered elsewhere.

### Avoid colloquial slogan-words

| Avoid | Why it fails |
|---|---|
| 白搭 / 立住 / 才顺 / 回炉 / 闸 | Slang verbs; rewrite as a literal claim |
| 必看 / 一图看懂 / 彻底搞懂 | Bait phrasing; state the figure's actual content |
| 爆款 / 神器 | Marketing tone in an engineering figure |
| 飞轮 / 闭环 (unless audience is fluent) | Use 数据循环 / 持续改进 / 四类入口 |

### Avoid product-specific judgments that date fast

Pinning a category to a current product name ages the figure within a quarter, because tools evolve faster than diagrams ship. Frame the paradigm and let the reader map products themselves: prefer 「上一代工具范式 / 新一代执行范式」over 「Cursor 是副驾驶 / Claude Code 是自动驾驶」.

### Slogan to neutral rewrites

| Before (slogan) | After (neutral) |
|---|---|
| 没对完，不算完成 | 交付前，过三遍 |
| 任一不过则回炉 | 任一步不通过，回到修改 |
| 交付前最后一道闸 | 交付前最后检查 |
| 订阅前先把这些习惯立住 | 订阅前的基础检查 |

The principle: a diagram caption is engineering documentation, not marketing copy. Restraint reads as competence; bravado reads as filler.

---

## Coupling rules (layout × content)

### Emphasis rhythm

Across any document:
- ≤ 2 emphasized items per line
- Emphasis must be a **quantifiable number** or a **distinctive phrase**
- Do not emphasize adjectives
- In prose-heavy sections, one emphasis per 80-150 words is a healthy default. Short sections do not need a forced highlight

### Number formatting

| Use | Avoid |
|---|---|
| 5,000+ | 5000+ (missing thousands separator) |
| 5,000+ | 5，000+ (full-width comma in a metric) |
| 90% | 90 % (space before percent) |
| ~$10M | $9,876,543 (false precision reads fake) |
| 2026.04 | 2026年4月 / April 2026 (when horizontal space is tight) |
| -> | → |
| n/a (EN), 不适用 (CN), 해당 없음 (KO) in an empty table cell | an em dash (U+2014); the Markdown residue check rejects it in every document |

### Language-specific punctuation

Chinese documents:
- Prefer `「」` for quoted prose, not straight double quotes
- Keep numbers, commas, percent signs, and dates half-width in metric-heavy areas
- Add spaces between Chinese text and Latin product names when it improves readability
- Short copy (UI hints, landing benefit items, changelog entries) joins clauses with commas; a period appears only at the end of the item, or not at all
- Never use `；` in user-visible strings; split into two sentences or rejoin with a comma. Self-check: grep short-copy blocks for `；` and mid-item `。`

English documents:
- Use straight quotes in source text unless the document already has a typographic quote convention
- Prefer compact date forms (`2026.04`) in dense layouts and natural dates (`April 2026`) in prose

### Emphasis is not bold

Use `color: var(--brand)` alone - don't also add `font-weight: bold`. Bold breaks the single-weight design language.

---

## Localization pass (multilingual surfaces)

Literal alignment is the failure mode; meaning alignment is the goal. Every time a multilingual page or document changes, finish with a native-reader pass per locale before shipping:

- **Read each locale straight through as a native reader**, not against the source text. Flag every sentence that carries the source language's skeleton: word order, comparison patterns, and punctuation rhythm are all allowed to diverge from the source.
- **Rewrite, don't adjust.** A source-shaped sentence usually needs its structure rebuilt, not a word swapped. `Buying X is like buying A + B + C at once` may need to become a fresh comparison native speakers would actually say, at the cost of dropping the source's phrasing entirely.
- **Localize the expression, preserve the facts.** Rework puns and parallel phrasing only when needed for natural local speech. `One price, five tools` can become `一次购买，包含五款工具`, never `永久更新` unless lifetime updates are part of the source offer.
- **User-adopted phrasing wins.** If the maintainer has already approved a specific line in one locale, treat it as fixed and localize around it, not over it.
- **Report coverage and unresolved issues.** List the locales and surfaces checked. Keep already-natural sentences; a rewrite count is not evidence of quality.

---

## Pre-ship checklist

Run through before shipping every draft:

- [ ] Any jargon like "leverage / unlock / embrace / pioneer"? Cut.
- [ ] Any Chinese filler like "拥抱 / 打造 / 赋能 / 重构"? Rewrite in plain language.
- [ ] Does every paragraph's first sentence stand alone? If not, that paragraph has no claim.
- [ ] Are all numbers verifiable? If asked "where did this come from", can you answer?
- [ ] Are current facts, versions, launch dates, funding, financials, and specs backed by reliable sources?
- [ ] Does every branded document have logo, product image, or UI screenshot coverage? Are missing materials clearly marked?
- [ ] Does the wording fit the author and subject, without stock phrases or forced slogans?
- [ ] Every emphasized (brand-colored) span is either a number or a distinctive phrase? If not, remove the emphasis.
- [ ] Paragraph lengths even? No paragraph over 5 lines?
- [ ] Number format consistent (commas, percent signs, arrows)?
- [ ] Chinese punctuation and Chinese / Latin spacing consistent where applicable?
- [ ] Page count within the document's constraint (resume 2, one-pager 1, letter 1)?
- [ ] Any AI writing cliches? CN: 本质是 / 这意味着 / 值得注意的是 / 不仅...而且 / 破折号堆砌。EN: em dashes, "It's worth noting", "This means that". See anti-patterns #28.
- [ ] Multi-page docs (>8 pages / >10 slides): domain terms re-annotated beyond the half-life window? See principle #7.
- [ ] Multilingual surfaces: native-reader localization pass done per locale, rewrite counts reported?

---

## Landing Page

A landing page is not a brochure. It is a conversion surface. Every element either builds trust or wastes attention.

### Global: no italic on landing pages either

Invariant #10 bans italic in print templates, and landing pages follow it too: gallery captions, feature subtitles and the footer ethos stay upright, separated by size, colour and position. Italic marks only a font face, syntax tokens or the author's own emphasis.

### Hero rules

- **Positioning comes before feature count.** Name the real product category in the first viewport. If the product has grown beyond its old anchor, rewrite the category instead of adding more feature bullets under the old one.
- **Tagline is one sentence, not a paragraph.** State what the product does in words the reader uses.
- **Tokens (key facts) are scannable proof.** Price, platform, refund policy, compatibility. No adjectives. `$9 lifetime` beats `Affordable pricing for everyone`.
- **CTA pair: secondary (try) + primary (buy).** Ghost button for low-commitment action, filled button for revenue action. Never three buttons.

### Section lede rules

- **A section lede is one plain sentence.** No bold, no brand color, no second qualifying line under it. If a comparison or caveat keeps fighting to get in, it belongs in the FAQ or the pricing terms, not the lede.
- **Competitor names stay out of the hero and ledes.** They live in the FAQ comparison answer and the meta description; naming rivals in the opening viewport frames the product by what it is not.

### Gallery rules

- **Show, don't describe.** Real screenshots replace feature paragraphs. Each panel is one shipped tool, one workflow, or one state users can actually reach.
- **Technical products can show the workflow itself.** A terminal transcript, command draft, or error recovery panel is a product screenshot when it shows the actual review/confirm boundary.
- **Captions add information.** Name what the screenshot shows or explain a useful detail. Omit a caption that repeats the heading; use imagery only when it helps the reader understand.
- **3-6 panels maximum.** More than 6 and the auto-rotate becomes noise. Users remember 4.

### Features list rules

- **Name the feature directly.** Add a subtitle only when it supplies useful context. Do not require a metaphor.
- **Description answers "so what?"** Not what it does, but why the user should care. One paragraph, 2-3 sentences.
- **Mechanics fold into the FAQ.** A feature block sells the outcome in a few quiet points; how the product behaves (activation, boundaries, safety rules, edge cases) belongs in FAQ answers. A standalone "behaviors" section is documentation leaking into the pitch, and it usually costs a full screen of scroll.

### Principles rules

- **Title is the commitment, description is the proof.** "Nothing leaves your Mac" is the title. How you enforce it is the description.
- **4-6 principles.** More than 6 dilutes the message. If you have 8, two are redundant.

### Social proof rules (testimonial content)

Layout lives in `references/design.md` «Testimonial wall»; these rules govern what goes in.

- **The collapsed view sells the current product.** Every quote visible before expansion must praise the product form being sold on this page. Praise for a sibling product line (a CLI when the page sells the GUI, an old major version) confuses buyers into "wait, which product is this"; it may appear after expansion, clearly attributed, or not at all.
- **Order by credibility, not recency.** Recognizable names first, then high-engagement posts, then well-written quotes from unknowns. A famous person's lukewarm quote beats a stranger's rave.
- **Quotes with expired facts get replaced or annotated.** An old early-bird price or a stale version number inside a quote reads as current fact to a new visitor. Swap the quote, trim the sentence, or add a short neutral note; never run it as-is.
- **Collapsed count protects the purchase flow.** Roughly 9-12 quotes before the fold; the wall must not push pricing below comfortable reach. More quotes belong behind the expand control, all at once, no pagination.
- **External source links dress like quotes.** A "see more on X/search" entry is a card in the same visual language at the end of the wall, one line of copy, not a foreign button floating after it.

### Pricing rules

- **Benefits are the headline, not the price.** The buyer should leave the section feeling "this is worth it", not "this costs money". Lead with 4-6 benefit points: one line each, similar lengths, no wrapping, rendered as a plain borderless list. The price supports the benefits, never the other way around.
- **State the price once, at medium weight.** One factual line (`$N · One-time purchase` shape), set in a readable but non-headline size. A giant price number turns the section into a price tag and invites "why so expensive" instead of "what do I get". Emphasis comes from placement (centered, own block, generous whitespace), not font size.
- **The number appears at most twice on the page.** Once in the pricing section, at most once as a hero token. Every extra repetition of the price amplifies price sensitivity.
- **CTA buttons carry the action, never the price.** `Buy {{PRODUCT}}`, not `Buy for $19`. The buyer already saw the number; putting it on the button makes the click feel like a payment instead of a decision.
- **Keep the block quiet.** No border, shadow, or gradient on pricing. One restrained fill is enough when grouping is necessary; otherwise let typography and spacing carry it.
- **Compare honestly.** Name the competitors, show their subscription price with `<s>`, then your one-time price. No vague "other tools charge more".
- **Terms at the bottom.** Payment methods, refund policy, device limit. Factual, not promotional.

### FAQ rules

- **First question is the positioning question.** Before "is it free" or "how do I install", users want to know what category this product is in. Lead with the comparison: "How is this different from {{CLI_NAME}} / {{MAC_APP_NAME}} / {{COMMON_TOOL}}?" or "Who is this not for?". This single question removes the misframing that AI assistants and first-time visitors do most often.
- **Compare against the tool users already know.** Use named alternatives from the source material, not generic "other apps" language.
- **Lead with the question the user is actually thinking.** "Is it free?" before "What's the refund policy?".
- **Answers in 1-2 sentences.** A FAQ answer longer than 3 sentences belongs in the docs page, not here.
- **6-8 questions maximum.** Cover: positioning, free tier, comparison, permissions/privacy, data collection, purchase flow, licensing.
- **llms-full.txt mirrors the FAQ.** Whatever you answer here, restate in `landing-page-llms-full.txt.example` so AI assistants summarizing the product give the same answer the visitor reads on the page. Divergence between FAQ and llms-full.txt is the most common AI-misrecommendation source.

### Footer rules

- **Keep the footer useful.** Include the brand and relevant links or license information. Preserve an established tagline; do not invent a poetic closing line to fill the space.
- **Links are navigation, not decoration.** Only link to pages that exist. Dead links destroy trust faster than missing links.

---

## SEO / content-marketing articles

An article written to attract search traffic is a teaching document with the product as a worked example, not a brochure with paragraphs.

- **The reader must learn something they keep.** The article's spine is a transferable mechanism: how a subsystem works, why a class of problem happens, what trade-offs exist. Explain it with real commands, code, or an architecture diagram at teaching depth (see `references/diagrams.md` density tiers), so the reader leaves with knowledge that works without the product.
- **The product is a worked example, not the subject.** It enters after the mechanism is established, as "here is how one tool applies this", and the product name stays out of the title's subject position.
- **The deletion test.** Remove every product mention; the article must still stand as a useful piece. If nothing is left, it was an ad, and search engines and readers both treat it as one.
- **Conclusion gives both paths.** End with what the reader can do manually, then what the product automates. Respecting the manual path is what makes the recommendation credible.

---

## Writing references

- **Paul Graham's essays** - short, direct, judgmental. The gold standard for essayistic writing.
- **Stripe Press books** - print-grade typography paired with deep content. Where to learn the craft of the single sentence.
- **Minto's Pyramid Principle** - conclusion first, evidence below. The shape of every one-pager and exec summary.
- **Ben Horowitz's blog** - how to write technical and business judgment in prose ordinary people can read. The template for long-doc voice.

None are required, but reading any one of them will move the dial on both your writing and your judgment.
