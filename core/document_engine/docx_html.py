"""Экспорт содержимого DOCX в самостоятельный HTML-документ."""

from base64 import b64encode
from html import escape
from pathlib import Path
from re import fullmatch
from types import SimpleNamespace
from urllib.parse import urlsplit

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.opc.constants import RELATIONSHIP_TYPE
from docx.oxml.ns import nsmap, qn
from docx.table import Table, _Cell
from docx.text.hyperlink import Hyperlink
from docx.text.paragraph import Paragraph
from docx.text.parfmt import ParagraphFormat
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
    elif (shading := _table_setting(properties, "w:shd")) is not None:
        fill = shading.get(qn("w:fill"), "")
        if fullmatch(r"[0-9a-fA-F]{6}", fill):
            css.append(f"background-color:#{fill}")
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


def _fill(shading):
    if shading is not None and fullmatch(r"[0-9a-fA-F]{6}", value := shading.get(qn("w:fill"), "")):
        return f"#{value}"
    return None


def _paragraph_css(paragraph, typography, *, table_style=None, list_level=None):
    style = paragraph.style
    formats = [paragraph.paragraph_format]
    direct = paragraph._p.pPr
    properties = [direct]
    style_fonts = tuple(_style_fonts(paragraph.style))
    if list_level is not None:
        level_properties = list_level.find(qn("w:pPr"))
        properties.append(level_properties)
        if level_properties is not None:
            formats.append(ParagraphFormat(SimpleNamespace(pPr=level_properties)))
    while style is not None:
        formats.append(style.paragraph_format)
        properties.append(style.element.find(qn("w:pPr")))
        style = style.base_style
    # Table style paragraph properties override the document's Normal style.
    while table_style is not None:
        if (table_properties := table_style.element.find(qn("w:pPr"))) is not None:
            index = 2 if list_level is not None and level_properties is not None else 1
            formats.insert(index, table_style.paragraph_format)
            properties.insert(index, table_properties)
            break
        table_style = table_style.base_style

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
    if background := _fill(_table_setting(properties, "w:shd")):
        css.append(f"background-color:{background}")

    defaults, _ = typography
    mark = direct.find(qn("w:rPr")) if direct is not None else None
    font_properties = (mark, *(font._element.rPr for font in style_fonts))
    size = next((element for props in (*font_properties, defaults)
                 if props is not None and (element := props.find(qn("w:sz"))) is not None), None)
    if size is not None:
        css.append(f"font-size:{int(size.get(qn('w:val'))) / 2:g}pt")
    _, theme = typography
    if family := next((name for prop in (*font_properties, defaults) if (name := _family(prop, theme))), None):
        css.append(f"font-family:{family}")
    return ";".join(css)


def _paragraph_html(paragraph, typography, *, table_style=None, list_level=None):
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
    css = _paragraph_css(paragraph, typography, table_style=table_style, list_level=list_level)
    attributes = f' style="{escape(css, quote=True)}"' if css else ""
    if paragraph._p.xpath(".//wp:anchor"):
        attributes += ' data-floating-picture="true"'
    if style in {"Caption", "Название объекта"}:
        attributes += ' data-caption="true"'
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


def _conditional_cell_properties(table, properties, row, column, columns, rows):
    look = _table_setting(properties, "w:tblLook")
    flags = {}
    if look is not None:
        mask = int(look.get(qn("w:val"), "0"), 16) if fullmatch(
            r"[0-9a-fA-F]{1,4}", look.get(qn("w:val"), ""),
        ) else 0
        for key, bit in (("firstRow", 0x20), ("lastRow", 0x40), ("firstColumn", 0x80),
                         ("lastColumn", 0x100), ("noHBand", 0x200), ("noVBand", 0x400)):
            value = look.get(qn(f"w:{key}"))
            flags[key] = bool(mask & bit) if value is None else value in {"1", "true", "on"}

    active = []
    for key, flag, position in (
        ("firstRow", "firstRow", row == 0), ("lastRow", "lastRow", row == rows - 1),
        ("firstCol", "firstColumn", column == 0), ("lastCol", "lastColumn", column == columns - 1),
    ):
        if position and flags.get(flag):
            active.append(key)
    for axis, offset, first, last, limit, flag, band in (
        ("Horz", row, "firstRow", "lastRow", rows, "noHBand", "Row"),
        ("Vert", column, "firstColumn", "lastColumn", columns, "noVBand", "Col"),
    ):
        start, end = int(flags.get(first, False)), limit - int(flags.get(last, False))
        if not flags.get(flag) and start <= offset < end:
            size = _table_setting(properties, f"w:tblStyle{band}BandSize")
            value = size.get(qn("w:val"), "") if size is not None else ""
            size = max(1, int(value)) if value.isascii() and value.isdecimal() else 1
            active.append(f"band{1 + ((offset - start) // size) % 2}{axis}")
    active.append("wholeTable")

    result = []
    style = table.style
    while style is not None:
        variants = {element.get(qn("w:type")): element.find(qn("w:tcPr"))
                    for element in style.element.findall(qn("w:tblStylePr"))}
        result.extend(variants[key] for key in active if variants.get(key) is not None)
        style = style.base_style
    return result


def _cell_style(cell, table, properties, row, column, down, rows, columns):
    css = []
    cell_properties = cell._tc.tcPr
    cell_styles = (cell_properties, *_conditional_cell_properties(table, properties, row, column, columns, rows))
    if background := _fill(_table_setting(cell_styles, "w:shd")):
        css.append(f"background-color:{background}")
    for side, default in (("left", 5.4), ("right", 5.4), ("top", 0), ("bottom", 0)):
        margin = _table_setting(cell_styles, f"w:tcMar/w:{side}")
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
        border = _table_setting(cell_styles, f"w:tcBorders/w:{side}")
        if border is None and not outside:
            border = _table_setting(cell_styles[1:], f"w:tcBorders/w:{inside}")
        if border is None:
            border = _table_setting(properties, f"w:tblBorders/w:{side if outside else inside}")
        if border is None:
            continue
        if border.get(qn("w:val")) in {"nil", "none"}:
            css.append(f"border-{side}:none")
            continue
        size = border.get(qn("w:sz"), "4")
        color = border.get(qn("w:color"), "auto")
        width = int(size) / 8 if size.isascii() and size.isdecimal() else .5
        if width:
            color = color if fullmatch(r"[0-9a-fA-F]{6}", color) else "000000"
            css.append(f"border-{side}:{width:g}pt solid #{color}")

    alignment = _table_setting(cell_styles, "w:vAlign")
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
                css = _cell_style(cell, table, properties, index, column, height, len(rows), column_count)
                hide_mark = _table_setting((cell._tc.tcPr,), "w:hideMark")
                empty_cell = len(cell._tc) == 2 and not cell._tc.xpath(".//w:r | .//w:hyperlink")
                hide_empty_mark = (
                    empty_cell and hide_mark is not None and hide_mark.get(qn("w:val")) not in {"0", "false", "off"}
                )
                content = "" if hide_empty_mark else _body_html(
                    cell, should_cancel, typography, table_style=table.style,
                )
                parts.extend((f'<td{attrs} style="{css}">', content, "</td>"))
            column += span
        parts.append("</tr>")
    return "".join((*parts, "</table>"))


def _blocks(parent, element):
    for child in element:
        if child.tag == qn("w:p"):
            yield Paragraph(child, parent)
        elif child.tag == qn("w:tbl"):
            yield Table(child, parent)
        elif child.tag == qn("w:sdt"):
            content = child.find(qn("w:sdtContent"))
            if content is not None:
                yield from _blocks(parent, content)


def _section_blocks(document, should_cancel):
    body = document.element.body
    blocks = []
    for block in _blocks(document, body):
        _check_cancel(should_cancel)
        blocks.append(block)
        if (isinstance(block, Paragraph) and block._p.getparent() is body
                and block._p.find("w:pPr/w:sectPr", nsmap) is not None):
            yield blocks
            blocks = []
    yield blocks


def _numbering_level(paragraph, numberings):
    properties = paragraph._p.pPr
    if properties is None or properties.numPr is None or properties.numPr.numId is None:
        return None, None, False
    numbering_id = properties.numPr.numId.val
    if numbering_id == 0:
        return None, None, True
    level = properties.numPr.ilvl.val if properties.numPr.ilvl is not None else 0
    key = numbering_id, level
    if key not in numberings:
        try:
            numbering = paragraph.part.part_related_by(RELATIONSHIP_TYPE.NUMBERING).element
        except KeyError:
            return key, None, True
        ids = numbering.xpath(f"./w:num[@w:numId='{numbering_id}']/w:abstractNumId/@w:val")
        overrides = numbering.xpath(f"./w:num[@w:numId='{numbering_id}']/w:lvlOverride[@w:ilvl='{level}']/w:lvl")
        definitions = []
        if ids and ids[0].isascii() and ids[0].isdigit():
            definitions = numbering.xpath(f"./w:abstractNum[@w:abstractNumId='{ids[0]}']/w:lvl[@w:ilvl='{level}']")
        numberings[key] = next(iter(overrides or definitions), None)
    return key, numberings[key], True


def _body_html(container, should_cancel, typography=None, *, section_blocks=None, table_style=None):
    if typography is None:
        typography = _typography(container)
    parts = []
    current_list = None
    numberings = {}
    if section_blocks is None:
        element = container._element
        body = element.find(qn("w:body"))
        section_blocks = _blocks(container, element if body is None else body)
        skip_section_mark = False
    else:
        skip_section_mark = True
    for block in section_blocks:
        _check_cancel(should_cancel)
        if skip_section_mark and not isinstance(block, Table):
            properties = block._p.pPr
            if (properties is not None and properties.sectPr is not None and not block.text
                    and not block._p.xpath(".//w:drawing | .//w:pict | .//w:br | .//w:cr")):
                continue
        style = block.style.name if block.style is not None else ""
        list_tag = list_level = list_key = None
        if not isinstance(block, Table):
            list_key, list_level, direct_numbering = _numbering_level(block, numberings)
            format_element = list_level.find(qn("w:numFmt")) if list_level is not None else None
            number_format = format_element.get(qn("w:val")) if format_element is not None else None
            if number_format == "decimal" or (not direct_numbering and style.startswith("List Number")):
                list_tag = "ol"
            elif number_format == "bullet" or (not direct_numbering and style.startswith("List Bullet")):
                list_tag = "ul"
        if current_list != (next_list := (list_tag, list_key) if list_tag else None):
            if current_list:
                parts.append(f"</{current_list[0]}>")
            if list_tag:
                parts.append(f"<{list_tag}>")
            current_list = next_list
        if isinstance(block, Table):
            parts.append(_table_html(block, should_cancel, typography))
        else:
            paragraph = _paragraph_html(block, typography, table_style=table_style, list_level=list_level)
            parts.append(f"<li>{paragraph}</li>" if list_tag else paragraph)
    if current_list:
        parts.append(f"</{current_list[0]}>")
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
