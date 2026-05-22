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
- `references/tokens.json` and `references/stabilizer_profiles.json` - canonical tokens and HTML stabilization profiles.
- `references/checks_thresholds.json` - rhythm / density / orphan check thresholds (loaded by `scripts/checks.py`).
- `references/cool_gray_buckets.json` - luminance buckets and replacement colors used by `stabilize.py` cool-gray normalization.
- `references/cross_template_diff_allowlist.json` - CSS variables that may legitimately differ between paired CN and EN templates (font stacks).
- `references/brand-profile.md` and `references/brand.example.md` - optional brand profile behavior and public example.
- `.claude-plugin/marketplace.json` - Claude Code plugin marketplace metadata.
- `assets/templates/` - document templates including browser-only landing page variants.
- `scripts/highlight.py` - Pygments-based syntax highlighting for code blocks at build time.
- `assets/demos/` - README showcase demos.
- `assets/diagrams/` - diagram prototypes and generated diagram assets.
- `assets/fonts/` and `assets/illustrations/` - bundled visual assets.
- `styles.css` - shared web-facing styles.
- `index.html`, `index-zh.html`, `index-en.html`, `index-ja.html` - public site entrypoints.
- `robots.txt`, `sitemap.xml`, and `vercel.json` - public crawler, deployment, and AI visibility files.
- `llms.txt` - AI crawler and model-facing project summary.
- `scripts/build.py` - CLI shell: build targets and dispatch to lint / verify / checks / tokens modules.
- `scripts/verify.py` - end-to-end render verification (page count, embedded fonts, advisory density scan).
- `scripts/lint.py` - template CSS lint rules and CN/EN cross-template `:root` consistency check.
- `scripts/tokens.py` - `tokens.json` drift check across HTML templates and PPTX slide scripts.
- `scripts/checks.py` - PDF-side checks: placeholders, orphans, density, slide-deck rhythm.
- `scripts/optional_deps.py` - centralized loader for weasyprint / pypdf / PyMuPDF with consistent install hints.
- `scripts/shared.py` - shared constants and the canonical `HTML_TEMPLATES` registry used by build and stabilize scripts.
- `scripts/ensure-fonts.sh` - verified font recovery helper (portable across bash 3.2+).
- `scripts/stabilize.py` - deterministic HTML template normalization and overflow solving.
- `scripts/package-skill.sh` - package builder for the release archive.
- `scripts/draft-release-notes.py` - bilingual release notes scaffold from `git log`.
- `scripts/tests/test_build.py` - zero-dependency test suite for build, stabilize, and shared helpers.
- `.github/workflows/check.yml` - PR/push CI that runs `--check` and the test suite.
- `.github/workflows/release.yml` - tag-triggered workflow that builds and attaches `dist/kami.zip` to the release.
- `dist/kami.zip` - tracked release archive.

Reference docs are English-only. Language-specific output differences belong in templates, not duplicated reference files.

## Commands

```bash
python3 scripts/build.py
python3 scripts/build.py --check
python3 scripts/build.py --verify
python3 scripts/build.py --check-placeholders path/to/filled.html
python3 scripts/build.py --check-orphans path/to/doc.pdf
python3 scripts/build.py --check-density path/to/doc.pdf
python3 scripts/build.py --check-rhythm slides slides-en
python3 scripts/stabilize.py all --report
python3 scripts/stabilize.py one-pager --write --strict --report
python3 scripts/tests/test_build.py
python3 scripts/draft-release-notes.py V1.4.0..HEAD --version V1.4.1 --title "Steadier Hand"
bash scripts/ensure-fonts.sh
bash scripts/package-skill.sh
```

## Working Rules

- Style changes must update `references/design.md` and the matching template tokens.
- Content changes should avoid CSS churn unless layout behavior is part of the task.
- New templates should copy the nearest existing template, stay aligned with `references/design.md`, and add demo coverage.
- Stabilizer changes should update `references/stabilizer_profiles.json` with deterministic, target-specific rules rather than hard-coded one-off behavior.
- Do not use graphic emoticons in docs, template comments, or script output.
- Use `OK:` and `ERROR:` for status text in scripts.
- Use `scripts/ensure-fonts.sh` to recover required fonts with retry and size validation when local font files are missing or truncated.
- Do not bundle large commercial font files into `dist/kami.zip`; package scripts should exclude them while templates keep stable local-preview paths.
- Keep multilingual public pages, `llms.txt`, `robots.txt`, sitemap, JSON-LD, and FAQ content aligned when changing public positioning or install instructions.
- Brand profile support is optional context. Keep public examples in `references/`; do not hard-code a maintainer's private local profile content.
- Slides default to WeasyPrint HTML-to-PDF templates unless the user explicitly needs editable PPTX output.
- Templates intentionally inline their CSS rather than share a `_kami.css` partial: each template must remain a single self-contained HTML file so users can copy-paste it without a build step. When fixing CSS drift, apply the same change across affected templates rather than introducing a build-time include.
- The canonical `HTML_TEMPLATES` registry lives in `scripts/shared.py`; `build.py` and `stabilize.py` derive their target dicts from it. Update the registry, not the per-script dicts, when adding or removing templates.

## Refactor And Packaging Hard Stops

- When refactoring `scripts/build.py`, `scripts/stabilize.py`, or package helpers into new modules, confirm every new helper file is tracked by Git. `scripts/package-skill.sh` packages from `git ls-files`, so untracked modules pass local imports but disappear from `dist/kami.zip`.
- Any source change that adds scripts, templates, reference JSON, workflows, or package inputs must refresh and inspect `dist/kami.zip`; package freshness is part of release readiness, not a later cleanup step.
- If `python3 scripts/build.py --verify` fails only because the host Python lacks PPTX fallback dependencies such as `python-pptx`, verify `slides` and `slides-en` from a temporary venv instead of treating the environment miss as a source regression.
- Do not commit one-off review reports or diagnostic snapshots as durable docs. Extract stable rules into `AGENTS.md`, `CLAUDE.md`, `SKILL.md`, or `references/` and discard the stale report.

## CI And Verification Discipline

- Tests that need `weasyprint` / `pypdf` / `PyMuPDF` must run in a CI job that installs those deps (currently `verify-render`). The `lint-and-test` job ships only Pygments, so a `find_spec(...) is not None` skip-guard there silently skips the test while still printing `OK:`. A green `lint-and-test` does not mean the solver / render tests ran.
- Edits to `.github/workflows/*.yml` should be validated on a feature branch (push, watch the run go green) before merging to `main`. Local font / dependency / runner assumptions diverge from CI more often than expected: this project has already burned commits on `pip` cache requiring a manifest, the `fallback_present` set missing Ubuntu defaults (DejaVu / Liberation), and CI never having commercial fonts (Charter / TsangerJinKai02).
- Differences between CI and host behavior are expressed as a single explicit opt-in env var (`KAMI_ALLOW_FALLBACK_ONLY=1` for missing primary fonts). When a third such flag is needed, migrate to `references/verify_profile.json` or a `--ci-mode` CLI flag instead of letting `KAMI_*` env vars sprawl.

## Current Risk Areas

- WeasyPrint rendering is sensitive to font availability, solid hex tag backgrounds, page breaks, CJK fallback, and synthetic bold. Verify visually for template changes.
- Slide output has two paths: `slides-weasy*.html` for default PDF decks and `slides*.py` for editable PPTX fallback.
- AI/public visibility spans `index*.html`, `llms.txt`, `robots.txt`, `sitemap.xml`, FAQ JSON-LD, README install text, diagram counts, and release archive links.
- `scripts/shared.py` centralizes constants used by build and stabilization scripts; keep paths and target names in sync before adding templates or diagrams.
- `dist/kami.zip` is a tracked release archive. Packaging changes must update and inspect it deliberately.
- `stabilize.py` only targets templates with `stabilize_max_pages > 0` in `HTML_TEMPLATES`. The `slides-weasy`, `equity-report`, `changelog`, and `landing-page` templates are intentionally excluded: the overflow solver is not appropriate for multi-page decks, paginated reports, or browser-only screen templates.

## High-Risk Pitfalls

See `references/production.md` Part 4.

1. Tag rgba double rectangle: use solid hex backgrounds.
2. Thin border plus border-radius double ring: border < 1pt with border-radius can trigger it.
3. Resume 2-page overflow: tiny font, fallback, line-height, or margin changes can break it.
4. `break-inside` fails inside flex: wrap content in a block wrapper.
5. `height: 100vh` is unreliable under `@page`: use explicit mm values.
6. SVG marker `orient="auto"` does not rotate in WeasyPrint: draw arrowheads manually.
7. Section body text should not use `max-width`: `.manifesto`, `.section-lede`, and similar text should fill the `.page` container. Exceptions: `.type-sample` and `.footer .colophon`.
8. Diagram template changes must sync to index showcase SVGs: any visual fix to `assets/diagrams/*.html` must also be applied to the matching mini SVG in `index.html`, `index-zh.html`, `index-ja.html`.

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

## Verification

- Template, CSS, or script changes: run `python3 scripts/build.py --check` (CSS lint + token sync + CN/EN cross-template `:root` consistency) and `python3 scripts/build.py --verify`.
- HTML stabilization changes: run `python3 scripts/stabilize.py all --report` and inspect generated files under `dist/stabilized/` or the requested output directory.
- Demo changes: regenerate the affected demo outputs and confirm page counts stay in range.
- Font issues: run `bash scripts/ensure-fonts.sh`, then rebuild the affected target.
- Slide rhythm or deck changes: run `python3 scripts/build.py --check-rhythm slides slides-en` plus the affected render command.
- Public site or AI visibility changes: check `index*.html`, `llms.txt`, `robots.txt`, `sitemap.xml`, and README links together.
- Packaging changes: run `bash scripts/package-skill.sh` and confirm `dist/kami.zip` stays small enough for release upload.
- Documentation-only changes: check links and references.

## Release Notes

For public releases, keep notes concise and bilingual when requested. Use one-to-one English and Chinese changelog items, 5 to 8 items, one sentence each.

## Release Flow

- `bash scripts/package-skill.sh` writes the tracked `dist/kami.zip` release archive and excludes large TsangerJinKai font files.
- `dist/kami.zip` should be committed with release changes and uploaded to the latest GitHub release asset when refreshing the Claude Desktop package.
- README and public site download links use `https://github.com/tw93/kami/releases/latest/download/kami.zip`; prefer refreshing that asset for small packaging or documentation fixes instead of creating a new tag.
- Create a new version tag only when the maintainer explicitly wants a versioned release.

## Fonts

- Chinese templates use TsangerJinKai02 W04/W05. Commercial use requires the appropriate font license.
- If TsangerJinKai is unavailable, fall back through Source Han Serif SC, Noto Serif CJK SC, Songti SC, STSong, then Georgia.
- English templates use Charter serif. Japanese output uses YuMincho first, then Hiragino Mincho ProN, Noto Serif CJK JP, Source Han Serif JP, TsangerJinKai02, and generic serif.
- Claude Desktop ZIPs do not bundle TsangerJinKai TTF files. Run `bash scripts/ensure-fonts.sh` before building Chinese documents when fonts are missing.
