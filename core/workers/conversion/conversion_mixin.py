import html
import os
import re
import shutil
import subprocess
import sys
import textwrap
import threading
from collections.abc import Callable
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait

from app.core.app_utils import _debug_log
from app.core.conversion_formats import (
    DOCUMENT_CATEGORY,
    PDF_IMAGE_TARGETS,
    format_for_path,
    source_formats_for_category,
    suffix_for_format,
)
from app.core.deps import (
    HAS_ODF_PYTHON,
    HAS_PDF_TO_DOCX,
    HAS_PYMUPDF,
    OpenDocumentText,
    ensure_pandoc_detected,
    load,
    pdf2docx,
    teletype,
    text,
)
from app.core.deps import (
    HAS_PIL as HAS_PIL,
)
from app.core.models import FileItem
from core.workers.atomic_output import atomic_output_path
from core.workers.common import record_file_error

from .image_conversion_mixin import ImageConversionMixin
from .image_encoding_mixin import ImageEncodingMixin

_TEXT_ENCODINGS = ("utf-8-sig", "utf-8", "cp1251", "cp1252", "latin-1")

_HTML_BLOCK_TAGS = frozenset(
    {"p", "div", "br", "li", "tr", "h1", "h2", "h3", "h4", "h5", "h6"}
)

_HTML_END_BLOCK_TAGS = _HTML_BLOCK_TAGS - {"br"}


_CONVERSION_OUTPUT_PATH_LOCK = threading.Lock()
_PANDOC_SOURCE_FORMATS = frozenset(
    {"DOCX", "ODT", "RTF", "TXT", "HTML", "MD", "EPUB"}
)
_PANDOC_TARGET_FORMATS = frozenset(
    {"DOCX", "ODT", "RTF", "TXT", "HTML", "MD", "EPUB", "PDF"}
)


def _bundled_pdf_engine() -> str | None:
    executable = os.path.abspath(sys.argv[0]) if sys.argv else ""
    if not executable:
        return None
    candidate = os.path.join(
        os.path.dirname(executable), "bin", "tectonic", "tectonic.exe"
    )
    return candidate if os.path.isfile(candidate) else None


class ConversionMixin(ImageEncodingMixin, ImageConversionMixin):
    CONVERTED_FOLDER_NAME = "Конвертированные"

    def _conversion_output_directory(self, file: FileItem) -> str:
        mode = str(
            getattr(self, "conversion_output_mode", "source_subfolder")
            or "source_subfolder"
        ).strip()
        custom_dir = str(
            getattr(self, "conversion_output_dir", "") or ""
        ).strip()
        if mode == "custom" and custom_dir:
            output_dir = os.path.abspath(os.path.expanduser(custom_dir))
        else:
            source_dir = os.path.dirname(os.path.abspath(file.path))
            output_dir = (
                source_dir
                if mode == "alongside"
                else os.path.join(source_dir, self.CONVERTED_FOLDER_NAME)
            )
        os.makedirs(output_dir, exist_ok=True)
        return output_dir

    def _conversion_output_path(
        self,
        file: FileItem,
        target_ext: str,
        *,
        reference_file: FileItem | None = None,
    ) -> str:
        target_ext = str(target_ext or "").strip()
        if target_ext and not target_ext.startswith("."):
            target_ext = f".{target_ext}"
        reference = reference_file or file
        stem = os.path.splitext(os.path.basename(reference.path))[0]
        base_path = os.path.join(
            self._conversion_output_directory(reference),
            f"{stem}{target_ext}",
        )

        with _CONVERSION_OUTPUT_PATH_LOCK:
            reserved = getattr(self, "_conversion_reserved_paths", None)
            if reserved is None:
                reserved = set()
                self._conversion_reserved_paths = reserved

            candidate = base_path
            base, ext = os.path.splitext(base_path)
            counter = 1
            while (
                os.path.exists(candidate)
                or os.path.normcase(candidate) in reserved
            ):
                candidate = f"{base}_{counter}{ext}"
                counter += 1
            reserved.add(os.path.normcase(candidate))
        return candidate

    def _release_conversion_output_path(self, path: str) -> None:
        reserved = getattr(self, "_conversion_reserved_paths", None)
        if reserved is not None and path:
            reserved.discard(os.path.normcase(path))

    def _discard_conversion_output(self, path: str) -> None:
        """Удаляет частичный результат и освобождает зарезервированное имя."""
        if not path:
            return
        try:
            if os.path.exists(path):
                os.remove(path)
        except OSError as error:
            _debug_log(
                f"Не удалось удалить частичный результат {path}: {error}"
            )
        finally:
            self._release_conversion_output_path(path)

    def _report_file_conversion_error(
        self,
        file: FileItem,
        error: Exception,
    ) -> None:
        """Сохраняет и публикует ошибку конвертации одного файла."""
        message = f"Ошибка конвертации файла {file.name}: {error}"
        record_file_error(self, file, message)

    @staticmethod
    def _converted_file_item(path: str | None) -> FileItem | None:
        if path and os.path.exists(path):
            return FileItem(path)
        return None

    def _get_conversion_handler(
        self,
    ) -> Callable[[FileItem], str | list[str] | None] | None:
        handlers: dict[str, Callable[[FileItem], str | list[str] | None]] = {
            "docx_to_odt": self._convert_docx_to_odt,
            "odt_to_docx": self._convert_odt_to_docx,
            "odt_to_pdf": self._convert_odt_to_pdf,
            "pdf_to_odt": self._convert_pdf_to_odt,
            "pdf_to_image": self._convert_pdf_to_image,
            "pdf_to_images": self._convert_pdf_to_image,
            "image_to_pdf": self._convert_image_to_pdf,
            "image_to_image": lambda file: self._convert_image_to_image(
                file, self.conversion_format
            ),
            "auto_image": lambda file: self._convert_image_auto(
                file, self.conversion_format
            ),
            "auto_document": lambda file: self._convert_document_auto(
                file, self.conversion_format
            ),
        }
        return handlers.get(self.conversion_type)

    def _convert_with_pandoc(
        self,
        file: FileItem,
        target_format: str,
        *,
        output_reference: FileItem | None = None,
    ) -> str:
        source_format = format_for_path(file.path)
        normalized_target = str(target_format or "").upper()
        if source_format not in _PANDOC_SOURCE_FORMATS:
            raise Exception(
                f"Pandoc не поддерживает входной формат {source_format}"
            )
        if normalized_target not in _PANDOC_TARGET_FORMATS:
            raise Exception(
                f"Pandoc не поддерживает выходной формат {normalized_target}"
            )

        available, pandoc_path = ensure_pandoc_detected()
        if not available or not pandoc_path:
            raise Exception(
                "Pandoc не найден. Установите Pandoc или задайте MULTIFORA_PANDOC_PATH"
            )

        output_path = self._conversion_output_path(
            file,
            suffix_for_format(normalized_target),
            reference_file=output_reference,
        )
        command = [pandoc_path, file.path, "--output", output_path, "--standalone"]
        if normalized_target == "PDF":
            configured_engine = os.environ.get("MULTIFORA_PANDOC_PDF_ENGINE")
            pdf_engine = configured_engine or _bundled_pdf_engine() or next(
                (
                    engine
                    for engine in ("tectonic", "xelatex", "lualatex", "pdflatex")
                    if shutil.which(engine)
                ),
                None,
            )
            if pdf_engine:
                command.extend(("--pdf-engine", pdf_engine))
                if os.path.basename(pdf_engine).lower() in {
                    "tectonic",
                    "tectonic.exe",
                }:
                    command.extend(("--variable", "mainfont=Arial"))
        creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        process = None
        cancel_action = None
        try:
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                creationflags=creation_flags,
            )
            cancel_action = process.terminate
            register_cancel = getattr(self, "_set_active_cancel_action", None)
            if callable(register_cancel):
                register_cancel(cancel_action)
            _stdout, stderr = process.communicate()
            if self._should_cancel():
                raise InterruptedError("Конвертация отменена пользователем")
            if process.returncode != 0:
                details = (stderr or "неизвестная ошибка").strip()
                if normalized_target == "PDF":
                    details += (
                        ". Для PDF Pandoc требуется TeX-движок, например MiKTeX или Tectonic"
                    )
                raise Exception(f"Pandoc завершился с ошибкой: {details}")
            if not os.path.isfile(output_path):
                raise Exception("Pandoc не создал выходной файл")
            return output_path
        except Exception:
            self._discard_conversion_output(output_path)
            raise
        finally:
            clear_cancel = getattr(self, "_clear_active_cancel_action", None)
            if cancel_action is not None and callable(clear_cancel):
                clear_cancel(cancel_action)

    @staticmethod
    def _read_text_file(path: str) -> str:
        with open(path, "rb") as stream:
            data = stream.read()
        for encoding in _TEXT_ENCODINGS:
            try:
                return data.decode(encoding)
            except UnicodeDecodeError:
                continue
        return data.decode("utf-8", errors="replace")

    @staticmethod
    def _html_to_text(value: str) -> str:
        from html.parser import HTMLParser

        class _Extractor(HTMLParser):
            def __init__(self):
                super().__init__()
                self.parts = []

            def handle_starttag(self, tag, _attrs):
                if tag.lower() in _HTML_BLOCK_TAGS:
                    self.parts.append("\n")

            def handle_endtag(self, tag):
                if tag.lower() in _HTML_END_BLOCK_TAGS:
                    self.parts.append("\n")

            def handle_data(self, data):
                self.parts.append(data)

        parser = _Extractor()
        parser.feed(value)
        text_value = "".join(parser.parts)
        text_value = re.sub(r"[ \t]+\n", "\n", text_value)
        text_value = re.sub(r"\n{3,}", "\n\n", text_value)
        return html.unescape(text_value).strip()

    @staticmethod
    def _rtf_to_text(value: str) -> str:
        # Достаточный резервный разбор для обычного RTF.
        value = re.sub(
            r"\\'([0-9a-fA-F]{2})",
            lambda match: bytes([int(match.group(1), 16)]).decode(
                "cp1251", errors="replace"
            ),
            value,
        )
        value = re.sub(
            r"\\u(-?\d+)\??",
            lambda match: chr(int(match.group(1)) % 65536),
            value,
        )
        value = (
            value.replace(r"\par", "\n")
            .replace(r"\line", "\n")
            .replace(r"\tab", "\t")
        )
        value = re.sub(r"\\[a-zA-Z]+-?\d* ?", "", value)
        value = (
            value.replace(r"\{", "{").replace(r"\}", "}").replace(r"\\", "\\")
        )
        value = value.replace("{", "").replace("}", "")
        value = re.sub(r"\n{3,}", "\n\n", value)
        return value.strip()

    def _extract_document_text(self, file: FileItem) -> str:
        source_format = format_for_path(file.path)
        if source_format in {"TXT", "MD"}:
            return self._read_text_file(file.path)
        if source_format == "HTML":
            return self._html_to_text(self._read_text_file(file.path))
        if source_format == "RTF":
            return self._rtf_to_text(self._read_text_file(file.path))
        if source_format == "DOCX":
            try:
                import docx

                document = docx.Document(file.path)
                parts = [paragraph.text for paragraph in document.paragraphs]
                for table in document.tables:
                    parts.extend(
                        "\t".join(cell.text for cell in row.cells)
                        for row in table.rows
                    )
                return "\n".join(parts)
            except Exception as error:
                raise Exception(f"Ошибка чтения DOCX: {error}") from error
        if source_format == "ODT":
            if not HAS_ODF_PYTHON:
                raise Exception("Установите odfpy для чтения ODT")
            try:
                odt_doc = load(file.path)
                paragraphs: list[str] = []
                for element in odt_doc.getElementsByType(text.P):
                    paragraph = teletype.extractText(element)
                    if paragraph.strip():
                        paragraphs.append(paragraph)
                return "\n".join(paragraphs)
            except Exception as error:
                raise Exception(f"Ошибка чтения ODT: {error}") from error
        if source_format in {"PDF", "EPUB", "FB2", "XPS", "MOBI"}:
            if not HAS_PYMUPDF:
                raise Exception(
                    "Установите PyMuPDF для чтения этого документа"
                )
            try:
                import pymupdf as fitz

                with fitz.open(file.path) as document:
                    return "\n".join(
                        page.get_text("text") for page in document
                    )
            except Exception as error:
                raise Exception(
                    f"Ошибка извлечения текста из {source_format}: {error}"
                ) from error
        raise Exception(
            f"Неподдерживаемый формат документа: {source_format or file.path}"
        )

    @staticmethod
    def _write_plain_text_file(output_path: str, content: str) -> None:
        with open(output_path, "w", encoding="utf-8", newline="") as stream:
            stream.write(content)

    @staticmethod
    def _write_html_file(output_path: str, content: str) -> None:
        paragraphs: list[str] = []
        for paragraph in re.split(r"\n\s*\n", content):
            escaped = html.escape(paragraph.strip()).replace("\n", "<br>\n")
            if escaped:
                paragraphs.append(f"<p>{escaped}</p>")

        with open(output_path, "w", encoding="utf-8", newline="") as stream:
            stream.write(
                '<!doctype html><html><head><meta charset="utf-8"></head><body>\n'
            )
            stream.write("\n".join(paragraphs))
            stream.write("\n</body></html>")

    def _write_rtf_file(self, output_path: str, content: str) -> None:
        escaped = "".join(self._rtf_escape_char(char) for char in content)
        escaped = escaped.replace("\n", r"\par" + "\n")
        with open(
            output_path,
            "w",
            encoding="ascii",
            errors="ignore",
            newline="",
        ) as stream:
            stream.write(r"{\rtf1\ansi\deff0\uc1 ")
            stream.write(escaped)
            stream.write("}")

    @staticmethod
    def _write_docx_file(output_path: str, content: str) -> None:
        try:
            import docx

            document = docx.Document()
            for paragraph in content.splitlines() or [""]:
                document.add_paragraph(paragraph)
            document.save(output_path)
        except Exception as error:
            raise Exception(f"Ошибка создания DOCX: {error}") from error

    @staticmethod
    def _write_odt_file(output_path: str, content: str) -> None:
        if not HAS_ODF_PYTHON:
            raise Exception("Установите odfpy для создания ODT")
        try:
            document = OpenDocumentText()
            for paragraph in content.splitlines() or [""]:
                document.text.addElement(text.P(text=paragraph))
            document.save(output_path)
        except Exception as error:
            raise Exception(f"Ошибка создания ODT: {error}") from error

    def _write_text_output(
        self,
        file: FileItem,
        target_format: str,
        content: str,
    ) -> str:
        normalized_target = str(target_format or "").upper()
        if normalized_target == "PDF":
            # PDF создаёт собственный путь результата. Ранний выход исключает
            # двойное резервирование имени и появление лишнего суффикса ``_1``.
            return self._write_text_pdf(file, content)

        target_ext = suffix_for_format(normalized_target)
        if not target_ext:
            raise Exception(f"Нельзя сохранить текст в {normalized_target}")

        output_path = self._conversion_output_path(file, target_ext)
        writers: dict[str, Callable[[str, str], None]] = {
            "TXT": self._write_plain_text_file,
            "MD": self._write_plain_text_file,
            "HTML": self._write_html_file,
            "RTF": self._write_rtf_file,
            "DOCX": self._write_docx_file,
            "ODT": self._write_odt_file,
        }
        writer = writers.get(normalized_target)
        if writer is None:
            self._release_conversion_output_path(output_path)
            raise Exception(f"Нельзя сохранить текст в {normalized_target}")

        try:
            writer(output_path, content)
            return output_path
        except Exception:
            self._discard_conversion_output(output_path)
            raise

    @staticmethod
    def _rtf_escape_char(char: str) -> str:
        """Экранирует символ для простого RTF fallback-экспортера."""
        if char in "\\{}":
            return "\\" + char
        codepoint = ord(char)
        if codepoint <= 127:
            return char
        signed = codepoint if codepoint < 32768 else codepoint - 65536
        return f"\\u{signed}?"

    @staticmethod
    def _find_unicode_font() -> str | None:
        candidates = [
            r"C:\Windows\Fonts\segoeui.ttf",
            r"C:\Windows\Fonts\arial.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
        ]
        for candidate in candidates:
            if os.path.exists(candidate):
                return candidate
        return None

    def _write_text_pdf(
        self,
        file: FileItem,
        content: str,
        *,
        output_reference: FileItem | None = None,
    ) -> str:
        if not HAS_PYMUPDF:
            raise Exception("Установите PyMuPDF для создания PDF")

        import pymupdf as fitz

        output_path = self._conversion_output_path(
            file,
            ".pdf",
            reference_file=output_reference,
        )
        document = fitz.open()
        try:
            font_path = self._find_unicode_font()
            font_kwargs = (
                {"fontname": "multifora", "fontfile": font_path}
                if font_path
                else {"fontname": "helv"}
            )
            page = None
            y_position = 0.0
            page_width, page_height = 595.0, 842.0
            margin = 48.0
            line_height = 15.0
            max_chars = 92

            def new_page() -> None:
                nonlocal page, y_position
                page = document.new_page(width=page_width, height=page_height)
                y_position = margin

            new_page()
            normalized_content = content.replace("\r\n", "\n").replace(
                "\r", "\n"
            )
            for paragraph in normalized_content.split("\n"):
                lines = textwrap.wrap(
                    paragraph,
                    width=max_chars,
                    replace_whitespace=False,
                    drop_whitespace=False,
                ) or [""]
                for line in lines:
                    if y_position > page_height - margin:
                        new_page()
                    page.insert_text(
                        (margin, y_position),
                        line,
                        fontsize=10.5,
                        **font_kwargs,
                    )
                    y_position += line_height
            document.save(output_path)
            return output_path
        except Exception:
            self._discard_conversion_output(output_path)
            raise
        finally:
            document.close()

    def _try_pandoc_conversion(
        self,
        file: FileItem,
        target_format: str,
        *,
        output_reference: FileItem | None = None,
    ) -> str | None:
        source_format = format_for_path(file.path)
        target_format = str(target_format or "").upper()
        if source_format not in _PANDOC_SOURCE_FORMATS:
            return None
        if target_format not in _PANDOC_TARGET_FORMATS:
            return None
        return self._convert_with_pandoc(
            file,
            target_format,
            output_reference=output_reference,
        )

    def _convert_pymupdf_document_to_pdf(self, file: FileItem) -> str | None:
        source_format = format_for_path(file.path)
        if (
            source_format not in {"EPUB", "FB2", "XPS", "MOBI"}
            or not HAS_PYMUPDF
        ):
            return None
        try:
            import pymupdf as fitz

            output_path = self._conversion_output_path(file, ".pdf")
            with fitz.open(file.path) as document:
                pdf_bytes = document.convert_to_pdf()
            with open(output_path, "wb") as stream:
                stream.write(pdf_bytes)
            return output_path
        except Exception as error:
            if "output_path" in locals():
                self._discard_conversion_output(output_path)
            _debug_log(
                f"PyMuPDF не смог напрямую создать PDF из {source_format}: {error}"
            )
            return None

    def _convert_document_to_pdf(
        self,
        file: FileItem,
        source_format: str,
    ) -> str:
        direct_result = self._try_pandoc_conversion(file, "PDF")
        if direct_result:
            return direct_result

        pymupdf_result = self._convert_pymupdf_document_to_pdf(file)
        if pymupdf_result:
            return pymupdf_result

        content = self._extract_document_text(file)
        self._warn_text_only_conversion(file)
        return self._write_text_pdf(file, content)

    def _warn_text_only_conversion(self, file: FileItem) -> None:
        """Предупреждает, если текстовый маршрут отбросит оформление документа."""
        if format_for_path(file.path) in {"TXT", "MD"}:
            return
        reporter = getattr(self, "_record_warning", None)
        if callable(reporter):
            reporter(
                file,
                f"{file.name}: выполнен текстовый экспорт; изображения, стили и таблицы могут быть потеряны",
            )

    def _convert_document_auto(
        self,
        file: FileItem,
        target_format: str,
    ) -> str | list[str] | None:
        source_format = format_for_path(file.path)
        normalized_target = str(target_format or "").upper()
        if source_format not in source_formats_for_category(DOCUMENT_CATEGORY):
            raise Exception("Файл не является поддерживаемым документом")
        if source_format == normalized_target:
            self.status.emit(f"Пропущен {file.name}: уже {normalized_target}")
            return None

        if source_format == "PDF" and normalized_target in PDF_IMAGE_TARGETS:
            return self._convert_pdf_to_image(file, normalized_target)

        # Для PDF сохраняем специализированные конвертеры, потому что они лучше
        # восстанавливают структуру документа, чем текстовый резервный маршрут.
        if source_format == "PDF" and normalized_target == "DOCX":
            return self._convert_pdf_to_docx(file)
        if source_format == "PDF" and normalized_target == "ODT":
            return self._convert_pdf_to_odt(file)
        if normalized_target == "PDF":
            return self._convert_document_to_pdf(file, source_format)

        # Pandoc используется первым для совместимых форматов, чтобы сохранить
        # структуру документа и не зависеть от офисных приложений.
        if normalized_target in {"DOCX", "ODT", "RTF", "HTML"}:
            direct_result = self._try_pandoc_conversion(
                file, normalized_target
            )
            if direct_result:
                return direct_result

        content = self._extract_document_text(file)
        self._warn_text_only_conversion(file)
        return self._write_text_output(file, normalized_target, content)

    def _convert_files(self) -> None:
        total = len(self.files)
        results: list[FileItem] = []

        if self.conversion_type == "pandoc_to_pdf":
            self._emit_finished(self._convert_pandoc_to_pdf_batch(), [])
            return
        if self.conversion_type == "pdf_to_docx":
            self._emit_finished(self._convert_pdf_to_docx_batch(), [])
            return

        handler = self._get_conversion_handler()
        for index, file in enumerate(self.files):
            if self._should_cancel():
                self.status.emit("Операция отменена пользователем")
                self._emit_finished(results, [])
                return
            if not file.is_file:
                continue

            self.status.emit(f"Конвертация: {file.name}")
            try:
                if handler is None:
                    raise Exception(
                        f"Неизвестная операция конвертации: {self.conversion_type}"
                    )
                output = handler(file)
                for path in output if isinstance(output, list) else [output]:
                    converted_item = self._converted_file_item(path)
                    if converted_item is not None:
                        results.append(converted_item)
            except Exception as error:
                self._report_file_conversion_error(file, error)

            self.progress.emit(int((index + 1) / total * 100))

        self._emit_finished(results, [])

    def _convert_sequential_batch(
        self,
        files: list[FileItem],
        converter: Callable[[FileItem], str | None],
    ) -> list[FileItem]:
        """Выполняет однотипную конвертацию последовательно с общим UI-циклом."""
        total = len(files)
        results: list[FileItem] = []
        for index, file in enumerate(files):
            if self._should_cancel():
                self.status.emit("Операция отменена пользователем")
                break
            if not file.is_file:
                continue

            self.status.emit(f"Конвертация: {file.name}")
            try:
                converted_item = self._converted_file_item(converter(file))
                if converted_item is not None:
                    results.append(converted_item)
            except Exception as error:
                self._report_file_conversion_error(file, error)
            self.progress.emit(int((index + 1) / total * 100))
        return results

    def _convert_pandoc_to_pdf_batch(self) -> list[FileItem]:
        """Последовательно конвертирует DOCX в PDF через Pandoc."""
        return self._convert_sequential_batch(
            list(self.files),
            self._convert_docx_to_pdf,
        )

    def _convert_pdf_to_docx_batch(self) -> list[FileItem]:
        files = [f for f in self.files if getattr(f, "is_file", False)]
        total = len(files)
        results: list[FileItem] = []
        if total == 0:
            return results

        if not HAS_PDF_TO_DOCX:
            msg = "Установите pdf2docx"
            record_file_error(self, None, msg)
            return results

        max_workers = min(4, max(1, ((os.cpu_count() or 2) // 2)))
        if total <= 1 or max_workers == 1:
            return self._convert_sequential_batch(
                files, self._convert_pdf_to_docx
            )

        processed = 0
        with ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="pdf2docx",
        ) as executor:
            future_map = {}
            for file in files:
                if self._should_cancel():
                    break
                if file.path.lower().endswith(".pdf"):
                    future_map[
                        executor.submit(self._convert_pdf_to_docx, file)
                    ] = file
                else:
                    processed += 1
                    self.progress.emit(int(processed / total * 100))

            pending = set(future_map)
            while pending:
                if self._should_cancel():
                    for future in pending:
                        future.cancel()
                    self.status.emit(
                        "Отмена: ожидаем завершения уже запущенных конвертаций…"
                    )
                    break
                # wait с таймаутом позволяет проверить запрос отмены, даже если
                # pdf2docx долго обрабатывает одну страницу документа.
                done, pending = wait(
                    pending, timeout=0.2, return_when=FIRST_COMPLETED
                )
                for future in done:
                    file = future_map[future]
                    self.status.emit(f"Конвертация: {file.name}")
                    try:
                        converted_item = self._converted_file_item(
                            future.result()
                        )
                        if converted_item is None:
                            raise Exception(
                                "pdf2docx не создал выходной DOCX-файл"
                            )
                        results.append(converted_item)
                    except Exception as error:
                        self._report_file_conversion_error(file, error)
                    finally:
                        processed += 1
                        self.progress.emit(int(processed / total * 100))

            # ThreadPoolExecutor ожидает активные задачи перед выходом из with.
            # Результаты, успевшие закончиться после запроса отмены, убираем,
            # чтобы не оставить на диске файлы, не показанные пользователю.
            if self._should_cancel():
                published = {item.path for item in results}
                for future in pending:
                    if future.cancelled():
                        continue
                    try:
                        path = future.result()
                    except Exception:
                        continue
                    if path and path not in published:
                        self._discard_conversion_output(path)

        return results

    def _convert_docx_to_pdf(
        self,
        file: FileItem,
        *,
        output_reference: FileItem | None = None,
    ) -> str:
        if not file.path.lower().endswith(".docx"):
            return None
        return self._convert_with_pandoc(
            file,
            "PDF",
            output_reference=output_reference,
        )

    def _convert_pdf_to_docx(self, file: FileItem) -> str:
        if not file.path.lower().endswith(".pdf"):
            return None
        if not HAS_PDF_TO_DOCX:
            raise Exception("Установите pdf2docx")

        docx_path = self._conversion_output_path(file, ".docx")
        try:
            with atomic_output_path(docx_path) as temporary:
                converter = pdf2docx.Converter(file.path)
                try:
                    converter.convert(temporary)
                finally:
                    converter.close()
                if self._should_cancel():
                    raise InterruptedError(
                        "Конвертация отменена пользователем"
                    )
            return docx_path
        except Exception as error:
            self._release_conversion_output_path(docx_path)
            raise Exception(
                f"Ошибка конвертации PDF в DOCX: {error}"
            ) from error

    def _convert_docx_to_odt(
        self,
        file: FileItem,
        *,
        output_reference: FileItem | None = None,
    ) -> str:
        if not file.path.lower().endswith(".docx"):
            return None
        return self._convert_with_pandoc(
            file, "ODT", output_reference=output_reference
        )

    def _convert_odt_to_docx(self, file: FileItem) -> str:
        if not file.path.lower().endswith(".odt"):
            return None
        return self._convert_with_pandoc(file, "DOCX")

    def _convert_odt_to_pdf(self, file: FileItem) -> str:
        if not file.path.lower().endswith(".odt"):
            return None
        return self._convert_with_pandoc(file, "PDF")

    def _convert_pdf_to_odt(self, file: FileItem) -> str:
        if file.path.lower().endswith(".pdf"):
            docx_path = self._convert_pdf_to_docx(file)
            if not docx_path or not os.path.exists(docx_path):
                raise Exception("Не удалось создать DOCX из PDF")
            try:
                return self._convert_docx_to_odt(
                    FileItem(docx_path),
                    output_reference=file,
                )
            finally:
                try:
                    if os.path.exists(docx_path):
                        os.remove(docx_path)
                except OSError as error:
                    _debug_log(
                        f"Не удалось удалить промежуточный DOCX: {error}"
                    )
        return None
