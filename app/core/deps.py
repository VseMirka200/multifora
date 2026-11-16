"""Ленивая проверка необязательных зависимостей приложения."""

from __future__ import annotations

import glob
import importlib.util
import os
import shutil
import sys
import threading

from app.core.app_utils import _debug_log

try:
    import winreg
except ImportError:
    winreg = None


HAS_ODF_PYTHON = importlib.util.find_spec("odf") is not None
HAS_PIL = importlib.util.find_spec("PIL") is not None
HAS_HEIF = HAS_PIL and importlib.util.find_spec("pillow_heif") is not None
HAS_GHOSTSCRIPT = False
GHOSTSCRIPT_PATH = None

_GHOSTSCRIPT_REGISTRY_PATHS = (
    r"SOFTWARE\\GPL Ghostscript",
    r"SOFTWARE\\AFPL Ghostscript",
    r"SOFTWARE\\Artifex Ghostscript",
    r"SOFTWARE\\WOW6432Node\\GPL Ghostscript",
    r"SOFTWARE\\WOW6432Node\\AFPL Ghostscript",
    r"SOFTWARE\\WOW6432Node\\Artifex Ghostscript",
)
_GHOSTSCRIPT_EXECUTABLES = ("gswin64c.exe", "gs.exe")


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
                    register_avif = getattr(
                        pillow_heif, "register_avif_opener", None
                    )
                    if callable(register_avif):
                        register_avif()
                except (ImportError, OSError) as error:
                    HAS_HEIF = False
                    _debug_log(f"Не удалось зарегистрировать HEIC/HEIF: {error}")
            _pillow_modules = (image_module, image_ops_module)
    return _pillow_modules


Image = _LazyModule(lambda: _load_pillow()[0])
ImageOps = _LazyModule(lambda: _load_pillow()[1])

_odf_modules = None
_odf_import_lock = threading.Lock()


def _load_odf():
    """Загружает odfpy только при конвертации ODT."""
    global HAS_ODF_PYTHON, _odf_modules
    if _odf_modules is not None:
        return _odf_modules
    with _odf_import_lock:
        if _odf_modules is None:
            try:
                from odf import teletype as teletype_module
                from odf import text as text_module
                from odf.opendocument import OpenDocumentText as document_type
                from odf.opendocument import load as load_document
            except ImportError:
                HAS_ODF_PYTHON = False
                raise
            _odf_modules = (
                teletype_module,
                text_module,
                document_type,
                load_document,
            )
    return _odf_modules


teletype = _LazyModule(lambda: _load_odf()[0])
text = _LazyModule(lambda: _load_odf()[1])


def OpenDocumentText(*args, **kwargs):
    return _load_odf()[2](*args, **kwargs)


def load(*args, **kwargs):
    return _load_odf()[3](*args, **kwargs)


def _registry_value(key, name: str) -> str | None:
    try:
        return winreg.QueryValueEx(key, name)[0]
    except OSError:
        return None


def _ghostscript_executable_from_registry_key(key) -> str | None:
    dll_path = _registry_value(key, "GS_DLL")
    if dll_path and os.path.exists(dll_path):
        executable = os.path.join(os.path.dirname(dll_path), "gswin64c.exe")
        if os.path.exists(executable):
            return executable

    library_path = _registry_value(key, "GS_LIB")
    if library_path and os.path.exists(library_path):
        executable = os.path.normpath(
            os.path.join(
                os.path.dirname(library_path), "..", "bin", "gswin64c.exe"
            )
        )
        if os.path.exists(executable):
            return executable
    return None


def _find_ghostscript_in_registry() -> str | None:
    """Ищет путь Ghostscript через реестр Windows."""
    if winreg is None:
        return None

    registry_roots = (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER)
    for root in registry_roots:
        for registry_path in _GHOSTSCRIPT_REGISTRY_PATHS:
            try:
                with winreg.OpenKey(root, registry_path) as key:
                    versions = []
                    index = 0
                    while True:
                        try:
                            versions.append(winreg.EnumKey(key, index))
                            index += 1
                        except OSError:
                            break

                    for version in sorted(versions, reverse=True):
                        try:
                            with winreg.OpenKey(key, version) as version_key:
                                executable = (
                                    _ghostscript_executable_from_registry_key(
                                        version_key
                                    )
                                )
                                if executable:
                                    return executable
                        except OSError:
                            continue
            except OSError:
                continue
    return None


def _ghostscript_candidates(custom_path: str | None = None) -> list[str]:
    candidates = []
    if custom_path:
        candidates.append(custom_path)

    environment_path = os.environ.get(
        "MULTIFORA_GHOSTSCRIPT_PATH"
    ) or os.environ.get("GHOSTSCRIPT_PATH")
    if environment_path:
        candidates.append(environment_path)

    executable = sys.argv[0] if sys.argv else ""
    base_dir = (
        os.path.dirname(os.path.abspath(executable)) if executable else None
    )

    if base_dir:
        candidates.append(
            os.path.join(base_dir, "bin", "gswin64", "gswin64c.exe")
        )

        # Версия из сборки имеет приоритет перед системной установкой.
        # Явный путь пользователя или переменная окружения по-прежнему важнее.
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    candidates.append(os.path.join(project_root, "bin", "gswin64", "gswin64c.exe"))
    registry_path = _find_ghostscript_in_registry()
    if registry_path:
        candidates.append(registry_path)

    candidates.append(r"C:\\Program Files\\gs\\gs*\\bin\\gswin64c.exe")
    candidates.extend(_GHOSTSCRIPT_EXECUTABLES)
    return candidates


def _resolve_executable_candidate(candidate: str) -> str | None:
    """Разрешает явный путь, glob-шаблон или имя команды из PATH."""
    if not candidate:
        return None

    paths = glob.glob(candidate) if "*" in candidate else [candidate]
    for path in paths:
        if os.path.isfile(path):
            return os.path.abspath(path)
        resolved_path = shutil.which(path)
        if resolved_path and os.path.isfile(resolved_path):
            return os.path.abspath(resolved_path)
    return None


def _detect_ghostscript(custom_path: str | None = None) -> None:
    """Определяет путь к Ghostscript."""
    global HAS_GHOSTSCRIPT, GHOSTSCRIPT_PATH

    HAS_GHOSTSCRIPT = False
    GHOSTSCRIPT_PATH = None

    for candidate in _ghostscript_candidates(custom_path):
        try:
            resolved_path = _resolve_executable_candidate(candidate)
        except OSError as error:
            _debug_log(
                f"Ошибка проверки пути Ghostscript {candidate!r}: {error}"
            )
            continue
        if not resolved_path:
            continue

        GHOSTSCRIPT_PATH = resolved_path
        HAS_GHOSTSCRIPT = True
        _debug_log(f"Ghostscript найден: {resolved_path}")
        return

    _debug_log("Ghostscript не найден")


def ensure_ghostscript_detected(
    custom_path: str | None = None,
) -> tuple[bool, str | None]:
    """Повторно определяет Ghostscript после возможного изменения пути или настроек."""
    if custom_path or not HAS_GHOSTSCRIPT or not GHOSTSCRIPT_PATH or not os.path.isfile(GHOSTSCRIPT_PATH):
        _detect_ghostscript(custom_path)
    return HAS_GHOSTSCRIPT, GHOSTSCRIPT_PATH


