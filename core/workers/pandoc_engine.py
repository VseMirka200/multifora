"""Run the bundled Pandoc document converter."""

import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from core.workers.engine_policy import adaptive_timeout


class PandocUnavailableError(RuntimeError):
    """Pandoc is missing or could not be started."""


def find_pandoc() -> str | None:
    root = (
        Path(sys.executable).resolve().parent
        if getattr(sys, "frozen", False)
        else Path(__file__).resolve().parents[2]
    )
    executable = root / "bin" / "pandoc" / ("pandoc.exe" if os.name == "nt" else "pandoc")
    if executable.is_file():
        return str(executable)
    return shutil.which("pandoc") if not getattr(sys, "frozen", False) else None


def run_pandoc(source: str, destination: str, reader: str, writer: str, should_cancel, timeout=None) -> str:
    executable = find_pandoc()
    if not executable:
        raise PandocUnavailableError("Не найден движок Pandoc")
    if should_cancel():
        raise InterruptedError("Операция отменена пользователем")
    if timeout is None:
        timeout = adaptive_timeout(os.path.getsize(source))
    arguments = [executable, "--sandbox", "--standalone", "--from", reader, "--to", writer, "--output", destination]
    arguments.extend(["--", os.path.abspath(source)])
    with tempfile.TemporaryFile(mode="w+t", encoding="utf-8", errors="replace") as log:
        try:
            process = subprocess.Popen(
                arguments, stdout=log, stderr=subprocess.STDOUT,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except OSError as error:
            raise PandocUnavailableError(f"Не удалось запустить Pandoc: {error}") from error
        start = time.monotonic()
        try:
            while process.poll() is None:
                if should_cancel():
                    raise InterruptedError("Операция отменена пользователем")
                if time.monotonic() - start > timeout:
                    raise TimeoutError("Превышено время работы Pandoc")
                time.sleep(0.1)
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
        log.seek(0)
        detail = log.read()[-1500:].strip()
        if process.returncode:
            raise RuntimeError("Ошибка Pandoc" + (f": {detail}" if detail else ""))
        if should_cancel():
            raise InterruptedError("Операция отменена пользователем")
        return detail
