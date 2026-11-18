"""Conversion through the bundled WordCraft document engine."""

from __future__ import annotations

import base64
import mimetypes
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from urllib.parse import unquote, urlsplit

from core.workers.atomic_output import atomic_output_path
from core.workers.engine_policy import adaptive_timeout

OFFICE_INPUTS = frozenset({"DOC", "DOCX", "ODT", "RTF", "HTML", "TXT"})
OFFICE_OUTPUTS = frozenset({"PDF", "DOCX", "ODT", "RTF", "TXT", "HTML"})
class OfficeUnavailableError(RuntimeError):
    """No installed office backend is available for the queue."""


def _stop_process(process):
    if process.poll() is None:
        if os.name == "nt":
            subprocess.run(
                ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                capture_output=True,
                timeout=15,
                check=False,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        else:
            process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()


def _run(arguments, directory, should_cancel, timeout, status):
    log_path = directory / "office.log"
    with log_path.open("wb") as log:
        process = subprocess.Popen(
            arguments,
            cwd=directory,
            stdout=log,
            stderr=subprocess.STDOUT,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        start = time.monotonic()
        next_notice = 5
        try:
            while process.poll() is None:
                if should_cancel():
                    raise InterruptedError("Конвертация отменена пользователем")
                elapsed = time.monotonic() - start
                if elapsed > timeout:
                    raise TimeoutError(f"Офисная конвертация превысила {timeout} секунд")
                if callable(status) and elapsed >= next_notice:
                    status(f"Офисная конвертация: прошло {int(elapsed)} с.")
                    next_notice += 15
                time.sleep(0.1)
        finally:
            _stop_process(process)
    if should_cancel():
        raise InterruptedError("Конвертация отменена пользователем")
    if process.returncode:
        detail = log_path.read_text(encoding="utf-8", errors="replace")[-2000:].strip()
        raise RuntimeError(detail or f"Офисное приложение завершилось с кодом {process.returncode}")


def _normalize_export(output, target):
    """Keep TXT in UTF-8 and embed HTML images before temporary files disappear."""
    if target not in {"TXT", "HTML"}:
        return
    data = output.read_bytes()
    charset = re.search(rb"charset\s*=\s*[\"']?([a-zA-Z0-9_-]+)", data[:4096], re.I)
    encoding = (
        "utf-16"
        if data.startswith((b"\xff\xfe", b"\xfe\xff"))
        else (charset.group(1).decode("ascii") if charset else "utf-8-sig")
    )
    content = data.decode(encoding).replace("\r\n", "\n").replace("\r", "\n")
    if target == "HTML":
        base = output.parent.resolve()

        def embed(match):
            src = match.group(2)
            parsed = urlsplit(src)
            if parsed.scheme or parsed.netloc:
                return match.group(0)
            image = (base / unquote(parsed.path)).resolve()
            if not image.is_relative_to(base) or not image.is_file():
                raise RuntimeError("Не найдено изображение HTML: " + src)
            mime = mimetypes.guess_type(image.name)[0]
            if not mime or not mime.startswith("image/"):
                raise RuntimeError("Неподдерживаемый ресурс HTML: " + src)
            uri = "data:" + mime + ";base64," + base64.b64encode(image.read_bytes()).decode("ascii")
            return 'src="' + uri + '"'

        content = re.sub(r"\bsrc\s*=\s*([\"'])(.*?)\1", embed, content, flags=re.I | re.S)
        content = re.sub(r"(charset\s*=\s*[\"']?)[a-zA-Z0-9_-]+", r"\g<1>utf-8", content, flags=re.I)
    output.write_text(content, encoding="utf-8", newline="\n")


def find_wordcraft() -> str | None:
    root = (
        Path(sys.executable).resolve().parent
        if getattr(sys, "frozen", False)
        else Path(__file__).resolve().parents[2]
    )
    executable = root / "bin" / "wordcraft" / "wordcraft-cli.exe"
    return str(executable) if executable.is_file() else None


def run_office(source, destination, target_format, should_cancel, *, status=None) -> str:
    """Convert with the bundled WordCraft CLI and publish only complete output."""
    target = target_format.upper()
    if target not in OFFICE_OUTPUTS:
        raise ValueError(f"Неподдерживаемый формат документа: {target}")
    if should_cancel():
        raise InterruptedError("Конвертация отменена")
    source = Path(source).resolve()
    if not source.is_file():
        raise FileNotFoundError(source)
    executable = find_wordcraft()
    if not executable:
        raise OfficeUnavailableError("Встроенный движок WordCraft не найден. Переустановите Мультифору.")
    if callable(status):
        status("WordCraft...")
    with tempfile.TemporaryDirectory(prefix="multifora_document_") as folder:
        directory = Path(folder)
        output = directory / ("result." + target.lower())
        _run([executable, "convert", str(source), str(output)], directory, should_cancel,
             adaptive_timeout(source.stat().st_size), status)
        if not output.is_file() or output.stat().st_size == 0:
            raise RuntimeError("WordCraft не создал выходной файл")
        _normalize_export(output, target)
        if target == "PDF":
            with output.open("rb") as stream:
                if stream.read(5) != b"%PDF-":
                    raise RuntimeError("WordCraft создал некорректный PDF")
        if should_cancel():
            raise InterruptedError("Конвертация отменена")
        with atomic_output_path(destination) as temporary:
            shutil.copyfile(output, temporary)
            if should_cancel():
                raise InterruptedError("Конвертация отменена")
    return ""
