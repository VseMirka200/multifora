import html
import os
import re
import tempfile
import threading
from collections.abc import Callable
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait

from app.core.app_utils import _debug_log
from app.core.conversion_formats import (
    DOCUMENT_CATEGORY,
    format_for_path,
    source_formats_for_category,
    suffix_for_format,
)
from app.core.deps import (
    HAS_ODF_PYTHON,
    OpenDocumentText,
    load,
    teletype,
    text,
)
from app.core.deps import (
    HAS_PIL as HAS_PIL,
)
from app.core.models import FileItem
from core.workers.atomic_output import atomic_output_path
from core.workers.common import record_file_error
from core.workers.ghostscript_engine import GhostscriptUnavailableError
from core.workers.pandoc_engine import PandocUnavailableError, run_pandoc

from .image_conversion_mixin import ImageConversionMixin
from .image_encoding_mixin import ImageEncodingMixin
from .tectonic_pdf import TectonicUnavailableError

_TEXT_ENCODINGS = ("utf-8-sig", "utf-8", "cp1251", "cp1252", "latin-1")

_HTML_BLOCK_TAGS = frozenset({"p", "div", "br", "li", "tr", "h1", "h2", "h3", "h4", "h5", "h6"})

_HTML_END_BLOCK_TAGS = _HTML_BLOCK_TAGS - {"br"}


_CONVERSION_OUTPUT_PATH_LOCK = threading.Lock()


class ConversionMixin(ImageEncodingMixin, ImageConversionMixin):
    CONVERTED_FOLDER_NAME = "Конвертированные"

    def _conversion_output_directory(self, file: FileItem) -> str:
        mode = str(getattr(self, "conversion_output_mode", "source_subfolder") or "source_subfolder").strip()
        custom_dir = str(getattr(self, "conversion_output_dir", "") or "").strip()
        if mode == "custom" and custom_dir:
            output_dir = os.path.abspath(os.path.expanduser(custom_dir))
        else:
            source_dir = os.path.dirname(os.path.abspath(file.path))
            output_dir = source_dir if mode == "alongside" else os.path.join(source_dir, self.CONVERTED_FOLDER_NAME)
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
            while os.path.exists(candidate) or os.path.normcase(candidate) in reserved:
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
            _debug_log(f"Не удалось удалить частичный результат {path}: {error}")
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
            "auto_document": lambda file: self._convert_document_auto(file, self.conversion_format),
        }
        return handlers.get(self.conversion_type)

    def _convert_text_document(
        self, file: FileItem, target_format: str, *, output_reference: FileItem | None = None
    ) -> str:
        if target_format.upper() == "PDF":
            return self._convert_document_to_pdf(file, format_for_path(file.path), output_reference=output_reference)
        # Legacy routes use the built-in text converter.
        content = self._extract_document_text(file)
        self._warn_text_only_conversion(file)
        if target_format.upper() == "PDF":
            return self._write_text_pdf(file, content, output_reference=output_reference)
        return self._write_text_output(file, target_format, content, output_reference=output_reference)

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
            lambda match: bytes([int(match.group(1), 16)]).decode("cp1251", errors="replace"),
            value,
        )
        value = re.sub(
            r"\\u(-?\d+)\??",
            lambda match: chr(int(match.group(1)) % 65536),
            value,
        )
        value = value.replace(r"\par", "\n").replace(r"\line", "\n").replace(r"\tab", "\t")
        value = re.sub(r"\\[a-zA-Z]+-?\d* ?", "", value)
        value = value.replace(r"\{", "{").replace(r"\}", "}").replace(r"\\", "\\")
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
                    parts.extend("\t".join(cell.text for cell in row.cells) for row in table.rows)
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
        if source_format == "PDF":
            from core.workers.ghostscript_engine import run_ghostscript

            with tempfile.TemporaryDirectory(prefix="multifora_text_") as directory:
                output = os.path.join(directory, "document.txt")
                run_ghostscript(
                    ["-sDEVICE=txtwrite", "-dTextFormat=3", f"-sOutputFile={output}", os.path.abspath(file.path)],
                    self._should_cancel,
                )
                return self._read_text_file(output)
        if source_format in {"EPUB", "FB2", "XPS", "MOBI"}:
            from .ebook_text import read_ebook_text

            return read_ebook_text(file.path, source_format, self._html_to_text)
        raise Exception(f"Неподдерживаемый формат документа: {source_format or file.path}")

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
            stream.write('<!doctype html><html><head><meta charset="utf-8"></head><body>\n')
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
        *,
        output_reference: FileItem | None = None,
    ) -> str:
        normalized_target = str(target_format or "").upper()
        if normalized_target == "PDF":
            # PDF создаёт собственный путь результата. Ранний выход исключает
            # двойное резервирование имени и появление лишнего суффикса ``_1``.
            return self._write_text_pdf(file, content, output_reference=output_reference)

        target_ext = suffix_for_format(normalized_target)
        if not target_ext:
            raise Exception(f"Нельзя сохранить текст в {normalized_target}")

        output_path = self._conversion_output_path(file, target_ext, reference_file=output_reference)
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
            with atomic_output_path(output_path) as temporary:
                writer(temporary, content)
            return output_path
        except Exception:
            self._release_conversion_output_path(output_path)
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

    def _write_text_pdf(self, file: FileItem, content: str, *, output_reference: FileItem | None = None) -> str:
        from .pdf_layout import PdfLayout

        markup = "".join("<p>" + (html.escape(line) or "&#160;") + "</p>" for line in content.split("\n"))
        return self._write_layout_pdf(file, PdfLayout(markup=markup), output_reference=output_reference)

    def _write_docx_pdf(self, file: FileItem, *, output_reference: FileItem | None = None) -> str:
        from .pdf_layout import docx_layout

        return self._write_layout_pdf(file, docx_layout(file.path), output_reference=output_reference)

    def _write_layout_pdf(
        self, file: FileItem, layout, *, output_reference: FileItem | None = None, resource_dir: str | None = None
    ) -> str:
        from .tectonic_pdf import render_pdf

        output_path = self._conversion_output_path(file, ".pdf", reference_file=output_reference)
        try:
            status_signal = getattr(self, "status", None)
            emit_status = getattr(status_signal, "emit", None)
            render_pdf(
                layout,
                output_path,
                self._should_cancel,
                resource_dir,
                status=(lambda message: emit_status(f"{file.name}: {message}")) if callable(emit_status) else None,
            )
            reporter = getattr(self, "_record_warning", None)
            if callable(reporter) and layout.warnings:
                reporter(file, f"{file.name}: " + "; ".join(sorted(layout.warnings)))
            return output_path
        except Exception:
            self._release_conversion_output_path(output_path)
            raise

    def _convert_document_to_pdf(
        self,
        file: FileItem,
        source_format: str,
        *,
        output_reference: FileItem | None = None,
    ) -> str:
        if source_format == "DOCX":
            return self._write_docx_pdf(file, output_reference=output_reference)
        if source_format == "ODT":
            from .pdf_layout import odt_layout

            return self._write_layout_pdf(file, odt_layout(file.path), output_reference=output_reference)
        if source_format == "EPUB":
            from .pdf_layout import epub_layout

            return self._write_layout_pdf(file, epub_layout(file.path), output_reference=output_reference)
        if source_format == "FB2":
            from .pdf_layout import fb2_layout

            return self._write_layout_pdf(file, fb2_layout(file.path), output_reference=output_reference)
        if source_format == "HTML":
            from .pdf_layout import PdfLayout

            markup = self._read_text_file(file.path)
            layout = PdfLayout(markup=markup)
            layout.warnings.add("часть CSS и внешние ресурсы HTML могут не поддерживаться")
            return self._write_layout_pdf(
                file,
                layout,
                output_reference=output_reference,
                resource_dir=os.path.dirname(os.path.abspath(file.path)),
            )
        if source_format == "MD":
            from .pdf_layout import markdown_layout

            layout = markdown_layout(self._read_text_file(file.path))
            return self._write_layout_pdf(
                file,
                layout,
                output_reference=output_reference,
                resource_dir=os.path.dirname(os.path.abspath(file.path)),
            )
        from .pdf_layout import PdfLayout

        content = self._extract_document_text(file)
        layout = PdfLayout(
            markup="".join("<p>" + (html.escape(line) or "&#160;") + "</p>" for line in content.splitlines())
        )
        if source_format != "TXT":
            layout.warnings.add("оформление исходного документа может быть потеряно")
        return self._write_layout_pdf(file, layout, output_reference=output_reference)

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

        readers = {
            "DOCX": "docx", "ODT": "odt", "HTML": "html", "MD": "markdown", "EPUB": "epub", "FB2": "fb2", "RTF": "rtf",
        }
        writers = {
            "DOCX": "docx", "ODT": "odt", "HTML": "html", "MD": "markdown", "EPUB": "epub",
            "RTF": "rtf", "TXT": "plain",
        }
        if source_format not in readers or normalized_target not in writers:
            raise ValueError("Неподдерживаемое направление конвертации Pandoc")
        output_path = self._conversion_output_path(file, suffix_for_format(normalized_target))
        try:
            with atomic_output_path(output_path) as temporary:
                warning = run_pandoc(
                    file.path, temporary, readers[source_format], writers[normalized_target], self._should_cancel
                )
            if warning:
                self._record_warning(file, f"Pandoc: {warning}")
            return output_path
        finally:
            self._release_conversion_output_path(output_path)

    def _convert_files(self) -> None:
        total = len(self.files)
        results: list[FileItem] = []

        handler = self._get_conversion_handler()
        for index, file in enumerate(self.files):
            if self._should_cancel():
                self.status.emit("Операция отменена пользователем")
                self._emit_finished(results, [])
                return
            if not file.is_file:
                continue

            self.status.emit(f"Конвертация {index + 1} из {total}: {file.name}")
            try:
                if handler is None:
                    raise Exception(f"Неизвестная операция конвертации: {self.conversion_type}")
                output = handler(file)
                for path in output if isinstance(output, list) else [output]:
                    converted_item = self._converted_file_item(path)
                    if converted_item is not None:
                        results.append(converted_item)
            except InterruptedError as error:
                if self._should_cancel():
                    self.status.emit("Операция отменена пользователем")
                    self._emit_finished(results, [])
                    return
                self._report_file_conversion_error(file, error)
            except Exception as error:
                self._report_file_conversion_error(file, error)
                if isinstance(error, (TectonicUnavailableError, GhostscriptUnavailableError, PandocUnavailableError)):
                    self._report_unprocessed_engine_errors(self.files[index + 1 :], error)
                    self.progress.emit(100)
                    break

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

            self.status.emit(f"Конвертация {index + 1} из {total}: {file.name}")
            try:
                converted_item = self._converted_file_item(converter(file))
                if converted_item is not None:
                    results.append(converted_item)
            except InterruptedError as error:
                if self._should_cancel():
                    self.status.emit("Операция отменена пользователем")
                    break
                self._report_file_conversion_error(file, error)
            except Exception as error:
                self._report_file_conversion_error(file, error)
                if isinstance(error, (TectonicUnavailableError, GhostscriptUnavailableError)):
                    self._report_unprocessed_engine_errors(files[index + 1 :], error)
                    self.progress.emit(100)
                    break
            self.progress.emit(int((index + 1) / total * 100))
        return results

    def _report_unprocessed_engine_errors(self, files, error: Exception) -> None:
        """Не запускает каждый следующий файл при общей ошибке движка."""
        for file in files:
            if getattr(file, "is_file", False):
                self._report_file_conversion_error(file, error)

    def _convert_docx_to_pdf_batch(self) -> list[FileItem]:
        """Последовательно конвертирует DOCX в PDF."""
        return self._convert_sequential_batch(
            list(self.files),
            self._convert_docx_to_pdf,
        )

    @staticmethod
    def _pdf_docx_worker_count(files: list[FileItem]) -> int:
        """Ограничивает число движков, чтобы большие PDF не перегружали память."""
        maximum = min(4, max(1, (os.cpu_count() or 2) // 2))
        sizes = []
        for file in files:
            try:
                sizes.append(os.path.getsize(file.path))
            except OSError:
                continue
        if sizes and max(sizes) >= 25 * 1024 * 1024:
            return 1
        if sizes and max(sizes) >= 10 * 1024 * 1024:
            return min(2, maximum)
        return maximum

    def _convert_pdf_to_docx_batch(self) -> list[FileItem]:
        files = [f for f in self.files if getattr(f, "is_file", False)]
        total = len(files)
        results_by_index: dict[int, FileItem] = {}
        if total == 0:
            return []

        max_workers = self._pdf_docx_worker_count(files)
        if total <= 1 or max_workers == 1:
            return self._convert_sequential_batch(files, self._convert_pdf_to_docx)

        valid = [(index, file) for index, file in enumerate(files) if file.path.lower().endswith(".pdf")]
        processed = total - len(valid)
        if processed:
            self.progress.emit(int(processed / total * 100))
        if valid:
            self.status.emit(f"Конвертация PDF: одновременно до {max_workers} файлов")
        next_file = 0
        common_error = None
        with ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="pdf-to-docx",
        ) as executor:
            pending = {}
            while next_file < len(valid) and len(pending) < max_workers and not self._should_cancel():
                index, file = valid[next_file]
                pending[executor.submit(self._convert_pdf_to_docx, file)] = (index, file)
                next_file += 1
            while pending:
                if self._should_cancel():
                    for future in pending:
                        future.cancel()
                    self.status.emit("Отмена: ожидаем завершения уже запущенных конвертаций…")
                    break
                # wait с таймаутом позволяет проверить запрос отмены, даже если
                # долго обрабатывает одну страницу документа.
                done, _ = wait(pending, timeout=0.2, return_when=FIRST_COMPLETED)
                for future in sorted(done, key=lambda item: pending[item][0]):
                    index, file = pending.pop(future)
                    self.status.emit(f"Конвертация: {file.name}")
                    try:
                        converted_item = self._converted_file_item(future.result())
                        if converted_item is None:
                            raise Exception("Движок не создал выходной DOCX-файл")
                        results_by_index[index] = converted_item
                    except InterruptedError as error:
                        if not self._should_cancel():
                            self._report_file_conversion_error(file, error)
                    except Exception as error:
                        self._report_file_conversion_error(file, error)
                        if isinstance(error, GhostscriptUnavailableError):
                            common_error = error
                    finally:
                        processed += 1
                        self.progress.emit(int(processed / total * 100))
                while (
                    common_error is None
                    and next_file < len(valid)
                    and len(pending) < max_workers
                    and not self._should_cancel()
                ):
                    index, file = valid[next_file]
                    pending[executor.submit(self._convert_pdf_to_docx, file)] = (index, file)
                    next_file += 1

            # ThreadPoolExecutor ожидает активные задачи перед выходом из with.
            # Результаты, успевшие закончиться после запроса отмены, убираем,
            # чтобы не оставить на диске файлы, не показанные пользователю.
            if self._should_cancel():
                published = {item.path for item in results_by_index.values()}
                for future in pending:
                    if future.cancelled():
                        continue
                    try:
                        path = future.result()
                    except Exception:
                        continue
                    if path and path not in published:
                        self._discard_conversion_output(path)
        if common_error is not None and not self._should_cancel():
            self._report_unprocessed_engine_errors([file for _, file in valid[next_file:]], common_error)
            self.progress.emit(100)
        return [results_by_index[index] for index in sorted(results_by_index)]

    def _convert_docx_to_pdf(
        self,
        file: FileItem,
        *,
        output_reference: FileItem | None = None,
    ) -> str:
        if not file.path.lower().endswith(".docx"):
            return None
        return self._convert_text_document(
            file,
            "PDF",
            output_reference=output_reference,
        )

    def _convert_pdf_to_docx(self, file: FileItem) -> str:
        if not file.path.lower().endswith(".pdf"):
            return None
        from core.workers.ghostscript_engine import run_ghostscript

        docx_path = self._conversion_output_path(file, ".docx")
        try:
            with atomic_output_path(docx_path) as temporary:
                run_ghostscript(
                    ["-sDEVICE=docxwrite", f"-sOutputFile={temporary}", os.path.abspath(file.path)],
                    self._should_cancel,
                )
                if self._should_cancel():
                    raise InterruptedError("Конвертация отменена пользователем")
            return docx_path
        except (InterruptedError, GhostscriptUnavailableError):
            self._release_conversion_output_path(docx_path)
            raise
        except Exception as error:
            self._release_conversion_output_path(docx_path)
            raise Exception(f"Ошибка конвертации PDF в DOCX: {error}") from error

    def _convert_docx_to_odt(
        self,
        file: FileItem,
        *,
        output_reference: FileItem | None = None,
    ) -> str:
        if not file.path.lower().endswith(".docx"):
            return None
        return self._convert_text_document(file, "ODT", output_reference=output_reference)

    def _convert_odt_to_docx(self, file: FileItem) -> str:
        if not file.path.lower().endswith(".odt"):
            return None
        return self._convert_text_document(file, "DOCX")

    def _convert_odt_to_pdf(self, file: FileItem) -> str:
        if not file.path.lower().endswith(".odt"):
            return None
        return self._convert_text_document(file, "PDF")

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
                    _debug_log(f"Не удалось удалить промежуточный DOCX: {error}")
        return None
