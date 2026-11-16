"""Преобразование структуры документов в разметку для встроенного PDF-движка."""

from __future__ import annotations

import base64
import binascii
import html
import posixpath
import re
from dataclasses import dataclass, field
from urllib.parse import unquote, urlsplit
from xml.etree import ElementTree as ET
from zipfile import ZipFile

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
R = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
WP = "{http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing}"
ODF_TEXT = "{urn:oasis:names:tc:opendocument:xmlns:text:1.0}"
ODF_TABLE = "{urn:oasis:names:tc:opendocument:xmlns:table:1.0}"
ODF_DRAW = "{urn:oasis:names:tc:opendocument:xmlns:drawing:1.0}"
ODF_SVG = "{urn:oasis:names:tc:opendocument:xmlns:svg-compatible:1.0}"
ODF_XLINK = "{http://www.w3.org/1999/xlink}"
ODF_STYLE = "{urn:oasis:names:tc:opendocument:xmlns:style:1.0}"
ODF_FO = "{urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0}"


@dataclass
class PdfLayout:
    markup: str = ""
    assets: dict[str, bytes] = field(default_factory=dict)
    warnings: set[str] = field(default_factory=set)
    width: float = 595.0
    height: float = 842.0
    margins: tuple[float, float, float, float] = (48, 48, 48, 48)


def _val(node, default=None):
    return node.get(W + "val", default) if node is not None else default


def _enabled(node):
    return node is not None and _val(node, "1") not in {"0", "false", "off"}


def docx_layout(path) -> PdfLayout:
    layout = PdfLayout()
    layout.warnings.add("расположение элементов и переносы строк могут отличаться")
    with ZipFile(path) as package:
        root = ET.fromstring(package.read("word/document.xml"))
        names = set(package.namelist())
        relationships = {}
        if "word/_rels/document.xml.rels" in names:
            rels = ET.fromstring(package.read("word/_rels/document.xml.rels"))
            for rel in rels:
                if rel.get("TargetMode") != "External":
                    target = rel.get("Target", "")
                    relationships[rel.get("Id")] = posixpath.normpath(
                        target.lstrip("/") if target.startswith("/") else posixpath.join("word", target)
                    )

        styles = {}
        defaults = None
        paragraph_defaults = None
        if "word/styles.xml" in names:
            styles_root = ET.fromstring(package.read("word/styles.xml"))
            defaults = styles_root.find(".//" + W + "rPrDefault/" + W + "rPr")
            paragraph_defaults = styles_root.find(".//" + W + "pPrDefault/" + W + "pPr")
            for style in styles_root.findall(W + "style"):
                styles[style.get(W + "styleId")] = style

        numberings = {}
        counters = {}
        if "word/numbering.xml" in names:
            number_root = ET.fromstring(package.read("word/numbering.xml"))
            abstracts = {node.get(W + "abstractNumId"): node for node in number_root.findall(W + "abstractNum")}
            for number in number_root.findall(W + "num"):
                abstract = abstracts.get(_val(number.find(W + "abstractNumId")))
                if abstract is not None:
                    numberings[number.get(W + "numId")] = (number, abstract)

        def list_info(num_pr):
            number_id = _val(num_pr.find(W + "numId"))
            level_value = _val(num_pr.find(W + "ilvl"), "0")
            if not number_id or number_id == "0" or not level_value.isdigit():
                return None
            level = int(level_value)
            if level > 8 or number_id not in numberings:
                layout.warnings.add("не удалось восстановить оформление списка")
                return None
            number, abstract = numberings[number_id]
            level_node = next(
                (item for item in abstract.findall(W + "lvl") if item.get(W + "ilvl") == str(level)), None
            )
            override = next(
                (item for item in number.findall(W + "lvlOverride") if item.get(W + "ilvl") == str(level)), None
            )
            if override is not None and override.find(W + "lvl") is not None:
                level_node = override.find(W + "lvl")
            if level_node is None:
                layout.warnings.add("не удалось восстановить уровень списка")
                return None
            fmt = _val(level_node.find(W + "numFmt"), "decimal")
            template = _val(level_node.find(W + "lvlText"), "•" if fmt == "bullet" else f"%{level + 1}.")
            if fmt == "bullet":
                label = {"\uf0b7": "•", "\uf0a7": "▪", "\uf0d8": "➢"}.get(template, template)
            else:
                starts = counters.setdefault(number_id, {})
                start = _val(override.find(W + "startOverride")) if override is not None else None
                start = start or _val(level_node.find(W + "start"), "1")
                start_value = int(start) if start and start.isdigit() else 1
                starts[level] = starts.get(level, start_value - 1) + 1
                for deeper in tuple(starts):
                    if deeper > level:
                        del starts[deeper]
                if fmt not in {"decimal", "decimalZero"}:
                    layout.warnings.add("формат нумерации списка может отличаться")
                label = template
                for counter_level in range(9):
                    value = starts.get(counter_level, 1)
                    text_value = f"{value:02d}" if fmt == "decimalZero" else str(value)
                    label = label.replace(f"%{counter_level + 1}", text_value)
            indentation = level_node.find("./" + W + "pPr/" + W + "ind")
            left = indentation.get(W + "left", "720") if indentation is not None else "720"
            hanging = indentation.get(W + "hanging", "360") if indentation is not None else "360"
            left_points = int(left) / 20 if left.lstrip("-").isdigit() else 36
            hanging_points = int(hanging) / 20 if hanging.lstrip("-").isdigit() else 18
            return label, left_points, hanging_points

        def style_chain(style_id, element):
            result, seen = [], set()
            while style_id and style_id not in seen and style_id in styles:
                seen.add(style_id)
                style = styles[style_id]
                part = style.find(W + element)
                if part is not None:
                    result.insert(0, part)
                style_id = _val(style.find(W + "basedOn"))
            return result

        def run_css(parts):
            props = {}
            for part in parts:
                if part is None:
                    continue
                for tag, css in (("b", "font-weight"), ("i", "font-style"), ("u", "text-decoration")):
                    node = part.find(W + tag)
                    if node is not None:
                        props[css] = (
                            {"b": "bold", "i": "italic", "u": "underline"}[tag]
                            if _enabled(node) and _val(node) != "none"
                            else {"b": "normal", "i": "normal", "u": "none"}[tag]
                        )
                size = _val(part.find(W + "sz"))
                if size and size.isdigit():
                    props["font-size"] = f"{int(size) / 2:g}pt"
                color = _val(part.find(W + "color"))
                if color and re.fullmatch(r"[0-9a-fA-F]{6}", color):
                    props["color"] = "#" + color
                fonts = part.find(W + "rFonts")
                if fonts is not None and fonts.get(W + "ascii"):
                    name = fonts.get(W + "ascii")
                    if re.fullmatch(r"[\w .-]{1,80}", name) and "_" not in name:
                        props["font-family"] = name
                    else:
                        layout.warnings.add("имя шрифта не поддерживается")
            return ";".join(f"{key}:{value}" for key, value in props.items())

        def image_xml(drawing):
            if drawing.find(".//" + WP + "anchor") is not None:
                layout.warnings.add("положение плавающих изображений может отличаться")
            values = []
            for blip in drawing.iter(A + "blip"):
                target = relationships.get(blip.get(R + "embed"))
                if not target or target not in names:
                    layout.warnings.add("не удалось извлечь изображение")
                    continue
                asset = f"image{len(layout.assets)}" + posixpath.splitext(target)[1]
                layout.assets[asset] = package.read(target)
                extent = drawing.find(".//" + WP + "extent")
                size = ""
                if extent is not None:
                    try:
                        width = int(extent.get("cx")) / 12700
                        height = int(extent.get("cy")) / 12700
                        size = f' style="width:{width:g}pt;height:{height:g}pt"'
                    except (TypeError, ValueError):
                        layout.warnings.add("размер изображения может отличаться")
                values.append(f'<img src="{asset}"{size}>')
            if not values:
                layout.warnings.add("неподдерживаемый рисунок или диаграмма не перенесены")
            return "".join(values)

        def paragraph(node):
            ppr = node.find(W + "pPr")
            style_id = _val(ppr.find(W + "pStyle")) if ppr is not None else None
            pparts = (
                ([paragraph_defaults] if paragraph_defaults is not None else [])
                + style_chain(style_id, "pPr")
                + ([ppr] if ppr is not None else [])
            )
            declarations = {}
            paragraph_run = ppr.find(W + "rPr") if ppr is not None else None
            if paragraph_run is None:
                paragraph_run = node.find("./" + W + "r/" + W + "rPr")
            paragraph_css = run_css([defaults, *style_chain(style_id, "rPr"), paragraph_run])
            for entry in paragraph_css.split(";"):
                if ":" in entry:
                    key, value = entry.split(":", 1)
                    if key in {"font-size", "font-family"}:
                        declarations[key] = value
            num_pr = None
            page_break_before = False
            for part in pparts:
                align = _val(part.find(W + "jc"))
                if align in {"left", "right", "center", "both"}:
                    declarations["text-align"] = "justify" if align == "both" else align
                indent = part.find(W + "ind")
                if indent is not None:
                    for attr, prop in (
                        ("left", "margin-left"),
                        ("right", "margin-right"),
                        ("firstLine", "text-indent"),
                    ):
                        val = indent.get(W + attr)
                        if val and val.lstrip("-").isdigit():
                            declarations[prop] = f"{int(val) / 20:g}pt"
                spacing = part.find(W + "spacing")
                if spacing is not None:
                    for attr, prop in (("before", "margin-top"), ("after", "margin-bottom")):
                        val = spacing.get(W + attr)
                        if val and val.isdigit():
                            declarations[prop] = f"{int(val) / 20:g}pt"
                    line = spacing.get(W + "line")
                    if line and line.isdigit():
                        if spacing.get(W + "lineRule", "auto") == "auto":
                            declarations["line-height"] = f"{int(line) / 240:g}"
                        else:
                            declarations["line-height"] = f"{int(line) / 20:g}pt"
                if part.find(W + "numPr") is not None:
                    num_pr = part.find(W + "numPr")
                page_break = part.find(W + "pageBreakBefore")
                if page_break is not None:
                    page_break_before = _enabled(page_break)
            children = []
            text_seen = False
            for child in node.iter():
                if child.tag != W + "r":
                    continue
                rpr = child.find(W + "rPr")
                rstyle = _val(rpr.find(W + "rStyle")) if rpr is not None else None
                css = run_css([defaults, *style_chain(style_id, "rPr"), *style_chain(rstyle, "rPr"), rpr])
                pieces = []
                for item in child:
                    if item.tag == W + "t":
                        pieces.append(html.escape(item.text or ""))
                        text_seen = text_seen or bool(item.text)
                    elif item.tag == W + "tab":
                        pieces.append("&#160;&#160;&#160;&#160;")
                    elif item.tag in {W + "br", W + "cr"}:
                        if item.get(W + "type") == "page":
                            pieces.append("<pagebreak/>")
                        else:
                            pieces.append("<br>")
                    elif item.tag == W + "lastRenderedPageBreak":
                        if not text_seen:
                            page_break_before = True
                        else:
                            layout.warnings.add("сохранённый разрыв внутри абзаца может отличаться")
                    elif item.tag == W + "drawing":
                        pieces.append(image_xml(item))
                    elif item.tag in {W + "object", W + "pict"}:
                        layout.warnings.add("встроенные объекты и рисунки старого формата не поддерживаются")
                children.append(f'<span style="{html.escape(css, quote=True)}">{"".join(pieces)}</span>')
            css = ";".join(f"{k}:{v}" for k, v in declarations.items())
            listing = list_info(num_pr) if num_pr is not None else None
            attrs = ""
            if page_break_before:
                attrs = ' data-page-break-before="true"'
            if listing:
                label, left, hanging = listing
                attrs += (
                    f' data-list-label="{html.escape(label, quote=True)}"'
                    f' data-list-left="{left:g}" data-list-hanging="{hanging:g}"'
                )
            return f'<p style="{css}"{attrs}>{"".join(children) or "&#160;"}</p>'

        def block(node):
            if node.tag == W + "p":
                return paragraph(node)
            if node.tag == W + "tbl":
                rows = []
                for row in node.findall(W + "tr"):
                    cells = []
                    for cell in row.findall(W + "tc"):
                        props = cell.find(W + "tcPr")
                        span = _val(props.find(W + "gridSpan")) if props is not None else None
                        if props is not None and props.find(W + "vMerge") is not None:
                            layout.warnings.add("вертикальное объединение ячеек может отличаться")
                        attr = f' colspan="{int(span)}"' if span and span.isdigit() else ""
                        cells.append(
                            f"<td{attr}>" + "".join(block(c) for c in cell if c.tag in {W + "p", W + "tbl"}) + "</td>"
                        )
                    rows.append("<tr>" + "".join(cells) + "</tr>")
                layout.warnings.add("ширина и границы таблиц могут отличаться")
                return "<table>" + "".join(rows) + "</table>"
            return ""

        body = root.find(W + "body")
        if body is None:
            raise ValueError("DOCX не содержит основной части документа")
        layout.markup = "".join(block(child) for child in body)
        sections = list(body.iter(W + "sectPr"))
        if sections:
            if len(sections) > 1:
                layout.warnings.add("параметры нескольких разделов могут отличаться")
            section = sections[0]
            size, margin = section.find(W + "pgSz"), section.find(W + "pgMar")
            if size is not None:
                try:
                    layout.width, layout.height = int(size.get(W + "w")) / 20, int(size.get(W + "h")) / 20
                except (TypeError, ValueError):
                    layout.warnings.add("размер страницы может отличаться")
            if margin is not None:
                try:
                    layout.margins = tuple(
                        max(0, int(margin.get(W + key, "960")) / 20) for key in ("left", "top", "right", "bottom")
                    )
                except ValueError:
                    layout.warnings.add("поля страницы могут отличаться")
            if section.findall(W + "headerReference") or section.findall(W + "footerReference"):
                layout.warnings.add("колонтитулы не перенесены")
        if (
            root.find(".//" + W + "footnoteReference") is not None
            or root.find(".//" + W + "endnoteReference") is not None
        ):
            layout.warnings.add("сноски не перенесены")
        if root.find(".//" + W + "txbxContent") is not None:
            layout.warnings.add("текстовые поля могут не сохраниться")
    return layout


def odt_layout(path) -> PdfLayout:
    layout = PdfLayout()
    with ZipFile(path) as package:
        root = ET.fromstring(package.read("content.xml"))
        names = set(package.namelist())
        styles = {}
        for style_root in [root] + ([ET.fromstring(package.read("styles.xml"))] if "styles.xml" in names else []):
            for style in style_root.iter(ODF_STYLE + "style"):
                name = style.get(ODF_STYLE + "name")
                if name:
                    styles[name] = style

        def style_css(node):
            name = node.get(ODF_TEXT + "style-name")
            chain, seen = [], set()
            while name and name in styles and name not in seen:
                seen.add(name)
                style = styles[name]
                chain.insert(0, style)
                name = style.get(ODF_STYLE + "parent-style-name")
            props = {}
            for style in chain:
                for part in style:
                    for attribute, css in (
                        ("font-weight", "font-weight"),
                        ("font-style", "font-style"),
                        ("font-size", "font-size"),
                        ("color", "color"),
                        ("text-align", "text-align"),
                        ("margin-left", "margin-left"),
                        ("margin-right", "margin-right"),
                        ("margin-top", "margin-top"),
                        ("margin-bottom", "margin-bottom"),
                        ("text-indent", "text-indent"),
                    ):
                        value = part.get(ODF_FO + attribute)
                        if value and re.fullmatch(r"[\w#.%-]+", value):
                            props[css] = value
                    if part.get(ODF_STYLE + "text-underline-style") not in (None, "none"):
                        props["text-decoration"] = "underline"
                    if part.get(ODF_STYLE + "font-name"):
                        layout.warnings.add("шрифты могут быть заменены")
            return ";".join(f"{key}:{value}" for key, value in props.items())

        def render(node):
            tag = node.tag
            if tag == ODF_DRAW + "image":
                name = node.get(ODF_XLINK + "href", "").lstrip("./")
                if name not in names:
                    layout.warnings.add("не удалось извлечь изображение")
                    return ""
                asset = f"image{len(layout.assets)}" + posixpath.splitext(name)[1]
                layout.assets[asset] = package.read(name)
                return f'<img src="{asset}">'
            content = html.escape(node.text or "") + "".join(
                render(child) + html.escape(child.tail or "") for child in node
            )
            if tag in {ODF_TEXT + "p", ODF_TEXT + "h"}:
                return f'<p style="{style_css(node)}">' + (content or "&#160;") + "</p>"
            if tag == ODF_TEXT + "span":
                return f'<span style="{style_css(node)}">' + content + "</span>"
            if tag == ODF_DRAW + "frame":
                width, height = node.get(ODF_SVG + "width"), node.get(ODF_SVG + "height")
                if (
                    width
                    and height
                    and all(re.fullmatch(r"[0-9.]+(?:cm|mm|in|pt)", value) for value in (width, height))
                ):
                    content = content.replace("<img ", f'<img style="width:{width};height:{height}" ', 1)
                if node.get(ODF_TEXT + "anchor-type") not in (None, "as-char"):
                    layout.warnings.add("положение плавающих изображений может отличаться")
                return content
            if tag == ODF_TEXT + "line-break":
                return "<br>"
            if tag == ODF_TEXT + "tab":
                return "&#160;&#160;&#160;&#160;"
            if tag == ODF_TEXT + "s":
                count = node.get(ODF_TEXT + "c", "1")
                return "&#160;" * min(int(count) if count.isdigit() else 1, 1000)
            if tag == ODF_TABLE + "table":
                return "<table>" + content + "</table>"
            if tag == ODF_TABLE + "table-row":
                return "<tr>" + content + "</tr>"
            if tag == ODF_TABLE + "table-cell":
                return "<td>" + content + "</td>"
            if tag == ODF_TEXT + "list-item":
                return "<li>" + content + "</li>"
            if tag == ODF_TEXT + "list":
                return "<ul>" + content + "</ul>"
            return content

        office = "{urn:oasis:names:tc:opendocument:xmlns:office:1.0}"
        body = root.find(".//" + office + "text")
        if body is None:
            raise ValueError("ODT не содержит основного текста")
        layout.markup = "".join(render(child) for child in body)
        layout.warnings.add("размеры страниц, таблицы и расположение элементов ODT могут отличаться")
        if "styles.xml" in names:
            style_root = ET.fromstring(package.read("styles.xml"))
            page_properties = style_root.find(".//" + ODF_STYLE + "page-layout-properties")
            if page_properties is not None:

                def points(value, default):
                    match = re.fullmatch(r"([0-9.]+)(cm|mm|in|pt)", value or "")
                    if not match:
                        return default
                    return float(match.group(1)) * {"cm": 72 / 2.54, "mm": 72 / 25.4, "in": 72, "pt": 1}[match.group(2)]

                layout.width = points(page_properties.get(ODF_FO + "page-width"), layout.width)
                layout.height = points(page_properties.get(ODF_FO + "page-height"), layout.height)
                common = points(page_properties.get(ODF_FO + "margin"), 48)
                layout.margins = tuple(
                    points(page_properties.get(ODF_FO + "margin-" + side), common)
                    for side in ("left", "top", "right", "bottom")
                )
            if any(node.tag in {ODF_STYLE + "header", ODF_STYLE + "footer"} for node in style_root.iter()):
                layout.warnings.add("колонтитулы не перенесены")
    return layout


def markdown_layout(source: str) -> PdfLayout:
    """Обрабатывает распространённую разметку без запуска внешних программ."""
    layout = PdfLayout()
    layout.warnings.add("сложная разметка Markdown и изображения могут не поддерживаться")

    def inline(value):
        value = html.escape(value)
        value = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", value)
        value = re.sub(r"(?<!\*)\*([^*]+)\*", r"<em>\1</em>", value)
        value = re.sub(r"`([^`]+)`", r"<code>\1</code>", value)
        return value

    blocks, in_list, in_code = [], False, False
    for line in source.splitlines():
        if line.startswith("```"):
            if in_list:
                blocks.append("</ul>")
                in_list = False
            blocks.append("</pre>" if in_code else "<pre>")
            in_code = not in_code
            continue
        if in_code:
            blocks.append(html.escape(line) + "\n")
            continue
        match = re.match(r"^\s*[-*+]\s+(.+)$", line)
        if match:
            if not in_list:
                blocks.append("<ul>")
                in_list = True
            blocks.append("<li>" + inline(match.group(1)) + "</li>")
            continue
        if in_list:
            blocks.append("</ul>")
            in_list = False
        heading = re.match(r"^(#{1,6})\s+(.+)$", line)
        if heading:
            level = len(heading.group(1))
            blocks.append(f"<h{level}>" + inline(heading.group(2)) + f"</h{level}>")
        elif line.strip():
            blocks.append("<p>" + inline(line) + "</p>")
    if in_list:
        blocks.append("</ul>")
    if in_code:
        blocks.append("</pre>")
    layout.markup = "".join(blocks)
    return layout


def epub_layout(path) -> PdfLayout:
    """Передаёт главы EPUB в движок вместе с локальными изображениями."""
    layout = PdfLayout()
    layout.warnings.add("оформление, шрифты и разбиение на страницы EPUB могут отличаться")
    with ZipFile(path) as package:
        names = set(package.namelist())
        container = ET.fromstring(package.read("META-INF/container.xml"))
        package_name = next(
            (node.get("full-path") for node in container.iter() if node.tag.rsplit("}", 1)[-1] == "rootfile"),
            None,
        )
        if not package_name or package_name not in names:
            raise ValueError("EPUB не содержит описания книги")
        metadata = ET.fromstring(package.read(package_name))
        manifest = {
            node.get("id"): node.get("href") for node in metadata.iter() if node.tag.rsplit("}", 1)[-1] == "item"
        }
        chapters = []
        for item in metadata.iter():
            if item.tag.rsplit("}", 1)[-1] != "itemref":
                continue
            href = manifest.get(item.get("idref"))
            if not href:
                layout.warnings.add("не найдена глава EPUB")
                continue
            chapter_name = posixpath.normpath(
                posixpath.join(posixpath.dirname(package_name), unquote(urlsplit(href).path))
            )
            if chapter_name not in names:
                layout.warnings.add("не найдена глава EPUB: " + href)
                continue
            data = package.read(chapter_name)
            try:
                chapter = data.decode("utf-8-sig")
            except UnicodeDecodeError:
                chapter = data.decode("utf-8", errors="replace")
                layout.warnings.add("кодировка главы EPUB может отображаться неправильно")

            def image(match, chapter_name=chapter_name):
                reference = html.unescape(match.group(2))
                url = urlsplit(reference)
                target = posixpath.normpath(posixpath.join(posixpath.dirname(chapter_name), unquote(url.path)))
                if url.scheme or url.netloc or target not in names:
                    layout.warnings.add("не найдено изображение EPUB: " + reference)
                    return match.group(0)
                suffix = posixpath.splitext(target)[1].lower()
                name = f"epub-image-{len(layout.assets)}{suffix}"
                layout.assets[name] = package.read(target)
                return match.group(1) + name + match.group(3)

            chapter = re.sub(r'(<img\b[^>]*?\bsrc\s*=\s*["\'])([^"\']+)(["\'])', image, chapter, flags=re.IGNORECASE)
            chapters.append(chapter)
        if not chapters:
            raise ValueError("EPUB не содержит доступных глав")
        layout.markup = "\n".join(chapters)
    return layout


def fb2_layout(path) -> PdfLayout:
    """Сохраняет структуру и встроенные изображения FictionBook."""
    layout = PdfLayout()
    layout.warnings.add("оформление и разбиение на страницы FB2 могут отличаться")
    root = ET.parse(path).getroot()
    binaries = {}
    for node in root.iter():
        if node.tag.rsplit("}", 1)[-1] != "binary" or not node.get("id"):
            continue
        content_type = node.get("content-type", "").lower()
        suffix = {"image/png": ".png", "image/jpeg": ".jpg", "image/jpg": ".jpg"}.get(content_type)
        if not suffix:
            layout.warnings.add("неподдерживаемый формат изображения FB2: " + content_type)
            continue
        try:
            data = base64.b64decode("".join((node.text or "").split()), validate=True)
        except (ValueError, binascii.Error):
            layout.warnings.add("повреждено изображение FB2: " + node.get("id"))
            continue
        name = f"fb2-image-{len(layout.assets)}{suffix}"
        layout.assets[name] = data
        binaries[node.get("id")] = name

    def render(node):
        name = node.tag.rsplit("}", 1)[-1]
        if name == "image":
            reference = node.get("{http://www.w3.org/1999/xlink}href", "").lstrip("#")
            target = binaries.get(reference)
            if not target:
                layout.warnings.add("не найдено изображение FB2: " + reference)
                return ""
            return f'<img src="{target}">'
        content = html.escape(node.text or "") + "".join(
            render(child) + html.escape(child.tail or "") for child in node
        )
        if name in {"p", "v", "subtitle", "text-author", "date"}:
            return "<p>" + (content or "&#160;") + "</p>"
        if name == "empty-line":
            return "<p>&#160;</p>"
        if name == "emphasis":
            return "<em>" + content + "</em>"
        if name == "strong":
            return "<strong>" + content + "</strong>"
        if name == "title":
            return "<strong>" + content + "</strong>"
        if name in {"table", "tr", "td", "th"}:
            return f"<{name}>" + content + f"</{name}>"
        if name in {"notes", "annotation"}:
            layout.warnings.add("расположение примечаний FB2 может отличаться")
        return content

    bodies = [node for node in root if node.tag.rsplit("}", 1)[-1] == "body"]
    if not bodies:
        raise ValueError("FB2 не содержит текста книги")
    layout.markup = "".join(render(body) for body in bodies)
    return layout
