"""Отрисовка документов с подбором системных шрифтов и формированием текста средствами Qt."""

from pathlib import Path
from re import fullmatch

from lxml import etree
from PySide6.QtCore import QMarginsF, QPointF, QRectF, QSizeF, QUrl
from PySide6.QtGui import (
    QAbstractTextDocumentLayout,
    QColor,
    QFont,
    QFontDatabase,
    QGuiApplication,
    QImage,
    QPageLayout,
    QPageSize,
    QPainter,
    QPalette,
    QPdfWriter,
    QTextDocument,
    QTextFrameFormat,
    QTextLength,
    QTextTable,
)
from reportlab.lib.pagesizes import A4

from core.document_engine.formatting import image_size, inline_style, points
from core.document_engine.rtf_export import image_data
from core.document_engine.table_layout import table_layout
from core.filesystem import atomic_output_path


class _LocalDocument(QTextDocument):
    def loadResource(self, resource_type, name):
        return None  # All embedded images are registered explicitly.


def _qt_tables(frame):
    for child in frame.childFrames():
        if isinstance(child, QTextTable):
            yield child
        yield from _qt_tables(child)


def _format_cell(cell, css):
    fmt = cell.format().toTableCellFormat()
    for side in ("Top", "Right", "Bottom", "Left"):
        edge = side.lower()
        if (padding := css.get(f"padding-{edge}")) is not None and padding not in {"0pt", "5.4pt"}:
            getattr(fmt, f"set{side}Padding")(points(padding) or 0)
        border = fullmatch(r"([\d.]+pt) solid (#[0-9a-fA-F]{6})", css.get(f"border-{edge}", ""))
        if border and (width := points(border[1])) is not None:
            getattr(fmt, f"set{side}Border")(width)
            getattr(fmt, f"set{side}BorderBrush")(QColor(border[2]))
            getattr(fmt, f"set{side}BorderStyle")(QTextFrameFormat.BorderStyle.BorderStyle_Solid)
    cell.setFormat(fmt)


def write_pdf(body, source, destination, should_cancel, *, layout=None):
    if QGuiApplication.instance() is None:
        raise RuntimeError("Для подбора шрифтов PDF требуется запущенное приложение Мультифора")
    if not QFontDatabase.families():
        raise RuntimeError("Системные шрифты для вывода PDF недоступны")
    if should_cancel():
        raise InterruptedError("Конвертация отменена")
    size = layout.size if layout else A4
    left, right, top, bottom = layout.margins if layout else (54, 54, 54, 54)
    width, height = size[0] - left - right, size[1] - top - bottom
    if width <= 0 or height <= 0:
        raise ValueError("Некорректные размеры страницы документа")
    document = _LocalDocument()
    font = document.defaultFont()
    # QPdfWriter может записать необязательные лигатуры как управляющие символы текстового слоя.
    for tag in ("liga", "clig", "dlig", "hlig"):
        font.setFeature(QFont.Tag.fromString(tag), 0)
    document.setDefaultFont(font)
    document.setDocumentMargin(0)
    document.setPageSize(QSizeF(width, height))
    cell_widths = {}
    tables = []
    for table in body.iter("table"):
        limit = next((cell_widths[parent] for parent in table.iterancestors() if parent in cell_widths), width)
        columns, _, placements = table_layout(table, limit)
        if not columns:
            continue
        tables.append((table, columns, placements))
        for cell, _, column, across, _ in placements:
            cell_widths[cell] = max(1, sum(columns[column:column + across]) - 12)
    root = Path(source).parent.resolve()
    for index, element in enumerate(body.iter("img")):
        if should_cancel():
            raise InterruptedError("Конвертация отменена")
        data = image_data(element, root)
        if data is None:
            element.attrib.pop("src", None)
            continue
        image = QImage(str(data)) if isinstance(data, Path) else QImage.fromData(data.getvalue())
        if image.isNull():
            continue
        url = QUrl(f"multifora-image:{index}")
        document.addResource(QTextDocument.ResourceType.ImageResource, url, image)
        element.set("src", url.toString())
        limit = next((cell_widths[parent] for parent in element.iterancestors() if parent in cell_widths), width)
        display_width, display_height = image_size(element, image.width(), image.height(),
                                                   width_limit=limit, height_limit=height)
        element.set("width", f"{display_width:g}")
        element.set("height", f"{display_height:g}")
    document.setHtml(etree.tostring(body, method="html", encoding="unicode"))
    for table, (source_table, widths, placements) in zip(_qt_tables(document.rootFrame()), tables, strict=False):
        if table.columns() != len(widths):
            continue
        fmt = table.format()
        fixed = QTextLength.Type.FixedLength
        fmt.setWidth(QTextLength(fixed, sum(widths)))
        fmt.setColumnWidthConstraints([QTextLength(fixed, value) for value in widths])
        if source_table.get("data-docx-table") == "true":
            fmt.setBorderCollapse(True)
            fmt.setCellSpacing(0)
            for element, row, column, _, _ in placements:
                cell = table.cellAt(row, column)
                if cell.isValid():
                    _format_cell(cell, inline_style(element))
        table.setFormat(fmt)
    with atomic_output_path(destination) as temporary:
        writer = QPdfWriter(temporary)
        writer.setResolution(72)
        writer.setPageSize(QPageSize(QSizeF(*size), QPageSize.Unit.Point))
        writer.setPageMargins(QMarginsF(), QPageLayout.Unit.Point)
        painter = QPainter(writer)
        if not painter.isActive():
            raise RuntimeError("Не удалось создать PDF")
        try:
            for index in range(max(1, document.pageCount())):
                if should_cancel():
                    raise InterruptedError("Конвертация отменена")
                if index and not writer.newPage():
                    raise RuntimeError("Не удалось создать страницу PDF")
                if layout:
                    font = painter.font()
                    font.setPointSize(9)
                    painter.setFont(font)
                    for line, text in enumerate(layout.header, start=1):
                        painter.drawText(QPointF(left, layout.header_distance + line * 10), text)
                    for line, text in enumerate(reversed(layout.footer)):
                        painter.drawText(QPointF(left, size[1] - layout.footer_distance - line * 10), text)
                context = QAbstractTextDocumentLayout.PaintContext()
                context.clip = QRectF(0, index * height, width, height)
                context.palette.setColor(QPalette.ColorRole.Text, QColor("black"))
                painter.save()
                painter.setClipRect(QRectF(left, top, width, height))
                painter.translate(left, top - index * height)
                document.documentLayout().draw(painter, context)
                painter.restore()
        finally:
            painter.end()
        del writer
        if should_cancel():
            raise InterruptedError("Конвертация отменена")
        with open(temporary, "rb") as stream:
            if stream.read(5) != b"%PDF-":
                raise RuntimeError("Не удалось создать PDF")
