"""Экспорт содержимого DOCX в самостоятельный HTML-документ."""

from base64 import b64encode
from html import escape
from pathlib import Path
from re import fullmatch
from urllib.parse import urlsplit

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.opc.constants import RELATIONSHIP_TYPE
from docx.oxml.ns import nsmap, qn
from docx.table import Table, _Cell
from docx.text.hyperlink import Hyperlink
from lxml import etree

from core.filesystem import atomic_output_path

_IMAGE_TYPES = {"image/png", "image/jpeg", "image/gif", "image/webp", "image/bmp"}
_PAGE_BREAK = '<br data-page-break="true">'
_HIGHLIGHTS = {
    "black": "#000000", "blue": "#0000FF", "cyan": "#00FFFF", "green": "#00FF00",
    "magenta": "#FF00FF", "red": "#FF0000", "yellow": "#FFFF00", "white": "#FFFFFF",
    "darkBlue": "#000080", "darkCyan": "#008080", "darkGreen": "#008000", "darkMagenta": "#800080",
    "darkRed": "#800000", "darkYellow": "#808000", "darkGray": "#808080", "lightGray": "#C0C0C0",
}
_ALIGNMENT = {
    WD_ALIGN_PARAGRAPH.LEFT: "left", WD_ALIGN_PARAGRAPH.CENTER: "center",
    WD_ALIGN_PARAGRAPH.RIGHT: "right", WD_ALIGN_PARAGRAPH.JUSTIFY: "justify",
    WD_ALIGN_PARAGRAPH.DISTRIBUTE: "justify",
}


def _check_cancel(should_cancel):
    if should_cancel():
        raise InterruptedError("Конвертация отменена")


def _inline_picture(element, part, extent):
    relationship = element.get(qn("r:embed"))
    if relationship is None:
        return ""
    image = part.related_parts.get(relationship)
    if image is None or image.content_type not in _IMAGE_TYPES:
        return ""
    encoded = b64encode(image.blob).decode("ascii")
    style = ""
    if extent is not None:
        width, height = int(extent.get("cx")) / 12700, int(extent.get("cy")) / 12700
        style = f' style="width:{width:.4f}pt;height:{height:.4f}pt"'
    return f'<img src="data:{image.content_type};base64,{encoded}" alt=""{style}>'


def _style_fonts(style):
    while style is not None:
        yield style.font
        style = style.base_style


def _typography(document):
    defaults = document.styles.element.find("w:docDefaults/w:rPrDefault/w:rPr", nsmap)
    theme = {}
    try:
        part = document.part.part_related_by(RELATIONSHIP_TYPE.THEME)
    except KeyError:
        return defaults, theme
    xml = etree.fromstring(part.blob, parser=etree.XMLParser(resolve_entities=False, no_network=True))
    for group in ("major", "minor"):
        for suffix, tag in (("HAnsi", "latin"), ("Ascii", "latin"), ("EastAsia", "ea"), ("Bidi", "cs")):
            font = xml.find(f".//a:fontScheme/a:{group}Font/a:{tag}", nsmap)
            if font is not None and (family := font.get("typeface")):
                theme[group + suffix] = family
    return defaults, theme


def _family(properties, theme):
    if properties is not None and (fonts := properties.find(qn("w:rFonts"))) is not None:
        for key in ("ascii", "hAnsi", "eastAsia", "cs"):
            if family := fonts.get(qn(f"w:{key}")):
                return family
            if family := theme.get(fonts.get(qn(f"w:{key}Theme"))):
                return family
    return None


def _run_html(run, paragraph, typography):
    fonts = (run.font, *_style_fonts(run.style), *_style_fonts(paragraph.style))
    fragments = []
    for child in run._element:
        if child.tag == qn("w:t"):
            fragments.append(escape(child.text or ""))
        elif child.tag in {qn("w:br"), qn("w:cr")}:
            fragments.append(_PAGE_BREAK if child.get(qn("w:type")) == "page" else "<br>")
        elif child.tag == qn("w:tab"):
            fragments.append("\t")
        elif child.tag == qn("w:drawing"):
            extent = next(child.iter(qn("wp:extent")), None)
            fragments.extend(_inline_picture(blip, run.part, extent) for blip in child.iter(qn("a:blip")))
    pieces = "".join(fragments).split(_PAGE_BREAK)
    for attribute, tag in (("bold", "strong"), ("italic", "em"), ("underline", "u")):
        flag = next((value for font in fonts if (value := getattr(font, attribute)) is not None), None)
        if flag:
            pieces = [f"<{tag}>{piece}</{tag}>" if piece else "" for piece in pieces]
    defaults, theme = typography
    properties = [font._element.rPr for font in fonts]
    family = next((name for prop in (*properties, defaults) if (name := _family(prop, theme))), None)
    size = next((font.size for font in fonts if font.size is not None), None)
    css = []
    if next((font.all_caps for font in fonts if font.all_caps is not None), False):
        css.append("text-transform:uppercase")
    color = next((font.color for font in fonts if font.color.type is not None), None)
    if color is not None and color.rgb is not None:
        css.append(f"color:#{color.rgb}")
    highlight = next((font.highlight_color for font in fonts if font.highlight_color is not None), None)
    if highlight is not None and (background := _HIGHLIGHTS.get(highlight.xml_value)):
        css.append(f"background-color:{background}")
    if family:
        css.append(f"font-family:{family}")
    if size is not None:
        css.append(f"font-size:{size.pt:g}pt")
    elif defaults is not None and (value := defaults.find(qn("w:sz"))) is not None:
        css.append(f'font-size:{int(value.get(qn("w:val"))) / 2:g}pt')
    if css and any(child.tag == qn("w:t") for child in run._element):
        style = escape(";".join(css), quote=True)
        pieces = [f'<span style="{style}">{piece}</span>' if piece else "" for piece in pieces]
    return _PAGE_BREAK.join(pieces)


def _paragraph_css(paragraph, typography):
    style = paragraph.style
    formats = [paragraph.paragraph_format]
    while style is not None:
        formats.append(style.paragraph_format)
        style = style.base_style

    def resolve(name):
        return next((value for fmt in formats if (value := getattr(fmt, name)) is not None), None)

    css = []
    if alignment := _ALIGNMENT.get(resolve("alignment")):
        css.append(f"text-align:{alignment}")
    for property_name, css_name in (
        ("left_indent", "margin-left"), ("right_indent", "margin-right"), ("first_line_indent", "text-indent"),
        ("space_before", "margin-top"), ("space_after", "margin-bottom"),
    ):
        if (length := resolve(property_name)) is not None:
            css.append(f"{css_name}:{length.pt:g}pt")
    line_spacing = resolve("line_spacing")
    if hasattr(line_spacing, "pt"):
        css.append(f"line-height:{line_spacing.pt:g}pt")
        if resolve("line_spacing_rule") == WD_LINE_SPACING.AT_LEAST:
            css.append("--docx-line-height-at-least:1")
    elif line_spacing is not None:
        css.append(f"line-height:{line_spacing * 100:g}%")
    if resolve("keep_with_next"):
        css.append("--docx-keep-with-next:1")
    if resolve("page_break_before"):
        css.append("page-break-before:always")

    defaults, _ = typography
    properties = paragraph._p.pPr
    mark = properties.find(qn("w:rPr")) if properties is not None else None
    size = next((element for props in (mark, defaults)
                 if props is not None and (element := props.find(qn("w:sz"))) is not None), None)
    if size is not None:
        css.append(f"font-size:{int(size.get(qn('w:val'))) / 2:g}pt")
    return ";".join(css)


def _paragraph_html(paragraph, typography):
    style = paragraph.style.name if paragraph.style is not None else ""
    levels = {f"Heading {level}": f"h{level}" for level in range(1, 7)}
    tag = levels.get(style, "h1" if style == "Title" else "p")
    inline = []
    for item in paragraph.iter_inner_content():
        if isinstance(item, Hyperlink):
            text = "".join(_run_html(run, paragraph, typography) for run in item.runs)
            url = item.url
            if url and (url.startswith("#") or urlsplit(url).scheme in {"https", "http", "mailto"}):
                text = f'<a href="{escape(url, quote=True)}">{text}</a>'
            inline.append(text)
        else:
            inline.append(_run_html(item, paragraph, typography))
    css = _paragraph_css(paragraph, typography)
    attributes = f' style="{escape(css, quote=True)}"' if css else ""
    return f"<{tag}{attributes}>{''.join(inline)}</{tag}>"


def _table_properties(table):
    yield table._tbl.tblPr
    style = table.style
    while style is not None:
        if (properties := style.element.find(qn("w:tblPr"))) is not None:
            yield properties
        style = style.base_style


def _table_setting(properties, tag):
    return next((value for prop in properties if prop is not None and (value := prop.find(tag, nsmap)) is not None),
                None)


def _cell_style(cell, properties, row, column, down, rows, columns):
    css = []
    cell_properties = cell._tc.tcPr
    for side, default in (("left", 5.4), ("right", 5.4), ("top", 0), ("bottom", 0)):
        margin = _table_setting((cell_properties,), f"w:tcMar/w:{side}")
        if margin is None:
            margin = _table_setting(properties, f"w:tblCellMar/w:{side}")
        width = margin.get(qn("w:w"), "") if margin is not None else ""
        if width.isascii() and width.isdecimal():
            default = int(width) / 20
        css.append(f"padding-{side}:{default:g}pt")

    for side, outside, inside in (
        ("left", column == 0, "insideV"),
        ("right", column + cell.grid_span == columns, "insideV"),
        ("top", row == 0, "insideH"),
        ("bottom", row + down == rows, "insideH"),
    ):
        border = _table_setting((cell_properties,), f"w:tcBorders/w:{side}")
        if border is None:
            border = _table_setting(properties, f"w:tblBorders/w:{side if outside else inside}")
        if border is None or border.get(qn("w:val")) in {"nil", "none"}:
            continue
        size = border.get(qn("w:sz"), "4")
        color = border.get(qn("w:color"), "auto")
        width = int(size) / 8 if size.isascii() and size.isdecimal() else .5
        if width:
            color = color if fullmatch(r"[0-9a-fA-F]{6}", color) else "000000"
            css.append(f"border-{side}:{width:g}pt solid #{color}")

    alignment = _table_setting((cell_properties,), "w:vAlign")
    if alignment is not None:
        value = {"center": "middle", "bottom": "bottom"}.get(alignment.get(qn("w:val")))
        if value:
            css.append(f"vertical-align:{value}")
    return ";".join(css)


def _table_html(table, should_cancel, typography):
    properties = tuple(_table_properties(table))
    justification = _table_setting(properties, "w:jc")
    alignment = justification.get(qn("w:val")) if justification is not None else None
    align = f' align="{alignment}"' if alignment in {"left", "center", "right"} else ""
    parts = [f'<table data-docx-table="true"{align}><colgroup>']
    for column in table.columns:
        width = f' style="width:{column.width.pt:g}pt"' if column.width else ""
        parts.append(f"<col{width}>")
    parts.append("</colgroup>")
    rows = []
    for row in table.rows:
        _check_cancel(should_cancel)
        cells = {}
        offset = row.grid_cols_before
        for cell_xml in row._tr.tc_lst:
            cell = _Cell(cell_xml, table)
            cells[offset] = cell
            offset += cell.grid_span
        rows.append((cells, offset + row.grid_cols_after, row.height))
    column_count = max(len(table.columns), max((columns for _, columns, _ in rows), default=0))
    for index, (cells, columns, row_height) in enumerate(rows):
        _check_cancel(should_cancel)
        parts.append(f'<tr style="height:{row_height.pt:g}pt">' if row_height else "<tr>")
        column = 0
        while column < columns:
            cell = cells.get(column)
            if cell is None:
                parts.append("<td></td>")
                column += 1
                continue
            span = cell.grid_span
            if cell._tc.vMerge != "continue":
                attrs = f' colspan="{span}"' if span > 1 else ""
                height = 1
                if cell._tc.vMerge == "restart":
                    for next_index in range(index + 1, len(rows)):
                        next_cells = rows[next_index][0]
                        below = next_cells.get(column)
                        if below is None or below.grid_span != span or below._tc.vMerge != "continue":
                            break
                        height += 1
                    if height > 1:
                        attrs += f' rowspan="{height}"'
                css = _cell_style(cell, properties, index, column, height, len(rows), column_count)
                hide_mark = _table_setting((cell._tc.tcPr,), "w:hideMark")
                empty_cell = len(cell._tc) == 2 and not cell._tc.xpath(".//w:r | .//w:hyperlink")
                hide_empty_mark = (
                    empty_cell and hide_mark is not None and hide_mark.get(qn("w:val")) not in {"0", "false", "off"}
                )
                content = "" if hide_empty_mark else _body_html(cell, should_cancel, typography)
                parts.extend((f'<td{attrs} style="{css}">', content, "</td>"))
            column += span
        parts.append("</tr>")
    return "".join((*parts, "</table>"))


def _body_html(container, should_cancel, typography=None, *, skip_section_mark=False):
    if typography is None:
        typography = _typography(container)
    parts = []
    current_list = None
    for block in container.iter_inner_content():
        _check_cancel(should_cancel)
        if skip_section_mark and not isinstance(block, Table):
            properties = block._p.pPr
            if (properties is not None and properties.sectPr is not None and not block.text
                    and not block._p.xpath(".//w:drawing | .//w:pict | .//w:br | .//w:cr")):
                continue
        style = block.style.name if block.style is not None else ""
        list_tag = None
        if not isinstance(block, Table):
            if style.startswith("List Number"):
                list_tag = "ol"
            elif style.startswith("List Bullet"):
                list_tag = "ul"
        if current_list != list_tag:
            if current_list:
                parts.append(f"</{current_list}>")
            if list_tag:
                parts.append(f"<{list_tag}>")
            current_list = list_tag
        if isinstance(block, Table):
            parts.append(_table_html(block, should_cancel, typography))
        else:
            paragraph = _paragraph_html(block, typography)
            parts.append(f"<li>{paragraph}</li>" if list_tag else paragraph)
    if current_list:
        parts.append(f"</{current_list}>")
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
