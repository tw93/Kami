<div align="center">
  <img src="skills/kami/assets/images/logo.svg" width="120" />
  <h1>Kami</h1>
  <p><b>よい内容には、よい版面を</b></p>
  <p><a href="README.md">English</a> · <a href="README_CN.md">中文</a> · <a href="README_TW.md">繁體</a> · 日本語 · <a href="README_KR.md">한국어</a> · <a href="README_DE.md">Deutsch</a> · <a href="README_FR.md">Français</a></p>
  <a href="https://github.com/tw93/kami/stargazers"><img src="https://img.shields.io/github/stars/tw93/kami?style=flat-square" alt="Stars"></a>
  <a href="https://github.com/tw93/kami/releases"><img src="https://img.shields.io/github/v/tag/tw93/kami?label=version&style=flat-square" alt="Version"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg?style=flat-square" alt="License"></a>
  <a href="https://x.com/HiTw93"><img src="https://img.shields.io/badge/follow-Tw93-red?style=flat-square&logo=x" alt="Twitter"></a>
</div>

## 概要

Kami（紙、かみ）は日本語の「紙」に由来します。AI Agent に組版ルールとテンプレートを提供し、PDF、PNG、編集可能な PowerPoint を出力でき、8 種類の文書テンプレートと公式サイト用ランディングページを内蔵しています。

三部作の納品を担う最後のピースとして、コードを書く [Kaku](https://github.com/tw93/Kaku)（書く）、エンジニア習慣を鍛える [Waza](https://github.com/tw93/Waza)（技）と連携し、技術的な成果物を論理的かつ美しく仕上げます。

## 出力サンプル

多様な形式と多言語の実物 PDF サンプルです。カードをクリックするとファイルを確認できます。

<table>
<tr>
  <td align="center" width="25%">
    <a href="site/assets/demos/demo-musk-resume.pdf"><img src="site/assets/demos/demo-musk-resume.png" alt="創業者 CV"></a>
    <br><b>履歴書</b> · 英語
    <br><sub>創業者 CV、2 ページ</sub>
  </td>
  <td align="center" width="25%">
    <a href="site/assets/demos/demo-kami-print.pdf"><img src="site/assets/demos/demo-kami-print.png" alt="Kami 印刷用一枚資料"></a>
    <br><b>一枚資料</b> · 中国語
    <br><sub>Kami 紹介、白地印刷版、1 ページ</sub>
  </td>
  <td align="center" width="25%">
    <a href="site/assets/demos/demo-tesla.pdf"><img src="site/assets/demos/demo-tesla.png" alt="Tesla 決算レポート"></a>
    <br><b>株式レポート</b> · 中国語
    <br><sub>Tesla Q1 2026 決算分析</sub>
  </td>
  <td align="center" width="25%">
    <a href="site/assets/demos/demo-agent-slides.pdf"><img src="site/assets/demos/demo-agent-slides.png" alt="Agent スライド" /></a>
    <br><b>スライド</b> · 英語
    <br><sub>登壇用スライド、全 8 ページ</sub>
  </td>
</tr>
<tr>
  <td align="center" width="25%">
    <a href="site/assets/demos/demo-mole.pdf"><img src="site/assets/demos/demo-mole.png" alt="Mole 概要資料"></a>
    <br><b>一枚資料</b> · 英語
    <br><sub>Mole 製品概要、1 ページ</sub>
  </td>
  <td align="center" width="25%">
    <a href="site/assets/demos/demo-letter.pdf"><img src="site/assets/demos/demo-letter.png" alt="推薦状"></a>
    <br><b>書簡</b> · 中国語
    <br><sub>正式な推薦状、1 ページ</sub>
  </td>
  <td align="center" width="25%">
    <a href="site/assets/demos/demo-changelog.pdf"><img src="site/assets/demos/demo-changelog.png" alt="更新履歴"></a>
    <br><b>更新履歴</b> · 英語
    <br><sub>Mole v1.7.1 リリースノート</sub>
  </td>
  <td align="center" width="25%">
    <a href="site/assets/demos/demo-kaku.pdf"><img src="site/assets/demos/demo-kaku.png" alt="Kaku 作品集"></a>
    <br><b>ポートフォリオ</b> · 日本語
    <br><sub>Kaku ターミナル作品集、7 ページ</sub>
  </td>
</tr>
</table>

## インストール

**Claude Code、Codex、Cursor、その他の Agent**

```bash
npx skills add tw93/kami -a claude-code codex cursor -g -y
```

スキルは共有ディレクトリ `~/.agents/skills` に配置されます。Claude Code は自動でシンボリックリンクを作成し、Codex や Cursor など対応 Agent からは `/kami` として認識されます。更新は `npx skills update -g -y` を実行してください。

または Agent に直接指示してインストール：
> https://kami.tw93.fun/llms.txt を読んで Kami をインストールして

**プラグイン形式での利用**（ホスト自身の更新コマンドを使いたい場合、名前空間は `/kami:kami`、Claude Code v2.1.142 以降）：

```bash
# Claude Code（更新：claude plugin update kami）
/plugin marketplace add tw93/kami
/plugin install kami@kami

# Codex（更新：codex plugin marketplace upgrade kami、その後 codex plugin add kami@kami）
codex plugin marketplace add tw93/kami
codex plugin add kami@kami
```

**Claude Desktop**：GitHub Releases から正式配布用の [kami.zip](https://github.com/tw93/kami/releases/latest/download/kami.zip) をダウンロードし、Customize > Skills > "+" > Create skill からアップロードします。GitHub のソース ZIP ではなく、このリリースアセットを使ってください。更新はスキルカードの「...」から Replace を選び、最新の ZIP をアップロードします。

大容量の CJK フォントは配布パッケージに含まれていません。`skills/kami/scripts/ensure-fonts.sh` が不足している中国語や韓国語のフォントをユーザーフォントディレクトリに補い、リポジトリをチェックアウトしている場合はリポジトリ内のフォントをスキルにコピーするので、テンプレートはまずローカルのフォントを読み込み、見つからないときだけ jsDelivr CDN にフォールバックします。

Windows では WSL（Ubuntu）上での利用をおすすめします。補助スクリプトは Bash で書かれており、ネイティブの Windows で WeasyPrint を動かすには GTK/Pango ランタイムを別途インストールする必要があります。

Kami は一日に一度だけ静かにバージョンを確認し、新しいリリースがあれば会話の中で知らせます。ローカルの XDG キャッシュディレクトリにマーカーを書き込み、GitHub の最新公開リリースを確認しますが、文書や会話の内容は送信しません。オフラインのときやキャッシュディレクトリがないときは何もせずスキップします。

## 使い方

### 対応言語

英語と中国語に最も手厚く対応しています。日本語と韓国語は専用フォントフォールバックとレイアウト微調整によりサポートされ、出力前に個別検証が行われます。どの言語もページ全体で単一のセリフ書体を使い、フォントの利用条件は [ライセンス](#ライセンス) にあります：

| 言語 | サポート度 | 既定の明朝体・セリフ書体 |
| :--- | :--- | :--- |
| **English** | 完全対応 | Charter |
| **中国語**（簡体字 / 繁体字） | 完全対応 | TsangerJinKai02（倉耳今楷） |
| **日本語** | フォント代替と個別検証 | YuMincho（游明朝） |
| **韓国語** | フォント代替と個別検証 | Source Han Serif K（본명조） |

スラッシュコマンドは不要で、自然言語のリクエストから自動で起動します。各言語のプロンプト例：

- 日本語: `スタートアップ向けの一枚資料を作って` / `この調査を長文レポートに整えて` / `正式な依頼文を作って` / `プロジェクト作品集を作って` / `履歴書を作って` / `登壇用スライドを作って` / `Marp で登壇スライドを作って` / `アプリのランディングページを作って`
- 中文: `帮我做一份一页纸` / `帮我排版一份长文档` / `帮我写一封正式信件` / `帮我做一份作品集` / `帮我做一份简历` / `帮我做一套演讲幻灯片` / `帮我做一份 Markdown 风格的演示稿` / `帮我做一个产品落地页`
- English: `make a one-pager for my startup` / `turn this research into a long doc` / `write a formal letter` / `make a portfolio of my projects` / `build me a resume` / `design a slide deck for my talk` / `make this talk as a Marp deck` / `build a landing page for my app`
- 한국어: `스타트업 원페이저를 만들어줘` / `이 리서치를 장문 문서로 정리해줘` / `정식 레터를 작성해줘` / `프로젝트 포트폴리오를 만들어줘` / `이력서를 만들어줘` / `발표용 슬라이드를 만들어줘` / `Marp 슬라이드로 만들어줘` / `앱 랜딩 페이지를 만들어줘`

**ブランド設定**（任意）

`~/.config/kami/brand.md` を作成すると、アイデンティティ、ブランド、既定値、書き方の癖を保存でき、文書ごとに好みを伝え直す必要がなくなります。ファイル先頭の YAML フロントマターに名前、役職、メール、ブランド色、言語、用紙サイズ、トーンなどの構造化フィールドを書き、本文の Markdown には自由なメモを書きます。Kami は現在の依頼で決まっていない部分にこの設定を使い、明示的な指示が常に優先されます。設定例は [brand.example.md](skills/kami/references/brand.example.md) を参照してください。

## 設計原則

基本の配色は淡い紙色の背景（`#f5f4ed`）、インクブルー（`#1B365D`）のアクセント、そしてセリフ書体です。文字の大きさと余白で見出しと本文を区別します。ブランドに合わせて既定値を調整できます。

- **テンプレート群**：一枚資料、長文レポート、書簡、ポートフォリオ、履歴書、スライド、決算レポート、更新履歴の 8 種とランディングページシステム。いずれも中国語、英語、韓国語の 3 バージョンがあり、書いた言語に合わせて Kami が対応するバージョンを選びます。
- **図表コンポーネント**：18 種のインライン SVG 図表で、1 ページを使うアーキテクチャ全景図も含みます。シーケンス図、クラス図、ER 図は Mermaid で書け、[beautiful-mermaid](https://github.com/lukilabs/beautiful-mermaid) が SVG を描画し、`skills/kami/scripts/mermaid_normalize.py` が Kami の配色に直して WeasyPrint 向けに整えます。Node は同梱していません。
- **スライド**：既定は WeasyPrint による HTML から PDF、依頼に応じて python-pptx による編集可能な PPTX、Markdown 優先のデッキには `skills/kami/assets/templates/marp/` の Marp 形式を使います。
- **コード表示**：Pygments があれば構文ハイライトし、なくても PDF は生成され、コードは単色で表示されます。
- **品質検証**：JSON Schema による入力構造検査と記述抜けを防ぐカバレッジ検査を行い、構造化ブリーフが読者と要件を記録し、ページ画像で最終の目視確認をします。
- **ローカル MCP**：`skills/kami/scripts/mcp_server.py` にゼロ依存の MCP サーバーを内蔵し、環境診断、レンダリング、構造チェック、スクリーンショットのツールを提供するので、MCP 対応の Agent ならスキル全体のプロンプトを読み込まずに Kami を操作できます。信頼できるローカル HTML だけをレンダリングしてください。参照先のファイルや HTTP、HTTPS のリソースは MCP プロセスの権限で読み込まれます。
- **白地印刷**：既定は紙色の背景で、オプションの白地版に切り替えると家庭やオフィスのプリンター向けになり、カードや表には暖色の背景が残ります。[Kami 紹介の一枚資料](site/assets/demos/demo-kami-print.pdf)（中国語）はこの白地版でレンダリングしており、手順は [production.md](skills/kami/references/production.md) にあります。

詳細仕様：[design.md](skills/kami/references/design.md)、クイックリファレンス：[CHEATSHEET.md](skills/kami/CHEATSHEET.md)。

## ドキュメントの先へ

<table>
<tr>
  <td align="center" width="25%" valign="top">
    <a href="https://kami.tw93.fun"><img src="site/assets/showcase/kami-landing.png" alt="Kami ページ" height="150"></a>
    <br><b>Kami</b> · ランディングページ
    <br><sub>デザインシステム公式サイト</sub>
  </td>
  <td align="center" width="25%" valign="top">
    <a href="https://mole.fit"><img src="site/assets/showcase/mole-landing.png" alt="Mole ページ" height="150"></a>
    <br><b>Mole</b> · ランディングページ
    <br><sub>macOS システムクリーナー</sub>
  </td>
  <td align="center" width="25%" valign="top">
    <img src="site/assets/illustrations/travel-spatialvla.png" alt="SpatialVLA 構成図" height="150">
    <br><b>構成図再描画</b> · 英語
    <br><sub>SpatialVLA 論文図 1 再構成</sub>
  </td>
  <td align="center" width="25%" valign="top">
    <img src="site/assets/illustrations/travel-tesla-optimus.png" alt="Tesla Optimus 特許図" height="150">
    <br><b>特許図レイアウト</b> · 中国語
    <br><sub>Tesla Optimus 特許図面一覧</sub>
  </td>
</tr>
</table>

同じ組版ルールは、製品の公式ウェブサイト制作や画像生成 AI のプロンプト指定にもそのまま適用できます。ランディングページは多言語サイトとしてそのままデプロイできます。ホストに画像生成機能があればそれで挿絵を描き、なければ Kami が同じ内容の完全な指示文を出力し、画像モデルで使えるようにします。

```text
Redraw this as a clean editorial diagram. Background: warm parchment (#f5f4ed), never pure white. One accent only, ink blue (#1B365D); everything else in warm gray with a yellow-brown undertone, no other colors. Thin single-line geometric strokes and simple flat icons. No gradients, no drop shadows, no 3D. Labels in a serif typeface. Generous whitespace, calm and composed, like a figure in a well-typeset report.
```

<sub>表の 2 枚の挿絵は ChatGPT Images で一度に生成し、手作業の修正はしていません。</sub>

## 開発の背景

米国株投資が好きで、Claude にリサーチレポートを書かせる場面が多いです。出力はいつも既定のドキュメント風で、灰色で平板、セッションごとにレイアウトが変わる。構成は追いづらく書式は古臭く、読み続ける気になれませんでした。書体、配色、余白をひとつずつ直していき、読んでいて心地よいページに仕上げました。

その後「あなたの知らない Agent：原理、アーキテクチャとエンジニアリング実践」の発表をすることになり、Claude Design で自分のスタイルのまま組版し、何度も調整を繰り返して納得のいく仕上がりにしました。その過程で SVG 図表を加え、配色と余白を揃え、普段作る文書にも使うようになり、テンプレートとルールをまとめたものが Kami です。

## サポート

- 有料の Mac クリーナーアプリ [Mole for Mac](https://mole.fit) の購入が、最も直接的な支援になります
- Kami が役に立った場合は、スターを付けたり、[Twitter で共有](https://x.com/intent/tweet?url=https://github.com/tw93/kami&text=Kami%20-%20A%20quiet%20design%20system%20for%20professional%20documents.)したり、Issue や PR をお寄せください
- 私には湯円（TangYuan）と可楽（Coke）という二匹の猫がいて、もし Kami を気に入っていただけたら、<a href="https://cats.tw93.fun?name=Kami" target="_blank">缶詰をごちそうしてください 🥩</a>

支援してくださった方々 🐱

<a href="https://cats.tw93.fun?name=Kami"><img src="https://raw.githubusercontent.com/tw93/sponsors/main/assets/sponsors.svg" width="1000" loading="lazy" /></a>

## ライセンス

MIT License for Kami code and templates. Please feel free to use and contribute to the development.

**フォント規約**：TsangerJinKai02 は個人非商用利用のみ無料、商用利用は [tsanger.cn](https://tsanger.cn) のライセンスが必要です。Source Han Serif K と JetBrains Mono は OFL です。Charter と YuMincho は OS 付属のフォントで、Kami には同梱していません。CJK 代替フォントはシステム同梱またはオープンソースです。
