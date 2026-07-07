import os
import sys
import time
import ctypes
import hashlib
import secrets
from ctypes import wintypes
from PyQt6.QtNetwork import QLocalSocket

from app.core.app_utils import _debug_log, _get_app_data_dir

def _get_ipc_token_path():
    """Путь к файлу токена для IPC."""
    return os.path.join(_get_app_data_dir(), "ipc_token.txt")

def _load_ipc_token():
    """Считывает IPC токен, если он существует."""
    try:
        token_path = _get_ipc_token_path()
        if os.path.exists(token_path):
            with open(token_path, "r", encoding="utf-8") as f:
                token = f.read().strip()
                return token or None
    except Exception as e:
        _debug_log(f"Ошибка загрузки IPC-токена: {e}")
    return None

def _ensure_ipc_token():
    """Гарантирует наличие IPC токена и возвращает его."""
    token = _load_ipc_token()
    if token:
        return token
    try:
        token = secrets.token_hex(16)
        token_path = _get_ipc_token_path()
        with open(token_path, "w", encoding="utf-8") as f:
            f.write(token)
        return token
    except Exception as e:
        _debug_log(f"Ошибка создания IPC-токена: {e}")
        return None

def _delete_ipc_token():
    """Удаляет IPC токен (для уменьшения времени жизни)."""
    try:
        token_path = _get_ipc_token_path()
        if os.path.exists(token_path):
            os.remove(token_path)
    except Exception as e:
        _debug_log(f"Ошибка удаления IPC-токена: {e}")

def _get_ipc_server_name():
    """Имя IPC сервера (пер-пользователь)."""
    try:
        home = os.path.expanduser("~")
        suffix = hashlib.sha1(home.encode("utf-8", "ignore")).hexdigest()[:8]
    except Exception:
        suffix = "default"
    return f"Multifora_IPC_{suffix}"

def _get_queue_dir():
    """Каталог очереди для файлов, пришедших из контекстного меню."""
    base_dir = os.path.join(_get_app_data_dir(), "queue")
    try:
        os.makedirs(base_dir, exist_ok=True)
    except Exception as e:
        _debug_log(f"Ошибка получения каталога очереди: {e}")
    return base_dir

def _collect_paths_from_args(args):
    """Нормализует и фильтрует пути из аргументов командной строки."""
    file_paths = []
    seen = set()
    try:
        script_path = os.path.abspath(sys.argv[0])
    except Exception:
        script_path = None
    try:
        exe_path = os.path.abspath(sys.executable)
    except Exception:
        exe_path = None

    def add_candidate(candidate):
        if not candidate:
            return
        clean = _normalize_path_candidate(candidate.strip('"\'')) 
        if not clean:
            return
        try:
            cand_abs = os.path.abspath(clean)
        except Exception:
            cand_abs = clean
        if cand_abs and (cand_abs == script_path or cand_abs == exe_path):
            return
        if os.path.exists(clean):
            if cand_abs not in seen:
                seen.add(cand_abs)
                file_paths.append(clean)

    for arg in args:
        if not arg:
            continue
        if arg.startswith('-') or arg.startswith('/'):
            continue
        add_candidate(arg)

    if not file_paths:
        try:
            import shlex
            candidates = []
            for arg in args:
                if not arg:
                    continue
                if arg.startswith('-') or arg.startswith('/'):
                    continue
                parts = shlex.split(arg, posix=False)
                if parts:
                    candidates.extend(parts)
            for cand in candidates:
                add_candidate(cand)
        except Exception:
            pass

    return file_paths

def _enqueue_files(file_paths):
    """Кладет файлы в очередь на диске (по одному файлу в отдельной записи)."""
    if not file_paths:
        return
    try:
        queue_dir = _get_queue_dir()
        ts = int(time.time() * 1000)
        queue_file = os.path.join(queue_dir, f"queue_{os.getpid()}_{ts}.txt")
        with open(queue_file, "w", encoding="utf-8") as f:
            for p in file_paths:
                if p:
                    f.write(p + "\n")
        _debug_log(f"Файлы добавлены в очередь: {file_paths!r} -> {queue_file}")
    except Exception as e:
        _debug_log(f"Ошибка добавления файлов в очередь: {e}")

def _drain_queued_files():
    """Забирает все файлы из очереди и очищает ее."""
    files = []
    try:
        import glob
        queue_dir = _get_queue_dir()
        for path in sorted(glob.glob(os.path.join(queue_dir, "queue_*.txt"))):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    for line in f:
                        p = line.strip()
                        if p:
                            files.append(p)
            finally:
                try:
                    os.remove(path)
                except Exception as e:
                    _debug_log(f"Ошибка удаления файла очереди: {e}")
    except Exception as e:
        _debug_log(f"Ошибка чтения очереди файлов: {e}")

    # Нормализуем и фильтруем существующие пути
    result = []
    seen = set()
    for p in files:
        p = _normalize_path_candidate(p)
        if not p:
            continue
        if os.path.exists(p) and p not in seen:
            seen.add(p)
            result.append(p)
    if result:
        _debug_log(f"Очередь обработана: {result!r}")
    return result

# --- Single-instance (Windows mutex) ---
MUTEX_HANDLE = None
ERROR_ALREADY_EXISTS = 183

def is_first_instance() -> bool:
    """Return True for the first running instance, False for subsequent ones."""
    global MUTEX_HANDLE
    try:
        # Local\ is per-user-session; enough for Explorer multi-launches.
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        create_mutex = kernel32.CreateMutexW
        create_mutex.argtypes = (wintypes.LPVOID, wintypes.BOOL, wintypes.LPCWSTR)
        create_mutex.restype = wintypes.HANDLE

        MUTEX_HANDLE = create_mutex(None, False, "Local\\Multifora_SingleInstance_Mutex")
        # If the mutex already exists, GetLastError returns ERROR_ALREADY_EXISTS (183)
        return ctypes.get_last_error() != ERROR_ALREADY_EXISTS
    except Exception:
        # If anything goes wrong, don't block execution.
        return True

def _get_command_line_args():
    """Безопасно парсит сырой командный ряд Windows (с учетом кавычек)."""
    if os.name != 'nt':
        return []
    try:
        shell32 = ctypes.WinDLL("shell32", use_last_error=True)
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

        kernel32.GetCommandLineW.restype = wintypes.LPCWSTR
        shell32.CommandLineToArgvW.argtypes = (wintypes.LPCWSTR, ctypes.POINTER(ctypes.c_int))
        shell32.CommandLineToArgvW.restype = ctypes.POINTER(wintypes.LPWSTR)
        kernel32.LocalFree.argtypes = (wintypes.HLOCAL,)
        kernel32.LocalFree.restype = wintypes.HLOCAL

        raw_cmd = kernel32.GetCommandLineW()
        argc = ctypes.c_int()
        argv = shell32.CommandLineToArgvW(raw_cmd, ctypes.byref(argc))
        if not argv:
            return []
        args = [argv[i] for i in range(argc.value)]
        kernel32.LocalFree(argv)
        return args
    except Exception:
        return []

def _normalize_path_candidate(path: str) -> str:
    """Нормализует путь (поддержка file://)."""
    if not path:
        return path
    try:
        if path.startswith("file://"):
            from urllib.parse import urlparse
            from urllib.request import url2pathname
            parsed = urlparse(path)
            return url2pathname(parsed.path)
    except Exception:
        pass
    return path

def collect_startup_files():
    """Собирает пути к файлам из командной строки."""
    _debug_log(f"Аргументы запуска sys.argv: {sys.argv!r}")
    file_paths = _collect_paths_from_args(sys.argv[1:])
    if file_paths:
        _debug_log(f"Стартовые файлы (sys.argv/shlex): {file_paths!r}")
        return file_paths

    # Fallback: парсим сырой командный ряд Windows
    try:
        candidates = _get_command_line_args()
        _debug_log(f"Аргументы через CommandLineToArgvW: {candidates!r}")
        if candidates:
            file_paths = _collect_paths_from_args(candidates[1:])
    except Exception:
        pass

    _debug_log(f"Стартовые файлы (резервный разбор): {file_paths!r}")
    return file_paths

def send_files_to_running_instance(file_paths, retries=50, delay=0.05):
    """Отправляет файлы запущенному экземпляру через IPC (QLocalSocket)."""
    if not file_paths:
        _debug_log("send_files_to_running_instance: нет файлов для отправки")
        return False

    token = _load_ipc_token()
    if not token:
        _debug_log("send_files_to_running_instance: IPC-токен не найден")
        return False

    server_name = _get_ipc_server_name()
    payload_lines = [f"TOKEN:{token}"]
    for path in file_paths:
        if path:
            payload_lines.append(f"ADD_FILE:{path}")
    payload = ("\n".join(payload_lines) + "\n").encode("utf-8")

    for _ in range(retries):
        try:
            socket_client = QLocalSocket()
            socket_client.connectToServer(server_name)
            if not socket_client.waitForConnected(200):
                time.sleep(delay)
                continue
            socket_client.write(payload)
            socket_client.flush()
            socket_client.waitForBytesWritten(500)
            socket_client.disconnectFromServer()
            _debug_log(f"Файлы отправлены запущенному экземпляру: {file_paths!r}")
            return True
        except Exception:
            time.sleep(delay)
            continue
    _debug_log("send_files_to_running_instance: не удалось подключиться после повторных попыток")
    return False

# Проверяем наличие библиотек для конвертации
