"""Общие цветные иконки по типу исходного файла."""

from functools import lru_cache
import os

from PyQt6.QtGui import QIcon

from app.core.app_icons import _find_bundled_icon
from app.core.conversion_formats import FILE_TYPE_EXTENSIONS

FILE_ICON_SIZE = 28

_CATEGORY_EXTENSIONS = {
    "document": "docm dot dotx dotm txt md markdown log csv tsv json xml yaml yml ini cfg conf toml sql py pyw js jsx ts tsx css scss html htm bat cmd ps1 sh c h cpp hpp cs java go rs rb php tex rst rtf",
    "image": "",
    "spreadsheet": "xls xlsx xlsm xlsb xlt xltx ods",
    "presentation": "ppt pptx pptm pps ppsx pot potx odp",
    "audio": "mp3 wav flac aac m4a ogg opus wma aiff aif mid midi",
    "video": "mp4 mkv avi mov webm wmv m4v mpg mpeg flv 3gp",
    "archive": "bz2 xz tgz zst cab iso",
}
_EXTENSION_CATEGORIES = {
    extension: category
    for category, extra in _CATEGORY_EXTENSIONS.items()
    for extension in (set(FILE_TYPE_EXTENSIONS.get(category, ()))
                      | {"." + ext for ext in extra.split()})
}


@lru_cache(maxsize=9)
def _category_icon(category: str) -> QIcon:
    if category == "folder":
        return QIcon(_find_bundled_icon("folder.svg") or "")
    return QIcon(_find_bundled_icon(f"file_types/{category}.svg") or "")


def file_icon(file_item) -> QIcon:
    if not file_item.is_file:
        return _category_icon("folder")
    extension = os.path.splitext(file_item.path)[1].lower()
    return _category_icon(_EXTENSION_CATEGORIES.get(extension, "unknown"))
