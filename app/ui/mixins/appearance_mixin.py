# -*- coding: utf-8 -*-
from pathlib import Path

from PyQt6.QtCore import QEvent, QObject, Qt, QTimer, QUrl
from PyQt6.QtGui import (
    QAction,
    QColor,
    QDesktopServices,
    QFont,
    QFontMetrics,
    QGuiApplication,
    QPalette,
    QTextCursor,
)
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListView,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSlider,
    QSpinBox,
    QStyle,
    QStyleOptionViewItem,
    QStyledItemDelegate,
    QTabBar,
    QTableWidget,
    QTabWidget,
    QTextBrowser,
    QToolButton,
    QVBoxLayout,
    QWidget,
)
from app.core.message_boxes import tune_message_box_layout
from app.ui.ui_components import (
    setup_standard_danger_button,
    setup_standard_dropdown,
    setup_standard_primary_button,
    setup_standard_secondary_button,
)


class AppearanceMixin:
    def _checkbox_checkmark_url(self):
        """Возвращает путь локальной иконки галочки для QSS."""
        icon_path = Path(__file__).resolve().parents[1] / "checkbox_checked.svg"
        return icon_path.resolve().as_posix()

    def _apply_detached_theme_style(self, style: str):
        """Применяет тему к отдельным окнам, не входящим в иерархию главного окна."""
        dialog = getattr(self, "_settings_dialog", None)
        if dialog is None:
            return
        try:
            dialog.setStyleSheet(style)
        except Exception:
            pass

    def apply_dark_style(self):
        """Применяет темный стиль для приложения"""
        checkmark_url = self._checkbox_checkmark_url()
        style = """
            QMainWindow {
                background-color: #4a4a4a;
            }
            QWidget {
                background-color: #4a4a4a;
                font-family: "Segoe UI";
                font-size: 14px;
                font-weight: 600;
            }
            QWidget#top_menu_bar {
                background-color: #4a4a4a;
            }
            QWidget#app_header {
                background-color: #4a4a4a;
            }
            QLineEdit, QPlainTextEdit, QTextBrowser, QListWidget, QTableWidget, QComboBox, QSpinBox {
                background-color: #3a3a3a;
            }
            QFrame#card {
                background-color: #343840;
                border: 1px solid #343840;
                border-top: none;
                border-top-left-radius: 0px;
                border-top-right-radius: 0px;
                border-bottom-left-radius: 0px;
                border-bottom-right-radius: 0px;
            }
            QFrame#card QWidget {
                background-color: transparent;
            }
            QFrame#settings_card {
                background-color: transparent;
                border: none;
            }
            QFrame#settings_card QWidget {
                background-color: transparent;
            }
            QFrame#card QPushButton {
                background-color: #3d74b3;
                color: #ffffff;
                border: none;
                border-radius: 4px;
            }
            QFrame#card QPushButton:hover {
                background-color: #4a82c0;
            }
            QFrame#card QPushButton:pressed {
                background-color: #3568a0;
            }
QFrame#card QPushButton:disabled {
                background-color: #6c7a86;
                color: #ffffff;
            }
            QFrame#card QPushButton#convert_btn,
            QFrame#card QPushButton[text="Конвертировать"],
            QFrame#card QPushButton[text="Сжать файлы"],
            QFrame#card QPushButton[text="Применить"],
            QFrame#card QPushButton[text="Откатить"] {
                background-color: #2c8f73;
            }
            QFrame#card QPushButton#convert_btn:hover,
            QFrame#card QPushButton[text="Конвертировать"]:hover,
            QFrame#card QPushButton[text="Сжать файлы"]:hover,
            QFrame#card QPushButton[text="Применить"]:hover,
            QFrame#card QPushButton[text="Откатить"]:hover {
                background-color: #36a083;
            }
            QFrame#card QPushButton#convert_btn:pressed,
            QFrame#card QPushButton[text="Конвертировать"]:pressed,
            QFrame#card QPushButton[text="Сжать файлы"]:pressed,
            QFrame#card QPushButton[text="Применить"]:pressed,
            QFrame#card QPushButton[text="Откатить"]:pressed {
                background-color: #287f67;
            }
            QLabel#card_title {
                font-size: 14px;
                font-weight: bold;
                color: #e0e0e0;
            }
            QLabel#card_item {
                font-size: 14px;
                color: #cfcfcf;
            }

            QPushButton {
                padding: 3px 10px;
                font-size: 14px;
                font-weight: normal;
                color: #fff;
                background-color: #3d74b3;
                border: none;
                border-radius: 4px;
                text-align: center;
                min-height: 26px;
                max-height: 28px;
            }
            QPushButton:hover {
                background-color: #4a82c0;
            }
            QPushButton:pressed {
                background-color: #3568a0;
            }
QPushButton:disabled {
                background-color: #6c7a86;
                color: #ffffff;
            }
            QPushButton#about_program_btn {
                padding: 0px;
                min-height: 0px;
                max-height: 20px;
                color: #7bdc8a;
                background-color: transparent;
                border: none;
                border-radius: 0px;
                text-align: center;
            }
            QPushButton#about_program_btn:hover {
                color: #57c56b;
                text-decoration: underline;
                background-color: transparent;
            }
            QPushButton#about_program_btn:pressed {
                background-color: transparent;
            }
            QPushButton#top_menu_link_btn {
                padding: 2px 8px;
                min-height: 0px;
                max-height: 22px;
                color: #e7e7e7;
                background-color: transparent;
                border: none;
                border-radius: 0px;
            }
            QPushButton#top_menu_link_btn:hover {
                color: #ffffff;
                text-decoration: underline;
                background-color: transparent;
            }
            QPushButton#top_menu_link_btn:pressed {
                background-color: transparent;
            }

            QPushButton#convert_btn {
                background-color: #2c8f73;
            }
            QPushButton#convert_btn:hover {
                background-color: #36a083;
            }
            QPushButton#convert_btn:pressed {
                background-color: #287f67;
            }
QPushButton#convert_btn:disabled {
                background-color: #2c8f73;
                color: #ffffff;
            }
            QPushButton#cancel_operation_btn {
                background-color: #c84b4b;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                min-width: 84px;
            }
            QPushButton#cancel_operation_btn:hover {
                background-color: #d75a5a;
            }
            QPushButton#cancel_operation_btn:pressed {
                background-color: #af3f3f;
            }
QPushButton#cancel_operation_btn:disabled {
                background-color: #c84b4b;
                color: #ffffff;
            }
            QPushButton[text="Откатить"]:disabled,
            QFrame#card QPushButton[text="Откатить"]:disabled {
                background-color: #2c8f73;
                color: #ffffff;
            }

            QPushButton[text="Очистить"] {
                background-color: #aa5257;
            }
            QPushButton[text="Очистить"]:hover {
                background-color: #bc6066;
            }
            QPushButton[text="Очистить"]:pressed {
                background-color: #9a464b;
            }

            QPushButton[text="Применить"] {
                background-color: #5fbf7a;
            }
            QPushButton[text="Применить"]:hover {
                background-color: #4fa66a;
            }
            QPushButton[text="Применить"]:pressed {
                background-color: #46955f;
            }

            QGroupBox {
                font-weight: bold;
                font-size: 13px;
                margin-top: 0px;
                padding-top: 0px;
                background-color: transparent;
                border: none;
                border-radius: 0px;
                color: #e0e0e0;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 6px;
                margin-left: 8px;
                color: #e0e0e0;
            }

            ExpandableGroupBox {
                font-weight: bold;
                font-size: 13px;
                margin-top: 0px;
                padding-top: 0px;
                margin: 0px;
                padding: 0px;
                background-color: transparent;
                border: none;
                border-radius: 0px;
                color: #e0e0e0;
            }
            QPushButton[buttonVariant="section"] {
                text-align: left;
                padding: 2px 10px;
                font-size: 14px;
                font-weight: bold;
                color: #ffffff;
                background-color: #3f78b5;
                border: none;
                border-radius: 0px;
                min-height: 34px;
                max-height: 34px;
            }
            QPushButton[buttonVariant="section"]:hover {
                background-color: #4c86c3;
                color: #ffffff;
            }
            QPushButton[buttonVariant="section"]:checked {
                background-color: #356da8;
                border: none;
                color: #ffffff;
                border-bottom-left-radius: 0px;
                border-bottom-right-radius: 0px;
            }

            QLabel {
                font-size: 14px;
                color: #e0e0e0;
            }
            QCheckBox {
                font-size: 14px;
                color: #e0e0e0;
                spacing: 8px;
                padding: 0px;
                min-height: 24px;
                max-height: 24px;
                qproperty-layoutDirection: LeftToRight;
            }
            QCheckBox::indicator {
                width: 14px;
                height: 14px;
                margin-right: 6px;
                border: 1px solid #c7cfda;
                border-radius: 2px;
                background-color: #f2f4f7;
            }
            QCheckBox::indicator:checked {
                border: 1px solid #3d74b3;
                background-color: #3d74b3;
                image: url("__CHECKMARK_URL__");
            }
            QComboBox {
                font-size: 14px;
                padding: 3px;
                min-height: 24px;
                max-height: 24px;
                background-color: #3a3a3a;
                color: #f0f0f0;
                border: 1px solid rgba(255, 255, 255, 0.55);
                border-radius: 0px;
            }
            QLineEdit,
            QSpinBox {
                font-size: 14px;
                padding: 3px;
                min-height: 24px;
                max-height: 24px;
            }
            QLineEdit,
            QSpinBox {
                padding: 3px;
                min-height: 24px;
                max-height: 24px;
            }
            QComboBox::drop-down {
                border-left: 1px solid rgba(255, 255, 255, 0.55);
            }
            QComboBox:hover {
                border: 1px solid rgba(255, 255, 255, 0.75);
            }
            QToolButton#menu_like_combo {
                font-size: 14px;
                padding: 3px;
                min-height: 24px;
                max-height: 24px;
                background-color: #3a3a3a;
                color: #f0f0f0;
                border: 1px solid rgba(255, 255, 255, 0.55);
                border-radius: 0px;
                text-align: left;
                padding-left: 8px;
            }
            QToolButton#menu_like_combo::menu-indicator {
                subcontrol-origin: padding;
                subcontrol-position: right center;
                right: 6px;
            }
            QToolButton#menu_like_combo:hover {
                border: 1px solid rgba(255, 255, 255, 0.75);
            }
            QComboBox QAbstractItemView {
                background-color: #ffffff;
                color: #1f2328;
                border: 1px solid #c7cfda;
                selection-background-color: #3d74b3;
                outline: 0px;
                border-radius: 0px;
                padding: 0px;
                margin: 0px;
            }
            QComboBox QListView {
                background-color: #ffffff;
                color: #1f2328;
                border: 1px solid #c7cfda;
                border-radius: 0px;
                margin: 0px;
                padding: 0px;
                outline: 0px;
            }
            QComboBox QListView::viewport {
                background-color: #ffffff;
                margin: 0px;
                padding: 0px;
            }
            QComboBox QAbstractItemView::item {
                padding: 4px 8px;
                margin: 0px;
                background-color: transparent;
                color: #1f2328;
            }
            QComboBox QAbstractItemView::item:selected {
                background-color: #3d74b3;
                color: #ffffff;
            }
            QMenu {
                background-color: #ffffff;
                color: #1f2328;
                border: 1px solid #c7cfda;
                margin: 0px;
                padding: 0px;
                border-radius: 0px;
            }
            QMenu#menu_like_combo_popup,
            QMenu#header_dropdown_popup {
                background-color: #ffffff;
                border: 1px solid #c7cfda;
                margin: 0px;
                padding: 0px;
                border-radius: 0px;
            }
            QMenu::item {
                padding: 4px 8px;
                background-color: transparent;
            }
            QMenu::item:selected {
                background-color: #3d74b3;
                color: #ffffff;
            }
            QMenu::separator {
                height: 1px;
                background: rgba(0, 0, 0, 0.2);
            }
            QToolButton#header_cell_tl,
            QToolButton#header_cell_tr,
            QToolButton#header_cell_bl {
                font-size: 13px;
                padding: 2px;
                padding-left: 8px;
                min-height: 20px;
                max-height: 20px;
                background-color: #3a3a3a;
                color: #f0f0f0;
                border: 1px solid rgba(255, 255, 255, 0.55);
                border-radius: 0px;
                text-align: left;
            }
            QLineEdit#header_cell_br {
                font-size: 13px;
                padding: 2px;
                min-height: 20px;
                max-height: 20px;
                background-color: #3a3a3a;
                color: #f0f0f0;
                border: 1px solid rgba(255, 255, 255, 0.55);
                border-radius: 0px;
            }
            QToolButton#header_cell_tl::menu-indicator,
            QToolButton#header_cell_tr::menu-indicator,
            QToolButton#header_cell_bl::menu-indicator {
                subcontrol-origin: padding;
                subcontrol-position: right center;
                right: 6px;
            }
            QToolButton#header_cell_tl:hover,
            QToolButton#header_cell_tr:hover,
            QToolButton#header_cell_bl:hover {
                border: 1px solid rgba(255, 255, 255, 0.75);
            }
            QToolButton#header_cell_tl:pressed,
            QToolButton#header_cell_tr:pressed,
            QToolButton#header_cell_bl:pressed {
                background-color: #363636;
            }
            /* Single grid lines between adjacent controls (no doubled borders). */
            QToolButton#header_cell_tr {
                border-left: 0px;
            }
            QToolButton#header_cell_bl {
                border-top: 0px;
                border-bottom: 0px;
            }
            QLineEdit#header_cell_br {
                border-left: 0px;
                border-top: 0px;
                border-bottom: 0px;
            }
            QLineEdit {
                font-size: 14px;
                padding: 3px;
                min-height: 24px;
                max-height: 24px;
                background-color: #3a3a3a;
                color: #f0f0f0;
                border: 1px solid #4a4a4a;
                border-radius: 0px;
            }
            QLineEdit::placeholder {
                color: #b4bcc6;
            }
            QPlainTextEdit {
                font-size: 14px;
                background-color: #363636;
                color: #f0f0f0;
                border: 1px solid #444;
                border-radius: 0px;
            }
            QPlainTextEdit:focus {
                border: 1px solid #2f79c6;
            }
            QSpinBox {
                font-size: 14px;
                padding: 3px;
                min-height: 24px;
                max-height: 24px;
                background-color: #3a3a3a;
                color: #f0f0f0;
                border: 1px solid #4a4a4a;
                border-radius: 0px;
            }
            QSlider {
                min-height: 20px;
                max-height: 20px;
            }
            QSlider::groove:horizontal {
                height: 4px;
                background: #3f3f3f;
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                background: #2f79c6;
                width: 12px;
                height: 12px;
                margin: -4px 0;
                border-radius: 6px;
            }
            QListWidget {
                font-size: 13px;
                background-color: #3a3a3a;
                color: #f0f0f0;
                border: 1px solid #4a4a4a;
                border-radius: 0px;
            }
            QListView {
                font-size: 13px;
                background-color: #3a3a3a;
                color: #f0f0f0;
                border: 1px solid #4a4a4a;
                border-radius: 0px;
            }
            QListView::item {
                padding: 2px 4px;
                min-height: 22px;
                color: #f0f0f0;
            }
            QListView::item:selected {
                background-color: #2f79c6;
                color: white;
            }
            QListView#files_list,
            QListWidget#files_list {
                background-color: #3a3a3a;
                alternate-background-color: #343840;
                color: #f0f0f0;
                selection-color: #1f2328;
                selection-background-color: #9fc5f8;
                show-decoration-selected: 1;
            }
            QListView#files_list::item,
            QListWidget#files_list::item {
                background-color: #3a3a3a;
                color: #f0f0f0;
            }
            QListView#files_list::item:alternate,
            QListWidget#files_list::item:alternate {
                background-color: #343840;
                color: #f0f0f0;
            }
            QListView#files_list::item:selected,
            QListWidget#files_list::item:selected,
            QListView#files_list::item:selected:active,
            QListWidget#files_list::item:selected:active,
            QListView#files_list::item:selected:!active,
            QListWidget#files_list::item:selected:!active {
                background-color: #9fc5f8;
                color: #1f2328;
                selection-color: #1f2328;
            }
            QListWidget::item {
                padding: 3px;
                color: #f0f0f0;
            }
            QListWidget::item:selected {
                background-color: #2f79c6;
                color: white;
            }
            QListWidget#settings_nav {
                background-color: #3d74b3;
                border: none;
                border-radius: 0px;
                padding: 0px;
                margin: 0px;
                outline: 0px;
            }
            QListWidget#settings_nav::item {
                padding: 2px 10px;
                margin: 0px;
                border-radius: 0px;
                color: #ffffff;
                font-family: "Segoe UI";
                font-size: 10px;
                font-weight: 900;
                background-color: #3d74b3;
                border: none;
                min-height: 36px;
                max-height: 36px;
            }
            QListWidget#settings_nav::item:hover {
                background-color: #4a82c0;
                color: #ffffff;
            }
            QListWidget#settings_nav::item:selected {
                background-color: #2f79c6;
                color: #ffffff;
                font-weight: 900;
                border: none;
            }
            QTabWidget::pane {
                border: none;
                border-radius: 0px;
                background-color: #4a4a4a;
            }
            QTabBar::tab {
                padding: 2px 10px;
                font-size: 14px;
                font-weight: bold;
                min-height: 18px;
                max-height: 18px;
                background-color: #3b3f46;
                color: #e8e8e8;
                border: none;
                border-radius: 0px;
                margin: 0px;
            }
            QTabBar::tab:selected {
                background-color: #2f333a;
                color: #e8e8e8;
            }
            QTabBar::tab:hover:!selected {
                background-color: #434853;
            }
            QProgressBar {
                font-size: 14px;
                min-height: 26px;
                max-height: 26px;
                background-color: #3f3f3f;
                color: #e0e0e0;
                border: 1px solid #4a4a4a;
                border-radius: 0px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #2f79c6;
                border-radius: 0px;
            }
            QStatusBar {
                font-size: 13px;
                background-color: #4a4a4a;
                color: #e0e0e0;
            }
            QMessageBox {
                background-color: #4a4a4a;
            }
            QMessageBox QLabel {
                font-size: 13px;
                color: #e0e0e0;
            }
            QMessageBox QPushButton {
                min-height: 22px;
                max-height: 22px;
                font-size: 13px;
                background-color: #2f79c6;
                color: white;
                border-radius: 4px;
            }
            QMessageBox QPushButton:hover {
                background-color: #2768a8;
            }
            QMessageBox QPushButton:pressed {
                background-color: #245f99;
            }
            QScrollArea {
                border: none;
                background-color: #4a4a4a;
            }
            QScrollArea QWidget#qt_scrollarea_viewport {
                background-color: #4a4a4a;
                border: none;
            }
            QScrollBar:vertical {
                background: transparent;
                border: none;
                width: 10px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: #5c5c5c;
                border-radius: 0px;
                min-height: 20px;
            }
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {
                border: none;
                background: transparent;
                height: 0px;
            }
            QScrollBar::add-page:vertical,
            QScrollBar::sub-page:vertical {
                background: transparent;
            }
            QScrollBar:horizontal {
                background: transparent;
                border: none;
                height: 10px;
                margin: 0px;
            }
            QScrollBar::handle:horizontal {
                background: #5c5c5c;
                border-radius: 0px;
                min-width: 20px;
            }
            QScrollBar::add-line:horizontal,
            QScrollBar::sub-line:horizontal {
                border: none;
                background: transparent;
                width: 0px;
            }
            QScrollBar::add-page:horizontal,
            QScrollBar::sub-page:horizontal {
                background: transparent;
            }
            QTableWidget {
                background-color: #3a3a3a;
                color: #f0f0f0;
                border: 1px solid #4a4a4a;
                border-radius: 6px;
            }
            QTableWidget::item {
                padding: 3px;
                color: #f0f0f0;
            }
            QTableWidget::item:selected {
                background-color: #2f79c6;
                color: white;
            }
            QHeaderView::section {
                background-color: #2b2b2b;
                color: #e0e0e0;
                padding: 4px;
                border: 1px solid #444;
            }
            /* Force light dropdown popup even in dark theme (override generic QListView). */
            QComboBox QAbstractItemView,
            QComboBox QListView,
            QComboBox QListView::viewport {
                background-color: #ffffff;
                color: #1f2328;
                font-family: "Segoe UI";
                font-size: 14px;
                font-weight: 600;
                border: 1px solid #c7cfda;
                border-radius: 0px;
                margin: 0px;
                padding: 0px;
                outline: 0px;
            }
            QComboBox QAbstractItemView::item {
                padding: 6px 10px;
                margin: 0px;
                background-color: transparent;
                color: #1f2328;
            }
            QComboBox QAbstractItemView::item:selected {
                background-color: #3d74b3;
                color: #ffffff;
            }
            QPushButton[buttonVariant="secondary"] {
                background-color: #3f78b5;
                color: #ffffff;
                border: none;
                border-radius: 4px;
            }
            QPushButton[buttonVariant="secondary"]:hover {
                background-color: #4c86c3;
            }
            QPushButton[buttonVariant="secondary"]:pressed {
                background-color: #356da8;
            }
            QPushButton[buttonVariant="secondary"]:disabled {
                background-color: #6a7f97;
                color: #ffffff;
            }
            QPushButton[buttonVariant="primary"] {
                background-color: #2f9a72;
                color: #ffffff;
                border: none;
                border-radius: 4px;
            }
            QPushButton[buttonVariant="primary"]:hover {
                background-color: #39ab82;
            }
            QPushButton[buttonVariant="primary"]:pressed {
                background-color: #288765;
            }
            QPushButton[buttonVariant="primary"]:disabled {
                background-color: #2f9a72;
                color: #ffffff;
            }
            QPushButton[buttonVariant="danger"] {
                background-color: #cf5656;
                color: #ffffff;
                border: none;
                border-radius: 4px;
            }
            QPushButton[buttonVariant="danger"]:hover {
                background-color: #dd6666;
            }
            QPushButton[buttonVariant="danger"]:pressed {
                background-color: #b94848;
            }
            QPushButton[buttonVariant="danger"]:disabled {
                background-color: #cf5656;
                color: #ffffff;
            }
            QPushButton[buttonVariant="link"] {
                background-color: transparent;
                color: #dce8f6;
                border: none;
                border-radius: 0px;
                padding: 2px 8px;
                min-height: 0px;
                max-height: 22px;
            }
            QPushButton[buttonVariant="link"]:hover {
                background-color: transparent;
                color: #ffffff;
                text-decoration: underline;
            }
            QPushButton[buttonVariant="link"]:pressed {
                background-color: transparent;
            }
        """
        style = style.replace("__CHECKMARK_URL__", checkmark_url)
        self.setStyleSheet(style)
        self._apply_detached_theme_style(style)
        self._apply_combo_popup_light_style()

    def apply_light_style(self):
        """Применяет светлый стиль для приложения."""
        checkmark_url = self._checkbox_checkmark_url()
        style = """
            QMainWindow, QWidget {
                background-color: #f3f3f3;
                color: #1f2328;
                font-family: "Segoe UI";
                font-size: 14px;
                font-weight: 600;
            }
            QLabel, QPushButton, QToolButton, QLineEdit, QPlainTextEdit, QComboBox, QMenu, QListWidget, QCheckBox {
                font-family: "Segoe UI";
                font-size: 14px;
            }
            QWidget#top_menu_bar, QWidget#app_header {
                background-color: #f3f3f3;
            }
            QFrame#card {
                background-color: #ffffff;
                border: 1px solid #c8cdd4;
                border-top: none;
                border-top-left-radius: 0px;
                border-top-right-radius: 0px;
                border-bottom-left-radius: 0px;
                border-bottom-right-radius: 0px;
            }
            QFrame#card QWidget {
                background-color: transparent;
            }
            QFrame#settings_card {
                background-color: transparent;
                border: none;
            }
            QFrame#settings_card QWidget {
                background-color: transparent;
            }
            QGroupBox {
                font-weight: bold;
                font-size: 14px;
                margin-top: 0px;
                padding-top: 0px;
                background-color: transparent;
                border: none;
                border-radius: 0px;
                color: #1f2328;
            }
            ExpandableGroupBox {
                font-weight: bold;
                font-size: 14px;
                margin-top: 0px;
                padding-top: 0px;
                margin: 0px;
                padding: 0px;
                background-color: transparent;
                border: none;
                border-radius: 0px;
                color: #1f2328;
            }
            QLabel {
                color: #1f2328;
            }
            QPushButton {
                padding: 3px 10px;
                font-size: 14px;
                font-weight: normal;
                color: #ffffff;
                background-color: #3d74b3;
                border: none;
                border-radius: 4px;
                text-align: center;
                min-height: 26px;
                max-height: 28px;
            }
            QPushButton:hover {
                background-color: #4a82c0;
            }
            QPushButton:pressed {
                background-color: #3568a0;
            }
            QPushButton:disabled {
                background-color: #7b8793;
                color: #ffffff;
            }
            QPushButton#about_program_btn {
                padding: 0px;
                min-height: 0px;
                max-height: 20px;
                color: #7bdc8a;
                background-color: transparent;
                border: none;
                border-radius: 0px;
                text-align: center;
            }
            QPushButton#about_program_btn:hover {
                color: #57c56b;
                text-decoration: underline;
                background-color: transparent;
            }
            QPushButton#about_program_btn:pressed {
                background-color: transparent;
            }
            QPushButton#top_menu_link_btn {
                padding: 2px 8px;
                min-height: 0px;
                max-height: 22px;
                color: #000000;
                background-color: transparent;
                border: none;
                border-radius: 0px;
            }
            QPushButton#top_menu_link_btn:hover {
                color: #000000;
                text-decoration: underline;
                background-color: transparent;
            }
            QPushButton#top_menu_link_btn:pressed {
                background-color: transparent;
            }
            QPushButton#convert_btn {
                background-color: #2c8f73;
            }
            QPushButton#convert_btn:hover {
                background-color: #36a083;
            }
            QPushButton#convert_btn:pressed {
                background-color: #287f67;
            }
            QPushButton#convert_btn:disabled {
                background-color: #5fbf7a;
                color: #ffffff;
            }
            QPushButton#cancel_operation_btn {
                background-color: #d65a5a;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                min-width: 84px;
            }
            QPushButton#cancel_operation_btn:hover {
                background-color: #e36a6a;
            }
            QPushButton#cancel_operation_btn:pressed {
                background-color: #bd4b4b;
            }
            QPushButton#cancel_operation_btn:disabled {
                background-color: #d65a5a;
                color: #ffffff;
            }
            QPushButton[text="Очистить"] {
                background-color: #aa5257;
            }
            QPushButton[text="Очистить"]:hover {
                background-color: #bc6066;
            }
            QPushButton[text="Очистить"]:pressed {
                background-color: #9a464b;
            }
            QPushButton[text="Применить"] {
                background-color: #5fbf7a;
            }
            QPushButton[text="Применить"]:hover {
                background-color: #4fa66a;
            }
            QPushButton[text="Применить"]:pressed {
                background-color: #46955f;
            }
            QPushButton[buttonVariant="section"] {
                text-align: left;
                padding: 2px 10px;
                font-size: 14px;
                font-weight: bold;
                color: #ffffff;
                background-color: #467fbd;
                border: none;
                border-radius: 0px;
                min-height: 34px;
                max-height: 34px;
            }
            QPushButton[buttonVariant="section"]:hover {
                background-color: #568ecc;
                color: #ffffff;
            }
            QPushButton[buttonVariant="section"]:checked {
                background-color: #3b70a8;
                border: none;
                color: #ffffff;
                border-bottom-left-radius: 0px;
                border-bottom-right-radius: 0px;
            }
            QLineEdit, QPlainTextEdit, QTextBrowser, QListWidget, QTableWidget, QComboBox, QSpinBox {
                background-color: #ffffff;
                color: #1f2328;
                border: 1px solid #c7cfda;
                border-radius: 0px;
            }
            QLineEdit,
            QComboBox,
            QSpinBox {
                padding: 3px;
                min-height: 24px;
                max-height: 24px;
            }
            QLineEdit::placeholder {
                color: #6f7785;
            }
            QToolButton#menu_like_combo {
                font-size: 14px;
                padding: 3px;
                min-height: 24px;
                max-height: 24px;
                background-color: #ffffff;
                color: #1f2328;
                border: 1px solid #c7cfda;
                border-radius: 0px;
                text-align: left;
                padding-left: 8px;
            }
            QToolButton#menu_like_combo::menu-indicator {
                subcontrol-origin: padding;
                subcontrol-position: right center;
                right: 6px;
            }
            QToolButton#menu_like_combo:hover {
                border: 1px solid #aab5c3;
                background-color: #f8fafc;
            }
            QToolButton#menu_like_combo:disabled {
                color: #8b949e;
                background-color: #f2f4f7;
                border: 1px solid #d6dbe2;
            }
            QToolButton#header_cell_tl,
            QToolButton#header_cell_tr,
            QToolButton#header_cell_bl {
                font-size: 14px;
                padding: 3px;
                padding-left: 8px;
                min-height: 24px;
                max-height: 24px;
                background-color: #ffffff;
                color: #1f2328;
                border: 1px solid #c7cfda;
                border-radius: 0px;
                text-align: left;
            }
            QLineEdit#header_cell_br {
                font-size: 14px;
                padding: 3px;
                min-height: 24px;
                max-height: 24px;
                background-color: #ffffff;
                color: #1f2328;
                border: 1px solid #c7cfda;
                border-radius: 0px;
            }
            QToolButton#header_cell_tr {
                border-left: 0px;
            }
            QToolButton#header_cell_bl {
                border-top: 0px;
                border-bottom: 0px;
            }
            QLineEdit#header_cell_br {
                border-left: 0px;
                border-top: 0px;
                border-bottom: 0px;
            }
            QListWidget#settings_nav {
                background-color: #3d74b3;
                border: none;
                border-radius: 0px;
                padding: 0px;
                margin: 0px;
                outline: 0px;
            }
            QListWidget#settings_nav::item {
                padding: 2px 10px;
                margin: 0px;
                border-radius: 0px;
                color: #ffffff;
                font-family: "Segoe UI";
                font-size: 10px;
                font-weight: 900;
                background-color: #3d74b3;
                border: none;
                min-height: 36px;
                max-height: 36px;
            }
            QListWidget#settings_nav::item:hover {
                background-color: #4a82c0;
                color: #ffffff;
            }
            QListWidget#settings_nav::item:selected {
                background-color: #2f79c6;
                color: #ffffff;
                font-weight: 900;
                border: none;
            }
            /* Force light dropdown popup even in dark theme (override generic QListView). */
            QComboBox QAbstractItemView,
            QComboBox QListView,
            QComboBox QListView::viewport {
                background-color: #ffffff;
                color: #1f2328;
                border: 1px solid #c7cfda;
                border-radius: 0px;
                margin: 0px;
                padding: 0px;
                outline: 0px;
            }
            QComboBox QAbstractItemView::item {
                padding: 4px 8px;
                margin: 0px;
                background-color: transparent;
                color: #1f2328;
            }
            QComboBox QAbstractItemView::item:selected {
                background-color: #3d74b3;
                color: #ffffff;
            }
            QListWidget {
                font-size: 13px;
                background-color: #ffffff;
                color: #1f2328;
                border: 1px solid #c7cfda;
                border-radius: 0px;
            }
            QListView {
                font-size: 13px;
                background-color: #ffffff;
                color: #1f2328;
                border: 1px solid #c7cfda;
                border-radius: 0px;
            }
            QListWidget#files_list,
            QListView#files_list {
                background-color: #f3f3f3;
                alternate-background-color: #4d82bd;
                color: #1f2328;
                selection-color: #1f2328;
                selection-background-color: #9fc5f8;
                show-decoration-selected: 1;
            }
            QListView#files_list::item,
            QListWidget#files_list::item {
                background-color: #f3f3f3;
                color: #1f2328;
            }
            QListView#files_list::item:alternate,
            QListWidget#files_list::item:alternate {
                background-color: #4d82bd;
                color: #ffffff;
            }
            QListView#files_list::item:selected,
            QListWidget#files_list::item:selected,
            QListView#files_list::item:selected:active,
            QListWidget#files_list::item:selected:active,
            QListView#files_list::item:selected:!active,
            QListWidget#files_list::item:selected:!active {
                background-color: #9fc5f8;
                color: #1f2328;
                selection-color: #1f2328;
            }
            QListView::item {
                padding: 2px 4px;
                min-height: 22px;
                color: #1f2328;
                background-color: transparent;
            }
            QListView::item:selected {
                background-color: #2f79c6;
                color: #ffffff;
            }
            QListWidget::item {
                padding: 3px;
                color: #1f2328;
            }
            QListWidget::item:selected {
                background-color: #2f79c6;
                color: #ffffff;
            }
            QMenu, QMenu#menu_like_combo_popup, QMenu#header_dropdown_popup {
                background-color: #f2f4f7;
                color: #1f2328;
                border: 1px solid #c7cfda;
                margin: 0px;
                padding: 0px;
                border-radius: 0px;
            }
            QMenu::item {
                padding: 4px 8px;
                background-color: transparent;
            }
            QMenu::item:selected {
                background-color: #3d74b3;
                color: #ffffff;
            }
            QMenu::separator {
                height: 1px;
                background: rgba(0, 0, 0, 0.2);
            }
            QCheckBox {
                font-size: 14px;
                color: #1f2328;
                spacing: 8px;
                min-height: 24px;
                max-height: 24px;
            }
            QCheckBox::indicator {
                width: 14px;
                height: 14px;
                margin-right: 6px;
                border: 1px solid #9aa6b5;
                border-radius: 2px;
                background-color: #ffffff;
            }
            QCheckBox::indicator:checked {
                border: 1px solid #3d74b3;
                background-color: #3d74b3;
                image: url("__CHECKMARK_URL__");
            }
            QTabWidget::pane {
                border: none;
                border-radius: 0px;
                background-color: #f2f4f7;
            }
            QScrollArea {
                border: none;
                background-color: #f2f4f7;
            }
            QScrollArea QWidget#qt_scrollarea_viewport {
                background-color: #f2f4f7;
                border: none;
            }
            QScrollBar:vertical {
                background: transparent;
                border: none;
                width: 10px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: #b8c0cc;
                border-radius: 0px;
                min-height: 20px;
            }
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {
                border: none;
                background: transparent;
                height: 0px;
            }
            QScrollBar::add-page:vertical,
            QScrollBar::sub-page:vertical {
                background: transparent;
            }
            QScrollBar:horizontal {
                background: transparent;
                border: none;
                height: 10px;
                margin: 0px;
            }
            QScrollBar::handle:horizontal {
                background: #b8c0cc;
                border-radius: 0px;
                min-width: 20px;
            }
            QScrollBar::add-line:horizontal,
            QScrollBar::sub-line:horizontal {
                border: none;
                background: transparent;
                width: 0px;
            }
            QScrollBar::add-page:horizontal,
            QScrollBar::sub-page:horizontal {
                background: transparent;
            }
            QProgressBar {
                font-size: 13px;
                min-height: 22px;
                max-height: 22px;
                background-color: #ffffff;
                color: #1f2328;
                border: 1px solid #c7cfda;
                border-radius: 0px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #3d74b3;
                border-radius: 0px;
            }
            QStatusBar {
                background-color: #f2f4f7;
                color: #1f2328;
            }
            QMessageBox {
                background-color: #f3f3f3;
            }
            QMessageBox QLabel {
                color: #1f2328;
            }
            /* Explicit button accent palette for light theme */
            QPushButton,
            QFrame#card QPushButton {
                color: #ffffff;
                background-color: #3d74b3;
                border: none;
            }
            QPushButton:hover,
            QFrame#card QPushButton:hover {
                background-color: #4a82c0;
            }
            QPushButton:pressed,
            QFrame#card QPushButton:pressed {
                background-color: #3568a0;
            }
            QPushButton:disabled,
            QFrame#card QPushButton:disabled {
                background-color: #7b8793;
                color: #ffffff;
            }
            QPushButton#convert_btn,
            QFrame#card QPushButton#convert_btn,
            QPushButton[text="Конвертировать"],
            QFrame#card QPushButton[text="Конвертировать"],
            QPushButton[text="Сжать файлы"],
            QFrame#card QPushButton[text="Сжать файлы"],
            QPushButton[text="Применить"],
            QFrame#card QPushButton[text="Применить"],
            QPushButton[text="Откатить"],
            QFrame#card QPushButton[text="Откатить"] {
                background-color: #2c8f73;
                color: #ffffff;
            }
            QPushButton#convert_btn:hover,
            QFrame#card QPushButton#convert_btn:hover,
            QPushButton[text="Конвертировать"]:hover,
            QFrame#card QPushButton[text="Конвертировать"]:hover,
            QPushButton[text="Сжать файлы"]:hover,
            QFrame#card QPushButton[text="Сжать файлы"]:hover,
            QPushButton[text="Применить"]:hover,
            QFrame#card QPushButton[text="Применить"]:hover,
            QPushButton[text="Откатить"]:hover,
            QFrame#card QPushButton[text="Откатить"]:hover {
                background-color: #36a083;
                color: #ffffff;
            }
            QPushButton#convert_btn:pressed,
            QFrame#card QPushButton#convert_btn:pressed,
            QPushButton[text="Конвертировать"]:pressed,
            QFrame#card QPushButton[text="Конвертировать"]:pressed,
            QPushButton[text="Сжать файлы"]:pressed,
            QFrame#card QPushButton[text="Сжать файлы"]:pressed,
            QPushButton[text="Применить"]:pressed,
            QFrame#card QPushButton[text="Применить"]:pressed,
            QPushButton[text="Откатить"]:pressed,
            QFrame#card QPushButton[text="Откатить"]:pressed {
                background-color: #287f67;
                color: #ffffff;
            }
            QPushButton[text="Конвертировать"]:disabled,
            QFrame#card QPushButton[text="Конвертировать"]:disabled,
            QPushButton[text="Откатить"]:disabled,
            QFrame#card QPushButton[text="Откатить"]:disabled {
                background-color: #7b8793;
                color: #ffffff;
            }
            QPushButton[text="Откатить"]:disabled,
            QFrame#card QPushButton[text="Откатить"]:disabled {
                background-color: #2c8f73;
                color: #ffffff;
            }
            QPushButton[text="Очистить"],
            QFrame#card QPushButton[text="Очистить"] {
                background-color: #aa5257;
            }
            QPushButton[text="Очистить"]:hover,
            QFrame#card QPushButton[text="Очистить"]:hover {
                background-color: #bc6066;
            }
            QPushButton[text="Очистить"]:pressed,
            QFrame#card QPushButton[text="Очистить"]:pressed {
                background-color: #9a464b;
            }
            QPushButton#about_program_btn,
            QPushButton#top_menu_link_btn {
                background-color: transparent;
                border: none;
            }
            QPushButton[buttonVariant="secondary"] {
                background-color: #467fbd;
                color: #ffffff;
                border: none;
                border-radius: 4px;
            }
            QPushButton[buttonVariant="secondary"]:hover {
                background-color: #568ecc;
            }
            QPushButton[buttonVariant="secondary"]:pressed {
                background-color: #3b70a8;
            }
            QPushButton[buttonVariant="secondary"]:disabled {
                background-color: #91a3b7;
                color: #ffffff;
            }
            QPushButton[buttonVariant="primary"] {
                background-color: #3aa277;
                color: #ffffff;
                border: none;
                border-radius: 4px;
            }
            QPushButton[buttonVariant="primary"]:hover {
                background-color: #46b385;
            }
            QPushButton[buttonVariant="primary"]:pressed {
                background-color: #2f8b67;
            }
            QPushButton[buttonVariant="primary"]:disabled {
                background-color: #3aa277;
                color: #ffffff;
            }
            QPushButton[buttonVariant="danger"] {
                background-color: #d85f5f;
                color: #ffffff;
                border: none;
                border-radius: 4px;
            }
            QPushButton[buttonVariant="danger"]:hover {
                background-color: #e37070;
            }
            QPushButton[buttonVariant="danger"]:pressed {
                background-color: #be4f4f;
            }
            QPushButton[buttonVariant="danger"]:disabled {
                background-color: #d85f5f;
                color: #ffffff;
            }
            QPushButton[buttonVariant="link"] {
                background-color: transparent;
                color: #2f5f99;
                border: none;
                border-radius: 0px;
                padding: 2px 8px;
                min-height: 0px;
                max-height: 22px;
            }
            QPushButton[buttonVariant="link"]:hover {
                background-color: transparent;
                color: #234a79;
                text-decoration: underline;
            }
            QPushButton[buttonVariant="link"]:pressed {
                background-color: transparent;
            }
        """
        style = style.replace("__CHECKMARK_URL__", checkmark_url)
        self.setStyleSheet(style)
        self._apply_detached_theme_style(style)
        self._apply_combo_popup_light_style()

    def _apply_combo_popup_light_style(self):
        """Обновляет popup обычных QComboBox через общий helper после смены темы."""
        try:
            combos = self.findChildren(QComboBox)
        except Exception:
            combos = []
        if not combos:
            return
        for combo in combos:
            try:
                setup_standard_dropdown(combo)
            except Exception:
                continue

    def _get_system_theme_mode(self):
        try:
            hints = QGuiApplication.styleHints()
            color_scheme = hints.colorScheme()
            if color_scheme == Qt.ColorScheme.Dark:
                return "dark"
            return "light"
        except Exception:
            try:
                color = self.palette().window().color()
                return "dark" if color.lightness() < 128 else "light"
            except Exception:
                return "dark"

    def apply_theme_mode(self, mode=None):
        normalized = str(mode or getattr(self, "theme_mode", "system")).strip().lower()
        if normalized not in ("system", "dark", "light"):
            normalized = "system"
        self.theme_mode = normalized

        effective_mode = self._get_system_theme_mode() if normalized == "system" else normalized
        self._effective_theme_mode = effective_mode
        if effective_mode == "light":
            self.apply_light_style()
        else:
            self.apply_dark_style()

        try:
            if callable(getattr(self, "_apply_logs_level_menu_style", None)):
                self._apply_logs_level_menu_style()
        except Exception:
            pass
        try:
            if callable(getattr(self, "_apply_theme_runtime_widgets", None)):
                self._apply_theme_runtime_widgets()
        except Exception:
            pass

        if hasattr(self, "theme_mode_combo") and self.theme_mode_combo is not None:
            try:
                idx = self.theme_mode_combo.findData(self.theme_mode)
                if idx >= 0 and self.theme_mode_combo.currentIndex() != idx:
                    self.theme_mode_combo.blockSignals(True)
                    self.theme_mode_combo.setCurrentIndex(idx)
                    self.theme_mode_combo.blockSignals(False)
            except Exception:
                pass

    def setup_system_theme_tracking(self):
        if getattr(self, "_system_theme_tracking_connected", False):
            return
        try:
            hints = QGuiApplication.styleHints()
            if hasattr(hints, "colorSchemeChanged"):
                hints.colorSchemeChanged.connect(self._on_system_theme_changed)
                self._system_theme_tracking_connected = True
        except Exception:
            pass

    def _on_system_theme_changed(self, _scheme):
        if getattr(self, "theme_mode", "system") == "system":
            self.apply_theme_mode("system")
        
    def show_russian_message_box(self, title, text, icon=QMessageBox.Icon.Question, default_no=True):
        """Показывает диалог подтверждения с русскими кнопками Да/Нет."""
        dialog = QDialog(self)
        dialog.setWindowTitle(str(title))
        dialog.setModal(True)
        dialog.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)
        try:
            dialog._effective_theme_mode = getattr(self, "_effective_theme_mode", "dark")
            dialog.setStyleSheet(self.styleSheet())
        except Exception:
            pass

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(12)

        content_row = QHBoxLayout()
        content_row.setContentsMargins(0, 0, 0, 0)
        content_row.setSpacing(10)

        icon_label = QLabel()
        icon_label.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        icon_label.setFixedSize(32, 32)
        icon_map = {
            QMessageBox.Icon.Information: QStyle.StandardPixmap.SP_MessageBoxInformation,
            QMessageBox.Icon.Warning: QStyle.StandardPixmap.SP_MessageBoxWarning,
            QMessageBox.Icon.Critical: QStyle.StandardPixmap.SP_MessageBoxCritical,
            QMessageBox.Icon.Question: QStyle.StandardPixmap.SP_MessageBoxQuestion,
        }
        try:
            standard_icon = dialog.style().standardIcon(icon_map.get(icon, QStyle.StandardPixmap.SP_MessageBoxQuestion))
            icon_label.setPixmap(standard_icon.pixmap(32, 32))
        except Exception:
            pass
        content_row.addWidget(icon_label, 0, Qt.AlignmentFlag.AlignVCenter)

        text_label = QLabel(str(text))
        text_label.setWordWrap(True)
        text_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        text_label.setMinimumHeight(36)
        content_row.addWidget(text_label, 1, Qt.AlignmentFlag.AlignVCenter)

        layout.addLayout(content_row)

        buttons_row = QHBoxLayout()
        buttons_row.setContentsMargins(0, 0, 0, 0)
        buttons_row.setSpacing(8)
        buttons_row.addStretch()

        yes_button = QPushButton("Да")
        setup_standard_secondary_button(yes_button, height=22)
        yes_button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        no_button = QPushButton("Нет")
        setup_standard_secondary_button(no_button, height=22)
        no_button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        for button in (yes_button, no_button):
            try:
                button.style().unpolish(button)
                button.style().polish(button)
                button.updateGeometry()
            except Exception:
                pass
        button_width = max(84, yes_button.sizeHint().width(), no_button.sizeHint().width())
        for button in (yes_button, no_button):
            button.setFixedWidth(button_width)
        buttons_row.addWidget(yes_button)
        buttons_row.addWidget(no_button)
        layout.addLayout(buttons_row)

        try:
            metrics = QFontMetrics(text_label.font())
            content_width = max(420, min(560, metrics.horizontalAdvance(str(text)) + 150))
            dialog.setMinimumWidth(content_width)
            dialog.resize(max(content_width, dialog.sizeHint().width()), dialog.sizeHint().height())
        except Exception:
            pass

        yes_button.clicked.connect(dialog.accept)
        no_button.clicked.connect(dialog.reject)

        if default_no:
            no_button.setFocus()
        else:
            yes_button.setFocus()

        return dialog.exec() == int(QDialog.DialogCode.Accepted)











