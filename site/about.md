# About Kami

Kami gives AI agents templates and layout rules for documents and landing pages.

HTML version: <https://kami.tw93.fun/about>

## Templates and layout rules

Kami uses a warm parchment background (`#f5f4ed`), ink-blue accents (`#1B365D`), serif fonts, and consistent spacing. These defaults help keep headings, text, tables, and diagrams readable across document types.

Documents render through HTML to PDF or PNG, while slide decks also have an editable PPTX path. Nine document templates cover the common cases: one-pager, letter, long document, portfolio, resume, slides, equity report, changelog, and social cards. Eighteen inline SVG diagram types cover the pictures those documents need, from architecture and flowchart to candlestick and Venn. A separate landing-page template applies the same restraint to a product page.

Kami also checks content and layout. Kami ships ten JSON content schemas and a set of checks that look for the failures agents actually produce: unfilled placeholders, markdown syntax leaking into the render, a line orphaned at a page break, a page that ends a third empty, a deck where six slides in a row share one layout.

## Customization and scope

Kami is not a hosted service. There is no Kami account, no API key, no server that receives your documents. The skill installs into your agent and runs on your machine; this domain serves a static site and a set of public metadata files, nothing more.

Kami provides a default style you can adapt to your brand. Share your colors, fonts, and layout preferences, or save them in a brand profile. The current request takes priority over those defaults.

Kami includes writing guidance, but claims and conclusions must come from your source material. Missing evidence stays marked for review.

## One maintainer, MIT licensed

Kami is built and maintained by [Tw93](https://tw93.fun), an independent developer. The source, including every template, script, and the skill definition itself, lives at <https://github.com/tw93/kami> under the MIT license. Use it commercially, fork it, or lift a single template out of it; keep the license notice when redistributing the code or templates. Font licenses apply separately.

Releases are tagged in the repository and published as a `kami.zip` asset for Claude Desktop, alongside the Claude Code and Codex plugin marketplaces. The homepage carries the current version. Interface, template registry, and public facts are cross-checked in CI, to catch version mismatches between the site, plugin manifests, and skill package.

The homepage is available in English, Simplified Chinese, Traditional Chinese, Japanese, and Korean. Fonts and spacing are adjusted for each language.

## Elsewhere

[Home](https://kami.tw93.fun/) · [Developers](https://kami.tw93.fun/developers) · [Contact](https://kami.tw93.fun/contact) · [Privacy](https://kami.tw93.fun/privacy) · [Source](https://github.com/tw93/kami)
