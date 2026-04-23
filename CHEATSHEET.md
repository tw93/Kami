# kami · Cheatsheet

One-page quick reference. Scan before filling a template or tweaking a detail. Full spec in `references/design.md`.

## Nine invariants

1. Page background `#f5f4ed` (parchment), never pure white
2. Single accent: ink-blue `#1B365D`
3. All grays **warm-toned** (yellow-brown undertone), no cool blue-gray
4. English: serif for headlines and body. Chinese: serif headlines, sans body. Sans for UI only
5. Serif weight locked at 500, no bold
6. Line-height: headlines 1.1-1.3 / dense 1.4-1.45 / reading 1.5-1.55
7. Tag backgrounds solid hex, no rgba (WeasyPrint double-rectangle bug)
8. Depth via ring / whisper shadow, no hard drop shadows
9. No italic in templates or demos

## Sources and Materials

| Trigger | Do first |
|---|---|
| Latest product / version / launch / funding / market data | Check reliable sources first |
| Company / product / project branded doc | Confirm logo, product image, or UI screenshot |
| Key number or result | Record the source; if unverifiable, write magnitude or mark missing |
| Missing material | Mark the gap or ask the user; do not use unrelated imagery |

## Color

| Role | Hex | Use |
|---|---|---|
| Parchment | `#f5f4ed` | Page background |
| Ivory | `#faf9f5` | Card / lifted container |
| Warm Sand | `#e8e6dc` | Button / interactive surface |
| Dark Surface | `#30302e` | Dark container |
| Deep Dark | `#141413` | Dark page background |
| **Brand** | **`#1B365D`** | **Accent · CTA · title left bar (≤ 5% of surface)** |
| Ink Light | `#2D5A8A` | Links on dark surfaces |
| Near Black | `#141413` | Primary text |
| Dark Warm | `#3d3d3a` | Secondary dark / link |
| Charcoal | `#4d4c48` | Button text / dense body |
| Olive | `#5e5d59` | Subtext · descriptions |
| Stone | `#87867f` | Tertiary · metadata |
| Warm Silver | `#b0aea5` | Light text on dark surfaces |
| Border Cream | `#e8e5da` | Default card border |
| Border Warm | `#e8e6dc` | Section divider |
| Ring Warm | `#d1cfc5` | Button hover/focus ring (not for cards) |

**rgba -> solid** (parchment base + ink-blue):

| Alpha | Solid |
|---|---|
| 0.08 | `#EEF2F7` |
| 0.14 | `#E4ECF5` |
| **0.18** | **`#E4ECF5`** ← default tag |
| 0.22 | `#D0DCE9` |
| 0.30 | `#D6E1EE` |

## Type (print pt)

| Role | Size | Weight | Line-height |
|---|---|---|---|
| Display | 36-48 | 500 | 1.10 |
| H1 | 18-22 | 500 | 1.20 |
| H2 | 14-16 | 500 | 1.25 |
| H3 | 12-13 | 500 | 1.30 |
| Body Lead | 11 | 400 | 1.55 |
| Body | 9.5-10 | 400 | 1.55 |
| Body Dense | 9-9.2 | 400 | 1.42 |
| Caption | 8.5-9 | 400 | 1.45 |
| Label | 7.5-8 | 600 | 1.35 |
| Tiny | 7 | 400 | 1.40 |

Screen (px) ≈ pt × 1.33.

## Font stacks

English:

```css
--serif: "Newsreader", "Source Serif 4", "Charter",
         Georgia, "Times New Roman", serif;
--sans:  "Inter", -apple-system, BlinkMacSystemFont,
         "Helvetica Neue", Arial, sans-serif;
--mono:  "JetBrains Mono", "SF Mono", "Fira Code",
         Consolas, Monaco, monospace;
```

Chinese:

```css
--serif: "TsangerJinKai02", "Source Han Serif SC",
         "Noto Serif CJK SC", "Songti SC", "STSong",
         Georgia, serif;
--sans:  "Inter", "TsangerJinKai02", -apple-system,
         BlinkMacSystemFont, "Source Han Sans SC",
         "Noto Sans CJK SC", "PingFang SC",
         "Microsoft YaHei", Arial, sans-serif;
--mono:  "JetBrains Mono", "SF Mono", Consolas,
         "TsangerJinKai02", "Source Han Serif SC",
         monospace;
```

Any font-family that may render Chinese must include a CJK fallback, including `@page` footer text, `pre`, `code`, and SVG labels. A pure mono stack can render missing glyph boxes in WeasyPrint.

## Spacing (4pt base)

| Tier | Value | Use |
|---|---|---|
| xs | 2-3pt | Inline |
| sm | 4-5pt | Tag padding |
| md | 8-10pt | Component interior |
| lg | 16-20pt | Between components |
| xl | 24-32pt | Section-title margin |
| 2xl | 40-60pt | Between major sections |
| 3xl | 80-120pt | Between chapters |

**Page margins (A4)**

| Document | T · R · B · L |
|---|---|
| Resume | 11 · 13 · 11 · 13 mm |
| One-Pager | 15 · 18 · 15 · 18 mm |
| Long Doc | 20 · 22 · 22 · 22 mm |
| Letter | 25 mm all sides |
| Portfolio | 12 · 15 · 12 · 15 mm |

## Radius scale

`4pt -> 6pt -> 8pt (default) -> 12pt -> 16pt -> 24pt -> 32pt (hero)`

## Common CSS snippets

### Card

```css
.card {
  background: var(--ivory);
  border: 0.5pt solid var(--border-cream);
  border-radius: 8pt;
  padding: 16pt 20pt;
  transition: box-shadow 0.2s;
}
.card:hover {
  box-shadow: 0 4pt 24pt rgba(0, 0, 0, 0.05);  /* whisper shadow */
}
```

### Tag (default lightest solid)

```css
.tag {
  background: #EEF2F7;            /* 0.08 equivalent */
  color: var(--brand);
  font-size: 8pt; font-weight: 600;
  padding: 1pt 5pt;
  border-radius: 2pt;
  letter-spacing: 0.4pt;
  text-transform: uppercase;
}
```

### Section title (brand left bar is the signature move)

```css
.section-title {
  font-family: var(--serif);
  font-size: 14pt; font-weight: 500;
  color: var(--near-black);
  margin: 24pt 0 10pt 0;
  border-left: 2.5pt solid var(--brand);
  border-radius: 1.5pt;
  padding-left: 8pt;
}
```

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
  border-left: 2pt solid var(--brand);
  padding: 4pt 0 4pt 14pt;
  color: var(--olive);
  line-height: 1.55;
}
```

## Diagram components

Twelve built-in diagram types. Extract the `<svg>` block and embed in a `<figure>` in long-doc / portfolio:

| Type | File | Use |
|---|---|---|
| Architecture | `assets/diagrams/architecture.html` | System components and connections |
| Flowchart | `assets/diagrams/flowchart.html` | Decision branches and flows |
| Quadrant | `assets/diagrams/quadrant.html` | 2×2 positioning |
| Bar Chart | `assets/diagrams/bar-chart.html` | Category comparison (up to 8 groups × 3 series) |
| Line Chart | `assets/diagrams/line-chart.html` | Trends over time (up to 12 points × 3 lines) |
| Donut Chart | `assets/diagrams/donut-chart.html` | Proportional breakdown (up to 6 segments) |
| State Machine | `assets/diagrams/state-machine.html` | Finite states + directed transitions |
| Timeline | `assets/diagrams/timeline.html` | Time axis + milestone events |
| Swimlane | `assets/diagrams/swimlane.html` | Cross-responsibility process flow |
| Tree | `assets/diagrams/tree.html` | Hierarchical relationships |
| Layer Stack | `assets/diagrams/layer-stack.html` | Vertically stacked system layers |
| Venn | `assets/diagrams/venn.html` | Set intersections and overlaps |

Usage: extract the `<svg>` block from the HTML file and paste into the template's `<figure>` container.

**Data chart colors**: primary series `#1B365D` · secondary `#5e5d59` → `#87867f` → `#b8b7b0` → `#d4d3cd` → `#EEF2F7`.

**Editing data**: only modify elements between `<!-- DATA START -->` / `<!-- DATA END -->`, leave CSS untouched. All coordinates must be divisible by 4.

## Dark section

Alternate light/dark rhythm: add `.sd-alt` to any section container.

- Background switches to `--deep-dark` (`#141413`)
- Body text switches to `--warm-silver` (`#b0aea5`)
- Headings switch to `--ivory`
- Appropriate for: section-level light/dark alternation in long-doc / portfolio
- Restriction: showcase pages only, never in print templates

## Verification checks

`python3 scripts/build.py --verify [target]` checks source templates and slides in sequence:

1. Source file exists
2. WeasyPrint render to PDF for HTML / diagram targets
3. Page count check for strict targets
4. Font embedding check
5. PPTX generation for `slides` / `slides-en`

Source templates intentionally keep `{{...}}` fields. Run `python3 scripts/build.py --check-placeholders path/to/filled.html` on completed documents.

## Quick decisions

| Need | Use |
|---|---|
| Headline | serif 500, line-height 1.10-1.30 |
| Reading body (EN) | serif 400, 9.5-10pt, 1.55 |
| Reading body (CN) | sans 400, 9.5-10pt, 1.55 |
| Emphasize a number | `color: var(--brand)`, no bold |
| Divide two sections | 2.5pt brand left bar, or 0.5pt warm dotted |
| Quote | 2pt brand left border + olive color |
| Code | ivory bg + 0.5pt border + 6pt radius + mono |
| Primary button | brand fill + ivory text |
| Secondary button | warm-sand + charcoal |
| Chapter start | serif heading + 2.5pt brand left bar |
| Cover | Display heading + right-aligned author/date + heavy whitespace |

Not on the table -> first principles: **serif carries authority, sans carries utility, warm gray carries rhythm, ink-blue carries focus**.
