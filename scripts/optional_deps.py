"""Centralized loader for optional third-party deps (weasyprint, pypdf, PyMuPDF).

build.py and stabilize.py previously each had inline `from weasyprint import HTML`
try/except blocks with duplicated install hints; this module collapses those into
one resolver each so the import error message stays consistent and the
WeasyPrint runtime is configured once at the import call site.
"""
from __future__ import annotations

from shared import configure_weasyprint_runtime

WEASYPRINT_INSTALL_HINT = "pip install weasyprint pypdf --break-system-packages"
PYMUPDF_INSTALL_HINT = "pip install pymupdf --break-system-packages"


class MissingDepError(RuntimeError):
    """Raised when an optional dependency is requested but not installed."""


def require_weasyprint_html():
    """Return the weasyprint.HTML class, configuring native libs first."""
    configure_weasyprint_runtime()
    try:
        from weasyprint import HTML
        return HTML
    except ImportError as exc:
        raise MissingDepError(
            f"missing weasyprint. {WEASYPRINT_INSTALL_HINT}"
        ) from exc


def require_pypdf_reader():
    """Return the pypdf.PdfReader class."""
    try:
        from pypdf import PdfReader
        return PdfReader
    except ImportError as exc:
        raise MissingDepError(
            f"missing pypdf. {WEASYPRINT_INSTALL_HINT}"
        ) from exc


def require_pypdf_writer():
    """Return the pypdf.PdfWriter class."""
    try:
        from pypdf import PdfWriter
        return PdfWriter
    except ImportError as exc:
        raise MissingDepError(
            f"missing pypdf. {WEASYPRINT_INSTALL_HINT}"
        ) from exc


def require_pymupdf():
    """Return the PyMuPDF module (imported as fitz)."""
    try:
        import fitz
        return fitz
    except ImportError as exc:
        raise MissingDepError(
            f"missing PyMuPDF. {PYMUPDF_INSTALL_HINT}"
        ) from exc
