"""Чтение текста UTF и экспорт в редактируемые форматы документов."""

import re
from codecs import BOM_UTF16_BE, BOM_UTF16_LE, BOM_UTF32_BE, BOM_UTF32_LE
from html import escape
from pathlib import Path
from xml.etree.ElementTree import Element, SubElement, tostring
from zipfile import ZIP_DEFLATED, ZipFile

from docx import Document

from core.filesystem import atomic_output_path

_ODT_MIME = "application/vnd.oasis.opendocument.text"
_OFFICE = "urn:oasis:names:tc:opendocument:xmlns:office:1.0"
_TEXT = "urn:oasis:names:tc:opendocument:xmlns:text:1.0"
_MANIFEST = "urn:oasis:names:tc:opendocument:xmlns:manifest:1.0"


def _check_cancel(should_cancel):
    if should_cancel():
        raise InterruptedError("Конвертация отменена")


def _lines(text, should_cancel):
    for line in text.split("\n"):
        _check_cancel(should_cancel)
        yield line


def _save_docx(path, text, should_cancel):
    document = Document()
    for line in _lines(text, should_cancel):
        document.add_paragraph(line)
    document.save(path)


def _save_html(path, text, should_cancel):
    paragraphs = "".join(f"<p>{escape(line)}</p>\n" for line in _lines(text, should_cancel))
    path.write_text(
        '<!doctype html><html><head><meta charset="utf-8"></head>'
        '<body style="white-space: pre-wrap">\n' + paragraphs + "</body></html>\n",
        encoding="utf-8",
    )


def _rtf_escape(line):
    encoded = line.encode("utf-16-le")
    for offset in range(0, len(encoded), 2):
        value = int.from_bytes(encoded[offset:offset + 2], "little", signed=True)
        if value == 9:
            yield "\\tab "
        elif 32 <= value < 127:
            char = chr(value)
            yield "\\" + char if char in "\\{}" else char
        else:
            yield f"\\u{value}?"


def _save_rtf(path, text, should_cancel):
    paragraphs = ("".join(_rtf_escape(line)) for line in _lines(text, should_cancel))
    path.write_text(r"{\rtf1\ansi\uc1 " + "\\par\n".join(paragraphs) + "}", encoding="ascii")


def _save_odt(path, text, should_cancel):
    content = Element(f"{{{_OFFICE}}}document-content", {f"{{{_OFFICE}}}version": "1.2"})
    body = SubElement(content, f"{{{_OFFICE}}}body")
    document = SubElement(body, f"{{{_OFFICE}}}text")
    for line in _lines(text, should_cancel):
        paragraph = SubElement(document, f"{{{_TEXT}}}p")
        for char in line:
            if char in " \t":
                leaf = SubElement(paragraph, f"{{{_TEXT}}}" + ("s" if char == " " else "tab"))
            elif len(paragraph):
                leaf.tail = (leaf.tail or "") + char
            else:
                paragraph.text = (paragraph.text or "") + char
    manifest = Element(f"{{{_MANIFEST}}}manifest", {f"{{{_MANIFEST}}}version": "1.2"})
    for name, media_type in (("/", _ODT_MIME), ("content.xml", "text/xml")):
        SubElement(manifest, f"{{{_MANIFEST}}}file-entry", {
            f"{{{_MANIFEST}}}full-path": name, f"{{{_MANIFEST}}}media-type": media_type,
        })
    with ZipFile(path, "w") as archive:
        archive.writestr("mimetype", _ODT_MIME)
        archive.writestr("content.xml", tostring(content, encoding="utf-8", xml_declaration=True), ZIP_DEFLATED)
        archive.writestr("META-INF/manifest.xml", tostring(manifest, encoding="utf-8"), ZIP_DEFLATED)


EDITABLE_EXPORTS = {"DOCX": _save_docx, "HTML": _save_html, "ODT": _save_odt, "RTF": _save_rtf}


def read_text(source):
    data = Path(source).read_bytes()
    if data.startswith((BOM_UTF32_LE, BOM_UTF32_BE)):
        text = data.decode("utf-32")
    elif data.startswith((BOM_UTF16_LE, BOM_UTF16_BE)):
        text = data.decode("utf-16")
    else:
        try:
            text = data.decode("utf-8-sig")
        except UnicodeDecodeError:
            from charset_normalizer import from_bytes

            cp1251 = data.decode("cp1251", errors="replace")
            if re.search(r"[А-Яа-яЁё]{3,}", cp1251) and "\ufffd" not in cp1251:
                text = cp1251
            else:
                choices = from_bytes(data, cp_isolation=["cp1252", "cp1251"])
                choice = choices["cp1252"] if "cp1252" in choices else choices.best()
                if choice is None:
                    raise
                text = str(choice)
    return text.replace("\r\n", "\n").replace("\r", "\n")


def convert_text(source, destination, target, should_cancel):
    _check_cancel(should_cancel)
    text = read_text(source)
    with atomic_output_path(destination) as temporary:
        EDITABLE_EXPORTS[target](Path(temporary), text, should_cancel)
        _check_cancel(should_cancel)
