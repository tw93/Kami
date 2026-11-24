"""Artifact production primitives shared by build, verify, and the MCP server.

One home for the render pipeline (read HTML, strictly render LaTeX to SVG, highlight code blocks, WeasyPrint
to PDF, stamp Kami metadata, count pages) and the PPTX fallback build. Before
this module existed the pipeline lived in build.py and was duplicated by
verify.py (through injected callbacks, to dodge a circular import) and the MCP
server (through a late import). Keeping it here, below build.py in the import
graph, dissolves both workarounds.
"""
from __future__ import annotations

import functools
import os
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

from font_compat import use_truetype_fonts
from hangul import join_hangul_words
from hans import use_source_han_fonts
from hant import use_traditional_fonts
from highlight import highlight_code_blocks
from math_render import MathRenderError, render_latex_in_html
from optional_deps import (
    MissingDepError,
    require_pypdf_reader,
    require_pypdf_writer,
    require_weasyprint_html,
)
from shared import EXAMPLES, TEMPLATES, pptx_targets


@functools.lru_cache(maxsize=1)
def infer_author() -> str:
    """Infer author name from git config or environment.

    Priority:
    1. git config user.name
    2. KAMI_AUTHOR env var
    3. fallback to "Kami"

    Cached so a full build doesn't shell out for every PDF target.
    """
    try:
        result = subprocess.run(
            ["git", "config", "user.name"],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except FileNotFoundError:
        pass

    if env_author := os.environ.get("KAMI_AUTHOR"):
        return env_author

    return "Kami"


def set_pdf_metadata(pdf_path: Path, author: str | None = None) -> None:
    """Set PDF metadata using pypdf, only if placeholders are still present."""
    try:
        PdfReader = require_pypdf_reader()
        PdfWriter = require_pypdf_writer()
    except MissingDepError:
        return

    if not pdf_path.exists():
        return

    reader = PdfReader(str(pdf_path))

    existing = reader.metadata or {}
    needs_update = False
    metadata = dict(existing)

    if author and existing.get("/Author"):
        author_value = str(existing["/Author"])
        if "{{" in author_value and "}}" in author_value:
            metadata["/Author"] = author
            needs_update = True

    if metadata.get("/Producer") != "Kami":
        metadata["/Producer"] = "Kami"
        needs_update = True
    if metadata.get("/Creator") != "Kami":
        metadata["/Creator"] = "Kami"
        needs_update = True

    if not needs_update:
        return

    # Clone the whole document catalog, not only its pages. WeasyPrint writes
    # useful document-level structures such as outlines, named destinations,
    # and /Lang; rebuilding from add_page() silently discards those while the
    # page count and pixels still look correct.
    writer = PdfWriter()
    writer.clone_document_from_reader(reader)
    writer.add_metadata(metadata)

    with open(pdf_path, "wb") as f:
        writer.write(f)


def render_pdf(src: Path, out: Path) -> int:
    """Render an HTML file to PDF and return its page count.

    The full pipeline every caller must agree on: strict TeX-to-SVG math rendering,
    build-time code highlighting, Korean word joining, Traditional Chinese
    Ming faces for zh-Hant documents, TrueType copies of
    CID-keyed CFF fonts, WeasyPrint with base_url at the source directory, Kami PDF metadata, page
    count via pypdf. Raises MissingDepError when weasyprint/pypdf are absent
    and MathRenderError when formula source or the locked renderer is invalid;
    callers decide how to report either failure.
    """
    HTML = require_weasyprint_html()
    PdfReader = require_pypdf_reader()

    out.parent.mkdir(parents=True, exist_ok=True)
    html_text = src.read_text(encoding="utf-8")
    html_text = render_latex_in_html(html_text)
    html_text = highlight_code_blocks(html_text)
    html_text = join_hangul_words(html_text)
    html_text = use_traditional_fonts(html_text)
    html_text = use_source_han_fonts(html_text)
    html_text = use_truetype_fonts(html_text, src.parent)
    # Build and validate beside the destination, then atomically replace it.
    # Metadata stamping and the final page read can still fail after WeasyPrint
    # succeeds; writing straight to `out` would destroy the last good artifact
    # before the caller learns that the render failed.
    with tempfile.TemporaryDirectory(
        dir=out.parent,
        prefix=f".{out.name}-",
    ) as staging_dir:
        candidate = Path(staging_dir) / out.name
        HTML(string=html_text, base_url=str(src.parent)).write_pdf(str(candidate))
        set_pdf_metadata(candidate, author=infer_author())
        page_count = len(PdfReader(str(candidate)).pages)
        os.replace(candidate, out)
    return page_count


_PPTX_REQUIRED_ENTRIES = {
    "[Content_Types].xml",
    "_rels/.rels",
    "ppt/presentation.xml",
}


def _pptx_issue(path: Path) -> str | None:
    """Return why ``path`` is not a readable PPTX package, else ``None``."""
    if not path.is_file():
        return "output not produced"
    try:
        with zipfile.ZipFile(path) as archive:
            bad_entry = archive.testzip()
            if bad_entry is not None:
                return f"corrupt ZIP entry: {bad_entry}"
            missing = sorted(_PPTX_REQUIRED_ENTRIES - set(archive.namelist()))
    except (OSError, zipfile.BadZipFile) as exc:
        return f"invalid PPTX package: {exc}"
    if missing:
        return f"missing PPTX package entry: {', '.join(missing)}"
    return None


def build_slides(name: str = "slides") -> bool:
    """Run a python-pptx slide script from the shared registry; True on success."""
    source = pptx_targets().get(name)
    if source is None:
        print(f"ERROR: {name}: unknown slides target")
        return False
    src = TEMPLATES / source
    if not src.exists():
        print(f"ERROR: {name}: source not found ({src})")
        return False

    EXAMPLES.mkdir(parents=True, exist_ok=True)
    out = EXAMPLES / f"{name}.pptx"
    # Build beside the destination and replace only after the new file proves
    # to be a readable PPTX package. A successful script that forgets to write
    # must not let an older output masquerade as this run's artifact.
    with tempfile.TemporaryDirectory(
        dir=out.parent,
        prefix=f".{out.name}-",
    ) as staging_dir:
        candidate = Path(staging_dir) / out.name
        result = subprocess.run(
            [sys.executable, str(src), "--out", str(candidate)],
            cwd=str(src.parent),
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            print(f"ERROR: {name}: {result.stderr.strip() or 'script failed'}")
            return False
        issue = _pptx_issue(candidate)
        if issue:
            print(f"ERROR: {name}: {issue}")
            return False
        os.replace(candidate, out)
    print(f"OK: {name}: generated {out.name}")
    return True
