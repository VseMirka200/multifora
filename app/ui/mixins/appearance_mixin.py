# -*- coding: utf-8 -*-
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import (
    QFontMetrics,
    QGuiApplication,
)
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QStyle,
    QVBoxLayout,
)
from app.ui.ui_components import (
    setup_standard_dropdown,
    setup_standard_secondary_button,
    refresh_standard_field_styles,
    refresh_standard_surface_styles,
)
from app.ui.ui_spacing import (
    LINK_BUTTON_HEIGHT,
    MARGINS_NONE,
    MESSAGE_DIALOG_MARGINS,
    SPACE_LG,
    SPACE_XL,
    SPACE_2XL,
)


class AppearanceMixin:
    def _checkbox_checkmark_url(self):
        """Возвращает путь локальной иконки галочки для QSS."""
        icon_path = Path(__file__).resolve().parents[1] / "checkbox_checked.svg"
        return icon_path.resolve().as_posix()

    def _tab_content_style_block(self, theme: str) -> str:
        is_light = str(theme).lower() == "light"
        base_text = "#1f2328" if is_light else "#e0e0e0"
        return f"""
            QStackedWidget#operations_stack {{
                background: transparent;
                border: none;
                margin: 0px;
                padding: 0px;
            }}
            QScrollArea#operation_page_scroll,
            QScrollArea#settings_page_scroll {{
                border: none;
                background: transparent;
                margin: 0px;
                padding: 0px;
            }}
            QWidget#operation_page_content,
            QWidget#settings_page_content,
            QWidget#rename_history_settings_page,
            QWidget#rename_history_settings_content,
            QWidget#template_params_widget,
            QFrame#template_numbering_card {{
                background-color: transparent;
                margin: 0px;
                padding: 0px;
            }}
            QFrame#card,
            QFrame#settings_card {{
                background-color: transparent;
                border: none;
            }}
            QFrame#card QWidget,
            QFrame#settings_card QWidget {{
                background-color: transparent;
            }}
            QLabel#tab_section_label {{
                font-size: 13px;
                font-weight: 700;
                color: {base_text};
            }}
            QLabel#settings_page_title {{
                font-size: 30px;
                font-weight: 700;
                color: {base_text};
                padding-bottom: 5px;
                margin-bottom: 3px;
                border-bottom: 1px solid {"rgba(0, 0, 0, 0.28)" if is_light else "rgba(255, 255, 255, 0.26)"};
            }}
            QFrame#settings_section_separator {{
                background-color: {"rgba(0, 0, 0, 0.36)" if is_light else "rgba(255, 255, 255, 0.38)"};
                border: none;
                margin: 0px;
                padding: 0px;
                min-height: 3px;
                max-height: 3px;
            }}
            QLabel#tab_hint_label {{
                font-size: 13px;
                color: #3d74b3;
            }}
        """

    def _apply_detached_theme_style(self, style: str):
        """Применяет тему к отдельным окнам, не входящим в иерархию главного окна."""
        dialog = getattr(self, "_settings_dialog", None)
        if dialog is None:
            return
        try:
            dialog.setStyleSheet(style)
            refresh_standard_field_styles(dialog)
            refresh_standard_surface_styles(dialog)
        except Exception:
            pass

    def apply_dark_style(self):
        """Применяет темный стиль для приложения"""
        checkmark_url = self._checkbox_checkmark_url()
        style = """
            QMainWindow {
                background-color: #2c2c2c;
            }
            QWidget {
                background-color: #2c2c2c;
                font-family: "Segoe UI";
                font-size: 14px;
                font-weight: 600;
            }
            QWidget#top_menu_bar {
                background-color: #2c2c2c;
            }
            QWidget#app_header {
                background-color: #2c2c2c;
            }
            QLineEdit,
            QPlainTextEdit,
            QTextBrowser,
            QTextEdit,
            QSpinBox,
            QDoubleSpinBox,
            QAbstractSpinBox,
            QDateEdit,
            QTimeEdit,
            QDateTimeEdit,
            QComboBox {
                background-color: #383838;
                color: #f0f0f0;
                border: 1px solid #4f4f4f;
            }
            QListWidget, QTableWidget {
                background-color: #383838;
            }
            QFrame#card {
                background-color: transparent;
                border: none;
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
            QFrame#settings_section_separator {
                background-color: rgba(255, 255, 255, 0.38);
                border: none;
                margin: 0px;
                padding: 0px;
                min-height: 3px;
                max-height: 3px;
            }
            QWidget#template_params_widget,
            QFrame#template_numbering_card {
                background-color: #383838;
            }
            QWidget#template_params_widget QLineEdit[renameTemplateField="true"],
            QWidget#template_params_widget QLineEdit[renameTemplateField="true"]:hover,
            QWidget#template_params_widget QLineEdit[renameTemplateField="true"]:focus,
            QWidget#template_params_widget QTextEdit[renameTemplateField="true"],
            QWidget#template_params_widget QTextEdit[renameTemplateField="true"]:hover,
            QWidget#template_params_widget QTextEdit[renameTemplateField="true"]:focus,
            QWidget#template_params_widget QSpinBox[renameTemplateField="true"],
            QWidget#template_params_widget QSpinBox[renameTemplateField="true"]:hover,
            QWidget#template_params_widget QSpinBox[renameTemplateField="true"]:focus,
            QWidget#template_params_widget QToolButton#menu_like_combo[renameTemplateField="true"],
            QWidget#template_params_widget QToolButton#menu_like_combo[renameTemplateField="true"]:hover,
            QWidget#template_params_widget QToolButton#menu_like_combo[renameTemplateField="true"]:focus {
                border: 1px solid #4f4f4f;
                border-radius: 4px;
            }
            QWidget#template_params_widget QLineEdit,
            QWidget#template_params_widget QPlainTextEdit,
            QWidget#template_params_widget QTextEdit,
            QWidget#template_params_widget QTextBrowser,
            QWidget#template_params_widget QSpinBox,
            QWidget#template_params_widget QSpinBox QLineEdit,
            QWidget#template_params_widget QDoubleSpinBox QLineEdit,
            QWidget#template_params_widget QAbstractSpinBox QLineEdit,
            QWidget#template_params_widget QComboBox QLineEdit,
            QWidget#template_params_widget QComboBox,
            QWidget#template_params_widget QToolButton#menu_like_combo {
                border: none;
                border-radius: 4px;
            }
            QWidget#template_params_widget QSpinBox::up-button,
            QWidget#template_params_widget QSpinBox::down-button,
            QWidget#template_params_widget QDoubleSpinBox::up-button,
            QWidget#template_params_widget QDoubleSpinBox::down-button,
            QWidget#template_params_widget QComboBox::drop-down {
                background-color: #383838;
                border: none;
            }
            QWidget#template_params_widget QComboBox {
                padding: 3px;
                min-height: 24px;
                max-height: 24px;
            }
            QWidget#template_params_widget QComboBox::drop-down {
                border: none;
                background-color: #383838;
                width: 18px;
            }
            QFrame#card QPushButton {
                border: none;
                border-radius: 4px;
                background-color: transparent;
            }
            QFrame#card QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.07);
            }
            QFrame#card QPushButton:pressed {
                background-color: rgba(255, 255, 255, 0.12);
            }
QFrame#card QPushButton:disabled {
                background-color: transparent;
            }
            QFrame#card QPushButton#convert_btn,
            QFrame#card QPushButton[text="Конвертировать"],
            QFrame#card QPushButton[text="Сжать файлы"],
            QFrame#card QPushButton[text="Откатить"] {
            }
            QFrame#card QPushButton#convert_btn:hover,
            QFrame#card QPushButton[text="Конвертировать"]:hover,
            QFrame#card QPushButton[text="Сжать файлы"]:hover,
            QFrame#card QPushButton[text="Начать действие"]:hover,
            QFrame#card QPushButton[text="Откатить"]:hover {
            }
            QFrame#card QPushButton#convert_btn:pressed,
            QFrame#card QPushButton[text="Конвертировать"]:pressed,
            QFrame#card QPushButton[text="Сжать файлы"]:pressed,
            QFrame#card QPushButton[text="Начать действие"]:pressed,
            QFrame#card QPushButton[text="Откатить"]:pressed {
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
                border: none;
                border-radius: 10px;
                text-align: center;
                min-height: 26px;
                max-height: 28px;
                background-color: transparent;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.06);
            }
            QPushButton:pressed {
                background-color: rgba(255, 255, 255, 0.10);
            }
QPushButton:disabled {
                background-color: transparent;
            }
            QPushButton#about_program_btn {
                padding: 0px;
                min-height: 0px;
                max-height: 20px;
                border: none;
                border-radius: 0px;
                text-align: center;
            }
            QPushButton#about_program_btn:hover {
                text-decoration: none;
            }
            QPushButton#about_program_btn:pressed {
            }
            QPushButton#top_menu_link_btn {
                padding: 2px 8px;
                min-height: 0px;
                max-height: 22px;
                border: none;
                border-radius: 0px;
            }
            QPushButton#top_menu_link_btn:hover {
                text-decoration: none;
            }
            QPushButton#top_menu_link_btn:pressed {
            }

            QPushButton#convert_btn {
            }
            QPushButton#convert_btn:hover {
            }
            QPushButton#convert_btn:pressed {
            }
QPushButton#convert_btn:disabled {
            }
            QPushButton#cancel_operation_btn {
                border: none;
                border-radius: 10px;
                min-width: 84px;
            }
            QPushButton#cancel_operation_btn:hover {
            }
            QPushButton#cancel_operation_btn:pressed {
            }
QPushButton#cancel_operation_btn:disabled {
            }
            QPushButton[text="Откатить"]:disabled,
            QFrame#card QPushButton[text="Откатить"]:disabled {
            }

            QPushButton[text="Очистить"] {
            }
            QPushButton[text="Очистить"]:hover {
            }
            QPushButton[text="Очистить"]:pressed {
            }

            QPushButton[text="Начать действие"] {
            }
            QPushButton[text="Начать действие"]:hover {
            }
            QPushButton[text="Начать действие"]:pressed {
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
                border: none;
                border-radius: 0px;
                min-height: 34px;
                max-height: 34px;
                background-color: transparent;
            }
            QPushButton[buttonVariant="section"]:hover {
                background-color: rgba(255, 255, 255, 0.06);
            }
            QPushButton[buttonVariant="section"]:checked {
                border: none;
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
                border: 1px solid #4a4a4a;
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
                background-color: #383838;
                color: #f0f0f0;
                border: 1px solid #4f4f4f;
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
            QSpinBox,
            QDoubleSpinBox,
            QAbstractSpinBox,
            QDateEdit,
            QTimeEdit,
            QDateTimeEdit,
            QComboBox {
                padding: 3px;
                min-height: 24px;
                max-height: 24px;
                background-color: #383838;
                color: #f0f0f0;
                border: 1px solid #4f4f4f;
                border-radius: 4px;
            }
            QComboBox::drop-down {
                border-left: 1px solid #4f4f4f;
                border-top-right-radius: 4px;
                border-bottom-right-radius: 4px;
            }
            QComboBox:on {
                border-bottom-left-radius: 0px;
                border-bottom-right-radius: 0px;
            }
            QComboBox:on::drop-down {
                border-bottom-right-radius: 0px;
            }
            QComboBox:hover {
                border: 1px solid #4f4f4f;
            }
            QToolButton#menu_like_combo {
                font-size: 14px;
                padding: 3px;
                min-height: 24px;
                max-height: 24px;
                border: 1px solid #4f4f4f;
                border-radius: 4px;
                text-align: left;
                padding-left: 6px;
            }
            QToolButton#menu_like_combo[menuOpen="true"] {
                border-bottom-left-radius: 0px;
                border-bottom-right-radius: 0px;
            }
            QToolButton#menu_like_combo::menu-indicator {
                subcontrol-origin: padding;
                subcontrol-position: right center;
                right: 6px;
            }
            QToolButton#menu_like_combo:hover {
                border: 1px solid #4f4f4f;
            }
            QToolButton#menu_like_combo[renameTemplateField="true"],
            QToolButton#menu_like_combo[renameTemplateField="true"]:hover,
            QToolButton#menu_like_combo[renameTemplateField="true"]:focus,
            QWidget#template_params_widget QSpinBox[renameTemplateField="true"],
            QWidget#template_params_widget QSpinBox[renameTemplateField="true"]:hover,
            QWidget#template_params_widget QSpinBox[renameTemplateField="true"]:focus {
                border: none;
                border-radius: 0px;
            }
            QComboBox QAbstractItemView {
                background-color: #383838;
                color: #f0f0f0;
                border: 1px solid #4f4f4f;
                outline: 0px;
                border-radius: 0px;
                padding: 0px;
                margin: 0px;
            }
            QComboBox QListView {
                background-color: #383838;
                color: #f0f0f0;
                border: 1px solid #4f4f4f;
                border-radius: 0px;
                margin: 0px;
                padding: 0px;
                outline: 0px;
            }
            QComboBox QListView::viewport {
                background-color: #383838;
                margin: 0px;
                padding: 0px;
            }
            QComboBox QAbstractItemView::item {
                padding: 4px 8px;
                margin: 0px;
                background-color: transparent;
                color: #f0f0f0;
            }
            QComboBox QAbstractItemView::item:hover,
            QComboBox QAbstractItemView::item:selected {
                background-color: rgba(255, 255, 255, 0.07);
                color: #f0f0f0;
            }
            QMenu {
                background-color: #383838;
                color: #f0f0f0;
                border: 1px solid #4f4f4f;
                margin: 0px;
                padding: 0px;
                border-radius: 0px;
            }
            QMenu#menu_like_combo_popup,
            QMenu#header_dropdown_popup {
                background-color: #383838;
                border: 1px solid #4f4f4f;
                margin: 0px;
                padding: 0px;
                border-radius: 0px;
            }
            QMenu#menu_like_combo_popup {
                border-top-left-radius: 0px;
                border-top-right-radius: 0px;
                border-bottom-left-radius: 4px;
                border-bottom-right-radius: 4px;
            }
            QMenu#header_dropdown_popup {
                border-top-left-radius: 0px;
                border-top-right-radius: 0px;
                border-bottom-left-radius: 4px;
                border-bottom-right-radius: 4px;
            }
            QMenu::item {
                padding: 4px 8px;
                margin: 1px 0px;
                background-color: transparent;
            }
            QMenu::item:selected {
                background-color: #3d74b3;
                color: #ffffff;
            }
            QMenu::separator {
                height: 1px;
                background: rgba(255, 255, 255, 0.18);
            }
            QToolButton#header_cell_tl,
            QToolButton#header_cell_tr,
            QToolButton#header_cell_bl {
                font-size: 13px;
                padding: 2px;
                padding-left: 8px;
                min-height: 20px;
                max-height: 20px;
                border: 1px solid #4f4f4f;
                border-radius: 4px;
                text-align: left;
            }
            QToolButton#header_cell_tl[menuOpen="true"],
            QToolButton#header_cell_tr[menuOpen="true"],
            QToolButton#header_cell_bl[menuOpen="true"] {
                border-bottom-left-radius: 0px;
                border-bottom-right-radius: 0px;
            }
            QLineEdit#header_cell_br {
                font-size: 13px;
                padding: 2px;
                min-height: 20px;
                max-height: 20px;
                background-color: #383838;
                color: #f0f0f0;
                border: 1px solid #4f4f4f;
                border-radius: 4px;
            }
            QToolButton#header_cell_tl::menu-indicator,
            QToolButton#header_cell_tr::menu-indicator,
            QToolButton#header_cell_bl::menu-indicator {
                subcontrol-origin: padding;
                subcontrol-position: right center;
                right: 6px;
            }
            QToolButton#header_cell_tl:pressed,
            QToolButton#header_cell_tr:pressed,
            QToolButton#header_cell_bl:pressed {
            }
            /* Single grid lines between adjacent controls (no doubled borders). */
            QToolButton#header_cell_tl {
                border-right: 0px;
            }
            QToolButton#header_cell_tr {
                border-left: 0px;
            }
            QToolButton#header_cell_bl {
                border-right: 0px;
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
                background-color: #383838;
                color: #f0f0f0;
                border: 1px solid #4f4f4f;
                border-radius: 0px;
            }
            QLineEdit::placeholder {
                color: #b4bcc6;
            }
            QPlainTextEdit {
                font-size: 14px;
                background-color: #383838;
                color: #f0f0f0;
                border: 1px solid #4f4f4f;
                border-radius: 4px;
            }
            QPlainTextEdit#logs_view {
                border-radius: 4px;
            }
            QPlainTextEdit#logs_view::corner {
                background: #383838;
                border-bottom-right-radius: 4px;
            }
            QPlainTextEdit:focus {
                border: 1px solid #3d74b3;
                border-radius: 4px;
            }
            QPlainTextEdit#logs_view:focus {
                border: 1px solid #3d74b3;
                border-radius: 4px;
            }
            QSpinBox {
                font-size: 14px;
                padding: 3px;
                min-height: 24px;
                max-height: 24px;
                background-color: #383838;
                color: #f0f0f0;
                border: 1px solid #4f4f4f;
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
                background: #3d74b3;
                width: 12px;
                height: 12px;
                margin: -4px 0;
                border-radius: 6px;
            }
            QListWidget {
                font-size: 13px;
                background-color: #383838;
                color: #f0f0f0;
                border: 1px solid #4f4f4f;
                border-radius: 0px;
            }
            QListWidget#rename_history_list {
                background-color: #383838;
                color: #f0f0f0;
                border: 1px solid #4f4f4f;
                border-radius: 4px;
            }
            QListView {
                font-size: 13px;
                background-color: #383838;
                color: #f0f0f0;
                border: 1px solid #4f4f4f;
                border-radius: 0px;
            }
            QListView::item {
                padding: 2px 4px;
                min-height: 22px;
                color: #f0f0f0;
            }
            QListView::item:selected {
                background-color: transparent;
                color: #f0f0f0;
            }
            QListView#files_list,
            QListWidget#files_list {
                background-color: #383838;
                alternate-background-color: #383838;
                color: #f0f0f0;
                border-radius: 4px;
                show-decoration-selected: 1;
            }
            QListView#files_list::item,
            QListWidget#files_list::item {
                background-color: #383838;
                color: #f0f0f0;
            }
            QListView#files_list::item:alternate,
            QListWidget#files_list::item:alternate {
                background-color: #383838;
                color: #f0f0f0;
            }
            QListView#files_list::item:hover,
            QListWidget#files_list::item:hover {
                background-color: rgba(255, 255, 255, 0.07);
                color: #f0f0f0;
            }
            QListView#files_list::item:selected,
            QListWidget#files_list::item:selected,
            QListView#files_list::item:selected:active,
            QListWidget#files_list::item:selected:active,
            QListView#files_list::item:selected:!active,
            QListWidget#files_list::item:selected:!active {
                background-color: rgba(255, 255, 255, 0.20);
                color: #f0f0f0;
                selection-color: #f0f0f0;
            }
            QListWidget::item {
                padding: 3px;
                color: #f0f0f0;
            }
            QListWidget::item:selected {
                background-color: #3d74b3;
                color: white;
            }
            QListWidget#settings_nav {
                background-color: transparent;
                border: none;
                border-radius: 0px;
                padding: 0px;
                margin: 0px;
                outline: 0px;
            }
            QListWidget#settings_nav::item {
                padding: 0px 7px;
                margin: 0px;
                border-radius: 4px;
                color: #ffffff;
                font-family: "Segoe UI";
                font-size: 13px;
                font-weight: 400;
                background-color: transparent;
                border: none;
                min-height: 36px;
                max-height: 36px;
            }
            QListWidget#settings_nav::item:hover {
                background-color: rgba(255, 255, 255, 0.07);
                color: #ffffff;
                border-radius: 0px;
            }
            QListWidget#settings_nav::item:selected {
                background-color: rgba(255, 255, 255, 0.12);
                color: #ffffff;
                font-weight: 400;
                border-radius: 0px;
                border: none;
            }
            QTabWidget::pane {
                border: none;
                border-radius: 0px;
                background-color: #2c2c2c;
            }
            QTabBar::tab {
                padding: 2px 7px;
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
                background-color: #3b3f46;
            }
            QProgressBar {
                font-size: 14px;
                min-height: 26px;
                max-height: 26px;
                background-color: #353535;
                color: #e0e0e0;
                border: 1px solid #4a4a4a;
                border-radius: 0px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #3d74b3;
                border-radius: 0px;
            }
            QStatusBar {
                font-size: 13px;
                background-color: #2c2c2c;
                color: #e0e0e0;
            }
            QMessageBox {
                background-color: #2c2c2c;
            }
            QMessageBox QLabel {
                font-size: 13px;
                color: #e0e0e0;
            }
            QMessageBox QPushButton {
                min-height: 22px;
                max-height: 22px;
                font-size: 13px;
                border-radius: 4px;
            }
            QMessageBox QPushButton:hover {
            }
            QMessageBox QPushButton:pressed {
            }
            QScrollArea {
                border: none;
                background-color: #2c2c2c;
            }
            QScrollArea QWidget#qt_scrollarea_viewport {
                background-color: #2c2c2c;
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
                background-color: #383838;
                color: #f0f0f0;
                border: 1px solid #4f4f4f;
                border-radius: 6px;
            }
            QTableWidget::item {
                padding: 3px;
                color: #f0f0f0;
            }
            QTableWidget::item:selected {
                background-color: #3d74b3;
                color: white;
            }
            QHeaderView::section {
                background-color: #2b2b2b;
                color: #e0e0e0;
                padding: 4px;
                border: 1px solid #4f4f4f;
            }
            /* Keep dropdown popup consistent with the dark field color. */
            QComboBox QAbstractItemView,
            QComboBox QListView,
            QComboBox QListView::viewport {
                background-color: #383838;
                color: #f0f0f0;
                font-family: "Segoe UI";
                font-size: 14px;
                font-weight: 600;
                border: 1px solid #4f4f4f;
                border-radius: 0px;
                margin: 0px;
                padding: 0px;
                outline: 0px;
            }
            QComboBox QAbstractItemView::item {
                padding: 6px 10px;
                margin: 0px;
                background-color: transparent;
                color: #f0f0f0;
            }
            QComboBox QAbstractItemView::item:hover,
            QComboBox QAbstractItemView::item:selected {
                background-color: rgba(255, 255, 255, 0.07);
                color: #f0f0f0;
            }
            QPushButton[buttonVariant="secondary"] {
                border: none;
                border-radius: 10px;
            }
            QPushButton[buttonVariant="secondary"]:hover {
            }
            QPushButton[buttonVariant="secondary"]:pressed {
            }
            QPushButton[buttonVariant="secondary"]:disabled {
            }
            QPushButton[buttonVariant="primary"] {
                border: none;
                border-radius: 10px;
            }
            QPushButton[buttonVariant="primary"]:hover {
            }
            QPushButton[buttonVariant="primary"]:pressed {
            }
            QPushButton[buttonVariant="primary"]:disabled {
            }
            QPushButton[buttonVariant="danger"] {
                border: none;
                border-radius: 10px;
            }
            QPushButton[buttonVariant="danger"]:hover {
            }
            QPushButton[buttonVariant="danger"]:pressed {
            }
            QPushButton[buttonVariant="danger"]:disabled {
            }
            QPushButton[buttonVariant="link"] {
                border: none;
                border-radius: 0px;
                padding: 2px 8px;
                min-height: 0px;
                max-height: 22px;
            }
            QPushButton[buttonVariant="link"]:hover {
                text-decoration: underline;
            }
            QPushButton[buttonVariant="link"]:pressed {
            }
        """
        style += self._tab_content_style_block("dark")
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
                background-color: transparent;
                border: none;
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
            QFrame#settings_section_separator {
                background-color: rgba(0, 0, 0, 0.36);
                border: none;
                margin: 0px;
                padding: 0px;
                min-height: 3px;
                max-height: 3px;
            }
            QWidget#template_params_widget {
                background-color: #383838;
            }
            QWidget#template_params_widget QLineEdit[renameTemplateField="true"],
            QWidget#template_params_widget QLineEdit[renameTemplateField="true"]:hover,
            QWidget#template_params_widget QLineEdit[renameTemplateField="true"]:focus,
            QWidget#template_params_widget QTextEdit[renameTemplateField="true"],
            QWidget#template_params_widget QTextEdit[renameTemplateField="true"]:hover,
            QWidget#template_params_widget QTextEdit[renameTemplateField="true"]:focus,
            QWidget#template_params_widget QSpinBox[renameTemplateField="true"],
            QWidget#template_params_widget QSpinBox[renameTemplateField="true"]:hover,
            QWidget#template_params_widget QSpinBox[renameTemplateField="true"]:focus,
            QWidget#template_params_widget QToolButton#menu_like_combo[renameTemplateField="true"],
            QWidget#template_params_widget QToolButton#menu_like_combo[renameTemplateField="true"]:hover,
            QWidget#template_params_widget QToolButton#menu_like_combo[renameTemplateField="true"]:focus {
                border: 1px solid #c7cfda;
                border-radius: 4px;
            }
            QWidget#template_params_widget QLineEdit,
            QWidget#template_params_widget QPlainTextEdit,
            QWidget#template_params_widget QTextEdit,
            QWidget#template_params_widget QTextBrowser,
            QWidget#template_params_widget QSpinBox,
            QWidget#template_params_widget QSpinBox QLineEdit,
            QWidget#template_params_widget QDoubleSpinBox QLineEdit,
            QWidget#template_params_widget QAbstractSpinBox QLineEdit,
            QWidget#template_params_widget QComboBox QLineEdit,
            QWidget#template_params_widget QComboBox,
            QWidget#template_params_widget QToolButton#menu_like_combo {
                border: none;
                border-radius: 4px;
            }
            QWidget#template_params_widget QSpinBox::up-button,
            QWidget#template_params_widget QSpinBox::down-button,
            QWidget#template_params_widget QDoubleSpinBox::up-button,
            QWidget#template_params_widget QDoubleSpinBox::down-button,
            QWidget#template_params_widget QComboBox::drop-down {
                background-color: #383838;
                border: none;
            }
            QWidget#template_params_widget QComboBox {
                padding: 3px;
                min-height: 24px;
                max-height: 24px;
            }
            QWidget#template_params_widget QComboBox::drop-down {
                border: none;
                background-color: #383838;
                width: 18px;
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
                border: none;
                border-radius: 10px;
                text-align: center;
                min-height: 26px;
                max-height: 28px;
            }
            QPushButton:hover {
            }
            QPushButton:pressed {
            }
            QPushButton:disabled {
            }
            QPushButton#about_program_btn {
                padding: 0px;
                min-height: 0px;
                max-height: 20px;
                border: none;
                border-radius: 0px;
                text-align: center;
            }
            QPushButton#about_program_btn:hover {
                text-decoration: underline;
            }
            QPushButton#about_program_btn:pressed {
            }
            QPushButton#top_menu_link_btn {
                padding: 2px 8px;
                min-height: 0px;
                max-height: 22px;
                border: none;
                border-radius: 0px;
            }
            QPushButton#top_menu_link_btn:hover {
                text-decoration: underline;
            }
            QPushButton#top_menu_link_btn:pressed {
            }
            QPushButton#convert_btn {
            }
            QPushButton#convert_btn:hover {
            }
            QPushButton#convert_btn:pressed {
            }
            QPushButton#convert_btn:disabled {
            }
            QPushButton#cancel_operation_btn {
                border: none;
                border-radius: 4px;
                min-width: 84px;
            }
            QPushButton#cancel_operation_btn:hover {
            }
            QPushButton#cancel_operation_btn:pressed {
            }
            QPushButton#cancel_operation_btn:disabled {
            }
            QPushButton[text="Очистить"] {
            }
            QPushButton[text="Очистить"]:hover {
            }
            QPushButton[text="Очистить"]:pressed {
            }
            QPushButton[text="Начать действие"] {
            }
            QPushButton[text="Начать действие"]:hover {
            }
            QPushButton[text="Начать действие"]:pressed {
            }
            QPushButton[buttonVariant="section"] {
                text-align: left;
                padding: 2px 10px;
                font-size: 14px;
                font-weight: bold;
                border: none;
                border-radius: 0px;
                min-height: 34px;
                max-height: 34px;
            }
            QPushButton[buttonVariant="section"]:hover {
            }
            QPushButton[buttonVariant="section"]:checked {
                border: none;
                border-bottom-left-radius: 0px;
                border-bottom-right-radius: 0px;
            }
            QLineEdit,
            QPlainTextEdit,
            QTextBrowser,
            QTextEdit,
            QSpinBox,
            QDoubleSpinBox,
            QAbstractSpinBox,
            QDateEdit,
            QTimeEdit,
            QDateTimeEdit,
            QComboBox {
                background-color: #ffffff;
                color: #1f2328;
                border: 1px solid #c7cfda;
                border-radius: 4px;
            }
            QComboBox::drop-down {
                border-left: 1px solid #c7cfda;
                border-top-right-radius: 4px;
                border-bottom-right-radius: 4px;
            }
            QComboBox:on {
                border-bottom-left-radius: 0px;
                border-bottom-right-radius: 0px;
            }
            QComboBox:on::drop-down {
                border-bottom-right-radius: 0px;
            }
            QComboBox {
                background-color: #ffffff;
                color: #1f2328;
                border: 1px solid #c7cfda;
                border-radius: 4px;
            }
            QListWidget, QTableWidget {
                background-color: #f8fafc;
                color: #1f2328;
                border: 1px solid #c7cfda;
                border-radius: 0px;
            }
            QLineEdit,
            QComboBox,
            QSpinBox,
            QDoubleSpinBox,
            QAbstractSpinBox,
            QDateEdit,
            QTimeEdit,
            QDateTimeEdit {
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
                border: 1px solid #c7cfda;
                border-radius: 4px;
                text-align: left;
                padding-left: 6px;
            }
            QToolButton#menu_like_combo[menuOpen="true"] {
                border-bottom-left-radius: 0px;
                border-bottom-right-radius: 0px;
            }
            QToolButton#menu_like_combo::menu-indicator {
                subcontrol-origin: padding;
                subcontrol-position: right center;
                right: 6px;
            }
            QToolButton#menu_like_combo:hover {
                border: 1px solid #aab5c3;
            }
            QToolButton#menu_like_combo:disabled {
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
                border: 1px solid #c7cfda;
                border-radius: 4px;
                text-align: left;
            }
            QToolButton#header_cell_tl[menuOpen="true"],
            QToolButton#header_cell_tr[menuOpen="true"],
            QToolButton#header_cell_bl[menuOpen="true"] {
                border-bottom-left-radius: 0px;
                border-bottom-right-radius: 0px;
            }
            QLineEdit#header_cell_br {
                font-size: 14px;
                padding: 3px;
                min-height: 24px;
                max-height: 24px;
                background-color: #ffffff;
                color: #1f2328;
                border: 1px solid #c7cfda;
                border-radius: 4px;
            }
            QToolButton#header_cell_tr {
                border-left: 0px;
            }
            QToolButton#header_cell_tl {
                border-right: 0px;
            }
            QToolButton#header_cell_bl {
                border-right: 0px;
                border-top: 0px;
                border-bottom: 0px;
            }
            QLineEdit#header_cell_br {
                border-left: 0px;
                border-top: 0px;
                border-bottom: 0px;
            }
            QListWidget#settings_nav {
                background-color: transparent;
                border: none;
                border-radius: 0px;
                padding: 0px;
                margin: 0px;
                outline: 0px;
            }
            QListWidget#settings_nav::item {
                padding: 0px 7px;
                margin: 0px;
                border-radius: 4px;
                color: #1f2328;
                font-family: "Segoe UI";
                font-size: 13px;
                font-weight: 400;
                background-color: transparent;
                border: none;
                min-height: 36px;
                max-height: 36px;
            }
            QListWidget#settings_nav::item:hover {
                background-color: rgba(61, 116, 179, 0.10);
                color: #1f2328;
                border-radius: 0px;
            }
            QListWidget#settings_nav::item:selected {
                background-color: rgba(61, 116, 179, 0.18);
                color: #1f2328;
                font-weight: 400;
                border-radius: 0px;
                border: none;
            }
            /* Force light dropdown popup even in dark theme (override generic QListView). */
            QComboBox QAbstractItemView,
            QComboBox QListView,
            QComboBox QListView::viewport {
                background-color: #ffffff;
                color: #1f2328;
                border: 1px solid #c7cfda;
                border-radius: 4px;
                margin: 0px;
                padding: 0px;
                outline: 0px;
            }
            QComboBox:on {
                border-bottom-left-radius: 0px;
                border-bottom-right-radius: 0px;
            }
            QComboBox:on::drop-down {
                border-bottom-right-radius: 0px;
            }
            QComboBox QAbstractItemView::item {
                padding: 4px 8px;
                margin: 1px 0px;
                background-color: transparent;
                color: #1f2328;
            }
            QComboBox QAbstractItemView::item:hover,
            QComboBox QAbstractItemView::item:selected {
                background-color: rgba(61, 116, 179, 0.10);
                color: #1f2328;
            }
            QListWidget {
                font-size: 13px;
                background-color: #ffffff;
                color: #1f2328;
                border: 1px solid #c7cfda;
                border-radius: 0px;
            }
            QListWidget#rename_history_list {
                background-color: #ffffff;
                color: #1f2328;
                border: 1px solid #c7cfda;
                border-radius: 4px;
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
                alternate-background-color: #3d74b3;
                color: #1f2328;
                border-radius: 4px;
                show-decoration-selected: 1;
            }
            QListView#files_list::item,
            QListWidget#files_list::item {
                background-color: #f3f3f3;
                color: #1f2328;
            }
            QListView#files_list::item:alternate,
            QListWidget#files_list::item:alternate {
                background-color: #3d74b3;
                color: #ffffff;
            }
            QListView#files_list::item:hover,
            QListWidget#files_list::item:hover {
                background-color: rgba(61, 116, 179, 0.10);
                color: #1f2328;
            }
            QListView#files_list::item:selected,
            QListWidget#files_list::item:selected,
            QListView#files_list::item:selected:active,
            QListWidget#files_list::item:selected:active,
            QListView#files_list::item:selected:!active,
            QListWidget#files_list::item:selected:!active {
                background-color: rgba(61, 116, 179, 0.22);
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
                background-color: #3d74b3;
                color: #ffffff;
            }
            QListWidget::item {
                padding: 3px;
                color: #1f2328;
            }
            QListWidget::item:selected {
                background-color: #3d74b3;
                color: #ffffff;
            }
            QMenu, QMenu#menu_like_combo_popup, QMenu#header_dropdown_popup {
                background-color: #ffffff;
                color: #1f2328;
                border: 1px solid #c7cfda;
                margin: 0px;
                padding: 0px;
                border-radius: 0px;
            }
            QMenu#menu_like_combo_popup {
                border-top-left-radius: 0px;
                border-top-right-radius: 0px;
                border-bottom-left-radius: 4px;
                border-bottom-right-radius: 4px;
            }
            QMenu#header_dropdown_popup {
                border-top-left-radius: 0px;
                border-top-right-radius: 0px;
                border-bottom-left-radius: 4px;
                border-bottom-right-radius: 4px;
            }
            QMenu::item {
                padding: 4px 8px;
                margin: 1px 0px;
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
                border: none;
                background-color: transparent;
            }
            QPushButton:hover,
            QFrame#card QPushButton:hover {
                background-color: rgba(61, 116, 179, 0.10);
            }
            QPushButton:pressed,
            QFrame#card QPushButton:pressed {
                background-color: rgba(61, 116, 179, 0.18);
            }
            QPushButton:disabled,
            QFrame#card QPushButton:disabled {
                background-color: transparent;
            }
            QPushButton#convert_btn,
            QFrame#card QPushButton#convert_btn,
            QPushButton[text="Конвертировать"],
            QFrame#card QPushButton[text="Конвертировать"],
            QPushButton[text="Сжать файлы"],
            QFrame#card QPushButton[text="Сжать файлы"],
            QPushButton[text="Начать действие"],
            QPushButton[text="Откатить"],
            QFrame#card QPushButton[text="Откатить"] {
            }
            QPushButton#convert_btn:hover,
            QFrame#card QPushButton#convert_btn:hover,
            QPushButton[text="Конвертировать"]:hover,
            QFrame#card QPushButton[text="Конвертировать"]:hover,
            QPushButton[text="Сжать файлы"]:hover,
            QFrame#card QPushButton[text="Сжать файлы"]:hover,
            QPushButton[text="Начать действие"]:hover,
            QFrame#card QPushButton[text="Начать действие"]:hover,
            QPushButton[text="Откатить"]:hover,
            QFrame#card QPushButton[text="Откатить"]:hover {
            }
            QPushButton#convert_btn:pressed,
            QFrame#card QPushButton#convert_btn:pressed,
            QPushButton[text="Конвертировать"]:pressed,
            QFrame#card QPushButton[text="Конвертировать"]:pressed,
            QPushButton[text="Сжать файлы"]:pressed,
            QFrame#card QPushButton[text="Сжать файлы"]:pressed,
            QPushButton[text="Начать действие"]:pressed,
            QFrame#card QPushButton[text="Начать действие"]:pressed,
            QPushButton[text="Откатить"]:pressed,
            QFrame#card QPushButton[text="Откатить"]:pressed {
            }
            QPushButton[text="Конвертировать"]:disabled,
            QFrame#card QPushButton[text="Конвертировать"]:disabled,
            QPushButton[text="Откатить"]:disabled,
            QFrame#card QPushButton[text="Откатить"]:disabled {
            }
            QPushButton[text="Начать действие"],
            QFrame#card QPushButton[text="Начать действие"] {
            }
            QPushButton[text="Начать действие"]:hover,
            QFrame#card QPushButton[text="Начать действие"]:hover {
            }
            QPushButton[text="Начать действие"]:pressed,
            QFrame#card QPushButton[text="Начать действие"]:pressed {
            }
            QPushButton[text="Откатить"]:disabled,
            QFrame#card QPushButton[text="Откатить"]:disabled {
            }
            QPushButton[text="Очистить"],
            QFrame#card QPushButton[text="Очистить"] {
            }
            QPushButton[text="Очистить"]:hover,
            QFrame#card QPushButton[text="Очистить"]:hover {
            }
            QPushButton[text="Очистить"]:pressed,
            QFrame#card QPushButton[text="Очистить"]:pressed {
            }
            QPushButton#about_program_btn,
            QPushButton#top_menu_link_btn {
                border: none;
            }
            QPushButton[buttonVariant="secondary"] {
                border: none;
                border-radius: 10px;
            }
            QPushButton[buttonVariant="secondary"]:hover {
            }
            QPushButton[buttonVariant="secondary"]:pressed {
            }
            QPushButton[buttonVariant="secondary"]:disabled {
            }
            QPushButton[buttonVariant="primary"] {
                border: none;
                border-radius: 10px;
            }
            QPushButton[buttonVariant="primary"]:hover {
            }
            QPushButton[buttonVariant="primary"]:pressed {
            }
            QPushButton[buttonVariant="primary"]:disabled {
            }
            QPushButton[buttonVariant="danger"] {
                border: none;
                border-radius: 10px;
            }
            QPushButton[buttonVariant="danger"]:hover {
            }
            QPushButton[buttonVariant="danger"]:pressed {
            }
            QPushButton[buttonVariant="danger"]:disabled {
            }
            QPushButton[buttonVariant="link"] {
                border: none;
                border-radius: 0px;
                padding: 2px 8px;
                min-height: 0px;
                max-height: 22px;
            }
            QPushButton[buttonVariant="link"]:hover {
                text-decoration: underline;
            }
            QPushButton[buttonVariant="link"]:pressed {
            }
        """
        style += self._tab_content_style_block("light")
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
        layout.setContentsMargins(*MESSAGE_DIALOG_MARGINS)
        layout.setSpacing(SPACE_2XL)

        content_row = QHBoxLayout()
        content_row.setContentsMargins(*MARGINS_NONE)
        content_row.setSpacing(SPACE_XL)

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
        buttons_row.setContentsMargins(*MARGINS_NONE)
        buttons_row.setSpacing(SPACE_LG)
        buttons_row.addStretch()

        yes_button = QPushButton("Да")
        setup_standard_secondary_button(yes_button, height=LINK_BUTTON_HEIGHT)
        yes_button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        no_button = QPushButton("Нет")
        setup_standard_secondary_button(no_button, height=LINK_BUTTON_HEIGHT)
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




