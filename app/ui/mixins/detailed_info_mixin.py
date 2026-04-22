# -*- coding: utf-8 -*-

import os
import sys

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)
from app.ui.ui_components import setup_standard_dialog


class DetailedInfoMixin:
    def _get_detailed_info_palette(self) -> dict[str, str]:
        mode = getattr(self, "theme_mode", "system")
        effective = mode
        if mode == "system":
            try:
                effective = self._get_system_theme_mode()
            except Exception:
                effective = "dark"

        if effective == "light":
            return {
                "dialog_bg": "#f3f3f3",
                "title": "#1f2328",
                "text": "#2b2f36",
                "link": "#0563C1",
                "link_hover": "#0B4E9B",
                "scroll_bg": "#f3f3f3",
            }

        return {
            "dialog_bg": "#4a4a4a",
            "title": "#e0e0e0",
            "text": "#cfcfcf",
            "link": "#5EA9FF",
            "link_hover": "#3E8FEF",
            "scroll_bg": "#4a4a4a",
        }

    def _get_qr_image_path(self) -> str:
        module_dir = os.path.dirname(os.path.abspath(__file__))
        run_dir = os.path.dirname(os.path.abspath(sys.argv[0])) if sys.argv else module_dir
        meipass_dir = getattr(sys, "_MEIPASS", "")

        candidates = [
            os.path.join(run_dir, "icons", "qr_code.png"),
            os.path.join(run_dir, "materials", "qrCode.png"),
            os.path.join(run_dir, "materials", "qr_code.png"),
            os.path.join(module_dir, "..", "..", "..", "icons", "qr_code.png"),
            os.path.join(module_dir, "..", "..", "..", "materials", "qrCode.png"),
            os.path.join(module_dir, "..", "..", "..", "materials", "qr_code.png"),
        ]
        if meipass_dir:
            candidates.extend(
                [
                    os.path.join(meipass_dir, "icons", "qr_code.png"),
                    os.path.join(meipass_dir, "materials", "qrCode.png"),
                    os.path.join(meipass_dir, "materials", "qr_code.png"),
                ]
            )

        for candidate in candidates:
            normalized = os.path.abspath(candidate)
            if os.path.exists(normalized):
                return normalized
        return ""

    def show_detailed_info(self):
        """Показывает модальное окно с подробной информацией о программе."""
        palette = self._get_detailed_info_palette()
        dialog = QDialog(self)
        setup_standard_dialog(dialog, title="Подробная информация о программе", min_width=500, min_height=400)
        dialog.setStyleSheet(
            """
            QDialog {
                background-color: %(dialog_bg)s;
            }
            QScrollArea {
                background-color: %(scroll_bg)s;
                border: none;
            }
            QScrollArea > QWidget > QWidget {
                background-color: %(scroll_bg)s;
            }
            QFrame#card {
                background-color: transparent;
                border: none;
                border-radius: 0px;
            }
            QLabel#card_title {
                font-size: 13px;
                font-weight: bold;
                color: %(title)s;
                margin-top: 6px;
                margin-bottom: 6px;
            }
            QLabel#card_item {
                font-size: 13px;
                color: %(text)s;
                margin: 0px;
                padding: 0px;
            }
            QLabel#card_link {
                font-size: 13px;
                color: %(text)s;
                margin: 0px;
                padding: 0px;
            }
            QLabel#card_link a {
                color: %(link)s;
                text-decoration: none;
                font-weight: bold;
            }
            QLabel#card_link a:hover {
                color: %(link_hover)s;
                text-decoration: underline;
            }
        """ % palette
        )

        layout = QVBoxLayout(dialog)
        layout.setSpacing(2)
        layout.setContentsMargins(0, 0, 0, 0)

        card_margins = (6, 2, 6, 2)
        card_spacing = 0

        title_label = QLabel("Мультифора - детальная информация")
        title_label.setStyleSheet(
            f"font-size: 13px; font-weight: bold; color: {palette['title']}; margin-top: 6px; margin-bottom: 6px;"
        )
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setSpacing(4)
        content_layout.setContentsMargins(0, 0, 0, 0)

        def create_info_card(title: str, items: list[str], item_spacing: int | None = None, wrap_items: bool = True):
            card = QFrame()
            card.setObjectName("card")
            card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(*card_margins)
            card_layout.setSpacing(card_spacing if item_spacing is None else item_spacing)

            if title:
                header = QLabel(title)
                header.setObjectName("card_title")
                card_layout.addWidget(header)

            for item in items:
                row = QWidget()
                row_layout = QHBoxLayout(row)
                row.setContentsMargins(0, 0, 0, 0)
                row_layout.setContentsMargins(0, 0, 0, 0)
                row_layout.setSpacing(0 if item_spacing == 0 else 6)

                text = item
                if text.startswith("•"):
                    text = text[1:].lstrip()

                item_label = QLabel()
                if "<a " in text or ("<" in text and ">" in text):
                    item_label.setObjectName("card_link")
                    item_label.setTextFormat(Qt.TextFormat.RichText)
                    item_label.setOpenExternalLinks(True)
                    item_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
                    styled_text = text.replace(
                        "<a ",
                        f'<a style="color:{palette["link"]}; text-decoration:none; font-weight:bold;" ',
                    )
                    item_label.setText(f"<span>{styled_text}</span>")
                else:
                    item_label.setObjectName("card_item")
                    item_label.setText(text)
                item_label.setContentsMargins(0, 0, 0, 0)
                item_label.setMargin(0)
                if item_spacing == 0:
                    if item_label.objectName() == "card_link":
                        item_label.setStyleSheet("margin: 0px; padding: 0px; line-height: 11px; font-size: 13px;")
                    else:
                        item_label.setStyleSheet("margin: 0px; padding: 0px; line-height: 11px; font-size: 13px;")
                item_label.setWordWrap(wrap_items)
                item_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
                row_layout.addWidget(item_label, 1)

                card_layout.addWidget(row)

            return card

        all_items = [
            '<div style="margin-top:6px; margin-bottom:6px;"><b>Основные возможности:</b></div>',
            "- Управление файлами через drag-and-drop",
            "- Пакетное переименование файлов",
            "- Конвертация документов между форматами",
            "- Сжатие изображений и PDF",
            "",
            '<div style="margin-top:6px; margin-bottom:6px;"><b>Поддерживаемые форматы:</b></div>',
            "- Документы: DOC, DOCX, PDF, TXT, RTF, ODT",
            "- Изображения: JPG, PNG; Архивы: ZIP, RAR, 7Z",
            "",
            '<div style="margin-top:6px; margin-bottom:6px;"><b>Разработка:</b></div>',
            "- Команда: Наспех",
            '- Главный разработчик: <a href="https://github.com/VseMirka200">VseMirka200</a>',
            '- Исходный код: <a href="https://github.com/VseMirka200/multifora">GitHub</a>',
            "",
            '<div style="margin-top:6px; margin-bottom:6px;"><b>Наши социальные сети:</b></div>',
            '- <a href="https://t.me/isip22">Telegram-канал</a>',
            "",
            '<div style="margin-top:6px; margin-bottom:6px;"><b>Поддержка проекта:</b></div>',
            'Если приложение вам нравится, вы можете поддержать его разработку: <a href="https://pay.cloudtips.ru/p/1fa22ea5">CloudTips</a>',
            "",
            '<div style="text-align:center; margin-top:2px; margin-bottom:2px;"><b>QR-код для сканирования ниже</b></div>',
        ]
        about_card = create_info_card("", all_items, item_spacing=0, wrap_items=True)
        content_layout.addWidget(about_card)

        if isinstance(about_card.layout(), QVBoxLayout):
            qr_image_label = QLabel()
            qr_image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            qr_image_path = self._get_qr_image_path()
            qr_pixmap = QPixmap(qr_image_path) if qr_image_path else QPixmap()
            if not qr_pixmap.isNull():
                qr_image_label.setPixmap(
                    qr_pixmap.scaled(
                        160,
                        160,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )
                )
            else:
                qr_image_label.setText("QR-код не найден")
                qr_image_label.setObjectName("card_item")
            about_card.layout().addSpacing(6)
            about_card.layout().addWidget(qr_image_label)
            about_card.layout().addSpacing(6)

            thanks_label = QLabel("Спасибо за вашу поддержку!")
            thanks_label.setObjectName("card_item")
            thanks_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            about_card.layout().addWidget(thanks_label)

        scroll.setWidget(content_widget)
        layout.addWidget(scroll)

        if callable(getattr(self, "attach_action_logging", None)):
            self.attach_action_logging(dialog)
        self.log_event("Открыто окно подробной информации")
        dialog.exec()


