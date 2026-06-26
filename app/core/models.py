import os

from app.core.conversion_formats import FILE_TYPE_EXTENSIONS, format_for_path

class FileItem:
    """Класс для хранения информации о файле"""
    def __init__(self, path: str):
        self.path = path
        self.original_path = path  # Сохраняем оригинальный путь
        self.is_file = os.path.isfile(path)
        self.name = os.path.basename(path)
        self.folder = os.path.dirname(path)
        self.size = os.path.getsize(path) if self.is_file else 0
        self.preview_name = self.name
        self.is_selected = False
        self.file_type = self._detect_file_type()
        
    def _detect_file_type(self) -> str:
        """Определяет тип файла"""
        if not self.is_file:
            return "folder"
        
        ext = os.path.splitext(self.name)[1].lower()
        
        for file_type, extensions in FILE_TYPE_EXTENSIONS.items():
            if ext in extensions:
                return file_type
        return "other"
        
    def get_icon(self) -> str:
        """Возвращает иконку для типа файла"""
        if not self.is_file:
            return "📁"

        if self.file_type == "image":
            return "🖼️"
        if self.file_type == "video":
            return "🎞️"
        if self.file_type == "audio":
            return "🔊"
        if self.file_type == "archive":
            return "📦"
        if format_for_path(self.path) == "DOCX":
            return "📝"
        return "📄"
    
    def update_info(self):
        """Обновляет информацию о файле"""
        if os.path.exists(self.path):
            self.is_file = os.path.isfile(self.path)
            self.name = os.path.basename(self.path)
            self.folder = os.path.dirname(self.path)
            self.size = os.path.getsize(self.path) if self.is_file else 0
            self.file_type = self._detect_file_type()
            return True
        return False


