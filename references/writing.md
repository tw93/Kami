# Content Strategy

How to write, not how to lay out. Good typography with bad content is just "polished mediocrity". This document covers the writing principles for both Chinese and English output. Shared rules come first; language-specific details are called out where they matter.

---

## Core principles (all documents)

### 1. Data over adjectives

- Avoid: "Delivered significant business growth"
- Use: write the specific numbers and deltas

Every sentence should survive the follow-up question "how much, specifically?". If you can't answer, don't write it.

### 2. Judgment over execution

Junior writes "what they did". Mid writes "how they did it". **Senior writes "why they made that call, and what they predicted correctly"**.

- Avoid: "Led the platform build-out"
- Use: write what judgment you made and how it was proven right

### 3. Distinctive phrasing over industry clichés

- Avoid: "Embrace the AI era, pioneer digital transformation paradigms"
- Use: say it in your own words, skip the industry vocabulary

**Distinctive phrasing is memorable**. A line you invented beats a line borrowed from an earnings call. It sounds like a person thinking, not a deck regurgitating.

### 4. Honest boundaries

- If you didn't do it, don't claim it
- If you don't know the exact number, don't invent one. Write a vague but honest magnitude
- Attribute collaborators

### 5. Sources before phrasing

For companies, products, people, launch dates, versions, funding, financials, market data, or technical specs, verify the source before writing. Priority: user-provided source material > official pages / docs / press releases > filings / app stores / repo releases > credible media.

- Do not write "latest", "new", version numbers, or market figures before checking them
- If sources conflict, list the conflict and ask the user instead of choosing one
- If only the magnitude is known, write the magnitude instead of false precision

### 6. Materials serve recognition

Branded documents should first make the subject recognizable, then use decoration and atmosphere with restraint.

- Company / product / project docs should confirm logo, product image, UI screenshot, and brand color before layout
- If a key material is missing, mark the gap or ask the user. Do not fill the page with unrelated imagery
- Physical products prefer official product images; digital products prefer real UI screenshots
- If brand color is unknown, keep kami ink-blue rather than inventing a new color

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

**Structure**:
1. **Cover** - big title + subtitle + author + date
2. **Contents** (auto-generated or hand-written TOC)
3. **Executive Summary** (≤ 1 page + 3-5 takeaways)
4. **Body** - chapters that each stand alone as an essay
5. **Appendix / references** (if applicable)

**Rules**:
- Every chapter opens with a "claim paragraph" (2-3 sentences summarizing the argument)
- After long paragraphs (>5 lines), intersperse callouts / quotes / figures to relieve eye fatigue
- Highlight key data / conclusions with `<span class="hl">`
- Chapters with external facts must preserve source cues so readers can distinguish fact, judgment, and inference
- Use "chapter breaks" (blank page + chapter number) between major sections

### Letter

**Structure**:
1. Letterhead (sender info, top right or centered)
2. Date (right-aligned)
3. Recipient salutation (left-aligned)
4. Body (3-5 paragraphs)
5. Sign-off ("Sincerely," / "Best regards,")
6. Signature (serif 500)
7. Enclosures (if any)

**Rules**:
- Minimal - no decorative elements
- Body prefers serif (editorial feel)
- Slightly larger type (11-12pt body) - this will be read, not scanned
- Paragraph spacing ≥ 10pt

**Common use cases**:
- Resignation / notice
- Recommendation letter
- Formal collaboration proposal
- Personal statement

**Language notes**:
- Chinese sign-offs can use "此致 / 敬礼", "顺颂商祺", or a context-appropriate formal closing
- English sign-offs should stay simple: "Best regards," / "Sincerely," / "Warm regards,"

### Portfolio

**Structure**:
1. **Cover** (name + one-line positioning + contact)
2. **About** (half-page introduction)
3. **Per-project 1-2 pages**:
 - Project title + type tag + date range
 - One-line description
 - 2-3 hero images (if applicable)
 - Role + challenge + outcome
4. **Selected works list** (additional projects as a short list)
5. **Contact** (return to contact details)

**Rules**:
- Visuals first, text supports
- Every project's outcome must be quantifiable
- Final product screenshots / real photos > design mockups > code screenshots
- If project images are missing, mark the gap. Do not fill the layout with unrelated imagery
- Don't list every tech stack - a mono tag row is enough

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

## Coupling rules (layout × content)

### Emphasis rhythm

Across any document:
- ≤ 2 emphasized items per line
- Emphasis must be a **quantifiable number** or a **distinctive phrase**
- Do not emphasize adjectives

### Number formatting

| Use | Avoid |
|---|---|
| 5,000+ | 5000+ (missing thousands separator) |
| 5,000+ | 5，000+ (full-width comma in a metric) |
| 90% | 90 % (space before percent) |
| ~$10M | $9,876,543 (false precision reads fake) |
| 2026.04 | 2026年4月 / April 2026 (when horizontal space is tight) |
| -> | → |

### Language-specific punctuation

Chinese documents:
- Prefer `「」` for quoted prose, not straight double quotes
- Keep numbers, commas, percent signs, and dates half-width in metric-heavy areas
- Add spaces between Chinese text and Latin product names when it improves readability

English documents:
- Use straight quotes in source text unless the document already has a typographic quote convention
- Prefer compact date forms (`2026.04`) in dense layouts and natural dates (`April 2026`) in prose

### Emphasis is not bold

Use `color: var(--brand)` alone - don't also add `font-weight: bold`. Bold breaks the single-weight design language.

---

## Pre-ship checklist

Run through before every draft:

- [ ] Any jargon like "leverage / unlock / embrace / pioneer"? Cut.
- [ ] Any Chinese filler like "拥抱 / 打造 / 赋能 / 重构"? Rewrite in plain language.
- [ ] Does every paragraph's first sentence stand alone? If not, that paragraph has no claim.
- [ ] Are all numbers verifiable? If asked "where did this come from", can you answer?
- [ ] Are current facts, versions, launch dates, funding, financials, and specs backed by reliable sources?
- [ ] Does every branded document have logo, product image, or UI screenshot coverage? Are missing materials clearly marked?
- [ ] At least one **distinctive phrase** (not industry boilerplate)?
- [ ] Every emphasized (brand-colored) span is either a number or a distinctive phrase? If not, remove the emphasis.
- [ ] Paragraph lengths even? No paragraph over 5 lines?
- [ ] Number format consistent (commas, percent signs, arrows)?
- [ ] Chinese punctuation and Chinese / Latin spacing consistent where applicable?
- [ ] Page count within the document's constraint (resume 2, one-pager 1, letter 1)?

---

## Writing references

- **Paul Graham's essays** - short, direct, judgmental. The gold standard for essayistic writing.
- **Stripe Press books** - print-grade typography paired with deep content. Where to learn the craft of the single sentence.
- **Minto's Pyramid Principle** - conclusion first, evidence below. The shape of every one-pager and exec summary.
- **Ben Horowitz's blog** - how to write technical and business judgment in prose ordinary people can read. The template for long-doc voice.

None are required, but reading any one of them will move the dial on both your writing and your judgment.
