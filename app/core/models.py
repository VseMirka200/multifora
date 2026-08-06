import os

from app.core.conversion_formats import FILE_TYPE_EXTENSIONS, format_for_path


_FILE_TYPE_ICONS = {
    "image": "🖼️",
    "video": "🎞️",
    "audio": "🔊",
    "archive": "📦",
}


class FileItem:
    """Класс для хранения информации о файле"""

    def __init__(self, path: str):
        self.path = path
        self.original_path = path
        self.preview_name = os.path.basename(path)
        self.is_selected = False
        self._refresh_path_metadata()

    def _refresh_path_metadata(self) -> None:
        self.is_file = os.path.isfile(self.path)
        self.name = os.path.basename(self.path)
        self.folder = os.path.dirname(self.path)
        self.size = os.path.getsize(self.path) if self.is_file else 0
        self.file_type = self._detect_file_type()

    def _detect_file_type(self) -> str:
        """Определяет тип файла"""
        if not self.is_file:
            return "folder"

        extension = os.path.splitext(self.name)[1].lower()
        for file_type, extensions in FILE_TYPE_EXTENSIONS.items():
            if extension in extensions:
                return file_type
        return "other"

    def get_icon(self) -> str:
        """Возвращает иконку для типа файла"""
        if not self.is_file:
            return "📁"
        if self.file_type in _FILE_TYPE_ICONS:
            return _FILE_TYPE_ICONS[self.file_type]
        if format_for_path(self.path) == "DOCX":
            return "📝"
        return "📄"

    def update_info(self):
        """Обновляет информацию о файле"""
        if not os.path.exists(self.path):
            return False
        self._refresh_path_metadata()
        return True
