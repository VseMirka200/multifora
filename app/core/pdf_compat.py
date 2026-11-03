"""Compatibility helpers for PDF backends used by third-party packages."""

from __future__ import annotations

import sys


def import_pymupdf_with_legacy_alias():
    """Import PyMuPDF and expose its supported legacy ``fitz`` module name.

    pdf2docx 0.5.x still imports ``fitz``.  Importing PyMuPDF's deprecated
    shim prints a warning, which is unsafe in a windowed frozen process with
    no console.  Registering the already imported package under the legacy
    name provides the same API without executing that shim.
    """
    import pymupdf

    sys.modules.setdefault("fitz", pymupdf)
    return pymupdf
