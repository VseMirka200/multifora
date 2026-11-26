"""Conversion worker routing to the native ArtCraft engines."""
from __future__ import annotations

import os
import threading
from collections.abc import Callable

from app.core.app_utils import _debug_log
from app.core.conversion_formats import suffix_for_format
from app.core.models import FileItem
from app.core import native_engines
from core.workers.common import record_file_error

_CONVERSION_OUTPUT_PATH_LOCK = threading.Lock()


class ConversionMixin:
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
        base_path = os.path.join(self._conversion_output_directory(reference), f"{stem}{target_ext}")
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
        if not path:
            return
        try:
            if os.path.exists(path):
                os.remove(path)
        except OSError as error:
            _debug_log(f"Не удалось удалить частичный результат {path}: {error}")
        finally:
            self._release_conversion_output_path(path)

    def _report_file_conversion_error(self, file: FileItem, error: Exception) -> None:
        record_file_error(self, file, f"Ошибка конвертации файла {file.name}: {error}")

    @staticmethod
    def _converted_file_item(path: str | None) -> FileItem | None:
        return FileItem(path) if path and os.path.isfile(path) else None

    def _get_conversion_handler(self) -> Callable[[FileItem], str | list[str] | None]:
        target_format = self.conversion_format
        target_ext = suffix_for_format(target_format)
        if not target_ext:
            raise ValueError(f"Формат {target_format!r} не поддерживается движками ArtCraft")

        def convert(file: FileItem) -> str | list[str] | None:
            output_path = self._conversion_output_path(file, target_ext)
            try:
                return native_engines.convert_file(self, file, target_format, output_path)
            except Exception:
                self._discard_conversion_output(output_path)
                raise

        return convert

    def _convert_files(self) -> None:
        total = len(self.files)
        results: list[FileItem] = []
        if not total:
            self._emit_finished(results, [])
            return
        try:
            handler = self._get_conversion_handler()
        except Exception as error:
            record_file_error(self, None, str(error))
            self._emit_finished(results, [])
            return

        for index, file in enumerate(self.files):
            if self._should_cancel():
                self.status.emit("Операция отменена пользователем")
                break
            if not getattr(file, "is_file", False):
                continue
            self.status.emit(f"Конвертация ({self.conversion_format}): {file.name}")
            try:
                output = handler(file)
                for path in output if isinstance(output, list) else [output]:
                    converted = self._converted_file_item(path)
                    if converted is not None:
                        results.append(converted)
            except InterruptedError:
                self.status.emit("Операция отменена пользователем")
                break
            except Exception as error:
                self._report_file_conversion_error(file, error)
            self.progress.emit(int((index + 1) / total * 100))
        self._emit_finished(results, [])
