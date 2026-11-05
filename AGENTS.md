# Kami Agent Guide

## Project

Kami is a document-generation skill and template system: self-contained editorial HTML
templates rendered to PDF / PPTX / PNG, plus reference specs, demo assets, and a
packaged skill archive. `SKILL.md` is the runtime manual for producing a document.
This file is the maintenance guide for changing the repository itself, and it records
the traps that a fresh read of the code does not reveal.

## Layout

One repository, three top-level roles, and the install tools only ever copy the first:

- `skills/kami/` is the skill and the only thing users install: `SKILL.md`,
  `CHEATSHEET.md`, `VERSION`, `LICENSE`, `references/`, `scripts/`, and the light
  `assets/` (templates, diagrams, logo, the two small font files). `npx skills add
  tw93/kami` copies exactly this directory; `bash scripts/package-skill.sh` zips it
  as `kami/` for Claude Desktop; `plugins/kami/skills/kami/` is a generated copy of it
  inside the Claude and Codex plugin. Ignored render output lives in
  `skills/kami/assets/examples/`. Every skill-relative path in `SKILL.md`
  resolves inside this directory, so nothing here may reach up into the repo.
- `site/` is kami.tw93.fun. The Vercel project's Root Directory is `site` (project
  setting, not a file), so only this tree deploys and `site/vercel.json` is the only
  Vercel config. It carries the pages, `styles.css`, `llms.txt`, `robots.txt`,
  `sitemap.xml`, `vercel.json`, `.well-known/`, `feeds/`, and the heavy showcase and
  demo assets. Skill facts it shows (`SKILL.md`, the discovery files) are generated
  into it, never hand-copied. `/SKILL.md` and `/kami-skill.md` send
  `X-Robots-Tag: noindex`: agents can still fetch the markdown, and search
  engines should not score that file as an HTML page.
- The root holds repository tooling only: `scripts/` (`build_metadata.py`,
  `package-skill.sh`, `release_gate.py`, `draft-release-notes.py`, `tests/`),
  `assets/fonts/` (the commercial TTFs; run `bash skills/kami/scripts/ensure-fonts.sh`
  once after cloning to copy them into the skill's ignored `assets/fonts/`, otherwise
  templates fall back to jsDelivr), `evals/` (the end-to-end skill eval suite, see
  Evals below), `docs/`, and `.github/`.

Run skill-side commands from `skills/kami/` (`cd skills/kami && python3
scripts/build.py --check`); the paths below are written from that directory unless
they start with `scripts/build_metadata.py`, `scripts/package-skill.sh`,
`scripts/release_gate.py`, or `scripts/tests/`, which live at the root. Paths under
`site/`, `plugins/`, `docs/`, `.github/`, `.claude-plugin/`, and `.agents/` are also
relative to the repository root.

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
- `scripts/diagram_geometry.py` checks annotated architecture SVG through the existing
  lint entry points. Keep geometry in the actual rect/line/polyline attributes,
  never a second JSON source. Mark node rectangles, edge shafts and label masks;
  leave boundary frames and arrowheads unmarked. Static mask checks do not replace
  rendered text-fit and arrowhead inspection.
- `scripts/deliver.py` - `build.py --deliver`, the one command `SKILL.md` gives an
  agent to finish a document: every document gate in a fixed order, the render, page
  images, and a single READY / NOT READY verdict. It owns the order; the individual
  `--check-*` flags stay for debugging one gate. Template family comes from content IR
  `type`, else from stylesheet overlap with the registered templates.
  `deliver(args, result)` also fills a dict with the same outcome for the MCP
  `kami_deliver` tool; `mcp_server.DELIVER_GATE_RULES` maps every deliver gate to a
  `kami_check` rule or declares it deliver-only, and `test_mcp` fails on a new gate
  that is in neither.
- `scripts/chart.py` - `build.py --chart` / `--check-charts`: data spec to SVG for
  bar, line, hbar, donut, candlestick, and waterfall. Chart geometry lives only here;
  each SVG embeds its spec in `data-kami-spec` and the drift gate regenerates and
  compares the marks. The five chart files in `assets/diagrams/` are its output for
  their demo data: change a chart's look in `chart.py` and regenerate them, never
  edit their SVG by hand (`--check` fails on drift).
- `scripts/brand_extract.py` - drafts a brand profile from a public website (colors,
  fonts, logo candidates, one contrast-checked accent). It fetches only the page and
  same-site stylesheets and never writes into `~/.config/kami/`.
- `scripts/html_visibility.py` - shared static HTML/CSS visibility analysis for
  `content.py` coverage and `checks.py` residue checks. Keep its conservative
  coverage and residue modes distinct; it does not implement browser layout.
- `scripts/tests/test_build.py` - the stable test entry point; sibling `test_*.py`
  modules group tests by responsibility, with counters and fixtures in `support.py`.
  `scripts/tests/corpus/<gate>/{flag,pass}/` is the labelled corpus for the PDF
  gates (orphans, density, resume balance), rendered and judged by `test_corpus.py`.
  Before changing a value in `checks_thresholds.json`, run it and read the per-gate
  `CORPUS:` line; a fixture that flips is the cost of the change, not noise.
  A rendered test that needs a line break forces it (`<br>`) instead of relying on
  font metrics: CI's Ubuntu has no Charter, the fallback fit a whole 330px line, and
  the Latin orphan test never passed on CI from `6b47277` until `ca66959`.
- `scripts/mermaid_normalize.py` - re-themes a beautiful-mermaid SVG to the Kami
  palette and makes it WeasyPrint-safe. Pure Python, no Node, ships in the package.
- `scripts/mcp_server.py` - zero-dependency MCP stdio server exposing
  `kami_templates` / `kami_doctor` / `kami_render` / `kami_check` /
  `kami_deliver` / `kami_screenshot`, so an MCP-capable agent can diagnose, render, and verify
  without reading `SKILL.md`. Register
  with `claude mcp add kami -- python3 <checkout>/skills/kami/scripts/mcp_server.py`.
- `scripts/math_render.py`, `scripts/mathjax_svg.js`, `scripts/ensure_mathjax.sh`,
  `scripts/mathjax-runtime/` - strict LaTeX to MathJax SVG; `render.py` imports
  `math_render`. This is the only Node dependency (Node 20 or 22+, refused otherwise),
  installed on demand by `ensure_mathjax.sh` from the tracked `package-lock.json`;
  all four ship in the package allowlist.
- `scripts/site_facts.py` - public-site fact drift checks (install commands, version,
  template and diagram counts across `site/index*.html`, the root `README.md`,
  `site/llms.txt`), wired into `build.py --check`; it resolves those files through
  `shared.REPO_ROOT` / `shared.SITE_ROOT` and skips itself in an installed skill.
- `scripts/check-update.sh` - quiet daily update check invoked from `SKILL.md`;
  writes a local cache marker, then resolves the latest published GitHub Release
  at most once per day. It uploads no user document or task content and stays
  silent on failure.
- `site/assets/showcase/` - README and public-site screenshots only.
  `site/assets/demos/` - README showcase demos. Neither is part of the skill.
- `assets/diagrams/src/*.mmd` - Mermaid source of the sequence / class / er diagrams.
  `assets/templates/marp/` - the Markdown-first Marp deck variant.
- `dist/` is ignored. The release archive is built by `release.yml` from
  `skills/kami` and uploaded as a release asset; nothing tracks it.
- `plugins/kami/`, `.claude-plugin/marketplace.json`,
  `.agents/plugins/marketplace.json`, and the site's discovery files are
  **generated**; see Generated Mirrors below.
- Public site surface under `site/`: `index.html` plus `index-zh|en|ja|ko|tw.html`,
  the English-only prose pages `developers|about|contact|privacy.html`, `styles.css`,
  `llms.txt`, `robots.txt`, `sitemap.xml`, `vercel.json`. `styles.css` is Kami's own site shell
  (language switcher, gallery, responsive behavior, `.hero.doc` / `.prose` for the
  prose pages); generic template rules never belong there.
- Agent-facing site surface, also under `site/`: `index.md` (Markdown twin of the homepage; `vercel.json`
  *redirects* `/` here for `Accept: text/markdown` and `/?mode=agent`, because Vercel
  applies `rewrites` only after the filesystem and `/` always matches `index.html`),
  `developers|about|contact|privacy.md`, `developers/llms.txt`, and the generated
  `.well-known/agent-skills/index.json`, `.well-known/mcp/server-card.json`,
  `feeds/catalog.jsonld`, `schemamap.xml`, `kami-skill.md` (served at `/SKILL.md` through a rewrite; it must not be named `SKILL.md`, or the skills CLI installs the site). Every new prose page needs its `.md` twin,
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
# from the repository root
python3 scripts/build_metadata.py            # regenerate plugins/kami, marketplaces, site discovery files
python3 scripts/build_metadata.py --check    # drift check for the same
bash scripts/package-skill.sh dist/kami.zip  # build the Claude Desktop archive from skills/kami
python3 scripts/tests/test_build.py          # full test suite
python3 scripts/draft-release-notes.py V1.4.0..HEAD --version V1.4.1 --title "Steadier Hand"
claude plugin eval . --runs 2 --ablation none -j 4 --keep-temp --trust-plugin --no-publish \
  --threshold 0 --judge-model sonnet --allow-tools Bash Write Edit   # end-to-end skill evals
python3 evals/score.py                       # deterministic gates over the newest eval run
# from skills/kami
bash scripts/ensure-fonts.sh                 # recover missing or truncated CJK fonts
python3 scripts/mcp_server.py                # MCP stdio server (render / check / screenshot)
python3 scripts/mermaid_normalize.py raw.svg -o clean.svg
```

## Working Rules

- `SKILL.md` is loaded whole on every trigger, so it carries routing, the execution
  contract, hard prohibitions, `--deliver`, and the feedback protocol, nothing else.
  Type-specific procedure (page density, resume recruiter pass, landing site mode,
  charts, illustrations) lives in the reference the tier table already sends the
  agent to. Before adding a paragraph to `SKILL.md`, name the eval case it fixes;
  before removing one, run the suite and compare against the last baseline.

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
  visual rules must rebuild the affected demo outputs (`site/assets/demos/*.pdf` / `*.png`)
  in the same change, not as a later cleanup. Demos inline their CSS by copy, so they
  silently keep the old style otherwise. Report the sweep: rebuilt N demos, K
  unaffected. The off-palette guard in `scripts/lint.py` scans `site/assets/demos/*.html`
  for stale hexes as a backstop, but it cannot see rendered PDFs or PNGs.
  Repository scans must reject an empty expected demo set; installed skills may
  skip the site because it is outside their distribution boundary. Test both modes
  with a known violating demo whenever repository paths change.
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
  `grep -rn "$(printf '\342\200\224')" README.md site/llms.txt site/index*.html`. Teaching
  counter-examples inside `references/anti-patterns.md` are exempt; its rule #28
  covers the generated-document side.
- For hosted-site or public-landing work, separate generic template work from Kami's
  own website first. Generic behavior lives in `assets/templates/landing-page*` and
  `references/`; Kami site facts live across `site/index*.html`, `site/styles.css`,
  `README.md`, `site/llms.txt`, `site/robots.txt`, `site/sitemap.xml`, and
  `site/vercel.json`. Public facts are wider
  than the hero: pricing, install path, version, release, support, analytics, FAQ, and
  positioning claims move together across pages, metadata, AI files, and download
  links. Do not leave a site-only analytics or tracking change contradicting the
  "no analytics" copy elsewhere.
- Landing or documentation-site work follows `references/design.md` Section 11 «Landing
  Page (screen-first)»: its «Documentation site» subsection for the doc shell (sidebar
  rail, on-this-page TOC, borderless prev/next pager), then the «Responsive
  screenshot verification» subsection that closes the section (breakpoint, tablet, and baseline screenshots
  per locale, objective line-widow scan) before shipping.
- Content changes should avoid CSS churn unless layout behavior is part of the task.
- Public copy states the product function before design terminology. Write each locale
  naturally, preserve approved taglines and personal stories, and keep claims identical
  across HTML, Markdown, metadata, and FAQ JSON-LD. Writing rules and schema comments
  must not require poetic captions, invented benefits, numeric filler, or rewrite quotas.
  Distinguish local document processing from update checks, remote assets, and the AI
  provider’s data handling.
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

## Issue And PR Maintenance

- Use official GitHub API or CLI for issue and PR work. Read the complete discussion,
  associated PRs, current source, and relevant tests before deciding what to change.
- Before each modification, check related local and live remote commits, branches,
  worktrees, accessible existing agent conversations, and the project inventory.
  Report the deduplication evidence and current owner before starting implementation.
- Validate an existing fix rather than implementing it again. When another conversation
  owns work in progress, leave implementation with that owner and report its verified
  identifier and status. Do not modify another conversation's uncommitted work.
- State access and inventory coverage gaps explicitly. A missing search result is not
  evidence that nobody owns the work; do not bypass reading restrictions.
- Perform development, builds, and tests in the user's local Mac checkout and
  branch. Do not default to creating a new PR, opening a cloud execution environment,
  or manually triggering remote CI. Preserve existing PRs and existing push-triggered
  CI; do not disable or reconfigure them. Pushes may continue under applicable
  specific authorization. Preserve the current branch while branch selection is
  unclear; do not switch or merge into main based on this workflow preference.
- Preserve the current checkout and user changes. Locate the cause before
  targeted tests, and avoid concurrent heavy builds. Never clean real user data
  to test a repair.
- Close a duplicate, verified resolved item, or clearly unrelated report only when the
  evidence and applicable user authorization support closure. Keep unresolved or
  uncertain reports open; an empty queue is not a correctness goal.
- Before implementing any change to a user interface, visual effect, interaction,
  user-facing parameter, or configuration default, present the concrete change to
  the user and obtain explicit confirmation. General repair or push authorization
  does not replace this confirmation. Include the issue, original behavior, proposed
  change, necessity, and alternatives. Pause and isolate any such unapproved work
  already in progress; do not submit or ship it. Report any already pushed changes
  accurately and do not roll them back without authorization. Internal repairs that
  do not change user behavior may continue under their applicable authorization.
- Confirm applicable authorization separately for commits, pushes, merges, and
  releases. Distinguish code fixed, tests passed, committed, released, and user retested.
- Keep reusable project guidance in this repository. Follow the existing rule above
  for one-off reports and diagnostics; do not mix temporary run status, private paths,
  personal information, or conversation identifiers into public maintenance guidance.
- If there are no open issues or PRs, report the verified result without inventing
  code changes or unnecessary repair branches.

## Generated Mirrors

`plugins/kami/skills/kami/` mirrors the distributable files from `skills/kami/`;
the two plugin manifests live in the outer `plugins/kami/` directory. The generated
copy excludes local fonts, render output, and caches. `.claude-plugin/marketplace.json`
and `.agents/plugins/marketplace.json`
point at it. Edit `skills/kami/` only and let `python3 scripts/build_metadata.py
--check` catch drift. Regenerate after any change under `skills/kami/`.

The same generator owns the site's machine-readable files under `site/`:
`.well-known/agent-skills/index.json` (carries a SHA-256 digest of `SKILL.md`, so any
skill edit changes it), `.well-known/mcp/server-card.json` (version plus the tool list
parsed out of `scripts/mcp_server.py` without importing it), `feeds/catalog.jsonld`
(built from `HTML_TEMPLATES` / `DIAGRAM_TEMPLATES`), `schemamap.xml`, and
`kami-skill.md` (the copy served at `/SKILL.md`). Never hand-edit these; change the source and
regenerate.

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
- `scripts/package-skill.sh` packages `git ls-files skills/kami`, so an untracked new
  module passes every local import and silently disappears from the archive. When
  adding a runtime module, confirm it is tracked by Git before calling the change done.
- The archive is not tracked. `release.yml` builds it from the tagged commit and
  uploads it, so a fix reaches `npx skills add` and plugin installs on the next `main`
  push but reaches Claude Desktop users only at the next release; name the channel
  that actually carries the fix before saying "fixed, please update".
- A versioned release must come from a commit reachable from `origin/main` with a
  successful exact-SHA `check.yml` run triggered by a `main` push. Published
  same-version assets are immutable in practice: a rerun may reuse `kami.zip` only
  when its entry names and payloads are identical, otherwise cut a new patch version.
- If `python3 scripts/build.py --verify` fails only because the host Python lacks PPTX
  fallback dependencies such as `python-pptx`, verify `slides` and `slides-en` from a
  temporary venv instead of treating the environment miss as a source regression.
- Resume templates (`assets/templates/resume.html`, `resume-en.html`, `resume-ko.html`) carry a two-page
  contract. Do not fix overflow by shrinking type or spacing globally first. Verify
  with `python3 scripts/build.py --verify resume`, `--verify resume-en`, and `--verify resume-ko`.
- Demo files such as `site/assets/demos/demo-resume-ko.html` own demo content, not the
  template contract. Durable rules go into templates or `references/`.

## CI Gotchas

Applies when editing `.github/workflows/*.yml` or adding a test with a heavy
dependency.

- `check.yml` has two jobs. `lint-and-test` runs dependency-light lint, metadata,
  and package gates. `verify-render` installs `weasyprint` / `pypdf` / `PyMuPDF` /
  `Pygments` / `python-pptx`, sets up Node 22 and runs `bash scripts/ensure_mathjax.sh`, then
  installs the checkout with `npx skills add` under a throwaway `HOME` and asserts
  the bare install is the kami skill alone (`SKILL.md` and `scripts/build.py`
  present, no `index.html`, no `site/`, no `TsangerJinKai02-W04.ttf`, unpacked tree
  under 6000 KB, a separate ceiling from the 6 MB ZIP limit under Refactor And
  Packaging Hard Stops), which is why a layout or size regression surfaces under a
  job named `render and verify`. It then runs the full test suite before template
  verification, including the three unlimited-page long-doc targets for rendered
  TOC counters. Tests that need an optional render dependency use the suite's
  explicit `SKIP:` counter and fail when a CI-required dependency is unavailable;
  never turn a skip into `OK:`.
- CI installs its Python dependencies and the skills CLI unpinned on purpose: users
  install the same unpinned way, so an upstream release that breaks Kami should turn
  CI red before it reaches them.
- Validate workflow edits with the CI run for the exact pushed commit on the authorized
  branch; do not create a feature branch solely for validation. A local pass does not
  prove CI font or dependency availability: check cache manifests, Ubuntu fallback
  fonts (DejaVu / Liberation), and the absence of commercial fonts (Charter / TsangerJinKai02).
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
  (`TEMPLATES/*.html` and `site/assets/demos/*.html`), so an off-palette color in Marp CSS
  still needs eyeball review.
- Resume targets require exactly two pages in all three language variants. Other
  `build_max_pages` values in `scripts/shared.py` are ceilings (one-pager 1, letter 1,
  changelog 2, equity-report 3; long-doc, portfolio, and slides-weasy are `0` =
  unlimited). Other undershooting documents are not flagged, so "this long-doc came out
  at 3 pages" is an authoring judgment call, not a gate failure. Landing pages are
  browser-only HTML with no page count at all.
- `scripts/render.py` sets PDF `/Author` from `git config user.name` or `KAMI_AUTHOR`
  only when the template still holds an author placeholder. `/Producer` and `/Creator`
  stay `Kami`.
- Long-doc TOCs use WeasyPrint `target-counter()` and stable chapter ids for rendered
  page numbers; do not reintroduce hand-written `.toc-page` spans. The row anchor must
  stay `display: block` with the numeral floated right: WeasyPrint 70.0 resolves
  `target-counter` to 0 on a flex anchor, and a `0` is valid-looking text that only the
  `--verify` link cross-check catches (production.md pitfall 24). Running headers
  default to `h1`. If a filled document does not use `h1` for chapter titles, add
  `.running-title` to the element that should drive the header.
- AI and public visibility spans `site/index*.html`, `site/llms.txt`, `site/robots.txt`,
  `site/sitemap.xml`, FAQ JSON-LD, README install text, diagram counts, and release archive
  links. Diagram count and names must stay aligned across `SKILL.md`, `CHEATSHEET.md`,
  `README.md`, `index*.html`, and `assets/diagrams/`.

## Critical Line-Break Scan

Applies before handing off any user-visible typeset deliverable (rendered PDF,
`README.md`, public site page).

- Scan page by page for three wrap candidates: a trailing line of only 1-2 words
  (orphan), a line one word away from wrapping, and a line that wraps early without
  filling its container. Confirm each in rendered context; an intentional short line
  is valid and does not need rewriting to make the count zero.
- Split the work: `python3 scripts/build.py --check-orphans <pdf>` and
  `--check-density <pdf>` catch PDF orphans and sparse pages deterministically; the
  manual pass covers what they cannot see, near-wrap and premature-wrap states inside
  a page, plus non-PDF surfaces (README and the responsive matrix in `references/design.md`).
- One confirmed defect means a whole-document sweep for that class, not a single-spot fix. Check container geometry and forced breaks before shortening copy; preserve
  facts and approved wording. Do not shrink type to dodge a wrap; deliberate layout
  changes must re-pass `python3 scripts/build.py --check` and the page-count
  contract.

## Evals

`evals/<case>/` holds end-to-end cases for `claude plugin eval`: a realistic request
with invented data (`prompt.md`), and graders for skill trigger, PDF (or HTML)
creation, and unfilled placeholders, plus fact fidelity in the HTML. Fact fidelity is
a `regex` grader wherever the facts are literal (one-pager-en, resume-cn, long-doc-cn,
equity-report-cn, letter-ko): LLM judges split on derived figures and reported false
FAILs on outputs whose facts were all present. What a judge was asked beyond the facts
is a `not_contains` regex too where it can be: invented contact details and non-Korean
copy in letter-ko, outside companies and consensus in equity-report-cn. A `focus` on a
long HTML file drew unanimous FAIL votes on outputs a standalone sonnet judge passed
with every figure rechecked (2026-10-30), matching the harness docs' advice to keep
`llm` graders for short outputs. Invented numbers in long-doc-cn are `score.py`'s
`invented` gate: every number with a unit must be supplied, or for % and 倍 a ratio or
percent change of two supplied ones; it catches invented seconds, 万, 元 and 台 but
not an invented percentage, since ratios of a dozen inputs reach most integers.
slides-en keeps the one LLM fidelity judge, which has passed every run on its deck.
`evals/score.py` then applies Kami's own gates to each kept run workspace (page
contract, atomic facts in the PDF text, fonts, density, residue, style, resume
balance, generated chart count), which the harness cannot run itself; it is
read-only unless given `--write`, which saves `gate-scores.json`. One suite run is 10
cases, 20 document builds at `--runs 2`, at roughly $1-3 each.

- Run it after any change to `SKILL.md`, a reference the tier table routes to, a
  template, or a gate an agent relies on, and compare against the previous run on the
  same cases; one run per case is noise, use `--runs 2` or more.
- The harness reads the plugin from `plugins/kami` live. Never run
  `scripts/build_metadata.py` while a suite is running, and regenerate it before a run
  so the suite tests the current skill.
- landing-page-en names Kami in its prompt because the description only claims a
  Kami landing page (6b39d04); an unnamed landing-page request fired the skill in 3 of
  4 runs, so the case measured trigger noise instead of the template.
- `--case` takes one glob, and a second `--case` replaces the first: on 2026-10-29
  `--case long-doc-cn --case equity-report-cn` ran only equity-report-cn.
- A file grader takes an exact path; globs such as `*.html` fail with "path does not
  exist". Every prompt pins its output file names for that reason.
- Kept workspaces live under `/private/tmp/e-*/sealed/home/cwd` with mode 000;
  `score.py` opens them itself. Results stay in the ignored `evals/results/`.
- Mathematics is not covered: the sandbox cannot install the MathJax runtime.
- LLM fidelity rubrics carry the case's full brief, because a judge that sees only a
  partial fact list fails supplied facts as invented. On artifacts over about 15k
  characters the harness judge is unreliable: before treating its FAIL as real,
  re-judge the stored `evidence` HTML with the same rubric (`claude -p --model sonnet`)
  and read the stated reason. In the 2026-10-15 baseline that split four failing cases
  into two noisy votes and two real unlabelled derived figures.
- resume-cn deliberately supplies thin notes (three employers, eight bullets). The
  expected behavior is two honest pages with `[DATA NEEDED]` gaps and a reported
  balance shortfall (`references/resume-writing.md` «Thin source»). `--deliver` and
  `score.py` both read that through `checks.resume_thin_source` and treat it as a
  reported gap rather than a balance failure.

## Verification

`SKILL.md` «5 · Deliver» owns the document side: `build.py --deliver` runs every
document gate (placeholders, math, residue, style, content coverage, render, page
contract, resume balance, fonts, density, orphans, page images) in order and ends
in one verdict. This section covers the maintenance side only.

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
- Packaging changes: `bash scripts/package-skill.sh dist/kami.zip`, then `unzip -l
  dist/kami.zip` to inspect for accidental large fonts, cache files, or a missing new
  helper.
- Marketplace or plugin changes: `python3 scripts/build_metadata.py --check` plus the
  isolated install smoke described under Generated Mirrors.
- Public site or AI visibility changes: check `site/index*.html`, README,
  `site/llms.txt`, `site/robots.txt`, `site/sitemap.xml`, JSON-LD, FAQ, install links, and download links
  together, then serve the page and verify the responsive matrix in
  `references/design.md` per locale.

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
  they are Latin documents, so `Charter` stays first there. The `social-cards`
  templates are the other: they carry no inline SVG, and their Latin letters and
  digits are set in Charter the way the published card sets were.
- The commercial TsangerJinKai02 files never ship inside the skill package, so a
  sandboxed install has no primary CJK serif and falls through the chain. Keep the
  chain wide (Source Han Serif SC and CN, Noto Serif CJK SC and Noto Serif SC, Songti
  SC, STSong, SimSun) so it lands on some serif rather than a system sans.
- `bash scripts/ensure-fonts.sh` downloads into the XDG user font dir
  (`${XDG_DATA_HOME:-~/.local/share}/fonts/kami`, override with `KAMI_FONT_DIR`),
  never into the skill's `assets/fonts`, so an installed Claude Desktop skill stays
  small. Inside a repo checkout it first restores missing or truncated font files from the root
  `assets/fonts/` into the skill's ignored font directory. It downloads to the user
  font directory only when usable fonts are still missing. Commercial use of TsangerJinKai02 requires
  the appropriate license.

## Releasing

`docs/release.md` owns release notes format, the tag and asset flow, and demo
screenshot regeneration commands. Read it when cutting or refreshing a release.
