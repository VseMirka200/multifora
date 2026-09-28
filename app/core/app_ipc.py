from __future__ import annotations

import ctypes
import glob
import hashlib
import os
import secrets
import shlex
import sys
import time
from ctypes import wintypes
from urllib.parse import urlparse
from urllib.request import url2pathname

try:
    from PyQt6.QtNetwork import QLocalSocket
except ImportError:
    QLocalSocket = None

from app.core.app_utils import _debug_log, _get_app_data_dir


MUTEX_HANDLE = None
ERROR_ALREADY_EXISTS = 183
_WINDOWS_OPTION_PREFIXES = ("-", "/")


def _get_ipc_token_path() -> str:
    """Путь к файлу токена для IPC."""
    return os.path.join(_get_app_data_dir(), "ipc_token.txt")


def _load_ipc_token() -> str | None:
    """Считывает IPC токен, если он существует."""
    try:
        token_path = _get_ipc_token_path()
        if not os.path.exists(token_path):
            return None
        with open(token_path, "r", encoding="utf-8") as token_file:
            return token_file.read().strip() or None
    except OSError as error:
        _debug_log(f"Ошибка загрузки IPC-токена: {error}")
        return None


def _ensure_ipc_token() -> str | None:
    """Гарантирует наличие IPC токена и возвращает его."""
    token = _load_ipc_token()
    if token:
        return token

    try:
        token = secrets.token_hex(16)
        with open(_get_ipc_token_path(), "w", encoding="utf-8") as token_file:
            token_file.write(token)
        return token
    except OSError as error:
        _debug_log(f"Ошибка создания IPC-токена: {error}")
        return None


def _delete_ipc_token() -> None:
    """Удаляет IPC токен (для уменьшения времени жизни)."""
    try:
        token_path = _get_ipc_token_path()
        if os.path.exists(token_path):
            os.remove(token_path)
    except OSError as error:
        _debug_log(f"Ошибка удаления IPC-токена: {error}")


def _get_ipc_server_name() -> str:
    """Имя IPC сервера (пер-пользователь)."""
    home = os.path.expanduser("~")
    suffix = hashlib.sha1(home.encode("utf-8", "ignore")).hexdigest()[:8]
    return f"Multifora_IPC_{suffix}"


def _get_queue_dir() -> str:
    """Каталог очереди для файлов, пришедших из контекстного меню."""
    queue_dir = os.path.join(_get_app_data_dir(), "queue")
    try:
        os.makedirs(queue_dir, exist_ok=True)
    except OSError as error:
        _debug_log(f"Ошибка получения каталога очереди: {error}")
    return queue_dir


def _is_option_argument(argument: str) -> bool:
    if argument.startswith("-"):
        return True
    return os.name == "nt" and argument.startswith(_WINDOWS_OPTION_PREFIXES[1])


def _candidate_arguments(args: list[str]) -> list[str]:
    return [argument for argument in args if argument and not _is_option_argument(argument)]


def _safe_absolute_path(path: str) -> str:
    try:
        return os.path.abspath(path)
    except Exception as error:
        _debug_log(f"Ошибка нормализации абсолютного пути {path!r}: {error}")
        return path


def _normalize_path_candidate(path: str) -> str:
    """Нормализует путь (поддержка file://)."""
    if not path:
        return path
    if not path.startswith("file://"):
        return path
    try:
        return url2pathname(urlparse(path).path)
    except Exception as error:
        _debug_log(f"Ошибка разбора file URL {path!r}: {error}")
        return path


def _add_existing_candidate(candidate, *, excluded_paths, seen, result) -> None:
    if not candidate:
        return
    normalized = _normalize_path_candidate(str(candidate).strip('"\''))
    if not normalized:
        return

    absolute_path = _safe_absolute_path(normalized)
    if absolute_path in excluded_paths or not os.path.exists(normalized):
        return
    if absolute_path in seen:
        return

    seen.add(absolute_path)
    result.append(normalized)


def _collect_paths_from_args(args: list[str]) -> list[str]:
    """Нормализует и фильтрует пути из аргументов командной строки."""
    excluded_paths = {
        path
        for path in (
            _safe_absolute_path(sys.argv[0]),
            _safe_absolute_path(sys.executable),
        )
        if path
    }
    file_paths = []
    seen = set()
    arguments = _candidate_arguments(args)

    for argument in arguments:
        _add_existing_candidate(
            argument,
            excluded_paths=excluded_paths,
            seen=seen,
            result=file_paths,
        )

    if file_paths:
        return file_paths

    try:
        split_candidates = [
            part
            for argument in arguments
            for part in shlex.split(argument, posix=False)
        ]
    except (TypeError, ValueError) as error:
        _debug_log(f"Ошибка резервного разбора аргументов запуска: {error}")
        return file_paths

    for candidate in split_candidates:
        _add_existing_candidate(
            candidate,
            excluded_paths=excluded_paths,
            seen=seen,
            result=file_paths,
        )
    return file_paths


def _enqueue_files(file_paths: list[str]) -> None:
    """Кладет файлы в очередь на диске (по одному файлу в отдельной записи)."""
    if not file_paths:
        return
    try:
        timestamp = int(time.time() * 1000)
        queue_file = os.path.join(
            _get_queue_dir(),
            f"queue_{os.getpid()}_{timestamp}.txt",
        )
        with open(queue_file, "w", encoding="utf-8") as queue_stream:
            for path in file_paths:
                if path:
                    queue_stream.write(f"{path}\n")
        _debug_log(f"Файлы добавлены в очередь: {file_paths!r} -> {queue_file}")
    except OSError as error:
        _debug_log(f"Ошибка добавления файлов в очередь: {error}")


def _read_queue_file(path: str) -> list[str]:
    queued_paths = []
    try:
        with open(path, "r", encoding="utf-8") as queue_stream:
            queued_paths.extend(line.strip() for line in queue_stream if line.strip())
    finally:
        try:
            os.remove(path)
        except OSError as error:
            _debug_log(f"Ошибка удаления файла очереди {path}: {error}")
    return queued_paths


def _drain_queued_files() -> list[str]:
    """Забирает все файлы из очереди и очищает ее."""
    queued_paths = []
    try:
        queue_pattern = os.path.join(_get_queue_dir(), "queue_*.txt")
        for queue_file in sorted(glob.glob(queue_pattern)):
            try:
                queued_paths.extend(_read_queue_file(queue_file))
            except Exception as error:
                _debug_log(f"Ошибка чтения файла очереди {queue_file}: {error}")
    except Exception as error:
        _debug_log(f"Ошибка чтения очереди файлов: {error}")

    result = []
    seen = set()
    for path in queued_paths:
        normalized = _normalize_path_candidate(path)
        if not normalized or not os.path.exists(normalized) or normalized in seen:
            continue
        seen.add(normalized)
        result.append(normalized)

    if result:
        _debug_log(f"Очередь обработана: {result!r}")
    return result


def is_first_instance() -> bool:
    """Возвращает True для первого экземпляра приложения и False для следующих."""
    global MUTEX_HANDLE
    if os.name != "nt":
        return True

    try:
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        create_mutex = kernel32.CreateMutexW
        create_mutex.argtypes = (wintypes.LPVOID, wintypes.BOOL, wintypes.LPCWSTR)
        create_mutex.restype = wintypes.HANDLE

        # Local\ ограничивает mutex текущим пользовательским сеансом Windows.
        MUTEX_HANDLE = create_mutex(None, False, "Local\\Multifora_SingleInstance_Mutex")
        return ctypes.get_last_error() != ERROR_ALREADY_EXISTS
    except Exception as error:
        # Ошибка системного mutex не должна блокировать запуск приложения.
        _debug_log(f"Ошибка проверки единственного экземпляра: {error}")
        return True


def _get_command_line_args() -> list[str]:
    """Безопасно парсит сырой командный ряд Windows (с учетом кавычек)."""
    if os.name != "nt":
        return []
    try:
        shell32 = ctypes.WinDLL("shell32", use_last_error=True)
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

        kernel32.GetCommandLineW.restype = wintypes.LPCWSTR
        shell32.CommandLineToArgvW.argtypes = (
            wintypes.LPCWSTR,
            ctypes.POINTER(ctypes.c_int),
        )
        shell32.CommandLineToArgvW.restype = ctypes.POINTER(wintypes.LPWSTR)
        kernel32.LocalFree.argtypes = (wintypes.HLOCAL,)
        kernel32.LocalFree.restype = wintypes.HLOCAL

        raw_command = kernel32.GetCommandLineW()
        argument_count = ctypes.c_int()
        arguments = shell32.CommandLineToArgvW(raw_command, ctypes.byref(argument_count))
        if not arguments:
            return []
        try:
            return [arguments[index] for index in range(argument_count.value)]
        finally:
            kernel32.LocalFree(arguments)
    except Exception as error:
        _debug_log(f"Ошибка разбора командной строки Windows: {error}")
        return []


def collect_startup_files() -> list[str]:
    """Собирает пути к файлам из командной строки."""
    _debug_log(f"Аргументы запуска sys.argv: {sys.argv!r}")
    file_paths = _collect_paths_from_args(sys.argv[1:])
    if file_paths:
        _debug_log(f"Стартовые файлы (sys.argv/shlex): {file_paths!r}")
        return file_paths

    raw_arguments = _get_command_line_args()
    _debug_log(f"Аргументы через CommandLineToArgvW: {raw_arguments!r}")
    if raw_arguments:
        file_paths = _collect_paths_from_args(raw_arguments[1:])

    _debug_log(f"Стартовые файлы (резервный разбор): {file_paths!r}")
    return file_paths


def send_files_to_running_instance(
    file_paths: list[str],
    retries: int = 50,
    delay: float = 0.05,
) -> bool:
    """Отправляет файлы запущенному экземпляру через IPC (QLocalSocket)."""
    if not file_paths:
        _debug_log("send_files_to_running_instance: нет файлов для отправки")
        return False
    if QLocalSocket is None:
        _debug_log("send_files_to_running_instance: PyQt6 недоступен")
        return False

    token = _load_ipc_token()
    if not token:
        _debug_log("send_files_to_running_instance: IPC-токен не найден")
        return False

    payload_lines = [f"TOKEN:{token}"]
    payload_lines.extend(f"ADD_FILE:{path}" for path in file_paths if path)
    payload = ("\n".join(payload_lines) + "\n").encode("utf-8")
    last_error = None

    for _attempt in range(retries):
        try:
            socket_client = QLocalSocket()
            socket_client.connectToServer(_get_ipc_server_name())
            if not socket_client.waitForConnected(200):
                time.sleep(delay)
                continue
            socket_client.write(payload)
            socket_client.flush()
            socket_client.waitForBytesWritten(500)
            socket_client.disconnectFromServer()
            _debug_log(f"Файлы отправлены запущенному экземпляру: {file_paths!r}")
            return True
        except Exception as error:
            last_error = error
            time.sleep(delay)

    suffix = f": {last_error}" if last_error else ""
    _debug_log(
        "send_files_to_running_instance: не удалось подключиться после повторных попыток"
        f"{suffix}"
    )
    return False
