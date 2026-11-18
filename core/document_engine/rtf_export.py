"""Write RTF from the shared representation of formatted documents."""

import base64
import re
from io import BytesIO
from pathlib import Path
from urllib.parse import unquote, urlsplit

from lxml import html
from PIL import Image

from core.document_engine.plain_text import _rtf_escape
from core.workers.atomic_output import atomic_output_path

_INLINE = {"strong": r"\b ", "b": r"\b ", "em": r"\i ", "i": r"\i ", "u": r"\ul "}
_BLOCK = {"p", "pre", "div", "li", "blockquote", *(f"h{i}" for i in range(1, 7))}
_SKIP = {"head", "script", "style", "template"}
_DATA_IMAGE = re.compile(r"data:image/(?:png|jpeg|gif|bmp|tiff|webp);base64,(.*)", re.I | re.S)


def _text(text, preformatted=False):
    if not text:
        return ""
    if not preformatted:
        text = re.sub(r"\s+", " ", text)
    return r"\line ".join("".join(_rtf_escape(line)) for line in text.split("\n"))


def image_data(node, root):
    source = node.get("src", "")
    if match := _DATA_IMAGE.fullmatch(source):
        data = BytesIO(base64.b64decode("".join(match[1].split()), validate=True))
    else:
        parsed = urlsplit(source)
        if parsed.scheme or parsed.netloc:
            return None
        path = (root / unquote(parsed.path)).resolve()
        if not path.is_relative_to(root) or not path.is_file():
            return None
        data = path
    return data


def _picture(node, root):
    data = image_data(node, root)
    if data is None:
        return _text(node.get("alt"))
    with Image.open(data) as picture, BytesIO() as png:
        picture.convert("RGBA").save(png, "PNG")
        width = min(picture.width * 15, 8640)
        height = round(width * picture.height / picture.width)
        return (
            rf"{{\pict\pngblip\picw{picture.width}\pich{picture.height}"
            rf"\picwgoal{width}\pichgoal{height} " + png.getvalue().hex() + "}"
        )


def _table(node, root, should_cancel):
    for row in node.xpath("./tr|./thead/tr|./tbody/tr|./tfoot/tr"):
        cells = row.xpath("./td|./th")
        if not cells:
            continue
        yield r"\trowd "
        for index in range(1, len(cells) + 1):
            yield rf"\cellx{index * 8640 // len(cells)} "
        for cell in cells:
            yield r"\pard\intbl "
            yield from _translate(cell, root, should_cancel, table_cell=True)
            yield r"\cell "
        yield "\\row\\pard\n"


def _translate(node, root, should_cancel, *, table_cell=False, preformatted=False):
    if should_cancel():
        raise InterruptedError("Конвертация отменена")
    tag = node.tag
    if not isinstance(tag, str) or tag in _SKIP:
        return
    if tag == "img":
        yield _picture(node, root)
        return
    if tag == "br":
        yield r"\line "
        return
    if tag == "table":
        yield from _table(node, root, should_cancel)
        return
    if tag in _INLINE:
        yield "{" + _INLINE[tag]
    preformatted = preformatted or tag == "pre" or "white-space: pre-wrap" in node.get("style", "")
    yield _text(node.text, preformatted)
    for child in node:
        yield from _translate(child, root, should_cancel, table_cell=table_cell, preformatted=preformatted)
        yield _text(child.tail, preformatted)
    if tag in _INLINE:
        yield "}"
    if tag in _BLOCK:
        yield r"\line " if table_cell else "\\par\n"


def export_rtf(source, destination, source_format, should_cancel):
    if source_format == "DOCX":
        from core.document_engine.docx_html import body_html

        body = html.fragment_fromstring(body_html(source, should_cancel), create_parent="body")
    elif source_format == "ODT":
        from core.document_engine.odt_html import read_body

        body = read_body(source, should_cancel)
    else:
        from core.document_engine.html_docx import read_body

        body = read_body(source, should_cancel)
    root = Path(source).parent.resolve()
    with atomic_output_path(destination) as temporary, Path(temporary).open("w", encoding="ascii") as stream:
        stream.write(r"{\rtf1\ansi\ansicpg1252\uc1 ")
        stream.writelines(_translate(body, root, should_cancel))
        stream.write("}")
        if should_cancel():
            raise InterruptedError("Конвертация отменена")
