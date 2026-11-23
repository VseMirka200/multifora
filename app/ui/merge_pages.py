"""Миниатюры страниц перед объединением документов."""

from pathlib import Path
from tempfile import TemporaryDirectory

from PySide6.QtCore import QSize, Qt, QThread, Signal
from PySide6.QtGui import QDrag, QIcon, QImage, QPixmap
from PySide6.QtWidgets import (
    QDialog, QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QPushButton, QVBoxLayout, QWidget,
)

from app.ui.ui_components import setup_standard_dialog, setup_standard_primary_button, setup_standard_secondary_button
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
    order_changed = Signal()

    def __init__(self, parent):
        super().__init__(parent)
        self.setViewMode(QListWidget.ViewMode.IconMode)
        self.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.setMovement(QListWidget.Movement.Snap)
        self.setDragDropMode(QListWidget.DragDropMode.InternalMove)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setIconSize(QSize(140, 140))
        self.setGridSize(QSize(158, 172))

    def move_current(self, row):
        current = self.currentRow()
        if current < 0 or not 0 <= row < self.count() or row == current:
            return
        item = self.takeItem(current)
        self.insertItem(row, item)
        self.setCurrentItem(item)
        self.doItemsLayout()
        self.order_changed.emit()

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
        self.move_current(row)
        event.acceptProposedAction()


class MergePagesPanel(QWidget):
    ready_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.files = []
        self.signature = None
        self.loader = None
        self.ready = False
        self.generation = 0
        layout = QVBoxLayout(self)
        self.hint = QLabel("Добавьте PDF или DOCX для объединения")
        self.hint.setWordWrap(True)
        layout.addWidget(self.hint)
        self.pages = PageList(self)
        layout.addWidget(self.pages, 1)
        self.pages.order_changed.connect(self.renumber)

    def stop(self):
        if self.loader is not None:
            self.loader.requestInterruption()
            self.loader.wait()

    def set_files(self, files):
        signature = tuple((f.path, Path(f.path).stat().st_mtime_ns if Path(f.path).exists() else None) for f in files)
        if signature == self.signature:
            return
        self.generation += 1
        generation = self.generation
        self.stop()
        self.signature = signature
        self.files = list(files)
        self.pages.clear()
        self.ready = False
        self.ready_changed.emit()
        if not files:
            self.hint.setText("Добавьте PDF или DOCX для объединения")
            return
        self.hint.setText("Загрузка всех страниц…")
        self.loader = ThumbnailLoader([f.path for f in files], self)
        failed = []

        def append(source, page, image):
            if generation != self.generation:
                return
            item = QListWidgetItem(QIcon(QPixmap.fromImage(image)), "")
            item.setData(Qt.ItemDataRole.UserRole, (source, page))
            item.setToolTip(f"{self.files[source].path}\nСтраница {page + 1}")
            self.pages.addItem(item)
            self.renumber()

        def error(message):
            if generation == self.generation:
                failed.append(message)
                self.hint.setText(f"Не удалось загрузить страницы: {message}")

        def finished():
            if generation != self.generation:
                return
            self.ready = not failed and self.pages.count() > 0
            if self.ready:
                self.hint.setText("Перетаскивайте страницы. Порядок объединения: слева направо, сверху вниз. Перестановка страниц DOCX сохраняется в PDF.")
            self.ready_changed.emit()

        self.loader.thumbnail.connect(append, Qt.ConnectionType.QueuedConnection)
        self.loader.failed.connect(error, Qt.ConnectionType.QueuedConnection)
        self.loader.finished.connect(finished, Qt.ConnectionType.QueuedConnection)
        self.loader.start()

    def renumber(self):
        for i in range(self.pages.count()):
            item = self.pages.item(i)
            source, page = item.data(Qt.ItemDataRole.UserRole)
            item.setText(f"{i + 1}. {self.files[source].name}\nСтраница {page + 1}")

    def page_order(self):
        return tuple(tuple(self.pages.item(i).data(Qt.ItemDataRole.UserRole)) for i in range(self.pages.count()))


def choose_merge_pages(parent, files, source_format):
    dialog = QDialog(parent)
    setup_standard_dialog(dialog, title="Порядок страниц", width=760, height=510)
    layout = QVBoxLayout(dialog)
    hint = QLabel("Загрузка миниатюр…")
    hint.setWordWrap(True)
    layout.addWidget(hint)
    pages = PageList(dialog)
    layout.addWidget(pages)
    controls = QHBoxLayout()
    for label, offset in (("← Раньше", -1), ("Позже →", 1)):
        button = QPushButton(label)
        button.clicked.connect(lambda checked=False, step=offset: pages.move_current(pages.currentRow() + step))
        controls.addWidget(button)
    layout.addLayout(controls)
    buttons = QHBoxLayout()
    cancel = QPushButton("Отмена")
    setup_standard_secondary_button(cancel)
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

    def renumber():
        for position in range(pages.count()):
            item = pages.item(position)
            source, page = item.data(Qt.ItemDataRole.UserRole)
            item.setText(f"{position + 1}. {Path(paths[source]).name}\nСтраница {page + 1}")

    pages.order_changed.connect(renumber)

    def append(source, page, image):
        key = (source, page)
        original.append(key)
        item = QListWidgetItem(QIcon(QPixmap.fromImage(image)), f"{Path(paths[source]).name} · {page + 1}")
        item.setToolTip(f"{paths[source]}\nСтраница {page + 1}")
        item.setData(Qt.ItemDataRole.UserRole, key)
        pages.addItem(item)
        renumber()

    def ready():
        if pages.isEnabled():
            message = "Перетащите страницы или используйте кнопки. Порядок результата: слева направо, сверху вниз."
            if source_format == "docx":
                message += " При перестановке отдельных страниц результат сохранится в PDF."
            hint.setText(message)
        proceed.setEnabled(pages.isEnabled() and pages.count() > 0)

    def failed(message):
        pages.clear()
        pages.setEnabled(False)
        hint.setText(f"Не удалось загрузить миниатюры: {message}\nЗакройте окно и проверьте исходные документы.")

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
