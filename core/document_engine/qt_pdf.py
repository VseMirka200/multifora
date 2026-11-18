"""Render documents requiring Qt's system font selection and text shaping."""

from pathlib import Path

from lxml import etree
from PySide6.QtCore import QMarginsF, QSizeF, QUrl
from PySide6.QtGui import QFontDatabase, QGuiApplication, QImage, QPageLayout, QPageSize, QPdfWriter, QTextDocument

from core.document_engine.rtf_export import image_data
from core.workers.atomic_output import atomic_output_path


class _LocalDocument(QTextDocument):
    def loadResource(self, resource_type, name):
        return None  # All embedded images are registered explicitly.


def write_pdf(body, source, destination, should_cancel):
    if QGuiApplication.instance() is None:
        raise RuntimeError("Для подбора шрифтов PDF требуется запущенное приложение Мультифора")
    if not QFontDatabase.families():
        raise RuntimeError("Системные шрифты для вывода PDF недоступны")
    if should_cancel():
        raise InterruptedError("Конвертация отменена")
    document = _LocalDocument()
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
    document.setHtml(etree.tostring(body, method="html", encoding="unicode"))
    with atomic_output_path(destination) as temporary:
        writer = QPdfWriter(temporary)
        writer.setResolution(72)
        writer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
        writer.setPageMargins(QMarginsF(19, 19, 19, 19), QPageLayout.Unit.Millimeter)
        document.setPageSize(QSizeF(writer.pageLayout().paintRectPixels(72).size()))
        document.print_(writer)
        del writer
        if should_cancel():
            raise InterruptedError("Конвертация отменена")
        with open(temporary, "rb") as stream:
            if stream.read(5) != b"%PDF-":
                raise RuntimeError("Не удалось создать PDF")
