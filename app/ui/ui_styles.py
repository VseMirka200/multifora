from app.ui.ui_spacing import FIELD_HEIGHT


def _build_menu_style(
    *,
    background: str,
    foreground: str,
    border: str,
    hover: str,
    separator: str,
    disabled: str,
) -> str:
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
    QMenu::item:disabled {{
        background-color: transparent;
        color: {disabled};
    }}
    QMenu::separator {{
        height: 1px;
        background: {separator};
    }}
"""


MENU_STYLE_LIGHT = _build_menu_style(
    background="#ffffff",
    foreground="#1f2328",
    border="#c7cfda",
    hover="rgba(61, 116, 179, 0.10)",
    separator="rgba(0, 0, 0, 0.2)",
    disabled="#6f7785",
)
MENU_STYLE_DARK = _build_menu_style(
    background="#383838",
    foreground="#f0f0f0",
    border="#4f4f4f",
    hover="rgba(255, 255, 255, 0.07)",
    separator="rgba(255, 255, 255, 0.18)",
    disabled="#a8a8a8",
)

STANDARD_RADIUS = 4


def build_splitter_style() -> str:
    return """
        QSplitter::handle:horizontal {
            background-color: transparent;
            border: none;
            margin: 0px;
        }
        QSplitter::handle:horizontal:hover {
            background-color: transparent;
        }
    """


def build_file_info_separator_style(theme: str) -> str:
    color = "rgba(31, 35, 40, 0.24)" if str(theme).lower() == "light" else "rgba(255, 255, 255, 0.18)"
    return f"background-color: {color}; border: none;"


def build_drop_zone_surface_style(theme: str) -> str:
    background = "#ffffff" if str(theme).lower() == "light" else "#383838"
    return f"""
        QWidget#drop_zone_surface {{
            background-color: {background};
            border: none;
            border-radius: {STANDARD_RADIUS}px;
        }}
    """


def drop_zone_muted_color(theme: str) -> str:
    return "#5b6470" if str(theme).lower() == "light" else "rgba(220,220,220,180)"


def build_drop_zone_overlay_style(theme: str) -> str:
    return f"""
        QWidget#drop_zone_overlay {{
            background-color: transparent;
            border: none;
            border-radius: {STANDARD_RADIUS}px;
        }}
        QWidget#drop_zone_overlay QLabel {{
            background-color: transparent;
            color: {drop_zone_muted_color(theme)};
        }}
    """


def build_drop_zone_hint_style(theme: str) -> str:
    return f"color: {drop_zone_muted_color(theme)}; font-size: 13px;"


def build_drop_action_tile_style(theme: str) -> str:
    light = str(theme).lower() == "light"
    border = "rgba(90, 100, 110, 170)" if light else "rgba(255,255,255,120)"
    hover_border = "rgba(61,116,179,220)" if light else "rgba(255,255,255,210)"
    hover_background = "rgba(61,116,179,18)" if light else "rgba(255,255,255,24)"
    return f"""
        QFrame#drop_action_tile {{
            background-color: transparent;
            border: 2px dashed {border};
            border-radius: 12px;
        }}
        QFrame#drop_action_tile:hover {{
            border-color: {hover_border};
            background-color: {hover_background};
        }}
    """


def build_drop_action_tile_text_style(theme: str) -> str:
    color = "#1f2328" if str(theme).lower() == "light" else "#f0f0f0"
    return f'font-family: "Segoe UI"; font-size: 12px; font-weight: 600; color: {color};'


_BUTTON_PALETTES = {
    "dark": ("#303030", "#3a3a3a", "#2a2a2a", "#474747", "#f1f1f1", "#292929", "#3b3b3b", "#787878"),
    "light": ("#f6f8fb", "#edf2f7", "#e2eaf3", "#d6dee8", "#243244", "#f8fafc", "#e4eaf2", "#9aa4b2"),
}


def build_standard_button_style(theme: str, role: str) -> str:
    palette = _BUTTON_PALETTES["light" if str(theme).lower() == "light" else "dark"]
    bg, hover, pressed, border, fg, disabled_bg, disabled_border, disabled_fg = palette
    return f"""
        QPushButton {{
            background-color: {bg}; color: {fg}; border: 1px solid {border};
            border-radius: 7px; padding: 2px 9px; font-weight: 500; font-size: 13px;
        }}
        QPushButton:hover {{ background-color: {hover}; border-color: {border}; }}
        QPushButton:pressed {{ background-color: {pressed}; border-color: {border}; }}
        QPushButton:disabled {{
            background-color: {disabled_bg}; color: {disabled_fg};
            border: 1px solid {disabled_border};
        }}
    """


def build_template_table_style(theme: str) -> str:
    light = str(theme).lower() == "light"
    foreground = "#1f2328" if light else "#f0f0f0"
    alternate = "#eef1f5" if light else "#454545"
    hover = "rgba(61, 116, 179, 0.10)" if light else "rgba(255, 255, 255, 0.07)"
    selected = "rgba(61, 116, 179, 0.22)" if light else "#5c5c5c"
    header = alternate if light else "#2b2b2b"
    return f"""
        QTableWidget {{
            background-color: transparent; alternate-background-color: {alternate};
            color: {foreground}; border: none; selection-background-color: {selected};
            selection-color: {foreground}; show-decoration-selected: 1;
        }}
        QTableWidget:focus, QTableWidget::item:focus {{ outline: none; border: none; }}
        QTableWidget::item {{
            padding: 2px 4px; min-height: 22px; background-color: transparent;
            color: {foreground};
        }}
        QTableWidget::item:alternate {{ background-color: {alternate}; color: {foreground}; }}
        QTableWidget::item:hover {{ background-color: {hover}; color: {foreground}; }}
        QTableWidget::item:selected,
        QTableWidget::item:selected:active,
        QTableWidget::item:selected:!active {{
            background-color: {selected}; color: {foreground}; selection-color: {foreground};
        }}
        QTableWidget::item:selected:focus {{
            outline: none; border: none; background-color: {selected};
        }}
        QHeaderView::section {{ background-color: {header}; color: {foreground}; padding: 4px; }}
        QTableCornerButton::section {{ background-color: {header}; border: none; }}
    """


def standard_palette(theme: str) -> dict[str, str]:
    if str(theme).lower() == "light":
        return {
            "bg": "#ffffff",
            "fg": "#1f2328",
            "border": "#c7cfda",
            "hover_border": "#aab5c3",
            "hover_bg": "#f8fafc",
            "disabled_bg": "#f2f4f7",
            "disabled_fg": "#6f7785",
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
                background-color: {p["bg"]};
                color: {p["fg"]};
                border: 1px solid {p["border"]};
                border-radius: {STANDARD_RADIUS}px;
            }}
            QLineEdit::placeholder {{
                color: {p["placeholder"]};
            }}
            QLineEdit:disabled {{
                background-color: {p["disabled_bg"]};
                color: {p["disabled_fg"]};
                border-color: {p["disabled_border"]};
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
            QTextEdit:disabled {{
                background-color: {p["disabled_bg"]};
                color: {p["disabled_fg"]};
                border-color: {p["disabled_border"]};
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
            QSpinBox:disabled,
            QDoubleSpinBox:disabled,
            QAbstractSpinBox:disabled,
            QDateEdit:disabled,
            QTimeEdit:disabled,
            QDateTimeEdit:disabled {{
                background-color: {p["disabled_bg"]};
                color: {p["disabled_fg"]};
                border-color: {p["disabled_border"]};
            }}
        """
    if kind == "combo":
        return f"""
            QComboBox {{
                padding: 3px;
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
            QComboBox:disabled {{
                background-color: {p["disabled_bg"]};
                color: {p["disabled_fg"]};
                border-color: {p["disabled_border"]};
            }}
            QComboBox:disabled::drop-down {{
                background-color: {p["disabled_bg"]};
                border-left-color: {p["disabled_border"]};
            }}
        """
    if kind == "menu":
        return f"""
            QToolButton#menu_like_combo {{
                font-size: 14px;
                padding: 3px;
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
            QToolButton#header_cell_tr {{
                font-size: 14px;
                padding: 3px;
                padding-left: 8px;
                background-color: {p["bg"]};
                color: {p["fg"]};
                border: 1px solid {p["border"]};
                border-radius: {STANDARD_RADIUS}px;
                text-align: left;
            }}
            QToolButton#header_cell_tl:hover,
            QToolButton#header_cell_tr:hover {{
                background-color: {p["hover_bg"]};
                border-color: {p["hover_border"]};
            }}
            QToolButton#header_cell_tl[menuOpen="true"],
            QToolButton#header_cell_tr[menuOpen="true"] {{
                border-bottom-left-radius: 0px;
                border-bottom-right-radius: 0px;
            }}
            QLineEdit#header_cell_br {{
                font-size: 14px;
                padding: 3px;
                background-color: {p["bg"]};
                color: {p["fg"]};
                border: 1px solid {p["border"]};
                border-radius: {STANDARD_RADIUS}px;
            }}
            QToolButton#header_cell_tl::menu-indicator,
            QToolButton#header_cell_tr::menu-indicator {{
                subcontrol-origin: padding;
                subcontrol-position: right center;
                right: 6px;
            }}
            QToolButton#header_cell_tl:pressed,
            QToolButton#header_cell_tr:pressed {{
                background-color: {p["bg"]};
            }}
            QToolButton#header_cell_tl:disabled,
            QToolButton#header_cell_tr:disabled,
            QLineEdit#header_cell_br:disabled {{
                background-color: {p["disabled_bg"]};
                color: {p["disabled_fg"]};
                border-color: {p["disabled_border"]};
            }}
        """
    if kind == "surface":
        alternate_bg = "#f8fafc" if str(theme).lower() == "light" else "#3d3d3d"
        hover_bg = "rgba(61, 116, 179, 0.10)" if str(theme).lower() == "light" else "rgba(255, 255, 255, 0.07)"
        selected_bg = "rgba(61, 116, 179, 0.22)" if str(theme).lower() == "light" else "rgba(61, 116, 179, 0.38)"
        return f"""
            QAbstractItemView#files_list,
            QListWidget#files_list,
            QListView#files_list {{
                background-color: {p["bg"]};
                alternate-background-color: {alternate_bg};
                color: {p["fg"]};
                border: 1px solid {p["border"]};
                border-radius: {STANDARD_RADIUS}px;
                outline: 0px;
                margin: 0px;
                padding: 0px;
                show-decoration-selected: 1;
            }}
            QAbstractItemView#files_list::item,
            QListWidget#files_list::item,
            QListView#files_list::item {{
                background-color: {p["bg"]};
                color: {p["fg"]};
            }}
            QAbstractItemView#files_list::item:alternate,
            QListWidget#files_list::item:alternate,
            QListView#files_list::item:alternate {{
                background-color: {alternate_bg};
                color: {p["fg"]};
            }}
            QAbstractItemView#files_list::item:hover,
            QListWidget#files_list::item:hover,
            QListView#files_list::item:hover {{
                background-color: {hover_bg};
                color: {p["fg"]};
            }}
            QAbstractItemView#files_list::item:selected,
            QListWidget#files_list::item:selected,
            QListView#files_list::item:selected,
            QAbstractItemView#files_list::item:selected:active,
            QListWidget#files_list::item:selected:active,
            QListView#files_list::item:selected:active,
            QAbstractItemView#files_list::item:selected:!active,
            QListWidget#files_list::item:selected:!active,
            QListView#files_list::item:selected:!active {{
                background-color: {selected_bg};
                color: {p["fg"]};
                selection-color: {p["fg"]};
            }}
        """
    return ""


def build_operations_tab_bar_style(theme: str) -> str:
    is_light = str(theme).lower() == "light"
    foreground = "#202833" if is_light else "#e3e6ea"
    selected_fg = "#ffffff" if not is_light else "#1d2f45"
    base_bg = "transparent"
    hover_bg = "transparent"
    underline = "#3d74b3"
    return f"""
        QTabBar#operations_tab_bar {{
            background-color: transparent;
            margin: 0px;
            padding: 0px;
            border: none;
        }}
        QTabBar#operations_tab_bar::tab {{
            margin: 0px 12px 0px 0px;
            padding: 0px 2px;
            min-width: 24px;
            min-height: 30px;
            max-height: 30px;
            font-weight: 500;
            color: {foreground};
            background-color: {base_bg};
            border: none;
            border-bottom: 1px solid transparent;
        }}
        QTabBar#operations_tab_bar::tab:selected {{
            color: {selected_fg};
            border-bottom: 1px solid {underline};
        }}
        QTabBar#operations_tab_bar::tab:!selected {{
            color: {foreground};
            background-color: transparent;
            border-bottom: 1px solid transparent;
        }}
        QTabBar#operations_tab_bar[settingsActive="true"]::tab:selected {{
            color: {foreground};
            border-bottom: 1px solid transparent;
        }}
    """


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
