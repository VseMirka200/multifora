"""Ленивая проверка необязательных зависимостей приложения."""

from __future__ import annotations

import glob
import os
import shutil
import sys

from app.core.app_utils import _debug_log

try:
    import winreg
except ImportError:
    winreg = None


fitz = None
Image = None
ImageOps = None
pdf2docx = None
text = None
teletype = None
load = None
OpenDocumentText = None

HAS_WORD_TO_PDF = False
HAS_PDF_TO_WORD = False
HAS_PYMUPDF = False
HAS_ODF_PYTHON = False
HAS_PIL = False
HAS_HEIF = False
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


try:
    import pymupdf as fitz

    HAS_PYMUPDF = True
    _debug_log("PyMuPDF найден")
except ImportError:
    _debug_log("PyMuPDF не найден. Установите: pip install PyMuPDF")

try:
    from PIL import Image, ImageOps

    HAS_PIL = True
    _debug_log("Pillow найден")
    try:
        import pillow_heif

        pillow_heif.register_heif_opener()
        register_avif = getattr(pillow_heif, "register_avif_opener", None)
        if callable(register_avif):
            register_avif()
        HAS_HEIF = True
        _debug_log("pillow-heif найден")
    except ImportError:
        _debug_log("pillow-heif не найден: HEIC/HEIF будут недоступны")
    except Exception as error:
        _debug_log(f"Не удалось зарегистрировать HEIC/HEIF: {error}")
except ImportError:
    _debug_log("Pillow не найден. Установите: pip install Pillow")


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
            os.path.join(os.path.dirname(library_path), "..", "bin", "gswin64c.exe")
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
                                executable = _ghostscript_executable_from_registry_key(version_key)
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

    environment_path = os.environ.get("MULTIFORA_GHOSTSCRIPT_PATH") or os.environ.get(
        "GHOSTSCRIPT_PATH"
    )
    if environment_path:
        candidates.append(environment_path)

    registry_path = _find_ghostscript_in_registry()
    if registry_path:
        candidates.append(registry_path)

    executable = sys.argv[0] if sys.argv else ""
    base_dir = os.path.dirname(os.path.abspath(executable)) if executable else None

    if base_dir:
        candidates.append(os.path.join(base_dir, "bin", "gswin64", "gswin64c.exe"))

    candidates.append(r"C:\\Program Files\\gs\\gs*\\bin\\gswin64c.exe")
    candidates.extend(_GHOSTSCRIPT_EXECUTABLES)
    return candidates


def _resolve_ghostscript_candidate(candidate: str) -> str | None:
    if not candidate:
        return None

    paths = glob.glob(candidate) if "*" in candidate else [candidate]
    for path in paths:
        if os.path.exists(path):
            return path
        resolved_path = shutil.which(path)
        if resolved_path and os.path.exists(resolved_path):
            return resolved_path
    return None


def _detect_ghostscript(custom_path: str | None = None) -> None:
    """Определяет путь к Ghostscript."""
    global HAS_GHOSTSCRIPT, GHOSTSCRIPT_PATH

    HAS_GHOSTSCRIPT = False
    GHOSTSCRIPT_PATH = None

    for candidate in _ghostscript_candidates(custom_path):
        try:
            resolved_path = _resolve_ghostscript_candidate(candidate)
        except OSError as error:
            _debug_log(f"Ошибка проверки пути Ghostscript {candidate!r}: {error}")
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
    if custom_path or not HAS_GHOSTSCRIPT or not GHOSTSCRIPT_PATH:
        _detect_ghostscript(custom_path)
    return HAS_GHOSTSCRIPT, GHOSTSCRIPT_PATH


try:
    import pythoncom  # noqa: F401
    import win32com.client  # noqa: F401

    HAS_WORD_TO_PDF = True
except ImportError:
    _debug_log("pywin32 не найден: конвертация Word в PDF недоступна")

try:
    import pdf2docx

    HAS_PDF_TO_WORD = True
except ImportError:
    _debug_log("pdf2docx не найден")

try:
    from odf import text, teletype
    from odf.opendocument import OpenDocumentText, load

    HAS_ODF_PYTHON = True
except ImportError:
    _debug_log("python-odf не найден")

