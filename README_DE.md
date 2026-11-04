<div align="center">
  <img src="skills/kami/assets/images/logo.svg" width="120" />
  <h1>Kami</h1>
  <p><b>Gute Inhalte verdienen gutes Papier.</b></p>
  <p><a href="README.md">English</a> · <a href="README_CN.md">中文</a> · <a href="README_TW.md">繁體</a> · <a href="README_JA.md">日本語</a> · <a href="README_KR.md">한국어</a> · Deutsch · <a href="README_FR.md">Français</a></p>
  <a href="https://github.com/tw93/kami/stargazers"><img src="https://img.shields.io/github/stars/tw93/kami?style=flat-square" alt="Stars"></a>
  <a href="https://github.com/tw93/kami/releases"><img src="https://img.shields.io/github/v/tag/tw93/kami?label=version&style=flat-square" alt="Version"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg?style=flat-square" alt="License"></a>
  <a href="https://x.com/HiTw93"><img src="https://img.shields.io/badge/follow-Tw93-red?style=flat-square&logo=x" alt="Twitter"></a>
</div>

## Warum Kami

Kami (紙, かみ) bedeutet auf Japanisch „Papier“. Es bietet KI-Agenten Layoutregeln und Vorlagen zur Erstellung von PDFs, PNGs und bearbeitbaren PowerPoint-Dateien, inklusive acht Dokumentvorlagen und einer Produkt-Landing-Page.

Als abschließender Teil der Trilogie für die Dokumentenbereitstellung ergänzt Kami das auf Code fokussierte [Kaku](https://github.com/tw93/Kaku) (書く) und das auf Engineering-Gewohnheiten ausgerichtete [Waza](https://github.com/tw93/Waza) (技), damit technische Ergebnisse nicht nur präzise, sondern auch visuell überzeugend sind.

## Beispiele

Beispiel-PDFs in verschiedenen Formaten und Sprachen. Klicken Sie auf eine Vorschau, um das Dokument zu öffnen.

<table>
<tr>
  <td align="center" width="25%">
    <a href="site/assets/demos/demo-musk-resume.pdf"><img src="site/assets/demos/demo-musk-resume.png" alt="Gründer-Lebenslauf"></a>
    <br><b>Lebenslauf</b> · Englisch
    <br><sub>Gründer-Lebenslauf, 2 Seiten</sub>
  </td>
  <td align="center" width="25%">
    <a href="site/assets/demos/demo-kami-print.pdf"><img src="site/assets/demos/demo-kami-print.png" alt="Kami-One-Pager, Druckversion"></a>
    <br><b>One-Pager</b> · Chinesisch
    <br><sub>Kami-Vorstellung · Druckversion</sub>
  </td>
  <td align="center" width="25%">
    <a href="site/assets/demos/demo-tesla.pdf"><img src="site/assets/demos/demo-tesla.png" alt="Tesla-Analysebericht"></a>
    <br><b>Finanzbericht</b> · Chinesisch
    <br><sub>Tesla Q1 2026 Quartalsanalyse</sub>
  </td>
  <td align="center" width="25%">
    <a href="site/assets/demos/demo-agent-slides.pdf"><img src="site/assets/demos/demo-agent-slides.png" alt="Agent-Präsentationsfolien" /></a>
    <br><b>Folien</b> · Englisch
    <br><sub>Agent-Keynote, 8 Folien</sub>
  </td>
</tr>
<tr>
  <td align="center" width="25%">
    <a href="site/assets/demos/demo-mole.pdf"><img src="site/assets/demos/demo-mole.png" alt="Mole-Produktübersicht"></a>
    <br><b>One-Pager</b> · Englisch
    <br><sub>Mole-Produktübersicht, 1 Seite</sub>
  </td>
  <td align="center" width="25%">
    <a href="site/assets/demos/demo-letter.pdf"><img src="site/assets/demos/demo-letter.png" alt="Empfehlungsschreiben"></a>
    <br><b>Brief</b> · Chinesisch
    <br><sub>Empfehlungsschreiben, 1 Seite</sub>
  </td>
  <td align="center" width="25%">
    <a href="site/assets/demos/demo-changelog.pdf"><img src="site/assets/demos/demo-changelog.png" alt="Mole Release Notes"></a>
    <br><b>Changelog</b> · Englisch
    <br><sub>Mole v1.7.1 Release Notes</sub>
  </td>
  <td align="center" width="25%">
    <a href="site/assets/demos/demo-kaku.pdf"><img src="site/assets/demos/demo-kaku.png" alt="Kaku-Portfolio"></a>
    <br><b>Portfolio</b> · Japanisch
    <br><sub>Kaku Terminal-Portfolio, 7 Seiten</sub>
  </td>
</tr>
</table>

## Installation

**Claude Code, Codex, Cursor und andere Agenten**

```bash
npx skills add tw93/kami -a claude-code codex cursor -g -y
```

Eine Kopie wird im gemeinsamen Verzeichnis `~/.agents/skills` abgelegt. Claude Code wird per Symlink verknüpft; Codex, Cursor und andere Agenten erkennen Kami als `/kami`. Aktualisierung per `npx skills update -g -y`.

Oder weisen Sie Ihren Agenten direkt an:
> Installiere Kami für mich anhand von https://kami.tw93.fun/llms.txt

**Host-Plugin**, falls Sie die Update-Befehle des jeweiligen Hosts bevorzugen (Namespace `/kami:kami`, Claude Code v2.1.142 oder neuer):

```bash
# Claude Code (Update: claude plugin update kami)
/plugin marketplace add tw93/kami
/plugin install kami@kami

# Codex (Update: codex plugin marketplace upgrade kami, danach codex plugin add kami@kami)
codex plugin marketplace add tw93/kami
codex plugin add kami@kami
```

**Claude Desktop**: Laden Sie das Release-Asset [kami.zip](https://github.com/tw93/kami/releases/latest/download/kami.zip) herunter (nicht die ZIP-Datei des GitHub-Quellcodes), öffnen Sie Customize > Skills > "+" > Create skill und laden Sie die Datei hoch. Zum Aktualisieren klicken Sie auf "..." auf der Skill-Karte, wählen Replace und laden die neueste ZIP-Datei hoch.

Große ostasiatische Schriftarten werden nicht im Paket mitgeliefert: `skills/kami/scripts/ensure-fonts.sh` lädt fehlende chinesische oder koreanische Schriftarten in das Benutzer-Font-Verzeichnis herunter. Bei einem Repository-Checkout werden die Schriften lokal eingebunden, bevor auf das jsDelivr-CDN zurückgegriffen wird.

Unter Windows empfiehlt sich WSL (Ubuntu): Die Hilfsskripte sind Bash-Skripte, und WeasyPrint braucht unter nativem Windows zusätzlich die GTK/Pango-Laufzeit.

Kami prüft höchstens einmal täglich im Hintergrund auf neue Versionen und informiert im Chat, wenn ein Update verfügbar ist. Dazu legt Kami eine Markierung im lokalen XDG-Cache-Verzeichnis ab und fragt das neueste öffentliche GitHub-Release ab; es werden keinerlei Dokument- oder Aufgabendaten übertragen, und offline oder ohne Schreibrechte im Cache-Verzeichnis wird die Prüfung still übersprungen.

## Verwendung

### Unterstützte Sprachen

Englisch und Chinesisch bieten die umfassendste Unterstützung. Japanisch und Koreanisch nutzen sprachspezifische Font-Fallbacks und angepasste Layouts, wobei jedes Ergebnis vor der Ausgabe geprüft wird. Jede Sprache verwendet auf der ganzen Seite eine einzige Serifenschrift, Deutsch wie Englisch in Charter; die Schriftlizenzen stehen unter [Lizenz](#lizenz):

| Sprache | Unterstützungsstufe | Standard-Serifenschrift |
| :--- | :--- | :--- |
| **Englisch** | Vollständig | Charter |
| **Chinesisch** (简体 / 繁體) | Vollständig | TsangerJinKai02 (仓耳今楷) |
| **Japanisch** (日本語) | Font-Fallbacks & Layoutprüfung | YuMincho (游明朝) |
| **Koreanisch** (한국어) | Font-Fallbacks & Layoutprüfung | Source Han Serif K (본명조) |

Der Skill wird automatisch durch natürliche Sprache aktiviert, ohne dass ein Schrägstrich-Befehl erforderlich ist. Beispielanfragen nach Sprache:

- Englisch: `make a one-pager for my startup` / `turn this research into a long doc` / `write a formal letter` / `make a portfolio of my projects` / `build me a resume` / `design a slide deck for my talk` / `make this talk as a Marp deck` / `build a landing page for my app`
- Chinesisch: `帮我做一份一页纸` / `帮我排版一份长文档` / `帮我写一封正式信件` / `帮我做一份作品集` / `帮我做一份简历` / `帮我做一套演讲幻灯片` / `帮我做一份 Markdown 风格的演示稿` / `帮我做一个产品落地页`
- Japanisch: `スタートアップ向けの一枚資料を作って` / `この調査を長文レポートに整えて` / `正式な依頼文を作って` / `プロジェクト作品集を作って` / `履歴書を作って` / `登壇用スライドを作って` / `Marp で登壇スライドを作って` / `アプリのランディングページを作って`
- Koreanisch: `스타트업 원페이저를 만들어줘` / `이 리서치를 장문 문서로 정리해줘` / `정식 레터를 작성해줘` / `프로젝트 포트폴리오를 만들어줘` / `이력서를 만들어줘` / `발표용 슬라이드를 만들어줘` / `Marp 슬라이드로 만들어줘` / `앱 랜딩 페이지를 만들어줘`
- Deutsch: `Erstelle einen One-Pager für mein Projekt` / `Formatiere diese Recherche als ausführlichen Bericht` / `Schreibe einen formellen Brief` / `Erstelle ein Portfolio meiner Arbeiten` / `Gestalte einen Lebenslauf für mich` / `Entwirf Vortragsfolien` / `Erstelle die Folien als Marp-Deck` / `Erstelle eine Landing-Page für meine App`

**Markenprofil** (optional)

Erstellen Sie `~/.config/kami/brand.md`, um Identität, Standardwerte und Layout-Präferenzen festzuhalten, damit Sie Ihre Vorlieben nicht für jedes Dokument wiederholen müssen. Die Datei enthält ein YAML-Frontmatter für strukturierte Felder (Name, Rolle, E-Mail, Markenfarbe, Sprache, Seitenformat, Tonalität) sowie einen Markdown-Bereich für freie Notizen. Kami nutzt diese Einstellungen dort, wo die aktuelle Anfrage etwas offenlässt; explizite Anweisungen im Prompt haben stets Vorrang. Siehe [brand.example.md](skills/kami/references/brand.example.md) für eine vollständige Vorlage.

## Designprinzipien

Standardmäßig verwendet Kami einen warmen Pergamenthintergrund (`#f5f4ed`), tintenblaue Akzente (`#1B365D`) und Serifenschriften. Hierarchien entstehen durch Schriftgröße und Weißraum. Alle Vorgaben lassen sich an das eigene Markendesign anpassen.

- **Vorlagen.** Neun Dokumentvorlagen: One-Pager, Ausführliches Dokument, Brief, Portfolio, Lebenslauf, Präsentationsfolien, Finanzbericht, Changelog und Social Cards, plus ein Landing-Page-System, jeweils auf Chinesisch, Englisch und Koreanisch. Kami wählt die passende Variante anhand der Sprache, in der Sie schreiben.
- **Diagramme.** 18 Inline-SVG-Typen, inklusive architektonischer Übersichtskarten. Sequenz-, Klassen- und ER-Diagramme können aus Mermaid-Syntax generiert werden: [beautiful-mermaid](https://github.com/lukilabs/beautiful-mermaid) rendert das SVG, und `skills/kami/scripts/mermaid_normalize.py` passt es an die Kami-Farbpalette an und macht es WeasyPrint-tauglich, ganz ohne Node.
- **Präsentationen.** Drei Rendering-Pfade: Standardmäßig WeasyPrint HTML zu PDF, python-pptx für bearbeitbare PPTX-Dateien auf Anfrage und eine Marp-Variante in `skills/kami/assets/templates/marp/` für Markdown-Folien.
- **Quellcode.** Pygments-Syntax-Highlighting bei installierter Bibliothek; ohne Pygments bleiben Codeblöcke monochrom und sauber lesbar.
- **Prüfschritte.** Content-Schemas validieren die Dokumentstruktur vor dem Rendern; Abdeckungsprüfungen stellen sicher, dass alle Fakten auf der Seite landen. Ein strukturiertes Briefing hält Zielgruppe und Anforderungen fest, und Seitenbilder dienen der abschließenden visuellen Prüfung.
- **MCP-Server.** Ein schlanker Server (`skills/kami/scripts/mcp_server.py`) stellt Werkzeuge für Diagnose, Rendering, strukturierte Prüfung und Screenshots bereit, sodass jeder MCP-fähige Agent Kami direkt ansteuern kann, ohne den vollständigen Skill-Prompt zu laden. Rendern Sie nur vertrauenswürdiges lokales HTML: referenzierte Dateien sowie HTTP- und HTTPS-Ressourcen werden mit den Rechten des MCP-Prozesses geladen.
- **Druckversion.** Pergament ist der Standard; eine optionale Weißpapier-Variante stellt den Hintergrund für Heim- und Bürodrucker auf reines Weiß um, während Tabellen und Karten ihre sanften Töne behalten. Der [einseitige Kami-Überblick](site/assets/demos/demo-kami-print.pdf) (Chinesisch) wurde mit dieser Variante gerendert, das Vorgehen steht in [production.md](skills/kami/references/production.md).

Vollständige Spezifikation: [design.md](skills/kami/references/design.md). Spickzettel: [CHEATSHEET.md](skills/kami/CHEATSHEET.md).

## Über Dokumente hinaus

<table>
<tr>
  <td align="center" width="25%" valign="top">
    <a href="https://kami.tw93.fun"><img src="site/assets/showcase/kami-landing.png" alt="Kami Landing Page" height="150"></a>
    <br><b>Kami</b> · Landing Page
    <br><sub>Design-System-Startseite</sub>
  </td>
  <td align="center" width="25%" valign="top">
    <a href="https://mole.fit"><img src="site/assets/showcase/mole-landing.png" alt="Mole Landing Page" height="150"></a>
    <br><b>Mole</b> · Landing Page
    <br><sub>macOS System-Dienstprogramm</sub>
  </td>
  <td align="center" width="25%" valign="top">
    <img src="site/assets/illustrations/travel-spatialvla.png" alt="SpatialVLA Architekturdiagramm" height="150">
    <br><b>Architekturzeichnung</b> · Englisch
    <br><sub>SpatialVLA Schema-Neuzeichnung</sub>
  </td>
  <td align="center" width="25%" valign="top">
    <img src="site/assets/illustrations/travel-tesla-optimus.png" alt="Tesla Optimus Patentübersicht" height="150">
    <br><b>Patent-Layout</b> · Chinesisch
    <br><sub>Tesla Optimus Patentzeichnung</sub>
  </td>
</tr>
</table>

Die gleichen Layoutregeln gelten für Produkt-Websites und Prompts für Bildgenerierungsmodelle. Landing Pages lassen sich als eigenständige mehrsprachige Websites bereitstellen. Illustrationen nutzen die Bildgenerierung des Hosts, wenn diese verfügbar ist; andernfalls gibt Kami dasselbe vollständige Briefing für ein Bildmodell aus.

```text
Redraw this as a clean editorial diagram. Background: warm parchment (#f5f4ed), never pure white. One accent only, ink blue (#1B365D); everything else in warm gray with a yellow-brown undertone, no other colors. Thin single-line geometric strokes and simple flat icons. No gradients, no drop shadows, no 3D. Labels in a serif typeface. Generous whitespace, calm and composed, like a figure in a well-typeset report.
```

<sub>Die beiden Illustrationen oben wurden mit ChatGPT Images in einem Durchgang erzeugt, ohne manuelle Nachbearbeitung.</sub>

## Entstehungsgeschichte

Ich investiere gerne in US-Aktien und lasse Claude oft Analysen verfassen. Jede Ausgabe sah nach demselben generischen Dokument aus: grau, kontrastarm, jedes Mal ein anderes Layout. Die Struktur war unübersichtlich und wenig einladend zum Lesen. Also begann ich Schritt für Schritt Typografie, Farben und Abstände anzupassen, bis die Berichte zu Dokumenten wurden, die man wirklich gerne liest.

Später stand ein Vortrag über KI-Agenten an. Das Dokument war fertig, aber ich wollte keine Folien von Grund auf bauen. Also nutzte ich Claude Design, um die Inhalte im gleichen Stil zu setzen. Daraus entstanden SVG-Diagramme, eine konsistente Farbpalette und ein klarer Rhythmus. Als das System für alle meine Dokumente passte, habe ich die Vorlagen und Regeln als Kami gebündelt.

## Unterstützung

- Die direkteste Unterstützung ist der Kauf meiner Mac-Bereinigungs-App [Mole for Mac](https://mole.fit)
- Wenn Kami Ihnen geholfen hat, vergeben Sie einen Stern auf GitHub, [teilen Sie das Projekt](https://x.com/intent/tweet?url=https://github.com/tw93/kami&text=Kami%20-%20A%20quiet%20design%20system%20for%20professional%20documents.) oder beteiligen Sie sich per Issue und PR
- Ich habe zwei Katzen, TangYuan und Coke, und wenn Kami Ihren Alltag bereichert hat, spendieren Sie ihnen gerne ein <a href="https://cats.tw93.fun?name=Kami" target="_blank">Dosenfutter 🥩</a>

Diese freundlichen Menschen haben bereits gespendet 🐱

<a href="https://cats.tw93.fun?name=Kami"><img src="https://raw.githubusercontent.com/tw93/sponsors/main/assets/sponsors.svg" width="1000" loading="lazy" /></a>

## Lizenz

MIT License for Kami code and templates. Please feel free to use and contribute to the development.

**Schriftarten**: TsangerJinKai02 ist für den persönlichen Gebrauch kostenlos; für die kommerzielle Nutzung ist eine Lizenz von [tsanger.cn](https://tsanger.cn) erforderlich. Source Han Serif K und JetBrains Mono stehen unter der OFL. Charter und YuMincho stammen vom Betriebssystem und werden nicht mit Kami ausgeliefert; ostasiatische Fallback-Schriften sind im System integriert oder offen lizenziert.
