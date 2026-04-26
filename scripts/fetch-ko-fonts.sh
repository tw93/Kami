#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FONTS="$ROOT/assets/fonts"
mkdir -p "$FONTS"

download() {
  local url="$1"
  local out="$2"
  if [[ -f "$FONTS/$out" ]]; then
    echo "OK: $out already exists"
    return
  fi
  echo "GET: $out"
  curl -fsSL "$url" -o "$FONTS/$out"
}

# Pretendard: SIL Open Font License 1.1
download "https://cdn.jsdelivr.net/gh/fonts-archive/Pretendard/Pretendard-Regular.woff2" "Pretendard-Regular.woff2"
download "https://cdn.jsdelivr.net/gh/fonts-archive/Pretendard/Pretendard-SemiBold.woff2" "Pretendard-SemiBold.woff2"

# Baemin display faces: free redistribution/use; do not sell font files by themselves.
download "https://unpkg.com/@kfonts/bm-dohyeon-otf@0.2.1/BMDOHYEON_otf.woff2" "BMDOHYEON.woff2"
download "https://unpkg.com/@kfonts/bm-jua-otf@0.2.0/BMJUA_otf.woff2" "BMJUA.woff2"

echo "OK: Korean font fetch complete"
