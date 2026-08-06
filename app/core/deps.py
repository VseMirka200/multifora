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
word_to_pdf = None
pdf2docx = None
convert_from_path = None
text = None
teletype = None
load = None
OpenDocumentText = None
get_ffmpeg_exe = None

HAS_WORD_TO_PDF = False
HAS_PDF_TO_WORD = False
HAS_PDF_TO_IMAGE = False
HAS_FFMPEG = False
HAS_PYMUPDF = False
HAS_ODF_PYTHON = False
HAS_PIL = False
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
    import fitz

    HAS_PYMUPDF = True
    _debug_log("PyMuPDF найден")
except ImportError:
    _debug_log("PyMuPDF не найден. Установите: pip install PyMuPDF")

try:
    from PIL import Image, ImageOps

    HAS_PIL = True
    _debug_log("Pillow найден")
except ImportError:
    _debug_log("Pillow не найден. Установите: pip install Pillow")


def _registry_value(key, name: str):
    try:
        return winreg.QueryValueEx(key, name)[0]
    except OSError:
        return None


def _ghostscript_executable_from_registry_key(key):
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


def _find_ghostscript_in_registry():
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


def _ghostscript_candidates(custom_path=None):
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

    try:
        base_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
    except Exception as error:
        _debug_log(f"Ошибка определения каталога приложения для Ghostscript: {error}")
        base_dir = None

    if base_dir:
        candidates.append(os.path.join(base_dir, "bin", "gswin64", "gswin64c.exe"))

    candidates.append(r"C:\\Program Files\\gs\\gs*\\bin\\gswin64c.exe")
    candidates.extend(_GHOSTSCRIPT_EXECUTABLES)
    return candidates


def _resolve_ghostscript_candidate(candidate):
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


def _detect_ghostscript(custom_path=None):
    """Определяет путь к Ghostscript."""
    global HAS_GHOSTSCRIPT, GHOSTSCRIPT_PATH

    HAS_GHOSTSCRIPT = False
    GHOSTSCRIPT_PATH = None

    for candidate in _ghostscript_candidates(custom_path):
        try:
            resolved_path = _resolve_ghostscript_candidate(candidate)
        except Exception as error:
            _debug_log(f"Ошибка проверки пути Ghostscript {candidate!r}: {error}")
            continue
        if not resolved_path:
            continue

        GHOSTSCRIPT_PATH = resolved_path
        HAS_GHOSTSCRIPT = True
        _debug_log(f"Ghostscript найден: {resolved_path}")
        return

    _debug_log("Ghostscript не найден")


def ensure_ghostscript_detected(custom_path=None):
    """Refresh Ghostscript detection when path/config may have changed."""
    if custom_path or not HAS_GHOSTSCRIPT or not GHOSTSCRIPT_PATH:
        _detect_ghostscript(custom_path)
    return HAS_GHOSTSCRIPT, GHOSTSCRIPT_PATH


try:
    from docx2pdf import convert as word_to_pdf

    HAS_WORD_TO_PDF = True
except ImportError:
    _debug_log("docx2pdf не найден")

try:
    import pdf2docx

    HAS_PDF_TO_WORD = True
except ImportError:
    _debug_log("pdf2docx не найден")

try:
    from pdf2image import convert_from_path

    HAS_PDF_TO_IMAGE = True
except ImportError:
    _debug_log("pdf2image не найден")

try:
    from odf import text, teletype
    from odf.opendocument import OpenDocumentText, load

    HAS_ODF_PYTHON = True
except ImportError:
    _debug_log("python-odf не найден")

try:
    from imageio_ffmpeg import get_ffmpeg_exe

    HAS_FFMPEG = True
    _debug_log("imageio-ffmpeg найден")
except ImportError:
    _debug_log("imageio-ffmpeg не найден. Установите: pip install imageio-ffmpeg")
