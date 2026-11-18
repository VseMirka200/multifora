"""Resolve installed Windows TrueType families for searchable PDF output."""

import os
from functools import cache
from pathlib import Path
from threading import Lock

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFError, TTFont

_LOCK = Lock()
_VARIANTS = {"normal": "", "bold": " bold", "italic": " italic", "boldItalic": " bold italic"}
_ALIASES = {"sans-serif": "Arial", "serif": "Times New Roman", "monospace": "Consolas"}


@cache
def _system_fonts():
    if os.name != "nt":
        return {}
    import winreg

    fonts = {}
    system_folder = Path(os.environ.get("WINDIR", r"C:\Windows"), "Fonts")
    for hive in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
        try:
            with winreg.OpenKey(hive, r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts") as key:
                for index in range(winreg.QueryInfoKey(key)[1]):
                    name, filename, _ = winreg.EnumValue(key, index)
                    if isinstance(filename, str) and filename.lower().endswith((".ttf", ".ttc")):
                        path = system_folder / os.path.expandvars(filename)
                        names = name.split(" (", 1)[0]
                        for index_in_file, face in enumerate(names.split(" & ") if path.suffix.lower() == ".ttc"
                                                            else (names,)):
                            fonts[face.casefold()] = path, index_in_file
        except OSError:
            continue
    return fonts


@cache
def pdf_font_family(family):
    family = _ALIASES.get(family.casefold(), family).casefold()
    files = _system_fonts()
    if family not in files:
        return None
    with _LOCK:
        variants = {}
        for style, suffix in _VARIANTS.items():
            face = files.get(family + suffix)
            name = f"MultiforaFont-{family}-{style}"
            if face is not None:
                path, index_in_file = face
                try:
                    pdfmetrics.registerFont(TTFont(name, path, subfontIndex=index_in_file))
                    variants[style] = name
                    continue
                except (OSError, TTFError):
                    pass
            if style == "normal":
                return None
            variants[style] = variants["normal"]
        name = variants.pop("normal")
        pdfmetrics.registerFontFamily(name, normal=name, **variants)
        return name
