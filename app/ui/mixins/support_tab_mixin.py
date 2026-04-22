# -*- coding: utf-8 -*-
import urllib.parse
import webbrowser

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)
from app.ui.ui_components import setup_standard_action_button, setup_standard_dialog, setup_standard_dropdown, setup_standard_primary_button


class SupportTabMixin:
    def create_support_tab(self):
        """Создает вкладку поддержки с упрощенной формой отправки сообщения."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        layout.addWidget(scroll)

        content_widget = QWidget()
        content_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 4, 0, 0)
        content_layout.setSpacing(0)
        content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        support_card = QFrame()
        support_card.setObjectName("card")
        support_card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        support_card_layout = QVBoxLayout(support_card)
        support_card_layout.setContentsMargins(8, 6, 8, 6)
        support_card_layout.setSpacing(4)

        title_label = QLabel("Поддержка")
        title_label.setObjectName("card_title")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        support_card_layout.addWidget(title_label)

        desc_label = QLabel(
            "Если у вас возникли проблемы с работой программы, есть вопросы "
            "или предложения по улучшению - напишите нам!"
        )
        desc_label.setStyleSheet("font-size: 13px; color: #ccc;")
        desc_label.setWordWrap(True)
        desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        support_card_layout.addWidget(desc_label)

        form_content = QWidget()
        form_layout = QVBoxLayout(form_content)
        form_layout.setSpacing(4)
        form_layout.setContentsMargins(0, 0, 0, 0)

        type_label = QLabel("Тип обращения:")
        type_label.setStyleSheet("font-size: 13px; font-weight: bold; color: #fff;")
        form_layout.addWidget(type_label)

        self.issue_type_combo = QComboBox()
        self.issue_type_combo.addItems(
            [
                "Сообщить об ошибке (баг)",
                "Задать вопрос",
                "Предложить идею",
            ]
        )
        setup_standard_dropdown(self.issue_type_combo)
        form_layout.addWidget(self.issue_type_combo)

        info_label = QLabel(
            "При отправке откроется ваш почтовый клиент с предзаполненной темой.\n\n"
            "Пожалуйста, подробно опишите проблему в теле письма и прикрепите скриншоты (если есть)."
        )
        info_label.setStyleSheet("font-size: 13px; color: #aaa; margin-top: 6px; margin-bottom: 6px;")
        info_label.setWordWrap(True)
        info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        form_layout.addWidget(info_label)

        send_btn = QPushButton("Отправить сообщение")
        send_btn.clicked.connect(self.send_email_from_tab)
        setup_standard_primary_button(send_btn)
        form_layout.addWidget(send_btn)

        form_content.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        support_card_layout.addWidget(form_content)
        content_layout.addWidget(support_card)
        scroll.setWidget(content_widget)

        return tab

    def _reorder_expandable_groups(self, layout: QVBoxLayout, groups: list):
        return

    def create_logs_tab(self):
        """Создает вкладку логов."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        layout.addWidget(scroll)

        content_widget = QWidget()
        content_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 4, 0, 0)
        content_layout.setSpacing(0)
        content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        logs_card = QFrame()
        logs_card.setObjectName("card")
        logs_card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        logs_card_layout = QVBoxLayout(logs_card)
        logs_card_layout.setContentsMargins(8, 6, 8, 6)
        logs_card_layout.setSpacing(4)

        title_label = QLabel("Логи")
        title_label.setObjectName("card_title")
        logs_card_layout.addWidget(title_label)

        self.logs_view = QPlainTextEdit()
        self.logs_view.setReadOnly(True)
        self.logs_view.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.logs_view.setMaximumBlockCount(self.max_log_lines)
        try:
            font = QFont("Consolas", 10)
            self.logs_view.setFont(font)
        except Exception:
            pass
        logs_card_layout.addWidget(self.logs_view)

        open_btn = QPushButton("Открыть логи")
        setup_standard_action_button(open_btn)
        open_btn.clicked.connect(self.open_logs_file)
        logs_card_layout.addWidget(open_btn)

        content_layout.addWidget(logs_card)
        scroll.setWidget(content_widget)

        self.load_logs_into_view()
        return tab

    def _build_support_mailto(self, issue_type: str) -> tuple[str, str]:
        issue_prefix = ""
        low = issue_type.lower()
        if "ошиб" in low or "баг" in low:
            issue_prefix = "БАГ"
        elif "вопрос" in low:
            issue_prefix = "ВОПРОС"
        elif "иде" in low or "предлож" in low:
            issue_prefix = "ПРЕДЛОЖЕНИЕ"

        email = "urban-solution@ya.ru"
        subject = f"[{issue_prefix}][Мультифора]"
        body = (
            "Чтобы мы могли помочь, пожалуйста, прикрепите скриншоты к этому письму "
            "(если есть)."
        )
        mailto_url = (
            f"mailto:{email}?subject={urllib.parse.quote(subject)}"
            f"&body={urllib.parse.quote(body)}"
        )
        return subject, mailto_url

    def send_email_from_tab(self, issue_type: str | None = None):
        """Отправка сообщения из вкладки помощи или из модального окна."""
        if issue_type is None:
            issue_type = self.issue_type_combo.currentText()

        subject, mailto_url = self._build_support_mailto(issue_type)
        email = "urban-solution@ya.ru"
        body = "Чтобы мы могли помочь, пожалуйста, прикрепите скриншоты к этому письму (если есть)."

        try:
            webbrowser.open(mailto_url)
            self.log_event(f"Открыт почтовый клиент: {subject}")
        except Exception as e:
            QMessageBox.warning(
                self,
                "Ошибка",
                "Не удалось открыть почтовый клиент: "
                f"{str(e)}\n\n"
                "Вы можете отправить письмо вручную на адрес:\n"
                f"{email}\n\n"
                f"Тема: {subject}\n\n"
                f"Сообщение:\n{body}",
            )
            self.log_event(f"Ошибка открытия почтового клиента: {str(e)}", "ERROR")

    def show_help_modal(self):
        """Открывает помощь как модальное окно."""
        dialog = QDialog(self)
        dialog._effective_theme_mode = getattr(self, "_effective_theme_mode", "dark")
        setup_standard_dialog(dialog, title="Помощь", min_width=460, min_height=180)

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(6)

        title = QLabel("Поддержка")
        title.setObjectName("card_title")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        desc = QLabel(
            "Выберите тип обращения и нажмите отправку. "
            "Откроется ваш почтовый клиент с готовой темой письма."
        )
        desc.setWordWrap(True)
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(desc)

        issue_combo = QComboBox()
        issue_combo._effective_theme_mode = getattr(self, "_effective_theme_mode", "dark")
        issue_combo.addItems(
            [
                "Сообщить об ошибке (баг)",
                "Задать вопрос",
                "Предложить идею",
            ]
        )
        setup_standard_dropdown(issue_combo)
        layout.addWidget(issue_combo)

        send_btn = QPushButton("Отправить")
        setup_standard_primary_button(send_btn)
        send_btn.clicked.connect(lambda: self.send_email_from_tab(issue_combo.currentText()))
        layout.addWidget(send_btn)
        if callable(getattr(self, "attach_action_logging", None)):
            self.attach_action_logging(dialog)
        self.log_event("Открыто окно помощи")
        dialog.exec()



