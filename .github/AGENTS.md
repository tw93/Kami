# CI Guide

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
