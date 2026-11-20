SPACE_NONE = 0
SPACE_XXS = 1
SPACE_XS = 2
SPACE_SM = 4
SPACE_MD = 6
SPACE_LG = 8
SPACE_XL = 10

MARGINS_NONE = (0, 0, 0, 0)
APP_MARGINS = (20, 0, 20, 16)
DIALOG_MARGINS = (12, 12, 12, 12)
DROP_ZONE_MARGINS = (0, 8, 0, 8)
SETTINGS_PANEL_MARGINS = (0, SPACE_LG, 0, 0)
SETTINGS_PANEL_COLUMN_GAP = SPACE_SM
PAGE_CONTENT_MARGINS = (16, 16, 16, 16)
PAGE_SECTION_SPACING = 12
OPERATIONS_PAGE_MARGINS = (0, 0, 0, 0)

CONTROL_HEIGHT = 28
FIELD_HEIGHT = CONTROL_HEIGHT
HEADER_FIELD_HEIGHT = CONTROL_HEIGHT
ACTION_BUTTON_HEIGHT = FIELD_HEIGHT
PROGRESS_HEIGHT = 22
TAB_BAR_HEIGHT = 40
CHECKBOX_SIZE = 16

STANDARD_RADIUS = 4

STANDARD_FORM_LABEL_STYLE = (
    "font-size: 13px; font-weight: 400; margin: 0px; padding: 0px;"
)
FILE_INFO_LABEL_STYLE = "font-size: 12px; font-weight: 500; padding: 0px 2px;"
TRANSPARENT_CONTAINER_STYLE = "background-color: transparent;"
SPLITTER_GRIP_LABEL_STYLE = (
    "background-color: transparent; border: none; padding: 0px;"
)
FILE_LIST_HEADER_STYLE = (
    "QHeaderView::section { background: transparent; border: none; "
    "border-right: 1px solid palette(mid); "
    "padding: 4px 6px; font-weight: 600; }"
    "QHeaderView::section:last, QHeaderView::section:only-one { "
    "border-right: none; }"
    "QHeaderView::up-arrow, QHeaderView::down-arrow { "
    "image: none; width: 0px; height: 0px; }"
)
FILE_LIST_DRAG_ACTIVE_STYLE = "QTableView { border: 2px dashed #3d74b3; }"


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


def build_operations_help_button_style(theme: str) -> str:
    foreground = "#202833" if str(theme).lower() == "light" else "#e3e6ea"
    return f"""
        QPushButton {{
            color: {foreground};
            background: transparent;
            border: none;
            border-bottom: 1px solid transparent;
            border-radius: 0px;
            padding: 0px 3px;
            font-size: 12px;
            font-weight: 500;
        }}
        QPushButton:checked {{
            border-bottom: 1px solid {foreground};
        }}
    """


def build_file_info_separator_style(theme: str) -> str:
    color = (
        "rgba(31, 35, 40, 0.24)"
        if str(theme).lower() == "light"
        else "rgba(255, 255, 255, 0.18)"
    )
    return f"background-color: {color}; border: none;"


def build_workspace_style(theme: str) -> str:
    dark = theme == "dark"
    background = "#202125" if dark else "#f6f7fa"
    panel = "#28292d" if dark else "#ffffff"
    border = "#55565b" if dark else "#c6c9d1"
    return f"""
        QWidget#workspace, QWidget#workspace .QWidget, QFrame#file_info_panel,
        QFrame#operation_result {{ background: {background}; }}
        QFrame#file_info_panel {{ border: none; }}
        QWidget#workspace QWidget#conversion_formats {{ background: transparent; }}
        QWidget#workspace QLabel {{ background: transparent; }}
        QWidget#operations_header_widget {{ border-bottom: 1px solid {border}; }}
        QFrame#operation_options {{
            background: {panel}; border: 1px solid {border}; border-radius: 7px;
        }}
    """


def build_drop_zone_surface_style(theme: str) -> str:
    background = "#ffffff" if str(theme).lower() == "light" else "#28292d"
    border = standard_palette(theme)["border"]
    return f"""
        QWidget#drop_zone_surface {{
            background-color: {background};
            border: 1px solid {border};
            border-radius: 7px;
        }}
    """


def drop_zone_muted_color(theme: str) -> str:
    return (
        "#5b6470" if str(theme).lower() == "light" else "rgba(220,220,220,180)"
    )


def build_drop_zone_overlay_style(theme: str) -> str:
    return f"""
        QWidget#drop_zone_overlay {{
            background-color: transparent;
            border: 1px dashed {drop_zone_muted_color(theme)};
            border-radius: 12px;
        }}
        QWidget#drop_zone_overlay QLabel {{
            background-color: transparent;
            color: {drop_zone_muted_color(theme)};
        }}
    """


def build_drop_zone_hint_style(theme: str) -> str:
    color = "#f2f3f6" if theme == "dark" else "#252933"
    return f"color: {color}; font-size: 18px; font-weight: 600;"


def build_drop_action_tile_style(theme: str) -> str:
    light = str(theme).lower() == "light"
    border = "rgba(90, 100, 110, 170)" if light else "rgba(255,255,255,120)"
    hover_border = "rgba(61,116,179,220)" if light else "rgba(255,255,255,210)"
    hover_background = standard_palette(theme)["hover_bg"]
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


def build_standard_button_style(theme: str, role: str) -> str:
    light = str(theme).lower() == "light"
    p = standard_palette(theme)
    bg, hover, pressed = p["bg"], p["hover_bg"], p["window_bg"]
    border, fg = p["border"], p["fg"]
    disabled_bg, disabled_border, disabled_fg = p["window_bg"], p["disabled_border"], p["disabled_fg"]
    if role == "primary":
        border, fg = ("#2869b7", "#245da3") if light else ("#629de1", "#b2d5ff")
    elif role == "danger":
        border, fg = ("#b7353d", "#98232b") if light else ("#ce6770", "#ffb2b8")
    focus = "#17395f" if light else "#b2d5ff"
    return f"""
        QPushButton {{
            background-color: {bg}; color: {fg}; border: 1px solid {border};
            border-radius: 7px; padding: 2px 9px; text-align: center;
            font-weight: 500; font-size: 13px;
        }}
        QPushButton:hover {{ background-color: {hover}; border-color: {border}; }}
        QPushButton:pressed {{ background-color: {pressed}; border-color: {border}; }}
        QPushButton:focus {{ border: 2px solid {focus}; padding: 1px 8px; }}
        QPushButton:disabled {{
            background-color: {disabled_bg}; color: {disabled_fg};
            border: 1px solid {disabled_border};
        }}
    """


def build_template_table_style(theme: str) -> str:
    palette = standard_palette(theme)
    foreground = palette["fg"]
    background = palette["bg"]
    border = palette["border"]
    alternate = palette["window_bg"]
    hover = selected = palette["hover_bg"]
    header = alternate
    return f"""
        QTableWidget {{
            background-color: {background}; alternate-background-color: {alternate};
            color: {foreground}; border: 1px solid {border}; border-radius: 4px;
            selection-background-color: {selected};
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
        QHeaderView::section {{ background-color: {header}; color: {foreground}; padding: 1px 4px; }}
        QTableCornerButton::section {{ background-color: {header}; border: none; }}
    """


def standard_palette(theme: str) -> dict[str, str]:
    if str(theme).lower() == "light":
        return {
            "window_bg": "#f4f6f8",
            "separator": "#dce2e9",
            "bg": "#ffffff",
            "fg": "#1f2328",
            "border": "#c7cfda",
            "hover_border": "#aab5c3",
            "hover_bg": "#dce6f1",
            "disabled_bg": "#f4f6f8",
            "disabled_fg": "#6f7785",
            "disabled_border": "#d6dbe2",
            "placeholder": "#6f7785",
        }
    return {
        "window_bg": "#2c2c2c",
        "separator": "rgba(255, 255, 255, 0.38)",
        "bg": "#383838",
        "fg": "#f0f0f0",
        "border": "#4f4f4f",
        "hover_border": "#4f4f4f",
        "hover_bg": "#505050",
        "disabled_bg": "#2c2c2c",
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
            QLineEdit:hover:enabled {{
                background-color: {p["hover_bg"]};
                border-color: {p["hover_border"]};
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
            QTextEdit:hover:enabled {{
                background-color: {p["hover_bg"]};
                border-color: {p["hover_border"]};
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
            QSpinBox:hover:enabled,
            QDoubleSpinBox:hover:enabled,
            QAbstractSpinBox:hover:enabled,
            QDateEdit:hover:enabled,
            QTimeEdit:hover:enabled,
            QDateTimeEdit:hover:enabled {{
                background-color: {p["hover_bg"]};
                border-color: {p["hover_border"]};
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
            QComboBox:hover:enabled {{
                background-color: {p["hover_bg"]};
                border: 1px solid {p["hover_border"]};
            }}
            QComboBox:hover:enabled::drop-down {{
                background-color: {p["hover_bg"]};
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
                font-size: 13px;
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
            QToolButton#menu_like_combo:hover:enabled {{
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
                font-size: 13px;
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
                font-size: 13px;
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
        surface = "#28292d" if str(theme).lower() == "dark" else "#ffffff"
        alternate_bg = p["window_bg"]
        hover_bg = selected_bg = p["hover_bg"]
        return f"""
            QAbstractItemView#files_list,
            QTableView#files_list,
            QListWidget#files_list,
            QListView#files_list {{
                background-color: {surface};
                alternate-background-color: {alternate_bg};
                color: {p["fg"]};
                border: none;
                border-radius: {STANDARD_RADIUS}px;
                outline: 0px;
                margin: 0px;
                padding: 0px;
                show-decoration-selected: 1;
            }}
            QAbstractItemView#files_list::item,
            QTableView#files_list::item,
            QListWidget#files_list::item,
            QListView#files_list::item {{
                background-color: {surface};
                color: {p["fg"]};
                padding: 0px 6px;
            }}
            QAbstractItemView#files_list::item:alternate,
            QTableView#files_list::item:alternate,
            QListWidget#files_list::item:alternate,
            QListView#files_list::item:alternate {{
                background-color: {alternate_bg};
                color: {p["fg"]};
            }}
            QAbstractItemView#files_list::item:hover,
            QTableView#files_list::item:hover,
            QListWidget#files_list::item:hover,
            QListView#files_list::item:hover {{
                background-color: {hover_bg};
                color: {p["fg"]};
            }}
            QAbstractItemView#files_list::item:selected,
            QTableView#files_list::item:selected,
            QListWidget#files_list::item:selected,
            QListView#files_list::item:selected,
            QAbstractItemView#files_list::item:selected:active,
            QTableView#files_list::item:selected:active,
            QListWidget#files_list::item:selected:active,
            QListView#files_list::item:selected:active,
            QAbstractItemView#files_list::item:selected:!active,
            QTableView#files_list::item:selected:!active,
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
    underline = "#3d74b3"
    active_text = underline if is_light else "#79b5f5"
    return f"""
        QToolButton#navigation_tab {{
            background: transparent; color: {foreground}; border: none;
            padding: 0px 8px; border-bottom: 3px solid transparent;
            font-size: 15px; font-weight: 400;
        }}
        QToolButton#navigation_tab:hover {{ color: {active_text}; }}
        QToolButton#navigation_tab:checked {{
            border-bottom: 3px solid #6495ff; font-weight: 600;
        }}
    """


def build_settings_navigation_style(theme: str) -> str:
    """Оформляет разделы настроек по аналогии с вкладками операций."""
    foreground = "#202833" if str(theme).lower() == "light" else "#e3e6ea"
    inactive_bg = standard_palette(theme)["bg"]
    separator = "#c7cfda" if str(theme).lower() == "light" else "#4f4f4f"
    active_text = "#3d74b3" if str(theme).lower() == "light" else "#79b5f5"
    return f"""
        QWidget#settings_nav {{
            background-color: transparent;
            border: none;
        }}
        QPushButton#settings_nav_item {{
            margin: 0px;
            padding: 0px 8px;
            font-size: 13px;
            font-weight: 600;
            color: {foreground};
            background-color: {inactive_bg};
            border: none;
            border-left: 1px solid {separator};
            border-right: 1px solid {separator};
            border-bottom: 1px solid {separator};
            border-radius: 0px;
            outline: none;
            text-align: left;
        }}
        QPushButton#settings_nav_item:checked {{
            color: {active_text};
            background-color: transparent;
        }}
        QPushButton#settings_nav_item[navPosition="first"] {{
            border-top: 1px solid {separator};
            border-top-left-radius: {STANDARD_RADIUS}px;
            border-top-right-radius: {STANDARD_RADIUS}px;
        }}
        QPushButton#settings_nav_item[navPosition="last"] {{
            border-bottom-left-radius: {STANDARD_RADIUS}px;
            border-bottom-right-radius: {STANDARD_RADIUS}px;
        }}
        QPushButton#settings_nav_item:focus {{
            outline: none;
        }}
    """


def build_tab_content_style_block(theme: str) -> str:
    is_light = str(theme).lower() == "light"
    base_text = "#1f2328" if is_light else "#e0e0e0"
    panel_border = "#c7cfda" if is_light else "#4f4f4f"
    return f"""
            QFrame#operations_panel {{
                background-color: transparent;
                border: 1px solid {panel_border};
                border-radius: {STANDARD_RADIUS}px;
            }}
            QFrame#file_info_panel {{
                background-color: transparent;
                border: 1px solid {panel_border};
                border-radius: {STANDARD_RADIUS}px;
            }}
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
                font-weight: 400;
                color: {base_text};
            }}
            QFrame#settings_section_separator {{
                background-color: {standard_palette(theme)["separator"]};
                border: none;
                margin: 0px;
                padding: 0px;
                min-height: {1 if is_light else 3}px;
                max-height: {1 if is_light else 3}px;
            }}
            QLabel#tab_hint_label {{
                font-size: 12px;
                color: #3d74b3;
            }}
        """
