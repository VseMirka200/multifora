"""Ленивая проверка необязательных зависимостей приложения."""

from __future__ import annotations

import importlib.util
import threading

from app.core.app_utils import _debug_log

HAS_PIL = importlib.util.find_spec("PIL") is not None
HAS_HEIF = HAS_PIL and importlib.util.find_spec("pillow_heif") is not None
class _LazyModule:
    def __init__(self, loader):
        self._loader = loader

    def __getattr__(self, name):
        return getattr(self._loader(), name)


_pillow_modules = None
_pillow_import_lock = threading.Lock()


def _load_pillow():
    """Загружает Pillow и регистрирует форматы при первой обработке изображения."""
    global HAS_HEIF, HAS_PIL, _pillow_modules
    if _pillow_modules is not None:
        return _pillow_modules
    with _pillow_import_lock:
        if _pillow_modules is None:
            try:
                from PIL import Image as image_module
                from PIL import ImageOps as image_ops_module
            except ImportError:
                HAS_PIL = False
                raise

            if HAS_HEIF:
                try:
                    import pillow_heif

                    pillow_heif.register_heif_opener()
                    register_avif = getattr(pillow_heif, "register_avif_opener", None)
                    if callable(register_avif):
                        register_avif()
                except (ImportError, OSError) as error:
                    HAS_HEIF = False
                    _debug_log(f"Не удалось зарегистрировать HEIC/HEIF: {error}")
            _pillow_modules = (image_module, image_ops_module)
    return _pillow_modules


Image = _LazyModule(lambda: _load_pillow()[0])
ImageOps = _LazyModule(lambda: _load_pillow()[1])


