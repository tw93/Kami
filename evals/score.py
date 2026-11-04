#!/usr/bin/env python3
"""Deterministic scoring for a `claude plugin eval` run of the Kami suite.

The eval harness grades what it can see (skill fired, files created, regex
and LLM reads of the HTML). It cannot run Kami's own gates on the rendered PDF,
so this script walks each kept run workspace and applies them: page contract,
atomic fact survival in the PDF text, font family, density, Markdown residue,
template style drift, the chart count for chart cases, and, for a brief that
withholds data, numbers no supplied figure accounts for. HTML-only cases
(landing pages) skip every PDF gate and read facts from the HTML text.

Run the suite with --keep-temp, then:
    python3 evals/score.py                       # newest results dir
    python3 evals/score.py evals/results/<ts>    # a specific run
    python3 evals/score.py --write               # also save gate-scores.json

Scoring is read-only by default. The harness deletes kept workspaces with the
rest of /tmp, so --write saves the rows to <results>/gate-scores.json, and a
later run reads a row back from there when its workspace is gone.
"""
from __future__ import annotations

import argparse
import contextlib
import io
import json
import os
import re
import stat
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "skills" / "kami" / "scripts"))

from checks import (  # noqa: E402
    check_markdown_residue, check_placeholders, check_resume_balance, resume_thin_source, scan_density,
)
from lint import check_style  # noqa: E402
from verify import check_fonts  # noqa: E402

# case -> (pinned output stem from prompt.md, min pages, max pages or 0 for none,
# atomic facts that must appear in the PDF text)
CONTRACTS: dict[str, tuple[str, int, int, list[str]]] = {
    "resume-cn": ("resume", 2, 2, ["林予安", "140", "900", "3.8", "1.6", "11%", "0.9%", "0.2%", "Sail UI", "1.8k"]),
    "one-pager-en": ("tidewell", 1, 1, ["$1.2M", "$310K", "38", "214", "14%", "6%", "$6M", "Leeds"]),
    "equity-report-cn": ("report", 1, 3, ["18.4", "26.9", "35.2", "42.6", "21.3%", "增持", "128"]),
    "slides-en": ("deck", 7, 12, ["400", "37", "41%", "88%", "23", "11 months"]),
    "letter-ko": ("letter", 1, 1, ["박서연", "김도윤", "90초", "Kafka", "Flink", "18"]),
    "long-doc-cn": ("whitepaper", 3, 0, ["350", "18.5", "4.2", "12.1", "2.3", "94%", "81%", "97%"]),
    "equity-report-charts-en": ("report", 1, 3, ["$412M", "$538M", "$701M", "61%", "27%", "12%", "$46", "Overweight"]),
    "portfolio-cn": ("portfolio", 1, 0, ["沈知行", "潮声", "37%", "2.4", "织页", "120", "归途", "4.6"]),
    "landing-page-en": ("index", 0, 0, ["Ledgerly", "$12", "14-day", "1,800", "40%", "CSV"]),
    "social-cards-cn": ("cards", 3, 6, ["我写代码的 6 个习惯", "验收标准", "十次有九次", "三个月后", "便签"]),
}
# Screen templates: HTML only, no PDF, so no page contract or PDF gates.
HTML_ONLY = {"landing-page-en"}
# Social cards are fixed 1242x1660 pages, often half empty by design: --deliver
# replaces the density gate with card fit for them, and the score drops density.
NO_DENSITY = {"social-cards-cn"}
# Cases whose prompt asks for charts: minimum <svg data-kami-chart> count.
MIN_CHARTS = {"equity-report-charts-en": 2}
CHART_SVG = re.compile(r"<svg\b[^>]*\bdata-kami-chart\b", re.I)
# Cases whose brief withholds data: every number with a unit in the HTML must be a
# supplied one, or, for a share or multiple (% or 倍), a ratio or percent change
# between two supplied ones, the complement of a supplied percentage, or a
# definitional percentage. Absolute units (万, 毫秒, 家, 元) take supplied values only,
# and differences are left out: with a dozen inputs they reach almost any small number.
SUPPLIED = {"long-doc-cn": (18.5, 12.1, 2.3, 4.2, 11, 48, 350, 16, 32, 3, 94, 81, 97, 90)}
DEFINITIONAL = {1.0, 50.0, 99.0, 100.0}
RELATIVE_UNITS = {"%", "个百分点", "倍"}
UNIT_NUMBER = re.compile(r"(?<![\d.A-Za-z])(\d+(?:\.\d+)?)\s*(%|个百分点|万|毫秒|ms|倍|秒|家|元|台)")
# Boolean gate columns; a row carries only the ones that applied to it.
GATES = ("contract", "fonts", "density", "residue", "balance", "placeholders", "style", "charts", "invented")


def _quiet(fn, argv: list[str]) -> tuple[int, str]:
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        try:
            code = fn(argv)
        except Exception as exc:  # a crashing gate is a failed gate, not a crashed scorer
            print(f"ERROR: {exc}")
            code = 2
    return code, buffer.getvalue().strip()


def _workspace(trace_path: str) -> Path | None:
    sealed = Path(trace_path).parent.parent / "sealed"
    if not sealed.exists():
        return None
    # The harness seals the run tree with mode 000; the scorer runs as its owner.
    sealed.chmod(sealed.stat().st_mode | stat.S_IRUSR | stat.S_IXUSR)
    cwd = sealed / "home" / "cwd"
    return cwd if cwd.exists() else None


def _deliverable(ws: Path, stem: str) -> tuple[Path | None, Path | None]:
    """Open the file names the prompt pinned, never a scratch or re-rendered copy."""
    pdf, html = ws / f"{stem}.pdf", ws / f"{stem}.html"
    return (pdf if pdf.is_file() else None), (html if html.is_file() else None)


def _pdf_text(pdf: Path) -> tuple[int, str]:
    import fitz  # PyMuPDF, already a Kami check dependency

    with fitz.open(str(pdf)) as doc:
        return len(doc), "".join(page.get_text() for page in doc)


def _html_text(html: Path, drop_svg: bool = False) -> str:
    raw = html.read_text(encoding="utf-8", errors="replace")
    raw = re.sub(r"(?is)<(style|script)\b.*?</\1>|<!--.*?-->", " ", raw)
    if drop_svg:  # chart axis ticks (0 5 10 15 20 万) are scale, not claims
        raw = re.sub(r"(?is)<svg\b.*?</svg>", " ", raw)
    import html as htmlmod

    return htmlmod.unescape(re.sub(r"<[^>]+>", " ", raw))


def _facts(row: dict, text: str, facts: list[str]) -> None:
    flat = re.sub(r"\s+", "", text)
    found = [f for f in facts if re.sub(r"\s+", "", f) in flat]
    row["facts"] = f"{len(found)}/{len(facts)}"
    row["missing"] = [f for f in facts if f not in found]


def _derivable(supplied: tuple[float, ...]) -> set[float]:
    values = DEFINITIONAL | {100 - a for a in supplied if a < 100}
    for a in supplied:
        for b in supplied:
            if a != b:
                values |= {a / b, a / b * 100, (a / b - 1) * 100, (1 - a / b) * 100}
    return values


def _invented(row: dict, text: str, supplied: tuple[float, ...]) -> None:
    """Numbers with a unit that no supplied figure accounts for, compared at the
    precision the text shows."""
    derived = _derivable(supplied)
    stray = []
    for value, unit in UNIT_NUMBER.findall(text):
        digits = len(value.split(".")[1]) if "." in value else 0
        pool = set(supplied) | (derived if unit in RELATIVE_UNITS else set())
        if not any(round(c, digits) == float(value) for c in pool):
            stray.append(value + unit)
    row["invented"] = not stray
    if stray:
        row["stray"] = sorted(set(stray))


def _html_gates(row: dict, case: str, html: Path, screen: bool | None) -> None:
    row["placeholders"] = _quiet(check_placeholders, [str(html)])[0] == 0
    row["style"] = _quiet(lambda argv: check_style(argv, screen=screen), [str(html)])[0] == 0
    count = len(CHART_SVG.findall(html.read_text(encoding="utf-8", errors="replace")))
    if count or case in MIN_CHARTS:
        row["chart_count"] = count
    if case in MIN_CHARTS:
        row["charts"] = count >= MIN_CHARTS[case]
    if case in SUPPLIED:
        _invented(row, _html_text(html, drop_svg=True), SUPPLIED[case])


def score_run(case: str, run: dict) -> dict:
    row: dict = {
        "case": case,
        "cost": run.get("costUsd") or 0.0,
        "turns": run.get("turns"),
        "secs": run.get("durationSeconds"),
        "harness": run.get("score"),
        "error": run.get("error"),
        "trace": run.get("tracePath"),
    }
    ws = _workspace(run.get("tracePath") or "")
    if ws is None:
        row["note"] = "workspace not kept (run with --keep-temp)"
        return row
    stem, lo, hi, facts = CONTRACTS[case]
    pdf, html = _deliverable(ws, stem)
    if case in HTML_ONLY:
        if html is None:
            row["note"] = f"no HTML delivered (expected {stem}.html)"
            return row
        row["html"] = str(html.relative_to(ws))
        _facts(row, _html_text(html), facts)
        row["residue"] = _quiet(check_markdown_residue, [str(html)])[0] == 0
        _html_gates(row, case, html, screen=True)
        return row
    if pdf is None:
        row["note"] = f"no PDF delivered (expected {stem}.pdf)"
        return row
    pages, text = _pdf_text(pdf)
    row.update({
        "pdf": str(pdf.relative_to(ws)),
        "pages": pages,
        "contract": lo <= pages and (hi == 0 or pages <= hi),
    })
    _facts(row, text, facts)
    row.update({
        "fonts": _quiet(check_fonts, [str(pdf)])[0] == 0,
        "residue": _quiet(check_markdown_residue, [str(pdf)])[0] == 0,
    })
    if case not in NO_DENSITY:
        _density(row, pdf)
    if case == "resume-cn":
        # Same verdict as --deliver: a shortfall the source cannot fill is a
        # reported data gap, not a layout failure.
        row["balance"] = (_quiet(check_resume_balance, [str(pdf)])[0] == 0
                          or bool(resume_thin_source(pdf)))
    if html is not None:
        _html_gates(row, case, html, screen=None)
    elif case in MIN_CHARTS:
        row["charts"] = False  # charts are counted in the HTML source
    return row


def _density(row: dict, pdf: Path) -> None:
    """Same verdict as --deliver, which runs density as advisory: only a SPARSE
    page (past `sparse_pct`, the half-empty page writing.md calls a draft
    defect) fails. WARN pages are look-here hints, counted in `density_warn`."""
    with contextlib.redirect_stdout(io.StringIO()):
        result = scan_density([str(pdf)], scan_single_page=True)
    if result is None:
        row["density"] = False
        return
    sparse, warn, missing, scanned = result
    row["density"] = scanned > 0 and missing == 0 and sparse == 0
    row["density_warn"] = warn


def gate_score(row: dict) -> float | None:
    """Share of deterministic gates passed, facts weighted as one gate."""
    if "facts" not in row:
        return 0.0 if str(row.get("note", "")).startswith(("no PDF delivered", "no HTML delivered")) else None
    gates = [row[k] for k in GATES if k in row]
    got, total = (int(x) for x in row["facts"].split("/"))
    return (sum(gates) + got / total) / (len(gates) + 1)


def _cached_rows(target: Path) -> tuple[dict, dict]:
    """Rows saved by an earlier --write, by trace path and by (case, run index)."""
    path = target / "gate-scores.json"
    try:
        rows = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return {}, {}
    by_trace, by_pos, seen = {}, {}, {}
    for row in rows:
        if not isinstance(row, dict) or "case" not in row:
            continue
        index = seen.get(row["case"], 0)
        seen[row["case"]] = index + 1
        by_pos[(row["case"], index)] = row
        if row.get("trace"):
            by_trace[row["trace"]] = row
    return by_trace, by_pos


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="score.py",
        description="Apply Kami's deterministic gates to a kept `claude plugin eval` run.",
    )
    parser.add_argument("results", nargs="?", type=Path,
                        help="results dir holding aggregate-result.json (default: newest under evals/results)")
    parser.add_argument("--write", action="store_true",
                        help="save the rows to <results>/gate-scores.json")
    args = parser.parse_args(argv[1:])
    results = HERE / "results"
    if args.results is not None:
        target = args.results
    else:
        dirs = sorted(
            p for p in results.iterdir() if (p / "aggregate-result.json").exists()
        ) if results.is_dir() else []
        if not dirs:
            print("ERROR: no results found; run claude plugin eval . --keep-temp first")
            return 2
        target = dirs[-1]
    if not (target / "aggregate-result.json").is_file():
        print(f"ERROR: {target}: no aggregate-result.json")
        return 2
    data = json.loads((target / "aggregate-result.json").read_text())
    by_trace, by_pos = _cached_rows(target)
    rows, cached = [], 0
    for case in data["cases"]:
        name = case["name"]
        if name not in CONTRACTS:
            continue
        for index, run in enumerate(case["arms"].get("with", [])):
            row = score_run(name, run)
            if "note" in row and row["note"].startswith("workspace not kept"):
                old = by_trace.get(row["trace"]) or by_pos.get((name, index))
                if old is not None and old.get("case") == name:
                    row, cached = dict(old), cached + 1
            rows.append(row)

    cols = ["case", "harness", "gates", "pages", "contract", "facts", "fonts", "density",
            "residue", "style", "placeholders", "balance", "charts", "invented", "turns", "secs", "cost"]
    print("\t".join(cols))
    total_cost = 0.0
    for row in rows:
        row["gates"] = gate_score(row)
        total_cost += row["cost"]
        cells = []
        for col in cols:
            value = row.get(col, "")
            if isinstance(value, bool):
                value = "ok" if value else "FAIL"
            elif isinstance(value, float):
                value = f"{value:.2f}"
            cells.append(str(value))
        print("\t".join(cells))
        for key in ("note", "error"):
            if row.get(key):
                print(f"  {row['case']}: {key}: {row[key]}")
        if row.get("missing"):
            print(f"  {row['case']}: missing facts: {', '.join(row['missing'])}")
        if row.get("stray"):
            print(f"  {row['case']}: numbers the brief does not account for: {', '.join(row['stray'])}")
    scored = [r["gates"] for r in rows if r["gates"] is not None]
    if scored:
        print(f"mean gate score {sum(scored) / len(scored):.2f} over {len(scored)} run(s); agent cost ${total_cost:.2f}")
    if cached:
        print(f"{cached} run(s) read from {target / 'gate-scores.json'}; their workspaces are gone")
    if args.write:
        out = target / "gate-scores.json"
        out.write_text(json.dumps(rows, ensure_ascii=False, indent=2))
        print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
