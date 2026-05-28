# Kami Korean Template Full-Set Design

- **Date:** 2026-05-28
- **Author:** glen (with Claude)
- **Status:** Approved for implementation planning
- **Scope:** Add a full Korean (`-ko`) variant family to Kami's editorial document template system, mirroring the existing CN / EN parity.

## 1. Problem & Goal

Kami currently ships two locale variants per template: Chinese (default, no suffix) and English (`-en`). Korean is supported only at the public-site landing layer (`index-ko.html`); no `-ko` document templates exist. Users wanting Korean editorial PDFs have no first-class path.

**Goal:** Extend the registry, lint pipeline, font bundle, and template set so that every Kami output target has a Korean sibling, using **Nanum Myeongjo** as the primary serif (the most widely used Korean web/print font, OFL-licensed and freely redistributable).

**Non-goals:**
- Translating reference docs (`references/writing.md`, `references/design.md`, etc.) — AGENTS.md mandates English-only references.
- Building a generic locale framework. KO is added by replicating the CN/EN pattern, not by introducing a new abstraction.
- Adding Japanese document templates. JA stays landing-page-only for now.

## 2. Decisions (locked during brainstorming)

| Topic | Decision |
|---|---|
| Body serif stack | Nanum Myeongjo first, with Apple SD Gothic Neo / Noto Serif KR / Source Han Serif K / Charter / Georgia fallbacks |
| Fork base | CN (`zh-CN`) templates — CJK locale tuning carries over more naturally than EN |
| Font bundling | Bundled in repo (`assets/fonts/NanumMyeongjo-Regular.ttf` + `-Bold.ttf`) **and** included in `dist/kami.zip` (OFL allows redistribution; not a "large commercial" font) |
| Slides scope | Both WeasyPrint HTML (`slides-weasy-ko.html`) and editable PPTX (`slides-ko.py`) — full CN/EN parity |
| Landing page | Included (`landing-page-ko.html`, screen-only) |
| Lint pair check | Generalize CN↔EN pair check to also cover CN↔KO |
| Demo coverage | Demo set for all 10 KO outputs |
| Rollout shape | 3 phases: infrastructure → pilot (`one-pager-ko`) → remaining 9 + finalization |

## 3. Architecture Overview

The KO variant family is a third sibling alongside CN and EN. No new abstractions, helpers, or build steps are introduced — only an additional locale of the existing pattern.

```
scripts/shared.py        HTML_TEMPLATES + SCREEN_TEMPLATES gain 10 KO entries
assets/templates/*-ko.*  10 new templates (9 HTML + 1 PPTX py)
assets/fonts/            NanumMyeongjo Regular + Bold .ttf + LICENSE-NanumMyeongjo.txt
references/
  cross_template_diff_allowlist.json  description updated; structure unchanged
  design.md                            new "KO locale tuning" section
scripts/lint.py          _pair_names + check_cross_template_consistency generalized
                         to match any "<base>-<variant>" pair (`-en`, `-ko`)
scripts/ensure-fonts.sh  Nanum Myeongjo download + size validation added
AGENTS.md                Fonts section + Repository Map + verification notes
scripts/package-skill.sh Confirm Nanum is included (not caught by TsangerJinKai
                         exclusion); add explicit verification step
assets/demos/            10 KO demo sets (HTML/PDF/PNG; .pptx for slides PPTX)
index-ko.html, llms.txt, sitemap.xml, README cross-links: parity check only
```

**Principles**
1. Extend existing registries, lint, and helpers; do **not** add new modules.
2. KO templates copy CN's CSS structure verbatim; only `<html lang>`, `@font-face`, the four font CSS variables (`--serif` / `--sans` / `--mono` / `--latin-ui`), and CJK letter-spacing/line-height tuning differ.
3. `references/cross_template_diff_allowlist.json` structure stays the same; the `_description` is updated to cover CN/EN/KO triples.

## 4. Component-Level Changes

### 4.1 New files (`assets/templates/`)

| File | Forked from | Key changes |
|---|---|---|
| `one-pager-ko.html` | `one-pager.html` | `lang="ko"`, `@font-face` Nanum Myeongjo W400/W700, `--serif` KR chain, CJK letter-spacing retuned for hangul metrics |
| `letter-ko.html` | `letter.html` | Same pattern |
| `long-doc-ko.html` | `long-doc.html` | Same + body line-height tuned for hangul readability (candidate: 1.7 → 1.75; final value set in pilot) |
| `portfolio-ko.html` | `portfolio.html` | Same pattern |
| `resume-ko.html` | `resume.html` | Same. **Strict 2-page constraint is the highest-risk target**; pilot tuning must not break it |
| `equity-report-ko.html` | `equity-report.html` | Same + data-table mono fallback decision (keep JetBrains Mono first; D2Coding as KR mono fallback) |
| `changelog-ko.html` | `changelog.html` | Same pattern |
| `slides-weasy-ko.html` | `slides-weasy.html` | Same + slide headline letter-spacing/line-height retuned for hangul tone |
| `slides-ko.py` | `slides.py` | Add `LANG = "ko"` and `KO_SERIF = "NanumMyeongjo"` alongside existing `CN_SERIF` / `JA_SERIF`; existing `LANG`-conditional dispatch already supports adding a branch |
| `landing-page-ko.html` | `landing-page.html` | `lang="ko"`, font stack swap; screen-only, not subject to `--verify` |

### 4.2 Common HTML transformation (applies to all 9 KO HTML templates)

1. `<html lang="zh-CN">` → `<html lang="ko">`
2. Replace the two TsangerJinKai `@font-face` blocks with two Nanum Myeongjo blocks (Regular 400, Bold 700) — local TTF path plus jsdelivr CDN fallback URL, mirroring the existing TsangerJinKai pattern.
3. Replace `--serif` CN chain with KR chain (see §5.1).
4. Replace any CN-specific `--sans` / `--mono` / `--latin-ui` definitions with KR equivalents (see §5.1).
5. Re-tune any CN-specific letter-spacing tweaks (typically on `h1` / display elements) for hangul. The pilot template fixes the canonical values; the remaining 9 templates inherit those values verbatim.
6. Add `font-synthesis: none;` to the body rule to prevent WeasyPrint from synthesizing fake bold when Bold weight is missing at runtime.
7. CSS structure, color tokens, spacing tokens, page rules, and component classes remain bit-identical to CN.

### 4.3 New font files (`assets/fonts/`)

- `NanumMyeongjo-Regular.ttf` (~4 MB)
- `NanumMyeongjo-Bold.ttf` (~4 MB)
- `LICENSE-NanumMyeongjo.txt` — OFL license text plus upstream source URL

Source: Naver hangeul.naver.com (official) or Google Fonts (static OTF/TTF). License: SIL Open Font License 1.1.

### 4.4 Modified files

| File | Change |
|---|---|
| `scripts/shared.py` | Add 9 KO HTML entries to `HTML_TEMPLATES` and `landing-page-ko` to `SCREEN_TEMPLATES`. (`slides-ko.py` is not in either map; PPTX scripts run independently, same as `slides.py` / `slides-en.py` today.) |
| `scripts/lint.py` | Generalize `_pair_names()` to iterate `_VARIANT_SUFFIXES = ("-en", "-ko")` and pair each base name with every existing variant. Generalize `check_cross_template_consistency` output labels from "CN/EN pair" to "CN-variant pair" and rename drift tuple fields from `cn_value`/`en_value` to `base_value`/`variant_value`. |
| `references/cross_template_diff_allowlist.json` | Update `_description` to read "CSS variables in `:root` that may legitimately differ between a base CN template and any of its variants (`-en`, `-ko`)." Structure of `always_allowed` and `per_pair_allowed` unchanged. |
| `references/design.md` | Add "KO locale tuning" section: Nanum Myeongjo metrics notes, letter-spacing/line-height baseline, body 14pt recommendation, `font-synthesis: none` rationale. Final numeric values populated after pilot. |
| `AGENTS.md` | Fonts section: add KR fallback chain and OFL note. Repository Map: add `-ko` templates and `index-ko.html` reference. Verification section: note that `--check` now covers CN↔EN and CN↔KO pairs. |
| `scripts/ensure-fonts.sh` | Add Nanum Myeongjo Regular/Bold to the download/verify table. URL: jsdelivr GitHub raw for the repo's own assets, plus an upstream mirror. Same size-validation pattern used for TsangerJinKai. |
| `scripts/package-skill.sh` | Verify Nanum Myeongjo TTFs are included by the `git ls-files`–based packaging. Inspect the exclusion patterns (currently `TsangerJinKai*`) and confirm `NanumMyeongjo*` is not collaterally excluded. Add an explicit assertion in the script's post-package check listing `NanumMyeongjo-Regular.ttf` and `-Bold.ttf` as required entries. |
| `assets/demos/` | Add 10 KO demo sets (see §6). |
| `index-ko.html`, `llms.txt`, `sitemap.xml`, README cross-links | Parity sweep: ensure KO landing references the new template set, sitemap is current, llms.txt mentions KO templates. |

### 4.5 Unchanged files

- `references/writing.md`, `references/resume-writing.md`, `references/anti-patterns.md`, `references/production.md`, `references/diagrams.md`, `references/tokens.json`, `references/checks_thresholds.json`, `references/cool_gray_buckets.json`, `references/stabilizer_profiles.json` — locale-neutral; KO inherits.
- `scripts/build.py`, `scripts/stabilize.py`, `scripts/verify.py`, `scripts/checks.py`, `scripts/tokens.py`, `scripts/highlight.py`, `scripts/draft-release-notes.py` — all consume `HTML_TEMPLATES` via `scripts/shared.py`; no direct edits required.

## 5. Font Stack & Bundling

### 5.1 KO `:root` font variables

```css
:root {
  --serif: "NanumMyeongjo", "Apple SD Gothic Neo", "Noto Serif KR",
           "Source Han Serif K", "AppleMyungjo", Charter, Georgia, serif;
  --sans:  "Apple SD Gothic Neo", "Noto Sans KR", "Malgun Gothic",
           -apple-system, "Segoe UI", Helvetica, Arial, sans-serif;
  --mono:  "JetBrains Mono", "D2Coding", "SF Mono", "Fira Code",
           Consolas, Monaco, monospace;
  --latin-ui: "Inter", -apple-system, "Segoe UI", Helvetica, Arial, sans-serif;
}
```

Fallback rationale:
- **Nanum Myeongjo** — bundled + CDN; guaranteed.
- **Apple SD Gothic Neo** — macOS default, free; gothic rather than myeongjo but a reliable readable hangul fallback.
- **Noto Serif KR / Source Han Serif K** — Linux/CI fallback if installed; preserves myeongjo tone.
- **AppleMyungjo** — older macOS systems.
- **Charter / Georgia / serif** — last-resort Latin shapes for digits and Latin runs.

### 5.2 `@font-face` block (identical across all 9 KO HTML templates)

```css
@font-face {
  font-family: "NanumMyeongjo";
  src: url("../fonts/NanumMyeongjo-Regular.ttf") format("truetype"),
       url("https://cdn.jsdelivr.net/gh/tw93/Kami@main/assets/fonts/NanumMyeongjo-Regular.ttf") format("truetype");
  font-weight: 400;
  font-style: normal;
}
@font-face {
  font-family: "NanumMyeongjo";
  src: url("../fonts/NanumMyeongjo-Bold.ttf") format("truetype"),
       url("https://cdn.jsdelivr.net/gh/tw93/Kami@main/assets/fonts/NanumMyeongjo-Bold.ttf") format("truetype");
  font-weight: 700;
  font-style: normal;
}
```

Difference from CN: TsangerJinKai uses W04 (400) / W05 (500); Nanum exposes Regular (400) / Bold (700). The pilot must visually confirm that bold weight reads naturally and is not "too heavy" for body emphasis. Add `font-synthesis: none;` to the body rule so missing weights do not get synthesized.

### 5.3 Font acquisition (`scripts/ensure-fonts.sh`)

Extend the existing TsangerJinKai / JetBrainsMono download table:
- `NanumMyeongjo-Regular.ttf` — expected size band ~3–5 MB.
- `NanumMyeongjo-Bold.ttf` — expected size band ~3–5 MB.
- Primary URL: the repository's own jsdelivr-mirrored copy (after first commit).
- Secondary URL (one-time bootstrap): Naver or Google Fonts upstream — recorded as a comment, not a CI fallback URL.

### 5.4 ZIP inclusion policy (`scripts/package-skill.sh`)

- `package-skill.sh` packages from `git ls-files`; `NanumMyeongjo-*.ttf` is included by default once tracked.
- Current exclusion is an exact regex: `^assets/fonts/TsangerJinKai02-W0[45]\.ttf$` (plus the unrelated showcase exclusion). `NanumMyeongjo-*.ttf` is **not** caught by this pattern, so no additional rule changes are required — only a verification step in Phase 3.
- After Phase 3 build, expected ZIP size delta: **~8 MB** (Regular + Bold combined). Final ZIP comfortably under any release-asset limit.

### 5.5 License & attribution

- `assets/fonts/LICENSE-NanumMyeongjo.txt` — full OFL 1.1 text + Naver source URL.
- `README.md` has two Fonts paragraphs (currently around lines 127 and 177). Update both to include Korean: "Korean: Nanum Myeongjo (OFL, Naver Corp.)" added to the language list, and the "free for personal use only" caveat clarified to apply only to TsangerJinKai. The "Chinese fonts load from local checkout first, then jsDelivr CDN" sentence near line 95 is generalized to "Chinese and Korean fonts".
- `AGENTS.md` Fonts section — KR fallback chain and OFL note.

## 6. Lint Pair Extension (CN↔KO)

### 6.1 Current `_pair_names` (`scripts/lint.py:207`)

Pairs each non-`-en` template with its `-en` sibling and runs `check_cross_template_consistency` against `:root` variables, gated by `cross_template_diff_allowlist.json`.

### 6.2 Generalization

```python
_VARIANT_SUFFIXES = ("-en", "-ko")

def _pair_names() -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    seen = set(HTML_TEMPLATES) | set(SCREEN_TEMPLATES)
    for name in sorted(seen):
        if any(name.endswith(s) for s in _VARIANT_SUFFIXES):
            continue
        for suffix in _VARIANT_SUFFIXES:
            variant = f"{name}{suffix}"
            if variant in seen:
                pairs.append((name, variant))
    return pairs
```

`check_cross_template_consistency` renames its log strings:
- `"CN/EN pair"` → `"CN-variant pair"`
- `cn_value` / `en_value` drift fields → `base_value` / `variant_value`

Behaviour: if KO templates do not yet exist for a base, only the CN↔EN pair is generated (back-compat).

### 6.3 `cross_template_diff_allowlist.json`

- `always_allowed` keeps `--serif`, `--sans`, `--mono`, `--latin-ui`.
- `per_pair_allowed` keyed by base name applies to *all* variants of that base. This is acceptable for the initial KO rollout because no KO-only token exceptions are anticipated. If KO-specific exceptions become necessary later, the structure can grow a `per_variant_allowed: {"<base>-ko": [...]}` field — explicitly out of scope for this design.

### 6.4 Effect

- Every KO `:root` is checked against its CN base; only the four font variables differ. All color, spacing, and brand tokens stay in lockstep across CN, EN, and KO.

## 7. Demo Coverage

### 7.1 Naming convention

Existing demos in `assets/demos/` are topic-based and language-unsuffixed: `demo-kaku.{html,pdf,png}`, `demo-tesla.{html,pdf,png}`, `demo-musk-resume.{html,pdf,png}`, `demo-agent-slides.{html,pdf,png}`, plus a standalone `equity-report-en.png`. There is no current pattern for per-locale demo duplication.

**Decision:** KO demos use the `-ko` suffix on the existing topic where applicable (e.g. `demo-kaku-ko.*`). For templates that do not yet have a corresponding CN topic demo (`long-doc`, `portfolio`, `equity-report`, `changelog`), a new KO topic is created; whether to backfill matching CN demos is tracked as a follow-up in §11.

### 7.2 Demo plan (10 deliverables)

| Base topic | Template | Demo files |
|---|---|---|
| Kaku | `one-pager-ko` | `demo-kaku-ko.{html,pdf,png}` |
| Tesla | `letter-ko` | `demo-tesla-ko.{html,pdf,png}` |
| (new) | `long-doc-ko` | `demo-longdoc-ko.{html,pdf,png}` |
| (new) | `portfolio-ko` | `demo-portfolio-ko.{html,pdf,png}` |
| Musk Resume | `resume-ko` | `demo-musk-resume-ko.{html,pdf,png}` |
| (new) | `equity-report-ko` | `demo-equity-ko.{html,pdf,png}` |
| (new) | `changelog-ko` | `demo-changelog-ko.{html,pdf,png}` |
| Agent Slides | `slides-weasy-ko` | `demo-agent-slides-ko.{html,pdf,png}` |
| Agent Slides | `slides-ko.py` | `demo-agent-slides-ko.pptx` |
| (screen) | `landing-page-ko` | `demo-landing-ko.html` + one browser screenshot |

### 7.3 Screenshot rules (per AGENTS.md "Demo Screenshots")

- Document templates: `pdftoppm -r 150 -f 1 -l 1 -png` → 1241×1754.
- Slides: capture two landscape pages, resize and stack with a parchment gap, extend to 1241×1754.
- `landing-page-ko`: browser screenshot, separate capture procedure outside the standard 1241×1754 rule.

### 7.4 Sample content

Sample content is not part of this design's scope, but the convention is: translate CN sample content into natural Korean and replace foreign proper nouns with Korean-appropriate placeholders (fictional Korean companies, names) where the original would feel awkward to a Korean reader. Tone and structure stay one-to-one with the CN demo.

## 8. Verification

### 8.1 Automated regression (build/verify pipeline)

- `python3 scripts/build.py --check` — lints all KO templates and checks CN↔EN plus CN↔KO `:root` consistency.
- `python3 scripts/build.py --verify` — page-count expectations:
  - `one-pager-ko` strict 1
  - `letter-ko` strict 1
  - `resume-ko` strict 2 — **highest regression risk**
  - `long-doc-ko` 7 ± 2
  - `portfolio-ko` 6 ± 2
  - `equity-report-ko` 2–3
  - `changelog-ko` 1–2
  - `slides-weasy-ko` 7 ± 3
- `python3 scripts/build.py --check-rhythm slides slides-en slides-weasy-ko` — slide rhythm extended to KO.
- `python3 scripts/tests/test_build.py` — registry and stabilize-helper regression.

### 8.2 Visual verification (manual, pilot phase)

Immediately after building `one-pager-ko` PDF, confirm:
1. Nanum Myeongjo glyphs are actually embedded in the PDF (font inspector).
2. H1 letter-spacing reads naturally on hangul (CN's `letter-spacing` value may need adjustment for hangul width).
3. Body line-height is comfortable for paragraphs of Korean.
4. No synthetic bold appears (`font-synthesis: none` is respected).
5. Latin numerals and English runs fall back cleanly to Charter / Georgia.
6. Page count stays strict 1.

Lock canonical tuning values in `references/design.md` after these six checks pass; the remaining 9 templates inherit them verbatim.

### 8.3 Fallback-only simulation

Build with `KAMI_ALLOW_FALLBACK_ONLY=1` (or equivalent KAMI env opt-in for missing primary fonts) to confirm Apple SD Gothic Neo / Noto Serif KR fallbacks render acceptably when Nanum is absent. If the result is materially worse, wire `scripts/ensure-fonts.sh`'s Nanum step into the CI's `verify-render` job so CI always has the primary fonts available.

### 8.4 Stabilize

- `python3 scripts/stabilize.py one-pager-ko --write --strict --report`
- `python3 scripts/stabilize.py resume-ko --write --strict --report`

`equity-report-ko`, `changelog-ko`, `slides-weasy-ko`, and `landing-page-ko` have `stabilize_max_pages = 0` and are not subject to the overflow solver.

### 8.5 Package inspection

After `bash scripts/package-skill.sh`:
- `assets/fonts/NanumMyeongjo-Regular.ttf` and `-Bold.ttf` are present.
- `assets/fonts/TsangerJinKai02-W04.ttf` and `-W05.ttf` are still excluded.
- All 10 `-ko` template files are present.
- All 10 KO demo deliverables are present.
- Final ZIP size recorded for the release notes.

## 9. Rollout Plan

### Phase 1 — Infrastructure

Goal: prepare the registry, lint, font ingestion, and documentation surface so Phase 2 can fork the pilot without scaffolding rework.

1. Add `assets/fonts/NanumMyeongjo-Regular.ttf`, `assets/fonts/NanumMyeongjo-Bold.ttf`, `assets/fonts/LICENSE-NanumMyeongjo.txt`. Git-track them.
2. Generalize `scripts/lint.py` `_pair_names` and `check_cross_template_consistency` (§6.2). KO not yet present, so the new pair list collapses to the existing CN/EN pairs at this point.
3. Update `references/cross_template_diff_allowlist.json` `_description` to mention KO.
4. Extend `scripts/ensure-fonts.sh` with the Nanum Myeongjo entries.
5. Update `AGENTS.md` Fonts section, Repository Map, and Verification notes.
6. Add a stub "KO locale tuning" section to `references/design.md` listing the items the pilot will populate (letter-spacing, line-height, body size, `font-synthesis`).
7. Do **not** modify `scripts/shared.py` yet — registry edits land with their templates in Phase 2/3 to avoid a broken-build window.

**Phase 1 verification:** `python3 scripts/tests/test_build.py`; `python3 scripts/build.py --check` (CN/EN-only result, must stay green); `bash scripts/ensure-fonts.sh` succeeds.

### Phase 2 — Pilot (`one-pager-ko`)

Goal: lock the canonical KO tuning by forking the simplest template end-to-end.

1. Fork `assets/templates/one-pager.html` → `one-pager-ko.html`. Apply §4.2 transformation.
2. Register `one-pager-ko` in `scripts/shared.py` `HTML_TEMPLATES`.
3. Generate `assets/demos/demo-kaku-ko.{html,pdf,png}` (PNG via the standard `pdftoppm` procedure).
4. Run the six visual checks from §8.2. Iterate on `letter-spacing`, `line-height`, body `font-size`, and `font-synthesis` until the page reads naturally and stays strict 1 page.
5. Record final tuning values in `references/design.md` KO section. These values become the standard for the remaining 9 templates.

**Phase 2 verification:** `--check`, `--verify` (page count strict 1), `stabilize.py one-pager-ko --strict`, demo PNG resolution 1241×1754, font embedding inspection.

### Phase 3 — Remaining 9 + finalization

1. Fork the remaining 9 templates (`letter-ko`, `long-doc-ko`, `portfolio-ko`, `resume-ko`, `equity-report-ko`, `changelog-ko`, `slides-weasy-ko`, `slides-ko.py`, `landing-page-ko`) applying the Phase 2 canonical tuning verbatim.
2. Register the new HTML/screen entries in `scripts/shared.py`.
3. Implement `slides-ko.py` by adding a `LANG = "ko"` branch with `KO_SERIF = "NanumMyeongjo"` alongside the existing `CN_SERIF` / `JA_SERIF` constants.
4. Generate the 9 remaining demo sets per §7.2.
5. Re-package: `bash scripts/package-skill.sh`. Inspect `dist/kami.zip` per §8.5.
6. Parity sweep: update `index-ko.html`, `llms.txt`, `sitemap.xml`, README install links, and any FAQ JSON-LD copy that mentions language coverage.
7. Final pass on `references/design.md` (fill any remaining KO notes) and `AGENTS.md` (note new template set in Repository Map; bump diagram/template counts only if used elsewhere).

**Phase 3 verification:** `--check`, `--verify`, `--check-rhythm slides slides-en slides-weasy-ko`, `stabilize.py all --report`, ZIP inspection, visual regression on a sample of two non-pilot templates (typically `resume-ko` and `slides-weasy-ko` as the highest-risk targets).

### Gates

- Phase 1 → Phase 2: `lint.py` pair generalization runs green on the current CN/EN set (no behavior change when KO is absent).
- Phase 2 → Phase 3: all six visual checks in §8.2 pass; canonical tuning values are committed to `references/design.md`.
- Phase 3 → done: §8.1–§8.5 all pass; `dist/kami.zip` regenerated and committed; cross-page references updated.

## 10. Risks & Mitigations

| Risk | Mitigation |
|---|---|
| `resume-ko` 2-page strict overflow when switching from TsangerJinKai (wider glyphs) to Nanum Myeongjo (narrower hangul) | Pilot tuning establishes safe body size and line-height; `stabilize.py resume-ko --strict` enforces 2 pages; visual regression mandated. |
| CI environment lacks Nanum Myeongjo, falls through to Apple SD Gothic Neo (unavailable on Linux) and lands on Noto Serif KR | `scripts/ensure-fonts.sh` Nanum step wired into the CI `verify-render` job; `KAMI_ALLOW_FALLBACK_ONLY` simulation run during Phase 2 to confirm acceptable degradation. |
| `package-skill.sh` exclusion patterns accidentally drop Nanum TTFs | Phase 1 task includes auditing exclusion patterns; Phase 3 ZIP inspection step is an explicit gate. |
| `font-synthesis` not respected by WeasyPrint version in use, producing fake bold | Verified during Phase 2 visual check #4; if synthesis still occurs, lock body weights to 400 only and use color/size for emphasis. |
| Sample content quality (Korean copywriting) lags template quality | Sample content is out of scope here; demo content can be iterated in a follow-up without re-touching the template/registry/lint layers. |
| Lint label rename (`CN/EN pair` → `CN-variant pair`) confuses contributors reading existing AGENTS.md notes | AGENTS.md verification section explicitly states the new wording in Phase 1. |

## 11. Open Items (resolved during implementation, not blockers)

- Exact `letter-spacing` and `line-height` numeric values for hangul — determined empirically in Phase 2.
- Whether `equity-report-ko` data tables benefit from `D2Coding` over `JetBrains Mono` — decided in Phase 3 visual review.
- Whether new topics introduced for KO demos (long-doc, portfolio, equity-report, changelog) should also be added for CN/EN later — out of scope here; tracked as a follow-up.

## 12. Deliverables Checklist

- [ ] `assets/fonts/NanumMyeongjo-Regular.ttf`, `-Bold.ttf`, `LICENSE-NanumMyeongjo.txt`
- [ ] 9 new `*-ko.html` templates + 1 `slides-ko.py`
- [ ] `scripts/shared.py` registry updates (9 HTML + 1 screen)
- [ ] `scripts/lint.py` pair generalization
- [ ] `references/cross_template_diff_allowlist.json` description update
- [ ] `references/design.md` "KO locale tuning" section with locked numeric values
- [ ] `scripts/ensure-fonts.sh` Nanum entries
- [ ] `AGENTS.md` Fonts / Repository Map / Verification updates
- [ ] `scripts/package-skill.sh` Nanum inclusion confirmation
- [ ] 10 demo sets under `assets/demos/`
- [ ] `dist/kami.zip` regenerated and committed
- [ ] `index-ko.html`, `llms.txt`, `sitemap.xml`, README cross-references updated
- [ ] All §8 verification gates pass
