# kami · Cheatsheet

One-page quick reference. Scan before filling a template or tweaking a detail. Full spec in `references/design.md`.

## Ten invariants

1. Default page background `#f5f4ed` (parchment); the white-paper print variant is an explicit exception
2. Single accent: ink-blue `#1B365D`; social cards pick one paper from `references/social-palettes.json`, each with one accent
3. All grays **warm-toned** (yellow-brown undertone), no cool blue-gray
4. One serif font per page (headings + body). `--sans` is a CSS alias for the same family; introduce a real sans only for genuinely UI-style chrome
5. Serif weights 400 body / 500 headings, no bold (social-card list numerals are the one Charter Bold)
6. Line-height: headlines 1.1-1.3 / dense 1.4-1.45 / reading 1.5-1.55
7. Letter-spacing: Chinese body with TsangerJinKai 0.1-0.2pt (dense layouts may push to 0.3pt); English body 0; small labels and all-caps overlines get +0.2-1pt
8. Tag backgrounds solid hex, no rgba (WeasyPrint double-rectangle bug)
9. No decorative ticks, short rules, or side accents; every line must encode separation, state, or relationship
10. No italic in templates or demos

## Sources and Materials

Full pass in SKILL.md «2 · Sources, materials, and content». The one contract worth repeating: a number you cannot verify ships as a magnitude or a marked gap, never as fake precision.

## Color


| Role         | Hex           | Use                                                 |
| ------------ | ------------- | --------------------------------------------------- |
| Parchment    | `#f5f4ed`     | Page background                                     |
| Ivory        | `#faf9f5`     | Quiet filled container                              |
| Inline Code  | `#f0eee6`     | Screen annotation, slightly darker than paper       |
| Warm Sand    | `#e8e6dc`     | Button / interactive surface                        |
| Dark Surface | `#30302e`     | Dark container                                      |
| Deep Dark    | `#141413`     | Dark page background                                |
| **Brand**    | **`#1B365D`** | **Accent · CTA · key labels (≤ 5% of surface)**     |
| Ink Light    | `#2D5A8A`     | Links on dark surfaces                              |
| Near Black   | `#141413`     | Primary text                                        |
| Dark Warm    | `#3d3d3a`     | Secondary text · table headers · links              |
| Olive        | `#504e49`     | Subtext · descriptions                              |
| Stone        | `#6b6a64`     | Tertiary · metadata                                 |
| Border       | `#e8e6dc`     | Primary border · section divider                    |
| Border Soft  | `#e5e3d8`     | Secondary border · row separator                    |


**Registered solid tints** (never substitute `rgba()`):


| Role        | Solid                       |
| ----------- | --------------------------- |
| Quiet fill  | `#EEF2F7`                   |
| Default tag | **`#E4ECF5`**               |


## Type (print pt)


| Role       | Size | Weight | Line-height |
| ---------- | ---- | ------ | ----------- |
| Display    | 36   | 500    | 1.10        |
| H1         | 22   | 500    | 1.20        |
| H2         | 16   | 500    | 1.25        |
| H3         | 13   | 500    | 1.30        |
| Body Lead  | 11   | 400    | 1.55        |
| Body       | 10   | 400    | 1.55        |
| Body Dense | 9.2  | 400    | 1.42        |
| Caption    | 9    | 400    | 1.45        |
| Label      | 9    | 500    | 1.35        |
| Tiny       | 9    | 400    | 1.40        |


Screen (px) ≈ pt × 1.33.
Minimum floor: web text >= 12px, PDF body text and labels >= 9pt. Named dense exceptions may go to 8-8.5pt: `.compact` tables, running footers, and dense resume timelines.

### Typography cross-check (from Pierrick Calvez, "A Five-Minute Guide to Better Typography")

- **Set blocks, not glyphs**: judge a paragraph as an even gray shape, not one nice letter at a time.
- **Measure**: reading body ~40-70 characters per line; hold screen prose to the ~720px reading column, print to the A4 margins.
- **Optical > mathematical alignment**: aligned when it looks aligned; nudge back quotes, bullets, and big display caps by eye.
- **Line-spacing maps onto Kami tiers**: short ~1.2x → tight/dense tiers; long reading ~1.5x → reading tier. Never invent 1.6+ on a print body.
- **Hierarchy = contrast (size / weight / space)**, not ornament. Use the next registered size step, never an in-between size or a decorative rule.
- **Left-align body; centre only short display lines.** No centred paragraphs or lists.
- **Do NOT import multi-weight**: the guide wants Light/Regular/Medium/Bold; Kami serif is 400 body + 500 headings only, no 700, no Light. Emphasis is size, space, and ink-blue. Also skip its em-dash / ornamental-punctuation habits (see anti-patterns #28). Full cross-check: `references/design.md` §2 «External principles cross-check».

## Font stacks

Each language uses a single serif for the entire page. `--sans` always equals `var(--serif)`.

English:

```css
--serif: Charter, Georgia, Palatino,
         "Times New Roman", serif;
--sans:  var(--serif);
--mono:  "JetBrains Mono", "SF Mono", "Fira Code",
         Consolas, Monaco, monospace;
```

Chinese:

```css
--serif: "TsangerJinKai02", "Source Han Serif SC", "Source Han Serif CN",
         "Noto Serif CJK SC", "Noto Serif SC", "Songti SC", "STSong", "SimSun",
         Georgia, serif;
--sans:  var(--serif);
--mono:  "JetBrains Mono", "SF Mono", Consolas,
         "TsangerJinKai02", "Source Han Serif SC",
         monospace;
```

Japanese:

```css
--serif: "YuMincho", "Yu Mincho", "Hiragino Mincho ProN",
         "Noto Serif CJK JP", "Source Han Serif JP",
         "TsangerJinKai02", Georgia, serif;
--sans:  var(--serif);
```

Any font-family that may render Chinese or Japanese must include a CJK fallback, including `@page` footer text, `pre`, `code`, and SVG labels. A pure mono stack can render missing glyph boxes in WeasyPrint.

## Spacing (4pt base)


| Tier | Value    | Use                    |
| ---- | -------- | ---------------------- |
| xs   | 2-3pt    | Inline                 |
| sm   | 4-5pt    | Tag padding            |
| md   | 8-10pt   | Component interior     |
| lg   | 16-20pt  | Between components     |
| xl   | 24-32pt  | Section-title margin   |
| 2xl  | 40-60pt  | Between major sections |
| 3xl  | 80-120pt | Between chapters       |


**Page margins (A4)**


| Document      | T · R · B · L        |
| ------------- | -------------------- |
| Resume        | 11 · 13 · 11 · 13 mm |
| One-Pager     | 15 · 18 · 15 · 18 mm |
| Long Doc      | 20 · 22 · 22 · 22 mm |
| Letter        | 25 mm all sides      |
| Portfolio     | 12 · 15 · 12 · 15 mm |
| Equity Report | 16 · 18 · 18 · 18 mm |
| Changelog     | 20 · 22 · 22 · 22 mm |
| Landing Page  | N/A (screen-first, max-width: 1120px, padding: 88px 64px) |


## Radius scale

Print radii stay within `2-6pt` and follow physical scale, from compact chips to
large media frames. Screen: `8px` for blocks and `999px` only for pill actions.
Do not use radius alone to create emphasis.

## Common CSS snippets

### Card

```css
.card {
  background: var(--ivory);       /* one quiet grouping cue; no border/shadow */
  border-radius: 4pt;
  padding: 16pt 20pt;
}
```

A sub-1pt closed border plus a radius renders as a double ring (production.md
pitfall #2) and fails `scripts/build.py --check`. To give a card more weight,
strengthen its label or opening sentence. Do not add an accent edge.

### Tag (solid fill, never rgba)

```css
.tag {
  background: var(--tag-bg);
  color: var(--brand);
  font-size: 9pt; font-weight: 500;
  padding: 1pt 5pt;
  border-radius: 3pt;
  letter-spacing: 0.3pt;
}
```

### Section title

```css
h2 {
  font-family: var(--serif);
  font-size: 16pt; font-weight: 500;
  color: var(--near-black);
  margin-bottom: 6pt;
}
```

Type carries the hierarchy; a section head needs no rule, bar, or underline.
This also applies to `changelog*.html`: release groups stay scannable through
type, numbering, and spacing. `resume*.html` uses a quiet full-width bottom
rule because it separates major content regions, and keeps project rows
borderless so section titles never create double rules or lonely page-top lines.

### Table (kami-table)

Base class works on bare `<table>` or `.kami-table`. Add variant classes for density/alignment:

```css
/* Base */
table, .kami-table {
  width: 100%; border-collapse: collapse;
  font-size: 9.5pt; margin: 12pt 0; break-inside: avoid;
}
table th { text-align: left; font-weight: 500; color: var(--dark-warm);
  padding: 6pt 8pt; border-bottom: 0.6pt solid var(--border); }
table td { padding: 5pt 8pt; border-bottom: 0.25pt solid var(--border);
  vertical-align: top; }
table.compact th { padding: 3pt 6pt; font-size: 8pt; }
table.compact td { padding: 2.5pt 6pt; font-size: 8pt; line-height: 1.4; }
table .total td { font-weight: 500; border-top: 0.6pt solid var(--border);
  border-bottom: none; }
/* Outer columns sit on the text edge; striped rows keep their inset */
table:not(.striped) th:first-child, table:not(.striped) td:first-child { padding-left: 0; }
table:not(.striped) th:last-child, table:not(.striped) td:last-child { padding-right: 0; }
```


| Variant   | Class              | Effect                                               |
| --------- | ------------------ | ---------------------------------------------------- |
| Compact   | `.compact`         | 8pt font, 3pt / 2.5pt vertical padding; use only when density requires it |
| Financial | `.financial`       | Right-align all columns except first, `tabular-nums` |
| Striped   | `.striped`         | Neutral rows only for 8+ body rows that remain hard to track   |
| Total row | `.total` on `<tr>` | Bold, 0.6pt neutral top rule, no bottom border       |


Start without striping. Add it only after the rendered 8+ row table fails the row-tracking check: `<table class="kami-table financial striped">`.

Table acceptance: all rules use `--border`; header and total rules are 0.6pt, body rules are 0.25pt; normal vertical padding is at least 6pt / 5pt, compact padding is at least 3pt / 2.5pt; the outer columns sit flush with the text edge unless the table is striped. No tinted header, category-colored value, brand-colored rule, vertical grid, or framed box.

### Metric (data card)

```css
.metric { display: flex; align-items: baseline; gap: 6pt; }
.metric-value {
  font-family: var(--serif); font-size: 16pt; font-weight: 500;
  color: var(--brand);
  font-variant-numeric: tabular-nums;
}
.metric-label { font-size: 9pt; color: var(--olive); }
```

### Quote

```css
.quote {
  margin: 12pt 16pt;
  padding: 4pt 0;
  color: var(--olive);
  line-height: 1.55;
}
```

## Diagram components

Eighteen built-in diagram types (incl. Mermaid-sourced sequence / class / ER; see `references/mermaid.md`). Extract the `<svg>` block and embed in a `<figure>` in long-doc / portfolio:


| Type          | File                                 | Use                                             |
| ------------- | ------------------------------------ | ----------------------------------------------- |
| Architecture  | `assets/diagrams/architecture.html`  | System components and connections               |
| Architecture Board | `assets/diagrams/architecture-board.html` | Report-scale five-layer system board (standalone page) |
| Flowchart     | `assets/diagrams/flowchart.html`     | Decision branches and flows                     |
| Quadrant      | `assets/diagrams/quadrant.html`      | 2×2 positioning                                 |
| Bar Chart     | `--chart` type `bar`                 | Category comparison (up to 8 groups × 3 series) |
| Line Chart    | `--chart` type `line`                | Trends over time (up to 12 points × 3 lines)    |
| Donut Chart   | `--chart` type `donut`               | Proportional breakdown (up to 6 segments)       |
| Horizontal Bar | `--chart` type `hbar`               | Ranking, or a share with 7+ parts (up to 12 rows) |
| State Machine | `assets/diagrams/state-machine.html` | Finite states + directed transitions            |
| Timeline      | `assets/diagrams/timeline.html`      | Time axis + milestone events                    |
| Swimlane      | `assets/diagrams/swimlane.html`      | Cross-responsibility process flow               |
| Tree          | `assets/diagrams/tree.html`          | Hierarchical relationships                      |
| Layer Stack   | `assets/diagrams/layer-stack.html`   | Vertically stacked system layers                |
| Venn          | `assets/diagrams/venn.html`          | Set intersections and overlaps                  |
| Candlestick   | `--chart` type `candlestick`         | OHLC price history (up to 30 days)              |
| Waterfall     | `--chart` type `waterfall`           | Revenue bridge / decomposition                  |


Usage: extract the `<svg>` block from the HTML file and paste into the template's `<figure>` container. Data charts are generated instead: write the numbers as a JSON spec, run `python3 scripts/build.py --chart spec.json -o chart.svg`, and paste that `<svg>` (spec fields in `references/diagrams.md` section 9).

**Repo-maintained diagram** (README / docs-site figure living in the user's repository): keep the trio consistent, `index.html` source + same-name PNG re-exported after every change + `prompt.md` (must preserve / suggested additions / visual direction / sister boundaries). Evidence pass before drawing; maturity encoding for shipped / in-build / future. See `references/diagrams.md` «Maintained diagram assets».

**Data charts**: colors, axes, and geometry come from `scripts/chart.py`. To change a number, edit the spec and regenerate; `--deliver` fails a chart whose marks no longer match its embedded spec.

## Verification checks

Finish every filled document with one command: `python3 scripts/build.py --deliver filled.html content.json`. It runs placeholders, strict math (rendered to MathJax SVG in place), Markdown residue, template style, content coverage, the PDF render, page contract, resume balance, fonts, density, and orphans (card fit and card orphans for social cards), exports page images, and ends in READY or NOT READY. Fix every ERROR, re-run, then view every page image against the printed checklist.

Validate the content IR before layout with `python3 scripts/build.py --check-content content.json` (schemas in `references/schemas/`). `python3 scripts/build.py --verify [target]` is the maintainer check for the source templates themselves, which intentionally keep `{{...}}` fields.

**Strict mathematics**: author formulas only as standard LaTeX `\( inline \)` or `\[ display \]`; the delivered result is MathJax SVG, never Unicode pseudo-formulas, raw TeX, or formula screenshots. Install the runtime once with `bash scripts/ensure_mathjax.sh`.

Marp variant deck (opt-in): `assets/templates/marp/`. Render with local `marp-cli`. See design.md §8 + production.md Part 2.5.

## Content quality (one rule per type)

Full quality bars in `references/writing.md`. The single most important rule for each document type:


| Document      | Core quality rule                                                                    |
| ------------- | ------------------------------------------------------------------------------------ |
| Resume        | Every bullet: action, honest scope, and a concrete result; use verified numbers when available                  |
| Portfolio     | Open with the problem and stakes, not the project name                               |
| Slides        | Slide titles are full sentences (assertions), not topic labels                       |
| Equity Report | Lead with variant perception: what you see that the market doesn't                   |
| Long Document | Each chapter claim paragraph must survive the "so what?" test                        |
| One-Pager     | Metrics are the headline; if the 4 cards don't tell the story, the metrics are wrong |
| Letter        | First paragraph states purpose in one sentence                                       |
| Changelog     | One sentence per change, verb-led, user-facing language                              |
| Social Cards  | The author's words unchanged; layout fixes every short line, never a rewrite         |


## Per-page font size strategy (Resume two-page)

Page 1 carries the projects section, which is the densest content. Page 2 carries open source, convictions, impact, skills, and education, which has more breathing room.

| Location | Class | Default | Dense (5 projects) |
|---|---|---|---|
| Project body | `.proj-text` | 9pt / lh 1.40 | 9pt / lh 1.38 |
| Timeline body | `.tl-body` | 9pt / lh 1.40 | 8.5pt (CN) |
| Summary | `.summary` | 9.2pt | 9pt via body |
| Section titles | `.section-title` | margin-top 5mm | 3.5mm |
| OS intro | `.os-intro` | 9.2pt | unchanged |
| Conviction body | `.conv-body` | 9pt | unchanged |
| Skills body | `.skill-body` | 9pt | unchanged |

**Reference config (5 projects + full page 2)**:

```html
<body class="resume--dense">
  <!-- page 1: 5 projects, timeline, summary -->
  <!-- page 2: OS grid (6), convictions, impact, skills, edu -->
</body>
```

Filled resume PDFs should be exactly 2 pages with both pages visually used. Check the rendered result:

```bash
python3 scripts/build.py --check-resume-balance path/to/resume.pdf
```

Page 2 font sizes stay at template defaults. The density variant only tightens page 1 elements. If page 2 has unusually long content, reduce `.os-intro`, `.conv-body`, or `.skill-body` individually, never globally.

Resume visual rule: header and section titles carry the only structural rules. Top metrics stack value over label so labels stay single-line; project rows separate by padding, not borders.

## Quick decisions


| Need                | Use                                                            |
| ------------------- | -------------------------------------------------------------- |
| Headline            | serif 500, line-height 1.10-1.30                               |
| Reading body        | serif 400, 9.5-10pt, 1.55 (CN pins `--sans: var(--serif)`)     |
| Emphasize a number  | `color: var(--brand)`, no bold                                 |
| Raise a passage     | `.callout`: ivory fill + 3pt radius, no accent edge              |
| Quote               | indented olive text with reading space, no fill or side rule     |
| Code                | `long-doc` `pre` / `code`: ivory fill, 4pt / 2pt radius, no border |
| Key figures         | `one-pager` `.metric`: baseline row, transparent, not a card    |
| Buttons             | `landing-page` `.btn-primary` / `.btn-ghost` (screen only)      |
| Section start       | serif scale and margin only, no tick, side bar, or short rule    |
| Cover               | Display heading + right-aligned author/date + heavy whitespace |
| Figure SVG          | `width: 100%; height: auto; max-height: <safe>`. Never `max-height` alone (starves width on wide viewBoxes; production.md #16). |
| Metric labels (4-col) | Soft cap 14-18 chars at 9pt Charter; trim context, don't wrap (production.md #17). |
| Multi-column body   | Hold lengths within ±10 chars across parallel columns (production.md #18). |
| Image references    | Always inside the demo's own `images/` folder (`site/assets/demos/images/` in this repository) or `site/assets/illustrations/`; never `../../sibling-project/...` (production.md #19). |
| Metric row layout   | Screen (landing page, slides): vertical stack (`flex-direction: column`), since horizontal baseline-align breaks when any label wraps. Print keeps the one-pager baseline row with `nowrap` labels (production.md #20). |
| Slide bullets       | Numerals `1. 2. 3.` or `•`; en-dash `–` reads informal at slide scale (production.md #21). Print docs keep en-dash. |


Not on the table -> first principles: **use type size for hierarchy, spacing for grouping, and ink-blue for emphasis**.
