# Kami for developers and agents

Use the local MCP server, ten content schemas, and CLI checks to render and review documents.

HTML version: <https://kami.tw93.fun/developers>

## There is no hosted Kami API

Kami installs into an AI agent and runs in that environment. There is no hosted Kami API, account, or API key. Update checks and remote resources may use the network; see the privacy page for details.

The integration surface is local: an MCP server for tool calls, JSON content schemas for structure, and CLI checks for verification. The static files listed at the end of this page are the machine-readable index of all of it, with generated discovery files and catalog feeds checked against the source.

## Install

```
# Claude Code, Codex, Cursor, and other agents
npx skills add tw93/kami -a claude-code codex cursor -g -y

# Claude Code plugin (v2.1.142+)
/plugin marketplace add tw93/kami
/plugin install kami@kami

# Codex plugin
codex plugin marketplace add tw93/kami
codex plugin add kami@kami

# MCP client, from a checkout
claude mcp add kami -- python3 <checkout>/skills/kami/scripts/mcp_server.py
```

Claude Desktop: download the release asset `kami.zip` from <https://github.com/tw93/kami/releases/latest/download/kami.zip>, not GitHub's Source code ZIP, then upload it under Customize > Skills.

## MCP tools

The server speaks newline-delimited JSON-RPC 2.0 over stdio and has no third-party dependency for the protocol itself. Tools that need WeasyPrint, pypdf, or PyMuPDF surface the install hint as a tool error instead of crashing.

| Tool | What it does |
| --- | --- |
| `kami_templates` | List document templates, browser-only templates, the diagram library, and content schema types, with the reference docs to read before filling. |
| `kami_doctor` | Report installed PDF render, visual-check, editable-PPTX, and font capabilities without treating an unavailable engine as a clean result. |
| `kami_render` | Render trusted local Kami HTML to PDF through WeasyPrint, with build-time code highlighting. Returns the PDF path and page count. |
| `kami_check` | Run the deterministic checks for a file. Returns the readable report plus stable rule IDs, findings, engine coverage, and explicit degraded checks. |
| `kami_deliver` | Finish a filled document in one call, the same gate as `build.py --deliver`: every check in order, the PDF render, page contract, and page images. Returns ready, the verdict, each check with its findings, and the data gaps to report. |
| `kami_screenshot` | Rasterize every PDF page to PNG and return the paths, deterministic CJK font verdict, and a `review_pending` checklist contract for the perceptual pass. |

The server card, including protocol version and tool list, is published at </.well-known/mcp/server-card.json>.

## Content schemas

Ten schemas live under `references/schemas/`: changelog, equity-report, landing-page, letter, long-doc, one-pager, portfolio, resume, slides, social-cards. Each states the structure and the quality bar for its type. A new `content.json` also carries a `brief` with audience, job, output contract, target, preserve boundary, evidence, and acceptance checks; older IR files remain valid. Fill the schema first, lay out second.

```
python3 scripts/build.py --check-content content.json
python3 scripts/build.py --check-content content.json filled.html
```

The second form reports coverage: fields that exist in the content object but never reached the document. Missing content can be easy to overlook in a quick review.

## Checks

- `--deliver filled.html [content.json]` - every check below that applies to a finished document, in order, plus the PDF render and page images, ending in one READY or NOT READY verdict. This is the command an agent runs to finish.
- `--check-placeholders` - unfilled template text still in the document.
- `--check-markdown` - markdown syntax that leaked into the rendered output.
- `--check-orphans` - single lines stranded at a page break.
- `--check-density` - pages ending with more than a quarter of the page empty.
- `--check-rhythm` - slide sequences that repeat one layout too many times.
- `--check-resume-balance` - column and section balance in a resume.
- `--check-visual` - exports page images and returns a fixed review checklist for a perceptual pass.

`python3 scripts/build.py --help` is the authoritative list. Repository-wide checks, `python3 scripts/build.py --check`, cover template lint, design-token sync, and public-site fact drift.

## Machine-readable files

- [/llms.txt](https://kami.tw93.fun/llms.txt) - product summary, install commands, and when an agent should reach for Kami.
- [/index.md](https://kami.tw93.fun/index.md) - the homepage as Markdown. A request to `/` carrying `Accept: text/markdown`, or `/?mode=agent`, redirects here.
- [/developers.md](https://kami.tw93.fun/developers.md) - this page as Markdown.
- [/developers/llms.txt](https://kami.tw93.fun/developers/llms.txt) - the developer surface on its own.
- [/.well-known/agent-skills/index.json](https://kami.tw93.fun/.well-known/agent-skills/index.json) - Agent Skills discovery index, with a SHA-256 digest of the skill file it points to.
- [/.well-known/mcp/server-card.json](https://kami.tw93.fun/.well-known/mcp/server-card.json) - MCP server card.
- [/feeds/catalog.jsonld](https://kami.tw93.fun/feeds/catalog.jsonld) - JSON-LD catalog of all 9 document templates and 18 diagram types, indexed by [/schemamap.xml](https://kami.tw93.fun/schemamap.xml).
- [/SKILL.md](https://kami.tw93.fun/SKILL.md) - the skill definition itself, served as `text/markdown`.
- [/sitemap.xml](https://kami.tw93.fun/sitemap.xml) and [/robots.txt](https://kami.tw93.fun/robots.txt) - crawl surface and AI crawler policy.

## Elsewhere

[Home](https://kami.tw93.fun/) · [About](https://kami.tw93.fun/about) · [Contact](https://kami.tw93.fun/contact) · [Privacy](https://kami.tw93.fun/privacy) · [Source](https://github.com/tw93/kami)
