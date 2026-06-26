import os
import sys
import ctypes

from app.core.app_utils import _debug_log, _get_app_data_dir
from app.core.deps import HAS_PIL, Image

def _get_app_icon_path():
    """Возвращает путь к PNG-иконке приложения (если есть)."""
    try:
        base_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
        candidates = [
            os.path.join(base_dir, "icons", "icon.png"),
            os.path.join(base_dir, "materials", "icons", "icon.png"),
            os.path.join(base_dir, "materials", "icons", "Логотип.png"),
            os.path.join(base_dir, "materials", "icon", "icon.png"),
        ]
        for icon_path in candidates:
            if os.path.exists(icon_path):
                return icon_path
    except Exception as e:
        _debug_log(f"Ошибка получения пути к PNG-иконке приложения: {e}")
    return None

def _get_app_icon_ico_path():
    """Возвращает путь к ICO-иконке приложения (если есть)."""
    try:
        base_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
        candidates = [os.path.join(base_dir, "icons", "icon.ico")]
        for ico_path in candidates:
            if os.path.exists(ico_path):
                return ico_path
    except Exception as e:
        _debug_log(f"Ошибка получения пути к ICO-иконке приложения: {e}")
    return None

def _get_app_icon_qt_path():
    """Возвращает лучший путь иконки для QIcon (ICO предпочтительнее PNG)."""
    ico_path = _get_app_icon_ico_path()
    if ico_path:
        return ico_path
    return _get_app_icon_path()

def _set_app_user_model_id():
    """Устанавливает AppUserModelID для корректной иконки в панели задач Windows."""
    if os.name != 'nt':
        return
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("Multifora.App")
    except Exception as e:
        _debug_log(f"Ошибка установки AppUserModelID: {e}")

def _get_shortcut_icon_path():
    """Гарантирует наличие ICO-иконки для ярлыков и возвращает ее путь."""
    try:
        ico_path = _get_app_icon_ico_path()
        if ico_path:
            return ico_path

        png_path = _get_app_icon_path()
        if not png_path:
            return None

        ico_path = os.path.join(_get_app_data_dir(), "app_icon.ico")
        try:
            png_mtime = os.path.getmtime(png_path)
            ico_mtime = os.path.getmtime(ico_path) if os.path.exists(ico_path) else 0
        except Exception:
            png_mtime = 0
            ico_mtime = 0

        if not os.path.exists(ico_path) or png_mtime > ico_mtime:
            if HAS_PIL:
                try:
                    with Image.open(png_path) as img:
                        sizes = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
                        img.save(ico_path, format="ICO", sizes=sizes)
                except Exception as e:
                    _debug_log(f"Ошибка сохранения ICO: {e}")
                    return None
            else:
                _debug_log("Pillow недоступен: не удалось создать ICO")
                return None
        return ico_path
    except Exception as e:
        _debug_log(f"Ошибка получения иконки для ярлыка: {e}")
    return None

