"""Подключение CLI-движков ArtCraft к пакетным операциям Multifora.

Пути можно задать переменными окружения:
MULTIFORA_PDFCRAFT_CLI, MULTIFORA_WORDCRAFT_CLI, MULTIFORA_PHOTOCRAFT_CLI.
В сборке также проверяется каталог bin/artcraft рядом с приложением.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from collections.abc import Sequence


_TOOL_ENV = {
    "pdfcraft": "MULTIFORA_PDFCRAFT_CLI",
    "wordcraft": "MULTIFORA_WORDCRAFT_CLI",
    "photocraft": "MULTIFORA_PHOTOCRAFT_CLI",
}
_TOOL_NAMES = {
    "pdfcraft": ("pdfcraft-cli.exe", "pdfcraft-cli"),
    "wordcraft": ("wordcraft-cli.exe", "wordcraft-cli"),
    "photocraft": ("photocraft-cli.exe", "photocraft-cli"),
}


def _application_roots() -> tuple[str, ...]:
    roots = []
    executable = os.path.abspath(sys.argv[0]) if sys.argv else ""
    if executable:
        roots.append(os.path.dirname(executable))
    roots.append(os.path.abspath(os.getcwd()))
    return tuple(dict.fromkeys(roots))


def resolve_artcraft_cli(tool: str) -> str | None:
    """Найти CLI ArtCraft, не предполагая, что он установлен."""
    normalized = str(tool or "").strip().lower()
    if normalized not in _TOOL_NAMES:
        raise ValueError(f"Неизвестный движок ArtCraft: {tool}")

    candidates = []
    configured = os.environ.get(_TOOL_ENV[normalized], "").strip()
    if configured:
        candidates.append(os.path.expandvars(os.path.expanduser(configured)))

    for root in _application_roots():
        candidates.extend(
            os.path.join(root, "bin", "artcraft", normalized, name)
            for name in _TOOL_NAMES[normalized]
        )
        candidates.extend(
            os.path.join(root, "bin", "artcraft", name)
            for name in _TOOL_NAMES[normalized]
        )

    located = shutil.which(_TOOL_NAMES[normalized][0])
    if located:
        candidates.append(located)
    located = shutil.which(_TOOL_NAMES[normalized][1])
    if located:
        candidates.append(located)

    for candidate in candidates:
        if os.path.isfile(candidate):
            return os.path.abspath(candidate)
    return None


def run_artcraft_cli(
    tool: str,
    arguments: Sequence[str],
    *,
    worker=None,
) -> None:
    """Запустить CLI без shell, поддерживая отмену фоновой операции."""
    executable = resolve_artcraft_cli(tool)
    if not executable:
        variable = _TOOL_ENV.get(str(tool or "").lower(), "MULTIFORA_ARTCRAFT_CLI")
        raise FileNotFoundError(
            f"Не найден {tool}-cli. Установите бинарный файл ArtCraft CLI "
            f"или задайте переменную {variable}."
        )

    if worker is not None and worker._should_cancel():
        raise InterruptedError("Операция отменена пользователем")

    process = subprocess.Popen(
        [executable, *map(str, arguments)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    cancel_action = process.terminate
    register = getattr(worker, "_set_active_cancel_action", None)
    clear = getattr(worker, "_clear_active_cancel_action", None)
    if callable(register):
        register(cancel_action)
    try:
        _stdout, stderr = process.communicate()
        if worker is not None and worker._should_cancel():
            raise InterruptedError("Операция отменена пользователем")
        if process.returncode:
            details = (stderr or "неизвестная ошибка").strip()
            raise RuntimeError(
                f"{tool}-cli завершился с кодом {process.returncode}: {details}"
            )
    except Exception:
        if process.poll() is None:
            process.terminate()
            process.communicate()
        raise
    finally:
        if callable(clear):
            clear(cancel_action)
