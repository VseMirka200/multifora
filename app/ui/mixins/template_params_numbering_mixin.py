from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QSizePolicy,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from app.core.app_utils import signals_blocked
from app.ui.ui_components import (
    MenuLikeComboBox,
    StandardPopupMenu,
    apply_standard_field_style,
    setup_standard_dropdown,
    setup_standard_form_label,
    setup_standard_line_input,
    setup_standard_spin_input,
)
from app.ui.ui_helpers import (
    create_param_block,
    create_spin_param_block,
)
from app.ui.ui_styles import (
    MARGINS_NONE,
    SPACE_NONE,
    SPACE_SM,
)


class TemplateParamsNumberingMixin:
    # Собирает параметры нумерации, чтобы порядок файлов учитывался в новых именах.
    def _numbering_mode_items(self):
        return [
            "Простая нумерация",
            "Нумерация с префиксом",
            "Нумерация с датой",
        ]

    def _normalize_numbering_mode(self, value: str) -> str:
        text = str(value or "").strip()
        if text in self._numbering_mode_items():
            return text
        if text == "Простая нумерация":
            return "Простая нумерация"
        if text == "Нумерация с префиксом":
            return "Нумерация с префиксом"
        if text == "Нумерация с датой":
            return "Нумерация с датой"
        return "Простая нумерация"

    def _set_numbering_mode_visibility(self, mode_text: str | None = None):
        mode_getter = getattr(
            getattr(self, "template_numbering_mode", None),
            "currentText",
            lambda: "",
        )
        mode = self._normalize_numbering_mode(mode_text or mode_getter())
        simple_visible = mode == "Простая нумерация"
        prefix_visible = mode == "Нумерация с префиксом"
        date_visible = mode == "Нумерация с датой"

        for widget in (
            getattr(self, "template_num_simple_widget", None),
            getattr(self, "template_num_prefix_widget", None),
            getattr(self, "template_num_date_widget", None),
        ):
            if widget is not None:
                widget.setVisible(False)

        if (
            simple_visible
            and getattr(self, "template_num_simple_widget", None) is not None
        ):
            self.template_num_simple_widget.setVisible(True)
        elif (
            prefix_visible
            and getattr(self, "template_num_prefix_widget", None) is not None
        ):
            self.template_num_prefix_widget.setVisible(True)
        elif (
            date_visible
            and getattr(self, "template_num_date_widget", None) is not None
        ):
            self.template_num_date_widget.setVisible(True)

    def _on_numbering_mode_changed(self, _index=None):
        self._set_numbering_mode_visibility()
        if callable(getattr(self, "refresh_rename_preview", None)):
            self.refresh_rename_preview()
        if callable(getattr(self, "_schedule_settings_save", None)):
            self._schedule_settings_save()

    def get_numbering_mode(self) -> str:
        combo = getattr(self, "template_numbering_mode", None)
        if combo is None:
            return "Простая нумерация"
        return self._normalize_numbering_mode(combo.currentText())

    def set_numbering_mode(self, mode_text: str):
        combo = getattr(self, "template_numbering_mode", None)
        if combo is None:
            return
        target = self._normalize_numbering_mode(mode_text)
        index = combo.findText(target)
        if index >= 0:
            with signals_blocked(combo):
                combo.setCurrentIndex(index)
        self._set_numbering_mode_visibility(target)

    def _create_labeled_spin_block(
        self,
        label_text: str,
        spinbox: QSpinBox,
        *,
        label: QLabel | None = None,
    ):
        if label is None:
            return create_spin_param_block(label_text, spinbox)
        return self._create_param_block_with_label(label, spinbox)

    def _create_param_block_with_label(self, label: QLabel, field: QWidget):
        setup_standard_form_label(label)
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setSpacing(SPACE_NONE)
        layout.setContentsMargins(*MARGINS_NONE)
        layout.addWidget(label)

        field_container = QWidget()
        field_layout = QHBoxLayout(field_container)
        field_layout.setContentsMargins(*MARGINS_NONE)
        field_layout.addWidget(field)
        layout.addWidget(field_container)
        return container

    def create_numbering_params(self):
        """Создает параметры для нумерации"""
        container = QFrame()
        container.setObjectName("template_numbering_card")
        layout = QVBoxLayout(container)
        layout.setSpacing(SPACE_SM)
        layout.setContentsMargins(SPACE_NONE, SPACE_NONE, SPACE_NONE, SPACE_SM)

        self.template_numbering_mode = MenuLikeComboBox()
        self.template_numbering_mode.addItems(self._numbering_mode_items())
        setup_standard_dropdown(self.template_numbering_mode)
        self.template_numbering_mode.currentIndexChanged.connect(
            self._on_numbering_mode_changed
        )
        layout.addWidget(
            create_param_block("Как нумеровать:", self.template_numbering_mode)
        )

        self.template_num_simple_widget = QWidget()
        simple_layout = QHBoxLayout(self.template_num_simple_widget)
        simple_layout.setSpacing(SPACE_SM)
        simple_layout.setContentsMargins(*MARGINS_NONE)

        self.template_num_start = QSpinBox()
        self.template_num_start.setMinimum(1)
        self.template_num_start.setMaximum(9999)
        self.template_num_start.setValue(1)
        setup_standard_spin_input(self.template_num_start)
        simple_layout.addWidget(
            self._create_labeled_spin_block(
                "Начальный номер:", self.template_num_start
            )
        )

        self.template_num_step = QSpinBox()
        self.template_num_step.setMinimum(1)
        self.template_num_step.setMaximum(100)
        self.template_num_step.setValue(1)
        setup_standard_spin_input(self.template_num_step)
        simple_layout.addWidget(
            self._create_labeled_spin_block(
                "Шаг нумерации:", self.template_num_step
            )
        )

        self.template_num_digits = QSpinBox()
        self.template_num_digits.setMinimum(1)
        self.template_num_digits.setMaximum(6)
        self.template_num_digits.setValue(3)
        setup_standard_spin_input(self.template_num_digits)
        simple_layout.addWidget(
            self._create_labeled_spin_block(
                "Кол-во цифр:", self.template_num_digits
            )
        )

        self.template_num_sep = QLineEdit()
        self.template_num_sep.setText("_")
        self.template_num_sep.setMaxLength(5)
        self.template_num_sep.setProperty("renameTemplateField", True)
        setup_standard_line_input(self.template_num_sep)
        simple_layout.addWidget(create_param_block("Разделитель:", self.template_num_sep))

        self.template_num_prefix_widget = QWidget()
        prefix_layout = QHBoxLayout(self.template_num_prefix_widget)
        prefix_layout.setSpacing(SPACE_SM)
        prefix_layout.setContentsMargins(*MARGINS_NONE)

        self.template_prefix_text = QLineEdit("фото_")
        self.template_prefix_text.setProperty("renameTemplateField", True)
        setup_standard_line_input(self.template_prefix_text)
        prefix_layout.addWidget(
            create_param_block("Префикс:", self.template_prefix_text)
        )

        self.template_prefix_start = QSpinBox()
        self.template_prefix_start.setRange(1, 9999)
        self.template_prefix_start.setValue(1)
        setup_standard_spin_input(self.template_prefix_start)
        prefix_layout.addWidget(
            self._create_labeled_spin_block(
                "Начальный номер:", self.template_prefix_start
            )
        )

        self.template_prefix_step = QSpinBox()
        self.template_prefix_step.setRange(1, 100)
        self.template_prefix_step.setValue(1)
        setup_standard_spin_input(self.template_prefix_step)
        prefix_layout.addWidget(
            self._create_labeled_spin_block(
                "Шаг нумерации:", self.template_prefix_step
            )
        )

        self.template_prefix_digits = QSpinBox()
        self.template_prefix_digits.setRange(1, 6)
        self.template_prefix_digits.setValue(3)
        setup_standard_spin_input(self.template_prefix_digits)
        prefix_layout.addWidget(
            self._create_labeled_spin_block(
                "Кол-во цифр:", self.template_prefix_digits
            )
        )

        self.template_num_date_widget = QWidget()
        date_layout = QHBoxLayout(self.template_num_date_widget)
        date_layout.setSpacing(SPACE_SM)
        date_layout.setContentsMargins(*MARGINS_NONE)

        self.template_date_format = MenuLikeComboBox()
        self.template_date_format.addItems(
            [
                "2024-01-15",
                "15-01-2024",
            ]
        )
        setup_standard_dropdown(self.template_date_format)
        date_layout.addWidget(
            create_param_block("Формат даты:", self.template_date_format)
        )

        self.template_date_start = QSpinBox()
        self.template_date_start.setRange(1, 9999)
        self.template_date_start.setValue(1)
        setup_standard_spin_input(self.template_date_start)
        date_layout.addWidget(
            self._create_labeled_spin_block(
                "Начальный номер:", self.template_date_start
            )
        )

        self.template_date_step = QSpinBox()
        self.template_date_step.setRange(1, 100)
        self.template_date_step.setValue(1)
        setup_standard_spin_input(self.template_date_step)
        date_layout.addWidget(
            self._create_labeled_spin_block(
                "Шаг нумерации:", self.template_date_step
            )
        )

        self.template_date_digits = QSpinBox()
        self.template_date_digits.setRange(1, 6)
        self.template_date_digits.setValue(3)
        setup_standard_spin_input(self.template_date_digits)
        date_layout.addWidget(
            self._create_labeled_spin_block(
                "Кол-во цифр:", self.template_date_digits
            )
        )

        layout.addWidget(self.template_num_simple_widget)
        layout.addWidget(self.template_num_prefix_widget)
        layout.addWidget(self.template_num_date_widget)

        self._set_numbering_mode_visibility(
            getattr(self, "current_template", "")
        )

        self.template_params_layout.addWidget(container)

    def create_date_original_params(self):
        """Создает параметры для даты + оригинальное название"""
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setSpacing(SPACE_SM)
        layout.setContentsMargins(*MARGINS_NONE)

        self.template_original_date_format = MenuLikeComboBox()
        self.template_original_date_format.addItems(
            [
                "2024-01-15_название",
                "15-01-2024_название",
            ]
        )
        setup_standard_dropdown(self.template_original_date_format)
        layout.addWidget(
            create_param_block(
                "Дата в начале:", self.template_original_date_format
            )
        )
        self.template_params_layout.addWidget(container)

    def _insert_custom_template_token(self, token: str):
        """Вставляет команду шаблона в текущую позицию курсора."""
        field = getattr(self, "template_custom", None)
        if field is None:
            return

        field.insert(token)
        field.setFocus()

    def create_custom_template_params(self):
        """Создает параметры для пользовательского шаблона"""
        container = QWidget(self.template_params_widget)
        layout = QHBoxLayout(container)
        layout.setContentsMargins(*MARGINS_NONE)
        layout.setSpacing(SPACE_SM)
        self.template_custom = QLineEdit(self.template_params_widget)
        setup_standard_line_input(self.template_custom)
        self.template_custom.setPlaceholderText(
            "например: фото_{num:03d,start=1,step=1}_{date}_{name}"
        )
        self.template_custom.setText(
            "фото_{num:03d,start=1,step=1}_{date}_{name}"
        )
        self.template_custom.setProperty("renameTemplateField", True)
        apply_standard_field_style(self.template_custom)
        self.template_custom.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        layout.addWidget(self.template_custom, 1)
        self.template_params_layout.addWidget(create_param_block("Шаблон имени", container))

    def _choose_template_token(self):
        previous = getattr(self, "_template_token_menu", None)
        if previous is not None:
            previous.close()
            previous.deleteLater()
        menu = StandardPopupMenu(self.btn_insert_token)
        menu.setAccessibleName("Подстановки для имени файла")
        self._template_token_menu = menu
        for token, description, icon in (
            ("{name}", "Исходное имя файла без расширения", "rename"),
            ("{num:03d,start=1,step=1}", "Порядковый номер: 001, 002, 003…", "number"),
            ("{date}", "Текущая дата", "calendar"),
            ("{ext}", "Расширение файла без точки", "details"),
            ("{created}", "Дата создания файла", "calendar"),
            ("{modified}", "Дата последнего изменения файла", "history"),
            ("{exif_date}", "Дата съёмки из метаданных EXIF", "camera"),
            ("{width}", "Ширина изображения в пикселях", "width"),
            ("{height}", "Высота изображения в пикселях", "height"),
        ):
            action = menu.add_command(f"{description} — {token}", icon_name=icon)
            action.setData(token)
            action.triggered.connect(lambda _checked=False, value=token: self._insert_custom_template_token(value))
        menu.popup(self.btn_insert_token.mapToGlobal(self.btn_insert_token.rect().bottomLeft()))
