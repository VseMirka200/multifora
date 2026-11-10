"""Совместимость PDF-библиотек, используемых сторонними пакетами."""

from __future__ import annotations

import sys


def import_pymupdf_with_legacy_alias():
    """Импортирует PyMuPDF и регистрирует прежнее имя модуля ``fitz``.

    pdf2docx 0.5.x использует имя ``fitz``. Устаревший модуль совместимости
    PyMuPDF выводит предупреждение, что опасно для оконного приложения без
    консоли. Регистрация уже загруженного пакета сохраняет тот же API.
    """
    import pymupdf

    sys.modules.setdefault("fitz", pymupdf)
    return pymupdf
