"""Импорт локальных HTML-документов в редактируемый DOCX."""

import re
from io import BytesIO
from pathlib import Path
from urllib.parse import urlsplit

from docx import Document
from docx.enum.section import WD_ORIENT
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_ROW_HEIGHT_RULE
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.opc.constants import RELATIONSHIP_TYPE
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt, RGBColor
from lxml import html
from PIL import Image

from core.document_engine.formatting import font_family, image_size, inline_style, points
from core.document_engine.rtf_export import image_data
from core.document_engine.table_layout import table_layout
from core.filesystem import atomic_output_path

_BLOCKS = {"div", "section", "article", "main", "header", "footer", "blockquote"}
_HEADINGS = {f"h{level}": f"Heading {level}" for level in range(1, 7)}
_SKIP = {"head", "style", "script", "template"}
_FORMATS = {"strong": "bold", "b": "bold", "em": "italic", "i": "italic", "u": "underline"}
_PARAGRAPHS = {*_HEADINGS, "p", "pre", "li"}
_PARAGRAPH_ALIGNMENT = {name: getattr(WD_ALIGN_PARAGRAPH, name.upper())
                        for name in ("left", "center", "right", "justify")}


def _append_text(paragraph, text, styles, preformatted):
    if not text:
        return
    if not preformatted:
        text = re.sub(r"[ \t\r\n\f]+", " ", text)
        if not paragraph.text:
            text = text.lstrip()
    if text:
        run = paragraph.add_run(text)
        for style, value in styles.items():
            if style == "color":
                run.font.color.rgb = RGBColor.from_string(value)
            elif style == "background":
                _word_property(run._r.get_or_add_rPr(), "shd", val="clear", fill=value)
            else:
                setattr(run.font, style, value)


def _word_property(parent, name, **attributes):
    tag = qn(f"w:{name}")
    element = parent.find(tag)
    if element is None:
        element = OxmlElement(f"w:{name}")
        parent.append(element)
    for key, value in attributes.items():
        element.set(qn(f"w:{key}"), str(value))
    return element


def _add_image(paragraph, node, root, width, height):
    data = image_data(node, root)
    if data is None:
        return
    with Image.open(data) as picture:
        dimensions = image_size(
            node, picture.width, picture.height, width_limit=width / 12700, height_limit=height / 12700,
        )
        if picture.format not in {"PNG", "JPEG", "GIF", "BMP", "TIFF"}:
            data = BytesIO()
            picture.convert("RGBA").save(data, format="PNG")
    paragraph.add_run().add_picture(str(data) if isinstance(data, Path) else data, *map(Pt, dimensions))


def _font_styles(node, styles, css):
    styles = styles.copy()
    if node.tag in _FORMATS:
        styles[_FORMATS[node.tag]] = True
    if family := font_family(css.get("font-family")):
        styles["name"] = family
    if size := points(css.get("font-size")):
        styles["size"] = Pt(size)
    if "font-weight" in css:
        styles["bold"] = css["font-weight"] in {"bold", "600", "700", "800", "900"}
    if "font-style" in css:
        styles["italic"] = css["font-style"] in {"italic", "oblique"}
    if "text-decoration" in css:
        styles["underline"] = "underline" in css["text-decoration"].split()
    for key, name in (("color", "color"), ("background-color", "background")):
        if name == "background" and node.tag in _PARAGRAPHS:
            continue
        if re.fullmatch(r"#[0-9a-fA-F]{6}", value := css.get(key, "")):
            styles[name] = value[1:].upper()
    return styles


def _inline(node, paragraph, root, bounds, styles, preformatted, should_cancel):
    if should_cancel():
        raise InterruptedError("Конвертация отменена")
    tag = node.tag
    if not isinstance(tag, str) or tag in _SKIP:
        return
    if tag == "img":
        _add_image(paragraph, node, root, *bounds)
        return
    if tag == "br":
        paragraph.add_run().add_break(WD_BREAK.PAGE if node.get("data-page-break") == "true" else WD_BREAK.LINE)
        return
    css = inline_style(node)
    styles = _font_styles(node, styles, css)
    preformatted = preformatted or tag == "pre" or css.get("white-space") == "pre-wrap"
    start = len(paragraph._p)
    _append_text(paragraph, node.text, styles, preformatted)
    for child in node:
        _inline(child, paragraph, root, bounds, styles, preformatted, should_cancel)
        _append_text(paragraph, child.tail, styles, preformatted)
    if tag == "a" and (href := node.get("href", "")):
        link = OxmlElement("w:hyperlink")
        if href.startswith("#"):
            link.set(qn("w:anchor"), href[1:])
        elif urlsplit(href).scheme in {"http", "https", "mailto"}:
            link.set(qn("r:id"), paragraph.part.relate_to(href, RELATIONSHIP_TYPE.HYPERLINK, is_external=True))
        else:
            return
        for run in list(paragraph._p)[start:]:
            link.append(run)
        paragraph._p.append(link)


def _paragraph_format(paragraph, css):
    fmt = paragraph.paragraph_format
    if (alignment := _PARAGRAPH_ALIGNMENT.get(css.get("text-align"))) is not None:
        fmt.alignment = alignment
    for attribute, name in (
        ("left_indent", "margin-left"), ("right_indent", "margin-right"), ("first_line_indent", "text-indent"),
        ("space_before", "margin-top"), ("space_after", "margin-bottom"),
    ):
        if re.fullmatch(r"-?(?:\d+(?:\.\d+)?|\.\d+)(?:pt|px|in|cm|mm|pc)?", value := css.get(name, "")):
            length = points(value.removeprefix("-")) or 0
            setattr(fmt, attribute, Pt(-length if value.startswith("-") and "indent" in attribute else length))
    spacing = css.get("line-height", "")
    if spacing.endswith("%") and (value := points(spacing[:-1] + "pt")):
        fmt.line_spacing = value / 100
    elif value := points(spacing):
        fmt.line_spacing = Pt(value)
    if css.get("page-break-before") == "always":
        fmt.page_break_before = True
    if css.get("--docx-keep-with-next"):
        fmt.keep_with_next = True
    if re.fullmatch(r"#[0-9a-fA-F]{6}", value := css.get("background-color", "")):
        properties = paragraph._p.get_or_add_pPr()
        shading = _word_property(properties, "shd", val="clear", fill=value[1:])
        properties.insert_element_before(shading, "w:tabs", "w:spacing", "w:ind", "w:jc", "w:rPr")
    size = points(css.get("font-size"))
    family = font_family(css.get("font-family"))
    if size or family:
        mark = _word_property(paragraph._p.get_or_add_pPr(), "rPr")
        if family:
            mark.rFonts_ascii = family
            mark.rFonts_hAnsi = family
        if size:
            mark.sz_val = Pt(size)


def _cell_format(cell, css):
    properties = cell._tc.get_or_add_tcPr()
    if css.get("vertical-align") in {"top", "middle", "bottom"}:
        name = "CENTER" if css["vertical-align"] == "middle" else css["vertical-align"].upper()
        cell.vertical_alignment = getattr(WD_CELL_VERTICAL_ALIGNMENT, name)
    for side in ("top", "left", "bottom", "right"):
        padding = css.get(f"padding-{side}", css.get("padding"))
        if padding is not None:
            _word_property(_word_property(properties, "tcMar"), side,
                           w=round((points(padding) or 0) * 20), type="dxa")
        border = css.get(f"border-{side}", css.get("border", ""))
        if match := re.fullmatch(r"(\S+) solid #([0-9a-fA-F]{6})", border):
            if width := points(match[1]):
                _word_property(_word_property(properties, "tcBorders"), side,
                               val="single", sz=max(1, round(width * 8)), color=match[2])
        elif border == "none":
            _word_property(_word_property(properties, "tcBorders"), side, val="nil")
    if re.fullmatch(r"#[0-9a-fA-F]{6}", value := css.get("background-color", "")):
        _word_property(properties, "shd", val="clear", fill=value[1:])


def _add_table(node, document, root, bounds, should_cancel, styles):
    widths, row_count, placements = table_layout(node, bounds[0] / 12700)
    if not widths:
        return
    table = document.add_table(rows=row_count, cols=len(widths)) if hasattr(document, "sections") else (
        document.add_table(rows=row_count, cols=len(widths), width=Pt(sum(widths)))
    )
    if node.get("data-docx-table") != "true":
        table.style = "Table Grid"
    table.autofit = False
    for column, width in zip(table.columns, widths, strict=True):
        column.width = Pt(width)
    for row, source in zip(table.rows, node.xpath("./tr|./thead/tr|./tbody/tr|./tfoot/tr"), strict=True):
        if height := points(inline_style(source).get("height")):
            row.height = Pt(height)
            row.height_rule = WD_ROW_HEIGHT_RULE.AT_LEAST
        for cell, width in zip(row.cells, widths, strict=True):
            cell.width = Pt(width)
    for source, row, column, across, down in placements:
        if should_cancel():
            raise InterruptedError("Конвертация отменена")
        cell = table.cell(row, column)
        if across > 1 or down > 1:
            cell = cell.merge(table.cell(row + down - 1, column + across - 1))
        _cell_format(cell, inline_style(source))
        original = cell.paragraphs[0]._p
        width = Pt(sum(widths[column:column + across]))
        _body(source, cell, root, (width, bounds[1]), should_cancel, styles=styles)
        if len(cell.paragraphs) > 1:
            cell._tc.remove(original)


def _body(node, document, root, bounds, should_cancel, list_style=None, *, styles=None):
    css = inline_style(node)
    styles = _font_styles(node, styles or {}, css)
    paragraph = None
    if node.text and node.text.strip():
        paragraph = document.add_paragraph()
        _append_text(paragraph, node.text, styles, css.get("white-space") == "pre-wrap")
    for child in node:
        if should_cancel():
            raise InterruptedError("Конвертация отменена")
        tag = child.tag
        if not isinstance(tag, str) or tag in _SKIP:
            pass
        elif tag in _BLOCKS or tag in {"ol", "ul"}:
            list_styles = {"ol": "List Number", "ul": "List Bullet"}
            _body(child, document, root, bounds, should_cancel, list_styles.get(tag, list_style), styles=styles)
            paragraph = None
        elif tag == "table":
            _add_table(child, document, root, bounds, should_cancel, styles)
            paragraph = None
        elif tag in _PARAGRAPHS:
            style = _HEADINGS.get(tag, list_style if tag == "li" else None)
            item = child
            if tag == "li" and len(child) == 1 and child[0].tag == "p" and not (child.text or "").strip():
                item = child[0]
            paragraph = document.add_paragraph(style=style)
            _paragraph_format(paragraph, inline_style(item))
            _inline(item, paragraph, root, bounds, styles, False, should_cancel)
            paragraph = None
        else:
            if paragraph is None:
                paragraph = document.add_paragraph()
            _inline(child, paragraph, root, bounds, styles, False, should_cancel)
        if child.tail and child.tail.strip():
            if paragraph is None:
                paragraph = document.add_paragraph()
            _append_text(paragraph, child.tail, styles, False)


def save_body_as_docx(body, root, destination, should_cancel):
    document = Document()
    section = document.sections[0]
    for name in ("page-width", "page-height", "margin-left", "margin-right", "margin-top", "margin-bottom"):
        value = body.get(f"data-{name}")
        length = points(value)
        if length or (value == "0pt" and name.startswith("margin-")):
            attribute = name.replace("-", "_") if name.startswith("page-") else f"{name[7:]}_margin"
            setattr(section, attribute, Pt(length or 0))
    if section.page_width > section.page_height:
        section.orientation = WD_ORIENT.LANDSCAPE
    bounds = (
        section.page_width - section.left_margin - section.right_margin,
        section.page_height - section.top_margin - section.bottom_margin - Pt(20),
    )
    _body(body, document, root, bounds, should_cancel)
    with atomic_output_path(destination) as temporary:
        document.save(temporary)
        if should_cancel():
            raise InterruptedError("Конвертация отменена")


def read_body(source, should_cancel):
    if should_cancel():
        raise InterruptedError("Конвертация отменена")
    source = Path(source)
    data = source.read_bytes()
    try:
        data = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        pass
    body = html.document_fromstring(data, parser=html.HTMLParser(no_network=True)).find("body")
    if body is None:
        raise ValueError("В HTML отсутствует содержимое документа")
    return body


def import_docx(source, destination, should_cancel):
    body = read_body(source, should_cancel)
    source = Path(source)
    save_body_as_docx(body, source.parent.resolve(), destination, should_cancel)
