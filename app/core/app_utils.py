import os
from datetime import datetime

def _debug_log(message: str):
    """Пишет диагностический лог в AppData (для отладки запуска/аргументов)."""
    try:
        base_dir = os.path.join(os.path.expanduser("~"), "AppData", "Roaming", "Multifora")
        os.makedirs(base_dir, exist_ok=True)
        log_path = os.path.join(base_dir, "debug_args.txt")
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] {message}\n")
    except Exception:
        pass

def _get_app_data_dir():
    """Базовый каталог данных приложения в AppData."""
    base_dir = os.path.join(os.path.expanduser("~"), "AppData", "Roaming", "Multifora")
    try:
        os.makedirs(base_dir, exist_ok=True)
    except Exception as e:
        _debug_log(f"Ошибка получения каталога данных приложения: {e}")
    return base_dir

