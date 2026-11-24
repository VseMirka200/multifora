"""Миниатюры страниц перед объединением документов."""

from pathlib import Path
from tempfile import TemporaryDirectory
import zipfile

from PySide6.QtCore import QByteArray, QEasingCurve, QItemSelectionModel, QMimeData, QSize, Qt, QThread, Signal, QVariantAnimation
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
                    source = Path(path)
                    if source.suffix.lower() == ".docx" and not zipfile.is_zipfile(source):
                        raise ValueError(
                            f"{source.name}: файл с расширением DOCX повреждён или имеет неверное расширение. "
                            "Ожидается настоящий документ DOCX."
                        )
                    try:
                        pdf = paged_source(path, staging, index, self.isInterruptionRequested)
                        for number, (width, height, pixels) in enumerate(page_thumbnails(pdf, self.isInterruptionRequested)):
                            image = QImage(pixels, width, height, width * 3, QImage.Format.Format_RGB888)
                            self.thumbnail.emit(index, number, image.copy())
                    except InterruptedError:
                        raise
                    except Exception as error:
                        raise RuntimeError(f"Не удалось обработать «{source.name}»: {error}") from error
        except InterruptedError:
            pass
        except Exception as error:
            self.failed.emit(str(error))


class PageList(QListWidget):
    """Список страниц с предсказуемой перестановкой drag-and-drop в сетке."""

    order_changed = Signal()
    _PAGE_MIME = "application/x-multifora-page-index"

    def __init__(self, parent):
        super().__init__(parent)
        self.setViewMode(QListWidget.ViewMode.IconMode)
        self.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.setFlow(QListWidget.Flow.LeftToRight)
        self.setWrapping(True)
        self.setMovement(QListWidget.Movement.Snap)
        self.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.viewport().setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDragDropMode(QListWidget.DragDropMode.DragDrop)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setDragDropOverwriteMode(False)
        self.setIconSize(QSize(140, 140))
        self.setGridSize(QSize(158, 172))
        self._move_animation = None

    def clear(self):
        if self._move_animation is not None:
            self._move_animation.stop()
            self._move_animation.deleteLater()
            self._move_animation = None
        super().clear()

    def move_current(self, row):
        current = self.currentRow()
        if current < 0 or not 0 <= row < self.count() or row == current:
            return
        self._move_page(current, row)

    def _move_page(self, source, destination):
        if self._move_animation is not None:
            self._move_animation.stop()
            self._move_animation.deleteLater()
            self._move_animation = None
            self.doItemsLayout()
        pages = [self.item(i) for i in range(self.count())]
        positions = {id(page): self.visualItemRect(page).topLeft() for page in pages}
        selected = [page for page in pages if page.isSelected()]
        item = self.takeItem(source)
        self.insertItem(destination, item)
        self.setCurrentItem(item, QItemSelectionModel.SelectionFlag.NoUpdate)
        for page in selected:
            page.setSelected(True)
        self.doItemsLayout()
        self.order_changed.emit()
        ends = [(self.item(i), self.visualItemRect(self.item(i)).topLeft())
                for i in range(self.count())]
        moves = [(page, positions[id(page)], end) for page, end in ends
                 if positions[id(page)] != end]
        if not moves:
            return
        animation = QVariantAnimation(self)
        animation.setDuration(220)
        animation.setStartValue(0.0)
        animation.setEndValue(1.0)
        animation.setEasingCurve(QEasingCurve.Type.OutCubic)

        def update(value):
            for page, start, end in moves:
                index = self.indexFromItem(page)
                if index.isValid():
                    self.setPositionForIndex(start + (end - start) * value, index)

        def finish():
            self._move_animation = None
            self.doItemsLayout()
            animation.deleteLater()

        animation.valueChanged.connect(update)
        animation.finished.connect(finish)
        self._move_animation = animation
        update(0.0)
        animation.start()

    def startDrag(self, supported_actions):
        row = self.currentRow()
        if row < 0:
            return
        mime = QMimeData()
        mime.setData(self._PAGE_MIME, QByteArray(str(row).encode("ascii")))
        drag = QDrag(self)
        drag.setMimeData(mime)
        item = self.item(row)
        if item is not None and not item.icon().isNull():
            drag.setPixmap(item.icon().pixmap(96, 96))
            drag.setHotSpot(drag.pixmap().rect().center())
        self._drag_item = item
        self._drag_original_row = row
        result = drag.exec(Qt.DropAction.MoveAction)
        if result != Qt.DropAction.MoveAction and self._drag_item is not None:
            current = self.row(self._drag_item)
            if current >= 0 and current != self._drag_original_row:
                self._move_page(current, self._drag_original_row)
        self._drag_item = None

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat(self._PAGE_MIME):
            event.setDropAction(Qt.DropAction.MoveAction)
            event.accept()
            return
        event.ignore()

    def dragMoveEvent(self, event):
        if event.mimeData().hasFormat(self._PAGE_MIME):
            if event.source() is self and getattr(self, "_drag_item", None) is not None:
                self._preview_drop(event.position().toPoint())
            event.setDropAction(Qt.DropAction.MoveAction)
            event.accept()
            return
        event.ignore()

    def dropEvent(self, event):
        if event.source() is not self or not event.mimeData().hasFormat(self._PAGE_MIME):
            event.ignore()
            return
        if getattr(self, "_drag_item", None) is None:
            event.ignore()
            return
        self._preview_drop(event.position().toPoint())
        event.setDropAction(Qt.DropAction.MoveAction)
        event.accept()

    def _preview_drop(self, pos):
        source_row = self.row(self._drag_item)
        if source_row < 0:
            return

        target_row = self.indexAt(pos).row()
        if target_row < 0:
            # При отпускании в промежутке между элементами выбираем ближайшую
            # ячейку; за последним рядом — конец списка.
            rects = [self.visualItemRect(self.item(i)) for i in range(self.count())]
            if not rects or pos.y() > max(rect.bottom() for rect in rects):
                target_row = self.count() - 1
                insert_after = True
            else:
                target_row = min(
                    range(self.count()),
                    key=lambda i: (self.visualItemRect(self.item(i)).center() - pos).manhattanLength(),
                )
                rect = self.visualItemRect(self.item(target_row))
                insert_after = pos.y() > rect.center().y() or (
                    abs(pos.y() - rect.center().y()) <= rect.height() // 3
                    and pos.x() > rect.center().x()
                )
        else:
            rect = self.visualItemRect(self.item(target_row))
            # Сетка читается слева направо, затем сверху вниз.
            insert_after = pos.y() > rect.center().y() or (
                abs(pos.y() - rect.center().y()) <= rect.height() // 3
                and pos.x() > rect.center().x()
            )

        destination = target_row + (1 if insert_after else 0)
        if destination > source_row:
            destination -= 1
        destination = max(0, min(destination, self.count() - 1))
        if destination != source_row:
            self._move_page(source_row, destination)


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
        layout.setContentsMargins(0, 0, 0, 0)
        self.hint = QLabel("Добавьте PDF или DOCX для объединения")
        self.hint.setWordWrap(True)
        self.hint.hide()
        self.pages = PageList(self)
        self.pages.setStyleSheet("QListWidget { border: none; }")
        self.pages.setToolTip("\u0412\u044b\u0434\u0435\u043b\u0438\u0442\u0435 \u043d\u0435\u0441\u043a\u043e\u043b\u044c\u043a\u043e \u0441\u0442\u0440\u0430\u043d\u0438\u0446 \u0441 Ctrl \u0438\u043b\u0438 Shift, \u0447\u0442\u043e\u0431\u044b \u043e\u0431\u044a\u0435\u0434\u0438\u043d\u0438\u0442\u044c \u0442\u043e\u043b\u044c\u043a\u043e \u0438\u0445.")
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

        # Не запускаем конвертацию для произвольных файлов из общего списка.
        # Вкладка объединения поддерживает только однородные наборы PDF или DOCX.
        suffixes = {Path(file.path).suffix.lower() for file in files}
        if len(suffixes) != 1 or not suffixes.issubset({".pdf", ".docx"}):
            names = ", ".join(Path(file.path).name for file in files[:3])
            if len(files) > 3:
                names += f" и ещё {len(files) - 3}"
            self.hint.setText(
                "Для объединения выберите минимум два документа одного формата: PDF или DOCX. "
                f"Текущий набор не подходит: {names}."
            )
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
                self.hint.hide()
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
        selected = self.pages.selectedItems()
        use_selection = len(selected) >= 2
        return tuple(
            tuple(self.pages.item(i).data(Qt.ItemDataRole.UserRole))
            for i in range(self.pages.count())
            if not use_selection or self.pages.item(i).isSelected()
        )


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
    cancel = QPushButton("Отмена", dialog)
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
