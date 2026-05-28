#!/usr/bin/env bash
set -euo pipefail

# Portable across bash 3.2+ (macOS stock /bin/bash) and bash 4+ (Linux, Homebrew).
# Avoids `declare -A` so the script runs on a fresh macOS without `brew install bash`.

FONT_DIR="$(cd "$(dirname "$0")/../assets/fonts" && pwd)"
MIN_SIZE_CN=10000000  # 10MB for TsangerJinKai (large CJK glyph set)
MIN_SIZE_KO=6500000   # 6.5MB for Source Han Serif K (Adobe full subset)

# --- TsangerJinKai (existing) -----------------------------------------------
CN_NAMES=("仓耳今楷02-W04.ttf" "仓耳今楷02-W05.ttf")
LOCAL_NAMES=("TsangerJinKai02-W04.ttf" "TsangerJinKai02-W05.ttf")

# --- Source Han Serif K (KO) -----------------------------------------------
KO_NAMES=("SourceHanSerifKR-Regular.otf" "SourceHanSerifKR-Medium.otf")

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

download_ko_serif() {
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

cn_failed=0
if $cn_all_present; then
  echo "OK: TsangerJinKai fonts present"
else
  echo "Downloading TsangerJinKai fonts..."
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
    # Don't exit yet — try the KO recovery too so a Korean-only user still gets KO fonts.
  fi
fi

# --- Source Han Serif K (KO) check ------------------------------------------
ko_all_present=true
for local_name in "${KO_NAMES[@]}"; do
  if ! check_size "$FONT_DIR/$local_name" "$MIN_SIZE_KO"; then
    ko_all_present=false
    break
  fi
done

ko_failed=0
if $ko_all_present; then
  echo "OK: Source Han Serif K fonts present"
else
  echo "Downloading Source Han Serif K fonts..."
  for local_name in "${KO_NAMES[@]}"; do
    if check_size "$FONT_DIR/$local_name" "$MIN_SIZE_KO"; then
      echo "  OK: $local_name already present"
      continue
    fi
    if ! download_ko_serif "$local_name"; then
      ko_failed=$((ko_failed + 1))
    fi
  done
  if [[ "$ko_failed" -gt 0 ]]; then
    echo ""
    echo "Some Source Han Serif K files could not be downloaded. Alternatives:"
    echo "  1. Download from https://github.com/adobe-fonts/source-han-serif/releases"
    echo "  2. Copy SourceHanSerifKR-Regular.otf and -Medium.otf manually into $FONT_DIR"
  fi
fi

# Final exit: fail only if either side failed AND its fonts are still missing.
if [[ "$cn_failed" -gt 0 || "$ko_failed" -gt 0 ]]; then
  exit 1
fi

echo "OK: all fonts ready"
