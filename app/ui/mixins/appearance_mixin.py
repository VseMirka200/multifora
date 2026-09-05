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
    refresh_standard_button_styles,
    refresh_standard_field_styles,
    refresh_standard_surface_styles,
)
from app.ui.ui_styles import build_tab_content_style_block
from app.ui.theme_styles import APPLICATION_STYLES
from app.ui.ui_spacing import (
    LINK_BUTTON_HEIGHT,
    MARGINS_NONE,
    MESSAGE_DIALOG_MARGINS,
    SPACE_LG,
    SPACE_XL,
    SPACE_2XL,
)
from app.core.app_utils import _log_ignored_error


class AppearanceMixin:
    # Управляет темой главного окна, отдельных диалогов и системным переключением.
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
            refresh_standard_button_styles(dialog)
            refresh_standard_field_styles(dialog)
            refresh_standard_surface_styles(dialog)
        except Exception as error:
            _log_ignored_error("AppearanceMixin._apply_detached_theme_style", error)

    def apply_dark_style(self):
        """Применяет тёмную тему к главному окну и диалогам."""
        self._apply_application_style("dark")

    def apply_light_style(self):
        """Применяет светлую тему к главному окну и диалогам."""
        self._apply_application_style("light")

    def _apply_application_style(self, theme: str) -> None:
        # Собираем QSS по имени темы и подставляем путь к галочке во время запуска.
        # Общий порядок обновления сохраняет оформление отдельных окон и списков.
        style = APPLICATION_STYLES[theme] + build_tab_content_style_block(theme)
        style = style.replace("__CHECKMARK_URL__", self._checkbox_checkmark_url())
        self.setStyleSheet(style)
        self._apply_detached_theme_style(style)
        self._refresh_combo_popup_styles()

    def _refresh_combo_popup_styles(self):
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
            except Exception as error:
                _log_ignored_error("AppearanceMixin._refresh_combo_popup_styles", error)
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
        except Exception as error:
            _log_ignored_error("AppearanceMixin.apply_theme_mode", error)
        try:
            if callable(getattr(self, "_apply_theme_runtime_widgets", None)):
                self._apply_theme_runtime_widgets()
        except Exception as error:
            _log_ignored_error("AppearanceMixin.apply_theme_mode", error)

        if hasattr(self, "theme_mode_combo") and self.theme_mode_combo is not None:
            try:
                idx = self.theme_mode_combo.findData(self.theme_mode)
                if idx >= 0 and self.theme_mode_combo.currentIndex() != idx:
                    self.theme_mode_combo.blockSignals(True)
                    self.theme_mode_combo.setCurrentIndex(idx)
                    self.theme_mode_combo.blockSignals(False)
            except Exception as error:
                _log_ignored_error("AppearanceMixin.apply_theme_mode", error)

    def setup_system_theme_tracking(self):
        if getattr(self, "_system_theme_tracking_connected", False):
            return
        try:
            hints = QGuiApplication.styleHints()
            if hasattr(hints, "colorSchemeChanged"):
                hints.colorSchemeChanged.connect(self._on_system_theme_changed)
                self._system_theme_tracking_connected = True
        except Exception as error:
            _log_ignored_error("AppearanceMixin.setup_system_theme_tracking", error)

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
        except Exception as error:
            _log_ignored_error("AppearanceMixin.show_russian_message_box", error)

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
            standard_icon = dialog.style().standardIcon(
            icon_map.get(icon, QStyle.StandardPixmap.SP_MessageBoxQuestion)
        )
            icon_label.setPixmap(standard_icon.pixmap(32, 32))
        except Exception as error:
            _log_ignored_error("AppearanceMixin.show_russian_message_box", error)
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
            except Exception as error:
                _log_ignored_error("AppearanceMixin.show_russian_message_box", error)
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
        except Exception as error:
            _log_ignored_error("AppearanceMixin.show_russian_message_box", error)

        yes_button.clicked.connect(dialog.accept)
        no_button.clicked.connect(dialog.reject)

        if default_no:
            no_button.setFocus()
        else:
            yes_button.setFocus()

        return dialog.exec() == int(QDialog.DialogCode.Accepted)

