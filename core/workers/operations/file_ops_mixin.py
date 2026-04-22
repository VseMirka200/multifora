import os
import shutil

from app.core.models import FileItem


class FileOpsMixin:
    def _copy_files(self):
        total = len(self.files)
        results = []

        for i, file in enumerate(self.files):
            if self._should_cancel():
                self.status.emit("Операция отменена пользователем")
                self.finished.emit({"new_files": results, "updated_files": [], "errors": self.errors})
                return

            dest_path = os.path.join(self.destination, file.name)
            dest_path = self._get_unique_path(dest_path)

            try:
                if file.is_file:
                    shutil.copy2(file.path, dest_path)
                else:
                    shutil.copytree(file.path, dest_path)
                results.append(FileItem(dest_path))
            except Exception as e:
                msg = f"Ошибка копирования {file.name}: {str(e)}"
                self._record_error(file, msg)
                self.error.emit(msg)

            self.progress.emit(int((i + 1) / total * 100))
            self.status.emit(f"Копирование: {file.name}")

        self.finished.emit({"new_files": results, "updated_files": [], "errors": self.errors})

    def _move_files(self):
        total = len(self.files)
        updated = []

        for i, file in enumerate(self.files):
            if self._should_cancel():
                self.status.emit("Операция отменена пользователем")
                self.finished.emit({"new_files": [], "updated_files": updated, "errors": self.errors})
                return

            dest_path = os.path.join(self.destination, file.name)
            dest_path = self._get_unique_path(dest_path)

            try:
                shutil.move(file.path, dest_path)
                updated.append((file, dest_path))
            except Exception as e:
                msg = f"Ошибка перемещения {file.name}: {str(e)}"
                self._record_error(file, msg)
                self.error.emit(msg)

            self.progress.emit(int((i + 1) / total * 100))
            self.status.emit(f"Перемещение: {file.name}")

        self.finished.emit({"new_files": [], "updated_files": updated, "errors": self.errors})

    def _rename_files(self):
        if len(self.files) != len(self.new_names):
            msg = "Ошибка переименования: несоответствие количества файлов и новых имен"
            self._record_error(None, msg)
            self.error.emit(msg)
            return

        total = len(self.files)
        updated = []

        for i, (file, new_name) in enumerate(zip(self.files, self.new_names)):
            if self._should_cancel():
                self.status.emit("Операция отменена пользователем")
                self.finished.emit({"new_files": [], "updated_files": updated, "errors": self.errors})
                return

            old_path = file.path
            new_path = os.path.join(file.folder, new_name)

            try:
                if os.path.exists(new_path) and old_path != new_path:
                    new_path = self._get_unique_path(new_path)

                os.rename(old_path, new_path)
                updated.append((file, new_path))
            except Exception as e:
                msg = f"Ошибка переименования {file.name}: {str(e)}"
                self._record_error(file, msg)
                self.error.emit(msg)

            self.progress.emit(int((i + 1) / total * 100))
            self.status.emit(f"Переименование: {file.name}")

        self.finished.emit({"new_files": [], "updated_files": updated, "errors": self.errors})

    def _get_unique_path(self, path: str) -> str:
        if not os.path.exists(path):
            return path

        base, ext = os.path.splitext(path)
        counter = 1
        while os.path.exists(path):
            path = f"{base}_{counter}{ext}"
            counter += 1
        return path
