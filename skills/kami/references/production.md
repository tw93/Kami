# Production (Build · Verify · Troubleshoot)

The engineering runbook for kami: from HTML / Python / Markdown sources to PDF,
PPTX, browser-deck, and DOCX deliverables. It covers each supported render path,
verification and debugging, and the known pitfalls gathered from production use.

---

## Part 1 · HTML -> PDF (WeasyPrint)

### Install

```bash
pip install weasyprint pypdf pymupdf --break-system-packages --quiet
```

Linux first-time:
```bash
apt install -y libpango-1.0-0 libpangoft2-1.0-0 fonts-noto-cjk
```

Windows: use WSL (Ubuntu) and follow the Linux steps; the helper scripts are Bash, and native Windows WeasyPrint needs the GTK/Pango runtime installed separately.

### Generate

```python
from weasyprint import HTML
HTML('doc.html').write_pdf('output.pdf')
```

**CWD matters**: `@font-face { src: url("xxx.ttf") }` uses relative paths, so run from the directory containing the font file.

```bash
cd /path/to/html-and-font
python3 -c "from weasyprint import HTML; HTML('doc.html').write_pdf('out.pdf')"
```

### Fonts

**Most stable setup**: font file alongside HTML, `@font-face` with relative path.

```html
<style>
@font-face {
  font-family: "TsangerJinKai02";
  src: url("TsangerJinKai02-W04.ttf");
  font-weight: 400 500;
}
body { font-family: Charter, Georgia, Palatino, serif; }
</style>
```

**No commercial font available**: fallback chains are embedded in every template.

```css
/* English */
font-family: Charter, Georgia, Palatino,
             "Times New Roman", serif;

/* Chinese */
font-family: "TsangerJinKai02", "Source Han Serif SC", "Source Han Serif CN",
             "Noto Serif CJK SC", "Noto Serif SC", "Songti SC", "STSong", "SimSun",
             Georgia, serif;

/* Japanese */
font-family: "YuMincho", "Yu Mincho", "Hiragino Mincho ProN",
             "Noto Serif CJK JP", "Source Han Serif JP",
             "TsangerJinKai02", Georgia, serif;

/* Korean */
font-family: "Source Han Serif K", "Source Han Serif KR",
             "Noto Serif KR", "Nanum Myeongjo", AppleMyungjo,
             "Apple SD Gothic Neo", Charter, Georgia, serif;
```

**Traditional Chinese** uses the Chinese templates with the root set to `<html lang="zh-Hant">` (or `zh-TW`, `zh-HK`, `zh-MO`). TsangerJinKai02 draws mainland punctuation only: the comma and full stop sit bottom-left in a cell about 0.68em wide, and the font has no `locl` forms for Taiwan or Hong Kong, where those marks are centered and one character wide. For such a root, `render_pdf` (`scripts/hant.py`) leads every stack that names TsangerJinKai02 with `Source Han Serif TC, Noto Serif CJK TC, Noto Serif TC, Songti TC, PMingLiU` and keeps TsangerJinKai02 behind them. The swap happens at render time because WeasyPrint draws inline SVG labels without the document stylesheet, so a `:lang()` rule never reaches them; it inserts the names unquoted for the reason in pitfall 4.1. `landing-page.html` does the swap with a `:lang()` rule, since browsers do apply the stylesheet to inline SVG. None of these faces ship with Kami: macOS has Songti TC, Windows has PMingLiU, Linux gets Noto Serif CJK TC from `fonts-noto-cjk`. The editable PPTX and Marp paths still set TsangerJinKai02.

**Font fallback affects page count**. Any font swap requires re-running the page-count check. If output overflows, first confirm the intended font actually loaded. If it did, edit content using pitfall "Hard-limit overflow"; spacing comes later and font size is the last resort.

**Claude Desktop skill ZIPs do not bundle large CJK font files**: `TsangerJinKai02-W04.ttf`, `TsangerJinKai02-W05.ttf`, `SourceHanSerifKR-Regular.otf`, and `SourceHanSerifKR-Medium.otf` can make Claude.ai / Desktop skill upload or execution time out. The ZIP you upload must be the `scripts/package-skill.sh` output under the 6MB package ceiling, never a hand-zipped checkout. `package-skill.sh` excludes those large font files. Templates still keep local-first and jsDelivr fallback `@font-face` paths.

When Chinese or Korean fonts are missing (the skill case), `scripts/ensure-fonts.sh` downloads them to the XDG user font dir (`${XDG_DATA_HOME:-~/.local/share}/fonts/kami`), **not** into the skill's `assets/fonts`. fontconfig scans that default dir on macOS and Linux, so WeasyPrint resolves `TsangerJinKai02` and `Source Han Serif K` from there while the installed skill stays small; online renders still use the jsDelivr `@font-face` URL. `KAMI_FONT_DIR` overrides the target and is meant for tests: fontconfig does not scan an arbitrary directory, so an override outside a scanned font tree downloads fonts that WeasyPrint and `kami_doctor` never see.

**Standalone HTML export** (sending a filled HTML file to someone else): this is not guaranteed to work outside the project tree. If the recipient cannot set up the font environment, use the PDF output instead.

If you do need to share HTML: the font file and the HTML must live in the same directory, and the `@font-face src` must use a bare filename with no path prefix:

```css
@font-face {
  font-family: "TsangerJinKai02";
  src: url("TsangerJinKai02-W04.ttf") format("truetype");
}
```

Remove the `../fonts/` prefix that templates use when fonts are in the project tree. The recipient must place the `.ttf` file alongside the `.html` file before running WeasyPrint. When in doubt, deliver the PDF.

### Page spec

```css
@page {
  size: A4;                     /* or 210mm 297mm / A4 landscape / 13in 10in */
  margin: 20mm 22mm;
  background: #f5f4ed;          /* extend past margins to avoid white printed edge */
}
```

### Print / white-paper variant (opt-in)

Parchment is the default and keeps shipping. Override to white only when a single
document is **headed for a home / office printer**: a full-page `#f5f4ed` tint
bands unevenly and burns toner, where white paper prints clean. This is the one
sanctioned print exception to design.md invariant #1, and it is
opt-in per document, never the default render.

White is not a one-line background swap. Parchment also serves as the surface that
`--ivory` cards, code blocks, and striped rows lift *off* of (they are "brighter
than parchment"). Flip the page to white and those surfaces, only 1.5% lighter than
white, vanish. So relocate the warmth instead of deleting it: sink parchment down
into the lift surface. Three edits on the copied, filled template:

```css
@page      { background: #ffffff; }   /* was #f5f4ed */
html, body { background: #ffffff; }   /* was var(--parchment) */
:root      { --ivory: #f5f4ed; }      /* parchment becomes the card/code/table lift */
```

Everything else is unchanged: ink-blue accent, warm text grays, and `--border`
hairlines all read fine on white. Leave the `--parchment` token itself alone (any
`var(--parchment)` section fill then reads as an intentional warm band on white).
A lifted surface that separated from parchment by fill *alone* (rare, most already
carry a `0.5pt var(--border)` edge) wants that border added so it holds an edge on
white.

Notes:
- Lint-safe by construction: `scripts/lint.py` off-palette and token-sync guards
  scan only registered templates, not generated documents, so `#ffffff` in a
  filled output never trips them.
- Page-count and `--check-density` contracts are unaffected; still inspect that
  cards, code, and tables read on white before shipping.
- If white-paper output ever becomes a first-class, frequent ask, promote this from
  a recipe to a `--page-bg` / `--surface` token pair in every template `:root`
  (ships commented, like the `.brand-logo` slot). `@page { background: var(--page-bg) }`
  is verified to resolve in WeasyPrint (68.1), so the token path is viable. Until
  then, keep it a recipe: the project's contract is "no new mode unless a request
  can't be met otherwise", and this recipe already meets the request.

### Headers & footers

Long-doc running headers use `string(section-title)`. The default templates set
that string on chapter `h1` elements, not on every `h2`, so a table of contents
heading cannot pin the header to "Contents" / "目录". If a filled document uses a
different element for chapter titles, add `.running-title` to that element.

```css
@page {
  @top-right {
    content: counter(page);
    font-family: serif; font-size: 9pt; color: #6b6a64;
  }
  @bottom-center {
    content: "{{DOC_NAME}} · {{AUTHOR}}";
    font-size: 9pt; color: #6b6a64;
  }
}

@page:first {
  @top-right { content: ""; }
  @bottom-center { content: ""; }
}
```

### WeasyPrint support matrix

| Solid | Partial | Unsupported |
|---|---|---|
| CSS Grid / Flexbox | CSS filter / transform (partial) | JavaScript |
| `@page` rules | inline SVG (some attrs) | `position: sticky` |
| `@font-face` | gradients (slow, use sparingly) | CSS animations / transitions |
| `break-before` / `break-inside: avoid` | | |
| CSS variables `var(--name)` | | |
| `target-counter(attr(href), page)` on a block anchor (pitfall 24) | | |
| `::before` / `::after` | | |

### Strict LaTeX mathematics

WeasyPrint has no JavaScript runtime, so MathJax/KaTeX script tags do **not** render mathematics. Kami therefore uses a local MathJax SVG path backed by Node.js 20 or Node.js 22 and newer. Author source formulas strictly as inline `\( ... \)` or display `\[ ... \]` in rendered body text. Delimiters inside title metadata, form options, literal/code/script/style/SVG/template/MathML regions are ignored. Do not ship Unicode approximations, raw TeX, or screenshot formulas.

```bash
# One-time dependency check/install
bash scripts/ensure_mathjax.sh

# Convert every standard LaTeX delimiter pair in delivered HTML to MathJax SVG
python3 scripts/math_render.py --in-place filled.html

# A completed HTML must have no raw TeX delimiters
python3 scripts/math_render.py --check filled.html
```

`render_pdf` performs the same conversion in memory as a hard fallback and fails on unmatched delimiters, invalid TeX, author-controlled color/HTML/link commands, unsafe MathJax markup, or a missing locked runtime. Formulas inherit the document's text color. The in-place command writes atomically and remains required when HTML itself is delivered, reviewed, or reused. MathJax SVG is vector output and prints sharply in WeasyPrint PDFs.

### PDF metadata

WeasyPrint reads standard meta tags in `<head>` and writes them into the PDF (Title / Author / Subject / Keywords). All templates have pre-built placeholders:

```html
<head>
  <title>{{DOC_TITLE}}</title>
  <meta name="author"      content="{{AUTHOR}}">
  <meta name="description" content="{{DESCRIPTION}}">
  <meta name="keywords"    content="{{KEYWORDS}}">
  <meta name="generator"   content="Kami">
</head>
```

**Auto-inference rules** (Claude fills these from the document content without asking):

| Field | Source |
|---|---|
| `<title>` | H1 heading or `.header .title` text |
| `author` | Resume / letter / portfolio: person's name from the document; everything else: `"Kami"` |
| `description` | One sentence extracted from the first 2 paragraphs, ≤150 characters |
| `keywords` | 3-5 keywords from title + section headings, comma-separated |
| `generator` | Fixed `"Kami"`, already set in template, do not change |

**Verify**:

```bash
pdfinfo assets/examples/one-pager-en.pdf   # shows Title / Author / Subject
```

---

## Part 2 · Python -> PPTX (python-pptx)

PPT shares the same design language but the medium (screen, 16:9, one-idea-per-slide) changes the details: fonts larger, layouts more rigid.

### Install

```bash
pip install python-pptx --break-system-packages --quiet
```

### Dimensions

- **16:9 widescreen** (preferred): 13.33 × 7.5 inch
- **4:3 traditional**: 10 × 7.5 inch
- **Safe zone**: 0.5 inch margin on all sides (projector crop), plus 0.3 inch at bottom for page number

### Palette (mirrors `assets/templates/slides.py`)

```python
from pptx.dml.color import RGBColor

PARCHMENT   = RGBColor(0xf5, 0xf4, 0xed)
IVORY       = RGBColor(0xfa, 0xf9, 0xf5)
BRAND       = RGBColor(0x1B, 0x36, 0x5D)
NEAR_BLACK  = RGBColor(0x14, 0x14, 0x13)
DARK_WARM   = RGBColor(0x3d, 0x3d, 0x3a)
OLIVE       = RGBColor(0x50, 0x4e, 0x49)
STONE       = RGBColor(0x6b, 0x6a, 0x64)
BORDER      = RGBColor(0xe8, 0xe6, 0xdc)
```

The PPTX path defines no tag constant; tag styling is print- and screen-only. `references/tokens.json` is the source of truth for the values; `scripts/tokens.py` pins the ones in its `PY_TOKEN_MAP` (`BORDER` is not among them, so change it in `slides.py` and here together).

### Type (bigger than print, optimized for projection)

| Role | Size | Font |
|---|---|---|
| Title | 48pt | Serif 500 |
| Subtitle | 24pt | Serif 400 |
| H2 chapter | 32pt | Serif 500 |
| H3 subtitle | 20pt | Serif 500 |
| Body | 18pt | Serif 400 |
| Caption | 14pt | Serif 400 |
| Footer | 12pt | Serif 400 |

English stack on PowerPoint:
- Serif: `Charter` -> `Georgia` -> `Palatino`
- Sans: same as serif (single-font-per-page rule)

### Nine standard layouts

1. **Cover**: parchment background, centered display title + brand-colored short line + subtitle / author / date
2. **Contents**: parchment, left-aligned `01  Chapter title` (number serif brand-colored)
3. **Chapter divider**: full brand ink-blue background, centered white title - the **only** fully chromatic slide in the deck
4. **Content slide**: eyebrow (serif stone) + core claim (serif near-black) + brand line + body (serif dark-warm)
5. **Data slide**: top takeaway + 2-4 metric cards (big number serif brand + small label serif olive)
6. **Comparison**: eyebrow + left column (muted, OLIVE/STONE) vs. right column (full-weight, DARK_WARM/NEAR_BLACK), separated by a 1pt BORDER warm-gray vertical divider. Left = "Before/Old/Problem"; right = "After/New/Solution". Use `comparison_slide()`.
7. **Pipeline**: eyebrow + title + serif numerals 01/02/03 + step title + step description, laid out in equal-width columns. All steps visible at once (no click-reveal). Use `pipeline_slide()`.
8. **Quote**: parchment, minimal, centered serif quote + `- Source`
9. **Closing**: parchment, centered "Thank you / Q&A / Contact"

### Template-bound PPTX inventory

Use this only when the user provides a real PPTX or brand template and explicitly asks to preserve its layout system. First inspect the template visually, identify the few reusable layout families, and map each planned section to one existing slide family. Then edit content while preserving the template's shape structure. Do not run this inventory step for Kami's default WeasyPrint or Marp paths; those already have fixed template contracts.

### Script skeleton

Full working example in `assets/templates/slides-en.py`. Key bits:

```python
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN

PARCHMENT = RGBColor(0xf5, 0xf4, 0xed)
BRAND     = RGBColor(0x1B, 0x36, 0x5D)
SERIF = "Charter"
SANS  = SERIF

prs = Presentation()
prs.slide_width  = Inches(13.33)
prs.slide_height = Inches(7.5)

def blank_slide():
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    bg = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE,
                                 0, 0, prs.slide_width, prs.slide_height)
    bg.fill.solid(); bg.fill.fore_color.rgb = PARCHMENT
    bg.line.fill.background(); bg.shadow.inherit = False
    return slide
```

### PPT notes

1. **One idea per slide** - if it runs over three lines, split it
2. **No default PowerPoint template** - it's cool-blue-gray, clashes with parchment
3. **Animations**: none by default. When motion carries meaning, use `fade` only
4. **Export to PDF** for sharing - cross-machine consistency is better than .pptx
 - macOS: Keynote -> Export to PDF
 - Linux: `libreoffice --headless --convert-to pdf output.pptx`

### PPTX delivery check

A generated PPTX is complete only after it has been opened in presentation software
or exported to PDF and inspected. Pass when the intended Kami font family remains
present, with no silent substitution to Calibri, Aptos, or another presentation
default; no text overflows or crops; all content stays inside the safe zone; and page
numbers remain intact. A successful `python-pptx` save is not delivery evidence.

### Slide scale rules (from production decks)

Print and slide share the same palette and serif, but sizing is different.
One rule covers most adjustments: **macro spacing x1.6, micro details x0.5** (letter-spacing, border weight, border-radius).

| Item | Print | Slide | Why |
|---|---|---|---|
| Container | A4 portrait | 1920x1080 or A4 landscape | Fixed ratio, never `100vw x 100vh` |
| Title size | 30-34pt | 48-64pt | Projection needs larger display |
| Slide padding | N/A | 72-80px top, 80px sides | Less than 72px top feels cramped |
| Eyebrow tracking | 0.5-1pt | 3px max | Print tracking looks scattered at slide scale |
| Display tracking | 0 to -0.2pt | -0.5pt | Tighten large titles to prevent letter gaps |
| Header gap | 8-14pt | 36px+ between rule and H1 | Below 36px the rule looks like an underline |
| Line-height titles | 1.1-1.3 | 1.3 minimum | CJK characters collide below 1.3 at slide sizes |
| Code blocks | Full runnable code | Pseudocode + `.hl` keywords | Slide code is for structure, not execution |
| Images | Inline with text | `width:100%; object-fit:contain; max-height:780px` | Avoid fixed height that clips different ratios |
| Footer | Per-template | Single component, CSS-injected text | Prevents drift across 50+ slides |
| Punctuation | Standard | Use ` - ` for short joins, `<ol>` for parallel items | CJK commas break visual rhythm at slide scale |

---

## Part 2.5 · Markdown -> Marp (variant deck path)

Marp is the third rendering path, used only when the user explicitly asks for Marp / markdown slides / a deck that lives in a `.md` file. The repo does **not** declare `marp-cli` as a dependency; install it on the user's machine.

### Install

Use the `npx @marp-team/marp-cli@latest ...` form below for zero-install. For repeat use, install via `npm i -g @marp-team/marp-cli` or `brew install marp-cli` (see [marp-cli docs](https://github.com/marp-team/marp-cli)). Kami's build pipeline (`build.py` / `package-skill.sh`) does not call `marp`.

### Files

| Asset | Path |
|---|---|
| CJK theme (CN, JP/KO best-effort) | `assets/templates/marp/slides-marp.css` (theme name: `kami`) |
| EN theme | `assets/templates/marp/slides-marp-en.css` (theme name: `kami-en`) |
| CJK sample deck | `assets/templates/marp/slides-marp.md` |
| EN sample deck | `assets/templates/marp/slides-marp-en.md` |

### Render commands

Run from the repo root so input paths resolve. **Input file must come before `--theme-set`**; `--theme-set` is a yargs array option and will swallow any positional arg that follows it.

**Font path caveat**: Marp inlines the theme CSS into the output HTML verbatim. The `@font-face` `url("../../fonts/...")` paths in the theme therefore resolve relative to the *output file location*, not the theme CSS location. When the output sits inside the repo (e.g. `-o assets/examples/kami.html`), the relative path matches and local Tsanger / Charter loads. When the output sits elsewhere (e.g. `-o /tmp/kami.html`), the relative path misses and the browser falls back to the jsDelivr CDN URL declared alongside each local one. This needs network. This differs from WeasyPrint, where CSS paths resolve relative to the input HTML.

```bash
# HTML preview (no Chromium needed; zero external download)
npx @marp-team/marp-cli@latest \
  assets/templates/marp/slides-marp.md \
  --theme-set assets/templates/marp \
  -o /tmp/kami-cn.html

# PDF (needs Chromium; see "Browser strategy" below)
npx @marp-team/marp-cli@latest \
  assets/templates/marp/slides-marp.md \
  --theme-set assets/templates/marp \
  --pdf --allow-local-files \
  -o /tmp/kami-cn.pdf

# PPTX (Chromium-rendered; not a python-pptx editable deck)
npx @marp-team/marp-cli@latest \
  assets/templates/marp/slides-marp.md \
  --theme-set assets/templates/marp \
  --pptx --allow-local-files \
  -o /tmp/kami-cn.pptx
```

`--theme-set` points at the directory; Marp picks up every `.css` in there. `--allow-local-files` is required for PDF / PPTX so the renderer may read the local font files referenced by `@font-face` URLs.

### Browser strategy (only for PDF / PPTX)

HTML output is pure Node and needs no browser. PDF / PPTX rendering goes through a headless browser. Three options, lightest first:

| Strategy | Setup | Cost |
|---|---|---|
| **HTML only, view in browser** | Use the HTML command above; open in any browser; export to PDF from the browser's print dialog if needed | 0 MB |
| **Reuse a local Chromium-family browser** | Set `PUPPETEER_EXECUTABLE_PATH` to the absolute path of an installed Chrome, Edge, Brave, Arc, or Chromium binary. Marp also honours `--browser chrome` / `edge` / `firefox` with `--browser-path`. | 0 MB (assumes the browser is already installed) |
| **Let Marp download its own Chromium** | First run of `--pdf` / `--pptx` triggers Puppeteer to fetch a pinned Chromium build (~150 MB to `~/.cache/puppeteer/`) | ~150 MB, one-time |

For light verification of the theme and sample deck, prefer the HTML path.

### Marp gotchas

| Symptom | Cause | Fix |
|---|---|---|
| Two page numbers per slide | Deck pinned a `.page-num` element and also set `paginate: true` | Pick one; the theme injects pagination via `section::after` |
| `position: absolute` does not pin `.co` | A child `<div>` overrode `position: relative` on the section | Marp themes already set `section { position: relative }`; do not override it per slide |
| PDF / PPTX export hangs on first run | Marp is downloading Chromium | Network-restricted environments need `PUPPETEER_EXECUTABLE_PATH` to a pre-installed Chrome |
| Markdown inside `<div class="c2">` renders as a literal HTML block | Missing blank line between the `<div>` and the Markdown body | Always leave a blank line above and below Markdown inside an HTML wrapper |

---

## Part 3 · Verify & Debug

### The loop (mandatory after every change)

```bash
# Filled document: every gate, the render, page images, one verdict
python3 scripts/build.py --deliver doc.html content.json

# Template work: build one target through render.py
python3 scripts/build.py one-pager
```

Both go through `scripts/render.py`, which also renders math, highlights code, and stamps PDF metadata. Call WeasyPrint directly only to isolate a suspected WeasyPrint bug, and never ship that output:

```bash
# Debug isolation only: raw WeasyPrint, no math, highlighting, or metadata
python3 -c "from weasyprint import HTML; HTML('doc.html').write_pdf('raw.pdf')"
```

**Not verified = not done.**

### Did the font actually load?

```bash
python3 scripts/build.py --check-fonts output.pdf   # verdict, from the PDF's span table
pdffonts output.pdf                                 # raw font table, if you want to look yourself
```

`--check-fonts` reads which family drew the body ideographs and fails on two
states `pdffonts` will not tell you apart: a sans substitution (the page reads
fine and looks cheap), and CJK text split across two families (per-glyph
fontconfig fallback, which breaks single words down the middle). Prefer it over
reading the font table by eye, and never sign off a CJK deliverable without it.

If the output shows `DejaVuSerif` / `Bitstream Vera` - your specified font didn't load, fell through to system ultimate fallback. Expected: `Charter`, `Georgia`, `TsangerJinKai02`, or a Japanese Mincho face such as `YuMincho`, `Hiragino-Mincho`, `Noto-Serif-CJK-JP`, or `Source-Han-Serif-JP`.

### One-step build + validate

Project script `scripts/build.py` is the productized version of the three-step loop:

```bash
python3 scripts/build.py               # all registered examples
python3 scripts/build.py resume-en     # one target + page count + fonts
python3 scripts/build.py --check       # scan for CSS rule violations
python3 scripts/build.py --check-density       # warn on pages with >25% trailing whitespace
python3 scripts/build.py --check-markdown output.pdf  # scan for raw Markdown markers
python3 scripts/build.py --check-content content.json filled.html  # content IR schema + coverage
python3 scripts/build.py --check-visual output.pdf    # page PNGs + perceptual review checklist
```

For long-doc templates, keep TOC entries as links to stable chapter ids. The page
number is generated with CSS `target-counter()` at render time, so content edits
do not require hand-updating page numbers.

### Page overflow (constrained templates)

When a constrained template exceeds its page ceiling, treat content as the primary
repair surface; use Part 4 pitfall "Hard-limit overflow" for the proven priority
order. The result must pass both checks:

```bash
python3 scripts/build.py --check
python3 scripts/build.py --verify
```

### Hi-res visual inspection

```bash
pdftoppm -png -r 160 output.pdf preview      # standard
pdftoppm -png -r 300 output.pdf preview      # detail bugs
pdftoppm -png -r 400 output.pdf preview      # extreme detail (tag double-rect check)
```

### 5-point pre-ship review

A successful render is not enough. Scan these before delivery:

| Dimension | Pass standard |
|---|---|
| Fact accuracy | Numbers, dates, versions, funding, specs, and market facts have sources; uncertainty is written as magnitude or marked as missing |
| Content structure | Headlines read as a summary; each paragraph opens with a claim; no ceremonial filler |
| Material coverage | Branded docs include logo, product image, or UI screenshot coverage; missing materials are clearly marked |
| Typographic detail | Fonts load correctly, line-height stays in spec, emphasis only marks numbers or distinctive phrases, tag backgrounds are solid hex |
| PDF readiness | Page count fits, placeholders are replaced, visual inspection shows no overflow, overlap, or broken page breaks |

If any row fails, fix it before delivery.

### Static product site pre-ship review

Run this when the deliverable is a landing page, product site, or hosted showcase rather than a PDF:

| Dimension | Pass standard |
|---|---|
| Runtime preview | Serve locally and inspect desktop plus 375px mobile. The first viewport shows the product category, real asset, CTA, and a hint of the next section. |
| Generated output | If pages come from `template + i18n + content`, run the generator's check mode. It must fail on missing keys and committed output drift. |
| Public metadata | Canonical, hreflang, `og:locale`, social image, JSON-LD, robots, sitemap, `llms.txt`, and `llms-full.txt` all reflect the shipped locale set. |
| Copy sync | Product positioning, price, version, install path, support link, FAQ, `llms.txt`, and `llms-full.txt` carry the same factual claims in every locale. |
| Asset reality | Screenshots are real product surfaces and every image path resolves from the repo or a public URL. No `/Users`, `file://`, or sibling-repo relative paths. |
| Screenshot fit | Hero, gallery, feature, and social-image slots use stable ratios. UI text, numbers, prompts, and controls are not cropped away for aesthetics. |
| Motion fallback | Gallery rotation, entrance animation, or custom transitions respect `prefers-reduced-motion`; a still page remains readable with motion disabled. |
| Link surface | Primary CTA, download, releases, docs, help, social links, and internal locale links resolve. Any named release or download artifact exists. |

If the site has only one or two locales, hand-maintained static pages are acceptable. For three or more locales, prefer a generator with a drift check over repeated manual edits.

---

## Part 4 · Known pitfalls

Every entry below came from a real failure. Check here first when something looks wrong.

Severity scale: **(P0)** render-breaking, must fix before delivery. **(P1)** breaks the design contract (rhythm, spec). **(P2)** visible to a careful reader, but not blocking. **(P3)** operational: affects workflow, not visual output.

### 1. (P0) Tag / Badge double-rectangle bug (the worst)

**Symptom**: PDFs show two concentric rectangles on tag backgrounds at zoom - an outer softer one and an inner tighter one. Especially visible on mobile PDF viewers.

**Root cause**: WeasyPrint renders `rgba(..., 0.xx)` by compositing the **padding area** and the **glyph pixel area** independently. Glyph anti-aliasing stacks alpha differently, creating the second visible edge.

**Fix**: Tag backgrounds must be solid hex. No rgba.

```css
/* avoid */ .tag { background: rgba(27, 54, 93, 0.18); }
/* use   */ .tag { background: var(--tag-bg); }
```

Kami ships two registered tints for this, `--tag-bg` and `--brand-tint`; `references/design.md` «Tags» owns which one to pick. A tint outside those two needs a `tokens.json` entry first, or `scripts/tokens.py` fails the sync guard.

If you genuinely need a texture, `linear-gradient` is safe engineering-wise (the tag rasterizes as one bitmap, no alpha compositing), but at tag size it oversells every time. Solid is the answer.

### 2. (P0) Thin border + radius = double circle

**Symptom**: `border: 0.4pt solid ...` + `border-radius: 2pt` shows two parallel arcs on zoom.

**Root cause**: WeasyPrint strokes border inner and outer paths separately when `< 1pt` + rounded corners - at thin widths they can't overlap.

**Fix (pick one)**:
1. Use background fill instead (preferred, design-consistent)
2. Border ≥ 1pt
3. Drop `border-radius`

### 3. (P1) 2-page hard-limit overflow

For resume, one-pager, and other length-capped docs.

**Common causes**: font fallback, content added, font-size bumped by accident, line-height pushed from 1.4 to 1.6.

**Diagnose**: `pdffonts output.pdf` to verify what actually loaded.

**Fix (priority)**:
1. Cut redundant qualifiers ("deeply researched" -> "researched")
2. Merge related data points in the same section
3. Drop non-essential items whole (not piecemeal)
4. Reduce section spacing (use sparingly - affects global rhythm)
5. Last resort: shrink font by 0.1-0.2pt

**Don't**: cut cover / education / timeline structural blocks; cut emphasis (resume becomes flat).

**5-project high-density layout** (when content legitimately needs 5 projects on page 1): add `class="resume--dense"` to `<body>`. This activates a built-in CSS variant that applies the following adjustments without touching any content:

| Property | Default | Dense |
|---|---|---|
| `body font-size` | 9.2pt | 9pt |
| `.proj-text line-height` | 1.40 | 1.38 (CN) / 1.40 (EN) |
| `.tl-body font-size` | 9pt | 8.5pt (CN only) |
| `.section-title margin-top` | 5mm | 3.5mm |

Apply dense mode only when the 4-project layout already overflows. Do not use it as a default; the visual rhythm is noticeably tighter.

Resume templates use section-title bottom rules and borderless project rows. Do not reintroduce project `border-top` as a density aid; it creates double rules below headings and orphan rules at page breaks.

### 4. (P1) Font fallback causes page count inconsistency

**Symptom**: 2 pages locally, 4 pages in CI / on server.

**Root cause**: font file neither alongside HTML nor system-installed.

**Fix**:

```bash
# Preferred: multi-source download script (retries, size validation).
# Lands fonts in ${XDG_DATA_HOME:-~/.local/share}/fonts/kami (fontconfig-scanned,
# outside the skill dir), then runs fc-cache. A repository checkout first copies
# missing or truncated fonts from root assets/fonts into the skill's ignored assets/fonts;
# downloads are needed only when usable fonts remain missing.
bash scripts/ensure-fonts.sh

# Or put .ttf alongside the HTML
cp TsangerJinKai02-W04.ttf workspace/

# macOS fallback font
brew install --cask font-source-han-serif-sc

# Linux system install
apt install fonts-noto-cjk
mkdir -p ~/.fonts && cp *.ttf ~/.fonts/ && fc-cache -f
```

### 4.1 (P1) Latin-first font stack splits CJK inside inline SVG

**Symptom**: labels inside an embedded SVG render in two typefaces at once,
often mid-word (`提交` in one face, `请` in another). The stack names a CJK
family, and a rendered PDF still shows two.

**Root cause**: for SVG text, a leading Latin serif (`Charter, Georgia, ...`)
ends the CSS stack walk. Characters it has no glyph for go to fontconfig
per glyph rather than continuing down the declared list, so the CJK families
written after it never get their turn and each ideograph lands wherever
fontconfig prefers (`Hiragino-Mincho` for some, `Songti-SC` for others).

**Fix**: in SVG `text` rules, put the CJK families first and let Latin faces
trail. `@font-face` fonts do resolve inside inline SVG, so `TsangerJinKai02`
leading the stack draws both scripts from one family. The walk stops at the
first family for a missing font too: WeasyPrint's SVG renderer tries only the
first family of a quoted list (verified on 68.1 and 70.0), so `"Source Han Serif TC",
"Songti TC"` on a machine without Source Han Serif TC never reaches Songti TC. An unquoted list (`Source Han Serif TC, Songti TC,
serif`) is split and walked, which is why `scripts/hant.py` writes its names
unquoted:

```css
/* wrong: CJK after Latin, splits per glyph */
text { font-family: Charter, Georgia, "TsangerJinKai02", "Songti SC", serif; }
/* right: one family draws the whole label */
text { font-family: "TsangerJinKai02", "Source Han Serif SC", "Songti SC", Charter, Georgia, serif; }
```

`--check-fonts` catches this state; a page render at normal size usually does not.

### 5. (P2) CJK and Latin crowding (Chinese mode only)

**Symptom**: "125.4k GitHub Stars" - k and G feel glued.

**Wrong fixes**: hand-added `&nbsp;` / `margin-left: 2mm` (misaligns adjacent elements).

**Right fix**: separate spans and let flex `gap` carry the space, never a hand-added `&nbsp;` or margin:

```html
<div class="metric">
  <span class="metric-value">125.4k</span>
  <span class="metric-label">GitHub Stars</span>
</div>
```
```css
.metric { display: flex; gap: 6pt; }   /* direction: see pitfall #20 */
```

The `gap` is the fix here. Whether the pair sits inline or stacks is a separate call, and pitfall #20 owns it.

### 6. (P2) Full-width vs half-width spaces (Chinese mode)

- **Between Chinese characters**: U+3000 full-width space + `·` + space
- **Between Latin words**: half-width space + `·` + space
- **Mixed**: prefer flex gap, don't hand-type spaces

### 7. (P2) Thousands / percent / arrows - be consistent

**Symptom**: one document mixes thousands separators, spaced percent signs, or
multiple arrow glyphs. `writing.md` "Number formatting" is the source of truth.

Self-check:
```bash
grep -oE '→|⟶|⇒' doc.html | sort | uniq -c
grep -oE '[0-9]{4,}' doc.html | sort -u
```

### 8. (P2) Too much / too little emphasis

**Symptom**: four or five ink-blue runs in one line create visual fatigue, while a
long prose section with none has no scan handle. `writing.md` "Emphasis rhythm" is
the source of truth for density and eligible content.

### 9. (P0) `height: 100vh` doesn't work

**Symptom**: full-bleed cover using `height: 100vh` renders empty.

**Root cause**: viewport units are undefined in WeasyPrint's `@page` context.

**Fix**:

```css
.cover {
  min-height: 257mm;                   /* A4 height 297 - 40mm margins */
  display: flex;
  flex-direction: column;
  justify-content: center;
}
```

### 10. (P1) `break-inside` fails inside flex

**Symptom**: `.card { break-inside: avoid }` still splits across pages.

**Root cause**: WeasyPrint's flex/grid `break-inside` support on direct children is incomplete.

**Fix**: wrap the flex item in an extra block:

```html
<div class="row">
  <div class="card-wrapper"><div class="card">...</div></div>
</div>
```
```css
.row { display: flex; }
.card-wrapper { break-inside: avoid; }
```

### 11. (P3) Hide page number on the first page

```css
@page:first {
  @top-right { content: ""; }
}
```

### 12. (P2) Printed white margin around the page

**Symptom**: printing produces a white border even though `background` is set.

**Root cause**: default `@page background` only covers the content area, not the margin.

**Fix**:

```css
@page {
  size: A4; margin: 20mm;
  background: #f5f4ed;    /* extends past margins */
}
```

### 13. (P2) Blurry images

**Symptom**: images in PDF look soft.

**Root cause**: WeasyPrint renders at source pixel density. A4 @ 300 dpi = 2480 × 3508 pixels.

**Fix**: source images at 2x or 3x.

### 14. (P0) SVG marker `orient="auto"` ignored

**Symptom**: SVG arrows using `<marker orient="auto">` or `orient="auto-start-reverse"` all point right (the marker's default drawing direction), regardless of the path's tangent angle.

**Root cause**: WeasyPrint's SVG renderer does not support the `orient="auto"` attribute on markers. The marker is always drawn at 0°.

**Fix**: skip `<marker>` entirely. Draw each arrowhead as a manual chevron `<path>` at the endpoint, with the direction hardcoded.

```xml
<!-- Bad: marker arrow, WeasyPrint renders all pointing right -->
<defs>
  <marker id="a" orient="auto" ...>
    <path d="M2 1L8 5L2 9" .../>
  </marker>
</defs>
<path d="M 440 52 Q 568 52 568 244" marker-end="url(#a)"/>

<!-- Good: manual chevron, direction per endpoint -->
<path d="M 440 52 Q 568 52 568 244" fill="none" stroke="#504e49" stroke-width="1.5"/>
<path d="M 560 236 L 568 244 L 576 236" fill="none" stroke="#504e49" stroke-width="1.5"
      stroke-linecap="round" stroke-linejoin="round"/>
```

Chevron templates (tip at endpoint, 8px arm length):

| Direction | chevron path |
|---|---|
| down | `M (x-8) (y-8) L x y L (x+8) (y-8)` |
| left | `M (x+8) (y-8) L x y L (x+8) (y+8)` |
| up | `M (x-8) (y+8) L x y L (x+8) (y+8)` |
| right | `M (x-8) (y-8) L x y L (x-8) (y+8)` |

### 15. (P1) Slide letter-spacing must be halved

**Symptom**: Slide text looks "scattered" or over-spaced when print letter-spacing values (e.g. `letter-spacing: 8px`) are used directly.

**Root cause**: Print letter-spacing values are tuned for small sizes (8-12pt). At slide sizes (48-64px), the same absolute value gets multiplied out of control.

**Fix**: Slide letter-spacing = print value / 2. Mono fonts are exempt (fixed-width by nature, no extra tracking needed).

```css
/* Print eyebrow */
.eyebrow { letter-spacing: 6px; }

/* Slide eyebrow */
.slide .eyebrow { letter-spacing: 3px; }   /* halved */
```

### 16. (P1) Figure SVG `max-height` starves width

**Symptom**: An inline `<svg>` inside `<figure>` sits at less than the page content width, leaving a visible parchment gap on the right while the surrounding title and table run full-width.

**Root cause**: When a figure SVG declares `max-height` without an explicit `width: 100%`, browsers and WeasyPrint preserve the viewBox aspect ratio and shrink width to honor the height cap. For wide viewBoxes (aspect > 1.5) the height cap becomes the binding constraint and width starves.

**Fix**: Always set both width and height behavior. Use `max-height` only as a safety ceiling, never as the primary sizing rule.

```css
/* avoid */
figure svg { max-height: 45mm; }

/* use */
figure svg { width: 100%; height: auto; max-height: 70mm; }
```

Quick check: if `viewBox` aspect ratio × current `max-height` < page content width, the chart is starved. Bump `max-height` until `aspect × max-height >= content width` or remove the cap.

### 17. (P1) Multi-column metric labels need word-budget discipline

**Symptom**: One or more labels in a 3-4 column metric row wrap to two lines while siblings stay on one line, breaking the baseline rhythm and pushing the value/label out of alignment.

**Root cause**: Equal-flex columns at gap `G` and content width `W` give each column `(W - G·(N-1)) / N` total. After the metric value (typically 12-18mm at 14pt Charter), the label has only what remains - usually 22-28mm for 4 columns at 184mm width.

**Fix**: Plan label text against the available budget before layout. Approximate budget at 9pt Charter:

| Layout | Per-column total | Label budget after value | Soft char limit |
|---|---|---|---|
| 4 columns, gap 7mm, content 184mm | ~40.7mm | ~22-26mm | 14-18 chars |
| 3 columns, gap 7mm, content 184mm | ~56.7mm | ~38-42mm | 24-28 chars |
| 4 columns, gap 5mm, content 184mm | ~42.7mm | ~24-28mm | 16-20 chars |

When the natural label is longer (e.g. "Falcon launches, lifetime"), trim to the data essential ("Falcon launches"); supporting context belongs in nearby body copy, not in a metric chip.

### 18. (P2) Multi-column body density imbalance

**Symptom**: A row of N parallel body columns (timeline cards, conviction cards, feature blurbs) renders with one column wrapping to one extra line while the others wrap evenly. The rhythm reads broken even when each individual cell looks fine.

**Root cause**: Equal-width columns wrap based on character count, not "ideas". A column with 88 chars next to siblings at 67-81 chars at the same width will spill to one extra line.

**Fix**: Hold body length within ±10 chars across parallel columns of the same width. Rewrite the longest column tighter rather than padding the shorter ones.

```text
col 1:  67 chars (2 lines)
col 2:  81 chars (2 lines)
col 3:  88 chars (3 lines)   <- breaks rhythm
col 3': 66 chars (2 lines)   <- fixed by trimming "general intelligence" -> "AGI"
```

### 19. (P0) Demo / template HTML must reference assets inside the kami repo

**Symptom**: Image slot renders as a missing-image placeholder in the PDF; rendered demo PNG looks empty where a screenshot should be.

**Root cause**: An `<img src="../../../sibling-project/asset.jpg">` reaches outside the kami repo. The path resolves on the maintainer's laptop where the sibling project happens to be checked out, but breaks for every other user, breaks the packaged skill ZIP, and breaks any CI that doesn't recreate the maintainer's working tree.

**Fix**: Every image referenced by a demo or template must live under the demo's `images/` folder (`site/assets/demos/images/` in this repository) or `site/assets/illustrations/`. Copy the source into the kami repo, then reference it with a relative path inside the repo.

```html
<!-- avoid -->
<img src="../../../kaku/website/public/shots/kaku-light.webp" alt="...">

<!-- use -->
<img src="images/kaku-hero.jpg" alt="...">
```

Quick check before building any demo: `rg 'src="(\.\./|/Users/|file://)' site/assets/demos/` should return zero matches.

### 20. (P1) Metric row baseline-align breaks when labels wrap

**Symptom**: A horizontal metric row with `display: flex; align-items: baseline` looks fine when every label is one line, but ugly when one label wraps. The big number "10×" sits at the visual top of its column while the multi-line label flows downward; sibling columns with one-line labels look balanced but the wrapped column reads broken.

**Root cause**: `align-items: baseline` aligns each metric to the **first line** of its label. When labels have different line counts, the visible heights differ but the numbers all sit at the same baseline (= top), making the row look uneven.

**Fix**: Stack vertically (`flex-direction: column`). All numbers sit on the same top edge, all labels start at the same y below the numbers, and label wrap only extends each column's bottom, which is invisible on a slide / page.

```css
/* inline: only when every label in the row is short and single-line */
.metric { display: flex; align-items: baseline; }

/* stack: the default whenever a label can wrap */
.metric { display: flex; flex-direction: column; }
```

The shipped templates follow exactly that split: `equity-report*.html` keeps the inline baseline because its labels are fixed short strings, while every `landing-page*.html` stacks, because a screen label is translated, retitled, and read at 375px. On slides, where metrics sit on a baseline strip at the bottom, one multi-line label among three columns is enough to break the rhythm, so stack there too.

### 21. (P2) Slide bullets: prefer short numerals or `•` over en-dash

**Symptom**: A bulleted list on a slide with `–` (en-dash, U+2013) markers reads heavy and informal, especially at large slide font sizes (12-14pt body). The en-dash is wide and creates a visible gap between marker and text.

**Root cause**: En-dash is a typographic primitive, originally meant for ranges ("1995–1997"), not list markers. At slide scale it looks elongated and informal.

**Fix**: Use either small numerals (`1.`, `2.`, `3.`) or a standard bullet (`•`) in brand color. Numerals are tighter horizontally and signal sequence; bullets are tightest visually and signal "items in any order".

```css
/* avoid on slides: en-dash reads informal at large font sizes */
ul.pts li::before { content: "\2013"; }

/* use: numbered, mono digit, brand color */
ul.pts { counter-reset: pts; }
ul.pts li { counter-increment: pts; padding-left: 18pt; }
ul.pts li::before {
  content: counter(pts) ".";
  color: var(--brand);
  font-weight: 500;
  font-variant-numeric: tabular-nums;
}
```

Print docs (long-doc, equity-report) keep the editorial en-dash style; slides switch to numerals.

### 22. (P1) Section body text is narrower than the page

**Symptom**: manifesto, section-lede, or similar body copy renders as a narrow inset
column while adjacent content fills the page.

**Root cause**: a generic article-style `max-width` was applied to body text. Kami
section copy should fill the `.page` container; `.type-sample` and
`.footer .colophon` are the intentional exceptions.

**Fix**: remove the body-copy `max-width` rather than widening it with another local
override. Keep the two named exceptions constrained.

### 23. (P3) Diagram fixes drift from public-site miniatures

**Symptom**: a diagram template renders correctly, but the public showcase still
shows the old geometry or styling.

**Root cause**: each public locale page contains a separate inline mini SVG; it is
not generated from `assets/diagrams/*.html`.

**Done when**: every visual change to a diagram template is also present in the
matching mini SVG in `index.html`, `index-zh.html`, `index-ja.html`, `index-ko.html`,
and `index-tw.html`.

### 24. (P0) `target-counter` resolves to 0 on a flex anchor (WeasyPrint 70.0)

**Symptom**: every long-doc TOC page number renders as `0`. WeasyPrint 69.0 and
earlier print the correct numbers from the same HTML; 70.0 (2026-09-08) does not.

**Root cause**: WeasyPrint 70.0 fails to resolve `target-counter()` in an
`::after` whose originating `<a>` is itself `display: flex`. The unresolved
counter still prints a well-formed `0`, so no text-level gate objects.

**Fix**: keep the anchor a block and float the numeral instead of relying on
flex alignment:

```css
.toc-title {
  flex: 1;             /* still a flex ITEM of .toc-item, which is fine */
  display: block;      /* must not be a flex CONTAINER itself */
}
.toc-title[href]::after {
  content: target-counter(attr(href), page);
  float: right;        /* not margin-left: auto */
}
```

**Done when**: `python3 scripts/build.py --verify long-doc` passes. That target
cross-checks each rendered numeral against the page its TOC row links to, so a
`0` fails the build instead of shipping. Same substitution as the resume badge
fix (`float: right` over `margin-left: auto`): it is stable across versions.
Match each numeral to its containing row, not every link to the same destination:
body cross-references are not TOC rows, and repeated destinations still need
separate checks. CI renders all three long-doc variants even without a page ceiling.

### 25. Korean text is extractable but absent in a PDF preview

**Symptom**: a Source Han Serif K PDF contains Korean text and embeds its font,
but MuPDF/PyMuPDF and macOS Preview (Quartz) show only Latin text and page
numbers, while Poppler (`pdftoppm`) draws the Korean.

**Root cause**: WeasyPrint subsets a CID-keyed CFF font (the `.otf` build of
Source Han Serif K) into a PDF font that MuPDF and Quartz draw blank; see the
[upstream issue](https://github.com/Kozea/WeasyPrint/issues/1593). The same
glyphs as TrueType outlines subset cleanly for every reader. `full_fonts=True`
also renders, but embeds about 7 MB per weight.

**Fix (in the pipeline)**: `render.render_pdf` runs `scripts/font_compat.py`,
which rewrites every `@font-face` source that resolves to a local CID-keyed CFF
file (relative path, `file://`, or a CDN URL whose file is in the skill font
directory or the `ensure-fonts.sh` directory) to a TrueType copy converted once
with fontTools and cached under `${XDG_CACHE_HOME:-~/.cache}/kami/fonts`. The first
Korean render takes about 10 seconds per weight; later ones read the cache.
A font fontconfig resolves by family name never passes through `@font-face` and is
not converted, so keep the template's `@font-face` path working
(`bash scripts/ensure-fonts.sh`).

**Verification**: render the page with MuPDF (`build.py --check-visual`) and open
the PDF in Preview; Poppler alone proves nothing, because it drew the broken file
too. Text extraction and embedded font names do not establish visible glyphs.

### 26. Korean breaks inside words

**Symptom**: Korean lines end mid-word ("파이프라 / 인을"), although Korean
breaks between words (eojeol) and the templates' CSS says so.

**Root cause**: WeasyPrint ignores `word-break: keep-all`.

**Fix (in the pipeline)**: `render.render_pdf` runs `scripts/hangul.py`, which puts
U+2060 WORD JOINER between the characters of each Hangul-bearing word in the copy
it renders (never in the source), across inline tags such as
`<span class="hl">18개 팀</span>이`. The joiner draws nothing and does not reach the
PDF text layer. Words over 16 characters stay breakable so narrow cells wrap
instead of overflowing. Do not add joiners or per-word spans to the source HTML.
Word-level breaking fills lines less tightly than syllable breaking, so a Korean
document near its page ceiling may need a shorter line or two.

### 27. A grid item set to `grid-column: 1 / -1` stays in one column

**Symptom**: an item meant to span a two-column grid in a PDF stays in the first
column, so whatever sits at its right edge (a star count, a date) stops mid-page.

**Root cause**: WeasyPrint ignores negative grid line numbers; the declaration is
dropped without a warning. Browsers honor it, so a landing page looks right.

**Fix**: in PDF templates span by count (`grid-column: span 2`) or with positive
lines (`1 / 3`). The resume templates use `.os-item:only-child { grid-column: span 2; }`
so a single open-source project spans the row.

---

## Part 5 · HTML -> DOCX (pandoc + SVG-to-PNG)

PDF is the delivery format; DOCX is the collaboration format. For proposal / report scenarios where the recipient needs to edit, comment, or forward to their team, ship a `.docx` alongside the PDF.

### Why two-step

`pandoc input.html -o output.docx` looks straightforward, but inline `<svg>` blocks fail Word's OOXML validation. Word treats them as unknown content and either drops them or refuses to open the file. The fix is to bake every SVG to PNG first, swap the `<svg>` blocks for `<img>` tags, then run pandoc.

### Install

```bash
# macOS
brew install pandoc librsvg

# Linux
apt install pandoc librsvg2-bin
```

### Workflow

```bash
# 1. Extract every SVG to its own file, ensuring xmlns is set
python3 - << 'EOF'
import re
src = open('input.html').read()
for i, m in enumerate(re.finditer(r'<svg[^>]*>.*?</svg>', src, re.DOTALL)):
    svg = m.group(0)
    if 'xmlns=' not in svg[:200]:
        svg = svg.replace('<svg ', '<svg xmlns="http://www.w3.org/2000/svg" ', 1)
    with open(f'/tmp/diagram-{i}.svg', 'w') as f:
        f.write('<?xml version="1.0"?>\n' + svg)
EOF

# 2. Rasterize each SVG to a wide PNG
for f in /tmp/diagram-*.svg; do
    rsvg-convert "$f" -o "${f%.svg}.png" -w 1600
done

# 3. Replace each <svg>...</svg> in the HTML with <img src="/tmp/diagram-N.png">
#    (do this with the same regex iteration that produced the indices above)

# 4. Convert
pandoc input-with-png.html -o output.docx
```

### What carries over

| Carries over | Lost |
|---|---|
| Headings, body, lists, tables | Grid layouts, custom positioning |
| Brand color on headings, `<strong>`, `.hl` | Subtle borders and shadows |
| PNG figures at full width | SVG editability |
| Page breaks via `<hr class="page-break">` | `@page` margins |

The recipient gets a Word document they can edit text in and replace figures in (drag a new PNG over the existing one). Complex layout differences are expected; the goal is editability, not visual fidelity.

### When not to ship a DOCX

Skip this for resume, one-pager, slides, and portfolio. They are visual artifacts; converting them produces a degraded version with no editability gain. Long-doc / proposal / equity-report are the document types where a DOCX companion has a real audience.
