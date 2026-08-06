import os
from datetime import datetime


def _debug_log(message: str):
    """Пишет диагностический лог в AppData (для отладки запуска/аргументов)."""
    try:
        base_dir = os.path.join(os.path.expanduser("~"), "AppData", "Roaming", "Multifora")
        os.makedirs(base_dir, exist_ok=True)
        log_path = os.path.join(base_dir, "debug_args.txt")
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(log_path, "a", encoding="utf-8") as log_file:
            log_file.write(f"[{timestamp}] {message}\n")
    except OSError:
        return


def _log_ignored_error(context: str, error: Exception) -> None:
    _debug_log(f"{context}: {error}")


def _get_app_data_dir():
    """Базовый каталог данных приложения в AppData."""
    base_dir = os.path.join(os.path.expanduser("~"), "AppData", "Roaming", "Multifora")
    try:
        os.makedirs(base_dir, exist_ok=True)
    except Exception as error:
        _debug_log(f"Ошибка получения каталога данных приложения: {error}")
    return base_dir

