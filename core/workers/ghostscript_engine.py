"""Запуск поставляемого с приложением Ghostscript."""

import os
import subprocess
import tempfile
import time

from app.core import deps
from core.workers.engine_policy import adaptive_timeout


class GhostscriptUnavailableError(RuntimeError):
    """Движок отсутствует или не может быть запущен."""


def run_ghostscript(arguments, should_cancel, timeout=None):
    available, executable = deps.ensure_ghostscript_detected()
    if not available or not executable:
        raise GhostscriptUnavailableError("Не найден движок Ghostscript")
    if should_cancel():
        raise InterruptedError("Операция отменена пользователем")
    if timeout is None:
        size = 0
        for argument in arguments:
            if not isinstance(argument, str) or argument.startswith("-"):
                continue
            try:
                if os.path.isfile(argument):
                    size += os.path.getsize(argument)
            except OSError:
                continue
        timeout = adaptive_timeout(size)
    try:
        temporary_log = tempfile.TemporaryFile(mode="w+t", encoding="utf-8", errors="replace")  # noqa: SIM115
    except OSError as error:
        raise GhostscriptUnavailableError(f"Не удалось создать временные файлы Ghostscript: {error}") from error
    with temporary_log as log:
        try:
            process = subprocess.Popen(
                [executable, "-dSAFER", "-dBATCH", "-dNOPAUSE", *arguments],
                stdout=log,
                stderr=subprocess.STDOUT,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except OSError as error:
            raise GhostscriptUnavailableError(f"Не удалось запустить Ghostscript: {error}") from error
        start = time.monotonic()
        try:
            while process.poll() is None:
                if should_cancel():
                    raise InterruptedError("Операция отменена пользователем")
                if time.monotonic() - start > timeout:
                    raise TimeoutError("Превышено время работы Ghostscript")
                time.sleep(0.1)
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
        if process.returncode:
            log.seek(0)
            detail = log.read()[-1500:].strip()
            raise RuntimeError("Ошибка Ghostscript" + (f": {detail}" if detail else ""))
        if should_cancel():
            raise InterruptedError("Операция отменена пользователем")
