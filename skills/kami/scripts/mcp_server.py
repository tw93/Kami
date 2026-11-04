#!/usr/bin/env python3
"""kami MCP server: render, check, and screenshot tools over stdio JSON-RPC.

Lets any MCP-capable agent use Kami as an engine (render + verify) without
reading SKILL.md: judgment stays in the skill prompt, execution lives here.
Render only trusted local HTML: referenced file, HTTP, and HTTPS resources load
with this process's filesystem and network permissions.
Zero third-party dependencies for the protocol itself; tools that need
weasyprint / pypdf / PyMuPDF surface the install hint as a tool error
instead of crashing the server.

Register with an MCP client, for example:
    claude mcp add kami -- python3 /absolute/path/to/kami/scripts/mcp_server.py

Tools:
    kami_templates   discover templates, diagram library, content schema types
    kami_doctor      report installed render, check, PPTX, and font capabilities
    kami_render      render a filled HTML file to PDF (WeasyPrint + highlight)
    kami_check       run deterministic checks with stable findings and coverage
    kami_deliver     finish a document: every gate in order, render, one READY verdict
    kami_screenshot  rasterize a PDF to page PNGs plus the review checklist

Transport: newline-delimited JSON-RPC 2.0 on stdin/stdout (MCP stdio).
All check output is captured; nothing but protocol frames touches stdout.
"""
from __future__ import annotations

import contextlib
import io
import json
import os
import sys
from pathlib import Path

from chart import check_charts
from checks import (
    check_density,
    check_markdown_residue,
    check_orphans,
    check_placeholders,
)
from content import check_content
from deliver import deliver
from lint import check_style
from math_render import check_latex_file
from optional_deps import MissingDepError, doctor_report
from render import render_pdf
from shared import (
    DIAGRAM_TEMPLATES,
    HTML_TEMPLATES,
    MARP_TEMPLATES,
    PPTX_TEMPLATES,
    ROOT,
    SCREEN_TEMPLATES,
    content_schema_types,
    kami_version,
)
from visual import MAX_DPI, MIN_DPI, REVIEW_CHECKLIST, render_pages
from verify import check_fonts

PROTOCOL_VERSION = "2025-11-25"
SUPPORTED_PROTOCOL_VERSIONS = {"2024-11-05", "2025-03-26", "2025-06-18", "2025-11-25"}

CHECK_RULESET_VERSION = 4
CHECK_REGISTRY = {
    "html.placeholders": {
        "scope": "html", "severity": "error", "required_engine": "stdlib",
        "explanation": "Completed HTML must not expose unresolved template placeholders.",
    },
    "html.markdown-residue": {
        "scope": "html", "severity": "error", "required_engine": "stdlib",
        "explanation": "Rendered audience copy must not expose raw Markdown syntax.",
    },
    "html.math": {
        "scope": "html", "severity": "error", "required_engine": "stdlib",
        "explanation": "Completed HTML must not expose raw or invalid LaTeX source.",
    },
    "html.charts": {
        "scope": "html", "severity": "error", "required_engine": "stdlib",
        "explanation": "Every generated data chart must still match the data spec it embeds.",
    },
    "html.style": {
        "scope": "html", "severity": "warning", "required_engine": "stdlib",
        "explanation": "Document CSS must keep to the template rule set (palette, emphasis, rules).",
    },
    "content.contract": {
        "scope": "content-ir", "severity": "error", "required_engine": "stdlib",
        "explanation": "Content IR must satisfy its document schema and optional artifact brief.",
    },
    "content.coverage": {
        "scope": "html+content-ir", "severity": "error", "required_engine": "stdlib",
        "explanation": "Every atomic fact and required asset in content IR must survive into the document.",
    },
    "pdf.markdown-residue": {
        "scope": "pdf", "severity": "error", "required_engine": "pypdf",
        "explanation": "Extracted PDF text must not expose raw Markdown syntax.",
    },
    "pdf.fonts": {
        "scope": "pdf", "severity": "error", "required_engine": "pymupdf",
        "explanation": "CJK text must be drawn by a serif from the template stack, not a fallback face.",
    },
    "pdf.orphans": {
        "scope": "pdf", "severity": "warning", "required_engine": "pymupdf",
        "explanation": "Rendered text blocks must not end in short orphan lines.",
    },
    "pdf.density": {
        "scope": "pdf", "severity": "warning", "required_engine": "pymupdf",
        "explanation": "Rendered pages must not carry excessive trailing whitespace.",
    },
}

# Every gate `--deliver` runs, and the kami_check rule that covers it on its
# own. Gates that need the fresh render or the detected template family live
# only in kami_deliver. test_mcp asserts this map names every deliver gate, so
# a new gate cannot silently skip the MCP surface.
DELIVER_GATE_RULES = {
    "placeholders": "html.placeholders",
    "math": "html.math",
    "markdown residue (html)": "html.markdown-residue",
    "data charts": "html.charts",
    "template style": "html.style",
    "content coverage": "content.coverage",
    "fonts": "pdf.fonts",
    "markdown residue (pdf)": "pdf.markdown-residue",
    "density": "pdf.density",
    "orphans": "pdf.orphans",
}
DELIVER_ONLY_GATES = {"render", "page contract", "page target", "resume balance", "page images",
                      "screen template", "one page per card", "card fit", "card orphans"}

TOOLS = [
    {
        "name": "kami_templates",
        "description": (
            "List Kami document templates, browser-only templates, the diagram "
            "library, and content schema types, with the reference docs to read "
            "before filling."
        ),
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "kami_doctor",
        "description": (
            "Report whether this installed Kami runtime can render PDFs, run "
            "visual checks, build editable PPTX fallback decks, and resolve "
            "the expected font families. Read-only; missing capabilities are "
            "reported explicitly rather than treated as clean checks."
        ),
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "kami_render",
        "description": (
            "Render trusted local Kami HTML to PDF via WeasyPrint, with "
            "build-time code highlighting. Referenced file, HTTP, and HTTPS "
            "resources load with this process's permissions. Returns the PDF "
            "path and page count."
        ),
        "inputSchema": {
            "type": "object",
            "required": ["html"],
            "properties": {
                "html": {"type": "string", "description": "Path to the filled HTML file"},
                "out": {"type": "string", "description": "Output PDF path (default: same stem .pdf)"},
            },
        },
    },
    {
        "name": "kami_check",
        "description": (
            "Run Kami's deterministic checks on one existing file without "
            "rendering. HTML: placeholders + strict mathematics + markdown "
            "residue + data charts + template style (+ content coverage when a "
            "content IR JSON is given). PDF: markdown residue + CJK fonts + "
            "orphans + density. JSON: content IR schema validation. Returns the "
            "legacy report plus stable rule IDs, findings, coverage status, and "
            "explicit degraded checks. To finish a document use kami_deliver, "
            "which also renders and enforces the page contract."
        ),
        "inputSchema": {
            "type": "object",
            "required": ["path"],
            "properties": {
                "path": {"type": "string", "description": "File to check (.html, .pdf, or content .json)"},
                "content": {"type": "string", "description": "Optional content IR JSON to verify coverage against an HTML file"},
            },
        },
    },
    {
        "name": "kami_deliver",
        "description": (
            "Finish a filled Kami document in one call, the same gate as "
            "`build.py --deliver`: HTML checks, strict mathematics rendered in "
            "place, data charts, template style, content coverage, then the PDF "
            "render, page contract, resume balance, CJK fonts, residue, "
            "density, orphans, and page images. Writes the PDF and page PNGs "
            "next to the HTML. Returns ready, the verdict, every check with "
            "its findings, data gaps to report, and the review checklist; view "
            "every page image against it before shipping."
        ),
        "inputSchema": {
            "type": "object",
            "required": ["html"],
            "properties": {
                "html": {"type": "string", "description": "Path to the filled HTML file"},
                "content": {"type": "string", "description": "Optional content IR JSON (enables coverage and the page target)"},
            },
        },
    },
    {
        "name": "kami_screenshot",
        "description": (
            "Rasterize every PDF page to PNG for a perceptual review pass. "
            "Writes or replaces <pdf-stem>-visual/page-*.png, then returns the "
            "image paths, deterministic CJK font verdict, and fixed review "
            "checklist; view every image against the checklist before shipping."
        ),
        "inputSchema": {
            "type": "object",
            "required": ["pdf"],
            "properties": {
                "pdf": {"type": "string", "description": "Path to the rendered PDF"},
                "dpi": {
                    "type": "integer",
                    "minimum": MIN_DPI,
                    "maximum": MAX_DPI,
                    "description": "Render DPI (default from checks thresholds)",
                },
            },
        },
    },
]


def _resolve(raw: str) -> Path:
    path = Path(raw).expanduser()
    return path if path.is_absolute() else (Path.cwd() / path)


def tool_templates(_args: dict) -> dict:
    return {
        "version": kami_version(),
        "document_templates": {name: spec.source for name, spec in HTML_TEMPLATES.items()},
        "screen_templates": dict(SCREEN_TEMPLATES),
        "pptx_templates": dict(PPTX_TEMPLATES),
        "marp_templates": dict(MARP_TEMPLATES),
        "diagram_templates": dict(DIAGRAM_TEMPLATES),
        "content_schema_types": content_schema_types(),
        "templates_dir": str(ROOT / "assets" / "templates"),
        "diagrams_dir": str(ROOT / "assets" / "diagrams"),
        "schemas_dir": str(ROOT / "references" / "schemas"),
        # The SKILL.md "New document" tier: templates carry every token, so
        # design.md is opened per component, not read whole before filling.
        "read_before_filling": [
            str(ROOT / "SKILL.md"),
            str(ROOT / "CHEATSHEET.md"),
            str(ROOT / "references" / "writing.md"),
        ],
    }


def tool_doctor(_args: dict) -> dict:
    return doctor_report()


def tool_render(args: dict) -> dict:
    html_path = _resolve(args["html"])
    if not html_path.exists():
        raise FileNotFoundError(f"HTML file not found: {html_path}")
    if html_path.suffix.lower() not in {".html", ".htm"}:
        raise ValueError(f"input must be an HTML file: {html_path.name}")
    out = _resolve(args["out"]) if args.get("out") else html_path.with_suffix(".pdf")
    if out.suffix.lower() != ".pdf":
        raise ValueError(f"output must use a .pdf suffix: {out.name}")
    if out.is_symlink():
        raise ValueError("output PDF must not be a symbolic link")
    same_file = out.resolve(strict=False) == html_path.resolve(strict=False)
    if out.exists():
        try:
            same_file = same_file or os.path.samefile(html_path, out)
        except OSError:
            pass
    if same_file:
        raise ValueError("output PDF must not overwrite the source HTML")
    # render_pdf is the same pipeline build.py and verify.py use: highlight,
    # WeasyPrint, Kami metadata, page count.
    pages = render_pdf(html_path, out)
    return {"pdf": str(out), "pages": pages}


def _run_check(fn, argv: list[str], **kwargs) -> tuple[int, str]:
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        code = fn(argv, **kwargs)
    return code, buffer.getvalue().rstrip()


def _check_plan(path: Path, content: str | None) -> list[tuple[str, object, list[str]]]:
    suffix = path.suffix.lower()
    if suffix in {".html", ".htm"}:
        checks: list[tuple[str, object, list[str]]] = [
            ("html.placeholders", check_placeholders, [str(path)]),
            ("html.math", check_latex_file, [str(path)]),
            ("html.markdown-residue", check_markdown_residue, [str(path)]),
            ("html.charts", check_charts, [str(path)]),
            ("html.style", check_style, [str(path)]),
        ]
        if content:
            content_path = str(_resolve(content))
            checks.append((
                "content.contract",
                check_content,
                [content_path, str(path)],
            ))
        return checks
    if suffix == ".pdf":
        return [
            ("pdf.markdown-residue", check_markdown_residue, [str(path)]),
            ("pdf.fonts", check_fonts, [str(path)]),
            ("pdf.orphans", check_orphans, [str(path)]),
            ("pdf.density", check_density, [str(path)]),
        ]
    if suffix == ".json":
        return [("content.contract", check_content, [str(path)])]
    raise ValueError(f"unsupported file type: {path.name} (expected .html, .pdf, or .json)")


def tool_check(args: dict) -> dict:
    path = _resolve(args["path"])
    if not path.exists():
        raise FileNotFoundError(f"file not found: {path}")

    reports: list[str] = []
    coverage: list[dict] = []
    findings: list[dict] = []
    worst = 0
    def record(rule_id: str, code: int, report: str) -> None:
        nonlocal worst
        worst = max(worst, code)
        status = "passed" if code == 0 else ("failed" if code == 1 else "degraded")
        rule = {"id": rule_id, **CHECK_REGISTRY[rule_id]}
        coverage.append({**rule, "status": status, "exit_code": code})
        if status != "passed":
            findings.append({**rule, "status": status, "evidence": report})

    for rule_id, fn, argv in _check_plan(path, args.get("content")):
        if rule_id == "content.contract" and len(argv) == 2:
            phase_codes: dict[str, int] = {}
            _, report = _run_check(fn, argv, phase_codes=phase_codes)
            reports.append(report)
            contract_code = phase_codes.get("contract", 2)
            record("content.contract", contract_code, report)
            if contract_code == 0 and "coverage" in phase_codes:
                record("content.coverage", phase_codes["coverage"], report)
            else:
                rule = {"id": "content.coverage", **CHECK_REGISTRY["content.coverage"]}
                coverage.append({
                    **rule,
                    "status": "not_run",
                    "exit_code": None,
                    "blocked_by": "content.contract",
                })
            continue
        code, report = _run_check(fn, argv)
        reports.append(report)
        record(rule_id, code, report)
    return {
        "ruleset_version": CHECK_RULESET_VERSION,
        "exit_code": worst,
        "ok": worst == 0,
        "degraded": any(item["status"] == "degraded" for item in coverage),
        "findings": findings,
        "coverage": coverage,
        "report": "\n".join(reports),
    }


def tool_deliver(args: dict) -> dict:
    html_path = _resolve(args["html"])
    if not html_path.exists():
        raise FileNotFoundError(f"HTML file not found: {html_path}")
    argv = [str(html_path)]
    if args.get("content"):
        argv.append(str(_resolve(args["content"])))
    result: dict = {}
    code, report = _run_check(deliver, argv, result=result)
    if "verdict" not in result:
        # Usage errors and missing dependencies stop before a verdict.
        raise ValueError(report or "deliver stopped before a verdict")
    return {**result, "exit_code": code, "report": report}


def tool_screenshot(args: dict) -> dict:
    pdf = _resolve(args["pdf"])
    if not pdf.exists():
        raise FileNotFoundError(f"PDF not found: {pdf}")
    dpi = args.get("dpi")
    if dpi is not None and (isinstance(dpi, bool) or not isinstance(dpi, int)):
        raise ValueError("dpi must be an integer")
    pages = render_pages(pdf, dpi=dpi)
    font_code, font_report = _run_check(check_fonts, [str(pdf)])
    return {
        "rasterized": True,
        "review_pending": True,
        "pages": [str(p) for p in pages],
        "font_check": {
            "exit_code": font_code,
            "ok": font_code == 0,
            "report": font_report,
        },
        "review_checklist": list(REVIEW_CHECKLIST),
        "instruction": (
            "Require font_check.ok, then view every page image against the "
            "checklist. Settle the perceptual review outside this tool before shipping."
        ),
    }


TOOL_HANDLERS = {
    "kami_templates": tool_templates,
    "kami_doctor": tool_doctor,
    "kami_render": tool_render,
    "kami_check": tool_check,
    "kami_deliver": tool_deliver,
    "kami_screenshot": tool_screenshot,
}


def _send(payload: dict) -> None:
    sys.stdout.write(json.dumps(payload, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def _reply(msg_id, result: dict) -> None:
    _send({"jsonrpc": "2.0", "id": msg_id, "result": result})


def _reply_error(msg_id, code: int, message: str) -> None:
    _send({"jsonrpc": "2.0", "id": msg_id, "error": {"code": code, "message": message}})


def _tool_result(msg_id, payload: dict, *, is_error: bool = False) -> None:
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    _reply(msg_id, {"content": [{"type": "text", "text": text}], "isError": is_error})


def handle(msg: dict) -> None:
    method = msg.get("method")
    has_id = "id" in msg
    msg_id = msg.get("id")
    if msg.get("jsonrpc") != "2.0" or not isinstance(method, str):
        if has_id:
            _reply_error(msg_id, -32600, "invalid request")
        return
    raw_params = msg.get("params")
    if raw_params is None:
        params = {}
    elif isinstance(raw_params, dict):
        params = raw_params
    else:
        if has_id:
            _reply_error(msg_id, -32602, "params must be an object")
        return

    if method == "initialize":
        if not has_id:
            return
        client_version = params.get("protocolVersion")
        agreed = client_version if client_version in SUPPORTED_PROTOCOL_VERSIONS else PROTOCOL_VERSION
        _reply(msg_id, {
            "protocolVersion": agreed,
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "kami", "version": kami_version()},
        })
        return
    if not has_id:
        return  # notifications (initialized, cancelled, ...) need no reply
    if method == "ping":
        _reply(msg_id, {})
        return
    if method == "tools/list":
        _reply(msg_id, {"tools": TOOLS})
        return
    if method == "tools/call":
        name = params.get("name")
        arguments = params.get("arguments")
        if not isinstance(name, str) or (arguments is not None and not isinstance(arguments, dict)):
            _reply_error(msg_id, -32602, "tool name must be a string and arguments must be an object")
            return
        handler = TOOL_HANDLERS.get(name)
        if handler is None:
            _reply_error(msg_id, -32602, f"unknown tool: {name}")
            return
        try:
            # Capture stray prints so nothing corrupts the protocol stream.
            with contextlib.redirect_stdout(io.StringIO()):
                result = handler(arguments or {})
            _tool_result(msg_id, result)
        except MissingDepError as exc:
            _tool_result(msg_id, {"error": str(exc)}, is_error=True)
        except Exception as exc:
            _tool_result(msg_id, {"error": f"{type(exc).__name__}: {exc}"}, is_error=True)
        return
    _reply_error(msg_id, -32601, f"method not found: {method}")


def main() -> int:
    # MCP stdio frames are UTF-8 regardless of the host locale (a Windows pipe
    # defaults to the ANSI code page and cannot encode CJK results).
    sys.stdin.reconfigure(encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8", newline="\n")
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            _reply_error(None, -32700, "parse error")
            continue
        if not isinstance(msg, dict):
            _reply_error(None, -32600, "invalid request")
            continue
        try:
            handle(msg)
        except Exception:
            # A malformed request must never terminate the stdio server or
            # prevent the client from sending the next frame.
            _reply_error(msg.get("id"), -32603, "internal error")
    return 0


if __name__ == "__main__":
    sys.exit(main())
