# Korean Production Notes

## Fonts

Run `scripts/fetch-ko-fonts.sh` before Korean PDF verification if the local machine does not already have the Korean fonts installed.

Default local font files:

- `assets/fonts/Pretendard-Regular.woff2`
- `assets/fonts/Pretendard-SemiBold.woff2`
- `assets/fonts/BMDOHYEON.woff2`

Optional display fonts:

- `BMJUA.woff2`
- `BMHANNAPro.woff2`
- `BMHANNAAir.woff2`

## PDF Checks

Use:

```bash
XDG_CACHE_HOME=/tmp DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib python3 scripts/build.py --verify one-pager-ko
XDG_CACHE_HOME=/tmp DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib python3 scripts/build.py --verify resume-ko
python3 scripts/build.py --verify slides-ko
```

On macOS, WeasyPrint may need Homebrew dynamic libraries exposed through `DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib`. `XDG_CACHE_HOME=/tmp` avoids fontconfig cache warnings in restricted agent sandboxes.

Then manually inspect:

- Hangul glyphs are not boxed or substituted with a CJK fallback.
- Body text has no wide tracking.
- Korean line breaks do not isolate one-syllable particles too often.
- Metrics and financial columns align with tabular numerals.
- BM DoHyeon appears only in display roles.

## WeasyPrint Notes

WeasyPrint rendering varies by installed font stack. Any font swap can change Korean page count. If a document overflows, first cut copy, then reduce vertical gaps, then reduce dense body size by at most `0.2pt`. Do not solve Korean overflow by squeezing letter-spacing.
