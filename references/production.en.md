# Production (Build · Verify · Troubleshoot)

The engineering runbook for kami: from HTML / Python templates to PDF / PPTX deliverables. Four parts: **HTML -> PDF** · **Python -> PPTX** · **Verify & Debug** · **15 known pitfalls**.

---

## Part 1 · HTML -> PDF (WeasyPrint)

### Install

```bash
pip install weasyprint pypdf --break-system-packages --quiet
```

Linux first-time:
```bash
apt install -y libpango-1.0-0 libpangoft2-1.0-0 fonts-noto-cjk
```

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
  font-family: "Newsreader";
  src: url("Newsreader-VariableFont.ttf");
}
body { font-family: "Newsreader", serif; }
</style>
```

**No commercial font available**: fallback chains are embedded in every template.

```css
/* English */
font-family: "Newsreader", "Source Serif 4", "Charter",
             Georgia, serif;

/* Chinese */
font-family: "TsangerJinKai02", "Source Han Serif SC",
             "Noto Serif CJK SC", "Songti SC", Georgia, serif;
```

**Font fallback affects page count**. Any font swap requires re-running the page-count check. If it overflows: lower `font-size` first, then tighten margins, then cut content.

### Page spec

```css
@page {
  size: A4;                     /* or 210mm 297mm / A4 landscape / 13in 10in */
  margin: 20mm 22mm;
  background: #f5f4ed;          /* extend past margins to avoid white printed edge */
}
```

### Headers & footers

```css
@page {
  @top-right {
    content: counter(page);
    font-family: serif; font-size: 9pt; color: #87867f;
  }
  @bottom-center {
    content: "{{DOC_NAME}} · {{AUTHOR}}";
    font-size: 8.5pt; color: #87867f;
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
| `::before` / `::after` | | |

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

### Palette (1:1 with design.en.md)

```python
from pptx.dml.color import RGBColor

PARCHMENT   = RGBColor(0xf5, 0xf4, 0xed)
IVORY       = RGBColor(0xfa, 0xf9, 0xf5)
BRAND       = RGBColor(0x1B, 0x36, 0x5D)
NEAR_BLACK  = RGBColor(0x14, 0x14, 0x13)
DARK_WARM   = RGBColor(0x3d, 0x3d, 0x3a)
OLIVE       = RGBColor(0x5e, 0x5d, 0x59)
STONE       = RGBColor(0x87, 0x86, 0x7f)
BORDER_WARM = RGBColor(0xe8, 0xe6, 0xdc)
TAG_BG      = RGBColor(0xee, 0xf2, 0xf7)
```

### Type (bigger than print, optimized for projection)

| Role | Size | Font |
|---|---|---|
| Title | 48pt | Serif 500 |
| Subtitle | 24pt | Sans 400 |
| H2 chapter | 32pt | Serif 500 |
| H3 subtitle | 20pt | Serif 500 |
| Body | 18pt | Sans 400 |
| Caption | 14pt | Sans 400 |
| Footer | 12pt | Sans 400 |

English stack on PowerPoint:
- Serif: `Newsreader` -> `Charter` -> `Georgia`
- Sans: `Inter` -> `Helvetica Neue` -> `Arial`

### Eight standard layouts

1. **Cover**: parchment background, centered display title + brand-colored short line + subtitle / author / date
2. **Contents**: parchment, left-aligned `01  Chapter title` (number serif brand-colored)
3. **Chapter divider**: full brand ink-blue background, centered white title - the **only** fully chromatic slide in the deck
4. **Content slide**: eyebrow (sans stone) + core claim (serif near-black) + brand line + body (sans dark-warm)
5. **Data slide**: top takeaway + 2-4 metric cards (big number serif brand + small label sans olive)
6. **Comparison**: two columns with a 0.5pt warm-gray divider
7. **Quote**: parchment, minimal, centered serif quote + `- Source`
8. **Closing**: parchment, centered "Thank you / Q&A / Contact"

### Script skeleton

Full working example in `assets/templates/slides-en.py`. Key bits:

```python
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN

PARCHMENT = RGBColor(0xf5, 0xf4, 0xed)
BRAND     = RGBColor(0xc9, 0x64, 0x42)
SERIF = "Newsreader"
SANS  = "Inter"

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
3. **Animations**: don't. Parchment is a print aesthetic, not a SaaS demo. At most `fade`
4. **Export to PDF** for sharing - cross-machine consistency is better than .pptx
 - macOS: Keynote -> Export to PDF
 - Linux: `libreoffice --headless --convert-to pdf output.pptx`

---

## Part 3 · Verify & Debug

### The three-step loop (mandatory after every change)

```bash
# 1. Generate
python3 -c "from weasyprint import HTML; HTML('doc.html').write_pdf('out.pdf')"

# 2. Page count
python3 -c "from pypdf import PdfReader; print(len(PdfReader('out.pdf').pages))"

# 3. Visual inspect (when in doubt)
pdftoppm -png -r 300 out.pdf inspect
```

**Not verified = not done.**

### Did the font actually load?

```bash
pdffonts output.pdf
```

If the output shows `DejaVuSerif` / `Bitstream Vera` - your specified font didn't load, fell through to system ultimate fallback. Expected: `Newsreader`, `Charter`, or `TsangerJinKai02`.

### One-step build + validate

Project script `scripts/build.py` is the productized version of the three-step loop:

```bash
python3 scripts/build.py               # all 12 examples
python3 scripts/build.py resume-en     # one target + page count + fonts
python3 scripts/build.py --check       # scan for CSS rule violations
```

### Hi-res visual inspection

```bash
pdftoppm -png -r 160 output.pdf preview      # standard
pdftoppm -png -r 300 output.pdf preview      # detail bugs
pdftoppm -png -r 400 output.pdf preview      # extreme detail (tag double-rect check)
```

---

## Part 4 · 15 known pitfalls

Every entry below came from a real failure. Check here first when something looks wrong.

### 1. Tag / Badge double-rectangle bug (the worst)

**Symptom**: PDFs show two concentric rectangles on tag backgrounds at zoom - an outer softer one and an inner tighter one. Especially visible on mobile PDF viewers.

**Root cause**: WeasyPrint renders `rgba(..., 0.xx)` by compositing the **padding area** and the **glyph pixel area** independently. Glyph anti-aliasing stacks alpha differently, creating the second visible edge.

**Fix**: Tag backgrounds must be solid hex. No rgba.

```css
/* ❌ */ .tag { background: rgba(201, 100, 66, 0.18); }
/* ✅ */ .tag { background: #E4ECF5; }
```

**rgba -> solid conversion** (parchment `#f5f4ed` base + ink-blue `#1B365D`):

| rgba alpha | Solid hex |
|---|---|
| 0.08 | `#EEF2F7` |
| 0.14 | `#E4ECF5` |
| **0.18** | **`#E4ECF5`** ← default |
| 0.22 | `#D0DCE9` |
| 0.30 | `#D6E1EE` |

Formula: `solid_channel = base + (foreground - base) × alpha`. Different base colors (e.g. ivory) need re-computing.

**Want "breathing" texture?** Use `linear-gradient` - the whole tag rasterizes as one bitmap, no alpha compositing:

```css
.tag { background: linear-gradient(to right, #D6E1EE, #E4ECF5 70%, #EEF2F7); }
```

**Aesthetic warning**: gradients work engineering-wise but usually oversell the tag. Priority order: lightest solid (`#EEF2F7`) > standard solid (`#E4ECF5`) > gradient (rarely). If the reader's eye lands on the tag background shape before the text inside - you went too far.

### 2. Thin border + radius = double circle

**Symptom**: `border: 0.4pt solid ...` + `border-radius: 2pt` shows two parallel arcs on zoom.

**Root cause**: WeasyPrint strokes border inner and outer paths separately when `< 1pt` + rounded corners - at thin widths they can't overlap.

**Fix (pick one)**:
1. Use background fill instead (preferred, design-consistent)
2. Border ≥ 1pt
3. Drop `border-radius`

### 3. 2-page hard-limit overflow

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

### 4. Font fallback causes page count inconsistency

**Symptom**: 2 pages locally, 4 pages in CI / on server.

**Root cause**: font file neither alongside HTML nor system-installed.

**Fix**:

```bash
# Put .ttf alongside the HTML
cp Newsreader.ttf workspace/

# Or system install (Linux)
apt install fonts-noto-cjk
mkdir -p ~/.fonts && cp *.ttf ~/.fonts/ && fc-cache -f
```

### 5. CJK and Latin crowding (Chinese mode only)

**Symptom**: "125.4k GitHub Stars" - k and G feel glued.

**Wrong fixes**: hand-added `&nbsp;` / `margin-left: 2mm` (misaligns adjacent elements).

**Right fix**: separate spans with flex gap:

```html
<div class="metric">
  <span class="metric-value">125.4k</span>
  <span class="metric-label">GitHub Stars</span>
</div>
```
```css
.metric { display: flex; align-items: baseline; gap: 6pt; }
```

### 6. Full-width vs half-width spaces (Chinese mode)

- **Between Chinese characters**: U+3000 full-width space + `·` + space
- **Between Latin words**: half-width space + `·` + space
- **Mixed**: prefer flex gap, don't hand-type spaces

### 7. Thousands / percent / arrows - be consistent

| ✅ | ❌ |
|---|---|
| `5,000+` | `5000+` |
| `90%` | `90 %` (pre-space) |
| `->` | `->` / `-&gt;` |

Self-check:
```bash
grep -oE '->|->|⟶|⇒' doc.html | sort | uniq -c
grep -oE '[0-9]{4,}' doc.html | sort -u
```

### 8. Too much / too little emphasis

- Four or five ink-blue runs in one line -> visual fatigue, no focal point
- Entire section with none -> flat, no scan handles

**Rule**: ≤ 2 emphases per line, ≥ 1 per section, only **quantifiable numbers or distinctive phrases** get highlighted - never adjectives.

Healthy ratio: one emphasis per 80-150 words.

### 9. `height: 100vh` doesn't work

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

### 10. `break-inside` fails inside flex

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

### 11. Hide page number on the first page

```css
@page:first {
  @top-right { content: ""; }
}
```

### 12. Printed white margin around the page

**Symptom**: printing produces a white border even though `background` is set.

**Root cause**: default `@page background` only covers the content area, not the margin.

**Fix**:

```css
@page {
  size: A4; margin: 20mm;
  background: #f5f4ed;    /* extends past margins */
}
```

### 13. Blurry images

**Symptom**: images in PDF look soft.

**Root cause**: WeasyPrint renders at source pixel density. A4 @ 300 dpi = 2480 × 3508 pixels.

**Fix**: source images at 2x or 3x.

### 14. Verification loop (catch-all)

```bash
python3 -c "from weasyprint import HTML; HTML('doc.html').write_pdf('out.pdf')"
python3 -c "from pypdf import PdfReader; print(len(PdfReader('out.pdf').pages))"
pdftoppm -png -r 300 out.pdf inspect    # when in doubt
```

**Not verified = not done.**

### 15. SVG marker `orient="auto"` ignored

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
<path d="M 440 52 Q 568 52 568 244" fill="none" stroke="#5e5d59" stroke-width="1.5"/>
<path d="M 560 236 L 568 244 L 576 236" fill="none" stroke="#5e5d59" stroke-width="1.5"
      stroke-linecap="round" stroke-linejoin="round"/>
```

Chevron templates (tip at endpoint, 8px arm length):

| Direction | chevron path |
|---|---|
| down | `M (x-8) (y-8) L x y L (x+8) (y-8)` |
| left | `M (x+8) (y-8) L x y L (x+8) (y+8)` |
| up | `M (x-8) (y+8) L x y L (x+8) (y+8)` |
| right | `M (x-8) (y-8) L x y L (x-8) (y+8)` |

### 16. Slide letter-spacing must be halved

**Symptom**: Slide text looks "scattered" or over-spaced when print letter-spacing values (e.g. `letter-spacing: 8px`) are used directly.

**Root cause**: Print letter-spacing values are tuned for small sizes (8-12pt). At slide sizes (48-64px), the same absolute value gets multiplied out of control.

**Fix**: Slide letter-spacing = print value / 2. Mono fonts are exempt (fixed-width by nature, no extra tracking needed).

```css
/* Print eyebrow */
.eyebrow { letter-spacing: 6px; }

/* Slide eyebrow */
.slide .eyebrow { letter-spacing: 3px; }   /* halved */
```
