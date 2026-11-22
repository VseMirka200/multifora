"""Миниатюры страниц перед объединением документов."""

from pathlib import Path
from tempfile import TemporaryDirectory

from PySide6.QtCore import QSize, Qt, QThread, Signal
from PySide6.QtGui import QDrag, QIcon, QImage, QPixmap
from PySide6.QtWidgets import (
    QDialog, QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QPushButton, QVBoxLayout,
)

from app.ui.ui_components import setup_standard_dialog, setup_standard_primary_button, setup_standard_danger_button
from core.merge_documents import paged_source


class ThumbnailLoader(QThread):
    thumbnail = Signal(int, int, QImage)
    failed = Signal(str)

    def __init__(self, paths, parent):
        super().__init__(parent)
        self.paths = paths

    def run(self):
        try:
            from core.pdf_engine.render import page_thumbnails

            with TemporaryDirectory() as staging:
                for index, path in enumerate(self.paths):
                    if self.isInterruptionRequested():
                        return
                    pdf = paged_source(path, staging, index, self.isInterruptionRequested)
                    for number, (width, height, pixels) in enumerate(page_thumbnails(pdf, self.isInterruptionRequested)):
                        image = QImage(pixels, width, height, width * 3, QImage.Format.Format_RGB888)
                        self.thumbnail.emit(index, number, image.copy())
        except InterruptedError:
            pass
        except Exception as error:
            self.failed.emit(str(error))


class PageList(QListWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.setViewMode(QListWidget.ViewMode.IconMode)
        self.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.setMovement(QListWidget.Movement.Snap)
        self.setDragDropMode(QListWidget.DragDropMode.InternalMove)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setIconSize(QSize(140, 140))
        self.setGridSize(QSize(158, 172))

    def startDrag(self, supported_actions):
        item = self.currentItem()
        if item is None:
            return
        drag = QDrag(self)
        drag.setMimeData(self.model().mimeData([self.currentIndex()]))
        drag.setPixmap(item.icon().pixmap(88, 88))
        drag.exec(Qt.DropAction.MoveAction)

    def dropEvent(self, event):
        if event.source() is not self:
            event.ignore()
            return
        target = self.indexAt(event.position().toPoint())
        row = target.row() if target.isValid() else self.count() - 1
        item = self.takeItem(self.currentRow())
        self.insertItem(row, item)
        self.setCurrentItem(item)
        self.doItemsLayout()
        event.acceptProposedAction()


def choose_merge_pages(parent, files, source_format):
    dialog = QDialog(parent)
    setup_standard_dialog(dialog, title="Порядок страниц", width=760, height=510)
    layout = QVBoxLayout(dialog)
    hint = QLabel("Загрузка миниатюр…")
    hint.setWordWrap(True)
    layout.addWidget(hint)
    pages = PageList(dialog)
    layout.addWidget(pages)
    buttons = QHBoxLayout()
    cancel = QPushButton("Отмена")
    setup_standard_danger_button(cancel)
    cancel.clicked.connect(dialog.reject)
    buttons.addWidget(cancel)
    proceed = QPushButton("Продолжить")
    setup_standard_primary_button(proceed)
    proceed.clicked.connect(dialog.accept)
    proceed.setEnabled(False)
    buttons.addWidget(proceed)
    layout.addLayout(buttons)
    paths = [file.path for file in files]
    original = []
    loader = ThumbnailLoader(paths, dialog)

    def append(source, page, image):
        key = (source, page)
        original.append(key)
        item = QListWidgetItem(QIcon(QPixmap.fromImage(image)), f"{Path(paths[source]).name} · {page + 1}")
        item.setToolTip(f"{paths[source]}\nСтраница {page + 1}")
        item.setData(Qt.ItemDataRole.UserRole, key)
        pages.addItem(item)

    def ready():
        if pages.isEnabled():
            message = "Перетащите страницы в нужном порядке."
            if source_format == "docx":
                message += " При перестановке отдельных страниц результат сохранится в PDF."
            hint.setText(message)
        proceed.setEnabled(True)

    def failed(message):
        pages.clear()
        pages.setEnabled(False)
        hint.setText(f"Не удалось загрузить миниатюры: {message}\nМожно объединить документы целиком в порядке очереди.")

    loader.thumbnail.connect(append, Qt.ConnectionType.QueuedConnection)
    loader.failed.connect(failed, Qt.ConnectionType.QueuedConnection)
    loader.finished.connect(ready, Qt.ConnectionType.QueuedConnection)
    loader.start()
    try:
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return None
        order = tuple(tuple(pages.item(i).data(Qt.ItemDataRole.UserRole)) for i in range(pages.count()))
        return order if order != tuple(original) else ()
    finally:
        loader.requestInterruption()
        loader.wait()
        dialog.deleteLater()
