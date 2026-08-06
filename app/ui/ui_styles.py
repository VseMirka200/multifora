from app.ui.ui_spacing import FIELD_HEIGHT, HEADER_FIELD_HEIGHT


def _build_menu_style(*, background: str, foreground: str, border: str, hover: str, separator: str) -> str:
    surface_rules = ""
    if background:
        surface_rules = f"background-color: {background};\n        color: {foreground};"
    return f"""
    QMenu {{
        {surface_rules}
        border: 1px solid {border};
        margin: 0px;
        padding: 0px;
        border-radius: 0px;
    }}
    QMenu#menu_like_combo_popup,
    QMenu#header_dropdown_popup {{
        border-top-left-radius: 0px;
        border-top-right-radius: 0px;
        border-bottom-left-radius: 4px;
        border-bottom-right-radius: 4px;
    }}
    QMenu::item {{
        padding: 4px 8px;
        margin: 1px 0px;
        background-color: transparent;
    }}
    QMenu::item:hover,
    QMenu::item:selected {{
        background-color: {hover};
        color: {foreground};
    }}
    QMenu::separator {{
        height: 1px;
        background: {separator};
    }}
"""


MENU_STYLE_LIGHT = _build_menu_style(
    background="",
    foreground="#1f2328",
    border="#c7cfda",
    hover="rgba(61, 116, 179, 0.10)",
    separator="rgba(0, 0, 0, 0.2)",
)
MENU_STYLE_DARK = _build_menu_style(
    background="#383838",
    foreground="#f0f0f0",
    border="#4f4f4f",
    hover="rgba(255, 255, 255, 0.07)",
    separator="rgba(255, 255, 255, 0.18)",
)

STANDARD_RADIUS = 4


def standard_palette(theme: str) -> dict[str, str]:
    if str(theme).lower() == "light":
        return {
            "bg": "#ffffff",
            "fg": "#1f2328",
            "border": "#c7cfda",
            "hover_border": "#aab5c3",
            "hover_bg": "#f8fafc",
            "disabled_bg": "#f2f4f7",
            "disabled_fg": "#8b949e",
            "disabled_border": "#d6dbe2",
            "placeholder": "#6f7785",
        }
    return {
        "bg": "#383838",
        "fg": "#f0f0f0",
        "border": "#4f4f4f",
        "hover_border": "#4f4f4f",
        "hover_bg": "#383838",
        "disabled_bg": "#3d3d3d",
        "disabled_fg": "#a8a8a8",
        "disabled_border": "#5a5a5a",
        "placeholder": "#9aa3ad",
    }


def build_standard_field_style(theme: str, kind: str) -> str:
    p = standard_palette(theme)
    if kind == "line":
        return f"""
            QLineEdit {{
                padding: 3px;
                min-height: {FIELD_HEIGHT}px;
                max-height: {FIELD_HEIGHT}px;
                background-color: {p["bg"]};
                color: {p["fg"]};
                border: 1px solid {p["border"]};
                border-radius: {STANDARD_RADIUS}px;
            }}
            QLineEdit::placeholder {{
                color: {p["placeholder"]};
            }}
        """
    if kind == "textedit":
        return f"""
            QTextEdit {{
                padding: 3px;
                min-height: {FIELD_HEIGHT}px;
                background-color: {p["bg"]};
                color: {p["fg"]};
                border: 1px solid {p["border"]};
                border-radius: {STANDARD_RADIUS}px;
            }}
            QTextEdit::placeholder {{
                color: {p["placeholder"]};
            }}
        """
    if kind == "spin":
        return f"""
            QSpinBox,
            QDoubleSpinBox,
            QAbstractSpinBox,
            QDateEdit,
            QTimeEdit,
            QDateTimeEdit {{
                padding: 3px;
                min-height: {FIELD_HEIGHT}px;
                max-height: {FIELD_HEIGHT}px;
                background-color: {p["bg"]};
                color: {p["fg"]};
                border: 1px solid {p["border"]};
                border-radius: {STANDARD_RADIUS}px;
            }}
            QSpinBox QLineEdit,
            QDoubleSpinBox QLineEdit,
            QAbstractSpinBox QLineEdit,
            QDateEdit QLineEdit,
            QTimeEdit QLineEdit,
            QDateTimeEdit QLineEdit {{
                background-color: {p["bg"]};
                color: {p["fg"]};
                border: none;
                border-radius: {STANDARD_RADIUS}px;
            }}
            QSpinBox::up-button,
            QSpinBox::down-button,
            QDoubleSpinBox::up-button,
            QDoubleSpinBox::down-button {{
                background-color: {p["bg"]};
                border: none;
            }}
        """
    if kind == "combo":
        return f"""
            QComboBox {{
                padding: 3px;
                min-height: {FIELD_HEIGHT}px;
                max-height: {FIELD_HEIGHT}px;
                background-color: {p["bg"]};
                color: {p["fg"]};
                border: 1px solid {p["border"]};
                border-radius: {STANDARD_RADIUS}px;
                text-align: left;
            }}
            QComboBox::drop-down {{
                background-color: {p["bg"]};
                border-left: 1px solid {p["border"]};
                border-top-right-radius: {STANDARD_RADIUS}px;
                border-bottom-right-radius: {STANDARD_RADIUS}px;
            }}
            QComboBox:on {{
                border-bottom-left-radius: 0px;
                border-bottom-right-radius: 0px;
            }}
            QComboBox:on::drop-down {{
                border-bottom-right-radius: 0px;
            }}
            QComboBox:hover {{
                border: 1px solid {p["hover_border"]};
            }}
            QComboBox QAbstractItemView,
            QComboBox QListView,
            QComboBox QListView::viewport {{
                background-color: {p["bg"]};
                color: {p["fg"]};
                border: 1px solid {p["border"]};
                border-top-left-radius: 0px;
                border-top-right-radius: 0px;
                border-bottom-left-radius: {STANDARD_RADIUS}px;
                border-bottom-right-radius: {STANDARD_RADIUS}px;
                outline: 0px;
                margin: 0px;
                padding: 0px;
            }}
            QComboBox QAbstractItemView::item {{
                padding: 4px 8px;
                margin: 0px;
                background-color: transparent;
                color: {p["fg"]};
            }}
            QComboBox QAbstractItemView::item:selected {{
                background-color: #3d74b3;
                color: #ffffff;
            }}
        """
    if kind == "menu":
        return f"""
            QToolButton#menu_like_combo {{
                font-size: 14px;
                padding: 3px;
                min-height: {FIELD_HEIGHT}px;
                max-height: {FIELD_HEIGHT}px;
                background-color: {p["bg"]};
                color: {p["fg"]};
                border: 1px solid {p["border"]};
                border-radius: {STANDARD_RADIUS}px;
                text-align: left;
                padding-left: 6px;
            }}
            QToolButton#menu_like_combo[menuOpen="true"] {{
                border-bottom-left-radius: 0px;
                border-bottom-right-radius: 0px;
            }}
            QToolButton#menu_like_combo::menu-indicator {{
                subcontrol-origin: padding;
                subcontrol-position: right center;
                right: 6px;
            }}
            QToolButton#menu_like_combo:hover {{
                border: 1px solid {p["hover_border"]};
                background-color: {p["hover_bg"]};
            }}
            QToolButton#menu_like_combo:disabled {{
                color: {p["disabled_fg"]};
                background-color: {p["disabled_bg"]};
                border: 1px solid {p["disabled_border"]};
            }}
        """
    if kind == "header":
        return f"""
            QToolButton#header_cell_tl,
            QToolButton#header_cell_tr,
            QToolButton#header_cell_bl {{
                font-size: 14px;
                padding: 3px;
                padding-left: 8px;
                min-height: {HEADER_FIELD_HEIGHT}px;
                max-height: {HEADER_FIELD_HEIGHT}px;
                background-color: {p["bg"]};
                color: {p["fg"]};
                border: 1px solid {p["border"]};
                border-radius: {STANDARD_RADIUS}px;
                text-align: left;
            }}
            QToolButton#header_cell_tl[menuOpen="true"],
            QToolButton#header_cell_tr[menuOpen="true"],
            QToolButton#header_cell_bl[menuOpen="true"] {{
                border-bottom-left-radius: 0px;
                border-bottom-right-radius: 0px;
            }}
            QLineEdit#header_cell_br {{
                font-size: 14px;
                padding: 3px;
                min-height: {HEADER_FIELD_HEIGHT}px;
                max-height: {HEADER_FIELD_HEIGHT}px;
                background-color: {p["bg"]};
                color: {p["fg"]};
                border: 1px solid {p["border"]};
                border-radius: {STANDARD_RADIUS}px;
            }}
            QToolButton#header_cell_tl::menu-indicator,
            QToolButton#header_cell_tr::menu-indicator,
            QToolButton#header_cell_bl::menu-indicator {{
                subcontrol-origin: padding;
                subcontrol-position: right center;
                right: 6px;
            }}
            QToolButton#header_cell_tl:pressed,
            QToolButton#header_cell_tr:pressed,
            QToolButton#header_cell_bl:pressed {{
                background-color: {p["bg"]};
            }}
        """
    if kind == "surface":
        return f"""
            QAbstractItemView#files_list,
            QListWidget#files_list,
            QListView#files_list {{
                background-color: {p["bg"]};
                color: {p["fg"]};
                border: 1px solid {p["border"]};
                border-radius: {STANDARD_RADIUS}px;
                outline: 0px;
                margin: 0px;
                padding: 0px;
            }}
        """
    return ""


def menu_style_for_theme(theme: str) -> str:
    return MENU_STYLE_LIGHT if str(theme).lower() == "light" else MENU_STYLE_DARK


def build_tab_content_style_block(theme: str) -> str:
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
            QLabel#settings_page_title_plain {{
                font-size: 30px;
                font-weight: 700;
                color: {base_text};
                padding-bottom: 5px;
                margin-bottom: 3px;
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
