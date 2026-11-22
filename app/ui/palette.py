"""Four base colours per theme and the interaction states derived from them."""

from functools import lru_cache
from types import MappingProxyType


def _mix(first, second, weight):
    channels = (
        round(int(first[i:i + 2], 16) * (1 - weight) + int(second[i:i + 2], 16) * weight)
        for i in (1, 3, 5)
    )
    return "#" + "".join(f"{channel:02x}" for channel in channels)


@lru_cache(maxsize=2)
def standard_palette(theme):
    light = str(theme).lower() == "light"
    if light:
        base, text, accent, danger = "#ffffff", "#20242b", "#245fb8", "#a52b38"
    else:
        base, text, accent, danger = "#202125", "#f0f2f5", "#8bb7ff", "#ff9ba5"

    surface = base if light else _mix(base, text, 0.05)
    window = _mix(base, text, 0.04) if light else base
    muted = _mix(surface, text, 0.70)
    border = _mix(surface, text, 0.28)
    return MappingProxyType({
        "window_bg": window, "bg": surface, "fg": text,
        "accent": accent, "on_accent": base, "danger": danger,
        "accent_hover": _mix(accent, text, 0.18),
        "danger_hover": _mix(danger, text, 0.15),
        "danger_pressed": _mix(danger, text, 0.30),
        "border": border, "disabled_border": border, "separator": border,
        "hover_border": _mix(surface, text, 0.50),
        "command_hover": _mix(surface, accent, 0.30),
        "inactive_accent": _mix(surface, accent, 0.09),
        "progress": _mix(surface, accent, 0.45),
        "hover_bg": _mix(surface, accent, 0.18),
        "disabled_bg": window, "disabled_fg": muted, "placeholder": muted,
    })
