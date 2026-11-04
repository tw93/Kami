---
name: kami
description: 'Typeset professional documents with Kami templates: resumes, one-pagers, white papers, letters, portfolios, slide decks, and social media cards. Use when asked to 做 PDF / 排版 / 简历 / 一页纸 / PPT / slides / 小红书配图, or to create a Kami landing page. Not for auditing or restyling an existing product site.'
---

# kami · 紙

**紙 · かみ** means paper in Japanese.

Good content deserves good paper. Use Kami’s templates and layout rules to create documents and landing pages with serif fonts, warm backgrounds, and ink-blue accents.

Part of `Kaku · Waza · Kami` - Kaku writes code, Waza drills habits, **Kami delivers documents**.

Commands and paths below are relative to this skill's directory. Keep the document in the user's working directory and call the scripts from there by their full path (`python3 <skill>/scripts/build.py ...`); relative file arguments resolve from your working directory first.

**Update check (non-blocking).** At the start of a task, run `bash scripts/check-update.sh`. It keeps a local daily marker and, at most once a day, reads Kami's latest published GitHub Release; it uploads no document or task content and stays silent when offline or sandboxed. When it prints a line about a newer Kami, relay it and continue.

**Brand profile.** If `~/.config/kami/brand.md` (or the legacy `~/.kami/brand.md`) exists, read `references/brand-profile.md` and apply it. Precedence: explicit prompt > editorial judgment > habit notes > frontmatter defaults > built-in defaults. The profile fills gaps silently and never overrides the current conversation. When the user names another project as the visual reference, run the style scan in the same file. When they give only a brand website, `python3 scripts/brand_extract.py <url>` drafts a profile; show the draft and use it for this document only after they accept it.

## 1 · Lock the contract

Before creating or changing an output, lock six things: language, template, output formats, page or length target, visual acceptance, and the verification command. Infer them from the request, then state the contract to the user in one short line in their language (template, length, formats, the figures you plan, any missing material) and continue without waiting. If they push back, adjust.

**Question budget.** Infer first. Ask at most once, in one compact question with at most two parts, and only when two or more of purpose, audience, hard constraints, or success are genuinely unresolvable, or two templates genuinely both fit. Otherwise take the smallest reasonable assumption and report it at the end.

Route by the artifact's current state:

| Current task | Mode | Contract |
|---|---|---|
| New document or substantial restructuring | **New document** | Lock the contract, write `content.json` with `brief` + `content`, then fill and deliver |
| Text replacement, translation, or factual correction in an existing artifact | **Content-only** | Preserve CSS and layout unless the new copy proves a fit defect |
| User supplies a render or screenshot and rejects how it looks | **Visual repair** | Treat the render as the brief; follow «Feedback protocol» |
| Standalone generated illustration, cover, or redraw | **Generated asset** | Lock the semantic brief before pixels (`references/diagrams.md` section 11); preserve accepted parts across iterations |

Use the nearest existing template and check. Do not add a template, shared CSS layer, dependency, script flag, or optional mode unless the request cannot be met without it.

### Language

| User language | HTML templates | Slides (PDF default) | Slides (PPTX, only when an editable deck is requested) | Slides (Marp) |
|---|---|---|---|---|
| Chinese (primary) | `*.html` | `slides-weasy.html` | `slides.py` | `slides-marp.md` |
| English | `*-en.html` | `slides-weasy-en.html` | `slides-en.py` | `slides-marp-en.md` |
| Japanese (best-effort) | `*.html`, JP Mincho first | `slides-weasy.html` | `slides.py` | `slides-marp.md` |
| Korean | `*-ko.html` | `slides-weasy-ko.html` | `slides-en.py` only if PPTX is required | `slides-marp.md` |
| Other (best-effort) | CJK or EN path by script coverage | `slides-weasy.html` or `-en` | `slides.py` / `slides-en.py` | `slides-marp.md` or `-en` |

Japanese, Korean, and other languages need a visual pass on the page images before shipping. Reference docs are shared English specs.

### Document type

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
| "小红书配图 / 社交卡片 / X 配图 / 推特图 / social cards / carousel" | Social Cards | `social-cards.html` | `social-cards-en.html` | `social-cards-ko.html` |

When two cells both fit, decide from the signals before asking:

| Signal | Document |
|---|---|
| 1 page for investors, recruiters, or an executive summary | one-pager |
| 1 page of formal correspondence (sales, hiring, resignation, memo) | letter |
| Exactly 2 pages of career narrative with project bullets | resume |
| 3-6 visual-heavy pages showcasing projects | portfolio |
| 6-15 pages of sustained argument, low visual density | long-doc |
| Presentation flow, one assertion per slide | slides |
| Metrics dashboard plus thesis plus price or risk view | equity-report |
| Version-by-version release facts | changelog |
| Product showcase, pricing, screenshots, FAQ for a browser | landing-page |
| A set of 3:4 images for a social feed, one point per image | social-cards |

Ask only in cases like "1.5 pages of career story, heavy visuals" (resume or portfolio?) or "2 pages of exec summary with metric tiles" (one-pager or equity-report?).

- **Changelog vs. release notes**: the changelog template is a styled document. GitHub release notes are a separate deliverable; use `/write`.
- **Landing page**: screen-first HTML, no PDF. Fill the `{{PLACEHOLDER}}` values and comment blocks and save a ready-to-serve file. The accent follows the product: use its own main color, ask the user to pick when it has none, and keep ink-blue only as the fallback (`references/design.md` Section 11 «Accent on a product site»). Companion files (`landing-page-*.example`) and the production site mode (docs, help, releases, legal pages, or more than two locales) live in `references/design.md` Section 11. Keep project-specific release artifacts, payment providers, appcast rules, and private local paths out of Kami.
- **Diagrams inside a document** come from `assets/diagrams/` (eighteen types), not a template. `references/diagrams.md` section 1 picks the type; extract the `<svg>` block into a `<figure>`. The same file owns architecture boards, diagrams maintained in the user's repo, and generated raster illustrations.
- **Charts from data** (pick and embed them without asking) are generated, never drawn by hand: write the numbers as a spec and run `python3 scripts/build.py --chart spec.json -o chart.svg` (`references/diagrams.md` section 9).
- **Slides**: read `references/deck-preflight.md` before drafting.
- **Social cards**: one `<section class="card">` per 1242x1660 image and one paper for the set, set on `<body>` (`references/design.md` Section 13). The cover headline is the post title and the cover carries a real photo or screenshot; the author's text stays as written, and a short last line is fixed with layout, not by rewording. `--deliver` writes each card at its pixel size.

## 2 · Sources, materials, and content

**Source check.** When the document names a company, product, person, release date, version, funding round, metric, market fact, or technical spec, work from primary sources, note source and date for the facts that drive it, and ask when sources conflict (`references/writing.md` «5. Sources before phrasing»). Skip it for personal drafts where the user supplied everything.

**Material check.** A branded subject needs what makes it recognizable: logo, product image or current UI screenshot, and brand colors when the document is branded (`references/writing.md` «6. Materials serve recognition»). When the request names no logo but the brand profile has one, fill the commented `.brand-logo` slot in `one-pager` / `portfolio` / `slides-weasy` (expand `~` to an absolute path; leave the slot commented if the file is missing). An explicit logo in the current request always wins.

**Gap report.** Everything the template needs that the input lacks, missing facts and missing materials alike, goes into one compact table shown once, with one question only when a missing item would change the deliverable. Inside the document, mark a gap as `[DATA NEEDED: what]`. Never fill a gap with a guess, a stock image, an approximated logo, or an invented value.

**Distill.** Unless the content already maps one-to-one onto the template sections or the user said to use it as-is, distill it. Every factual claim, number, date, name, source, and material reference from the input must land in a template section or in the gap report.

**Content IR (new documents).** Write the distilled content and the locked contract to `content.json` next to the working HTML before filling. Read `references/schemas/<type>.json` first: its `$comment` notes carry the per-field quality bar. The envelope is strict: only `type`, `lang` (`cn`, `en`, `ko`, `zh-TW`, ...), `brief`, and `content`.

```json
{
  "type": "resume",
  "lang": "cn",
  "brief": {
    "audience": "Hiring manager for a senior product role",
    "job": "Earn an interview by proving scope and outcomes",
    "template": "resume",
    "formats": ["html", "pdf"],
    "page_target": 2,
    "narrative": "Scope first, then evidence, then fit",
    "required_facts": ["team size", "measured outcomes"],
    "required_assets": [],
    "acceptance_checks": ["two pages", "all atomic facts survive"],
    "preserve": [],
    "explicit_deviations": []
  },
  "content": { ... }
}
```

`type` is a schema name in `references/schemas/` (one-pager, letter, resume, long-doc, portfolio, slides, equity-report, changelog, landing-page). For a visual repair, add `target`, `evidence`, and `preserve` to `brief`. Validate before layout with `python3 scripts/build.py --check-content content.json` and fix errors by fixing the content (or asking for the fact), never by loosening structure. Short atomic values (names, metrics, dates, bullets) must survive into the document verbatim; values over 80 characters may be rephrased.

## 3 · Read the right amount

Read the lowest tier that covers the task. The templates already carry every token and component, so a new document does not need the full design spec.

| Task | Read |
|---|---|
| Content-only change | `CHEATSHEET.md` |
| Layout tweak within spec | `CHEATSHEET.md` + the template |
| New document | the template + `CHEATSHEET.md` + `references/schemas/<type>.json` + the `references/writing.md` sections for that type («Per-document strategies», «Quality bars by document type»); open `references/design.md` only for the component or rule you are about to change |
| Resume | + `references/resume-writing.md` |
| Slides, long-doc, portfolio, equity-report, changelog | + `references/writing.md` «Page density» |
| Slides | + `references/deck-preflight.md` and the `references/design.md` section 8 «Deck Recipe» it points to |
| Social cards | + `references/design.md` section 13 «Social Cards» |
| Diagram | `references/diagrams.md`; `references/mermaid.md` when the source is Mermaid text |
| Company, product, market, or branded subject | `references/writing.md` sections 5-6 |
| Rendering bug, font issue, overflow | `references/production.md` Part 4 (and the design spec if CSS is the cause) |
| Reviewing an AI-generated draft | `references/anti-patterns.md` |

## 4 · Fill the template

- Copy the template into the working directory; never write HTML from scratch. CSS stays untouched during a content fill. A layout change stays within spec, and a real style change moves `references/design.md` and the sibling templates together, never one file.
- Meet the quality bar for the type in `references/writing.md` «Quality bars by document type»: a resume bullet needs action, honest scope, and an observable result; an equity report needs variant perception and quantified catalysts; slides need assertion titles. Structure is necessary, not sufficient.
- Do not invent metrics, financial data, or statistics, and keep any figure you compute from the supplied ones next to its inputs or marked as derived; do not describe stock images as placeholders; do not pad slots (three real projects do not become five). Avoid the patterns in `references/anti-patterns.md`.
- Tables separate rows with whitespace first and neutral hairlines second; decoration earns its place only by encoding data, state, grouping, or a relationship (`references/design.md` «Table (kami-table)» and «Subtractive rule»).
- Resume: run the recruiter pass in `references/resume-writing.md` before building.
- Mathematics is strict LaTeX: author formulas only as inline `\( ... \)` or display `\[ ... \]` in rendered body text, never as Unicode approximations, ASCII fractions, screenshots, or raw TeX on the page. `--deliver` renders them to MathJax SVG in place; it needs Node.js 20 or 22+ and `bash scripts/ensure_mathjax.sh` once.
- Code blocks with `class="language-*"` are highlighted when optional `Pygments` is installed; without it they render monochrome.

Fill the four metadata placeholders in `<head>`; WeasyPrint writes them into the PDF:

| CN | EN | Rule |
|---|---|---|
| `{{作者}}` | `{{AUTHOR}}` | Resume, letter, portfolio: the person's name from the document. Others: leave it, the build infers it from `git config user.name`, then `KAMI_AUTHOR` |
| `{{摘要}}` | `{{DESCRIPTION}}` | One sentence (≤150 chars) from the first two paragraphs |
| `{{关键词}}` | `{{KEYWORDS}}` | 3-5 keywords from the title and section headings |
| `{{文档标题}}` etc. | `{{DOC_TITLE}}` etc. | From the H1 or `.header .title` |

Keep `<meta name="generator" content="Kami">` as is.

**Output formats.** Do not ask; decide from context. Any document: HTML + PDF (PDF is the deliverable, HTML the source). Slides: HTML + PDF, plus PPTX only when an editable deck is requested. "分享 / 发朋友圈 / share / post / preview": add PNG. "嵌入 / 插图 / embed in another doc": PNG only. Landing page: the static HTML file. Word or `.docx` for long-doc, proposal, or equity-report: the PDF plus a DOCX through `references/production.md` Part 5. An explicit format request overrides all of this.

## 5 · Deliver

One command finishes a document. Run it from the document's directory, fix every `ERROR`, and re-run until it reports `READY`:

```bash
python3 scripts/build.py --deliver filled.html content.json
```

It checks the HTML (placeholders, strict math rendered in place, Markdown residue, generated charts against their data, template style, content coverage), renders the PDF next to it, then checks the PDF (page contract, resume balance, the font that actually drew CJK text, residue, density, orphans; for social cards one page per card, card fit and card orphans) and exports page images. `WARN` lines point at where to look, not at failures. `GAP` lines are the `[DATA NEEDED]` markers you must report.

Then do the part no script can: open every page image and walk the printed checklist. One hit means a whole-document sweep for that class of issue. Fix the three most visible defects per round, re-run `--deliver`, and stop after three rounds; list what is still wrong rather than looping. If the host cannot view images, send the image paths and the checklist to the user instead of skipping the pass. A missing CJK serif shows no fallback boxes, only a heavier, flatter page, which is why the font gate exists; never call a CJK document visually verified without it.

Other surfaces:

- **Landing pages and any browser surface**: `--deliver` checks the HTML only. Screenshot the responsive matrix in every shipped locale before calling it done (`references/design.md` «Responsive screenshot verification»); do not wait for the user to ask about mobile.
- **Editable PPTX**: `python3 scripts/build.py --verify slides` (or `slides-en`) and `--check-rhythm`.
- **Missing dependencies or fonts**: `python3 scripts/build.py --doctor` reports what is installed; `bash scripts/ensure-fonts.sh` recovers CJK fonts (the commercial TsangerJinKai02 never ships inside the skill package). Render failures and their fixes: `references/production.md` Part 4.

**Fresh review.** After `READY` and the image pass, review once from the contract rather than from your own rationale: reread `brief`, the coverage result, and the page images; check every acceptance item and `preserve` boundary; fix P0/P1 findings, each tied to the page or element that proves it. Use an isolated reviewer when the host has one.

**Definition of done.** The closing message gives:

1. The path of every deliverable, in every promised format.
2. The `--deliver` verdict and page count against the contract.
3. Every `[DATA NEEDED]` gap and every assumption you made, listed.
4. The visual verdict stated honestly: when page images could not be inspected, say "build verified, visuals unconfirmed", not "done".

## Feedback protocol

When the user gives visual feedback ("looks off", "太挤了", "not elegant"), inspect the current render before asking them to choose a value. The render is the evidence; the user's negative label is the acceptance signal.

1. Name the concrete defect in one sentence: page or surface, viewport or state, and whether it is density, hierarchy, alignment, type, color, cropping, or text fit.
2. Lock the repair boundary: `target` is allowed to change; `preserve` names the adjacent pages, sections, content, and shared tokens that must stay stable. Ask only when two plausible targets would produce materially different artifacts.
3. Make the smallest content, geometry, spacing, typography, crop, or token change that fixes the defect. Never hide a content problem by shrinking type first.
4. Verify the affected matrix rather than one screenshot:
   - PDF: target page, neighboring pages, total page count, font result, and every locale or template variant reached by a shared token.
   - Screen: the breakpoint, tablet, and baseline matrix in `references/design.md` «Responsive screenshot verification»; every shipped locale; affected default, focus/selected, loading, empty/error, and transition states only when the surface has them.
   - PPTX: editable source plus a rendered PDF or opened-deck inspection.
   - Generated asset: target slot at its smallest display size plus sibling assets in the same deliverable.

Never say "I'll adjust the spacing" without naming the exact property and its new value.

**Escalate after two rounds.** If the same element is still not approved after two adjustment rounds, stop nudging values and produce one comparison artifact: the current state plus 2-3 labeled variants (A/B/C) of the same content in the product's actual frame and background, changing only the compared property. For choices with no objective criterion (typeface, accent color, logo), start there: a specimen sheet of up to 5 labeled half-page blocks with identical title-plus-paragraph content. After the pick, apply it everywhere and rebuild what it touches in the same round.

## When not to use this skill

- The user explicitly wants Material, Fluent, or a Tailwind default: a different design language.
- Dark, cyberpunk, or futurist aesthetics (this is deliberately anti-future).
- Saturated multi-color palettes (this has one accent).
- Cartoon, animation, or illustration style (this is editorial).
- Dynamic web app UI (this is for print and static documents).
