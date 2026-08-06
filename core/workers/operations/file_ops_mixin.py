import os
import shutil

from app.core.models import FileItem
from core.workers.common import emit_progress, finish_if_cancelled, get_unique_path, record_file_error


class FileOpsMixin:
    def _copy_files(self):
        self._transfer_files(move=False)

    def _move_files(self):
        self._transfer_files(move=True)

    def _transfer_files(self, *, move: bool) -> None:
        total = len(self.files)
        new_files = []
        updated_files = []
        action_name = "Перемещение" if move else "Копирование"
        error_action = "перемещения" if move else "копирования"

        for index, file_item in enumerate(self.files):
            if finish_if_cancelled(self, new_files, updated_files):
                return

            destination_path = self._get_unique_path(
                os.path.join(self.destination, file_item.name)
            )
            try:
                if move:
                    shutil.move(file_item.path, destination_path)
                    updated_files.append((file_item, destination_path))
                else:
                    if file_item.is_file:
                        shutil.copy2(file_item.path, destination_path)
                    else:
                        shutil.copytree(file_item.path, destination_path)
                    new_files.append(FileItem(destination_path))
            except Exception as error:
                message = f"Ошибка {error_action} {file_item.name}: {error}"
                record_file_error(self, file_item, message)

            emit_progress(self, index, total)
            self.status.emit(f"{action_name}: {file_item.name}")

        self._emit_finished(new_files, updated_files)

    def _rename_files(self):
        if len(self.files) != len(self.new_names):
            message = "Ошибка переименования: несоответствие количества файлов и новых имен"
            record_file_error(self, None, message)
            return

        total = len(self.files)
        updated_files = []

        for index, (file_item, new_name) in enumerate(zip(self.files, self.new_names)):
            if finish_if_cancelled(self, [], updated_files):
                return

            old_path = file_item.path
            new_path = os.path.join(file_item.folder, new_name)

            try:
                if os.path.exists(new_path) and old_path != new_path:
                    new_path = self._get_unique_path(new_path)
                os.rename(old_path, new_path)
                updated_files.append((file_item, new_path))
            except Exception as error:
                message = f"Ошибка переименования {file_item.name}: {error}"
                record_file_error(self, file_item, message)

            emit_progress(self, index, total)
            self.status.emit(f"Переименование: {file_item.name}")

        self._emit_finished([], updated_files)

    def _get_unique_path(self, path: str) -> str:
        return get_unique_path(path)
