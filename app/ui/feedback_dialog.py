"""Компактная форма подготовки обращения в GitFlic."""

from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
)

from app.core.feedback import (
    GITFLIC_NEW_ISSUE_URL,
    ISSUE_TYPES,
    get_issue_type,
    issue_markdown,
)
from app.ui.ui_components import (
    setup_standard_dialog,
    setup_standard_line_input,
    setup_standard_primary_button,
    setup_standard_secondary_button,
)


class FeedbackDialog(QDialog):
    """Не отправляет информацию в сеть: копирует шаблон, открывает браузер."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._effective_theme_mode = getattr(parent, "_effective_theme_mode", "dark")
        setup_standard_dialog(self, title="Обращение в GitFlic")
        self.setWindowFlag(Qt.WindowType.MSWindowsFixedSizeDialogHint, True)
        self.setWindowFlag(Qt.WindowType.WindowMaximizeButtonHint, False)
        self.setSizeGripEnabled(False)
        if parent is not None:
            self.setStyleSheet(parent.styleSheet())

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(8)

        hint = QLabel("Выберите тему, заполните обращение и откройте GitFlic.")
        hint.setWordWrap(True)
        root.addWidget(hint)

        root.addWidget(QLabel("Тип обращения"))
        self.issue_type = QComboBox(self)
        for kind in ISSUE_TYPES:
            self.issue_type.addItem(kind.caption, kind.key)
        root.addWidget(self.issue_type)

        root.addWidget(QLabel("Название"))
        self.subject = QLineEdit(self)
        setup_standard_line_input(self.subject)
        self.subject.setMaxLength(250)  # лимит GitFlic
        root.addWidget(self.subject)

        root.addWidget(QLabel("Описание (Markdown)"))
        self.details = QPlainTextEdit(self)
        self.details.setObjectName("feedback_description")
        self.details.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        root.addWidget(self.details)

        privacy_hint = QLabel(
            "🔒 Обращение не отправляется автоматически. Скопируйте название "
            "и описание по отдельности, затем опубликуйте проблему в GitFlic."
        )
        privacy_hint.setWordWrap(True)
        root.addWidget(privacy_hint)

        copy_buttons = QHBoxLayout()
        copy_buttons.setSpacing(8)
        self.copy_title_button = QPushButton("Копировать название")
        setup_standard_secondary_button(self.copy_title_button)
        self.copy_title_button.clicked.connect(self.copy_title)
        copy_buttons.addWidget(self.copy_title_button)
        self.copy_details_button = QPushButton("Копировать описание")
        setup_standard_secondary_button(self.copy_details_button)
        self.copy_details_button.clicked.connect(self.copy_description)
        copy_buttons.addWidget(self.copy_details_button)
        copy_buttons.addStretch(1)
        root.addLayout(copy_buttons)

        buttons = QHBoxLayout()
        buttons.setSpacing(8)
        self.cancel_button = QPushButton("Закрыть")
        setup_standard_secondary_button(self.cancel_button)
        self.cancel_button.clicked.connect(self.reject)
        buttons.addWidget(self.cancel_button)
        buttons.addStretch(1)
        self.submit_button = QPushButton("Открыть GitFlic")
        setup_standard_primary_button(self.submit_button)
        self.submit_button.clicked.connect(self.copy_and_open)
        buttons.addWidget(self.submit_button)
        root.addLayout(buttons)

        self.issue_type.currentIndexChanged.connect(self._fill_template)
        self._fill_template()
        # Фиксированное компактное окно, в описании скролл вместо растяжения.
        screen = QApplication.primaryScreen()
        available = screen.availableGeometry() if screen else None
        width = min(530, available.width() - 40) if available else 530
        height = min(490, available.height() - 80) if available else 490
        self.setFixedSize(max(340, width), max(300, height))

    def _fill_template(self, _index=0):
        kind = get_issue_type(self.issue_type.currentData())
        self.subject.setText(kind.subject)
        self.details.setPlainText(issue_markdown(kind.key))

    def copy_title(self):
        QApplication.clipboard().setText(self.subject.text().strip())

    def copy_description(self):
        QApplication.clipboard().setText(self.details.toPlainText().strip())

    def copy_and_open(self):
        if not self.subject.text().strip() or not self.details.toPlainText().strip():
            QMessageBox.information(self, "Неполное обращение", "Укажите название и описание.")
            return
        self.copy_description()
        if not QDesktopServices.openUrl(QUrl(GITFLIC_NEW_ISSUE_URL)):
            QMessageBox.warning(
                self,
                "Не удалось открыть GitFlic",
                "Описание уже скопировано. Откройте вручную: "
                + GITFLIC_NEW_ISSUE_URL,
            )
        # Не закрываем форму: после вставки описания можно вернуться и
        # скопировать название в отдельное поле GitFlic.
