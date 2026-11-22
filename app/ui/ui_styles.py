from app.ui.palette import standard_palette
from app.ui.typography import BODY_PX, CAPTION_PX, SECTION_PX

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
FILE_PANEL_RADIUS = 7
FIELD_HEIGHT = CONTROL_HEIGHT
HEADER_FIELD_HEIGHT = CONTROL_HEIGHT
ACTION_BUTTON_HEIGHT = FIELD_HEIGHT
PROGRESS_HEIGHT = 22
TAB_BAR_HEIGHT = 40
CHECKBOX_SIZE = 16

STANDARD_RADIUS = 4

STANDARD_FORM_LABEL_STYLE = (
    f"font-size: {BODY_PX}px; font-weight: 400; margin: 0px; padding: 0px;"
)
FILE_INFO_LABEL_STYLE = f"font-size: {CAPTION_PX}px; font-weight: 500; padding: 0px 2px;"
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
FILE_LIST_DRAG_ACTIVE_STYLE = "QTableView { border: 2px dashed palette(highlight); }"


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
    foreground = standard_palette(theme)["fg"]
    return f"""
        QPushButton {{
            color: {foreground};
            background: transparent;
            border: none;
            border-bottom: 1px solid transparent;
            border-radius: 0px;
            padding: 0px 3px;
            font-size: {CAPTION_PX}px;
            font-weight: 500;
        }}
        QPushButton:checked {{
            border-bottom: 1px solid {foreground};
        }}
    """


def build_file_info_separator_style(theme: str) -> str:
    color = standard_palette(theme)["separator"]
    return f"background-color: {color}; border: none;"


def build_workspace_style(theme: str) -> str:
    p = standard_palette(theme)
    background, panel, border = p["window_bg"], p["bg"], p["border"]
    return f"""
        QWidget#workspace, QWidget#workspace .QWidget, QFrame#file_info_panel,
        QFrame#operation_result {{ background: {background}; }}
        QFrame#file_info_panel {{ border: none; }}
        QWidget#workspace QWidget#conversion_formats {{ background: transparent; }}
        QWidget#workspace QWidget#compress_page QStackedWidget,
        QWidget#workspace QWidget#compress_page QStackedWidget .QWidget,
        QWidget#workspace QWidget#compress_page QCheckBox {{ background: transparent; }}
        QWidget#workspace QWidget#template_params_widget,
        QWidget#template_params_widget .QWidget,
        QWidget#template_params_widget QFrame#template_numbering_card {{ background: transparent; }}
        QWidget#workspace QLabel {{ background: transparent; }}
        QWidget#operations_header_widget {{ border-bottom: 1px solid {border}; }}
        QFrame#settings_section, QFrame#support_card {{
            background: {panel}; border: 1px solid {border}; border-radius: 7px;
        }}
        QWidget#workspace QWidget#settings_row {{ background: transparent; }}
        QFrame#section_line {{ border: none; background: {border}; }}
        QPushButton#support_action {{ background: transparent; border: none; border-radius: 5px; }}
        QPushButton#support_action:hover, QPushButton#support_action:focus {{ background: {border}; }}
        QLabel[sectionHint="true"], QLabel[settingsHint="true"] {{
            font-size: {CAPTION_PX}px; color: {p["disabled_fg"]};
        }}
        QFrame#operation_options {{
            background: {panel}; border: 1px solid {border}; border-radius: 7px;
        }}
    """


def build_drop_zone_surface_style(theme: str) -> str:
    background = standard_palette(theme)["bg"]
    border = standard_palette(theme)["border"]
    return f"""
        QWidget#drop_zone_surface {{
            background-color: {background};
            border: 1px solid {border};
            border-radius: {FILE_PANEL_RADIUS}px;
        }}
    """


def drop_zone_muted_color(theme: str) -> str:
    return standard_palette(theme)["disabled_fg"]


def build_drop_zone_overlay_style(theme: str) -> str:
    return f"""
        QWidget#drop_zone_overlay {{
            background-color: transparent;
            border: none;
            color: {drop_zone_muted_color(theme)};
        }}
        QWidget#drop_zone_overlay QLabel {{
            background-color: transparent;
            color: {drop_zone_muted_color(theme)};
        }}
    """


def build_drop_zone_hint_style(theme: str) -> str:
    color = standard_palette(theme)["fg"]
    return f"color: {color}; font-size: {SECTION_PX}px; font-weight: 600;"


def build_drop_action_tile_style(theme: str) -> str:
    p = standard_palette(theme)
    border, hover_border, hover_background = p["border"], p["accent"], p["hover_bg"]
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
    color = standard_palette(theme)["fg"]
    return f'font-size: {CAPTION_PX}px; font-weight: 600; color: {color};'


def build_standard_button_style(theme: str, role: str) -> str:
    p = standard_palette(theme)
    bg, hover, pressed = p["bg"], p["hover_bg"], p["window_bg"]
    border, fg = p["border"], p["fg"]
    disabled_bg, disabled_border, disabled_fg = p["window_bg"], p["disabled_border"], p["disabled_fg"]
    if role == "primary":
        bg = border = p["accent"]
        fg, hover, pressed = p["on_accent"], p["accent_hover"], p["accent_hover"]
        disabled_bg = p["inactive_accent"]
    elif role == "command":
        bg, hover, pressed = p["hover_bg"], p["command_hover"], p["progress"]
        border = p["command_hover"]
    elif role == "danger":
        bg = border = p["danger"]
        fg, hover, pressed = p["on_accent"], p["danger_hover"], p["danger_pressed"]
    focus = p["fg"] if role == "primary" else p["accent"]
    return f"""
        QAbstractButton {{
            background-color: {bg}; color: {fg}; border: 1px solid {border};
            border-radius: 7px; padding: 2px 9px; text-align: center;
            font-weight: 500; font-size: {BODY_PX}px;
        }}
        QAbstractButton:hover {{ background-color: {hover}; border-color: {border}; }}
        QAbstractButton:pressed {{ background-color: {pressed}; border-color: {border}; }}
        QAbstractButton:focus {{ border: 2px solid {focus}; padding: 1px 8px; }}
        QAbstractButton:disabled {{
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
            AutoHeightTextEdit {{
                min-height: 0px;
                padding: {SPACE_SM}px {SPACE_LG}px;
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
                background-color: transparent;
                color: {p["fg"]};
                border: none;
                padding: 0px;
            }}
            QSpinBox::up-button,
            QSpinBox::down-button,
            QDoubleSpinBox::up-button,
            QDoubleSpinBox::down-button {{
                width: 18px;
                background-color: transparent;
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
                font-size: {BODY_PX}px;
                padding: 3px;
                background-color: {p["bg"]};
                color: {p["fg"]};
                border: 1px solid {p["border"]};
                border-radius: {STANDARD_RADIUS}px;
                text-align: left;
                padding-left: 6px;
            }}
            QToolButton#menu_like_combo[ruleSelector="true"] {{
                background-color: {p["hover_bg"]};
                border-color: {p["command_hover"]};
                border-radius: 6px;
            }}
            QToolButton#menu_like_combo[ruleSelector="true"]:focus {{
                border-color: {p["accent"]};
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
                font-size: {BODY_PX}px;
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
                font-size: {BODY_PX}px;
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
        surface = p["bg"]
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
    p = standard_palette(theme)
    foreground, active_text = p["fg"], p["accent"]
    return f"""
        QToolButton#navigation_tab {{
            background: transparent; color: {foreground}; border: none;
            padding: 0px 8px; border-bottom: 3px solid transparent;
            font-size: {BODY_PX}px; font-weight: 400;
        }}
        QToolButton#navigation_tab:hover {{ color: {active_text}; }}
        QToolButton#navigation_tab:checked {{
            border-bottom: 3px solid {active_text}; font-weight: 600;
        }}
    """


def build_settings_navigation_style(theme: str) -> str:
    """Оформляет разделы настроек по аналогии с вкладками операций."""
    foreground = standard_palette(theme)["fg"]
    inactive_bg = standard_palette(theme)["bg"]
    separator = standard_palette(theme)["border"]
    active_text = standard_palette(theme)["accent"]
    return f"""
        QWidget#settings_nav {{
            background-color: transparent;
            border: none;
        }}
        QPushButton#settings_nav_item {{
            margin: 0px;
            padding: 0px 8px;
            font-size: {BODY_PX}px;
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
    base_text = standard_palette(theme)["fg"]
    panel_border = standard_palette(theme)["border"]
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
                font-size: {BODY_PX}px;
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
                font-size: {CAPTION_PX}px;
                color: {standard_palette(theme)["accent"]};
            }}
        """
