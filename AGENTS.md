# Kami Agent Guide

> Personal/global agent rules may live outside this repository. This file records Kami-specific repository maps, Working Rules, Current Risk Areas, Verification, Release Flow, and Fonts.

## Project

Kami is a document-generation skill and template system. It ships editorial HTML templates, reference guides, demo assets, and a packaged skill archive.

## Repository Map

- `SKILL.md` - skill routing and operating rules.
- `CHEATSHEET.md` - quick design reference.
- `CLAUDE.md` - Claude-specific notes pointing to AGENTS.md.
- `references/` - design, writing, diagram, and production guidance.
- `references/design.md`, `writing.md`, `production.md`, `diagrams.md` - full specs.
- `references/resume-writing.md` - resume-specific bullet/project framing rules.
- `references/anti-patterns.md` - six-category checklist for reviewing drafts.
- `references/mermaid.md` - Mermaid diagram support: the two render paths (PDF vs browser) and the authoring pipeline.
- `references/mermaid-theme.json` - canonical Kami↔beautiful-mermaid color/font theme (kept in sync with `tokens.json`).
- `references/tokens.json` - canonical color tokens (drift-checked by `scripts/tokens.py`).
- `references/checks_thresholds.json` - rhythm / density / orphan check thresholds (loaded by `scripts/checks.py`).
- `references/brand-profile.md` and `references/brand.example.md` - optional brand profile behavior and public example.
- `.claude-plugin/marketplace.json` - **generated** Claude Code plugin marketplace metadata. Points Claude Code at `plugins/kami`.
- `.agents/plugins/marketplace.json` - **generated** Codex repo marketplace. Points Codex at `plugins/kami`; never hand-edit.
- `plugins/kami/` - **generated** Claude Code / Codex plugin tree. Mirrors the lightweight skill package under `plugins/kami/skills/kami/`; edit source files and run `python3 scripts/build_metadata.py`.
- `assets/templates/` - document templates including browser-only landing page variants.
- `scripts/highlight.py` - Pygments-based syntax highlighting for code blocks at build time.
- `assets/demos/` - README showcase demos.
- `assets/showcase/` - README and public-site-only screenshots; excluded from `dist/kami.zip`.
- `assets/diagrams/` - diagram prototypes and generated diagram assets; `src/*.mmd` records the Mermaid source of the `sequence` / `class` / `er` diagrams.
- `scripts/mermaid_normalize.py` - re-themes any beautiful-mermaid SVG to the Kami palette and makes it WeasyPrint-safe (resolves `color-mix()`/`var()` to static hex, rewrites fonts). Pure Python, no Node; ships in the package.
- `assets/fonts/` and `assets/illustrations/` - bundled visual assets.
- `styles.css` - shared web-facing styles.
- `index.html`, `index-zh.html`, `index-en.html`, `index-ja.html`, `index-ko.html`, `index-tw.html` - public site entrypoints.
- `robots.txt`, `sitemap.xml`, and `vercel.json` - public crawler, deployment, and AI visibility files.
- `llms.txt` - AI crawler and model-facing project summary.
- `scripts/build.py` - CLI shell: build targets and dispatch to lint / verify / checks / tokens modules.
- `scripts/verify.py` - end-to-end render verification (page count, embedded fonts, advisory density scan).
- `scripts/lint.py` - template CSS lint rules and base/variant cross-template `:root` consistency check (CN↔EN and CN↔KO).
- `scripts/tokens.py` - `tokens.json` drift check across HTML templates and PPTX slide scripts.
- `scripts/checks.py` - PDF-side checks: placeholders, orphans, density, slide-deck rhythm.
- `scripts/optional_deps.py` - centralized loader for weasyprint / pypdf / PyMuPDF with consistent install hints.
- `scripts/shared.py` - shared constants and the canonical `HTML_TEMPLATES` registry used by the build scripts.
- `scripts/ensure-fonts.sh` - verified font recovery helper (portable across bash 3.2+).
- `scripts/package-skill.sh` - package builder for the release archive.
- `scripts/site_facts.py` - public-site fact drift checks (install commands, version, template and diagram counts across `index*.html`, README, `llms.txt`); wired into `build.py --check`.
- `scripts/check-update.sh` - quiet daily update check invoked from `SKILL.md`; read-only VERSION compare, silent on any failure.
- `scripts/build_metadata.py` - codegen for Claude Code / Codex marketplace metadata and plugin mirror files. Run after changing `SKILL.md`, `CHEATSHEET.md`, `VERSION`, `references/`, `scripts/`, or shipped lightweight assets.
- `scripts/draft-release-notes.py` - bilingual release notes scaffold from `git log`.
- `scripts/tests/test_build.py` - zero-dependency test suite for build and shared helpers.
- `.github/workflows/check.yml` - PR/push CI that runs `--check` and the test suite.
- `.github/workflows/release.yml` - tag-triggered workflow that builds and attaches `dist/kami.zip` to the release.
- `dist/kami.zip` - tracked release archive.

Reference docs are English-only. Language-specific output differences (CN/EN/KO) belong in templates, not duplicated reference files.

## Commands

```bash
python3 scripts/build.py
python3 scripts/build.py --check
python3 scripts/build.py --verify
python3 scripts/build.py --check-placeholders path/to/filled.html
python3 scripts/build.py --check-markdown path/to/filled.pdf
python3 scripts/build.py --check-orphans path/to/doc.pdf
python3 scripts/build.py --check-density path/to/doc.pdf
python3 scripts/build.py --check-rhythm slides slides-en
python3 scripts/build_metadata.py
python3 scripts/build_metadata.py --check
python3 scripts/tests/test_build.py
# Re-theme + WeasyPrint-safe a beautiful-mermaid SVG (no Node), then embed in a diagram shell:
python3 scripts/mermaid_normalize.py raw.svg -o clean.svg
python3 scripts/draft-release-notes.py V1.4.0..HEAD --version V1.4.1 --title "Steadier Hand"
bash scripts/ensure-fonts.sh
bash scripts/package-skill.sh
```

## Working Rules

- Style changes must update `references/design.md` and the matching template tokens.
- Landing or documentation-site work follows `references/design.md` Section 11: «Documentation site» for the doc shell (sidebar rail, on-this-page TOC, borderless prev/next pager, build-time zero-JS code highlighting) and «Responsive screenshot verification» (screenshot at 375px / 1280px per locale, objective line-widow scan) before shipping.
- For hosted Kami site or public landing changes, first separate generic template work from Kami's own website. Generic behavior lives in `assets/templates/landing-page*` and `references/`; Kami site facts live across `index*.html`, `styles.css`, README, `llms.txt`, `robots.txt`, `sitemap.xml`, and `vercel.json`.
- Public facts are wider than the hero. Pricing, install path, version, release, support, analytics, FAQ, and positioning claims must move together across pages, metadata, AI files, and download links. Do not leave site-only analytics or tracking changes contradicting "no analytics" or app/package privacy copy.
- Content changes should avoid CSS churn unless layout behavior is part of the task.
- For document or template tasks, lock the output contract before editing: language, template, output format, page or length target, visual acceptance check, and verification command.
- Prefer the nearest existing template and deterministic verifier. Do not add a template, shared CSS layer, dependency, script flag, or optional mode unless the current request cannot be satisfied without it.
- New templates should copy the nearest existing template, stay aligned with `references/design.md`, and add demo coverage.
- Do not use graphic emoticons in docs, template comments, or script output.
- Do not use em dashes (U+2014) in repository docs, generated documents, template comments, or site copy; use colons, commas, periods, or parentheses instead. Self-check: `grep -rn '—' README.md llms.txt index*.html`. Teaching counter-examples inside `references/anti-patterns.md` are exempt; its rule #27 covers the generated-document side.
- Use `OK:` and `ERROR:` for status text in scripts.
- Use `scripts/ensure-fonts.sh` to recover required fonts with retry and size validation when local font files are missing or truncated. It downloads to the XDG user font dir (`${XDG_DATA_HOME:-~/.local/share}/fonts/kami`), never into the skill's `assets/fonts`, so an installed Claude Desktop skill stays small; inside a repo checkout it is a no-op because the committed large fonts already satisfy the templates' relative path.
- Do not bundle large CJK font files into `dist/kami.zip`; package scripts should exclude them while templates keep stable local-preview paths. The skill ZIP uploaded to Claude Desktop must be the `scripts/package-skill.sh` output under the 6MB package ceiling and must contain a top-level `kami/` skill folder; a hand-zipped checkout includes the tracked large fonts and Claude Desktop rejects it.
- Do not bundle README/public-site-only showcase screenshots into `dist/kami.zip`; keep them under `assets/showcase/` and exclude that directory in `scripts/package-skill.sh`.
- Keep multilingual public pages, `llms.txt`, `robots.txt`, sitemap, JSON-LD, and FAQ content aligned when changing public positioning or install instructions.
- Brand profile support is optional context. Keep public examples in `references/`; do not hard-code a maintainer's private local profile content.
- Slides default to WeasyPrint HTML-to-PDF templates unless the user explicitly needs editable PPTX output.
- Templates intentionally inline their CSS rather than share a `_kami.css` partial: each template must remain a single self-contained HTML file so users can copy-paste it without a build step. When fixing CSS drift, apply the same change across affected templates rather than introducing a build-time include.
- All template registries live in `scripts/shared.py`: `HTML_TEMPLATES` (PDF docs), `SCREEN_TEMPLATES` (browser-only), and `DIAGRAM_TEMPLATES` (assets/diagrams). `build.py` derives its target dicts from them via `build_targets()` / `screen_targets()` / `diagram_targets()`. Update the registry, not the per-script dicts, when adding or removing a template or diagram.
- Mermaid diagrams: never embed raw beautiful-mermaid SVG into a PDF-bound template. WeasyPrint cannot resolve `color-mix()`, render `<foreignObject>`, or fetch a runtime web font, so always pipe through `scripts/mermaid_normalize.py` first (`--check` lint enforces this). It is pure Python, no Node bundled. `xychart-beta` is browser-only (it styles via `<style>` class selectors); use the hand-drawn chart diagrams for PDF. Full flow in `references/mermaid.md`.

## Refactor And Packaging Hard Stops

- When refactoring `scripts/build.py` or package helpers into new modules, confirm every new helper file is tracked by Git. `scripts/package-skill.sh` packages from `git ls-files`, so untracked modules pass local imports but disappear from `dist/kami.zip`.
- Any source change that adds scripts, templates, reference JSON, workflows, or package inputs must refresh and inspect `dist/kami.zip`; package freshness is part of release readiness, not a later cleanup step.
- Changes to `SKILL.md`, templates, scripts, references, or package inputs must decide explicitly whether `dist/kami.zip` needs refresh. If the behavior is shipped through the skill package, rebuild and inspect the ZIP before handoff.
- Marketplace, plugin path, version, or generated mirror changes require runtime installation proof, not metadata proof only. For Claude Code changes, use an isolated `HOME=/tmp/...` smoke with `claude plugin marketplace add <path>`, `claude plugin install kami@kami`, `claude plugin details kami@kami`, and confirm the installed cache is the lightweight `plugins/kami` tree. For Codex changes, use an isolated `CODEX_HOME=/tmp/...` smoke with `codex plugin marketplace add <path>`, `codex plugin add kami@kami`, and `codex plugin list`; keep the generator, mirror tree, package audit, and install path aligned.
- If `python3 scripts/build.py --verify` fails only because the host Python lacks PPTX fallback dependencies such as `python-pptx`, verify `slides` and `slides-en` from a temporary venv instead of treating the environment miss as a source regression.
- Do not commit one-off review reports or diagnostic snapshots as durable docs. Extract stable rules into `AGENTS.md`, `CLAUDE.md`, `SKILL.md`, or `references/` and discard the stale report.

## CI And Verification Discipline

- Tests that need `weasyprint` / `pypdf` / `PyMuPDF` must run in a CI job that installs those deps (currently `verify-render`). The `lint-and-test` job ships only Pygments, so a `find_spec(...) is not None` skip-guard there silently skips the test while still printing `OK:`. A green `lint-and-test` does not mean the solver / render tests ran.
- Edits to `.github/workflows/*.yml` should be validated on a feature branch (push, watch the run go green) before merging to `main`. Local font / dependency / runner assumptions diverge from CI more often than expected: this project has already burned commits on `pip` cache requiring a manifest, the `fallback_present` set missing Ubuntu defaults (DejaVu / Liberation), and CI never having commercial fonts (Charter / TsangerJinKai02).
- Differences between CI and host behavior are expressed as a single explicit opt-in env var (`KAMI_ALLOW_FALLBACK_ONLY=1` for missing primary fonts). When a third such flag is needed, migrate to `references/verify_profile.json` or a `--ci-mode` CLI flag instead of letting `KAMI_*` env vars sprawl.

## Current Risk Areas

- WeasyPrint rendering is sensitive to font availability, solid hex tag backgrounds, page breaks, CJK fallback, and synthetic bold. Verify visually for template changes.
- Slide output has three paths: `slides-weasy*.html` for default PDF decks, `slides*.py` for editable PPTX fallback, and `assets/templates/marp/slides-marp*.{md,css}` for Markdown-first Marp decks.
- Marp theme CSS (`assets/templates/marp/slides-marp.css` and `-en`) inlines a full copy of the design tokens (`--parchment`, `--brand`, `--serif`, rhythm modules) because Marp themes must be self-contained. `build.py --sync` / `--check`, the CSS lint rules, and the off-palette hex guard all scan `marp/*.css` through `shared.iter_template_files`, so token drift, rule violations, and stray colors are caught alongside the editorial HTML templates.
- AI/public visibility spans `index*.html`, `llms.txt`, `robots.txt`, `sitemap.xml`, FAQ JSON-LD, README install text, diagram counts, and release archive links.
- `scripts/shared.py` centralizes constants used by the build scripts; keep paths and target names in sync before adding templates or diagrams.
- `dist/kami.zip` is a tracked release archive. Packaging changes must update and inspect it deliberately.
- Claude Code / Codex plugin files are generated artifacts. Do not edit `plugins/kami/`, `.claude-plugin/marketplace.json`, or `.agents/plugins/marketplace.json` directly; regenerate from the root source files and let `python3 scripts/build_metadata.py --check` catch drift.

## Hotspot Ownership

- `references/design.md` and `plugins/kami/skills/kami/references/design.md` own the Kami visual system, including large landing-page and documentation-site rules. Boundary: edit only the root source, and use the plugin path only as a generated mirror. Verification: `python3 scripts/build.py --check` plus screenshots for screen surfaces, then `python3 scripts/build_metadata.py --check`.
- `styles.css` owns the hosted Kami public site shell, language switcher, gallery, and shared responsive behavior. Boundary: do not move generic template rules here. Verification: serve the site and screenshot 375px / 1280px per locale touched.
- `assets/templates/landing-page.html`, `assets/templates/landing-page-en.html`, `assets/templates/landing-page-ko.html`, `plugins/kami/skills/kami/assets/templates/landing-page.html`, `plugins/kami/skills/kami/assets/templates/landing-page-en.html`, and `plugins/kami/skills/kami/assets/templates/landing-page-ko.html` own the generic screen-first template shipped to users. Boundary: edit root templates, keep real product-site facts in filled sites, and treat plugin paths as generated mirrors. Verification: `python3 scripts/build.py landing-page`, browser screenshots for changed breakpoints, and `python3 scripts/build_metadata.py --check`.
- `references/production.md` and `plugins/kami/skills/kami/references/production.md` own production troubleshooting, pre-ship review, and known render pitfalls. Boundary: add stable invariants only, not dated review notes. Verification: `python3 scripts/build.py --check`, `python3 scripts/build_metadata.py --check`, and the relevant render command named by the rule.
- `assets/templates/resume.html`, `assets/templates/resume-ko.html`, `plugins/kami/skills/kami/assets/templates/resume.html`, and `plugins/kami/skills/kami/assets/templates/resume-ko.html` own high-density resume layout. Boundary: preserve the two-page contract and do not fix overflow by generic shrinking first. Verification: `python3 scripts/build.py --verify resume` and `python3 scripts/build.py --verify resume-ko`.
- `assets/demos/demo-resume-ko.html` owns the Korean resume demo content, not the template contract. Boundary: regenerate demo outputs when the demo changes, but put durable resume rules in templates or references. Verification: build the affected demo and confirm page count plus rendered screenshot.
- `scripts/tests/test_build.py` and `plugins/kami/skills/kami/scripts/tests/test_build.py` own the zero-dependency test suite. Boundary: edit the root test file and regenerate the plugin mirror. Verification: `python3 scripts/tests/test_build.py` and `python3 scripts/build_metadata.py --check`.

## High-Risk Pitfalls

See `references/production.md` Part 4.

1. Tag rgba double rectangle: use solid hex backgrounds.
2. Thin border plus border-radius double ring: border < 1pt with border-radius can trigger it.
3. Resume 2-page overflow: tiny font, fallback, line-height, or margin changes can break it.
4. `break-inside` fails inside flex: wrap content in a block wrapper.
5. `height: 100vh` is unreliable under `@page`: use explicit mm values.
6. SVG marker `orient="auto"` does not rotate in WeasyPrint: draw arrowheads manually.
7. Section body text should not use `max-width`: `.manifesto`, `.section-lede`, and similar text should fill the `.page` container. Exceptions: `.type-sample` and `.footer .colophon`.
8. Diagram template changes must sync to index showcase SVGs: any visual fix to `assets/diagrams/*.html` must also be applied to the matching mini SVG in `index.html`, `index-zh.html`, `index-ja.html`, `index-ko.html`, `index-tw.html`.

## Demo Screenshots

All demo PNG files use **1241x1754px** (first A4 portrait page at 150dpi).

For one-page and multi-page documents (one-pager / letter / resume / portfolio / long-doc / equity-report), capture page 1:

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

## Verification Details

- Expected page counts: one-pager 1, letter 1, resume 2 strict, long-doc 7 plus or minus 2, portfolio 6 plus or minus 2, slides 7 plus or minus 3, equity-report 2 to 3, changelog 1 to 2. Landing pages are browser-only HTML with no PDF page count.
- `scripts/build.py` sets PDF `/Author` from `git config user.name` or `KAMI_AUTHOR` only when the template still has an author placeholder. `/Producer` and `/Creator` should remain `Kami`.
- Demo PNGs under `assets/demos/` are first-page previews at 1241x1754px. For slide demos, capture the first two landscape pages, stack them with a parchment gap, then extend to 1241x1754px.
- Diagram count and names must stay aligned across `SKILL.md`, `CHEATSHEET.md`, `README.md`, `index*.html`, and `assets/diagrams/`.
- Long-doc TOCs use WeasyPrint `target-counter()` and stable chapter ids for rendered page numbers. Do not reintroduce hand-written `.toc-page` spans in the templates. Running headers default to `h1`; if a filled document does not use `h1` for chapter titles, add `.running-title` to the element that should drive the header.

## Verification

- Template, CSS, or script changes: run `python3 scripts/build.py --check` (CSS lint + token sync + base/variant cross-template `:root` consistency, currently CN↔EN and CN↔KO) and `python3 scripts/build.py --verify`.
- Demo changes: regenerate the affected demo outputs and confirm page counts stay in range.
- Font issues: run `bash scripts/ensure-fonts.sh`, then rebuild the affected target.
- Markdown-sourced filled documents: run `python3 scripts/build.py --check-markdown path/to/filled.pdf` after rendering, especially when the source had thematic breaks, bold markers, or inline-code backticks.
- Slide rhythm or deck changes: run `python3 scripts/build.py --check-rhythm slides slides-en` plus the affected render command.
- Public site or AI visibility changes: check `index*.html`, README, `llms.txt`, `robots.txt`, `sitemap.xml`, JSON-LD, FAQ, install links, and release/download links together. Serve the page and screenshot 375px / 1280px per locale, plus 320px when CTA width or mobile nav changes.
- Packaging changes: run `bash scripts/package-skill.sh` and confirm `dist/kami.zip` stays small enough for release upload. Inspect `unzip -l dist/kami.zip` for accidental large fonts, showcase screenshots, cache files, or missing new helper files.
- Claude Code / Codex marketplace changes: run `python3 scripts/build_metadata.py --check` and confirm `plugins/kami/.claude-plugin/plugin.json`, `plugins/kami/.codex-plugin/plugin.json`, `.claude-plugin/marketplace.json`, and `.agents/plugins/marketplace.json` stay generated. If install behavior, version selection, or source path changed, also run the matching isolated install smoke.
- Documentation-only changes: check links and references.

## Critical Line-Break Scan

- Every user-visible typeset deliverable (rendered PDFs, README, public site pages) gets a page-by-page scan for three critical wrap states before handoff: a trailing line of only 1-2 words (orphan), a line one word away from wrapping, and a line that wraps early without filling its container.
- Split the work between script and eye: `python3 scripts/build.py --check-orphans <pdf>` and `--check-density <pdf>` deterministically catch PDF orphan trailing lines and pages with too much trailing whitespace; the manual pass covers what they cannot see, near-wrap and premature-wrap states inside a page, plus non-PDF surfaces (README, `index*.html` at 375px / 1280px screenshots).
- One hit means a whole-document sweep for the same class of issue, not a single-spot fix. Fix by adjusting content length (add or cut words) first; changing font size or spacing to dodge a wrap is the last resort and must re-pass `python3 scripts/build.py --check` and the page-count contract afterwards.

## Release Notes

- Before drafting notes, read the previous published release and treat it as the hard format template: `gh release view $(gh release list -R tw93/Kami --limit 1 --json tagName --jq '.[0].tagName') -R tw93/Kami`. Mirror its exact structure (centered logo block, `### Changelog`, `### 更新日志`, closing tagline blockquote); do not rebuild the shape from memory.
- For public releases, keep notes concise and bilingual. Use one-to-one English and Chinese changelog items, 5 to 8 items, one sentence each.
- Generate the scaffold with `python3 scripts/draft-release-notes.py V<prev>..V<new> --version V<new> --title "<Codename>"`, then regroup the raw commit list into 5 to 8 product-themed bullets and translate each to Chinese. Do not paste raw commit subjects.
- Match the established shape: title is `V<x.y.z> <Two-Word Codename>` (e.g. `V1.7.2 Cleaner Resumes`), body is the centered logo block + `### Changelog` (English numbered list) + `### 更新日志` (Chinese numbered list) + the closing tagline line.

## Release Flow

- `bash scripts/package-skill.sh` writes the tracked `dist/kami.zip` release archive with a top-level `kami/` skill folder and excludes large TsangerJinKai / Source Han Serif K font files plus README/public-site-only showcase screenshots.
- `dist/kami.zip` should be committed with release changes and uploaded to the latest GitHub release asset when refreshing the Claude Desktop package.
- When refreshing a GitHub release asset, download the uploaded `kami.zip` and compare ZIP entry names plus per-entry SHA-256 digests against local `dist/kami.zip`; do not rely on release-page text, file size, or container SHA alone.
- README and public site download links use `https://github.com/tw93/kami/releases/latest/download/kami.zip`; prefer refreshing that asset for small packaging or documentation fixes instead of creating a new tag.
- Create a new version tag only when the maintainer explicitly wants a versioned release. Tag the commit that already contains the final refreshed `dist/kami.zip`; do not tag a source-only commit and refresh the archive afterward.
- On tag push, `.github/workflows/release.yml` builds and attaches `dist/kami.zip`, creates the release if missing, and adds the house-style reactions (`+1 eyes heart hooray laugh rocket`, one each). Do not `gh release create` by hand; let CI create the placeholder, then set the real title and notes with `gh release edit V<x> --title "V<x> <Codename>" --notes-file <file>`.
- If reactions are ever missing (older release, CI skipped), add them manually: `rid=$(gh api repos/tw93/Kami/releases/tags/V<x> --jq .id); for r in +1 eyes heart hooray laugh rocket; do gh api -X POST repos/tw93/Kami/releases/$rid/reactions -f content="$r"; done`.
- Reactions are part of publish completion, not optional polish. After the release is live, read back `gh api repos/tw93/Kami/releases/$rid/reactions --jq '.[].content'` and confirm all six positive reactions (`+1`, `laugh`, `heart`, `hooray`, `rocket`, `eyes`) are present. Never add `-1` or `confused`; a negative reaction on our own release reads as self-deprecation.

## Fonts

- Chinese templates use TsangerJinKai02 W04/W05. Commercial use requires the appropriate font license.
- If TsangerJinKai is unavailable, fall back through Source Han Serif SC, Noto Serif CJK SC, Songti SC, STSong, then Georgia.
- English templates use Charter serif. Japanese output uses YuMincho first, then Hiragino Mincho ProN, Noto Serif CJK JP, Source Han Serif JP, TsangerJinKai02, and generic serif.
- Korean templates use Source Han Serif K (Adobe, also distributed as Noto Serif KR by Google). Fallback chain: Source Han Serif K, Source Han Serif KR, Noto Serif KR, Apple SD Gothic Neo, AppleMyungjo, Charter, Georgia. `Source Han Serif KR` is the actual family name inside the bundled OTFs and must stay in the chain so fontconfig can resolve the `ensure-fonts.sh`-downloaded font by name on an offline Linux skill install.
- Claude Desktop ZIPs do not bundle TsangerJinKai TTF or Source Han Serif K OTF files (the OTFs are OFL-licensed and git-tracked for the CDN `@font-face` fallback, but excluded from the package to keep it small). Run `bash scripts/ensure-fonts.sh` before building Chinese or Korean documents when fonts are missing; it drops them in the XDG user font dir (fontconfig-scanned, outside the skill), so the installed skill stays small and online renders still use the jsDelivr `@font-face` fallback.
