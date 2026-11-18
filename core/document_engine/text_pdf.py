"""Render plain UTF text into a searchable PDF."""

import os
from pathlib import Path
from threading import Lock
from unicodedata import bidirectional, combining

from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas

from core.document_engine.plain_text import read_text
from core.workers.atomic_output import atomic_output_path

_FONT_NAME = "MultiforaText"
_FONT_LOCK = Lock()
_FONT_SIZE = 11
_LEADING = 15
_MARGIN = 54
_FONTS = Path(os.environ.get("WINDIR", r"C:\Windows"), "Fonts")


def _text_font(text):
    if any(bidirectional(char) in {"R", "AL", "AN"} or combining(char) for char in text):
        return None
    with _FONT_LOCK:
        if _FONT_NAME not in pdfmetrics.getRegisteredFontNames():
            path = _FONTS / "consola.ttf"
            if not path.is_file():
                return None
            pdfmetrics.registerFont(TTFont(_FONT_NAME, path))
        font = pdfmetrics.getFont(_FONT_NAME)
        return font if all(char in "\r\n\t\f" or ord(char) in font.face.charWidths for char in text) else None


def register_font_family():
    with _FONT_LOCK:
        registered = pdfmetrics.getRegisteredFontNames()
        family = {}
        for style, filename in (("bold", "consolab.ttf"), ("italic", "consolai.ttf"), ("boldItalic", "consolaz.ttf")):
            path = _FONTS / filename
            name = _FONT_NAME + style
            if path.is_file():
                if name not in registered:
                    pdfmetrics.registerFont(TTFont(name, path))
                family[style] = name
            else:
                family[style] = _FONT_NAME
        pdfmetrics.registerFontFamily(_FONT_NAME, normal=_FONT_NAME, **family)


def export_pdf(source, destination, should_cancel):
    if should_cancel():
        raise InterruptedError("Конвертация отменена")
    text = read_text(source)
    font = _text_font(text)
    if font is None:
        from lxml import etree

        from core.document_engine.qt_pdf import write_pdf

        body = etree.Element("body")
        etree.SubElement(body, "pre").text = text
        return write_pdf(body, source, destination, should_cancel)
    width, height = A4
    columns = int((width - 2 * _MARGIN) / font.stringWidth("0", _FONT_SIZE))
    with atomic_output_path(destination) as temporary:
        pdf = Canvas(temporary, pagesize=A4, pageCompression=1)
        pdf.setFont(_FONT_NAME, _FONT_SIZE)
        for section_index, section in enumerate(text.split("\f")):
            if section_index:
                pdf.showPage()
                pdf.setFont(_FONT_NAME, _FONT_SIZE)
            y = height - _MARGIN
            for line in section.split("\n"):
                line = line.expandtabs(4)
                for offset in range(0, max(len(line), 1), columns):
                    if should_cancel():
                        raise InterruptedError("Конвертация отменена")
                    if y < _MARGIN:
                        pdf.showPage()
                        pdf.setFont(_FONT_NAME, _FONT_SIZE)
                        y = height - _MARGIN
                    pdf.drawString(_MARGIN, y, line[offset:offset + columns])
                    y -= _LEADING
        pdf.save()
        if should_cancel():
            raise InterruptedError("Конвертация отменена")
