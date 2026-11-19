"""Сводка и подробности последней файловой операции."""

import os

from PySide6.QtCore import QStringListModel, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QListView,
    QMenu,
    QPlainTextEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from app.ui.ui_components import setup_standard_dialog, setup_standard_popup_menu, setup_standard_secondary_button
from core.operation_result import OperationResult

_TITLES = {
    "success": "Готово",
    "warning": "Завершено с замечаниями",
    "partial": "Обработана часть файлов",
    "failed": "Не удалось выполнить операцию",
    "cancelled": "Операция отменена",
}


class OperationResultPanel(QFrame):
    retry_requested = Signal(object)
    undo_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("operation_result")
        self.result = OperationResult()
        self.retryable = []
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(4)
        self.summary = QLabel()
        self.summary.setWordWrap(True)
        layout.addWidget(self.summary)

        actions = QHBoxLayout()
        self.open_result = QPushButton("Открыть")
        self.open_folder = QPushButton("Папка результата")
        for button in (self.open_result, self.open_folder):
            button.clicked.connect(lambda _checked, target=button: self._open_path(target.property("resultPath")))
        self.details = QPushButton("Подробности")
        self.undo = QPushButton("Откатить переименование")
        self.undo.hide()
        self.undo.clicked.connect(self.undo_requested)
        self.details.clicked.connect(self._show_details)
        for button in (self.open_result, self.open_folder, self.details, self.undo):
            setup_standard_secondary_button(button)
            actions.addWidget(button)
        actions.addStretch()
        layout.addLayout(actions)
        self.hide()

    def set_result(self, result: OperationResult, *, can_retry: bool):
        self.result = result
        self.retryable = [
            issue for issue in result.errors if can_retry and issue.get("retryable") and issue.get("path")
        ]
        outputs = list(dict.fromkeys(
            [item.path for item in result.new_files] + [path for _, path in result.updated_files]
        ))
        summary = [
            f"Создано {len(result.new_files)}",
            f"Изменено {len(result.updated_files)}",
        ]
        if result.warnings:
            summary.append(f"Предупреждений {len(result.warnings)}")
        if result.errors:
            summary.append(f"Ошибок {len(result.errors)}")
        if result.compression_sizes:
            saved = sum(size.before - size.after for size in result.compression_sizes)
            summary.append(f"Экономия {saved:,} Б".replace(",", " "))
        self.summary.setText(f"{_TITLES[result.outcome]} · {' · '.join(summary)}")
        self._set_path_menu(self.open_result, outputs)
        folders = list(dict.fromkeys(os.path.dirname(path) for path in outputs))
        self._set_path_menu(self.open_folder, folders, folders=True)
        self.details.setVisible(bool(result.errors or result.warnings or result.compression_sizes))
        self.show()

    def _set_path_menu(self, button, paths, *, folders=False):
        previous = button.menu()
        if previous is not None:
            button.setMenu(None)
            previous.deleteLater()
        button.setVisible(bool(paths))
        button.setProperty("resultPath", paths[0] if len(paths) == 1 else "")
        if len(paths) <= 1:
            return
        menu = QMenu(button)
        setup_standard_popup_menu(menu)
        for path in paths[:12]:
            label = path if folders else os.path.basename(path)
            action = menu.addAction(label.replace("&", "&&"))
            action.setToolTip(path)
            action.triggered.connect(lambda _checked, value=path: self._open_path(value))
        if len(paths) > 12:
            all_results = menu.addAction("Показать все…")
            all_results.triggered.connect(lambda: self._show_paths(paths))
        button.setMenu(menu)

    @staticmethod
    def _open_path(path):
        if path:
            QDesktopServices.openUrl(QUrl.fromLocalFile(path))

    def _show_paths(self, paths):
        dialog = QDialog(self)
        setup_standard_dialog(dialog, title="Результаты", min_width=520, min_height=300)
        layout = QVBoxLayout(dialog)
        view = QListView(dialog)
        model = QStringListModel(paths, view)
        view.setModel(model)
        view.setAccessibleName("Пути к результатам")
        view.activated.connect(lambda index: self._open_path(index.data()))
        layout.addWidget(view)
        close = QPushButton("Закрыть")
        setup_standard_secondary_button(close)
        close.clicked.connect(dialog.reject)
        layout.addWidget(close)
        dialog.exec()
        dialog.deleteLater()

    def _show_details(self):
        rows = [
            (issue, status)
            for issues, status in ((self.result.errors, "Ошибка"), (self.result.warnings, "Предупреждение"))
            for issue in issues
        ]
        rows.extend((
            {
                "path": size.path,
                "message": f"{size.before:,} → {size.after:,} Б".replace(",", " "),
            },
            "Сжато" if size.after < size.before else "Без изменений",
        ) for size in self.result.compression_sizes)
        dialog = QDialog(self)
        setup_standard_dialog(dialog, title="Результат операции", min_width=540, min_height=330)
        dialog.resize(720, 400)
        layout = QVBoxLayout(dialog)
        table = QTableWidget(len(rows), 3, dialog)
        table.setHorizontalHeaderLabels(("Файл", "Состояние", "Что произошло"))
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        table.setAccessibleName("Проблемы по файлам")
        for index, (issue, status) in enumerate(rows):
            path = issue.get("path") or ""
            name = issue.get("name") or os.path.basename(path) or "Операция"
            explanation = issue.get("explanation") or (
                "Откройте технические сведения." if status == "Ошибка" else issue["message"]
            )
            for column, text in enumerate((name, status, explanation)):
                item = QTableWidgetItem(text)
                item.setToolTip(path if column == 0 and path else text)
                table.setItem(index, column, item)
        layout.addWidget(table)
        diagnostics = QPlainTextEdit(dialog)
        diagnostics.setReadOnly(True)
        diagnostics.setAccessibleName("Технические сведения выбранной строки")
        diagnostics.hide()
        layout.addWidget(diagnostics)

        actions = QHBoxLayout()
        expand = QPushButton("Технические сведения")
        expand.setCheckable(True)
        expand.toggled.connect(diagnostics.setVisible)
        copy = QPushButton("Скопировать сведения")
        copy.clicked.connect(lambda: QApplication.clipboard().setText(diagnostics.toPlainText()))
        retry = QPushButton(f"Повторить для {len(self.retryable)}")
        retry.setVisible(bool(self.retryable))
        close = QPushButton("Закрыть")
        close.clicked.connect(dialog.reject)
        for button in (expand, copy, retry, close):
            setup_standard_secondary_button(button)
            actions.addWidget(button)
        layout.addLayout(actions)

        def update_diagnostics():
            row = table.currentRow()
            if row < 0:
                return
            issue, _ = rows[row]
            diagnostics.setPlainText("\n".join(part for part in (issue.get("path"), issue["message"]) if part))

        def retry_files():
            issues = list(self.retryable)
            dialog.accept()
            self.retry_requested.emit(issues)

        retry.clicked.connect(retry_files)
        table.itemSelectionChanged.connect(update_diagnostics)
        if rows:
            table.selectRow(0)
            update_diagnostics()
        dialog.exec()
        dialog.deleteLater()
