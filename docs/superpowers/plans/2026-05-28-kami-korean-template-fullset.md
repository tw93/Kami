# Kami Korean Template Full-Set Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a full Korean (`-ko`) variant family to Kami's editorial template system using Nanum Myeongjo as primary serif, mirroring existing CN/EN parity across 10 outputs.

**Architecture:** Replicate the CN/EN sibling pattern as a third sibling (CN/EN/KO). Generalize the existing `_pair_names` lint helper to cover any `-en`/`-ko` variant of a base template; otherwise extend registries, fonts, and demos without introducing new abstractions. Three phases: infra → pilot (`one-pager-ko`) → roll out remaining 9 + finalize.

**Tech Stack:** Python 3 (stdlib only), bash, WeasyPrint for HTML→PDF, python-pptx for slides PPTX, Nanum Myeongjo (OFL).

**Spec:** `docs/superpowers/specs/2026-05-28-kami-korean-template-fullset-design.md`

---

## Phase 1 — Infrastructure

### Task 1: Acquire and commit Nanum Myeongjo font files

**Files:**
- Create: `assets/fonts/NanumMyeongjo-Regular.ttf` (binary, ~4 MB)
- Create: `assets/fonts/NanumMyeongjo-Bold.ttf` (binary, ~4 MB)
- Create: `assets/fonts/LICENSE-NanumMyeongjo.txt`

- [ ] **Step 1: Download Nanum Myeongjo Regular and Bold**

Download the official OFL TTFs from Google Fonts (static files) or Naver. Verify each file is between 3 MB and 6 MB:

```bash
cd /Users/glen/private_qazz92/Kami
curl -fSL "https://github.com/google/fonts/raw/main/ofl/nanummyeongjo/NanumMyeongjo-Regular.ttf" \
  -o assets/fonts/NanumMyeongjo-Regular.ttf
curl -fSL "https://github.com/google/fonts/raw/main/ofl/nanummyeongjo/NanumMyeongjo-Bold.ttf" \
  -o assets/fonts/NanumMyeongjo-Bold.ttf
ls -lh assets/fonts/NanumMyeongjo-*.ttf
```

Expected: two files each in the 3–6 MB band. If the GitHub raw URL ever shifts, use `https://fonts.google.com/specimen/Nanum+Myeongjo` → "Download family" and copy the two static files into place.

- [ ] **Step 2: Write the OFL license file**

Create `assets/fonts/LICENSE-NanumMyeongjo.txt` with the full SIL Open Font License 1.1 text (copy from `https://scripts.sil.org/cms/scripts/page.php?item_id=OFL_web`) and prepend:

```
Nanum Myeongjo
Copyright (c) 2010, NAVER Corporation (https://www.navercorp.com/)
This Font Software is licensed under the SIL Open Font License, Version 1.1.

Source: https://hangeul.naver.com/ (official) — also distributed via Google Fonts
        https://fonts.google.com/specimen/Nanum+Myeongjo

----

[FULL OFL 1.1 LICENSE TEXT BELOW]
```

- [ ] **Step 3: Verify file sizes are not truncated**

Run:

```bash
python3 -c "
from pathlib import Path
for n in ('NanumMyeongjo-Regular.ttf', 'NanumMyeongjo-Bold.ttf'):
    p = Path('assets/fonts') / n
    size = p.stat().st_size
    assert 3_000_000 <= size <= 6_500_000, f'{n} size {size} outside expected band'
    print(f'OK: {n} {size:,} bytes')
print('OK: Nanum Myeongjo font files present and sized correctly')
"
```

Expected: two `OK:` lines plus a final `OK:` summary.

- [ ] **Step 4: Verify TTF magic bytes**

Both files must start with the OpenType/TrueType signature (`\x00\x01\x00\x00`). Run:

```bash
python3 -c "
for n in ('NanumMyeongjo-Regular.ttf', 'NanumMyeongjo-Bold.ttf'):
    with open(f'assets/fonts/{n}', 'rb') as f:
        head = f.read(4)
    assert head == b'\x00\x01\x00\x00', f'{n} not a TrueType file: {head!r}'
    print(f'OK: {n} TTF magic verified')
"
```

Expected: two `OK:` lines.

- [ ] **Step 5: Commit fonts and license**

```bash
git add assets/fonts/NanumMyeongjo-Regular.ttf assets/fonts/NanumMyeongjo-Bold.ttf assets/fonts/LICENSE-NanumMyeongjo.txt
git commit -m "$(cat <<'EOF'
chore: add Nanum Myeongjo fonts (OFL) for upcoming KO templates

Bundles Regular and Bold weights from Naver / Google Fonts under the SIL
Open Font License 1.1. License text and source URL included alongside the
TTFs so downstream package consumers retain attribution.
EOF
)"
```

---

### Task 2: Generalize lint pair detection (CN↔EN + CN↔KO)

**Files:**
- Modify: `scripts/lint.py` (around lines 196–280: `_pair_names` and `check_cross_template_consistency`)
- Modify: `scripts/tests/test_build.py` (add KO pair-detection test)

- [ ] **Step 1: Add the failing test in `scripts/tests/test_build.py`**

Locate the existing pair-related assertions in `scripts/tests/test_build.py` (search for `_pair_names`). Add a new test function near them and call it from the test runner. Append at an appropriate location in the file:

```python
def test_pair_names_includes_ko_variants_when_present(tmp_path):
    """`_pair_names` must yield (base, base-ko) pairs in addition to (base, base-en)."""
    # _pair_names reads from HTML_TEMPLATES / SCREEN_TEMPLATES at import time, so
    # monkey-patch the module-level set used inside the function via a small fixture.
    import build as build_mod
    captured = list(build_mod._pair_names())
    bases = {base for base, _ in captured}
    # Sanity: existing CN/EN pairs still detected.
    assert ("one-pager", "one-pager-en") in captured, "CN/EN pair regressed"
    # KO detection is conditional on KO templates being registered; this test
    # documents the contract: any base whose `-ko` sibling is present in the
    # registry must appear as a (base, base-ko) pair.
    from shared import HTML_TEMPLATES, SCREEN_TEMPLATES
    seen = set(HTML_TEMPLATES) | set(SCREEN_TEMPLATES)
    for base in bases:
        ko_name = f"{base}-ko"
        if ko_name in seen:
            assert (base, ko_name) in captured, f"KO sibling for {base} not paired"
```

Then register the test by appending its call into the runner section near the bottom of the file (look for the block of `test_*` function calls):

```python
test_pair_names_includes_ko_variants_when_present(tempfile.TemporaryDirectory().name)
```

- [ ] **Step 2: Run the test to verify it passes (baseline) before changing lint**

Run:

```bash
python3 scripts/tests/test_build.py 2>&1 | tail -20
```

Expected: the new test prints `OK:` even before lint changes, because no `-ko` templates are registered yet — the assertion body is vacuously true. The point of the test is to lock the *contract* so the upcoming generalization does not regress CN/EN, and to assert KO behavior the moment a KO template appears in the registry.

- [ ] **Step 3: Generalize `_pair_names` in `scripts/lint.py`**

Replace the existing definition (currently at `scripts/lint.py:207`):

```python
def _pair_names() -> list[tuple[str, str]]:
    """Return [(cn_name, en_name), ...] for every CN template that has an -en sibling."""
    pairs: list[tuple[str, str]] = []
    seen = set(HTML_TEMPLATES) | set(SCREEN_TEMPLATES)
    for name in sorted(seen):
        if name.endswith("-en"):
            continue
        en_name = f"{name}-en"
        if en_name in seen:
            pairs.append((name, en_name))
    return pairs
```

with the generalized version:

```python
_VARIANT_SUFFIXES: tuple[str, ...] = ("-en", "-ko")


def _pair_names() -> list[tuple[str, str]]:
    """Return [(base_name, variant_name), ...] for every base template that has
    one of the recognized locale-variant siblings (`-en`, `-ko`).

    A base template is any registered name that does not itself end in a
    recognized variant suffix.
    """
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

- [ ] **Step 4: Update `check_cross_template_consistency` log strings**

In the same file, find the existing function body. Update the drift-tuple comment and the OK/error messages so the labels read "base-variant" instead of "CN/EN".

Replace:

```python
    drift: list[tuple[str, str, str, str]] = []  # (pair, var, cn_value, en_value)
```

with:

```python
    drift: list[tuple[str, str, str, str]] = []  # (pair, var, base_value, variant_value)
```

Replace the loop header:

```python
    for cn_name, en_name in pairs:
        try:
            cn_path, _ = _source_for(cn_name)
            en_path, _ = _source_for(en_name)
```

with:

```python
    for base_name, variant_name in pairs:
        try:
            base_path, _ = _source_for(base_name)
            variant_path, _ = _source_for(variant_name)
```

Then rename all subsequent references in the loop body so `cn_path` → `base_path`, `en_path` → `variant_path`, `cn_vars` → `base_vars`, `en_vars` → `variant_vars`, `cn_name` → `base_name`, `en_name` → `variant_name`. Update the verbose print:

```python
        if verbose:
            print(f"  pair {base_name}/{variant_name}: checked {len(shared_keys)} shared vars")
```

And the success / drift output:

```python
    if not drift:
        print(f"OK: cross-template :root vars in sync across {len(pairs)} base-variant pair(s)")
        return 0

    print(f"\n[cross-template-drift] {len(drift)}")
    for pair, var, base_val, variant_val in drift:
        print(f"  {pair}: {var} base={base_val} variant={variant_val}")
    return 1
```

Also update the multi-line header comment around `scripts/lint.py:196–205` so the wording reflects multi-variant coverage:

```python
# This check pairs each base template (e.g. `foo.html`) with every recognized
# locale variant (`foo-en.html`, `foo-ko.html`), parses the `:root { ... }`
# block of each, and flags variables that differ. Font-stack variables
# (`--serif`, `--sans`, `--mono`, `--latin-ui`) are allowlisted because each
# locale deliberately uses different fonts.
```

- [ ] **Step 5: Run the lint test suite and full --check**

```bash
python3 scripts/tests/test_build.py 2>&1 | tail -10
python3 scripts/build.py --check 2>&1 | tail -10
```

Expected: `test_build.py` ends with `OK: ... tests passed, 0 failed.` (or whatever the existing summary format is — same line as before). `build.py --check` ends with `OK: cross-template :root vars in sync across N base-variant pair(s)` where N equals the previous CN/EN pair count.

- [ ] **Step 6: Commit lint generalization**

```bash
git add scripts/lint.py scripts/tests/test_build.py
git commit -m "$(cat <<'EOF'
refactor: generalize lint pair detection for KO variants

Replaces the CN/EN-only pair builder with a variant-suffix table so KO
templates land in the cross-template :root drift check as soon as they
are registered. Output labels switch from "CN/EN pair" to
"base-variant pair" to keep the wording locale-neutral. Existing CN/EN
behavior is unchanged.
EOF
)"
```

---

### Task 3: Update the cross-template diff allowlist description

**Files:**
- Modify: `references/cross_template_diff_allowlist.json`

- [ ] **Step 1: Update the `_description` field**

Replace the existing `_description` value in `references/cross_template_diff_allowlist.json`:

```json
{
  "_description": "CSS variables in :root that may legitimately differ between a base CN template and any of its locale variants (-en, -ko). Anything not listed here must match across the base and each variant.",
  "always_allowed": [
    "--serif",
    "--sans",
    "--mono",
    "--latin-ui"
  ],
  "per_pair_allowed": {
    "_doc": "key = base template name (e.g. 'one-pager'); value = list of additional CSS variables that may differ for any variant of that base"
  }
}
```

- [ ] **Step 2: Verify JSON parses**

```bash
python3 -c "import json; json.load(open('references/cross_template_diff_allowlist.json'))"
```

Expected: no output (success).

- [ ] **Step 3: Re-run --check**

```bash
python3 scripts/build.py --check 2>&1 | tail -5
```

Expected: green run.

- [ ] **Step 4: Commit**

```bash
git add references/cross_template_diff_allowlist.json
git commit -m "docs: extend cross-template allowlist description to KO variants"
```

---

### Task 4: Extend `scripts/ensure-fonts.sh` with Nanum Myeongjo

**Files:**
- Modify: `scripts/ensure-fonts.sh`

- [ ] **Step 1: Add Nanum to the parallel arrays and download loop**

Inside `scripts/ensure-fonts.sh`, just below the TsangerJinKai parallel-array declarations, add a second pair of parallel arrays and a second `for` loop that mirrors the existing pattern. Insert the additions so the script:

1. Keeps the existing TsangerJinKai handling unchanged.
2. After the TsangerJinKai block, checks Nanum Myeongjo presence and downloads from CDN mirrors if missing.

Replace the file body with:

```bash
#!/usr/bin/env bash
set -euo pipefail

# Portable across bash 3.2+ (macOS stock /bin/bash) and bash 4+ (Linux, Homebrew).
# Avoids `declare -A` so the script runs on a fresh macOS without `brew install bash`.

FONT_DIR="$(cd "$(dirname "$0")/../assets/fonts" && pwd)"
MIN_SIZE_CN=10000000  # 10MB for TsangerJinKai (large CJK glyph set)
MIN_SIZE_KO=2500000   # 2.5MB for Nanum Myeongjo (smaller per-weight)

# --- TsangerJinKai (existing) -----------------------------------------------
CN_NAMES=("仓耳今楷02-W04.ttf" "仓耳今楷02-W05.ttf")
LOCAL_NAMES=("TsangerJinKai02-W04.ttf" "TsangerJinKai02-W05.ttf")

# --- Nanum Myeongjo (new) ---------------------------------------------------
NANUM_NAMES=("NanumMyeongjo-Regular.ttf" "NanumMyeongjo-Bold.ttf")

# Mirror order is intentionally jsdmirror-first here, opposite of the
# templates' @font-face fallback (which lists jsdelivr first). Reasoning:
# this script runs interactively when fonts are missing locally, often from
# China where jsdmirror is reachable and faster than jsdelivr; templates run
# anywhere and prioritize jsdelivr's broader global coverage.
MIRROR_SOURCES=(
  "https://cdn.jsdmirror.com/gh/tw93/Kami@main/assets/fonts"
  "https://cdn.jsdelivr.net/gh/tw93/Kami@main/assets/fonts"
)

check_size() {
  local file="$1"
  local min_size="$2"
  [[ -f "$file" ]] || return 1
  local size
  size=$(wc -c < "$file" | tr -d ' ')
  [[ "$size" -ge "$min_size" ]]
}

download_tsanger() {
  local cn_name="$1"
  local local_name="$2"
  local target="$FONT_DIR/$local_name"

  # Source 1: official tsanger.cn
  local official_url="https://tsanger.cn/download/${cn_name}"
  echo "  Trying: tsanger.cn (official)"
  if curl --retry 2 --connect-timeout 15 --max-time 300 -fSL "$official_url" -o "$target.tmp" 2>/dev/null; then
    if check_size "$target.tmp" "$MIN_SIZE_CN"; then
      mv "$target.tmp" "$target"
      echo "  OK: $local_name downloaded ($(du -h "$target" | cut -f1))"
      return 0
    else
      rm -f "$target.tmp"
    fi
  else
    rm -f "$target.tmp"
  fi

  # Source 2+: CDN mirrors (already named TsangerJinKai02-W0x.ttf)
  for src in "${MIRROR_SOURCES[@]}"; do
    local url="$src/$local_name"
    echo "  Trying: $url"
    if curl --retry 2 --connect-timeout 15 --max-time 300 -fSL "$url" -o "$target.tmp" 2>/dev/null; then
      if check_size "$target.tmp" "$MIN_SIZE_CN"; then
        mv "$target.tmp" "$target"
        echo "  OK: $local_name downloaded ($(du -h "$target" | cut -f1))"
        return 0
      else
        rm -f "$target.tmp"
      fi
    else
      rm -f "$target.tmp"
    fi
  done

  echo "  ERROR: all sources failed for $local_name"
  return 1
}

download_nanum() {
  local local_name="$1"
  local target="$FONT_DIR/$local_name"

  for src in "${MIRROR_SOURCES[@]}"; do
    local url="$src/$local_name"
    echo "  Trying: $url"
    if curl --retry 2 --connect-timeout 15 --max-time 300 -fSL "$url" -o "$target.tmp" 2>/dev/null; then
      if check_size "$target.tmp" "$MIN_SIZE_KO"; then
        mv "$target.tmp" "$target"
        echo "  OK: $local_name downloaded ($(du -h "$target" | cut -f1))"
        return 0
      else
        rm -f "$target.tmp"
      fi
    else
      rm -f "$target.tmp"
    fi
  done

  echo "  ERROR: all sources failed for $local_name"
  return 1
}

mkdir -p "$FONT_DIR"

# --- TsangerJinKai check ----------------------------------------------------
cn_all_present=true
for local_name in "${LOCAL_NAMES[@]}"; do
  if ! check_size "$FONT_DIR/$local_name" "$MIN_SIZE_CN"; then
    cn_all_present=false
    break
  fi
done

if $cn_all_present; then
  echo "OK: TsangerJinKai fonts present"
else
  echo "Downloading TsangerJinKai fonts..."
  cn_failed=0
  for i in "${!CN_NAMES[@]}"; do
    cn_name="${CN_NAMES[$i]}"
    local_name="${LOCAL_NAMES[$i]}"
    if check_size "$FONT_DIR/$local_name" "$MIN_SIZE_CN"; then
      echo "  OK: $local_name already present"
      continue
    fi
    if ! download_tsanger "$cn_name" "$local_name"; then
      cn_failed=$((cn_failed + 1))
    fi
  done
  if [[ "$cn_failed" -gt 0 ]]; then
    echo ""
    echo "Some TsangerJinKai files could not be downloaded. Alternatives:"
    echo "  1. Install Source Han Serif SC: brew install --cask font-source-han-serif-sc"
    echo "  2. Copy TsangerJinKai02-W04.ttf and W05.ttf manually into $FONT_DIR"
    # Don't exit yet — try Nanum too.
  fi
fi

# --- Nanum Myeongjo check ---------------------------------------------------
ko_all_present=true
for local_name in "${NANUM_NAMES[@]}"; do
  if ! check_size "$FONT_DIR/$local_name" "$MIN_SIZE_KO"; then
    ko_all_present=false
    break
  fi
done

if $ko_all_present; then
  echo "OK: Nanum Myeongjo fonts present"
else
  echo "Downloading Nanum Myeongjo fonts..."
  ko_failed=0
  for local_name in "${NANUM_NAMES[@]}"; do
    if check_size "$FONT_DIR/$local_name" "$MIN_SIZE_KO"; then
      echo "  OK: $local_name already present"
      continue
    fi
    if ! download_nanum "$local_name"; then
      ko_failed=$((ko_failed + 1))
    fi
  done
  if [[ "$ko_failed" -gt 0 ]]; then
    echo ""
    echo "Some Nanum Myeongjo files could not be downloaded. Alternatives:"
    echo "  1. Download from https://fonts.google.com/specimen/Nanum+Myeongjo"
    echo "  2. Copy NanumMyeongjo-Regular.ttf and -Bold.ttf manually into $FONT_DIR"
    exit 1
  fi
fi

echo "OK: all fonts ready"
```

- [ ] **Step 2: Smoke-test the script with fonts already present**

```bash
bash scripts/ensure-fonts.sh
```

Expected: prints `OK: TsangerJinKai fonts present` and `OK: Nanum Myeongjo fonts present`, then `OK: all fonts ready`.

- [ ] **Step 3: Smoke-test the download path by temporarily renaming one Nanum file**

```bash
mv assets/fonts/NanumMyeongjo-Regular.ttf assets/fonts/NanumMyeongjo-Regular.ttf.bak
bash scripts/ensure-fonts.sh || true
ls -lh assets/fonts/NanumMyeongjo-Regular.ttf || echo "download failed (acceptable in offline test)"
# Restore from backup if download didn't repopulate
if [[ ! -s assets/fonts/NanumMyeongjo-Regular.ttf ]]; then
  mv assets/fonts/NanumMyeongjo-Regular.ttf.bak assets/fonts/NanumMyeongjo-Regular.ttf
else
  rm -f assets/fonts/NanumMyeongjo-Regular.ttf.bak
fi
```

Expected: either the script downloads the file from jsdelivr (it should succeed once Task 1's commit has propagated to the CDN — this may take a few minutes on the first run), or the restore step recovers the file. Final state must have `NanumMyeongjo-Regular.ttf` present.

- [ ] **Step 4: Commit**

```bash
git add scripts/ensure-fonts.sh
git commit -m "$(cat <<'EOF'
chore: extend ensure-fonts.sh with Nanum Myeongjo recovery

Mirrors the existing TsangerJinKai download flow for Nanum Regular/Bold
with a separate minimum-size threshold appropriate to the smaller hangul
font files. Both checks run independently so a missing CN font doesn't
block KO recovery and vice versa.
EOF
)"
```

---

### Task 5: Update `AGENTS.md` with KO references

**Files:**
- Modify: `AGENTS.md`

- [ ] **Step 1: Update the Fonts section**

Find the Fonts section near the bottom of `AGENTS.md` (currently around lines 175–181). Replace it with:

```markdown
## Fonts

- Chinese templates use TsangerJinKai02 W04/W05. Commercial use requires the appropriate font license.
- If TsangerJinKai is unavailable, fall back through Source Han Serif SC, Noto Serif CJK SC, Songti SC, STSong, then Georgia.
- English templates use Charter serif. Japanese output uses YuMincho first, then Hiragino Mincho ProN, Noto Serif CJK JP, Source Han Serif JP, TsangerJinKai02, and generic serif.
- Korean templates use Nanum Myeongjo (OFL, Naver). Fallback chain: Nanum Myeongjo, Apple SD Gothic Neo, Noto Serif KR, Source Han Serif K, AppleMyungjo, Charter, Georgia.
- Claude Desktop ZIPs bundle Nanum Myeongjo (OFL allows redistribution) but do not bundle TsangerJinKai TTF files. Run `bash scripts/ensure-fonts.sh` before building Chinese documents when fonts are missing.
```

- [ ] **Step 2: Update the Repository Map**

Find the Repository Map block (currently around lines 9–48). In the `assets/templates/` line, the existing entry stays. Just below the public-site entrypoints line (`index.html`, `index-zh.html`, `index-en.html`, `index-ja.html`), update to include `index-ko.html`:

Replace:

```markdown
- `index.html`, `index-zh.html`, `index-en.html`, `index-ja.html` - public site entrypoints.
```

with:

```markdown
- `index.html`, `index-zh.html`, `index-en.html`, `index-ja.html`, `index-ko.html` - public site entrypoints.
```

And update the trailing reference-only line to mention KO:

Replace:

```markdown
Reference docs are English-only. Language-specific output differences belong in templates, not duplicated reference files.
```

with:

```markdown
Reference docs are English-only. Language-specific output differences (CN/EN/KO) belong in templates, not duplicated reference files.
```

- [ ] **Step 3: Update the Verification section**

Find the Verification section (currently around lines 153–162). Replace the `--check` bullet:

```markdown
- Template, CSS, or script changes: run `python3 scripts/build.py --check` (CSS lint + token sync + CN/EN cross-template `:root` consistency) and `python3 scripts/build.py --verify`.
```

with:

```markdown
- Template, CSS, or script changes: run `python3 scripts/build.py --check` (CSS lint + token sync + base/variant cross-template `:root` consistency, currently CN↔EN and CN↔KO) and `python3 scripts/build.py --verify`.
```

- [ ] **Step 4: Verify markdown lint manually**

```bash
grep -n "Korean\|Nanum\|index-ko" AGENTS.md
```

Expected: three lines minimum — Fonts section, Repository Map line, plus any other Korean-related references.

- [ ] **Step 5: Commit**

```bash
git add AGENTS.md
git commit -m "docs: note Korean template support and Nanum Myeongjo fallback chain"
```

---

### Task 6: Add a "KO locale tuning" stub to `references/design.md`

**Files:**
- Modify: `references/design.md`

- [ ] **Step 1: Locate the existing CN/EN locale notes**

```bash
grep -n "CN locale\|EN locale\|locale tuning\|TsangerJinKai\|Charter" references/design.md | head
```

Note the line number of the section where existing locale tuning notes live.

- [ ] **Step 2: Append a "KO locale tuning" section**

Append at the end of `references/design.md` (or adjacent to existing locale notes if a "Locale tuning" cluster already exists — judgment call by reading the surrounding 30 lines):

```markdown
## KO locale tuning

Korean templates use Nanum Myeongjo (OFL, Naver Corp.) as the primary serif.
The font's hangul metrics differ from TsangerJinKai (CN) and Charter (EN), so
the CN per-component overrides for `h1` letter-spacing and line-height must be
re-tuned. Canonical values are locked during the pilot (`one-pager-ko`) and
applied verbatim across the remaining KO templates.

Canonical values (to be filled in by the `one-pager-ko` pilot):

- Body `font-size`: TBD pt (pilot baseline starts at 10pt, matching CN one-pager)
- Body `line-height`: TBD (pilot baseline starts at CN value)
- Body `letter-spacing`: TBD pt (pilot baseline starts at CN value)
- H1 `font-size`: TBD pt
- H1 `letter-spacing`: TBD
- `font-synthesis: none;` MUST be applied to the body rule to prevent
  WeasyPrint from synthesizing fake bold when Bold weight resolution fails
  through fallbacks.

Fallback chain (consistent across all KO templates):

```css
--serif: "NanumMyeongjo", "Apple SD Gothic Neo", "Noto Serif KR",
         "Source Han Serif K", "AppleMyungjo", Charter, Georgia, serif;
--sans:  "Apple SD Gothic Neo", "Noto Sans KR", "Malgun Gothic",
         -apple-system, "Segoe UI", Helvetica, Arial, sans-serif;
--mono:  "JetBrains Mono", "D2Coding", "SF Mono", "Fira Code",
         Consolas, Monaco, monospace;
--latin-ui: "Inter", -apple-system, "Segoe UI", Helvetica, Arial, sans-serif;
```

The pilot updates the TBD entries above with concrete numeric values before
the remaining KO templates are forked.
```

- [ ] **Step 3: Verify the section reads sensibly**

```bash
tail -50 references/design.md
```

Expected: the new section is visible and self-contained.

- [ ] **Step 4: Commit**

```bash
git add references/design.md
git commit -m "docs: add KO locale tuning stub for Nanum Myeongjo pilot"
```

---

## Phase 2 — Pilot (`one-pager-ko`)

### Task 7: Fork `one-pager-ko.html`

**Files:**
- Create: `assets/templates/one-pager-ko.html`

- [ ] **Step 1: Copy `one-pager.html` to `one-pager-ko.html` as a starting point**

```bash
cp assets/templates/one-pager.html assets/templates/one-pager-ko.html
```

- [ ] **Step 2: Update `<html lang>` and header comment**

In `assets/templates/one-pager-ko.html`, replace the leading comment block and the `<html>` tag.

Replace:

```html
<!-- ==================================================================
     ONE-PAGER TEMPLATE · parchment design system
     单页 A4 方案/报告/执行摘要
     改完跑：python3 -c "from weasyprint import HTML; HTML('one-pager.html').write_pdf('out.pdf')"
     目标：页数必须 == 1
     ================================================================== -->
<html lang="zh-CN">
```

with:

```html
<!-- ==================================================================
     ONE-PAGER TEMPLATE (KO) · parchment design system
     단일 A4 제안서/리포트/요약서
     변경 후 실행: python3 -c "from weasyprint import HTML; HTML('one-pager-ko.html').write_pdf('out.pdf')"
     목표: 페이지 수 == 1
     ================================================================== -->
<html lang="ko">
```

- [ ] **Step 3: Replace the `@font-face` blocks**

Replace:

```html
  /* Regular weight */
  @font-face {
    font-family: "TsangerJinKai02";
    src: url("../fonts/TsangerJinKai02-W04.ttf") format("truetype"),
       url("https://cdn.jsdelivr.net/gh/tw93/Kami@main/assets/fonts/TsangerJinKai02-W04.ttf") format("truetype");
    font-weight: 400;
    font-style: normal;
  }

  /* Bold weight - W05 for all bold variants */
  @font-face {
    font-family: "TsangerJinKai02";
    src: url("../fonts/TsangerJinKai02-W05.ttf") format("truetype"),
       url("https://cdn.jsdelivr.net/gh/tw93/Kami@main/assets/fonts/TsangerJinKai02-W05.ttf") format("truetype");
    font-weight: 500;
    font-style: normal;
  }
```

with:

```html
  /* Regular weight */
  @font-face {
    font-family: "NanumMyeongjo";
    src: url("../fonts/NanumMyeongjo-Regular.ttf") format("truetype"),
       url("https://cdn.jsdelivr.net/gh/tw93/Kami@main/assets/fonts/NanumMyeongjo-Regular.ttf") format("truetype");
    font-weight: 400;
    font-style: normal;
  }

  /* Bold weight */
  @font-face {
    font-family: "NanumMyeongjo";
    src: url("../fonts/NanumMyeongjo-Bold.ttf") format("truetype"),
       url("https://cdn.jsdelivr.net/gh/tw93/Kami@main/assets/fonts/NanumMyeongjo-Bold.ttf") format("truetype");
    font-weight: 700;
    font-style: normal;
  }
```

- [ ] **Step 4: Replace the `:root` font variables**

Replace the existing `--serif` and `--sans` lines inside `:root`:

```css
    --serif: "TsangerJinKai02", "Source Han Serif SC", "Noto Serif CJK SC", "Songti SC", "STSong", Georgia, serif;
    --sans: var(--serif);
```

with:

```css
    --serif: "NanumMyeongjo", "Apple SD Gothic Neo", "Noto Serif KR", "Source Han Serif K", "AppleMyungjo", Charter, Georgia, serif;
    --sans: var(--serif);
```

- [ ] **Step 5: Add `font-synthesis: none;` to the body rule**

Find the existing body rule:

```css
  body {
    color: var(--near-black);
    font-family: var(--serif);
    font-size: 10pt;
    line-height: 1.45;
    letter-spacing: 0.3pt;
  }
```

Replace with:

```css
  body {
    color: var(--near-black);
    font-family: var(--serif);
    font-size: 10pt;
    line-height: 1.45;
    letter-spacing: 0.3pt;
    font-synthesis: none;
  }
```

- [ ] **Step 6: Update the CN-specific H1 tuning comment**

Find the CN-specific tuning comment:

```css
  /* CN locale tuning: TsangerJinKai glyphs are wider per character, so H1 sits
     slightly smaller (24pt vs EN 26pt) with looser leading (1.15 vs EN 1.12)
     to keep optical density aligned across the two locales. */
```

Replace with:

```css
  /* KO locale tuning: Nanum Myeongjo hangul glyphs have a smaller optical body
     than TsangerJinKai. H1 starts at the CN baseline (24pt / line-height 1.15);
     adjust during pilot if hangul reads too tight or too loose, then lock into
     references/design.md and propagate to remaining KO templates. */
```

H1 numeric values stay at the CN baseline (24pt, 500 weight, 1.15 line-height) until Step 5 in Task 9 confirms them. Bold weight in the CN template is `500`; with Nanum the closest weight is `700` (Bold). If the visual check shows the H1 looks too light, change `font-weight: 500;` to `font-weight: 700;` during Task 9 tuning.

- [ ] **Step 7: Translate the placeholder strings to Korean**

Replace the CJK placeholders so authors using the template see Korean prompts:

```bash
python3 -c "
from pathlib import Path
import re
p = Path('assets/templates/one-pager-ko.html')
t = p.read_text(encoding='utf-8')
mapping = {
    '{{文档标题}}': '{{문서 제목}}',
    '{{作者}}':     '{{작성자}}',
    '{{摘要}}':     '{{요약}}',
    '{{关键词}}':   '{{키워드}}',
}
for k, v in mapping.items():
    t = t.replace(k, v)
p.write_text(t, encoding='utf-8')
print('OK: placeholders translated')
"
```

> Additional CN content strings inside the template body should be translated by hand during Task 9 when confirming the demo content. This step only updates the four `<meta>`-level placeholder tokens.

- [ ] **Step 8: Stage but do not commit yet**

Hold the commit until Task 8 registers the template, so the working tree change is atomic.

---

### Task 8: Register `one-pager-ko` in `scripts/shared.py`

**Files:**
- Modify: `scripts/shared.py:101-122` (the `HTML_TEMPLATES` dict)

- [ ] **Step 1: Add the KO entry to `HTML_TEMPLATES`**

In `scripts/shared.py`, locate the `HTML_TEMPLATES` block. Add `one-pager-ko` immediately below `resume-en`:

Replace:

```python
HTML_TEMPLATES: dict[str, TemplateSpec] = {
    # Core six
    "one-pager":    TemplateSpec("one-pager.html",    1, 1),
    "letter":       TemplateSpec("letter.html",       1, 1),
    "long-doc":     TemplateSpec("long-doc.html",     0, 9),
    "portfolio":    TemplateSpec("portfolio.html",    0, 8),
    "resume":       TemplateSpec("resume.html",       2, 2),
    "one-pager-en": TemplateSpec("one-pager-en.html", 1, 1),
    "letter-en":    TemplateSpec("letter-en.html",    1, 1),
    "long-doc-en":  TemplateSpec("long-doc-en.html",  0, 9),
    "portfolio-en": TemplateSpec("portfolio-en.html", 0, 8),
    "resume-en":    TemplateSpec("resume-en.html",    2, 2),
    # Equity report
```

with:

```python
HTML_TEMPLATES: dict[str, TemplateSpec] = {
    # Core six
    "one-pager":    TemplateSpec("one-pager.html",    1, 1),
    "letter":       TemplateSpec("letter.html",       1, 1),
    "long-doc":     TemplateSpec("long-doc.html",     0, 9),
    "portfolio":    TemplateSpec("portfolio.html",    0, 8),
    "resume":       TemplateSpec("resume.html",       2, 2),
    "one-pager-en": TemplateSpec("one-pager-en.html", 1, 1),
    "letter-en":    TemplateSpec("letter-en.html",    1, 1),
    "long-doc-en":  TemplateSpec("long-doc-en.html",  0, 9),
    "portfolio-en": TemplateSpec("portfolio-en.html", 0, 8),
    "resume-en":    TemplateSpec("resume-en.html",    2, 2),
    # Korean — added incrementally as templates land; see Phase 3 plan.
    "one-pager-ko": TemplateSpec("one-pager-ko.html", 1, 1),
    # Equity report
```

- [ ] **Step 2: Run `--check` to confirm lint passes**

```bash
python3 scripts/build.py --check 2>&1 | tail -10
```

Expected: ends with `OK: cross-template :root vars in sync across N base-variant pair(s)` where N has grown by 1 (the new CN↔KO `one-pager` pair).

- [ ] **Step 3: Run `--verify` for the new target**

```bash
python3 scripts/build.py --verify one-pager-ko 2>&1 | tail -20
```

Expected: PDF renders, page count is exactly 1, embedded font set includes `NanumMyeongjo` (or at least one Korean serif fallback if Nanum is unavailable on the build host).

If verify fails because the host lacks WeasyPrint or its native deps, follow `AGENTS.md` guidance and skip the render check temporarily, but the lint check above must still pass.

- [ ] **Step 4: Run the regression test suite**

```bash
python3 scripts/tests/test_build.py 2>&1 | tail -10
```

Expected: ends with `0 failed.`

- [ ] **Step 5: Commit pilot template + registry as one atomic change**

```bash
git add assets/templates/one-pager-ko.html scripts/shared.py
git commit -m "$(cat <<'EOF'
feat: add KO one-pager pilot template

Adds `one-pager-ko.html` as the canonical KO fork from the CN one-pager,
swapping the @font-face blocks and `:root` font variables to Nanum Myeongjo
(OFL, Naver) with the locale's fallback chain. Registers the template in
`HTML_TEMPLATES` with strict 1-page constraint. Layout, tokens, and spacing
remain identical to the CN base; only the locale variables differ.

This pilot establishes the canonical KO tuning values. Subsequent KO
templates inherit the same locale variables verbatim.
EOF
)"
```

---

### Task 9: Visually verify `one-pager-ko` and lock canonical tuning

**Files:**
- Modify: `assets/templates/one-pager-ko.html` (if tuning needs adjustment)
- Modify: `references/design.md` (lock final numeric values into the KO section)

- [ ] **Step 1: Build the pilot PDF**

```bash
python3 scripts/build.py one-pager-ko 2>&1 | tail -5
```

Expected: writes `dist/one-pager-ko.pdf`. If the build path differs, locate the output via:

```bash
find dist -name "one-pager-ko*.pdf" -mmin -5
```

- [ ] **Step 2: Inspect embedded fonts in the PDF**

```bash
python3 -c "
import sys
try:
    from pypdf import PdfReader
except ImportError:
    print('SKIP: pypdf not installed (install in a venv if needed)')
    sys.exit(0)
import re
from pathlib import Path
pdf = next(Path('dist').glob('one-pager-ko*.pdf'))
reader = PdfReader(str(pdf))
fonts = set()
for page in reader.pages:
    resources = page.get('/Resources') or {}
    font_dict = resources.get('/Font') or {}
    for f in font_dict.values():
        try:
            base = f.get_object().get('/BaseFont')
            if base:
                fonts.add(str(base))
        except Exception:
            pass
print('Embedded fonts:', sorted(fonts))
assert any('Nanum' in f or 'NanumMyeongjo' in f for f in fonts), 'Nanum Myeongjo not embedded'
print('OK: Nanum Myeongjo embedded in', pdf)
"
```

Expected: the printed font list contains a `NanumMyeongjo` entry. If it does not, ensure `bash scripts/ensure-fonts.sh` ran and `assets/fonts/NanumMyeongjo-*.ttf` are still present.

- [ ] **Step 3: Open the PDF and run the six visual checks (manual)**

Open `dist/one-pager-ko.pdf` in a PDF viewer. Verify, in order:

1. **Glyphs render**: every hangul character is a real glyph, not a missing-character square or a different-style fallback.
2. **H1 letter-spacing**: the title line reads naturally; characters are not visually colliding or floating apart. If too tight, increase `h1` `letter-spacing` (try `0.5pt` increments). If too airy, decrease.
3. **Body line-height**: a body paragraph of 4+ lines reads comfortably. If lines feel cramped, raise `line-height` from `1.45` toward `1.55` in `0.05` steps.
4. **No synthetic bold**: bold runs use the embedded Bold weight, not a synthesized version. Synthesized bold typically looks blurry or unevenly thickened. If detected, confirm `font-synthesis: none;` is on `body`.
5. **Latin/numerics fallback**: digits and any English words use Charter / Georgia rather than a system fallback font that breaks the editorial tone.
6. **Page count**: the PDF has exactly **1** page.

For each check that fails, edit `assets/templates/one-pager-ko.html` and rebuild:

```bash
python3 scripts/build.py one-pager-ko 2>&1 | tail -3
```

Iterate until all six checks pass.

- [ ] **Step 4: Lock final tuning values into `references/design.md`**

Edit `references/design.md` so the "KO locale tuning" section the Phase 1 stub created now lists the *actual* values used in the pilot. Replace each `TBD` line with the concrete value from the verified template. Example (use the actual values you settled on, not these literal numbers):

```markdown
- Body `font-size`: 10pt (matches CN one-pager)
- Body `line-height`: 1.5 (raised from CN 1.45 for hangul readability)
- Body `letter-spacing`: 0pt (CN's 0.3pt overcompensates for Nanum)
- H1 `font-size`: 24pt
- H1 `font-weight`: 700 (raised from CN 500 because Nanum Bold reads lighter)
- H1 `line-height`: 1.2 (raised from CN 1.15)
- H1 `letter-spacing`: -0.2pt
- `font-synthesis: none;` is applied to the body rule.
```

If any value in `one-pager-ko.html` was not changed from the CN baseline, list it as `<value> (matches CN baseline)` so the next forks know they can copy CN verbatim.

- [ ] **Step 5: Final regression**

```bash
python3 scripts/build.py --check 2>&1 | tail -5
python3 scripts/build.py --verify one-pager-ko 2>&1 | tail -10
python3 scripts/stabilize.py one-pager-ko --strict --report 2>&1 | tail -10
```

Expected: all three end on `OK:` lines. `--verify one-pager-ko` reports exactly 1 page.

- [ ] **Step 6: Commit pilot tuning lock-in**

```bash
git add assets/templates/one-pager-ko.html references/design.md
git commit -m "$(cat <<'EOF'
docs: lock KO locale tuning values from one-pager-ko pilot

Records the canonical Nanum Myeongjo tuning values (body font-size,
line-height, letter-spacing; H1 weight, leading, tracking;
font-synthesis policy) discovered during the one-pager-ko pilot. Subsequent
KO templates inherit these values verbatim.
EOF
)"
```

> If Step 4 produced no edits to `one-pager-ko.html` (CN baseline was already correct for KO), the commit may include only `references/design.md`. That's fine — the lock-in document is the deliverable.

---

### Task 10: Build `demo-kaku-ko` demo set

**Files:**
- Create: `assets/demos/demo-kaku-ko.html`
- Create: `assets/demos/demo-kaku-ko.pdf`
- Create: `assets/demos/demo-kaku-ko.png`

- [ ] **Step 1: Copy `demo-kaku.html` as a starting point and translate to Korean**

```bash
cp assets/demos/demo-kaku.html assets/demos/demo-kaku-ko.html
```

Then edit `assets/demos/demo-kaku-ko.html`:

1. Change `<html lang="zh-CN">` to `<html lang="ko">`.
2. Replace TsangerJinKai `@font-face` blocks with Nanum Myeongjo blocks (identical to the template — copy the two `@font-face` blocks from `assets/templates/one-pager-ko.html` directly).
3. Replace the `--serif` and `--sans` lines in `:root` with the KO chain (copy from `one-pager-ko.html`).
4. Translate body content to natural Korean. Keep the same structure (eyebrow, title, subtitle, sections, signature). The Kaku character name can stay as `Kaku` or be transliterated as `카쿠` — choose whichever sounds natural in Korean editorial copy. Replace company / location proper nouns that are CN-specific with Korean equivalents (fictional Korean companies are acceptable).

- [ ] **Step 2: Build the demo PDF**

```bash
python3 -c "
from weasyprint import HTML
HTML('assets/demos/demo-kaku-ko.html').write_pdf('assets/demos/demo-kaku-ko.pdf')
print('OK: built assets/demos/demo-kaku-ko.pdf')
"
ls -lh assets/demos/demo-kaku-ko.pdf
```

Expected: PDF is generated, file size is in the typical demo range (50 KB – 500 KB depending on content).

- [ ] **Step 3: Verify page count**

```bash
python3 -c "
from pypdf import PdfReader
r = PdfReader('assets/demos/demo-kaku-ko.pdf')
assert len(r.pages) == 1, f'expected 1 page, got {len(r.pages)}'
print('OK: demo-kaku-ko.pdf is 1 page')
"
```

Expected: prints `OK:` line.

- [ ] **Step 4: Capture the PNG screenshot**

```bash
pdftoppm -r 150 -f 1 -l 1 -png assets/demos/demo-kaku-ko.pdf /tmp/p
cp /tmp/p-1.png assets/demos/demo-kaku-ko.png
python3 -c "
from PIL import Image
im = Image.open('assets/demos/demo-kaku-ko.png')
assert im.size == (1241, 1754), f'expected 1241x1754, got {im.size}'
print(f'OK: PNG size {im.size}')
"
```

Expected: PNG is 1241×1754. If `pdftoppm` outputs a slightly different size (e.g. 1240×1754) due to rendering rounding, resize:

```bash
magick assets/demos/demo-kaku-ko.png -resize 1241x1754! assets/demos/demo-kaku-ko.png
```

- [ ] **Step 5: Commit the demo set**

```bash
git add assets/demos/demo-kaku-ko.html assets/demos/demo-kaku-ko.pdf assets/demos/demo-kaku-ko.png
git commit -m "feat: add KO one-pager demo (demo-kaku-ko)"
```

---

## Phase 3 — Remaining 9 templates + finalization

Phase 3 tasks (Tasks 11–18) all follow the same shape:

1. Copy the CN template to its `-ko` sibling.
2. Apply locale transformations (lang, `@font-face`, `:root --serif`/`--sans`, `font-synthesis: none;`).
3. Apply the canonical tuning values locked in Task 9 to the body and `h1` rules (only override CN baselines for variables the pilot actually changed; otherwise leave CN values untouched).
4. Register in `HTML_TEMPLATES` (or `SCREEN_TEMPLATES` for landing-page).
5. Build a demo set following Task 10's pattern.
6. Verify and commit.

Tasks 11–17 detail the specific deltas; Tasks 18–19 handle the slides-PPTX and landing-page cases that diverge from the standard pattern.

### Task 11: Fork `letter-ko.html` + demo

**Files:**
- Create: `assets/templates/letter-ko.html`
- Create: `assets/demos/demo-tesla-ko.{html,pdf,png}`
- Modify: `scripts/shared.py` (add `letter-ko` to `HTML_TEMPLATES`)

- [ ] **Step 1: Fork the template**

```bash
cp assets/templates/letter.html assets/templates/letter-ko.html
```

Apply the four locale transformations in the same order as Task 7 (steps 2–6), using the same `@font-face` blocks and `:root` lines. If Task 9 raised body `line-height` or changed H1 weight in `one-pager-ko.html`, apply the *same* changes to the body and `h1` rules in `letter-ko.html`. Translate the CN placeholder tokens (search for `{{...}}` and any CN section labels) into Korean.

- [ ] **Step 2: Register in `scripts/shared.py`**

Add directly below the existing `"one-pager-ko"` registry line:

```python
    "letter-ko":    TemplateSpec("letter-ko.html",    1, 1),
```

- [ ] **Step 3: Build and verify**

```bash
python3 scripts/build.py --check 2>&1 | tail -5
python3 scripts/build.py --verify letter-ko 2>&1 | tail -10
python3 scripts/stabilize.py letter-ko --strict --report 2>&1 | tail -10
```

Expected: all three end on `OK:` lines, page count exactly 1.

- [ ] **Step 4: Build the demo**

```bash
cp assets/demos/demo-tesla.html assets/demos/demo-tesla-ko.html
```

Edit `assets/demos/demo-tesla-ko.html` to apply the same locale swap and translate the content into Korean. Then:

```bash
python3 -c "from weasyprint import HTML; HTML('assets/demos/demo-tesla-ko.html').write_pdf('assets/demos/demo-tesla-ko.pdf')"
pdftoppm -r 150 -f 1 -l 1 -png assets/demos/demo-tesla-ko.pdf /tmp/p
cp /tmp/p-1.png assets/demos/demo-tesla-ko.png
python3 -c "
from PIL import Image
im = Image.open('assets/demos/demo-tesla-ko.png')
if im.size != (1241, 1754):
    im.resize((1241, 1754)).save('assets/demos/demo-tesla-ko.png')
print('OK: demo-tesla-ko.png 1241x1754')
"
```

- [ ] **Step 5: Commit**

```bash
git add assets/templates/letter-ko.html scripts/shared.py assets/demos/demo-tesla-ko.*
git commit -m "feat: add KO letter template + demo-tesla-ko"
```

---

### Task 12: Fork `long-doc-ko.html` + demo

**Files:**
- Create: `assets/templates/long-doc-ko.html`
- Create: `assets/demos/demo-longdoc-ko.{html,pdf,png}`
- Modify: `scripts/shared.py`

- [ ] **Step 1: Fork the template**

```bash
cp assets/templates/long-doc.html assets/templates/long-doc-ko.html
```

Apply Task 7 steps 2–6 transformations. Long-doc is multi-page (target 7±2); body line-height is the highest-impact variable for hangul comfort across many pages. If Task 9's body line-height was 1.5, apply that; if Task 9 kept 1.45, keep it.

- [ ] **Step 2: Register**

In `scripts/shared.py`, after the existing KO entries:

```python
    "long-doc-ko":  TemplateSpec("long-doc-ko.html",  0, 9),
```

- [ ] **Step 3: Build and verify**

```bash
python3 scripts/build.py --check 2>&1 | tail -5
python3 scripts/build.py --verify long-doc-ko 2>&1 | tail -10
python3 scripts/stabilize.py long-doc-ko --strict --report 2>&1 | tail -15
```

Expected: page count is in `7 ± 2` range. Stabilize keeps it ≤ 9 pages.

- [ ] **Step 4: Build the demo**

Long-doc has no existing CN topic demo (per Task 7.1 inventory). Create new KO-only content:

```bash
# Copy long-doc-ko template as the demo HTML starting point and fill with sample
# Korean content (a hypothetical research note, ~5 sections, ~6 pages).
cp assets/templates/long-doc-ko.html assets/demos/demo-longdoc-ko.html
```

Edit `assets/demos/demo-longdoc-ko.html`:

1. Update the `@font-face` `url(...)` paths from `../fonts/...` to `../../assets/fonts/...` so the demo file resolves the same font assets when viewed in-place. (Inspect another existing demo HTML to confirm the relative-path convention used in `assets/demos/`.)
2. Replace placeholder tokens with concrete Korean content. ~5 short sections about a topic of your choice (e.g. "한국어 타이포그래피 가이드" — a Korean typography guide).

Build PDF and PNG identically to Task 11 Step 4.

- [ ] **Step 5: Commit**

```bash
git add assets/templates/long-doc-ko.html scripts/shared.py assets/demos/demo-longdoc-ko.*
git commit -m "feat: add KO long-doc template + demo-longdoc-ko"
```

---

### Task 13: Fork `portfolio-ko.html` + demo

**Files:**
- Create: `assets/templates/portfolio-ko.html`
- Create: `assets/demos/demo-portfolio-ko.{html,pdf,png}`
- Modify: `scripts/shared.py`

- [ ] **Step 1: Fork**

```bash
cp assets/templates/portfolio.html assets/templates/portfolio-ko.html
```

Apply Task 7 transformations.

- [ ] **Step 2: Register**

```python
    "portfolio-ko": TemplateSpec("portfolio-ko.html", 0, 8),
```

- [ ] **Step 3: Build and verify**

```bash
python3 scripts/build.py --check 2>&1 | tail -5
python3 scripts/build.py --verify portfolio-ko 2>&1 | tail -10
python3 scripts/stabilize.py portfolio-ko --strict --report 2>&1 | tail -10
```

Expected: page count 6 ± 2.

- [ ] **Step 4: Demo**

No existing CN portfolio demo. Create a KO-only `demo-portfolio-ko` set with sample content (3–5 fictional portfolio items in Korean). Follow Task 12 Step 4 conventions for paths and PNG sizing.

- [ ] **Step 5: Commit**

```bash
git add assets/templates/portfolio-ko.html scripts/shared.py assets/demos/demo-portfolio-ko.*
git commit -m "feat: add KO portfolio template + demo-portfolio-ko"
```

---

### Task 14: Fork `resume-ko.html` + demo (strict 2-page)

**Files:**
- Create: `assets/templates/resume-ko.html`
- Create: `assets/demos/demo-musk-resume-ko.{html,pdf,png}`
- Modify: `scripts/shared.py`

> Highest regression risk in Phase 3: the strict 2-page constraint can break if Nanum Myeongjo's hangul glyphs shift body height per line. If the build comes out at 1 or 3 pages, the body font-size or line-height needs locale-specific tuning *in this template only*.

- [ ] **Step 1: Fork**

```bash
cp assets/templates/resume.html assets/templates/resume-ko.html
```

Apply Task 7 transformations.

- [ ] **Step 2: Register**

```python
    "resume-ko":    TemplateSpec("resume-ko.html",    2, 2),
```

- [ ] **Step 3: Build and verify with strict 2-page check**

```bash
python3 scripts/build.py --verify resume-ko 2>&1 | tail -10
```

Expected: exactly 2 pages.

If the result is 1 page (content too compact under Nanum metrics), reduce body `font-size` or tighten section spacing until 2 pages emerge. If the result is 3 pages (content overflows), the stabilizer can tighten:

```bash
python3 scripts/stabilize.py resume-ko --write --strict --report 2>&1 | tail -15
```

Iterate until 2 pages.

- [ ] **Step 4: Demo**

```bash
cp assets/demos/demo-musk-resume.html assets/demos/demo-musk-resume-ko.html
```

Apply locale swap and translate. The Musk resume narrative can either stay as Elon Musk's resume (translated to Korean), or be re-purposed to a fictional Korean executive. Translation is acceptable.

Build PDF (must be 2 pages) and PNG (page-1 capture per Task 11 Step 4).

- [ ] **Step 5: Commit**

```bash
git add assets/templates/resume-ko.html scripts/shared.py assets/demos/demo-musk-resume-ko.*
git commit -m "feat: add KO resume template (strict 2-page) + demo-musk-resume-ko"
```

---

### Task 15: Fork `equity-report-ko.html` + demo

**Files:**
- Create: `assets/templates/equity-report-ko.html`
- Create: `assets/demos/demo-equity-ko.{html,pdf,png}`
- Modify: `scripts/shared.py`

- [ ] **Step 1: Fork**

```bash
cp assets/templates/equity-report.html assets/templates/equity-report-ko.html
```

Apply Task 7 transformations. Equity-report has data tables that may use the `--mono` chain — confirm the mono variable in `:root` is set to a chain that contains a Korean-friendly mono fallback (D2Coding is the standard KR mono). Update if missing:

```css
    --mono: "JetBrains Mono", "D2Coding", "SF Mono", "Fira Code", Consolas, Monaco, monospace;
```

- [ ] **Step 2: Register**

```python
    "equity-report-ko": TemplateSpec("equity-report-ko.html", 3, 0),
```

- [ ] **Step 3: Build and verify**

```bash
python3 scripts/build.py --check 2>&1 | tail -5
python3 scripts/build.py --verify equity-report-ko 2>&1 | tail -10
```

Expected: page count 2–3. (Stabilize disabled for this template.)

- [ ] **Step 4: Demo**

No existing CN equity-report demo. Build `demo-equity-ko.html` with a fictional Korean company's equity research note.

- [ ] **Step 5: Commit**

```bash
git add assets/templates/equity-report-ko.html scripts/shared.py assets/demos/demo-equity-ko.*
git commit -m "feat: add KO equity-report template + demo-equity-ko"
```

---

### Task 16: Fork `changelog-ko.html` + demo

**Files:**
- Create: `assets/templates/changelog-ko.html`
- Create: `assets/demos/demo-changelog-ko.{html,pdf,png}`
- Modify: `scripts/shared.py`

- [ ] **Step 1: Fork**

```bash
cp assets/templates/changelog.html assets/templates/changelog-ko.html
```

Apply Task 7 transformations.

- [ ] **Step 2: Register**

```python
    "changelog-ko": TemplateSpec("changelog-ko.html", 2, 0),
```

- [ ] **Step 3: Build and verify**

```bash
python3 scripts/build.py --check 2>&1 | tail -5
python3 scripts/build.py --verify changelog-ko 2>&1 | tail -10
```

Expected: page count 1–2.

- [ ] **Step 4: Demo**

No existing CN changelog demo. Build `demo-changelog-ko.html` with a sample changelog (a few release entries in Korean).

- [ ] **Step 5: Commit**

```bash
git add assets/templates/changelog-ko.html scripts/shared.py assets/demos/demo-changelog-ko.*
git commit -m "feat: add KO changelog template + demo-changelog-ko"
```

---

### Task 17: Fork `slides-weasy-ko.html` + demo

**Files:**
- Create: `assets/templates/slides-weasy-ko.html`
- Create: `assets/demos/demo-agent-slides-ko.{html,pdf,png}`
- Modify: `scripts/shared.py`

- [ ] **Step 1: Fork**

```bash
cp assets/templates/slides-weasy.html assets/templates/slides-weasy-ko.html
```

Apply Task 7 transformations. Slides landscape templates emphasize H1 / display weights more than body, so re-confirm H1 weight (700 with Nanum Bold tends to read well at slide scale).

- [ ] **Step 2: Register**

```python
    "slides-weasy-ko": TemplateSpec("slides-weasy-ko.html", 0, 0),
```

- [ ] **Step 3: Build and verify**

```bash
python3 scripts/build.py --check 2>&1 | tail -5
python3 scripts/build.py --verify slides-weasy-ko 2>&1 | tail -10
python3 scripts/build.py --check-rhythm slides slides-en slides-weasy-ko 2>&1 | tail -10
```

Expected: page count 7 ± 3. Rhythm check ends `OK:`.

- [ ] **Step 4: Demo**

```bash
cp assets/demos/demo-agent-slides.html assets/demos/demo-agent-slides-ko.html
```

Apply locale swap. Translate slide titles and bullet content to Korean.

Build PDF then capture the two-page landscape stack PNG (per AGENTS.md slide demo rule):

```bash
python3 -c "from weasyprint import HTML; HTML('assets/demos/demo-agent-slides-ko.html').write_pdf('assets/demos/demo-agent-slides-ko.pdf')"
pdftoppm -r 150 -f 1 -l 2 -png assets/demos/demo-agent-slides-ko.pdf /tmp/sl
magick /tmp/sl-1.png -resize x867 /tmp/sl1.png
magick /tmp/sl-2.png -resize x867 /tmp/sl2.png
magick -size $(identify -format '%w' /tmp/sl1.png)x20 xc:'#f5f4ed' /tmp/gap.png
magick /tmp/sl1.png /tmp/gap.png /tmp/sl2.png -append /tmp/stacked.png
magick /tmp/stacked.png -gravity Center -background '#f5f4ed' -extent 1241x1754 assets/demos/demo-agent-slides-ko.png
python3 -c "
from PIL import Image
im = Image.open('assets/demos/demo-agent-slides-ko.png')
assert im.size == (1241, 1754), im.size
print('OK: slides demo PNG 1241x1754')
"
```

- [ ] **Step 5: Commit**

```bash
git add assets/templates/slides-weasy-ko.html scripts/shared.py assets/demos/demo-agent-slides-ko.{html,pdf,png}
git commit -m "feat: add KO slides-weasy template + demo-agent-slides-ko"
```

---

### Task 18: Create `slides-ko.py` (PPTX) + PPTX demo

**Files:**
- Create: `assets/templates/slides-ko.py`
- Create: `assets/demos/demo-agent-slides-ko.pptx`

- [ ] **Step 1: Copy `slides.py` as the starting point**

```bash
cp assets/templates/slides.py assets/templates/slides-ko.py
```

- [ ] **Step 2: Adjust the LANG dispatch and add a Korean serif constant**

Find the existing constants near `slides.py:39-44`:

```python
# Fonts. Single serif per page. PPT falls back on the viewer's system.
# For Japanese best-effort output, set LANG = "ja" before generating.
LANG = "zh"
CN_SERIF = "Source Han Serif SC"
JA_SERIF = "YuMincho"  # Windows: Yu Mincho; Linux: Noto Serif CJK JP

SERIF = JA_SERIF if LANG == "ja" else CN_SERIF
```

Replace with:

```python
# Fonts. Single serif per page. PPT falls back on the viewer's system.
# For non-default locales, set LANG = "ja" or LANG = "ko" before generating.
LANG = "ko"
CN_SERIF = "Source Han Serif SC"
JA_SERIF = "YuMincho"        # Windows: Yu Mincho; Linux: Noto Serif CJK JP
KO_SERIF = "NanumMyeongjo"   # Windows/macOS/Linux: Nanum Myeongjo (OFL, Naver)

if LANG == "ja":
    SERIF = JA_SERIF
elif LANG == "ko":
    SERIF = KO_SERIF
else:
    SERIF = CN_SERIF
```

- [ ] **Step 3: Update the file's header comment and output filename**

Find the script's top-of-file docstring and any hard-coded output paths. If `slides.py` writes to `slides.pptx`, update `slides-ko.py` to write to `slides-ko.pptx`:

```bash
grep -n "pptx\|filename\|output" assets/templates/slides-ko.py | head
```

Locate the `pptx_path` / `output_path` definition and rename to `slides-ko.pptx`. Translate any visible CN string literals (title text, default labels) to Korean.

- [ ] **Step 4: Run the script**

```bash
cd assets/templates && python3 slides-ko.py && cd ../..
ls -lh assets/templates/slides-ko.pptx 2>/dev/null || ls -lh slides-ko.pptx 2>/dev/null
```

Expected: a `.pptx` file is generated, file size > 50 KB.

- [ ] **Step 5: Move the PPTX to the demos directory**

```bash
mv assets/templates/slides-ko.pptx assets/demos/demo-agent-slides-ko.pptx 2>/dev/null || \
  mv slides-ko.pptx assets/demos/demo-agent-slides-ko.pptx
```

- [ ] **Step 6: Open the PPTX in a viewer (manual)**

Open `assets/demos/demo-agent-slides-ko.pptx` in PowerPoint or LibreOffice Impress. Confirm:
1. Korean text renders (not boxes/tofu).
2. NanumMyeongjo is the active font (visible in font name dropdown when text is selected).
3. Slide layout matches the CN PPTX visually.

If Korean does not render, the most likely cause is that the viewer doesn't have Nanum Myeongjo installed; the PPTX itself contains the correct font reference. Document any viewer-side rendering issues in `references/design.md` KO section.

- [ ] **Step 7: Commit**

```bash
git add assets/templates/slides-ko.py assets/demos/demo-agent-slides-ko.pptx
git commit -m "feat: add KO slides PPTX template + demo PPTX"
```

---

### Task 19: Fork `landing-page-ko.html` + demo screenshot

**Files:**
- Create: `assets/templates/landing-page-ko.html`
- Create: `assets/demos/demo-landing-ko.html`
- Create: `assets/demos/demo-landing-ko.png`
- Modify: `scripts/shared.py:124-127` (the `SCREEN_TEMPLATES` dict)

- [ ] **Step 1: Fork**

```bash
cp assets/templates/landing-page.html assets/templates/landing-page-ko.html
```

Apply locale transformations. `landing-page.html` uses an external jsdelivr `@font-face` URL pointing to a third-party Tsanger mirror (see line 53-60). For the KO variant:
1. Change `<html lang>` to `ko`.
2. Replace the two `@font-face` blocks with the standard Nanum Myeongjo blocks (use the repo's own `assets/fonts/...` paths plus the jsdelivr fallback — same pattern as document templates).
3. Replace `:root --serif` and `--sans` with the KO chains.

- [ ] **Step 2: Register in `SCREEN_TEMPLATES`**

In `scripts/shared.py`:

```python
SCREEN_TEMPLATES: dict[str, str] = {
    "landing-page":    "landing-page.html",
    "landing-page-en": "landing-page-en.html",
    "landing-page-ko": "landing-page-ko.html",
}
```

- [ ] **Step 3: Run lint**

```bash
python3 scripts/build.py --check 2>&1 | tail -5
```

Expected: passes (no PDF render check applies to screen templates).

- [ ] **Step 4: Build the demo**

The landing-page demo is browser-only — no PDF, no 1241×1754 print capture. Create a representative HTML demo:

```bash
cp assets/templates/landing-page-ko.html assets/demos/demo-landing-ko.html
```

Edit `assets/demos/demo-landing-ko.html` to (1) fix `@font-face` URLs to point one directory up (`../../assets/fonts/...`) matching other demos and (2) replace placeholder body content with concrete Korean copy.

Capture a screenshot via a headless browser. Choose the path most readily available on the maintainer's host:

```bash
# Option A: Playwright
python3 -c "
from playwright.sync_api import sync_playwright
with sync_playwright() as pw:
    browser = pw.chromium.launch()
    page = browser.new_page(viewport={'width': 1280, 'height': 1800})
    page.goto('file://' + __import__('os').path.abspath('assets/demos/demo-landing-ko.html'))
    page.screenshot(path='assets/demos/demo-landing-ko.png', full_page=True)
    browser.close()
print('OK: landing demo PNG captured')
" 2>/dev/null || echo "playwright unavailable, falling back"

# Option B: Chrome headless
[ -f assets/demos/demo-landing-ko.png ] || google-chrome --headless --disable-gpu \
  --screenshot=assets/demos/demo-landing-ko.png --window-size=1280,1800 \
  "file://$(pwd)/assets/demos/demo-landing-ko.html" 2>/dev/null

ls -lh assets/demos/demo-landing-ko.png
```

Expected: PNG exists, file size > 50 KB.

- [ ] **Step 5: Commit**

```bash
git add assets/templates/landing-page-ko.html scripts/shared.py assets/demos/demo-landing-ko.html assets/demos/demo-landing-ko.png
git commit -m "feat: add KO landing-page screen template + demo-landing-ko"
```

---

### Task 20: Update cross-references and AI visibility files

**Files:**
- Modify: `README.md` (Fonts paragraphs around lines 95, 127, 177)
- Modify: `index-ko.html` (template gallery / availability copy)
- Modify: `llms.txt`
- Modify: `sitemap.xml`

- [ ] **Step 1: Update the README Fonts paragraphs**

Line ~95 currently reads:

```
The ZIP is lightweight: Chinese fonts load from local checkout first, then jsDelivr CDN.
```

Replace with:

```
The ZIP is lightweight: Chinese and Korean fonts load from local checkout first, then jsDelivr CDN.
```

Line ~127 currently reads:

```
**Fonts**: Each language uses a single serif font for the entire page. Chinese: TsangerJinKai02. Japanese: YuMincho. English: Charter. TsangerJinKai is free for personal use, commercial use requires a license from [tsanger.cn](https://tsanger.cn). All other fonts are system-bundled.
```

Replace with:

```
**Fonts**: Each language uses a single serif font for the entire page. Chinese: TsangerJinKai02. Japanese: YuMincho. English: Charter. Korean: Nanum Myeongjo (OFL, Naver Corp.). TsangerJinKai is free for personal use, commercial use requires a license from [tsanger.cn](https://tsanger.cn). Nanum Myeongjo and other open-licensed fonts are bundled in the ZIP.
```

Line ~177 currently reads:

```
**Fonts**: TsangerJinKai02 (Chinese) is free for personal use only; commercial use requires a license from [tsanger.cn](https://tsanger.cn). Charter (English), YuMincho (Japanese), and CJK fallbacks are system-bundled or open-licensed.
```

Replace with:

```
**Fonts**: TsangerJinKai02 (Chinese) is free for personal use only; commercial use requires a license from [tsanger.cn](https://tsanger.cn). Charter (English), YuMincho (Japanese), Nanum Myeongjo (Korean, OFL/Naver), and CJK fallbacks are system-bundled or open-licensed.
```

- [ ] **Step 2: Update `index-ko.html`**

Skim `index-ko.html` for any mention of "templates", "available languages", or "지원 언어". Add Korean to the supported-language list and link the KO demos where the CN/EN landing pages link to their respective demos. The specific edits depend on the current copy — do a careful read first:

```bash
grep -n "template\|Korean\|한국어\|언어\|demo" index-ko.html | head -30
```

Make the minimal edits required so a visitor landing on `index-ko.html` discovers that Korean is now a fully supported template language.

- [ ] **Step 3: Update `llms.txt`**

```bash
grep -n "languages\|template\|Korean\|Nanum" llms.txt | head
```

Add Korean to any explicit language enumeration. Add a line under the templates section noting that `*-ko.html` files exist for all 9 HTML targets plus `slides-ko.py` and `landing-page-ko.html`.

- [ ] **Step 4: Update `sitemap.xml`**

Confirm `index-ko.html` is listed in the sitemap. If not, add a `<url>` entry mirroring the existing `index-ja.html` entry, with the URL pointing to `https://kami.<domain>/index-ko.html` (or the appropriate domain). The exact domain is visible in adjacent entries.

- [ ] **Step 5: Run the project's check pipeline**

```bash
python3 scripts/build.py --check 2>&1 | tail -10
python3 scripts/tests/test_build.py 2>&1 | tail -10
```

Expected: both green.

- [ ] **Step 6: Commit cross-references**

```bash
git add README.md index-ko.html llms.txt sitemap.xml
git commit -m "site: announce Korean template support across README, llms.txt, sitemap, index-ko"
```

---

### Task 21: Re-package `dist/kami.zip` and verify packaging

**Files:**
- Modify: `dist/kami.zip` (regenerated)

- [ ] **Step 1: Run the package script**

```bash
bash scripts/package-skill.sh 2>&1 | tail -20
ls -lh dist/kami.zip
```

Expected: ZIP regenerated; file size has grown by approximately 8 MB versus the previous release (Nanum Regular + Bold).

- [ ] **Step 2: Verify all KO templates and demos are inside the ZIP**

```bash
python3 -c "
import zipfile
need = [
    'assets/templates/one-pager-ko.html',
    'assets/templates/letter-ko.html',
    'assets/templates/long-doc-ko.html',
    'assets/templates/portfolio-ko.html',
    'assets/templates/resume-ko.html',
    'assets/templates/equity-report-ko.html',
    'assets/templates/changelog-ko.html',
    'assets/templates/slides-weasy-ko.html',
    'assets/templates/slides-ko.py',
    'assets/templates/landing-page-ko.html',
    'assets/fonts/NanumMyeongjo-Regular.ttf',
    'assets/fonts/NanumMyeongjo-Bold.ttf',
    'assets/fonts/LICENSE-NanumMyeongjo.txt',
    'assets/demos/demo-kaku-ko.html',
    'assets/demos/demo-kaku-ko.pdf',
    'assets/demos/demo-kaku-ko.png',
    'assets/demos/demo-tesla-ko.html',
    'assets/demos/demo-tesla-ko.pdf',
    'assets/demos/demo-tesla-ko.png',
    'assets/demos/demo-longdoc-ko.html',
    'assets/demos/demo-longdoc-ko.pdf',
    'assets/demos/demo-longdoc-ko.png',
    'assets/demos/demo-portfolio-ko.html',
    'assets/demos/demo-portfolio-ko.pdf',
    'assets/demos/demo-portfolio-ko.png',
    'assets/demos/demo-musk-resume-ko.html',
    'assets/demos/demo-musk-resume-ko.pdf',
    'assets/demos/demo-musk-resume-ko.png',
    'assets/demos/demo-equity-ko.html',
    'assets/demos/demo-equity-ko.pdf',
    'assets/demos/demo-equity-ko.png',
    'assets/demos/demo-changelog-ko.html',
    'assets/demos/demo-changelog-ko.pdf',
    'assets/demos/demo-changelog-ko.png',
    'assets/demos/demo-agent-slides-ko.html',
    'assets/demos/demo-agent-slides-ko.pdf',
    'assets/demos/demo-agent-slides-ko.png',
    'assets/demos/demo-agent-slides-ko.pptx',
    'assets/demos/demo-landing-ko.html',
    'assets/demos/demo-landing-ko.png',
]
with zipfile.ZipFile('dist/kami.zip') as z:
    names = set(z.namelist())
missing = [n for n in need if n not in names]
assert not missing, f'missing in ZIP: {missing}'
print(f'OK: all {len(need)} required KO files present in dist/kami.zip')
"
```

Expected: `OK: all 39 required KO files present in dist/kami.zip`.

- [ ] **Step 3: Verify TsangerJinKai TTFs are still excluded**

```bash
python3 -c "
import zipfile
with zipfile.ZipFile('dist/kami.zip') as z:
    names = set(z.namelist())
forbidden = [n for n in names if 'TsangerJinKai02-W0' in n]
assert not forbidden, f'TsangerJinKai TTFs should not be in ZIP: {forbidden}'
print('OK: TsangerJinKai TTFs correctly excluded')
"
```

Expected: `OK: TsangerJinKai TTFs correctly excluded`.

- [ ] **Step 4: Record final ZIP size**

```bash
python3 -c "
import os
size = os.path.getsize('dist/kami.zip')
print(f'dist/kami.zip: {size:,} bytes ({size / 1024 / 1024:.1f} MB)')
"
```

Record this number; it'll go into the release notes.

- [ ] **Step 5: Run the full verification gauntlet**

```bash
python3 scripts/build.py --check 2>&1 | tail -5
python3 scripts/build.py --verify 2>&1 | tail -10
python3 scripts/tests/test_build.py 2>&1 | tail -10
python3 scripts/stabilize.py all --report 2>&1 | tail -15
python3 scripts/build.py --check-rhythm slides slides-en slides-weasy-ko 2>&1 | tail -5
```

All five must end on `OK:` lines. If any fails, the diagnostic is in the tail output — fix the regressing template, re-package, and rerun.

- [ ] **Step 6: Commit the regenerated ZIP**

```bash
git add dist/kami.zip
git commit -m "$(cat <<'EOF'
chore: refresh dist/kami.zip with Korean template full set

Adds 10 KO outputs (9 HTML templates + slides-ko.py) and Nanum Myeongjo
Regular/Bold TTFs to the release archive. TsangerJinKai TTFs remain
excluded per the existing commercial-font policy.
EOF
)"
```

---

## Self-Review

This plan was written from the spec at `docs/superpowers/specs/2026-05-28-kami-korean-template-fullset-design.md`. Spec coverage check:

- **§3 Architecture overview** → Tasks 1–21 cover the full file inventory listed.
- **§4 Component changes** → Tasks 7–19 (templates), Task 1 (fonts), Task 8/11–17/19 (registry), Task 2 (lint), Task 3 (allowlist), Task 6/9 (design.md), Task 5 (AGENTS.md), Task 4 (ensure-fonts.sh), Task 10–19 (demos).
- **§5 Font stack & bundling** → Task 1 (acquire), Task 7 (`@font-face` in template), Task 4 (ensure-fonts.sh), Task 21 (ZIP verification), Task 20 (README attribution).
- **§6 Lint pair extension** → Task 2.
- **§7 Demo coverage** → Tasks 10–19, Task 21 (final ZIP inventory).
- **§8 Verification** → Task 9 (pilot visual checks), Tasks 11–19 (per-template build/verify), Task 21 (full gauntlet).
- **§9 Rollout plan** → Phase 1 (Tasks 1–6), Phase 2 (Tasks 7–10), Phase 3 (Tasks 11–21).
- **§10 Risks** → Resume strict 2-page (Task 14 explicit fallback), CI font fallback (Task 4 + Task 21 verification), package exclusion regex (Task 21 Step 3), `font-synthesis` (Task 7 Step 5).

Gaps from spec to plan: none identified.

Type / name consistency: variant suffix table is `_VARIANT_SUFFIXES`; pair function name is `_pair_names`; new variable names `base_path` / `variant_path` / `base_vars` / `variant_vars` are used consistently in Task 2 Step 4. Template registry name keys (`one-pager-ko`, `letter-ko`, ...) match the source filenames in Tasks 11–19.

Placeholder check: the only "TBD" references are inside `references/design.md` content that the pilot deliberately fills in during Task 9 Step 4 — that's the intentional spec mechanism, not a plan placeholder.
