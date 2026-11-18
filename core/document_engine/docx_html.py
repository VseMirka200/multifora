"""Export the body of a DOCX as standalone HTML."""

from base64 import b64encode
from html import escape
from pathlib import Path
from urllib.parse import urlsplit

from docx import Document
from docx.oxml.ns import qn
from docx.table import Table
from docx.text.hyperlink import Hyperlink

from core.workers.atomic_output import atomic_output_path

_IMAGE_TYPES = {"image/png", "image/jpeg", "image/gif", "image/webp", "image/bmp"}


def _check_cancel(should_cancel):
    if should_cancel():
        raise InterruptedError("Конвертация отменена")


def _inline_picture(element, part):
    relationship = element.get(qn("r:embed"))
    if relationship is None:
        return ""
    image = part.related_parts.get(relationship)
    if image is None or image.content_type not in _IMAGE_TYPES:
        return ""
    encoded = b64encode(image.blob).decode("ascii")
    return f'<img src="data:{image.content_type};base64,{encoded}" alt="">'


def _run_html(run):
    fragments = []
    for child in run._element:
        if child.tag == qn("w:t"):
            fragments.append(escape(child.text or ""))
        elif child.tag in {qn("w:br"), qn("w:cr")}:
            fragments.append('<br data-page-break="true">' if child.get(qn("w:type")) == "page" else "<br>")
        elif child.tag == qn("w:tab"):
            fragments.append("\t")
        elif child.tag == qn("w:drawing"):
            fragments.extend(_inline_picture(blip, run.part) for blip in child.iter(qn("a:blip")))
    text = "".join(fragments)
    for flag, tag in ((run.bold, "strong"), (run.italic, "em"), (run.underline, "u")):
        if flag:
            text = f"<{tag}>{text}</{tag}>"
    return text


def _paragraph_html(paragraph):
    style = paragraph.style.name if paragraph.style is not None else ""
    levels = {f"Heading {level}": f"h{level}" for level in range(1, 7)}
    tag = levels.get(style, "h1" if style == "Title" else "p")
    inline = []
    for item in paragraph.iter_inner_content():
        if isinstance(item, Hyperlink):
            text = "".join(_run_html(run) for run in item.runs)
            url = item.url
            if url and (url.startswith("#") or urlsplit(url).scheme in {"https", "http", "mailto"}):
                text = f'<a href="{escape(url, quote=True)}">{text}</a>'
            inline.append(text)
        else:
            inline.append(_run_html(item))
    return f"<{tag}>{''.join(inline)}</{tag}>"


def _body_html(container, should_cancel):
    parts = []
    for block in container.iter_inner_content():
        _check_cancel(should_cancel)
        if isinstance(block, Table):
            parts.append("<table>")
            for row in block.rows:
                _check_cancel(should_cancel)
                parts.append("<tr>")
                for cell in row.cells:
                    parts.extend(("<td>", _body_html(cell, should_cancel), "</td>"))
                parts.append("</tr>")
            parts.append("</table>")
        else:
            parts.append(_paragraph_html(block))
    return "".join(parts)


def body_html(source, should_cancel):
    _check_cancel(should_cancel)
    document = Document(source)
    return _body_html(document, should_cancel)


def export_html(source, destination, should_cancel):
    body = body_html(source, should_cancel)
    html = (
        '<!doctype html><html><head><meta charset="utf-8">'
        '<style>p,h1,h2,h3,h4,h5,h6{white-space:pre-wrap}td{vertical-align:top}</style>'
        f'</head><body>\n{body}\n</body></html>\n'
    )
    with atomic_output_path(destination) as temporary:
        Path(temporary).write_text(html, encoding="utf-8", newline="\n")
        _check_cancel(should_cancel)
