---
marp: true
theme: kami-en
size: 280mm 158mm
paginate: true
footer: "Kami · Marp"
---

<!-- _class: cover -->
<!-- _paginate: false -->
<!-- _footer: "" -->

# Decks that read like paper

<div class="sub">Kami Marp deck · editorial rhythm in Markdown</div>
<div class="meta">Kami · 2026</div>

---

<span class="eyebrow">01 · Origin</span>

## Not a new design, just the Kami WeasyPrint deck ported to Markdown

<p class="lead">Same palette, same fonts, same layout tokens. What changes is the file format and how you edit it.</p>

<div class="c2">

<div>

### Shared with WeasyPrint slides

- `--parchment` `#f5f4ed` warm cream canvas
- `--brand` `#1B365D` the only chromatic accent
- `--serif` Charter on English, Tsanger on Chinese
- 280×158mm 16:9 page
- `.eyebrow` `.lead` `.co` `.c2` `.t2x2` carry over

</div>

<div>

### What Marp changes

- Page unit is `section`, not `.slide`
- Page break is `---`, not `break-after: page`
- Pagination via `paginate: true` injects automatically
- Per-slide class via `<!-- _class: cover -->`
- Renders through local `marp-cli`, not `build.py`

</div>

</div>

---

<span class="eyebrow">02 · Four pillars</span>

## A deck stands on these four locked decisions, settled before you write

<table class="t2x2">
<tr>
<td>

<div class="mt"><span class="ml">A</span>Palette</div>

One ink-blue accent, never above 5% of surface area. Warm neutrals carry the rest. No cool gray, no pure white.

</td>
<td>

<div class="mt"><span class="ml">B</span>Type</div>

One serif per page. Body 400, headings 500. No synthetic bold. Charter for EN, Tsanger W04 / W05 for CN.

</td>
</tr>
<tr>
<td>

<div class="mt"><span class="ml">C</span>Layout</div>

`.c2` two-column via CSS Grid. `.t2x2` four-quadrant via HTML `<table>`. Grid will not align row heights in a 2×2.

</td>
<td>

<div class="mt"><span class="ml">D</span>Rhythm</div>

`--rhythm-module: 14pt` and `--rhythm-section: 18pt`. Two tokens govern all spacing. Do not sprinkle ad-hoc margins.

</td>
</tr>
</table>

---

<span class="eyebrow">03 · Title rule</span>

## Every slide title is a full declarative sentence, not a topic label

Avoid noun phrases like "Q3 results" or "Team intro". Rewrite to "Q3 revenue beat guidance by 12 percent" or "The team has only built retrieval for five years". A reader scanning titles should leave with the takeaway; the body just supplies evidence.

<div class="co">Title carries the claim. Body grounds it. The deck gains a spine.</div>

---

<span class="eyebrow">04 · Render matrix</span>

## One Markdown source, three export targets

<table class="data">
<tr><td>HTML preview</td><td>0 MB extra download</td><td>Open in any browser. Lightest path.</td></tr>
<tr><td>PDF export</td><td>~150 MB Chromium, or reuse a local Chrome</td><td>See production.md «Browser strategy»</td></tr>
<tr><td>PPTX export</td><td>Same dependency as PDF</td><td>Slide-image dump; not an editable deck</td></tr>
<tr><td>VS Code preview</td><td>0 MB (VS Code bundles Chromium)</td><td>Install the Marp for VS Code extension</td></tr>
</table>

---

<!-- _class: cover -->
<!-- _paginate: false -->
<!-- _footer: "" -->

# Copy it, swap in your story

<div class="sub">Replace the content. Leave the structure alone.</div>
<div class="meta">github.com/tw93/Kami</div>
