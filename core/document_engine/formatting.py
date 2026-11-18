"""Read the dimensions and typography shared by the document converters."""

import re
from math import isfinite

_LENGTH = re.compile(r"([0-9]+(?:\.[0-9]*)?|\.[0-9]+)(pt|px|in|cm|mm|pc)?", re.I)
_POINTS = {None: .75, "px": .75, "pt": 1, "in": 72, "cm": 72 / 2.54, "mm": 72 / 25.4, "pc": 12}


def points(value):
    match = _LENGTH.fullmatch((value or "").strip())
    if match:
        length = float(match[1]) * _POINTS[match[2].lower() if match[2] else None]
        if length > 0 and isfinite(length):
            return length
    return None


def inline_style(node):
    return {
        key.strip().lower(): value.strip()
        for declaration in node.get("style", "").split(";")
        for key, separator, value in (declaration.partition(":"),)
        if separator
    }


def font_family(value):
    return (value or "").split(",", 1)[0].strip().strip("'\"")


def _image_length(value, limit):
    value = (value or "").strip()
    if limit and value.endswith("%"):
        fraction = points(value[:-1] + "pt")
        if fraction:
            return limit * (fraction / 100)
    return points(value)


def image_size(node, pixel_width, pixel_height, *, width_limit=None, height_limit=None):
    style = inline_style(node)
    width = _image_length(style.get("width", node.get("width")), width_limit)
    height = _image_length(style.get("height", node.get("height")), height_limit)
    if width is None and height is None:
        width, height = .75 * pixel_width, .75 * pixel_height
    elif width is None:
        width = height * pixel_width / pixel_height
    elif height is None:
        height = width * pixel_height / pixel_width
    max_width = _image_length(style.get("max-width"), width_limit)
    max_height = _image_length(style.get("max-height"), height_limit)
    width_scale = min((limit / width for limit in (width_limit, max_width) if limit), default=1)
    height_scale = min((limit / height for limit in (height_limit, max_height) if limit), default=1)
    scale = min(1, width_scale, height_scale)
    return width * scale, height * scale
