# Korean Design System

Kami Korean is not a translation of the Chinese or English templates. Hangul has square syllable blocks, uneven internal stroke density, heavy final consonants, and frequent Latin/number mixing. The system keeps the parchment and ink-blue identity, but changes type strategy for Korean reading.

## Principles

1. Use modern Korean sans for dense information. Pretendard is the default body face because it balances Hangul, Latin, and numerals without letter-spacing tricks.
2. Use display faces sparingly. BM DoHyeon can make a cover or headline memorable, but it is too loud for body text.
3. Keep body letter-spacing at `0`. Hangul opened with tracking quickly looks like public-office slideware.
4. Give Hangul slightly more line-height than English print. Dense documents use `1.44-1.50`; reading documents use `1.56-1.62`.
5. Treat numerals as a first-class typography problem. Metrics, dates, and financial tables need tabular numbers and right alignment.
6. Preserve Kami restraint: parchment background, one ink-blue accent, warm neutrals, no hard shadows, no italic.

## Font Strategy

```css
--sans: "Pretendard", "Sunghyun Sans KR", "Sunghyun Sans",
        "Apple SD Gothic Neo", "Noto Sans KR", "Malgun Gothic", sans-serif;

--serif: "Noto Serif KR", "Nanum Myeongjo",
         "AppleMyungjo", "Batang", Georgia, serif;

--display: "BM DoHyeon", "Pretendard",
           "Apple SD Gothic Neo", "Noto Sans KR", sans-serif;

--mono: "JetBrains Mono", "SF Mono", Consolas,
        "Pretendard", "Noto Sans KR", monospace;
```

### Roles

| Role | Font | Notes |
|---|---|---|
| Body | Pretendard | Default for one-pager, resume, report summaries, tables, slides |
| Editorial body | Noto Serif KR | Long documents and formal letters only |
| Display title | BM DoHyeon | Cover/headline only; never paragraphs |
| Warm formal accent | Noto Serif KR | Section titles, quotes, letter body |
| Numbers/code | JetBrains Mono or Pretendard tabular | Use `font-variant-numeric: tabular-nums` |

BM Jua and BM Hanna Air can be used for playful branded pieces, but they are not default. They change the tone too strongly for professional documents.

## Type Scale

| Role | Size | Weight | Line-height | Letter spacing |
|---|---:|---:|---:|---:|
| Display | 24-30pt | 400 display / 600 sans | 1.12-1.18 | -0.015em to 0 |
| H1 | 20-24pt | 600 | 1.18-1.24 | -0.01em to 0 |
| H2 | 13-16pt | 600 | 1.25-1.32 | 0 |
| Body lead | 11.5-12.5pt | 400 | 1.56-1.62 | 0 |
| Body | 9.5-10pt | 400 | 1.50-1.58 | 0 |
| Dense body | 8.8-9.4pt | 400 | 1.42-1.48 | 0 |
| Label | 8.5-9pt | 600 | 1.32-1.40 | 0.02-0.04em |

## Document Defaults

| Document | Default body | Accent |
|---|---|---|
| One-pager | Pretendard | BM DoHyeon for H1 only |
| Resume | Pretendard | BM DoHyeon for name and metric values |
| Slides | Pretendard | BM DoHyeon for cover/chapter |
| Long doc | Noto Serif KR or Pretendard by topic | Serif if essay-like, sans if data-heavy |
| Letter | Noto Serif KR | Minimal, no decorative display face |
| Equity report | Pretendard | Tables and numerals over ornament |

## Korean Layout Rules

- Set `word-break: keep-all` and `overflow-wrap: break-word`.
- Do not justify Korean body text in narrow columns.
- Avoid four-column Korean prose; use it only for metric cards.
- Keep bullet lines short. Korean bullets longer than two lines read like paragraphs.
- Avoid all-caps English labels inside Korean documents unless they are product terms.
- Use `YYYY.MM.DD` for dates unless the source requires another form.

## Font Licensing Notes

Pretendard is licensed under SIL Open Font License 1.1. Sunghyun Sans is also OFL 1.1. Baemin fonts are distributed for free use, modification, and redistribution, but the font files must not be sold by themselves. Keep font license files or attribution notes when bundling.
