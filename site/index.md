# Kami

Kami gives AI agents templates and layout rules for documents and landing pages. It includes one-pagers, resumes, portfolios, slide decks, long reports, letters, equity reports, and changelogs. Documents export to PDF or PNG; slides also support editable PPTX.


The default style uses a warm parchment canvas (`#f5f4ed`), a single ink-blue accent (`#1B365D`), serif fonts and clear heading levels (Charter for Latin, TsangerJinKai for Chinese), and consistent spacing. An opt-in white-paper variant renders the same document on a white background for home and office printers while keeping warm backgrounds in cards and tables.

Kami runs entirely on the machine that installs it. There is no hosted Kami API, no account, and no key to obtain. Everything below is a local command or a static file on this site.

## When to use Kami

Reach for Kami when the user asks for a document whose *appearance* matters and a plain markdown answer would not be enough:

- "Make me a resume / CV" - use the `resume` template and `references/schemas/resume.json`.
- "Turn this into a one-pager / product brief / intro sheet" - `one-pager`.
- "Write a formal letter, offer, or notice" - `letter`.
- "Build a slide deck for this talk" - `slides`, exported to PDF or editable PPTX.
- "Write up this research / spec / report as a document" - `long-doc`.
- "Show my work / case studies / portfolio" - `portfolio`.
- "Analyze this stock or company and produce a report" - `equity-report`.
- "Write release notes for this version" - `changelog`.
- "Draw an architecture diagram, flowchart, timeline, or chart to embed" - one of the 18 inline SVG diagram types.
- "Build a landing page in this style" - the browser-only `landing-page` template.

Do not reach for Kami for chat answers, code files, or content where the user only wants the text. Kami's cost is layout work; it pays off when the artifact is delivered to someone else.

How an agent should call Kami: install the skill (below), fill the template HTML, then verify with `python3 scripts/build.py --check-content` and `--check-visual`, or drive the same steps as tools through the local MCP server. The judgment lives in `SKILL.md`; the execution lives in the scripts.

## Install

- Claude Code, Codex, Cursor, and other agents: `npx skills add tw93/kami -a claude-code codex cursor -g -y`
- Claude Code plugin (v2.1.142+): `/plugin marketplace add tw93/kami` then `/plugin install kami@kami`
- Codex plugin: `codex plugin marketplace add tw93/kami` then `codex plugin add kami@kami`
- Claude Desktop: download the release asset `kami.zip` from <https://github.com/tw93/kami/releases/latest/download/kami.zip> (not GitHub's Source code ZIP) and upload it under Customize > Skills.
- MCP client: `claude mcp add kami -- python3 <checkout>/skills/kami/scripts/mcp_server.py`

## What ships

Nine document templates: one-pager, letter, long document, portfolio, resume, slides, equity report, changelog, social cards. Each exists in Chinese, English, and Korean variants where the typography differs.

Eighteen inline SVG diagram types: architecture, architecture board, flowchart, quadrant, bar chart, line chart, donut chart, state machine, timeline, swimlane, tree, layer stack, venn, candlestick, waterfall, sequence, class, ER.

Ten content schemas under `references/schemas/`: changelog, equity-report, landing-page, letter, long-doc, one-pager, portfolio, resume, slides, social-cards. Each one states the structure and the quality bar for its document type.

## Agent interfaces

- **Content contracts**: `references/schemas/<type>.json` carries the per-type structure, while `content.json.brief` records the artifact target, preserve boundary, evidence, and acceptance checks. Validate before layout and check coverage after filling: `python3 scripts/build.py --check-content content.json filled.html`.
- **Deterministic checks**: placeholders, markdown residue, page density, orphan lines, and slide rhythm, plus a perceptual pass that exports page images with a fixed review checklist (`--check-visual`).
- **MCP server**: `python3 scripts/mcp_server.py` speaks MCP over stdio with `kami_templates`, `kami_doctor`, `kami_render`, `kami_check`, `kami_deliver`, and `kami_screenshot`, so an agent can diagnose, render, and verify without loading the skill prompt.
- **Machine-readable site surfaces**: [/llms.txt](https://kami.tw93.fun/llms.txt), [/developers.md](https://kami.tw93.fun/developers.md), [/.well-known/mcp/server-card.json](https://kami.tw93.fun/.well-known/mcp/server-card.json), [/.well-known/agent-skills/index.json](https://kami.tw93.fun/.well-known/agent-skills/index.json), and the catalog feeds in [/schemamap.xml](https://kami.tw93.fun/schemamap.xml).

## Pages

- [Homepage](https://kami.tw93.fun/) - design system overview with live demos
- [Developers](https://kami.tw93.fun/developers) - agent and developer integration surface
- [About](https://kami.tw93.fun/about) - what Kami is, who maintains it
- [Contact](https://kami.tw93.fun/contact) - support and reporting channels
- [Privacy](https://kami.tw93.fun/privacy) - what this site and the skill collect
- [Source](https://github.com/tw93/kami) - templates, scripts, and skill definition

Localized versions of the homepage: [简体中文](https://kami.tw93.fun/index-zh.html), [繁體中文](https://kami.tw93.fun/index-tw.html), [日本語](https://kami.tw93.fun/index-ja.html), [한국어](https://kami.tw93.fun/index-ko.html).

## License

MIT, maintained by [Tw93](https://tw93.fun).
