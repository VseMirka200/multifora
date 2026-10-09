"""Базовые QSS-темы. Общее оформление полей и кнопок дополняется в ui_styles."""

DARK_APPLICATION_STYLE = """
QMainWindow {
    background-color: #2c2c2c;
}
QWidget {
    background-color: #2c2c2c;
    color: #e0e0e0;
    font-family: "Segoe UI";
    font-size: 14px;
    font-weight: 600;
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
QFrame#settings_card QLabel[settingsHint="true"] {
    color: #a8a8a8;
    font-size: 11px;
    font-weight: 400;
}
QFrame#settings_card QLabel[aboutVersionBadge="true"] {
    background-color: #383838;
    color: #c9d1d9;
    border: 1px solid #555555;
    border-radius: 10px;
    padding: 3px 10px;
    font-size: 12px;
    font-weight: 600;
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
    color: #a8a8a8;
}
QPushButton {
    padding: 3px 10px;
    color: #e0e0e0;
    font-size: 14px;
    font-weight: normal;
    border: none;
    border-radius: 10px;
    text-align: center;
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
    color: #a8a8a8;
}
QPushButton#cancel_operation_btn {
    border: none;
    border-radius: 10px;
    min-width: 84px;
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
QLabel:disabled,
QCheckBox:disabled {
    color: #a8a8a8;
}
QComboBox {
    font-size: 14px;
    padding: 3px;
    background-color: #383838;
    color: #f0f0f0;
    border: 1px solid #4f4f4f;
    border-radius: 0px;
}
QLineEdit,
QSpinBox {
    font-size: 14px;
    padding: 3px;
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
QToolButton#menu_like_combo[renameTemplateField="true"],
QToolButton#menu_like_combo[renameTemplateField="true"]:hover,
QToolButton#menu_like_combo[renameTemplateField="true"]:focus,
QWidget#template_params_widget QSpinBox[renameTemplateField="true"],
QWidget#template_params_widget QSpinBox[renameTemplateField="true"]:hover,
QWidget#template_params_widget QSpinBox[renameTemplateField="true"]:focus {
    border: none;
    border-radius: 0px;
}
QLineEdit {
    font-size: 14px;
    padding: 3px;
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
QListWidget::item {
    padding: 3px;
    color: #f0f0f0;
}
QListWidget::item:selected {
    background-color: #3d74b3;
    color: white;
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
    font-size: 13px;
    border-radius: 4px;
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
"""

LIGHT_APPLICATION_STYLE = """
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
QFrame#settings_card QLabel[settingsHint="true"] {
    color: #6f7785;
    font-size: 11px;
    font-weight: 400;
}
QFrame#settings_card QLabel[aboutVersionBadge="true"] {
    background-color: #ffffff;
    color: #57606a;
    border: 1px solid #d0d7de;
    border-radius: 10px;
    padding: 3px 10px;
    font-size: 12px;
    font-weight: 600;
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
    background-color: transparent;
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
    background-color: #ffffff;
    border: none;
}
QWidget#template_params_widget QComboBox {
    padding: 3px;
}
QWidget#template_params_widget QComboBox::drop-down {
    border: none;
    background-color: #ffffff;
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
QLabel {
    color: #1f2328;
}
QPushButton {
    padding: 3px 10px;
    color: #1f2328;
    font-size: 14px;
    font-weight: normal;
    border: none;
    border-radius: 10px;
    text-align: center;
}
QPushButton:disabled {
    color: #6f7785;
}
QPushButton#cancel_operation_btn {
    border: none;
    border-radius: 4px;
    min-width: 84px;
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
}
QLineEdit::placeholder {
    color: #6f7785;
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
QLabel:disabled,
QCheckBox:disabled {
    color: #6f7785;
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
/* Neutral button interaction states for light theme */
QPushButton,
QFrame#card QPushButton {
    border: none;
    background-color: transparent;
}
QPushButton:hover,
QFrame#card QPushButton:hover {
    background-color: rgba(0, 0, 0, 0.06);
}
QPushButton:pressed,
QFrame#card QPushButton:pressed {
    background-color: rgba(0, 0, 0, 0.10);
}
QPushButton:disabled,
QFrame#card QPushButton:disabled {
    background-color: transparent;
}
"""


def _build_global_dropdown_style(
    *,
    background: str,
    foreground: str,
    border: str,
    hover: str,
    separator: str,
    disabled: str,
    scroll_track: str,
    scroll_handle: str,
    scroll_handle_hover: str,
) -> str:
    """Единое оформление всех раскрывающихся меню и списков приложения."""
    return f"""
QMenu {{
    background-color: {background};
    color: {foreground};
    border: 1px solid {border};
    margin: 0px;
    padding: 0px;
    border-radius: 0px;
}}
QMenu#menu_like_combo_popup,
QMenu#header_dropdown_popup,
QMenu#help_menu_popup {{
    border-top-left-radius: 0px;
    border-top-right-radius: 0px;
    border-bottom-left-radius: 4px;
    border-bottom-right-radius: 4px;
    padding-bottom: 0px;
}}
QMenu::item,
QMenu QListWidget#scrollable_filter_list::item {{
    padding: 4px 8px;
    margin: 0px;
    border: 0px;
    background-color: {background};
    color: {foreground};
}}
QMenu#header_dropdown_popup::item {{
    padding-left: 4px;
    padding-right: 4px;
}}
QMenu#help_menu_popup::item {{
    min-height: 18px;
    max-height: 18px;
    padding: 0px 4px;
    font-size: 12px;
    font-weight: 500;
}}
QMenu::item:hover,
QMenu::item:selected,
QMenu QListWidget#scrollable_filter_list::item:hover {{
    background-color: {hover};
    color: {foreground};
}}
QMenu::item:disabled {{
    background-color: {background};
    color: {disabled};
}}
QMenu::separator {{
    height: 1px;
    background: {separator};
}}
QMenu QListWidget#scrollable_filter_list {{
    background-color: {background};
    color: {foreground};
    border: 0px;
    outline: 0px;
    padding: 0px;
}}
QMenu QListWidget#scrollable_filter_list QScrollBar:vertical {{
    background-color: {scroll_track};
    border: 0px;
    width: 14px;
    margin: 14px 0px 14px 0px;
}}
QMenu QListWidget#scrollable_filter_list QScrollBar::handle:vertical {{
    background-color: {scroll_handle};
    border: 0px;
    border-radius: 3px;
    min-height: 20px;
}}
QMenu QListWidget#scrollable_filter_list QScrollBar::handle:vertical:hover {{
    background-color: {scroll_handle_hover};
}}
QMenu QListWidget#scrollable_filter_list QScrollBar::sub-line:vertical,
QMenu QListWidget#scrollable_filter_list QScrollBar::add-line:vertical {{
    background-color: {scroll_track};
    border: 0px;
    height: 14px;
    width: 14px;
    subcontrol-origin: margin;
}}
QMenu QListWidget#scrollable_filter_list QScrollBar::sub-line:vertical {{
    subcontrol-position: top;
}}
QMenu QListWidget#scrollable_filter_list QScrollBar::add-line:vertical {{
    subcontrol-position: bottom;
}}
QMenu QListWidget#scrollable_filter_list QScrollBar::up-arrow:vertical {{
    image: url("__SCROLL_UP_URL__");
    width: 8px;
    height: 8px;
}}
QMenu QListWidget#scrollable_filter_list QScrollBar::down-arrow:vertical {{
    image: url("__SCROLL_DOWN_URL__");
    width: 8px;
    height: 8px;
}}
QMenu QListWidget#scrollable_filter_list QScrollBar::add-page:vertical,
QMenu QListWidget#scrollable_filter_list QScrollBar::sub-page:vertical {{
    background-color: {scroll_track};
}}
QComboBox QAbstractItemView,
QComboBox QListView,
QComboBox QListView::viewport {{
    background-color: {background};
    color: {foreground};
    border: 1px solid {border};
    border-top-left-radius: 0px;
    border-top-right-radius: 0px;
    border-bottom-left-radius: 4px;
    border-bottom-right-radius: 4px;
    outline: 0px;
    margin: 0px;
    padding: 0px;
}}
QComboBox QAbstractItemView::item {{
    padding: 4px 8px;
    margin: 0px;
    background-color: transparent;
    color: {foreground};
}}
QComboBox QAbstractItemView::item:hover,
QComboBox QAbstractItemView::item:selected {{
    background-color: {hover};
    color: {foreground};
}}
"""


DARK_APPLICATION_STYLE += _build_global_dropdown_style(
    background="#383838",
    foreground="#f0f0f0",
    border="#4f4f4f",
    hover="#464646",
    separator="rgba(255, 255, 255, 0.18)",
    disabled="#a8a8a8",
    scroll_track="#2f2f2f",
    scroll_handle="#777777",
    scroll_handle_hover="#909090",
)
LIGHT_APPLICATION_STYLE += _build_global_dropdown_style(
    background="#ffffff",
    foreground="#1f2328",
    border="#c7cfda",
    hover="#ecf1f7",
    separator="rgba(0, 0, 0, 0.2)",
    disabled="#6f7785",
    scroll_track="#eef1f5",
    scroll_handle="#8f99a6",
    scroll_handle_hover="#707b89",
)


APPLICATION_STYLES = {
    "dark": DARK_APPLICATION_STYLE,
    "light": LIGHT_APPLICATION_STYLE,
}
