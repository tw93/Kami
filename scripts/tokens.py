"""Token-sync checker for kami templates.

Splits out from build.py: scans `:root { ... }` blocks across HTML templates
and `RGBColor(0xXX, 0xXX, 0xXX)` constants in the PPTX slide scripts, and
reports drift from `references/tokens.json` (the canonical color tokens).
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from shared import DIAGRAMS, ROOT, TEMPLATES, TOKENS_FILE

ROOT_BLOCK = re.compile(r":root\s*\{([^}]*)\}", re.DOTALL)
CSS_VAR = re.compile(r"--([\w-]+)\s*:\s*([^;]+);")
PY_RGB = re.compile(
    r"^([A-Z][A-Z_]+)\s*=\s*RGBColor\(\s*0x([0-9a-fA-F]{2})\s*,"
    r"\s*0x([0-9a-fA-F]{2})\s*,\s*0x([0-9a-fA-F]{2})\s*\)",
    re.MULTILINE,
)
# Python const name -> tokens.json key. Only constants that mirror a CSS token.
PY_TOKEN_MAP = {
    "PARCHMENT": "--parchment",
    "IVORY": "--ivory",
    "BRAND": "--brand",
    "NEAR_BLACK": "--near-black",
    "DARK_WARM": "--dark-warm",
    "CHARCOAL": "--charcoal",
    "OLIVE": "--olive",
    "STONE": "--stone",
}


def sync_check(verbose: bool = False) -> int:
    if not TOKENS_FILE.exists():
        print(f"ERROR: tokens.json not found at {TOKENS_FILE.relative_to(ROOT)}")
        return 1

    try:
        canonical: dict[str, str] = json.loads(TOKENS_FILE.read_text())
    except json.JSONDecodeError as exc:
        print(f"ERROR: tokens.json is malformed: {exc}")
        return 1

    targets: list[Path] = list(TEMPLATES.glob("*.html"))
    if DIAGRAMS.exists():
        targets.extend(DIAGRAMS.glob("*.html"))
    py_targets: list[Path] = list(TEMPLATES.glob("*.py"))

    drift: list[tuple[str, str, str, str]] = []  # (file, token, expected, actual)

    for path in sorted(targets):
        text = path.read_text(encoding="utf-8", errors="replace")
        block_match = ROOT_BLOCK.search(text)
        if not block_match:
            if verbose:
                print(f"  (skip {path.name}: no :root block)")
            continue
        root_block = block_match.group(1)
        found: dict[str, str] = {
            m.group(1): m.group(2).strip()
            for m in CSS_VAR.finditer(root_block)
        }
        rel = path.relative_to(ROOT)
        for token, expected in canonical.items():
            name = token.lstrip("-")
            actual = found.get(name)
            # Only flag if the template defines the token but with a wrong value.
            # Templates that don't use a token don't need to define it.
            if actual is not None and actual.lower() != expected.lower():
                drift.append((str(rel), token, expected, actual))

    for path in sorted(py_targets):
        text = path.read_text(encoding="utf-8", errors="replace")
        rel = path.relative_to(ROOT)
        for m in PY_RGB.finditer(text):
            name = m.group(1)
            token = PY_TOKEN_MAP.get(name)
            if token is None:
                continue
            expected = canonical.get(token)
            if expected is None:
                continue
            actual = f"#{m.group(2)}{m.group(3)}{m.group(4)}"
            if actual.lower() != expected.lower():
                drift.append((str(rel), token, expected, actual))

    if not drift:
        scanned = len(targets) + len(py_targets)
        print(f"OK: tokens in sync across {scanned} template(s)")
        return 0

    print(f"\n[token-drift] {len(drift)}")
    for file, token, expected, actual in drift:
        print(f"  {file}: {token} expected {expected}, got {actual}")

    return 1
