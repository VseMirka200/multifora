import ctypes
import os
import sys

from app.core.app_utils import _debug_log, _get_app_data_dir

_ICON_SIZES = ((16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256))


def _application_base_dir():
    try:
        return os.path.dirname(os.path.abspath(sys.argv[0]))
    except Exception as error:
        _debug_log(f"Ошибка определения каталога приложения: {error}")
        return None


def _find_bundled_icon(filename: str):
    base_dirs = [
        getattr(sys, "_MEIPASS", None),
        _application_base_dir(),
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    ]
    for directory in ("assets", "icons"):
        for base_dir in base_dirs:
            if base_dir:
                icon_path = os.path.join(base_dir, directory, filename)
                if os.path.isfile(icon_path):
                    return icon_path
    return None


def _get_app_icon_path():
    """Возвращает путь к PNG-иконке приложения (если есть)."""
    return _find_bundled_icon("icon.png")


def _get_app_icon_ico_path():
    """Возвращает путь к ICO-иконке приложения (если есть)."""
    return _find_bundled_icon("icon.ico")


def _get_app_icon_qt_path():
    """Возвращает SVG для интерфейса, с резервными ICO и PNG."""
    return _find_bundled_icon("icon.svg") or _get_app_icon_ico_path() or _get_app_icon_path()


def _set_app_user_model_id():
    """Устанавливает AppUserModelID для корректной иконки в панели задач Windows."""
    if os.name != "nt":
        return
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("Multifora.App")
    except Exception as error:
        _debug_log(f"Ошибка установки AppUserModelID: {error}")


def _icon_needs_refresh(png_path: str, ico_path: str) -> bool:
    if not os.path.exists(ico_path):
        return True
    try:
        return os.path.getmtime(png_path) > os.path.getmtime(ico_path)
    except OSError as error:
        _debug_log(f"Ошибка сравнения дат изменения иконок: {error}")
        return False


def _get_shortcut_icon_path():
    """Гарантирует наличие ICO-иконки для ярлыков и возвращает ее путь."""
    try:
        bundled_ico_path = _get_app_icon_ico_path()
        if bundled_ico_path:
            return bundled_ico_path

        png_path = _get_app_icon_path()
        if not png_path:
            return None

        generated_ico_path = os.path.join(_get_app_data_dir(), "app_icon.ico")
        if not _icon_needs_refresh(png_path, generated_ico_path):
            return generated_ico_path
        try:
            from PIL import Image
        except ImportError:
            _debug_log("Pillow недоступен: не удалось создать ICO")
            return None

        try:
            with Image.open(png_path) as image:
                image.save(generated_ico_path, format="ICO", sizes=_ICON_SIZES)
        except Exception as error:
            _debug_log(f"Ошибка сохранения ICO: {error}")
            return None
        return generated_ico_path
    except Exception as error:
        _debug_log(f"Ошибка получения иконки для ярлыка: {error}")
        return None
