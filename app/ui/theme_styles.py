"""Базовые QSS-темы с дополнительным оформлением из ``ui_styles``."""

from string import Template

from app.ui.typography import BODY_PX, CAPTION_PX, FONT_FAMILY, SECTION_PX
from app.ui.palette import standard_palette


def _theme_style(theme: str, qss: str) -> str:
    return Template(qss).substitute(
        family=FONT_FAMILY, caption=CAPTION_PX, body=BODY_PX, section=SECTION_PX, **standard_palette(theme)
    )


_TEMPLATE_MENU_FIELD_SELECTOR = (
    "QWidget#template_params_widget "
    'QToolButton#menu_like_combo[renameTemplateField="true"]'
)

DARK_APPLICATION_STYLE = _theme_style("dark", """
QMainWindow {
    background-color: $window_bg;
}
QWidget {
    background-color: $window_bg;
    selection-background-color: $hover_bg;
    selection-color: $fg;
    color: $fg;
    font-family: "$family";
    font-size: ${body}px;
    font-weight: 400;
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
    background-color: $bg;
    color: $fg;
    border: 1px solid $border;
}
QListWidget, QTableWidget {
    background-color: $bg;
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
QFrame#settings_section {
    background-color: $bg;
    border: 1px solid $border;
    border-radius: 6px;
}
QLabel[clickableCheckboxLabel="true"]:hover:enabled,
QFrame#settings_section QLabel[clickableCheckboxLabel="true"]:hover:enabled {
    background-color: $hover_bg;
    border-radius: 4px;
}
QFrame#settings_section QWidget#settings_row,
QFrame#settings_section QLabel,
QFrame#settings_section QCheckBox {
    background-color: transparent;
    border: none;
}
QFrame#settings_card {
    background-color: transparent;
    border: none;
}
QFrame#settings_card QWidget {
    background-color: transparent;
}
QFrame#settings_card QLabel[settingsHint="true"] {
    color: $disabled_fg;
    font-size: ${caption}px;
    font-weight: 400;
}
QFrame#settings_card QLabel[aboutVersionBadge="true"] {
    background-color: $bg;
    color: $disabled_fg;
    border: 1px solid $border;
    border-radius: 10px;
    padding: 3px 10px;
    font-size: ${caption}px;
    font-weight: 600;
}
QFrame#settings_section_separator {
    background-color: $separator;
    border: none;
    margin: 0px;
    padding: 0px;
    min-height: 3px;
    max-height: 3px;
}
QWidget#template_params_widget,
QFrame#template_numbering_card {
    background-color: $bg;
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
__TEMPLATE_MENU_FIELD_SELECTOR__,
__TEMPLATE_MENU_FIELD_SELECTOR__:hover,
__TEMPLATE_MENU_FIELD_SELECTOR__:focus {
    border: 1px solid $border;
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
    background-color: $bg;
    border: none;
}
QWidget#template_params_widget QComboBox {
    padding: 3px;
}
QWidget#template_params_widget QComboBox::drop-down {
    border: none;
    background-color: $bg;
    width: 18px;
}
QFrame#card QPushButton {
    border: none;
    border-radius: 4px;
    background-color: transparent;
}
QFrame#card QPushButton:hover {
    background-color: $hover_bg;
}
QFrame#card QPushButton:pressed {
    background-color: $hover_bg;
}
QFrame#card QPushButton:disabled {
    background-color: transparent;
    color: $disabled_fg;
}
QPushButton {
    padding: 3px 10px;
    color: $fg;
    font-size: ${body}px;
    font-weight: normal;
    border: none;
    border-radius: 10px;
    text-align: center;
    background-color: transparent;
}
QPushButton:hover {
    background-color: $hover_bg;
}
QPushButton:pressed {
    background-color: $hover_bg;
}
QPushButton:disabled {
    background-color: transparent;
    color: $disabled_fg;
}
QPushButton#cancel_operation_btn {
    border: none;
    border-radius: 10px;
    min-width: 84px;
}

QGroupBox {
    font-weight: 600;
    font-size: ${section}px;
    margin-top: 0px;
    padding-top: 0px;
    background-color: transparent;
    border: none;
    border-radius: 0px;
    color: $fg;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 6px;
    margin-left: 8px;
    color: $fg;
}

QLabel {
    font-size: ${body}px;
    color: $fg;
}
QCheckBox {
    font-size: ${body}px;
    color: $fg;
    spacing: 8px;
    padding: 0px;
    min-height: 24px;
    max-height: 24px;
    qproperty-layoutDirection: LeftToRight;
}
QLabel:disabled,
QCheckBox:disabled {
    color: $disabled_fg;
}
QComboBox {
    font-size: ${body}px;
    padding: 3px;
    background-color: $bg;
    color: $fg;
    border: 1px solid $border;
    border-radius: 0px;
}
QLineEdit,
QSpinBox {
    font-size: ${body}px;
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
    background-color: $bg;
    color: $fg;
    border: 1px solid $border;
    border-radius: 4px;
}
QComboBox::drop-down {
    border-left: 1px solid $border;
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
    border: 1px solid $border;
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
    font-size: ${body}px;
    padding: 3px;
    background-color: $bg;
    color: $fg;
    border: 1px solid $border;
    border-radius: 0px;
}
QLineEdit::placeholder {
    color: $disabled_fg;
}
QPlainTextEdit {
    font-size: ${body}px;
    background-color: $bg;
    color: $fg;
    border: 1px solid $border;
    border-radius: 4px;
}
QPlainTextEdit:focus {
    border: 1px solid $accent;
    border-radius: 4px;
}
QSpinBox {
    font-size: ${body}px;
    padding: 3px;
    background-color: $bg;
    color: $fg;
    border: 1px solid $border;
    border-radius: 0px;
}
QSlider {
    min-height: 20px;
    max-height: 20px;
}
QSlider::groove:horizontal {
    height: 4px;
    background: $hover_bg;
    border-radius: 2px;
}
QSlider::handle:horizontal {
    background: $accent;
    width: 12px;
    height: 12px;
    margin: -4px 0;
    border-radius: 6px;
}
QListWidget {
    font-size: ${body}px;
    background-color: $bg;
    color: $fg;
    border: 1px solid $border;
    border-radius: 0px;
}
QListWidget#rename_history_list {
    background-color: $bg;
    color: $fg;
    border: 1px solid $border;
    border-radius: 4px;
}
QListView {
    font-size: ${body}px;
    background-color: $bg;
    color: $fg;
    border: 1px solid $border;
    border-radius: 0px;
}
QListView::item {
    padding: 2px 4px;
    min-height: 22px;
    color: $fg;
}
QListView::item:selected {
    background-color: transparent;
    color: $fg;
}
QListWidget::item {
    padding: 3px;
    color: $fg;
}
QListWidget::item:selected {
    background-color: $hover_bg;
    color: $fg;
}
QTabBar::tab {
    padding: 2px 7px;
    font-size: ${body}px;
    font-weight: 600;
    min-height: 18px;
    max-height: 18px;
    background-color: $bg;
    color: $fg;
    border: none;
    border-radius: 0px;
    margin: 0px;
}
QTabBar::tab:selected {
    background-color: $hover_bg;
    color: $fg;
}
QTabBar::tab:hover:!selected {
    background-color: $bg;
}
QProgressBar {
    font-size: ${body}px;
    min-height: 26px;
    max-height: 26px;
    background-color: $window_bg;
    color: $fg;
    border: 1px solid $hover_border;
    border-radius: 0px;
    text-align: center;
}
QProgressBar::chunk {
    background-color: $progress;
    border-radius: 0px;
}
QStatusBar {
    font-size: ${caption}px;
    background-color: $window_bg;
    color: $fg;
}
QMessageBox {
    background-color: $window_bg;
}
QMessageBox QLabel {
    font-size: ${body}px;
    color: $fg;
}
QMessageBox QPushButton {
    font-size: ${body}px;
    border-radius: 4px;
}
QScrollArea {
    border: none;
    background-color: $window_bg;
}
QScrollArea QWidget#qt_scrollarea_viewport {
    background-color: $window_bg;
    border: none;
}
QScrollBar:vertical {
    background: transparent;
    border: none;
    width: 10px;
    margin: 0px;
}
QScrollBar::handle:vertical {
    background: $hover_border;
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
    background: $hover_border;
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
    background-color: $bg;
    color: $fg;
    border: 1px solid $border;
    border-radius: 6px;
}
QTableWidget::item {
    padding: 3px;
    color: $fg;
}
QTableWidget::item:selected {
    background-color: $hover_bg;
    color: $fg;
}
QHeaderView::section {
    background-color: $window_bg;
    color: $fg;
    padding: 4px;
    border: 1px solid $border;
}
""").replace("__TEMPLATE_MENU_FIELD_SELECTOR__", _TEMPLATE_MENU_FIELD_SELECTOR)

LIGHT_APPLICATION_STYLE = _theme_style("light", """
QMainWindow, QWidget {
    background-color: $window_bg;
    selection-background-color: $hover_bg;
    selection-color: $fg;
    color: $fg;
    font-family: "$family";
    font-size: ${body}px;
    font-weight: 400;
}
QLabel,
QPushButton,
QToolButton,
QLineEdit,
QPlainTextEdit,
QComboBox,
QMenu,
QListWidget,
QCheckBox {
    font-family: "$family";
    font-size: ${body}px;
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
QFrame#settings_section {
    background-color: $bg;
    border: 1px solid $border;
    border-radius: 6px;
}
QLabel[clickableCheckboxLabel="true"]:hover:enabled,
QFrame#settings_section QLabel[clickableCheckboxLabel="true"]:hover:enabled {
    background-color: $hover_bg;
    border-radius: 4px;
}
QFrame#settings_section QWidget#settings_row,
QFrame#settings_section QLabel,
QFrame#settings_section QCheckBox {
    background-color: transparent;
    border: none;
}
QFrame#settings_card {
    background-color: transparent;
    border: none;
}
QFrame#settings_card QWidget {
    background-color: transparent;
}
QFrame#settings_card QLabel[settingsHint="true"] {
    color: $disabled_fg;
    font-size: ${caption}px;
    font-weight: 400;
}
QFrame#settings_card QLabel[aboutVersionBadge="true"] {
    background-color: $bg;
    color: $disabled_fg;
    border: 1px solid $border;
    border-radius: 10px;
    padding: 3px 10px;
    font-size: ${caption}px;
    font-weight: 600;
}
QFrame#settings_section_separator {
    background-color: $separator;
    border: none;
    margin: 0px;
    padding: 0px;
    min-height: 1px;
    max-height: 1px;
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
__TEMPLATE_MENU_FIELD_SELECTOR__,
__TEMPLATE_MENU_FIELD_SELECTOR__:hover,
__TEMPLATE_MENU_FIELD_SELECTOR__:focus {
    border: 1px solid $border;
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
    background-color: $bg;
    border: none;
}
QWidget#template_params_widget QComboBox {
    padding: 3px;
}
QWidget#template_params_widget QComboBox::drop-down {
    border: none;
    background-color: $bg;
    width: 18px;
}
QGroupBox {
    font-weight: 600;
    font-size: ${section}px;
    margin-top: 0px;
    padding-top: 0px;
    background-color: transparent;
    border: none;
    border-radius: 0px;
    color: $fg;
}
QLabel {
    color: $fg;
}
QPushButton {
    padding: 3px 10px;
    color: $fg;
    font-size: ${body}px;
    font-weight: normal;
    border: none;
    border-radius: 10px;
    text-align: center;
}
QPushButton:disabled {
    color: $disabled_fg;
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
    background-color: $bg;
    color: $fg;
    border: 1px solid $border;
    border-radius: 4px;
}
QComboBox::drop-down {
    border-left: 1px solid $border;
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
    background-color: $bg;
    color: $fg;
    border: 1px solid $border;
    border-radius: 4px;
}
QListWidget, QTableWidget {
    background-color: $bg;
    color: $fg;
    border: 1px solid $border;
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
    color: $disabled_fg;
}
QListWidget {
    font-size: ${body}px;
    background-color: $bg;
    color: $fg;
    border: 1px solid $border;
    border-radius: 0px;
}
QListWidget#rename_history_list {
    background-color: $bg;
    color: $fg;
    border: 1px solid $border;
    border-radius: 4px;
}
QListView {
    font-size: ${body}px;
    background-color: $bg;
    color: $fg;
    border: 1px solid $border;
    border-radius: 0px;
}
QListView::item {
    padding: 2px 4px;
    min-height: 22px;
    color: $fg;
    background-color: transparent;
}
QListView::item:selected {
    background-color: $hover_bg;
    color: $fg;
}
QListWidget::item {
    padding: 3px;
    color: $fg;
}
QListWidget::item:selected {
    background-color: $hover_bg;
    color: $fg;
}
QCheckBox {
    font-size: ${body}px;
    color: $fg;
    background-color: transparent;
    spacing: 8px;
    min-height: 24px;
    max-height: 24px;
}
QLabel:disabled,
QCheckBox:disabled {
    color: $disabled_fg;
}
QScrollArea {
    border: none;
    background-color: $window_bg;
}
QScrollArea QWidget#qt_scrollarea_viewport {
    background-color: $window_bg;
    border: none;
}
QScrollBar:vertical {
    background: transparent;
    border: none;
    width: 10px;
    margin: 0px;
}
QScrollBar::handle:vertical {
    background: $hover_border;
    border-radius: 4px;
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
    background: $hover_border;
    border-radius: 4px;
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
    font-size: ${body}px;
    min-height: 22px;
    max-height: 22px;
    background-color: $bg;
    color: $fg;
    border: 1px solid $border;
    border-radius: 0px;
    text-align: center;
}
QProgressBar::chunk {
    background-color: $progress;
    border-radius: 0px;
}
QStatusBar {
    font-size: ${caption}px;
    background-color: $window_bg;
    color: $fg;
}
QMessageBox {
    background-color: $window_bg;
}
QMessageBox QLabel {
    color: $fg;
}
/* Neutral button interaction states for light theme */
QPushButton,
QFrame#card QPushButton {
    border: none;
    background-color: transparent;
}
QPushButton:hover,
QFrame#card QPushButton:hover {
    background-color: $hover_bg;
}
QPushButton:pressed,
QFrame#card QPushButton:pressed {
    background-color: $hover_bg;
}
QPushButton:disabled,
QFrame#card QPushButton:disabled {
    background-color: transparent;
}
QLabel {
    background-color: transparent;
}
""").replace("__TEMPLATE_MENU_FIELD_SELECTOR__", _TEMPLATE_MENU_FIELD_SELECTOR)

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
QMenu#header_dropdown_popup,
QMenu#menu_like_combo_popup {{
    border-top-color: {background};
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
QMenu#menu_like_combo_popup::item {{
    padding-left: 3px;
    padding-right: 4px;
}}
QMenu#help_menu_popup::item {{
    min-height: 18px;
    max-height: 18px;
    padding: 0px 4px;
    font-size: {CAPTION_PX}px;
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
QSpinBox::up-arrow, QDoubleSpinBox::up-arrow,
QMenu QListWidget#scrollable_filter_list QScrollBar::up-arrow:vertical {{
    image: url("__SCROLL_UP_URL__");
    width: 8px;
    height: 8px;
}}
QSpinBox::down-arrow, QDoubleSpinBox::down-arrow,
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


def _dropdown_theme(theme):
    p = standard_palette(theme)
    return _build_global_dropdown_style(
        background=p["bg"], foreground=p["fg"], border=p["border"],
        hover=p["hover_bg"], separator=p["separator"], disabled=p["disabled_fg"],
        scroll_track=p["window_bg"], scroll_handle=p["hover_border"],
        scroll_handle_hover=p["disabled_fg"],
    )


DARK_APPLICATION_STYLE += _dropdown_theme("dark")
LIGHT_APPLICATION_STYLE += _dropdown_theme("light")


APPLICATION_STYLES = {
    "dark": DARK_APPLICATION_STYLE,
    "light": LIGHT_APPLICATION_STYLE,
}
