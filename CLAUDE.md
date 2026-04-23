# Kami

Kami is one project in the Kaku (write code), Waza (practice craft), and Kami (ship documents) trilogy.
Warm parchment canvas, ink-blue accent, serif-led hierarchy, and editorial whitespace across six document templates.

## Structure

| Path | Purpose | Change frequency |
|---|---|---|
| `SKILL.md` | Claude routing and operating rules | Low |
| `CHEATSHEET.md` | Quick design reference, English-only source | Low |
| `references/design.md` | Design system spec, English-only source | Low |
| `references/writing.md` | Content strategy spec, English-only source | Low |
| `references/production.md` | WeasyPrint build and troubleshooting runbook, English-only source | Medium |
| `assets/templates/` | 6 document templates in 2 output languages | Medium |
| `assets/demos/` | README showcase demos, regenerate after visual changes | Medium |
| `scripts/build.py` | PDF / PNG / PPTX build and verification script | Low |
| `scripts/package-skill.sh` | Claude Desktop ZIP packager, excluding large fonts | Low |
| `dist/kami.zip` | Claude Desktop ZIP artifact, updated from main | Medium |

Reference docs are English-only. Do not recreate `*.en.md` duplicates. Chinese / English output differences belong in the templates.
Do not use graphic emoticons in docs, template comments, or script output. Use `OK:` / `ERROR:` for status and `Use` / `Avoid` for comparisons.

## Verification

```bash
python3 scripts/build.py          # build all outputs
python3 scripts/build.py --check  # scan CSS invariants and token drift
python3 scripts/build.py --verify # verify templates, page counts, fonts, and slides
python3 scripts/build.py --check-placeholders path/to/filled.html
```

Expected page counts: one-pager 1 / letter 1 / resume 2 strict / long-doc 7 +/- 2 / portfolio 6 +/- 2 / slides 7 +/- 3

## Demo Screenshots

All demo PNG files use **1241x1754px** (first A4 portrait page at 150dpi).

For one-page and multi-page documents (one-pager / letter / resume / portfolio / long-doc), capture page 1:
```bash
pdftoppm -r 150 -f 1 -l 1 -png <pdf> /tmp/p && cp /tmp/p-1.png <target>.png
```

For landscape slides, capture the first 2 pages, resize each to 867px high, add a 20px gap, then extend to 1241px wide:
```bash
pdftoppm -r 150 -f 1 -l 2 -png <pdf> /tmp/sl
magick /tmp/sl-1.png -resize x867 /tmp/sl1.png
magick /tmp/sl-2.png -resize x867 /tmp/sl2.png
magick -size $(identify -format '%w' /tmp/sl1.png)x20 xc:'#f5f4ed' /tmp/gap.png
magick /tmp/sl1.png /tmp/gap.png /tmp/sl2.png -append /tmp/stacked.png
magick /tmp/stacked.png -gravity Center -background '#f5f4ed' -extent 1241x1754 <target>.png
```

## Change Rules

- Style changes: update `references/design.md` and the matching template `<style>` tokens, then run `build.py` and confirm page counts stay stable.
- Content changes: keep CSS unchanged, edit only the body, then run `build.py`.
- New templates: copy the nearest existing template, keep it aligned with `design.md`, add routing to `SKILL.md`, and add demos.

## High-Risk Pitfalls

See `references/production.md` Part 4.

1. Tag rgba double rectangle: use solid hex backgrounds.
2. Thin border plus border radius double ring: border < 1pt with border-radius can trigger it.
3. Resume 2-page overflow: tiny font, fallback, line-height, or margin changes can break it.
4. `break-inside` fails inside flex: wrap content in a block wrapper.
5. `height: 100vh` is unreliable under `@page`: use explicit mm values.
6. SVG marker `orient="auto"` does not rotate in WeasyPrint: draw arrowheads manually.
7. Section body text should not use `max-width`: `.manifesto`, `.section-lede`, and similar text should fill the `.page` container. Exceptions: `.type-sample` and `.footer .colophon`.

## Release Flow

Run this before publishing or refreshing the latest release:

```bash
bash scripts/package-skill.sh        # writes dist/kami.zip (<5MB, excludes TsangerJinKai TTF)
python3 scripts/build.py --verify
git push origin main
LATEST_TAG="$(gh release list -R tw93/kami --limit 1 --json tagName -q '.[0].tagName')"
gh release upload "$LATEST_TAG" dist/kami.zip --clobber -R tw93/kami
```

`dist/kami.zip` is a tracked artifact and should be committed with the release changes. README and website download links use `https://cdn.jsdelivr.net/gh/tw93/kami@main/dist/kami.zip`, so users can update from the current `main` branch. For small packaging or documentation fixes, refresh the latest release asset with `--clobber` instead of creating a new version tag. Create a new tag only when the user explicitly wants a versioned release.

## Fonts

`TsangerJinKai02-W04.ttf` is a commercial font. Commercial use requires a license from tsanger.cn.
Fallback without TsangerJinKai: Source Han Serif SC -> Noto Serif CJK SC -> Songti SC -> Georgia.
English templates use Newsreader serif.

The Claude Desktop ZIP does not bundle TsangerJinKai TTF files. They are about 19MB each and can make upload or execution time out. Before building Chinese documents, the skill checks for missing fonts and downloads them from jsDelivr into `assets/fonts/`. WeasyPrint then uses the existing relative `@font-face` paths without changing HTML.
