import os
import sys
import shutil
import winreg

from app.core.app_utils import _debug_log

# Optional dependency placeholders
fitz = None
Image = None
ImageOps = None
word_to_pdf = None
pdf2docx = None
convert_from_path = None
pd = None
text = None
teletype = None
load = None
OpenDocumentText = None
get_ffmpeg_exe = None

HAS_WORD_TO_PDF = False
HAS_PDF_TO_WORD = False
HAS_PDF_TO_IMAGE = False
HAS_FFMPEG = False
HAS_PANDAS = False
HAS_PYMUPDF = False
HAS_ODF_PYTHON = False
HAS_PIL = False

# Проверяем наличие GhostPCL и Ghostscript
HAS_GHOSTPCL = False
HAS_GHOSTSCRIPT = False
GHOSTPCL_PATH = None
GHOSTSCRIPT_PATH = None

# Проверяем наличие PyMuPDF
try:
    import fitz
    HAS_PYMUPDF = True
    _debug_log("PyMuPDF найден")
except ImportError:
    _debug_log("PyMuPDF не найден. Установите: pip install PyMuPDF")

# Проверяем наличие Pillow
try:
    from PIL import Image, ImageOps
    HAS_PIL = True
    _debug_log("Pillow найден")
except ImportError:
    _debug_log("Pillow не найден. Установите: pip install Pillow")

# Проверяем наличие Ghostscript (ваш путь gs10.06.0)
def _find_ghostscript_in_registry():
    """Ищет путь Ghostscript через реестр Windows."""
    reg_roots = [winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER]
    reg_paths = [
        r"SOFTWARE\\GPL Ghostscript",
        r"SOFTWARE\\AFPL Ghostscript",
        r"SOFTWARE\\Artifex Ghostscript",
        r"SOFTWARE\\WOW6432Node\\GPL Ghostscript",
        r"SOFTWARE\\WOW6432Node\\AFPL Ghostscript",
        r"SOFTWARE\\WOW6432Node\\Artifex Ghostscript",
    ]
    for root in reg_roots:
        for reg_path in reg_paths:
            try:
                with winreg.OpenKey(root, reg_path) as key:
                    versions = []
                    i = 0
                    while True:
                        try:
                            versions.append(winreg.EnumKey(key, i))
                            i += 1
                        except OSError:
                            break
                    for version in sorted(versions, reverse=True):
                        try:
                            with winreg.OpenKey(key, version) as vkey:
                                dll_path = None
                                try:
                                    dll_path = winreg.QueryValueEx(vkey, "GS_DLL")[0]
                                except OSError:
                                    dll_path = None
                                if dll_path and os.path.exists(dll_path):
                                    bin_dir = os.path.dirname(dll_path)
                                    cand = os.path.join(bin_dir, "gswin64c.exe")
                                    if os.path.exists(cand):
                                        return cand
                                    cand = os.path.join(bin_dir, "gswin32c.exe")
                                    if os.path.exists(cand):
                                        return cand
                                try:
                                    gs_lib = winreg.QueryValueEx(vkey, "GS_LIB")[0]
                                except OSError:
                                    gs_lib = None
                                if gs_lib and os.path.exists(gs_lib):
                                    base_dir = os.path.dirname(gs_lib)
                                    bin_dir = os.path.join(base_dir, "..", "bin")
                                    cand = os.path.join(bin_dir, "gswin64c.exe")
                                    if os.path.exists(cand):
                                        return cand
                                    cand = os.path.join(bin_dir, "gswin32c.exe")
                                    if os.path.exists(cand):
                                        return cand
                        except OSError:
                            continue
            except OSError:
                continue
    return None

def _detect_ghostscript(custom_path=None):
    """Определяет путь к Ghostscript."""
    global HAS_GHOSTSCRIPT, GHOSTSCRIPT_PATH

    HAS_GHOSTSCRIPT = False
    GHOSTSCRIPT_PATH = None

    candidates = []
    if custom_path:
        candidates.append(custom_path)

    env_path = os.environ.get("MULTIFORA_GHOSTSCRIPT_PATH") or os.environ.get("GHOSTSCRIPT_PATH")
    if env_path:
        candidates.append(env_path)

    reg_path = _find_ghostscript_in_registry()
    if reg_path:
        candidates.append(reg_path)

    try:
        base_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
    except Exception:
        base_dir = None

    if base_dir:
        candidates.extend([
            os.path.join(base_dir, "bin", "gswin64", "gswin64c.exe"),
            os.path.join(base_dir, "bin", "gswin32", "gswin32c.exe"),
        ])

    candidates.extend([
        r"C:\\Program Files\\gs\\gs*\\bin\\gswin64c.exe",
        r"C:\\Program Files (x86)\\gs\\gs*\\bin\\gswin32c.exe",
        "gswin64c.exe",
        "gswin32c.exe",
        "gs.exe",
    ])

    for path in candidates:
        try:
            if not path:
                continue
            if "*" in path:
                import glob
                matches = glob.glob(path)
                if matches:
                    path = matches[0]
                else:
                    continue
            if os.path.exists(path):
                GHOSTSCRIPT_PATH = path
                HAS_GHOSTSCRIPT = True
                _debug_log(f"Ghostscript найден: {path}")
                return
            which_path = shutil.which(path)
            if which_path and os.path.exists(which_path):
                GHOSTSCRIPT_PATH = which_path
                HAS_GHOSTSCRIPT = True
                _debug_log(f"Ghostscript найден в PATH: {which_path}")
                return
        except Exception:
            continue

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
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    _debug_log("pandas не найден")

try:
    from odf import text, teletype
    from odf.opendocument import load, OpenDocumentText
    HAS_ODF_PYTHON = True
except ImportError:
    _debug_log("python-odf не найден")

try:
    from imageio_ffmpeg import get_ffmpeg_exe
    HAS_FFMPEG = True
    _debug_log("imageio-ffmpeg найден")
except ImportError:
    _debug_log("imageio-ffmpeg не найден. Установите: pip install imageio-ffmpeg")



