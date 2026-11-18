import os
import tempfile
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
    HAS_PIL as HAS_PIL,
)
from app.core.models import FileItem
from core.workers.common import record_file_error
from core.workers.office_engine import OFFICE_INPUTS, OFFICE_OUTPUTS, OfficeUnavailableError, run_office
from core.workers.pdfcraft_engine import PdfCraftUnavailableError

from .image_conversion_mixin import ImageConversionMixin
from .image_encoding_mixin import ImageEncodingMixin

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
            "docx_to_odt": self._convert_docx_to_odt,
            "odt_to_docx": self._convert_odt_to_docx,
            "odt_to_pdf": self._convert_odt_to_pdf,
            "pdf_to_odt": self._convert_pdf_to_odt,
            "pdf_to_image": self._convert_pdf_to_image,
            "pdf_to_images": self._convert_pdf_to_image,
            "image_to_pdf": self._convert_image_to_pdf,
            "image_to_image": lambda file: self._convert_image_to_image(file, self.conversion_format),
            "auto_image": lambda file: self._convert_image_auto(file, self.conversion_format),
            "auto_document": lambda file: self._convert_document_auto(file, self.conversion_format),
        }
        return handlers.get(self.conversion_type)

    def _convert_text_document(
        self, file: FileItem, target_format: str, *, output_reference: FileItem | None = None
    ) -> str:
        return self._convert_document_auto(file, target_format, output_reference=output_reference)

    def _convert_document_auto(
        self, file: FileItem, target_format: str, *, output_reference: FileItem | None = None
    ) -> str | list[str] | None:
        source_format = format_for_path(file.path)
        target = str(target_format or "").upper()
        if source_format not in source_formats_for_category(DOCUMENT_CATEGORY):
            raise ValueError("Файл не является поддерживаемым документом")
        if source_format == target and output_reference is None:
            signal = getattr(self, "status", None)
            if signal is not None:
                signal.emit(f"Пропущен {file.name}: уже {target}")
            return None
        if source_format == "PDF" and target in PDF_IMAGE_TARGETS:
            return self._convert_pdf_to_image(file, target)
        if source_format == "PDF" and target == "DOCX":
            return self._convert_pdf_to_docx(file)
        if target not in OFFICE_OUTPUTS:
            raise ValueError(f"Неподдерживаемый выходной формат: {target}")
        reference = output_reference or file
        output = self._conversion_output_path(file, suffix_for_format(target), reference_file=reference)
        try:
            with tempfile.TemporaryDirectory(prefix="multifora_document_") as directory:
                source = os.path.abspath(file.path)
                if source_format == "PDF":
                    from core.workers.pdfcraft_engine import export_pdf

                    if target == "TXT":
                        export_pdf(source, output, "TXT", self._should_cancel)
                        return output
                    intermediate = os.path.join(directory, "source.docx")
                    export_pdf(source, intermediate, "DOCX", self._should_cancel)
                    source = intermediate
                elif source_format not in OFFICE_INPUTS:
                    raise ValueError(f"Неподдерживаемый входной формат: {source_format}")

                def status(message):
                    signal = getattr(self, "status", None)
                    if signal is not None:
                        signal.emit(f"{reference.name}: {message}")

                warning = run_office(source, output, target, self._should_cancel, status=status)
                reporter = getattr(self, "_record_warning", None)
                if warning and callable(reporter):
                    reporter(reference, warning)
                return output
        finally:
            self._release_conversion_output_path(output)

    def _convert_files(self) -> None:
        total = len(self.files)
        results: list[FileItem] = []

        if self.conversion_type == "docx_to_pdf":
            self._emit_finished(self._convert_docx_to_pdf_batch(), [])
            return
        if self.conversion_type == "pdf_to_docx" or (
            self.conversion_type == "auto_document"
            and str(self.conversion_format).upper() == "DOCX"
            and self.files
            and all(not file.is_file or format_for_path(file.path) == "PDF" for file in self.files)
        ):
            self._emit_finished(self._convert_pdf_to_docx_batch(), [])
            return

        handler = self._get_conversion_handler()
        if self.conversion_type in {"auto_image", "image_to_image", "image_to_pdf"} and len(self.files) > 1:
            self._emit_finished(self._convert_image_batch(handler), [])
            return
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
                if isinstance(error, (OfficeUnavailableError, PdfCraftUnavailableError)):
                    self._report_unprocessed_engine_errors(self.files[index + 1 :], error)
                    self.progress.emit(100)
                    break

            self.progress.emit(int((index + 1) / total * 100))

        self._emit_finished(results, [])

    def _convert_image_batch(self, handler) -> list[FileItem]:
        """Обрабатывает не более двух изображений одновременно, ограничивая расход памяти."""
        files = [file for file in self.files if file.is_file]
        results = {}
        next_index = 0
        completed = 0
        with ThreadPoolExecutor(max_workers=2, thread_name_prefix="image-convert") as executor:
            pending = {}
            while pending or (next_index < len(files) and not self._should_cancel()):
                while len(pending) < 2 and next_index < len(files) and not self._should_cancel():
                    file = files[next_index]
                    pending[executor.submit(handler, file)] = (next_index, file)
                    next_index += 1
                if not pending:
                    break
                done, _ = wait(pending, timeout=0.2, return_when=FIRST_COMPLETED)
                for future in done:
                    index, file = pending.pop(future)
                    try:
                        output = future.result()
                        item = self._converted_file_item(output)
                        if item is not None:
                            results[index] = item
                    except Exception as error:
                        self._report_file_conversion_error(file, error)
                    completed += 1
                    self.status.emit(f"Конвертация: {file.name}")
                    self.progress.emit(int(completed / len(files) * 100))
        if self._should_cancel():
            self.status.emit("Операция отменена пользователем")
        return [results[index] for index in sorted(results)]

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
                if isinstance(error, (OfficeUnavailableError, PdfCraftUnavailableError)):
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
                        if isinstance(error, PdfCraftUnavailableError):
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
        from core.workers.pdfcraft_engine import PdfCraftUnavailableError, export_pdf

        docx_path = self._conversion_output_path(file, ".docx")
        try:
            export_pdf(file.path, docx_path, "DOCX", self._should_cancel)
            return docx_path
        except (InterruptedError, PdfCraftUnavailableError):
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
            return self._convert_document_auto(file, "ODT")
        return None
