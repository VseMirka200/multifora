"""Чтение, миграция и атомарное сохранение настроек пользователя в JSON."""

import json
import os
import tempfile

from app.core.app_utils import _debug_log, _get_app_data_dir

_SETTINGS_FILENAME = "multifora_settings.json"


def log_settings_error(context: str, error: Exception) -> None:
    _debug_log(f"Ошибка {context}: {error}")


def _legacy_settings_candidates() -> tuple[str, ...]:
    user_dir = os.path.expanduser("~")
    roaming_dir = os.path.join(user_dir, "AppData", "Roaming")
    return (
        os.path.join(roaming_dir, "Multifora", _SETTINGS_FILENAME),
        os.path.join(roaming_dir, "python", "Multifora", _SETTINGS_FILENAME),
        os.path.join(roaming_dir, _SETTINGS_FILENAME),
        os.path.join(user_dir, "Documents", "Multifora", _SETTINGS_FILENAME),
    )


def _migrate_legacy_settings(target_file: str) -> None:
    existing_candidates = []
    for candidate in _legacy_settings_candidates():
        try:
            if os.path.exists(candidate):
                existing_candidates.append(candidate)
        except OSError as error:
            log_settings_error(
                f"проверки старого файла настроек {candidate}", error
            )

    if not existing_candidates:
        return

    try:
        newest_candidate = max(existing_candidates, key=os.path.getmtime)
        target_exists = os.path.exists(target_file)
        target_is_older = target_exists and os.path.getmtime(
            newest_candidate
        ) > os.path.getmtime(target_file)
        should_migrate = not target_exists or target_is_older
        if not should_migrate or os.path.normcase(
            newest_candidate
        ) == os.path.normcase(target_file):
            return

        with open(newest_candidate, encoding="utf-8") as source:
            migrated_data = source.read()
        with open(target_file, "w", encoding="utf-8") as destination:
            destination.write(migrated_data)
    except Exception as error:
        log_settings_error("миграции файла настроек", error)


def get_settings_file_path() -> str:
    """Возвращает путь к настройкам в профиле текущего пользователя."""
    target_dir = _get_app_data_dir()
    target_file = os.path.join(target_dir, _SETTINGS_FILENAME)
    _migrate_legacy_settings(target_file)
    return target_file


def read_settings(settings_file: str) -> dict | None:
    if not os.path.exists(settings_file):
        return None
    with open(settings_file, encoding="utf-8") as settings_stream:
        data = json.load(settings_stream)
    if not isinstance(data, dict):
        raise ValueError(
            "корневое значение файла настроек должно быть объектом"
        )
    return data


def write_settings(settings_file: str, data: dict) -> None:
    temporary = None
    try:
        folder = os.path.dirname(os.path.abspath(settings_file))
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=folder,
            prefix=".__multifora_settings_",
            suffix=".tmp",
            delete=False,
        ) as settings_stream:
            temporary = settings_stream.name
            json.dump(data, settings_stream, ensure_ascii=False, indent=2)
            settings_stream.flush()
            os.fsync(settings_stream.fileno())
        os.replace(temporary, settings_file)
        temporary = None
    finally:
        if temporary and os.path.exists(temporary):
            try:
                os.remove(temporary)
            except OSError as error:
                log_settings_error("удаления временных настроек", error)
