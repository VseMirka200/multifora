"""Модель, делегат и виджет таблицы файлов."""

import os
from dataclasses import dataclass
from weakref import WeakKeyDictionary

from PySide6.QtCore import (
    QAbstractTableModel,
    QItemSelectionModel,
    QMimeData,
    QModelIndex,
    QRectF,
    QSize,
    Qt,
    QTimer,
    Signal,
)
from PySide6.QtGui import (
    QCursor,
    QDrag,
    QFontMetrics,
    QKeySequence,
    QPainterPath,
    QRegion,
)
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QHeaderView,
    QStyle,
    QStyledItemDelegate,
    QStyleOptionButton,
    QStyleOptionViewItem,
    QTableView,
)

from app.ui.checkbox_style import paint_checkbox
from app.ui.ui_components import apply_standard_field_style
from app.ui.ui_styles import (
    FILE_LIST_DRAG_ACTIVE_STYLE,
    FILE_LIST_HEADER_STYLE,
    FILE_PANEL_RADIUS,
)
from core.file_models import FileItem, file_item_source_folder, file_item_type_label


class FileListItemAdapter:
    def __init__(self, view, index: QModelIndex):
        self._view = view
        self._index = index

    def data(self, role):
        return self._view.model().data(self._index, role)


def selected_file_items(list_widget, *, files_only: bool = False) -> list:
    """Извлекает отмеченные файлы из совместимого списка."""
    if list_widget is None:
        return []
    result = []
    for item in list_widget.selectedItems():
        file_item = item.data(Qt.ItemDataRole.UserRole)
        if file_item is None:
            continue
        if files_only and not getattr(file_item, "is_file", False):
            continue
        result.append(file_item)
    return result


def operation_file_items(files, *, files_only=False, visible_files=None, is_checked=None):
    """Отметки задают область операции, фильтры ограничивают видимую очередь."""
    files = list(files)
    is_checked = is_checked or (lambda item: getattr(item, "checked", False))
    marked = any(is_checked(item) for item in files)
    candidates = files if visible_files is None else visible_files
    return [
        item
        for item in candidates
        if (not marked or is_checked(item)) and (not files_only or getattr(item, "is_file", False))
    ]


@dataclass(slots=True)
class FilePreview:
    preview_name: str
    preview_folder: str
    conversion_target_format: str = ""
    checked: bool = False
    rename_status: str = ""


class FileListModel(QAbstractTableModel):
    COLUMN_OLD_NAME = 0
    COLUMN_NEW_NAME = 1
    COLUMN_TYPE = 2
    COLUMN_PATH = 3
    COLUMN_CHECK = 4
    COLUMN_ORDER = 5
    # Совместимость с кодом, которому нужна любая колонка для выбора строки.
    COLUMN_NAME = COLUMN_OLD_NAME
    HEADERS = ("Старое имя", "Новое имя", "Тип файла", "Исходная папка", "", "№")

    # Хранит общий порядок файлов, чтобы выделение и перетаскивание не расходились с UI.
    def __init__(self, parent=None):
        super().__init__(parent)
        self._previews: WeakKeyDictionary[FileItem, FilePreview] = WeakKeyDictionary()
        self._files = []
        self._folder_header = self.HEADERS[self.COLUMN_PATH]
        self.compression_sizes_visible = False
        self.conversion_formats_visible = False
        self.merge_order_visible = False
        self.full_path_tooltip = False

    def preview_for(self, item):
        if not isinstance(item, FileItem):
            # Существующие адаптеры таблицы могут предоставлять атрибуты предпросмотра напрямую.
            return item
        preview = self._previews.get(item)
        if preview is None:
            preview = FilePreview(item.name, item.folder)
            self._previews[item] = preview
        return preview

    def is_checked(self, item):
        return bool(getattr(self.preview_for(item), "checked", False))

    def set_checked(self, item, checked):
        state = self.preview_for(item)
        if getattr(state, "checked", False) == checked:
            return False
        state.checked = checked
        return True

    def set_conversion_formats_visible(self, visible: bool) -> None:
        if self.conversion_formats_visible == visible:
            return
        self.conversion_formats_visible = visible
        self.headerDataChanged.emit(Qt.Orientation.Horizontal, self.COLUMN_OLD_NAME, self.COLUMN_TYPE)
        self.refresh()

    def _conversion_type_label(self, file_item) -> str:
        source = file_item_type_label(file_item)
        if not getattr(file_item, "is_file", False):
            return source
        target = getattr(self.preview_for(file_item), "conversion_target_format", "") or "—"
        return f"{source} → {target}"

    def set_compression_sizes_visible(self, visible: bool) -> None:
        if self.compression_sizes_visible == visible:
            return
        self.compression_sizes_visible = visible
        self.headerDataChanged.emit(Qt.Orientation.Horizontal, self.COLUMN_OLD_NAME, self.COLUMN_TYPE)
        self.refresh()

    def set_merge_order_visible(self, visible: bool) -> None:
        if self.merge_order_visible != visible:
            self.merge_order_visible = visible
            self.headerDataChanged.emit(Qt.Orientation.Horizontal, self.COLUMN_OLD_NAME, self.COLUMN_OLD_NAME)

    @staticmethod
    def _format_file_size(size: int) -> str:
        value = max(0, int(size))
        if value < 1024:
            return f"{value} Б"
        for unit in ("КБ", "МБ", "ГБ", "ТБ"):
            value /= 1024
            if value < 1024 or unit == "ТБ":
                return f"{value:.1f} {unit}".replace(".", ",")
        return ""

    def _compression_size_label(self, file_item) -> str:
        if not getattr(file_item, "is_file", False):
            return "—"
        return self._format_file_size(getattr(file_item, "size", 0))

    def set_folder_header(self, text: str) -> None:
        """Меняет заголовок папки в соответствии с предпросмотром операции."""
        header = str(text or self.HEADERS[self.COLUMN_PATH])
        if header == self._folder_header:
            return
        self._folder_header = header
        self.headerDataChanged.emit(
            Qt.Orientation.Horizontal, self.COLUMN_PATH, self.COLUMN_PATH
        )

    def displayed_folder(self, item):
        source = file_item_source_folder(item)
        if self._folder_header == self.HEADERS[self.COLUMN_PATH]:
            return source
        return getattr(self.preview_for(item), "preview_folder", "") or source

    @staticmethod
    def _original_display_name(file_item) -> str:
        return file_item.name

    def rowCount(self, parent=QModelIndex()):
        if parent.isValid():
            return 0
        return len(self._files)

    def columnCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.HEADERS)

    def headerData(
        self, section, orientation, role=Qt.ItemDataRole.DisplayRole
    ):
        if (
            orientation == Qt.Orientation.Horizontal
            and section == self.COLUMN_CHECK
            and role == Qt.ItemDataRole.ToolTipRole
        ):
            return "В работу: отметить все файлы текущего списка или снять отметки"
        if orientation == Qt.Orientation.Horizontal and section == self.COLUMN_TYPE and self.compression_sizes_visible:
            if role == Qt.ItemDataRole.DisplayRole:
                return "Размер"
            if role == Qt.ItemDataRole.ToolTipRole:
                return "Текущий размер файла. Итоговый размер появится в сводке сжатия."
        if orientation == Qt.Orientation.Horizontal and section == self.COLUMN_TYPE and self.conversion_formats_visible:
            if role == Qt.ItemDataRole.DisplayRole:
                return "Формат → результат"
            if role == Qt.ItemDataRole.ToolTipRole:
                return "Исходный формат и формат результата. Сортировка по исходному типу файла."
        if (
            orientation == Qt.Orientation.Horizontal
            and role == Qt.ItemDataRole.DisplayRole
            and 0 <= section < len(self.HEADERS)
        ):
            if section == self.COLUMN_OLD_NAME and (
                self.compression_sizes_visible or self.conversion_formats_visible or self.merge_order_visible
            ):
                return "Имя файла"
            if section == self.COLUMN_PATH:
                return self._folder_header
            return self.HEADERS[section]
        return super().headerData(section, orientation, role)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or index.row() >= len(self._files):
            return None
        file_item = self._files[index.row()]
        if index.column() == self.COLUMN_CHECK:
            if role == Qt.ItemDataRole.CheckStateRole:
                return Qt.CheckState.Checked if self.is_checked(file_item) else Qt.CheckState.Unchecked
            if role == Qt.ItemDataRole.ToolTipRole:
                return (
                    "Зажмите ЛКМ и проведите вверх или вниз, чтобы поставить или снять галочки.\n"
                    "Без отметок обрабатываются все файлы текущего списка."
                )
        if role == Qt.ItemDataRole.DisplayRole:
            if index.column() == self.COLUMN_ORDER:
                return index.row() + 1
            if index.column() == self.COLUMN_OLD_NAME:
                return self._original_display_name(file_item)
            if index.column() == self.COLUMN_NEW_NAME:
                preview = self.preview_for(file_item)
                name = getattr(preview, "preview_name", "") or self._original_display_name(file_item)
                status = getattr(preview, "rename_status", "")
                return f"{name} · {status}" if status else name
            if index.column() == self.COLUMN_TYPE:
                if self.compression_sizes_visible:
                    return self._compression_size_label(file_item)
                if self.conversion_formats_visible:
                    return self._conversion_type_label(file_item)
                return file_item_type_label(file_item)
            if index.column() == self.COLUMN_PATH:
                return str(self.displayed_folder(file_item))
        if role == Qt.ItemDataRole.ToolTipRole:
            if index.column() == self.COLUMN_TYPE and self.conversion_formats_visible:
                return (
                    f"{self._conversion_type_label(file_item)}\n"
                    "Исходный формат → формат результата. Прочерк означает, что файл не участвует в конвертации."
                )
            if index.column() == self.COLUMN_TYPE and self.compression_sizes_visible:
                return (
                    f"{self._compression_size_label(file_item)}\n"
                    "Оценка зависит от выбранного режима и содержимого файла. "
                    "Точный размер будет известен после сжатия.\n"
                    "Прочерк означает, что файл не участвует в сжатии."
                )
            if index.column() == self.COLUMN_OLD_NAME:
                path = getattr(file_item, "path", "") if self.full_path_tooltip else ""
                return path or self._original_display_name(file_item)
            if index.column() == self.COLUMN_NEW_NAME:
                return self.data(index, Qt.ItemDataRole.DisplayRole)
            if index.column() == self.COLUMN_PATH:
                preview_folder = getattr(self.preview_for(file_item), "preview_folder", "")
                folder = self.displayed_folder(file_item)
                if preview_folder and preview_folder != folder:
                    return f"{folder}\nПапка результата: {preview_folder}"
                return str(preview_folder or getattr(file_item, "path", "") or folder)
        if role == Qt.ItemDataRole.SizeHintRole:
            metrics = QFontMetrics(QApplication.font())
            text = self.data(index, Qt.ItemDataRole.DisplayRole) or ""
            width = metrics.horizontalAdvance(str(text)) + 12
            return QSize(width, metrics.height() + 8)
        if role == Qt.ItemDataRole.UserRole:
            return file_item
        return None

    def setData(self, index, value, role=Qt.ItemDataRole.EditRole):
        if (
            not index.isValid()
            or not self._files
            or index.column() != self.COLUMN_CHECK
            or role != Qt.ItemDataRole.CheckStateRole
        ):
            return False
        checked = value in (Qt.CheckState.Checked, Qt.CheckState.Checked.value)
        item = self._files[index.row()]
        if not self.set_checked(item, checked):
            return False
        self.dataChanged.emit(index, index, [Qt.ItemDataRole.CheckStateRole])
        return True

    def flags(self, index):
        if not self._files or not index.isValid():
            return Qt.ItemFlag.ItemIsEnabled
        flags = (
            Qt.ItemFlag.ItemIsEnabled
            | Qt.ItemFlag.ItemIsDragEnabled | Qt.ItemFlag.ItemIsDropEnabled
        )
        if index.column() == self.COLUMN_CHECK:
            flags |= Qt.ItemFlag.ItemIsUserCheckable
        return flags

    def supportedDropActions(self):
        return Qt.DropAction.MoveAction

    def supportedDragActions(self):
        return Qt.DropAction.MoveAction

    def set_files(self, files: list):
        self.beginResetModel()
        self._files = list(files)
        self.endResetModel()

    def clear(self):
        self.set_files([])

    def files(self):
        return list(self._files)

    def moveRows(
        self,
        sourceParent,
        sourceRow,
        count,
        destinationParent,
        destinationChild,
    ):
        if count <= 0:
            return False
        if sourceRow < 0 or (sourceRow + count) > len(self._files):
            return False
        if destinationChild < 0 or destinationChild > len(self._files):
            return False
        if (
            destinationChild >= sourceRow
            and destinationChild <= sourceRow + count
        ):
            return False

        self.beginMoveRows(
            sourceParent,
            sourceRow,
            sourceRow + count - 1,
            destinationParent,
            destinationChild,
        )
        rows = self._files[sourceRow : sourceRow + count]
        del self._files[sourceRow : sourceRow + count]
        if destinationChild > sourceRow:
            destinationChild -= count
        for i, item in enumerate(rows):
            self._files.insert(destinationChild + i, item)
        self.endMoveRows()
        if self.merge_order_visible:
            first, last = sorted((sourceRow, destinationChild))
            self.dataChanged.emit(self.index(first, self.COLUMN_ORDER),
                                  self.index(last + count - 1, self.COLUMN_ORDER),
                                  [Qt.ItemDataRole.DisplayRole])
        return True

    def refresh(self):
        if not self._files:
            return
        top_left = self.index(0, 0)
        bottom_right = self.index(len(self._files) - 1, self.columnCount() - 1)
        self.dataChanged.emit(
            top_left,
            bottom_right,
            [
                Qt.ItemDataRole.DisplayRole,
                Qt.ItemDataRole.SizeHintRole,
                Qt.ItemDataRole.ToolTipRole,
            ],
        )


class FileListItemDelegate(QStyledItemDelegate):
    def __init__(self, parent=None, horizontal_padding: int = 6):
        super().__init__(parent)
        self._horizontal_padding = max(0, int(horizontal_padding))

    def sizeHint(self, option, index):
        hint = super().sizeHint(option, index)
        hint.setHeight(
            max(hint.height(), QFontMetrics(option.font).height() + 8)
        )
        return hint

    def paint(self, painter, option, index):
        view_option = QStyleOptionViewItem(option)
        self.initStyleOption(view_option, index)
        if index.column() != index.model().COLUMN_CHECK:
            view_option.state &= ~QStyle.StateFlag.State_HasFocus
        checked = index.data(Qt.ItemDataRole.CheckStateRole)
        if checked is not None:
            view_option.features &= ~QStyleOptionViewItem.ViewItemFeature.HasCheckIndicator
            widget = view_option.widget
            style = widget.style() if widget is not None else QApplication.style()
            style.drawControl(QStyle.ControlElement.CE_ItemViewItem, view_option, painter, widget)
            view_option.state &= ~(QStyle.StateFlag.State_On | QStyle.StateFlag.State_Off)
            view_option.state |= (
                QStyle.StateFlag.State_On if checked == Qt.CheckState.Checked
                else QStyle.StateFlag.State_Off
            )
            paint_checkbox(painter, view_option)
            return
        available_width = max(
            0, view_option.rect.width() - 2 * self._horizontal_padding
        )
        view_option.text = view_option.fontMetrics.elidedText(
            view_option.text,
            Qt.TextElideMode.ElideRight,
            available_width,
        )
        super().paint(painter, view_option, index)


class FileListWidget(QTableView):
    _COLUMN_RESIZE_PRECISION = 100
    _CHECK_COLUMN_WIDTH = 36
    _NAME_COLUMN_MAX_WIDTH = 220

    filesDropped = Signal(list)
    itemDoubleClicked = Signal(object)
    itemSelectionChanged = Signal()
    orderChanged = Signal()
    deleteRequested = Signal()
    openRequested = Signal()
    copyRequested = Signal()
    renameRequested = Signal()

    def __init__(self):
        super().__init__()

        self.setModel(FileListModel(self))
        self.setItemDelegate(FileListItemDelegate(self))
        self.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.keyboard_reordering_enabled = False
        self.setAlternatingRowColors(True)
        self.setWordWrap(False)
        self.setTextElideMode(Qt.TextElideMode.ElideRight)
        self.setShowGrid(False)
        self.verticalHeader().hide()
        header = self.horizontalHeader()
        header.setStyleSheet(FILE_LIST_HEADER_STYLE)
        # Номера остальных колонок сохраняются для существующих настроек сортировки.
        header.moveSection(self.model().COLUMN_CHECK, 0)
        header.moveSection(header.visualIndex(self.model().COLUMN_ORDER), 1)
        self.setColumnHidden(self.model().COLUMN_ORDER, True)
        header.setStretchLastSection(True)
        # Измерение каждой ячейки заметно замедляет сброс модели для больших
        # пакетов. Репрезентативная выборка сохраняет полезную автоширину и
        # ограничивает работу при замене видимой модели фильтром.
        header.setResizeContentsPrecision(self._COLUMN_RESIZE_PRECISION)
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(self.model().COLUMN_CHECK, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(self.model().COLUMN_CHECK, self._CHECK_COLUMN_WIDTH)
        header.setSectionResizeMode(self.model().COLUMN_ORDER, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(self.model().COLUMN_ORDER, 60)
        self.check_all_checkbox = QCheckBox(header.viewport())
        self.check_all_checkbox.setObjectName("check_all_files")
        self.check_all_checkbox.setAccessibleName("Отметить видимые файлы")
        self.check_all_checkbox.setToolTip(
            "Отметить видимые файлы (Ctrl+A) или снять их отметки"
        )
        self.check_all_checkbox.setFixedSize(24, 24)
        self.check_all_checkbox.clicked.connect(self._set_checks)
        header.geometriesChanged.connect(self._position_header_checkbox)
        header.sectionResized.connect(self._position_header_checkbox)
        header.sectionMoved.connect(self._position_header_checkbox)
        self.horizontalScrollBar().valueChanged.connect(self._position_header_checkbox)
        self.itemSelectionChanged.connect(self._sync_header_checkbox)
        self.model().modelReset.connect(self._sync_header_checkbox)
        self._sync_header_checkbox()
        self._position_header_checkbox()
        self.setMouseTracking(True)
        self.viewport().setMouseTracking(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.setHorizontalScrollMode(
            QAbstractItemView.ScrollMode.ScrollPerPixel
        )
        self.setAcceptDrops(True)
        self.viewport().setAcceptDrops(True)
        self.setDragEnabled(False)
        self.setDropIndicatorShown(True)
        self.setDragDropOverwriteMode(False)
        self.setDragDropMode(QAbstractItemView.DragDropMode.DropOnly)

        self.doubleClicked.connect(self._on_double_clicked)
        self.model().dataChanged.connect(self._on_checks_changed)
        self._check_drag_value = None
        self._check_drag_last_row = None
        self._check_drag_timer = QTimer(self)
        self._check_drag_timer.setInterval(40)
        self._check_drag_timer.timeout.connect(self._continue_check_drag)
        self._reset_empty_table_layout()

    def _position_header_checkbox(self):
        header = self.horizontalHeader()
        column = self.model().COLUMN_CHECK
        option = QStyleOptionButton()
        self.check_all_checkbox.initStyleOption(option)
        indicator = self.check_all_checkbox.style().subElementRect(
            QStyle.SubElement.SE_CheckBoxIndicator, option, self.check_all_checkbox
        )
        # QCheckBox размещает индикатор у левого края своего поля.
        # Совмещаем с ячейками сам индикатор, а не внешние границы виджета.
        self.check_all_checkbox.move(
            round(header.sectionViewportPosition(column)
                  + (header.sectionSize(column) - indicator.width()) / 2 - indicator.x()),
            round((header.height() - indicator.height()) / 2 - indicator.y()),
        )

    def _sync_header_checkbox(self):
        files = self.model().files()
        marked = sum(self.model().is_checked(item) for item in files)
        self.check_all_checkbox.setEnabled(bool(files))
        partial = 0 < marked < len(files)
        self.check_all_checkbox.setTristate(partial)
        if partial:
            self.check_all_checkbox.setCheckState(Qt.CheckState.PartiallyChecked)
        else:
            self.check_all_checkbox.setChecked(bool(marked))

    def _on_double_clicked(self, index: QModelIndex):
        if not index.isValid() or index.column() == self.model().COLUMN_CHECK:
            return
        self.itemDoubleClicked.emit(FileListItemAdapter(self, index))

    def _on_checks_changed(self, _first, _last, roles):
        if Qt.ItemDataRole.CheckStateRole in roles:
            if self._check_drag_value is not None and self.model().conversion_formats_visible:
                # Фильтр по формату применяется после завершения отметки диапазона.
                self._sync_header_checkbox()
            else:
                self.itemSelectionChanged.emit()

    def clear(self):
        self.set_files([])

    def selectedItems(self):
        return [
            FileListItemAdapter(self, self.model().index(row, self.model().COLUMN_NAME))
            for row, item in enumerate(self.model().files())
            if self.model().is_checked(item)
        ]

    def selected_file_items(self, *, files_only: bool = False) -> list:
        return selected_file_items(self, files_only=files_only)

    def clearSelection(self):
        self._set_checks(False)

    def selectAll(self):
        self._set_checks(True)

    def _set_checks(self, checked):
        model = self.model()
        files = model.files()
        changed = False
        for item in files:
            changed = model.set_checked(item, checked) or changed
        if changed:
            self.viewport().update()
            self.itemSelectionChanged.emit()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Заголовок и viewport рисуются отдельно от скруглённой внешней рамки.
        inner_radius = FILE_PANEL_RADIUS - 1
        clip = QPainterPath()
        clip.addRoundedRect(QRectF(self.rect()), inner_radius, inner_radius)
        self.setMask(QRegion(clip.toFillPolygon().toPolygon()))

    def mousePressEvent(self, event):
        self._drag_start = event.position().toPoint()
        index = self.indexAt(event.position().toPoint())
        if (
            event.button() == Qt.MouseButton.LeftButton
            and index.isValid()
            and index.column() == self.model().COLUMN_CHECK
            and index.data(Qt.ItemDataRole.UserRole) is not None
        ):
            self.selectionModel().setCurrentIndex(index, QItemSelectionModel.SelectionFlag.NoUpdate)
            value = index.data(Qt.ItemDataRole.CheckStateRole)
            self._check_drag_value = value != Qt.CheckState.Checked
            self._check_drag_last_row = index.row()
            self._apply_check_drag(index.row())
            self._check_drag_timer.start()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._check_drag_value is not None:
            if event.buttons() & Qt.MouseButton.LeftButton:
                self._move_check_drag(event.position().toPoint())
                event.accept()
                return
            self._finish_check_drag(notify=True)
        start = getattr(self, "_drag_start", None)
        if (
            self.dragEnabled()
            and start is not None
            and event.buttons() & Qt.MouseButton.LeftButton
            and (event.position().toPoint() - start).manhattanLength() >= QApplication.startDragDistance()
        ):
            index = self.indexAt(start)
            if index.isValid() and index.column() != self.model().COLUMN_CHECK:
                self._drag_row = index.row()
                drag = QDrag(self)
                mime = QMimeData()
                mime.setData("application/x-multifora-row", b"row")
                drag.setMimeData(mime)
                drag.exec(Qt.DropAction.MoveAction)
                self._drag_start = None
                return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self._check_drag_value is not None:
            self._finish_check_drag(notify=True)
            event.accept()
            return
        index = self.indexAt(event.position().toPoint())
        if event.button() == Qt.MouseButton.LeftButton and index.column() == self.model().COLUMN_CHECK:
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def _apply_check_drag(self, row):
        first, last = sorted((self._check_drag_last_row, row))
        changed = False
        files = self.model().files()
        for item in files[first:last + 1]:
            if self.model().set_checked(item, self._check_drag_value):
                changed = True
        self._check_drag_last_row = row
        if changed:
            column = self.model().COLUMN_CHECK
            self.model().dataChanged.emit(
                self.model().index(first, column), self.model().index(last, column),
                [Qt.ItemDataRole.CheckStateRole],
            )

    def _move_check_drag(self, position):
        if not self.model().files():
            self._finish_check_drag()
            return
        height = self.viewport().height()
        scrollbar = self.verticalScrollBar()
        if position.y() < 18:
            scrollbar.setValue(scrollbar.value() - 12)
        elif position.y() > height - 18:
            scrollbar.setValue(scrollbar.value() + 12)
        row = self.rowAt(max(0, min(position.y(), height - 1)))
        if row < 0 and position.y() >= 0:
            row = len(self.model().files()) - 1
        if row >= 0:
            self._apply_check_drag(row)

    def _continue_check_drag(self):
        if not QApplication.mouseButtons() & Qt.MouseButton.LeftButton:
            self._finish_check_drag(notify=True)
            return
        self._move_check_drag(self.viewport().mapFromGlobal(QCursor.pos()))

    def _finish_check_drag(self, *, notify=False):
        was_dragging = self._check_drag_value is not None
        self._check_drag_timer.stop()
        self._check_drag_value = None
        self._check_drag_last_row = None
        self._drag_start = None
        if was_dragging and notify and self.model().conversion_formats_visible:
            self.itemSelectionChanged.emit()

    def set_files(self, files: list):
        self._finish_check_drag()
        self.model().set_files(files)
        if files:
            header = self.horizontalHeader()
            for column in range(self.model().columnCount()):
                if column not in (self.model().COLUMN_CHECK, self.model().COLUMN_ORDER):
                    header.setSectionResizeMode(column, QHeaderView.ResizeMode.Interactive)
            header.setStretchLastSection(True)
            self._resize_columns_to_contents()
            return

        self._reset_empty_table_layout()

    def _reset_empty_table_layout(self):
        """Вписывает пустую таблицу в панель независимо от прежней ширины колонок."""
        header = self.horizontalHeader()
        header.setStretchLastSection(False)
        for column in range(self.model().columnCount()):
            if column not in (self.model().COLUMN_CHECK, self.model().COLUMN_ORDER):
                header.setSectionResizeMode(column, QHeaderView.ResizeMode.Stretch)
        header.resizeSection(self.model().COLUMN_CHECK, self._CHECK_COLUMN_WIDTH)
        self.horizontalScrollBar().setValue(
            self.horizontalScrollBar().minimum()
        )
        self.verticalScrollBar().setValue(self.verticalScrollBar().minimum())

    def refresh(self):
        self.model().refresh()

    def move_current_row(self, delta):
        index = self.currentIndex()
        model = self.model()
        row = index.row()
        target = row + delta
        if not index.isValid() or not (0 <= target < len(model.files())):
            return
        if model.moveRows(QModelIndex(), row, 1, QModelIndex(), target + (delta > 0)):
            self.orderChanged.emit()
            self.setCurrentIndex(model.index(target, model.COLUMN_NAME))
            self.scrollTo(self.currentIndex())

    def _resize_columns_to_contents(self):
        header = self.horizontalHeader()
        for column in (self.model().COLUMN_OLD_NAME, self.model().COLUMN_NEW_NAME):
            self.resizeColumnToContents(column)
            # Длинные имена раскрываются ручным расширением колонки.
            width = max(header.sectionSizeHint(column), header.sectionSize(column) // 2)
            header.resizeSection(column, min(width, self._NAME_COLUMN_MAX_WIDTH))
        self.resizeColumnToContents(self.model().COLUMN_TYPE)
        if header.isSortIndicatorShown():
            section = header.sortIndicatorSection()
            if 0 <= section < self.model().columnCount():
                # Qt не всегда учитывает ширину системной стрелки
                # при resizeColumnToContents, и она накладывается на заголовок.
                header.resizeSection(section, header.sectionSize(section) + 6)

    def set_manual_sorting(self, enabled: bool):
        self.setDragEnabled(enabled)
        self.setDragDropMode(
            QAbstractItemView.DragDropMode.InternalMove
            if enabled
            else QAbstractItemView.DragDropMode.DropOnly
        )
        if enabled:
            self.setDefaultDropAction(Qt.DropAction.MoveAction)

    def keyPressEvent(self, event):
        if (
            self.keyboard_reordering_enabled
            and event.modifiers() == Qt.KeyboardModifier.AltModifier
            and event.key() in (Qt.Key.Key_Up, Qt.Key.Key_Down)
        ):
            self.move_current_row(-1 if event.key() == Qt.Key.Key_Up else 1)
        elif event.key() == Qt.Key.Key_Delete:
            self.deleteRequested.emit()
        elif event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.openRequested.emit()
        elif event.key() == Qt.Key.Key_F2:
            self.renameRequested.emit()
        elif event.matches(QKeySequence.StandardKey.Copy):
            self.copyRequested.emit()
        elif event.key() == Qt.Key.Key_Space and self.currentIndex().isValid():
            index = self.model().index(self.currentIndex().row(), self.model().COLUMN_CHECK)
            self.model().setData(
                index,
                Qt.CheckState.Unchecked
                if self.model().is_checked(index.data(Qt.ItemDataRole.UserRole))
                else Qt.CheckState.Checked,
                Qt.ItemDataRole.CheckStateRole,
            )
        elif event.matches(QKeySequence.StandardKey.SelectAll):
            self.selectAll()
        else:
            super().keyPressEvent(event)
            return
        event.accept()

    def select_paths(self, paths: list):
        path_set = set(paths)
        changed = False
        for item in self.model().files():
            if item.path in path_set and self.model().set_checked(item, True):
                changed = True
        if changed:
            self.viewport().update()
            self.itemSelectionChanged.emit()

    def dragEnterEvent(self, event):
        if event.source() == self and self.dragEnabled():
            event.acceptProposedAction()
        elif event.mimeData().hasUrls():
            self.setStyleSheet(FILE_LIST_DRAG_ACTIVE_STYLE)
            event.accept()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if event.source() == self and self.dragEnabled():
            event.acceptProposedAction()
        elif event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        apply_standard_field_style(self)
        event.accept()

    def dropEvent(self, event):
        apply_standard_field_style(self)
        if event.source() == self and self.dragEnabled():
            target = self.indexAt(event.position().toPoint())
            destination = target.row() if target.isValid() else len(self.model().files())
            if target.isValid() and event.position().y() > self.visualRect(target).center().y():
                destination += 1
            if self.model().moveRows(QModelIndex(), self._drag_row, 1, QModelIndex(), destination):
                self.orderChanged.emit()
            event.accept()
        elif event.mimeData().hasUrls():
            event.accept()
            paths = []
            for url in event.mimeData().urls():
                file_path = url.toLocalFile()
                if os.path.exists(file_path):
                    paths.append(file_path)
            if paths:
                self.filesDropped.emit(paths)
        else:
            event.ignore()
