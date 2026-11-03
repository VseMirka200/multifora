"""Ленивая проверка необязательных зависимостей приложения."""

from __future__ import annotations

import glob
import importlib.util
import os
import shutil
import sys
import threading

from app.core.app_utils import _debug_log
from app.core.pdf_compat import import_pymupdf_with_legacy_alias

try:
    import winreg
except ImportError:
    winreg = None


fitz = None

HAS_PANDOC = False
PANDOC_PATH = None
HAS_PYMUPDF = importlib.util.find_spec("pymupdf") is not None
HAS_PDF_TO_DOCX = (
    HAS_PYMUPDF and importlib.util.find_spec("pdf2docx") is not None
)
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


_pdf2docx_module = None
_pdf2docx_import_lock = threading.Lock()


def _load_pdf2docx():
    """Load the heavy PDF converter only inside the conversion worker."""
    global fitz, _pdf2docx_module
    if _pdf2docx_module is not None:
        return _pdf2docx_module
    with _pdf2docx_import_lock:
        if _pdf2docx_module is None:
            fitz = import_pymupdf_with_legacy_alias()
            import pdf2docx as module

            _pdf2docx_module = module
    return _pdf2docx_module


class _LazyModule:
    def __init__(self, loader):
        self._loader = loader

    def __getattr__(self, name):
        return getattr(self._loader(), name)


pdf2docx = _LazyModule(_load_pdf2docx)

_pillow_modules = None
_pillow_import_lock = threading.Lock()


def _load_pillow():
    """Load Pillow and register optional formats on the first image operation."""
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
    """Load odfpy only when an ODT conversion is requested."""
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

    # The packaged copy is deterministic and must win over an unrelated
    # machine-wide Ghostscript installation. Explicit custom/env overrides
    # above remain available for users who intentionally select another build.
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
    if custom_path or not HAS_GHOSTSCRIPT or not GHOSTSCRIPT_PATH:
        _detect_ghostscript(custom_path)
    return HAS_GHOSTSCRIPT, GHOSTSCRIPT_PATH


def _pandoc_candidates(custom_path: str | None = None) -> list[str]:
    candidates = []
    if custom_path:
        candidates.append(custom_path)
    environment_path = os.environ.get("MULTIFORA_PANDOC_PATH")
    if environment_path:
        candidates.append(environment_path)

    executable = sys.argv[0] if sys.argv else ""
    if executable:
        base_dir = os.path.dirname(os.path.abspath(executable))
        candidates.append(os.path.join(base_dir, "bin", "pandoc", "pandoc.exe"))
        candidates.append(os.path.join(base_dir, "bin", "pandoc.exe"))
    candidates.extend(("pandoc.exe", "pandoc"))
    return candidates


def _detect_pandoc(custom_path: str | None = None) -> None:
    """Определяет путь к CLI Pandoc без запуска внешнего процесса."""
    global HAS_PANDOC, PANDOC_PATH
    HAS_PANDOC = False
    PANDOC_PATH = None
    for candidate in _pandoc_candidates(custom_path):
        try:
            resolved_path = _resolve_executable_candidate(candidate)
        except OSError as error:
            _debug_log(f"Ошибка проверки пути Pandoc {candidate!r}: {error}")
            continue
        if resolved_path:
            HAS_PANDOC = True
            PANDOC_PATH = resolved_path
            _debug_log(f"Pandoc найден: {resolved_path}")
            return
    _debug_log("Pandoc не найден")


def ensure_pandoc_detected(
    custom_path: str | None = None,
) -> tuple[bool, str | None]:
    if custom_path or not HAS_PANDOC or not PANDOC_PATH:
        _detect_pandoc(custom_path)
    return HAS_PANDOC, PANDOC_PATH


_detect_pandoc()
