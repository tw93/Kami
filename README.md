<div align="center">
  <img src="https://gw.alipayobjects.com/zos/k/vl/logo.svg" width="120" />
  <h1>Kami</h1>
  <p><b>Good content deserves good paper.</b></p>
  <a href="https://github.com/tw93/kami/stargazers"><img src="https://img.shields.io/github/stars/tw93/kami?style=flat-square" alt="Stars"></a>
  <a href="https://github.com/tw93/kami/releases"><img src="https://img.shields.io/github/v/tag/tw93/kami?label=version&style=flat-square" alt="Version"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg?style=flat-square" alt="License"></a>
  <a href="https://twitter.com/HiTw93"><img src="https://img.shields.io/badge/follow-Tw93-red?style=flat-square&logo=Twitter" alt="Twitter"></a>
</div>

## Why

Kami (紙, かみ) means paper in Japanese: the surface where a finished idea lands. AI can produce documents better than most humans do manually. The missing piece is not capability but constraint: without a design system, every session drifts into generic gray and inconsistent layouts.

Kami fills that gap: one constraint language, nine templates, simple enough for agents to run reliably, strict enough that every output is something you actually want to ship.

Part of a trilogy: [Kaku](https://github.com/tw93/Kaku) (書く) writes code, [Waza](https://github.com/tw93/Waza) (技) drills habits, [Kami](https://github.com/tw93/Kami) (紙) delivers documents.

## Showcase

Real PDFs from one constraint set, across templates and languages. Click any preview to open it.

<table>
<tr>
  <td align="center" width="25%">
    <a href="assets/demos/demo-musk-resume.pdf"><img src="assets/demos/demo-musk-resume.png" alt="Founder resume"></a>
    <br><b>Resume</b> · English
    <br><sub>Founder resume, 2 pages</sub>
  </td>
  <td align="center" width="25%">
    <a href="assets/demos/demo-kami-print.pdf"><img src="assets/demos/demo-kami-print.png" alt="Kami print one-pager"></a>
    <br><b>One-Pager</b> · 中文
    <br><sub>Kami 介绍 · 白底打印版</sub>
  </td>
  <td align="center" width="25%">
    <a href="assets/demos/demo-tesla.pdf"><img src="assets/demos/demo-tesla.png" alt="Tesla equity report"></a>
    <br><b>Equity Report</b> · 中文
    <br><sub>Tesla Q1 2026 财报点评</sub>
  </td>
  <td align="center" width="25%">
    <a href="assets/demos/demo-agent-slides.pdf"><img src="assets/demos/demo-agent-slides.png" alt="Agent keynote slides" /></a>
    <br><b>Slides</b> · English
    <br><sub>Agent keynote, 8 slides</sub>
  </td>
</tr>
<tr>
  <td align="center" width="25%">
    <a href="assets/demos/demo-mole.pdf"><img src="assets/demos/demo-mole.png" alt="Mole product brief"></a>
    <br><b>One-Pager</b> · English
    <br><sub>Mole product brief, 1 page</sub>
  </td>
  <td align="center" width="25%">
    <a href="assets/demos/demo-letter.pdf"><img src="assets/demos/demo-letter.png" alt="Recommendation letter"></a>
    <br><b>Letter</b> · 中文
    <br><sub>推荐信, 1 页</sub>
  </td>
  <td align="center" width="25%">
    <a href="assets/demos/demo-changelog.pdf"><img src="assets/demos/demo-changelog.png" alt="Mole release notes"></a>
    <br><b>Changelog</b> · English
    <br><sub>Mole v1.7.1 release notes</sub>
  </td>
  <td align="center" width="25%">
    <a href="assets/demos/demo-kaku.pdf"><img src="assets/demos/demo-kaku.png" alt="Kaku portfolio"></a>
    <br><b>Portfolio</b> · 日本語
    <br><sub>Kaku ターミナル作品集 · 7 ページ</sub>
  </td>
</tr>
</table>

## Install

**Claude Code**, v2.1.142 or newer

```bash
/plugin marketplace add tw93/kami
/plugin install kami@kami
```

**Codex plugin marketplace**

```bash
codex plugin marketplace add tw93/kami
codex plugin add kami@kami
```

This installs Kami as a Codex plugin from the repo marketplace, so future updates can use `codex plugin marketplace upgrade kami` followed by `codex plugin add kami@kami`.

**Generic agents** for OpenCode, Pi, and other tools that read from `~/.agents/`

```bash
npx skills add tw93/kami/plugins/kami/skills/kami -a '*' -g -y
```

The subpath points at the self-contained skill package. A bare `tw93/kami` would install only `SKILL.md`, because the repo root doubles as the website source and the `skills` CLI treats a root-level skill as a single file.

**Claude Desktop**

Download [kami.zip](https://github.com/tw93/kami/releases/latest/download/kami.zip), open Customize > Skills > "+" > Create skill, and upload the ZIP directly, no need to unzip.

The ZIP is lightweight: large CJK fonts are excluded from the skill package. In a repo checkout they load from local font files first, then jsDelivr CDN; in an installed skill, `scripts/ensure-fonts.sh` recovers missing Chinese or Korean fonts into the user font directory.

**Update**

- Claude Code: `claude plugin update kami`
- Codex: `codex plugin marketplace upgrade kami`, then `codex plugin add kami@kami` to refresh the installed snapshot
- Claude Desktop: download the latest [kami.zip](https://github.com/tw93/kami/releases/latest/download/kami.zip), click "..." on the skill card, choose Replace, upload
- Generic agents: re-run the `npx skills add tw93/kami/plugins/kami/skills/kami -a '*' -g -y` command, which overwrites the existing copy. Avoid `npx skills update` for now: it collapses a repo-root skill down to a single `SKILL.md` (vercel-labs/skills#1517).

Kami also runs a quiet version check at most once a day and tells you in chat when a newer version is out; it only reads a public version file, sends no data, and is skipped when offline.

## Use

The skill auto-triggers from natural requests, no slash command needed. Optimized for English and Chinese; Japanese and Korean are supported via best-effort CJK paths with visual QA before delivery.

Example prompts by language:

- English: `make a one-pager for my startup` / `turn this research into a long doc` / `write a formal letter` / `make a portfolio of my projects` / `build me a resume` / `design a slide deck for my talk` / `make this talk as a Marp deck` / `build a landing page for my app`
- 中文: `帮我做一份一页纸` / `帮我排版一份长文档` / `帮我写一封正式信件` / `帮我做一份作品集` / `帮我做一份简历` / `帮我做一套演讲幻灯片` / `帮我做一份 Markdown 风格的演示稿` / `帮我做一个产品落地页`
- 日本語: `スタートアップ向けの一枚資料を作って` / `この調査を長文レポートに整えて` / `正式な依頼文を作って` / `プロジェクト作品集を作って` / `履歴書を作って` / `登壇用スライドを作って` / `Marp で登壇スライドを作って` / `アプリのランディングページを作って`
- 한국어: `스타트업 원페이저를 만들어줘` / `이 리서치를 장문 문서로 정리해줘` / `정식 레터를 작성해줘` / `프로젝트 포트폴리오를 만들어줘` / `이력서를 만들어줘` / `발표용 슬라이드를 만들어줘` / `Marp 슬라이드로 만들어줘` / `앱 랜딩 페이지를 만들어줘`

**Brand profile** (optional)

Create `~/.config/kami/brand.md` to persist identity, brand, defaults, and writing habits. See [brand.example.md](references/brand.example.md) for a full template.

The file has YAML frontmatter for structured fields like name, role, email, brand color, language, page size, and tone, plus a Markdown body for freeform notes. Kami treats it as the lowest-resolution context: applied only when the current request is ambiguous, and always overridable by what the specific document needs. The goal is to feel familiar across your work without making every output look the same.

## Design

Warm parchment canvas `#f5f4ed`, ink blue `#1B365D` as the sole accent, serif carries hierarchy, no hard shadows or flashy palettes. Not a UI framework; a constraint system for printed matter. Documents should read as composed pages, not dashboards.

- **Templates.** Eight document templates: One-Pager, Long Doc, Letter, Portfolio, Resume, Slides, Equity Report, and Changelog, plus a Landing Page system, in EN, CN, and KO.
- **Diagrams.** Seventeen inline SVG types. Sequence, class, and ER can be authored from Mermaid text: [beautiful-mermaid](https://github.com/lukilabs/beautiful-mermaid) renders the SVG and `scripts/mermaid_normalize.py` re-themes it to the Kami palette and makes it WeasyPrint-safe, no Node bundled.
- **Slides.** Three rendering paths: WeasyPrint HTML to PDF by default, python-pptx for editable PPTX on request, and a Marp variant in `assets/templates/marp/` for Markdown-first decks.
- **Code.** Pygments-based syntax highlighting when `Pygments` is installed; without it, PDFs still render and code stays monochrome.
- **Print.** Parchment is the default canvas; an opt-in white-paper variant flips any document to a white background for home or office printers, sinking the warmth into cards and tables so the hierarchy still reads. The [one-page Kami intro](assets/demos/demo-kami-print.pdf) (Chinese) is rendered with this variant; recipe in [production.md](references/production.md).

Kami picks the right variant based on the language you write in.

**Fonts**: Each language uses a single serif font for the entire page. Chinese: TsangerJinKai02. Japanese: YuMincho. Korean: Source Han Serif K. English: Charter. See [License](#license) for font terms.

Full spec: [design.md](references/design.md). Cheatsheet: [CHEATSHEET.md](CHEATSHEET.md).

## Beyond Documents

One constraint set, applied past the page: it lays out deployable websites and briefs AI image renderers, so both come back in the Kami look.

<table>
<tr>
  <td align="center" width="25%" valign="top">
    <a href="https://kami.tw93.fun"><img src="assets/showcase/kami-landing.png" alt="Kami landing page" height="150"></a>
    <br><b>Kami</b> · landing page
    <br><sub>Design system homepage</sub>
  </td>
  <td align="center" width="25%" valign="top">
    <a href="https://mole.fit"><img src="assets/showcase/mole-landing.png" alt="Mole landing page" height="150"></a>
    <br><b>Mole</b> · landing page
    <br><sub>macOS system utility</sub>
  </td>
  <td align="center" width="25%" valign="top">
    <img src="assets/illustrations/travel-spatialvla.png" alt="SpatialVLA architecture redraw" height="150">
    <br><b>Architecture redraw</b> · English
    <br><sub>SpatialVLA Figure 1, schematic</sub>
  </td>
  <td align="center" width="25%" valign="top">
    <img src="assets/illustrations/travel-tesla-optimus.png" alt="Tesla Optimus patent overview" height="150">
    <br><b>Evidence layout</b> · 中文
    <br><sub>Tesla Optimus 专利图一览</sub>
  </td>
</tr>
</table>

Landing pages ship as deployable multilingual sites. Illustrations are drawn by the host's own image model: where the host can generate images, like ChatGPT, it renders directly; where it cannot, like Claude or Codex, it outputs the brief for you to paste into any image model.

```text
Redraw this as a clean editorial diagram. Background: warm parchment (#f5f4ed), never pure white. One accent only, ink blue (#1B365D); everything else in warm gray with a yellow-brown undertone, no other colors. Thin single-line geometric strokes and simple flat icons. No gradients, no drop shadows, no 3D. Labels in a serif typeface. Generous whitespace, calm and composed, like a figure in a well-typeset report.
```

<sub>Rendered by ChatGPT Images in a single pass with no manual touch-up. Kami specifies, the renderer draws.</sub>

## Background

I like investing in US equities and ask Claude to write research reports all the time. Every output landed in the same default-doc look: gray, flat, a different layout each session. The structure was hard to scan, the formatting felt dated, and nothing about the page made me want to keep reading. So I started fixing the typography, the palette, the spacing, one rule at a time, until the report became a page I actually enjoyed.

Later I needed to present "The Agent You Don't Know: Principles, Architecture and Engineering Practice." I already had the document and didn't want to build slides from scratch, so I used Claude Design to lay it out in my own style, tweaked it round after round, and eventually got it to a place I was happy with. That process added inline SVG charts, a unified warm palette, and a tighter editorial rhythm. It kept growing until it covered every document I regularly ship, so I kept abstracting the process, and it became kami: one quiet design system I can hand to any agent and trust the output.

## Support

- The most direct way to support me is getting [Mole for Mac](https://mole.fit), my paid Mac cleanup app.
- If Kami helped you, give it a star, [share it](https://twitter.com/intent/tweet?url=https://github.com/tw93/kami&text=Kami%20-%20A%20quiet%20design%20system%20for%20professional%20documents.), or open an issue or PR.
- I have two cats, TangYuan and Coke. If you think kami delights your life, you can feed them <a href="https://cats.tw93.fun?name=Kami" target="_blank">canned food 🥩</a>.

<details>
<summary>These lovely people already did 🐱</summary>
<br/>
<a href="https://cats.tw93.fun?name=Kami"><img src="https://cdn.jsdelivr.net/gh/tw93/sponsors@main/assets/sponsors.svg" width="1000" loading="lazy" /></a>
</details>

## License

MIT License for kami code and templates. Feel free to use and contribute.

**Fonts**: TsangerJinKai02 is free for personal use only; commercial use requires a license from [tsanger.cn](https://tsanger.cn). Charter, YuMincho, Source Han Serif K under OFL, and CJK fallbacks are system-bundled or open-licensed.
