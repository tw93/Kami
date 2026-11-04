---
type: regex
target: {source: file, path: "cards.html"}
match: not_contains
pattern: '>[^<]*\{\{[^}\n]{1,60}\}\}'
---
