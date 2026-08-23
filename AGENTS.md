# Kami Agent Guide

## Project

Kami is a document-generation skill and template system: self-contained editorial HTML
templates rendered to PDF / PPTX / PNG, plus reference specs, demo assets, and a
packaged skill archive. `SKILL.md` is the runtime manual for producing a document.
This file is the maintenance guide for changing the repository itself, and it records
the traps that a fresh read of the code does not reveal.

## Repository Map

Only the entries whose role is not obvious from the filename:

- `SKILL.md` - skill routing plus the document-side build and verify commands.
  `CHEATSHEET.md` - quick design reference. Both ship inside the package.
- `references/design.md`, `writing.md`, `production.md`, `diagrams.md` - full specs.
  `production.md` Part 4 is the single source of truth for render failures, their
  verified causes, and their fixes; add pitfalls there, not here.
  `docs/release.md` - release notes, release flow, demo screenshot regeneration.
  `anti-patterns.md`, `resume-writing.md`, `mermaid.md`, `deck-preflight.md`,
  `brand-profile.md` and `brand.example.md` - scoped guides.
- `references/tokens.json` (color tokens, drift-checked by `scripts/tokens.py`),
  `references/mermaid-theme.json` (Kami to beautiful-mermaid theme, kept in sync with
  `tokens.json`), `references/checks_thresholds.json` (rhythm / density / orphan /
  visual thresholds read by `checks.py` and `visual.py`). These are live inputs to
  gates: editing a number changes what passes.
- `references/schemas/` - one JSON Schema subset per document type. The `$comment`
  fields carry the per-field quality bar distilled from `writing.md`, so schema edits
  and `writing.md` edits move together.
- `scripts/shared.py` - the canonical registries (`HTML_TEMPLATES`,
  `SCREEN_TEMPLATES`, `PPTX_TEMPLATES`, `MARP_TEMPLATES`, `DIAGRAM_TEMPLATES`) and each template's
  `build_max_pages`. `build.py` derives its internal build targets from them;
  Marp stays discovery-only because it uses an external CLI. Add or remove a
  template or diagram here, never in a per-script dict.
- `scripts/render.py` - the single render entry (`render_pdf`, `build_slides`, PDF
  metadata stamping). `build.py`, `verify.py`, and `mcp_server.py` all call it; never
  open a second WeasyPrint call site.
- `scripts/mermaid_normalize.py` - re-themes a beautiful-mermaid SVG to the Kami
  palette and makes it WeasyPrint-safe. Pure Python, no Node, ships in the package.
- `scripts/mcp_server.py` - zero-dependency MCP stdio server exposing
  `kami_templates` / `kami_doctor` / `kami_render` / `kami_check` /
  `kami_screenshot`, so an MCP-capable agent can diagnose, render, and verify
  without reading `SKILL.md`. Register
  with `claude mcp add kami -- python3 <checkout>/scripts/mcp_server.py`.
- `scripts/site_facts.py` - public-site fact drift checks (install commands, version,
  template and diagram counts across `index*.html`, `README.md`, `llms.txt`), wired
  into `build.py --check`.
- `scripts/check-update.sh` - quiet daily update check invoked from `SKILL.md`;
  writes a local cache marker, then GETs the public VERSION file at most once per
  day. It uploads no user document or task content and stays silent on failure.
- `assets/showcase/` - README and public-site screenshots only. `assets/demos/` -
  README showcase demos. `scripts/package-skill.sh` excludes both from the ZIP.
- `assets/diagrams/src/*.mmd` - Mermaid source of the sequence / class / er diagrams.
  `assets/templates/marp/` - the Markdown-first Marp deck variant.
- `dist/kami.zip` - **tracked** release archive, committed with release changes.
- `plugins/kami/`, `.claude-plugin/marketplace.json`, and
  `.agents/plugins/marketplace.json` are **generated**; see Generated Mirrors below.
- Public site surface: `index.html` plus `index-zh|en|ja|ko|tw.html`, the English-only
  prose pages `developers|about|contact|privacy.html`, `styles.css`, `llms.txt`,
  `robots.txt`, `sitemap.xml`, `vercel.json`. `styles.css` is Kami's own site shell
  (language switcher, gallery, responsive behavior, `.hero.doc` / `.prose` for the
  prose pages); generic template rules never belong there.
- Agent-facing site surface: `index.md` (Markdown twin of the homepage; `vercel.json`
  *redirects* `/` here for `Accept: text/markdown` and `/?mode=agent`, because Vercel
  applies `rewrites` only after the filesystem and `/` always matches `index.html`),
  `developers|about|contact|privacy.md`, `developers/llms.txt`, and the generated
  `.well-known/agent-skills/index.json`, `.well-known/mcp/server-card.json`,
  `feeds/catalog.jsonld`, `schemamap.xml`. Every new prose page needs its `.md` twin,
  a `rewrites` entry for the extensionless URL, and a `sitemap.xml` row.
  The `has`-conditioned redirects and the `Link` headers are only observable on a
  deploy: verify them with `curl -sI` against the preview URL, never locally.
- `.github/workflows/check.yml` (PR/push CI) and `release.yml` (tag-triggered build
  and asset upload).

Reference docs are English-first and never forked per language. Inline CJK examples
are fine where the rule itself is about CJK typography (term annotation, punctuation,
spacing); language-specific output differences (CN/EN/KO) live in templates, not in
duplicated reference files.

## Commands

`python3 scripts/build.py --help` prints the authoritative flag list and the module
map. Read it instead of trusting any copy; hand-maintained lists here have gone stale
before. The commands it does not cover:

```bash
python3 scripts/build_metadata.py            # regenerate plugin mirror + marketplace metadata
python3 scripts/build_metadata.py --check    # drift check for the same
bash scripts/package-skill.sh                # build the tracked dist/kami.zip
bash scripts/ensure-fonts.sh                 # recover missing or truncated CJK fonts
python3 scripts/mcp_server.py                # MCP stdio server (render / check / screenshot)
python3 scripts/mermaid_normalize.py raw.svg -o clean.svg
python3 scripts/draft-release-notes.py V1.4.0..HEAD --version V1.4.1 --title "Steadier Hand"
python3 scripts/tests/test_build.py          # zero-dependency test suite
```

## Working Rules

- Style changes must update `references/design.md` and the matching template tokens.
- A CSS snippet in a reference doc is a shipped artifact, not prose: an agent copies
  it before it reads a template. Every fenced `css` / `html` block is scanned by
  `--check-docs` (inside `--check`) with the template rule set, and every `var()` it
  names must resolve to a registered token or one a shipped template defines. Teach
  from a component a template actually has; a recipe for assembling a new container
  is how a document ends up carrying three unrelated emphasis languages. Tag a
  deliberate counter-example inline with `/* avoid */` so the scan reads it as the
  lesson rather than the violation.
- A change touching template tokens, shared CSS gestures, or `references/design.md`
  visual rules must rebuild the affected demo outputs (`assets/demos/*.pdf` / `*.png`)
  in the same change, not as a later cleanup. Demos inline their CSS by copy, so they
  silently keep the old style otherwise. Report the sweep: rebuilt N demos, K
  unaffected. The off-palette guard in `scripts/lint.py` scans `assets/demos/*.html`
  for stale hexes as a backstop, but it cannot see rendered PDFs or PNGs.
- Templates intentionally inline their CSS rather than share a `_kami.css` partial:
  each template must stay a single self-contained HTML file the user can copy-paste
  with no build step. Fix CSS drift by applying the same change across the affected
  templates, never by introducing a build-time include.
- For document or template tasks, lock the output contract before editing: language,
  template, output format, page or length target, visual acceptance check, and
  verification command.
- Prefer the nearest existing template and deterministic verifier. Do not add a
  template, shared CSS layer, dependency, script flag, or optional mode unless the
  current request cannot be satisfied without it. A new template copies the nearest
  existing one, stays aligned with `references/design.md`, and adds demo coverage; a
  new document type also needs a schema in `references/schemas/`.
- Slides default to WeasyPrint HTML-to-PDF templates unless the user explicitly needs
  editable PPTX output.
- Mermaid diagrams: never embed raw beautiful-mermaid SVG into a PDF-bound template.
  WeasyPrint cannot resolve `color-mix()`, render `<foreignObject>`, or fetch a
  runtime web font, so always pipe through `scripts/mermaid_normalize.py` first
  (`--check` enforces this). `xychart-beta` is browser-only because it styles through
  `<style>` class selectors; use the hand-drawn chart diagrams for PDF. Full flow in
  `references/mermaid.md`.
- Do not use graphic emoticons in docs, template comments, or script output. Use `OK:`
  and `ERROR:` for script status text.
- Do not use em dashes (U+2014) in repository docs, generated documents, template
  comments, or site copy; use colons, commas, periods, or parentheses. Self-check:
  `grep -rn "$(printf '\342\200\224')" README.md llms.txt index*.html`. Teaching
  counter-examples inside `references/anti-patterns.md` are exempt; its rule #28
  covers the generated-document side.
- For hosted-site or public-landing work, separate generic template work from Kami's
  own website first. Generic behavior lives in `assets/templates/landing-page*` and
  `references/`; Kami site facts live across `index*.html`, `styles.css`, `README.md`,
  `llms.txt`, `robots.txt`, `sitemap.xml`, and `vercel.json`. Public facts are wider
  than the hero: pricing, install path, version, release, support, analytics, FAQ, and
  positioning claims move together across pages, metadata, AI files, and download
  links. Do not leave a site-only analytics or tracking change contradicting the
  "no analytics" copy elsewhere.
- Landing or documentation-site work follows `references/design.md` Section 11 «Landing
  Page (screen-first)»: its «Documentation site» subsection for the doc shell (sidebar
  rail, on-this-page TOC, borderless prev/next pager), then Section 12 «Responsive
  screenshot verification» (screenshot at 375px / 1280px per locale, objective
  line-widow scan) before shipping.
- Content changes should avoid CSS churn unless layout behavior is part of the task.
- Brand profile support is optional context. Keep public examples in `references/`; do
  not hard-code a maintainer's private local profile.
- Demo, reference-example, and handoff content distilled from a maintainer's private
  documents (resume, business proposal, pricing, client names) must be de-identified
  before it lands in the repo: swap in public figures, public projects, or invented
  generic data. Job-search, quote, and engagement-period fields count as sensitive
  even without names. List the swapped-out identifying signals in the handoff report;
  do not rely on the maintainer to spot leftovers.
- Do not commit one-off review reports or diagnostic snapshots as durable docs.
  Extract the stable rule into `AGENTS.md`, `SKILL.md`, or `references/`, then discard
  the report.

## Generated Mirrors

`plugins/kami/`, `.claude-plugin/marketplace.json`, and `.agents/plugins/marketplace.json`
are generated from the root sources. Edit the root file only, treat every
`plugins/kami/skills/kami/...` path as a mirror, and let
`python3 scripts/build_metadata.py --check` catch drift. Regenerate after changing
`SKILL.md`, `CHEATSHEET.md`, `VERSION`, `references/`, `scripts/`, or shipped
lightweight assets.

The same generator owns the site's machine-readable discovery files:
`.well-known/agent-skills/index.json` (carries a SHA-256 digest of `SKILL.md`, so any
skill edit changes it), `.well-known/mcp/server-card.json` (version plus the tool list
parsed out of `scripts/mcp_server.py` without importing it), `feeds/catalog.jsonld`
(built from `HTML_TEMPLATES` / `DIAGRAM_TEMPLATES`), and `schemamap.xml`. Never
hand-edit these four; change the source and regenerate.

Marketplace, plugin path, version, or install-path changes need runtime installation
proof, not metadata proof. Claude Code: an isolated `HOME=/tmp/...` smoke with
`claude plugin marketplace add <path>`, `claude plugin install kami@kami`,
`claude plugin details kami@kami`, confirming the installed cache is the lightweight
`plugins/kami` tree. Codex: an isolated `CODEX_HOME=/tmp/...` smoke with
`codex plugin marketplace add <path>`, `codex plugin add kami@kami`,
`codex plugin list`.

## Refactor And Packaging Hard Stops

- The shipped archive must be the output of `bash scripts/package-skill.sh`: a
  top-level `kami/` directory under a 6 MB ceiling. A hand-zipped checkout is
  rejected on size.
- `scripts/package-skill.sh` packages from `git ls-files`, so an untracked new module
  passes every local import and silently disappears from `dist/kami.zip`. When
  splitting `build.py` or a package helper into new modules, confirm each new file is
  tracked by Git and added to the scripts allowlist in `package-skill.sh` (its
  coverage gate fails the build otherwise).
- Any source change to `SKILL.md`, scripts, templates, reference JSON, workflows, or
  package inputs must refresh and inspect `dist/kami.zip`. Package freshness is release
  readiness, not later cleanup. It is also the precondition for telling a reporter a fix
  has shipped: a commit on `main` reaches `npx skills add` and plugin installs right
  away, but Claude Desktop users download
  `releases/latest/download/kami.zip`, so name the channel that actually carries the fix
  and confirm that asset was refreshed before saying "fixed, please update".
- If `python3 scripts/build.py --verify` fails only because the host Python lacks PPTX
  fallback dependencies such as `python-pptx`, verify `slides` and `slides-en` from a
  temporary venv instead of treating the environment miss as a source regression.
- Resume templates (`assets/templates/resume.html`, `resume-ko.html`) carry a two-page
  contract. Do not fix overflow by shrinking type or spacing globally first. Verify
  with `python3 scripts/build.py --verify resume` and `--verify resume-ko`.
- Demo files such as `assets/demos/demo-resume-ko.html` own demo content, not the
  template contract. Durable rules go into templates or `references/`.

## CI Gotchas

Applies when editing `.github/workflows/*.yml` or adding a test with a heavy
dependency.

- `check.yml` has two jobs. `lint-and-test` runs dependency-light lint, metadata,
  and package gates. `verify-render` installs `weasyprint` / `pypdf` / `PyMuPDF` /
  `Pygments`, then runs the full test suite before template verification. Tests that
  need an optional render dependency use the suite's explicit `SKIP:` counter and
  fail when a CI-required dependency is unavailable; never turn a skip into `OK:`.
- Validate workflow edits on a feature branch (push, watch the run go green) before
  merging to `main`. Local font and dependency assumptions diverge from CI more often
  than expected; this project has already burned commits on `pip` cache requiring a
  manifest, the `fallback_present` set missing Ubuntu defaults (DejaVu / Liberation),
  and CI never having commercial fonts (Charter / TsangerJinKai02).
- Host-versus-CI differences are expressed as explicit opt-in env vars, currently
  `KAMI_ALLOW_FALLBACK_ONLY` (accept fallback fonts), `KAMI_AUTHOR`, `KAMI_FONT_DIR`,
  `KAMI_PACKAGE_ROOT_NAME`, `KAMI_PACKAGE_MAX_BYTES`, and `KAMI_UPDATE_URL`. That is
  already the ceiling: before adding another, move the behavior into a `--ci-mode`
  flag or a config file rather than letting `KAMI_*` sprawl.

## Current Risk Areas

- WeasyPrint rendering is sensitive to font availability, solid hex tag backgrounds,
  page breaks, CJK fallback, and synthetic bold. Verify visually for template changes.
- Slide output has three paths: `slides-weasy*.html` for default PDF decks,
  `slides*.py` for the editable PPTX fallback, and
  `assets/templates/marp/slides-marp*.{md,css}` for Markdown-first Marp decks.
- Marp theme CSS inlines a full copy of the design tokens because Marp themes must be
  self-contained. `build.py --sync` / `--check` token-sync those files and the CSS
  lint rules scan them (both walk `shared.iter_template_files`), so token drift is
  caught. The remaining hole: the off-palette hex guard globs `*.html` only
  (`TEMPLATES/*.html` and `assets/demos/*.html`), so an off-palette color in Marp CSS
  still needs eyeball review.
- Page counts are a ceiling, never a floor. `build.py --verify` fails only when a PDF
  exceeds `build_max_pages` in `scripts/shared.py` (one-pager 1, letter 1, resume 2,
  changelog 2, equity-report 3; long-doc, portfolio, and slides-weasy are `0` =
  unlimited). An undershooting document is never flagged, so "this long-doc came out
  at 3 pages" is an authoring judgment call, not a gate failure. Landing pages are
  browser-only HTML with no page count at all.
- `scripts/render.py` sets PDF `/Author` from `git config user.name` or `KAMI_AUTHOR`
  only when the template still holds an author placeholder. `/Producer` and `/Creator`
  stay `Kami`.
- Long-doc TOCs use WeasyPrint `target-counter()` and stable chapter ids for rendered
  page numbers; do not reintroduce hand-written `.toc-page` spans. Running headers
  default to `h1`. If a filled document does not use `h1` for chapter titles, add
  `.running-title` to the element that should drive the header.
- AI and public visibility spans `index*.html`, `llms.txt`, `robots.txt`,
  `sitemap.xml`, FAQ JSON-LD, README install text, diagram counts, and release archive
  links. Diagram count and names must stay aligned across `SKILL.md`, `CHEATSHEET.md`,
  `README.md`, `index*.html`, and `assets/diagrams/`.

## Critical Line-Break Scan

Applies before handing off any user-visible typeset deliverable (rendered PDF,
`README.md`, public site page).

- Scan page by page for three critical wrap states: a trailing line of only 1-2 words
  (orphan), a line one word away from wrapping, and a line that wraps early without
  filling its container.
- Split the work: `python3 scripts/build.py --check-orphans <pdf>` and
  `--check-density <pdf>` catch PDF orphans and sparse pages deterministically; the
  manual pass covers what they cannot see, near-wrap and premature-wrap states inside
  a page, plus non-PDF surfaces (README, `index*.html` at 375px / 1280px).
- One hit means a whole-document sweep for that class, not a single-spot fix. Fix by
  adjusting content length first; changing font size or spacing to dodge a wrap is the
  last resort and must re-pass `python3 scripts/build.py --check` and the page-count
  contract.

## Verification

`SKILL.md` Step 5 owns the document-side commands (render, placeholders, markdown
residue, content IR, visual, rhythm, resume balance). This section covers the
maintenance side only.

- Template or CSS changes: `python3 scripts/build.py --check` (CSS lint, token sync,
  base/variant cross-template `:root` consistency, currently CN to EN and CN to KO)
  plus `--verify` for the affected targets, or full `--verify` when the change is
  cross-template.
- Script changes: `python3 scripts/tests/test_build.py` and
  `python3 scripts/build.py --check`. Run full `--verify` only when the render
  pipeline itself changed (`render.py`, `verify.py`, WeasyPrint handling).
- Font-stack changes (any `--serif` / `--mono` / SVG `text` chain): rebuild the
  examples, then `python3 scripts/build.py --check-fonts assets/examples/*.pdf`. The
  page-count contract cannot see which family actually drew the text, and a wrong one
  renders cleanly; this is how the diagram labels were found splitting mid-word across
  two faces.
- Demo changes: regenerate the affected demo outputs and confirm page counts stay in
  range. Font issues: `bash scripts/ensure-fonts.sh`, then rebuild the target.
- MCP server changes: smoke the stdio protocol end to end (initialize, tools/list, one
  tools/call per changed tool) through a scripted stdin session, and check that output
  stays newline-delimited JSON with no stray prints on stdout.
- Packaging changes: `bash scripts/package-skill.sh`, then `unzip -l dist/kami.zip` to
  inspect for accidental large fonts, showcase screenshots, cache files, or a missing
  new helper.
- Marketplace or plugin changes: `python3 scripts/build_metadata.py --check` plus the
  isolated install smoke described under Generated Mirrors.
- Public site or AI visibility changes: check `index*.html`, README, `llms.txt`,
  `robots.txt`, `sitemap.xml`, JSON-LD, FAQ, install links, and download links
  together, then serve the page and screenshot 375px / 1280px per locale, plus 320px
  when CTA width or mobile nav changes.

## Fonts

`references/production.md` Part 1 «Fonts» owns the full stack: per-language family
chains, fallbacks, `@font-face` paths, and the recovery flow. Two facts that must not
drift out of it:

- `Source Han Serif KR` is the real family name inside the bundled OTFs and must stay
  in every Korean fallback chain, otherwise fontconfig cannot resolve the
  `ensure-fonts.sh`-downloaded font by name on an offline Linux skill install.
- CJK families lead every stack that CJK text can reach, Latin faces trail. A leading
  Latin serif ends the stack walk for characters it lacks, which sends each ideograph
  to fontconfig separately and splits words across two faces inside inline SVG
  (`production.md` pitfall #4.1). The `-en` templates are the deliberate exception:
  they are Latin documents, so `Charter` stays first there.
- The commercial TsangerJinKai02 files never ship inside the skill package, so a
  sandboxed install has no primary CJK serif and falls through the chain. Keep the
  chain wide (Source Han Serif SC and CN, Noto Serif CJK SC and Noto Serif SC, Songti
  SC, STSong, SimSun) so it lands on some serif rather than a system sans.
- `bash scripts/ensure-fonts.sh` downloads into the XDG user font dir
  (`${XDG_DATA_HOME:-~/.local/share}/fonts/kami`, override with `KAMI_FONT_DIR`),
  never into the skill's `assets/fonts`, so an installed Claude Desktop skill stays
  small. Inside a repo checkout it is a no-op because the committed fonts already
  satisfy the templates' relative paths. Commercial use of TsangerJinKai02 requires
  the appropriate license.

## Releasing

`docs/release.md` owns release notes format, the tag and asset flow, and demo
screenshot regeneration commands. Read it when cutting or refreshing a release.
