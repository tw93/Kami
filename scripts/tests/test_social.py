"""Social cards: the papers, their lint scope, and the card gates in --deliver."""
from __future__ import annotations

from support import check, skip

import contextlib
import io
import re
import tempfile
from pathlib import Path

from lint import _off_palette_findings, _social_palette_findings, scan_text
from optional_deps import MissingDepError, require_pymupdf, require_weasyprint_html
from shared import TEMPLATES, load_social_palettes, load_tokens, social_palette_values

SOCIAL_TEMPLATES = ("social-cards.html", "social-cards-en.html", "social-cards-ko.html")


def _luminance(hex_color: str) -> float:
    def channel(c: int) -> float:
        c /= 255
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b)


def _contrast(a: str, b: str) -> float:
    hi, lo = sorted((_luminance(a), _luminance(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def test_social_papers_meet_their_contrast_floors() -> None:
    papers = load_social_palettes()
    weak = [
        (name, role, round(_contrast(paper["bg"], paper[role]), 2))
        for name, paper in papers.items()
        for role, floor in (("fg", 8.8), ("accent", 6.0), ("muted", 4.3))
        if _contrast(paper["bg"], paper[role]) < floor
    ]
    check("social papers: at least eight, parchment first", len(papers) >= 8
          and next(iter(papers)) == "parchment", str(list(papers)))
    check("social papers keep text 8.8:1, accent 6:1, muted 4.3:1", not weak, str(weak))
    tokens = {k: v.lower() for k, v in load_tokens().items()}
    parchment = papers["parchment"]
    check("parchment paper is the print palette",
          (parchment["bg"].lower(), parchment["fg"].lower(), parchment["accent"].lower(),
           parchment["muted"].lower())
          == (tokens["--parchment"], tokens["--near-black"], tokens["--brand"], tokens["--stone"]),
          str(parchment))


def test_social_templates_mirror_the_palette_file() -> None:
    clean = {name: _social_palette_findings(TEMPLATES / name) for name in SOCIAL_TEMPLATES}
    check("every social-cards template mirrors social-palettes.json",
          all(not f for f in clean.values()),
          str({k: [x.excerpt for x in v] for k, v in clean.items() if v}))
    with tempfile.TemporaryDirectory() as tmp:
        drifted = Path(tmp, "social-cards.html")
        raw = (TEMPLATES / "social-cards.html").read_text(encoding="utf-8")
        drifted.write_text(raw.replace("--social-teal-accent:    #a8d0cf",
                                       "--social-teal-accent:    #a8d0d0"), encoding="utf-8")
        missing = Path(tmp, "social-cards-en.html")
        missing.write_text(re.sub(r"  body\.paper-pine [^\n]*\n", "", raw), encoding="utf-8")
        drift_found = [f.excerpt for f in _social_palette_findings(drifted)]
        missing_found = [f.excerpt for f in _social_palette_findings(missing)]
    check("palette drift is reported per token",
          any("--social-teal-accent" in f for f in drift_found), str(drift_found))
    check("a paper without its body rule is reported",
          any("body.paper-pine" in f for f in missing_found), str(missing_found))


def test_social_values_stay_out_of_documents() -> None:
    teal = load_social_palettes()["teal"]["bg"]
    snippet = f"<style>.card {{ background: {teal}; }}</style>"
    with tempfile.TemporaryDirectory() as tmp:
        document = Path(tmp, "one-pager.html")
        document.write_text(snippet, encoding="utf-8")
        cards = Path(tmp, "social-cards-x.html")
        cards.write_text(snippet, encoding="utf-8")
        # A filled set saved under any name is known by its palette tokens.
        filled = Path(tmp, "cards.html")
        filled.write_text(f"<style>:root {{ --social-teal-bg: {teal}; }}</style>{snippet}",
                          encoding="utf-8")
        tokens = {v.lower() for v in load_tokens().values()}
        from lint import _allowed_for
        doc_hits = _off_palette_findings(document, _allowed_for(document, tokens))
        card_hits = _off_palette_findings(cards, _allowed_for(cards, tokens))
        filled_hits = _off_palette_findings(filled, _allowed_for(filled, tokens,
                                                                 filled.read_text(encoding="utf-8")))
    check("a social paper in a document is still off-palette", bool(doc_hits))
    check("the same value in a social card file is allowed", not card_hits,
          str([f.excerpt for f in card_hits]))
    check("a filled set named cards.html is allowed its paper", not filled_hits,
          str([f.excerpt for f in filled_hits]))
    check("social palette values are not print tokens",
          teal.lower() in social_palette_values() and teal.lower() not in tokens)


def test_social_line_height_ceiling_is_scoped() -> None:
    css = "<style>:root { --social-ink-bg: #1B365D; } .body { line-height: 1.75; }</style>"
    social = scan_text(css, Path("cards.html"))
    print_css = css.replace("--social-ink-bg: #1B365D;", "--brand: #1B365D;")
    document = scan_text(print_css, Path("doc.html"))
    check("social cards may set body type at 1.75",
          not [f for f in social if f.rule == "line-height-too-loose"], str(social))
    check("a document at 1.75 is still too loose",
          any(f.rule == "line-height-too-loose" for f in document), str(document))


def _deliver(html: Path) -> str:
    from deliver import deliver
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        deliver([str(html)])
    return out.getvalue()


def _card(heading: str, items: list[str]) -> str:
    rows = "".join(f'  <div class="item"><div class="n">{i:02d}</div><p>{t}</p></div>\n'
                   for i, t in enumerate(items, 1))
    return (f'<section class="card">\n  <div class="meta">Kami</div>\n  <h2>{heading}</h2>\n'
            f'{rows}  <div class="foot">Kami social cards</div>\n</section>\n')


def _set(cards: str, paper: str = "paper-pine") -> str:
    raw = (TEMPLATES / "social-cards-en.html").read_text(encoding="utf-8")
    head = raw.split("</head>", 1)[0].replace("{{Title}}", "Kami").replace("{{Author}}", "Kami")
    return f'{head}</head>\n<body class="{paper}">\n{cards}</body>\n</html>\n'


def test_social_cards_deliver_gates() -> None:
    try:
        require_weasyprint_html()
        fitz = require_pymupdf()
    except MissingDepError as exc:
        skip("social cards deliver gates", str(exc))
        return
    short = "Keep the author's words exactly as they were written for the post."
    with tempfile.TemporaryDirectory() as tmp:
        good = Path(tmp, "good.html")
        good.write_text(_set(_card("Two rules", [short, short])), encoding="utf-8")
        good_report = _deliver(good)
        images = sorted(Path(tmp, "good-visual").glob("page-*.png"))
        sizes = [(int.from_bytes(image.read_bytes()[16:20], "big"),
                  int.from_bytes(image.read_bytes()[20:24], "big")) for image in images]

        crowded = Path(tmp, "crowded.html")
        # The second card overflows; the first may be a text-only cover.
        crowded.write_text(_set(_card("Fits", [short]) + _card("Too many", [short * 3] * 6)),
                           encoding="utf-8")
        crowded_report = _deliver(crowded)

    check("a fitting card set delivers READY", "READY: 0 errors" in good_report, good_report[-600:])
    check("card images come out at 1242x1660", sizes == [(1242, 1660)], str(sizes))
    check("an overflowing card fails one page per card",
          "ERROR: one page per card" in crowded_report, crowded_report[-900:])
    check("an overflowing card fails card fit", "ERROR: card fit" in crowded_report,
          crowded_report[-900:])


def test_card_orphans_find_a_short_cjk_tail() -> None:
    try:
        require_weasyprint_html()
        fitz = require_pymupdf()
    except MissingDepError as exc:
        skip("card orphans", str(exc))
        return
    from checks import card_orphans
    import render
    raw = (TEMPLATES / "social-cards.html").read_text(encoding="utf-8")
    head = raw.split("</head>", 1)[0].replace("{{标题}}", "卡片").replace("{{作者}}", "Kami")
    # 42px type in a 930px column holds 22 characters per line: 22 + 2 leaves
    # a two-character tail, 22 + 8 does not.
    tail = "这" * 22 + "个。"
    body = "这" * 22 + "是一个正常的结尾。"
    cards = "".join(
        f'<section class="card"><div class="meta">卡片</div><h2>第 1 条</h2>'
        f'<div class="item"><div class="n">01</div><p>{text}</p></div>'
        f'<div class="foot">卡片</div></section>' for text in (tail, body))
    with tempfile.TemporaryDirectory() as tmp:
        html = Path(tmp, "cards.html")
        html.write_text(f"{head}</head><body class=\"paper-espresso\">{cards}</body></html>",
                        encoding="utf-8")
        render.render_pdf(html, html.with_suffix(".pdf"))
        with fitz.open(str(html.with_suffix(".pdf"))) as doc:
            found = [card_orphans(page, 3) for page in doc]
    check("a two-character CJK tail is a card orphan", bool(found and found[0]), str(found))
    check("a full last line is not", len(found) == 2 and not found[1], str(found))


def _render_cards(tmp: str, name: str, cards: str, template: str = "social-cards-en.html",
                  paper: str = "paper-pine"):
    import render
    raw = (TEMPLATES / template).read_text(encoding="utf-8")
    head = raw.split("</head>", 1)[0]
    for slot in ("{{Title}}", "{{标题}}", "{{제목}}"):
        head = head.replace(slot, "Kami")
    for slot in ("{{Author}}", "{{作者}}", "{{작성자}}"):
        head = head.replace(slot, "Kami")
    html = Path(tmp, f"{name}.html")
    html.write_text(f'{head}</head><body class="{paper}">{cards}</body></html>', encoding="utf-8")
    pdf = html.with_suffix(".pdf")
    render.render_pdf(html, pdf)
    return html, pdf


def test_card_fit_reports_each_failure() -> None:
    try:
        require_weasyprint_html()
        fitz = require_pymupdf()
    except MissingDepError as exc:
        skip("card fit branches", str(exc))
        return
    from checks import card_fit_issues

    def body(style: str) -> str:
        return (f'<section class="card"><div class="meta">Kami</div><h2>Fit</h2>'
                f'<p class="body" style="position: absolute; left: 96px; {style}">A short line.</p>'
                f'<div class="foot">Kami social cards</div></section>')

    with tempfile.TemporaryDirectory() as tmp:
        photo = Path(tmp, "photo.png")
        fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 40, 30), 0).save(str(photo))
        cover = (f'<section class="card cover"><div class="meta">Kami</div><h1>Title</h1>'
                 f'<div class="photo"><img src="{photo.name}" alt=""></div>'
                 f'<p class="body" style="position: absolute; left: 96px; top: 700px">On the photo.</p>'
                 f'</section>')
        _, pdf = _render_cards(tmp, "fit", cover + body("top: 640px") + body("top: 1440px")
                               + body("top: 1540px"))
        with fitz.open(str(pdf)) as doc:
            found = [card_fit_issues(page, 40, 24, cover=i == 0) for i, page in enumerate(doc)]
    check("card fit: four cards, four pages", len(found) == 4, str(found))
    if len(found) != 4:
        return
    check("text over the cover photo is reported",
          any("on the photo" in f for f in found[0]), str(found[0]))
    check("a card with room above its footer passes", not found[1], str(found[1]))
    check("text crowding the footer is reported",
          any("between the content and the footer" in f for f in found[2]), str(found[2]))
    check("text under the footer is reported",
          any("under the footer" in f for f in found[3]), str(found[3]))


def test_card_orphans_skip_list_numbers_and_catch_one_word() -> None:
    try:
        require_weasyprint_html()
        fitz = require_pymupdf()
    except MissingDepError as exc:
        skip("card orphans on lists", str(exc))
        return
    from checks import card_orphans
    items = "".join(f'<div class="item"><div class="n">{i:02d}</div><p>One short line.</p></div>'
                    for i in (1, 2, 3))
    lists = (f'<section class="card"><div class="meta">Kami</div><h2>Rules</h2>{items}'
             f'<div class="foot">Kami</div></section>')
    # The break is forced: a measure-driven wrap depended on Charter, and on a runner without it the
    # fallback face fit the whole line in 330px, so the one-word case never wrapped there.
    def tail(text: str) -> str:
        return (f'<section class="card"><div class="meta">Kami</div><h2>Tail</h2>'
                f'<p class="body">{text}</p><div class="foot">Kami</div></section>')
    with tempfile.TemporaryDirectory() as tmp:
        _, pdf = _render_cards(tmp, "orphans", lists + tail("aaaaaa bbbbbb cccccc<br>dddddd")
                               + tail("aaaaaa bbbbbb cccccc<br>dd ee"))
        with fitz.open(str(pdf)) as doc:
            found = [card_orphans(page, 3, 1) for page in doc]
    check("orphans: three cards, three pages", len(found) == 3, str(found))
    if len(found) != 3:
        return
    check("stacked single-line list numbers are not an orphan", not found[0], str(found[0]))
    check("a one-word last line in Latin text is an orphan", bool(found[1]), str(found[1]))
    check("a two-word last line is not", not found[2], str(found[2]))


def test_trimmed_card_set_still_delivers_as_cards() -> None:
    try:
        require_weasyprint_html()
        require_pymupdf()
    except MissingDepError as exc:
        skip("trimmed card set", str(exc))
        return
    raw = (TEMPLATES / "social-cards-en.html").read_text(encoding="utf-8")
    head = raw.split("</head>", 1)[0].replace("{{Title}}", "Kami").replace("{{Author}}", "Kami")
    # One paper per set: an agent deletes the seven unused paper rules and the shot rules.
    head = re.sub(r"  body\.paper-[^\n]*\n", "", head)
    head = re.sub(r"  body\[class[^\n]*\n", "", head)
    head = re.sub(r"  \.shot[^\n]*\{[^}]*\}\n", "", head)
    head = re.sub(r"  \.shot img[^\n]*\n", "", head)
    short = "Keep the author's words exactly as they were written for the post."
    with tempfile.TemporaryDirectory() as tmp:
        html = Path(tmp, "cards.html")
        html.write_text(f"{head}</head>\n<body>\n{_card('Two rules', [short, short])}</body>\n</html>\n",
                        encoding="utf-8")
        from deliver import detect_template
        _, score = detect_template(html.read_text(encoding="utf-8"))
        report = _deliver(html)
    check("the trimmed set falls under the stylesheet threshold", score < 0.5, str(score))
    check("a trimmed set is still delivered as social cards",
          "one page per card" in report and "card fit" in report, report[-700:])
