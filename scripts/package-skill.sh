#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="${1:-"$ROOT/dist/kami.zip"}"
PACKAGE_MAX_BYTES="${KAMI_PACKAGE_MAX_BYTES:-6000000}"
PACKAGE_FORBIDDEN_RE='^(assets/showcase/|assets/images/[123]\.png$|assets/fonts/TsangerJinKai02-W0[45]\.ttf$|assets/fonts/SourceHanSerifKR-(Regular|Medium)\.otf$)'
PACKAGE_REQUIRED_ENTRY='assets/images/logo.svg'

mkdir -p "$(dirname "$OUT")"
rm -f "$OUT"

cd "$ROOT"

MANIFEST="$(mktemp)"
FILTERED_MANIFEST="$(mktemp)"
trap 'rm -f "$MANIFEST" "$FILTERED_MANIFEST"' EXIT

git ls-files > "$MANIFEST"
awk '
  /^assets\/fonts\/TsangerJinKai02-W0[45]\.ttf$/ { next }
  /^assets\/fonts\/SourceHanSerifKR-(Regular|Medium)\.otf$/ { next }
  /^assets\/examples\// { next }
  /^assets\/illustrations\// { next }
  /^assets\/showcase\// { next }
  /^dist\// { next }
  /^\.vercel\// { next }
  /(^|\/)__pycache__\// { next }
  /\.pyc$/ { next }
  /(^|\/)\.DS_Store$/ { next }
  { print }
' "$MANIFEST" > "$FILTERED_MANIFEST"

zip -X -q "$OUT" -@ < "$FILTERED_MANIFEST"

entries="$(zipinfo -1 "$OUT")"
if forbidden_entries="$(printf '%s\n' "$entries" | grep -E "$PACKAGE_FORBIDDEN_RE")"; then
  echo "ERROR: disallowed package entry found in $OUT:" >&2
  printf '%s\n' "$forbidden_entries" >&2
  exit 1
fi

if ! printf '%s\n' "$entries" | grep -Fxq "$PACKAGE_REQUIRED_ENTRY"; then
  echo "ERROR: required package entry missing from $OUT: $PACKAGE_REQUIRED_ENTRY" >&2
  exit 1
fi

size_bytes="$(wc -c < "$OUT" | tr -d '[:space:]')"
if (( size_bytes > PACKAGE_MAX_BYTES )); then
  echo "ERROR: package exceeds ${PACKAGE_MAX_BYTES} bytes: ${size_bytes} bytes" >&2
  exit 1
fi

echo "OK: package audit passed (${size_bytes} bytes, limit ${PACKAGE_MAX_BYTES})"
echo "OK: wrote $OUT"
