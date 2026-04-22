import os

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
        
        if ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp', '.svg', '.ico']:
            return "image"
        elif ext in ['.doc', '.docx', '.pdf', '.txt', '.rtf', '.odt']:
            return "document"
        elif ext in ['.zip', '.rar', '.7z', '.tar', '.gz']:
            return "archive"
        else:
            return "other"
        
    def get_icon(self) -> str:
        """Возвращает иконку для типа файла"""
        if not self.is_file:
            return "📁"
        
        ext = os.path.splitext(self.name)[1].lower()
        icon_map = {
            # Документы
            '.doc': '📝', '.docx': '📝', '.pdf': '📄', '.txt': '📄', '.rtf': '📄',
            # Изображения
            '.jpg': '🖼️', '.jpeg': '🖼️', '.png': '🖼️', '.gif': '🖼️', '.bmp': '🖼️',
            '.tiff': '🖼️', '.webp': '🖼️', '.svg': '🖼️', '.ico': '🖼️',
            # Архивы
            '.zip': '📦', '.rar': '📦', '.7z': '📦', '.tar': '📦', '.gz': '📦',
        }
        return icon_map.get(ext, '📄')
    
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


