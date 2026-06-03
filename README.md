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

Kami fills that gap: one constraint language, nine templates, simple enough for agents to run reliably, strict enough that every output is something you actually want to ship. English and Chinese are first-class; Japanese and Korean work via best-effort CJK paths with visual QA before delivery.

Part of a trilogy: [Kaku](https://github.com/tw93/Kaku) (書く) writes code, [Waza](https://github.com/tw93/Waza) (技) drills habits, [Kami](https://github.com/tw93/Kami) (紙) delivers documents.

## See it

<table>
<tr>
  <td align="center" width="25%">
    <a href="assets/demos/demo-tesla.pdf"><img src="assets/demos/demo-tesla.png" alt="Tesla equity report"></a>
    <br><b>Equity Report</b> · 中文
    <br><sub>Tesla Q1 2026 财报点评</sub>
  </td>
  <td align="center" width="25%">
    <a href="assets/demos/demo-agent-slides.pdf"><img src="assets/demos/demo-agent-slides.png" alt="Agent keynote slides" /></a>
    <br><b>Slides</b> · English
    <br><sub>Agent keynote, 6 slides</sub>
  </td>
  <td align="center" width="25%">
    <a href="assets/demos/demo-resume-ko.pdf"><img src="assets/demos/demo-resume-ko.png" alt="Korean resume"></a>
    <br><b>Resume</b> · 한국어
    <br><sub>개발자 이력서, 2페이지</sub>
  </td>
  <td align="center" width="25%">
    <a href="assets/demos/demo-kaku.pdf"><img src="assets/demos/demo-kaku.png" alt="Kaku portfolio"></a>
    <br><b>Portfolio</b> · 日本語
    <br><sub>Kaku ターミナル作品集 · 7 ページ</sub>
  </td>
</tr>
</table>

## Landing Pages

The landing-page template in action: three products, one constraint set. Five `.example` companions (vercel, sitemap, robots, llms, llms-full) ship alongside for multilingual deployment.

<table>
<tr>
  <td align="center" width="33%">
    <a href="https://kami.tw93.fun"><img src="assets/showcase/kami-landing.png" alt="Kami landing page"></a>
    <br><b>Kami</b> · English
    <br><sub>Design system homepage</sub>
  </td>
  <td align="center" width="33%">
    <a href="https://luo.tw93.fun"><img src="assets/showcase/luo-landing.png" alt="Luo landing page"></a>
    <br><b>Luo</b> · 中文
    <br><sub>CJK reading font specimen</sub>
  </td>
  <td align="center" width="33%">
    <a href="https://mole.fit"><img src="assets/showcase/mole-landing.png" alt="Mole landing page"></a>
    <br><b>Mole</b> · English
    <br><sub>macOS system utility</sub>
  </td>
</tr>
</table>

## Usage

**Claude Code**

```bash
npx skills add tw93/kami -a claude-code -g -y
```

**Claude Code plugin marketplace** (requires Claude Code v2.1.142+)

```bash
/plugin marketplace add tw93/kami
/plugin install kami@kami
```

**Generic agents** (Codex, OpenCode, Pi, and other tools that read from `~/.agents/`)

```bash
npx skills add tw93/kami -a '*' -g -y
```

**Claude Desktop**

Download [kami.zip](https://github.com/tw93/kami/releases/latest/download/kami.zip), open Customize > Skills > "+" > Create skill, and upload the ZIP directly (no need to unzip).

The ZIP is lightweight: large CJK fonts are excluded from the skill package. In a repo checkout they load from local font files first, then jsDelivr CDN; in an installed skill, `scripts/ensure-fonts.sh` recovers missing Chinese or Korean fonts into the user font directory. To update: download the same URL, click "..." on the skill card, choose Replace, upload.

The skill auto-triggers from natural requests, no slash command needed. Optimized for English and Chinese; Japanese and Korean are supported via best-effort CJK paths with visual QA before delivery.

Example prompts by language:

- English: `make a one-pager for my startup` / `turn this research into a long doc` / `write a formal letter` / `make a portfolio of my projects` / `build me a resume` / `design a slide deck for my talk` / `make this talk as a Marp deck` / `build a landing page for my app`
- 中文: `帮我做一份一页纸` / `帮我排版一份长文档` / `帮我写一封正式信件` / `帮我做一份作品集` / `帮我做一份简历` / `帮我做一套演讲幻灯片` / `帮我做一份 Markdown 风格的演示稿` / `帮我做一个产品落地页`
- 日本語: `スタートアップ向けの一枚資料を作って` / `この調査を長文レポートに整えて` / `正式な依頼文を作って` / `プロジェクト作品集を作って` / `履歴書を作って` / `登壇用スライドを作って` / `Marp で登壇スライドを作って` / `アプリのランディングページを作って`
- 한국어: `스타트업 원페이저를 만들어줘` / `이 리서치를 장문 문서로 정리해줘` / `정식 레터를 작성해줘` / `프로젝트 포트폴리오를 만들어줘` / `이력서를 만들어줘` / `발표용 슬라이드를 만들어줘` / `Marp 슬라이드로 만들어줘` / `앱 랜딩 페이지를 만들어줘`

**Optional: brand profile**

Create `~/.config/kami/brand.md` to persist identity, brand, defaults, and writing habits. See [brand.example.md](references/brand.example.md) for a full template.

The file has YAML frontmatter (structured fields: name, role, email, website, GitHub, brand color, language, page size, currency locale, tone, and more) plus a Markdown body for freeform notes. Kami treats it as the lowest-resolution context: applied only when the current request is ambiguous, and always overridable by what the specific document needs. The goal is to feel familiar across your work without making every output look the same.

## Design

Warm parchment canvas, ink blue as the sole accent, serif carries hierarchy, no hard shadows or flashy palettes. Not a UI framework; a constraint system for printed matter. Documents should read as composed pages, not dashboards.

Nine template types: One-Pager, Long Doc, Letter, Portfolio, Resume, Slides, Equity Report, Changelog, and Landing Page in EN, CN, and KO. Fourteen inline SVG diagram types included. Slides ship in three rendering paths: WeasyPrint HTML to PDF (default), python-pptx (editable PPTX, on request), and a Marp variant in `assets/templates/marp/` for Markdown-first decks. Code blocks support Pygments-based syntax highlighting when `Pygments` is installed; without it, PDFs still render and code stays monochrome. Kami picks the right variant based on the language you write in.

| Element | Rule |
|---|---|
| Canvas | `#f5f4ed` parchment, never pure white |
| Accent | Ink blue `#1B365D` only, no second chromatic hue |
| Neutrals | All warm-toned (yellow-brown undertone), no cool blue-grays |
| Serif | Body 400, headings 500. Avoid synthetic bold |
| Line-height | Tight titles 1.1-1.3, dense body 1.4-1.45, reading body 1.5-1.55 |
| Shadows | Ring or whisper only, no hard drop shadows |
| Tags | Solid hex backgrounds only. `rgba()` triggers a WeasyPrint double-rectangle bug |

**Fonts**: Each language uses a single serif font for the entire page. Chinese: TsangerJinKai02. Japanese: YuMincho. Korean: Source Han Serif K. English: Charter. TsangerJinKai is free for personal use, commercial use requires a license from [tsanger.cn](https://tsanger.cn). Source Han Serif K is OFL-licensed. All other fonts are system-bundled.

Full spec: [design.md](references/design.md). Cheatsheet: [CHEATSHEET.md](CHEATSHEET.md).

## Travel

The same constraint system doubles as a brief you can hand to any drawing tool. Point it at the [references folder](references/) and the output inherits warm parchment, ink-blue restraint, single-line geometric icons, and editorial typography.

> Apply the Kami design system from github.com/tw93/kami/tree/main/references

<table>
<tr>
  <td align="center" width="33%">
    <img src="assets/illustrations/travel-tesla-optimus.png" alt="Tesla Optimus patent overview">
    <br><b>Evidence layout</b> · 中文
    <br><sub>Tesla Optimus 手部和前臂专利图一览</sub>
  </td>
  <td align="center" width="33%">
    <img src="assets/illustrations/travel-spatialvla.png" alt="SpatialVLA architecture redraw">
    <br><b>Architecture redraw</b> · English
    <br><sub>SpatialVLA Figure 1, schematic</sub>
  </td>
  <td align="center" width="33%">
    <img src="assets/illustrations/travel-3d-representations.png" alt="3D representation tradeoffs">
    <br><b>Concept tradeoff</b> · 中文
    <br><sub>3D 表示的算力-推理性取舍</sub>
  </td>
</tr>
</table>

<sub>Rendered by ChatGPT Images 2.0 in a single pass with no manual touch-up. Kami specifies, the renderer draws.</sub>

## Background

I like investing in US equities and ask Claude to write research reports all the time. Every output landed in the same default-doc look: gray, flat, a different layout each session. The structure was hard to scan, the formatting felt dated, and nothing about the page made me want to keep reading. So I started fixing the typography, the palette, the spacing, one rule at a time, until the report became a page I actually enjoyed.

Later I needed to present "The Agent You Don't Know: Principles, Architecture and Engineering Practice." I already had the document and didn't want to build slides from scratch, so I used Claude Design to lay it out in my own style, tweaked it round after round, and eventually got it to a place I was happy with. That process added inline SVG charts, a unified warm palette, and a tighter editorial rhythm. It kept growing until it covered every document I regularly ship, so I kept abstracting the process, and it became kami: one quiet design system I can hand to any agent and trust the output.

## Support

- If kami helped you, [share it](https://twitter.com/intent/tweet?url=https://github.com/tw93/kami&text=Kami%20-%20A%20quiet%20design%20system%20for%20professional%20documents.) with friends or give it a star.
- Got ideas or bugs? Open an issue or PR.
- I have two cats, TangYuan and Coke. If you think kami delights your life, you can feed them <a href="https://cats.tw93.fun?name=Kami" target="_blank">canned food 🥩</a>.

<a href="https://cats.tw93.fun?name=Kami"><img src="https://cdn.jsdelivr.net/gh/tw93/sponsors@main/assets/sponsors.svg" width="1000" loading="lazy" /></a>

## License

MIT License for kami code and templates. Feel free to use and contribute.

**Fonts**: TsangerJinKai02 (Chinese) is free for personal use only; commercial use requires a license from [tsanger.cn](https://tsanger.cn). Charter (English), YuMincho (Japanese), Source Han Serif K (Korean, OFL), and CJK fallbacks are system-bundled or open-licensed.
