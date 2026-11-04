"""One-shot delivery gate for a filled Kami document.

The individual checks exist so they can be debugged one at a time; a finished
document needs all of them, in order, every time. Remembering that order is
the part an agent drops, so this module owns it:

    HTML   placeholders, strict math (rendered in place when present),
           Markdown residue, data charts, template style, content coverage
           (with an IR)
    render the PDF next to the HTML through the shared render pipeline
    PDF    page contract, resume balance, fonts, Markdown residue,
           density, orphans, page images for the perceptual pass
           (social cards: one page per card, card fit and card orphans in
           place of density and orphans, images at the platform's pixel size)

It ends with one verdict line. ERROR items block delivery; WARN items are
judgment calls to look at in the page images; GAP lines are `[DATA NEEDED]`
markers the closing message must list.

Usage:
    python3 scripts/build.py --deliver filled.html [content.json]
"""
from __future__ import annotations

import contextlib
import io
import json
import re
from pathlib import Path

from chart import check_charts, find_charts
from checks import (
    check_card_fit,
    check_card_orphans,
    check_density,
    check_markdown_residue,
    check_orphans,
    check_placeholders,
    check_resume_balance,
    resume_thin_source,
)
from content import check_content
from lint import check_style
from math_render import MathRenderError, _latex_spans
from math_render import main as math_main
from optional_deps import MissingDepError
from render import render_pdf
from shared import (
    HTML_TEMPLATES,
    SCREEN_TEMPLATES,
    TEMPLATES,
    is_social_cards,
    load_checks_thresholds,
    resolve_input,
)
from verify import check_fonts
from visual import CARD_REVIEW_CHECKLIST, REVIEW_CHECKLIST, render_pages, visual_output_dir

# Content IR type names that differ from the template family name.
_IR_TO_FAMILY = {"slides": "slides-weasy"}
_LOCALE_SUFFIX = re.compile(r"-(en|ko)$")
_STYLE_BLOCK = re.compile(r"<style[^>]*>(.*?)</style>", re.S | re.I)
_CSS_COMMENT = re.compile(r"/\*.*?\*/", re.S)
_SELECTOR = re.compile(r"([^{}@;]+)\{")
_GAP = re.compile(r"\[DATA NEEDED[^\]]*\]")
_TAG = re.compile(r"<[^>]+>")
_CARD = re.compile(r"<section\b[^>]*\bclass=[\"'][^\"']*\bcard\b", re.I)
_HTML_COMMENT = re.compile(r"<!--.*?-->", re.S)


def _selectors(html: str) -> set[str]:
    css = _CSS_COMMENT.sub("", " ".join(_STYLE_BLOCK.findall(html)))
    return {" ".join(s.split()) for s in _SELECTOR.findall(css) if s.strip()}


def detect_template(html: str) -> tuple[str | None, float]:
    """Return the template whose stylesheet the document still carries.

    Filled documents keep their template CSS untouched (SKILL.md «4 · Fill the template»), so
    selector overlap identifies the family without asking the author.
    """
    doc = _selectors(html)
    if not doc:
        return None, 0.0
    best, best_score = None, 0.0
    sources = {name: spec.source for name, spec in HTML_TEMPLATES.items()}
    sources.update(SCREEN_TEMPLATES)
    for name, source in sources.items():
        path = TEMPLATES / source
        if not path.exists():
            continue
        ref = _selectors(path.read_text(encoding="utf-8", errors="replace"))
        if not ref:
            continue
        score = len(doc & ref) / len(ref)
        if score > best_score:
            best, best_score = name, score
    return (best, best_score) if best_score >= 0.5 else (None, best_score)


def family(name: str) -> str:
    return _LOCALE_SUFFIX.sub("", _IR_TO_FAMILY.get(name, name))


MAX_DETAIL_LINES = 5


class Report:
    def __init__(self, base: Path) -> None:
        self.errors = 0
        self.warnings = 0
        self.prefix = f"{base}/"
        self.items: list[dict] = []

    def line(self, status: str, label: str, detail: str = "") -> None:
        if status == "ERROR":
            self.errors += 1
        elif status == "WARN":
            self.warnings += 1
        self.items.append({"status": status, "check": label, "detail": detail})
        print(f"{status + ':':<7}{label}{'  ' + detail if detail else ''}")

    def check(self, label: str, fn, argv: list[str], *, warn_only: bool = False) -> int:
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            try:
                code = fn(argv)
            except Exception as exc:  # a crashing gate must not cost the verdict
                print(f"ERROR: {type(exc).__name__}: {exc}")
                code = 2
        output = [
            ln.strip().replace(self.prefix, "")
            for ln in buffer.getvalue().splitlines()
            if ln.strip() and not ln.startswith("OK:")
        ]
        if code == 0:
            self.line("OK", label)
        else:
            self.line("WARN" if warn_only and code == 1 else "ERROR", label)
            self.items[-1]["findings"] = output
            for ln in output[:MAX_DETAIL_LINES]:
                print(f"         {ln}")
            if len(output) > MAX_DETAIL_LINES:
                print(f"         ... {len(output) - MAX_DETAIL_LINES} more; run the single check for the full list")
        return code


def _page_contract(report: Report, fam: str | None, pages: int, target: int | None) -> None:
    if fam is None:
        report.line("WARN", "page contract", f"{pages} page(s); template not recognized, no ceiling applied")
        return
    ceiling = HTML_TEMPLATES[fam].build_max_pages if fam in HTML_TEMPLATES else 0
    if fam == "resume":
        # Exactly two pages; the balance check below enforces and explains it.
        report.line("OK" if pages == 2 else "ERROR", "page contract", f"{pages} page(s), resume requires exactly 2")
    elif ceiling and pages > ceiling:
        report.line("ERROR", "page contract", f"{pages} page(s), {fam} allows at most {ceiling}")
    else:
        limit = f"at most {ceiling}" if ceiling else "no ceiling"
        report.line("OK", "page contract", f"{pages} page(s), {fam}: {limit}")
    if target and pages != target and fam != "resume":
        report.line("WARN", "page target", f"brief asks for {target}, rendered {pages}")


def deliver(args: list[str], result: dict | None = None) -> int:
    """Run every gate and print one verdict; `result`, when given, receives
    the same outcome as data (the MCP server's kami_deliver reads it)."""
    if result is None:
        result = {}
    files = [a for a in args if not a.startswith("-")]
    if not files or len(files) > 2 or not files[0].lower().endswith((".html", ".htm")):
        print("ERROR: usage: --deliver filled.html [content.json]")
        return 2
    html_path = resolve_input(files[0]).resolve()
    content_path = resolve_input(files[1]).resolve() if len(files) == 2 else None
    if not html_path.is_file():
        print(f"ERROR: {files[0]}: file not found")
        return 2
    if content_path is not None and not content_path.is_file():
        print(f"ERROR: {files[1]}: file not found")
        return 2

    raw = html_path.read_text(encoding="utf-8", errors="replace")
    ir_type, page_target = None, None
    if content_path is not None:
        try:
            data = json.loads(content_path.read_text(encoding="utf-8"))
            ir_type = data.get("type") if isinstance(data, dict) else None
            ir_type = ir_type if isinstance(ir_type, str) else None
            brief = data.get("brief") if isinstance(data, dict) else None
            if isinstance(brief, dict) and isinstance(brief.get("page_target"), int):
                page_target = brief["page_target"]
        except (json.JSONDecodeError, OSError):
            pass  # check_content below reports the malformed IR
    detected, _ = detect_template(raw)
    # A card set keeps one paper's rules and drops the other seven, which can
    # pull the selector overlap under the threshold; its palette tokens still
    # name it, and missing it would run the print gates at the print dpi.
    if not ir_type and (not detected or family(detected) != "social-cards") \
            and is_social_cards(html_path, raw):
        detected = "social-cards"
    fam = family(ir_type) if ir_type else (family(detected) if detected else None)
    screen = fam == "landing-page"

    print(f"Kami deliver: {html_path}")
    print(f"       template: {detected or 'not recognized'}"
          f"{f', content type {ir_type}' if ir_type else ''}")
    report = Report(html_path.parent)

    # --- HTML side -------------------------------------------------------
    report.check("placeholders", check_placeholders, [str(html_path)])
    try:
        spans, issues = _latex_spans(raw)
    except MathRenderError as exc:
        spans, issues = [], [str(exc)]
    math_failed = bool(issues)
    if issues:
        report.line("ERROR", "math", "; ".join(issues))
    elif spans:
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            code = math_main(["--in-place", str(html_path)])
        if code == 0:
            report.line("OK", "math", f"rendered {len(spans)} formula(s) to SVG in place")
        else:
            math_failed = True
            report.line("ERROR", "math", buffer.getvalue().strip()
                        + " (run bash scripts/ensure_mathjax.sh first)")
    else:
        report.line("OK", "math", "no formulas")
    report.check("markdown residue (html)", check_markdown_residue, [str(html_path)])
    if find_charts(raw):
        report.check("data charts", check_charts, [str(html_path)])
    # The output path rarely keeps the template file name, so hand the style
    # gate the detected family; an unrecognized document keeps the name fallback.
    report.check("template style",
                 lambda argv: check_style(argv, screen=screen if fam else None),
                 [str(html_path)], warn_only=True)
    if content_path is not None:
        report.check("content coverage", check_content, [str(content_path), str(html_path)])

    gaps = list(dict.fromkeys(_GAP.findall(_TAG.sub(" ", raw))))

    # --- Render and PDF side ---------------------------------------------
    pages_png: list[Path] = []
    rendered_pdf: Path | None = None
    if screen:
        report.line("WARN", "screen template",
                    "no PDF; screenshot the responsive matrix per locale (design.md «Responsive screenshot verification»)")
    elif math_failed:
        # render_pdf would re-run MathJax on the same TeX and report the same
        # cause a second time; one cause, one ERROR.
        report.line("SKIP", "render", "math failed; fix it and re-run --deliver")
    else:
        pdf = html_path.with_suffix(".pdf")
        try:
            pages = render_pdf(html_path, pdf)
        except MissingDepError as exc:
            print(f"ERROR: {exc}")
            return 2
        except Exception as exc:  # WeasyPrint and math failures both block delivery
            report.line("ERROR", "render", str(exc))
            pages = 0
        if pages:
            rendered_pdf = pdf
            report.line("OK", "render", f"{pdf.name} ({pages} page(s))")
            _page_contract(report, fam, pages, page_target)
            if fam == "resume":
                thin = resume_thin_source(pdf) if pages == 2 else None
                if thin:
                    report.line("WARN", "resume balance", thin)
                else:
                    report.check("resume balance", check_resume_balance, [str(pdf)])
            social = fam == "social-cards"
            if social:
                cards = len(_CARD.findall(_HTML_COMMENT.sub("", raw)))
                report.line("OK" if cards == pages else "ERROR", "one page per card",
                            f"{cards} card(s), {pages} page(s)"
                            + ("" if cards == pages else "; a card that outgrew 1660px spilled over, split it"))
            report.check("fonts", check_fonts, [str(pdf)])
            report.check("markdown residue (pdf)", check_markdown_residue, [str(pdf)])
            if social:
                report.check("card fit", check_card_fit, [str(pdf)])
                report.check("card orphans", check_card_orphans, [str(pdf)], warn_only=True)
            else:
                report.check("density", check_density, [str(pdf)], warn_only=True)
                report.check("orphans", check_orphans, [str(pdf)], warn_only=True)
            dpi = int(load_checks_thresholds()["social_cards"]["image_dpi"]) if social else None
            try:
                pages_png = render_pages(pdf, dpi=dpi)
                report.line("OK", "page images", f"{visual_output_dir(pdf).name}/ ({len(pages_png)} image(s))")
            except MissingDepError as exc:
                print(f"ERROR: {exc}")
                return 2
            except Exception as exc:
                report.line("ERROR", "page images", str(exc))

    for gap in gaps:
        print(f"GAP:   {gap}")
    checklist = CARD_REVIEW_CHECKLIST if fam == "social-cards" else REVIEW_CHECKLIST
    result.update({
        "html": str(html_path),
        "template": detected,
        "content_type": ir_type,
        "checks": report.items,
        "gaps": gaps,
        "page_images": [str(p) for p in pages_png],
        "review_checklist": list(checklist) if pages_png else [],
    })
    if rendered_pdf is not None:
        result["pdf"] = str(rendered_pdf)

    if report.errors:
        verdict = f"NOT READY: {report.errors} error(s), {report.warnings} warning(s)"
    else:
        verdict = f"READY: 0 errors, {report.warnings} warning(s), {len(gaps)} data gap(s) to report"
    print(verdict)
    result.update({"ready": not report.errors, "verdict": verdict})
    if pages_png:
        print("Next: view every page image against this checklist, fix what you see, re-run --deliver:")
        for item in checklist:
            print(f"  - {item}")
    return 1 if report.errors else 0
