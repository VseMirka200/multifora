"""Конвертация презентаций через установленный LibreOffice Impress."""

import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time

from core.conversion_formats import PRESENTATION_FORMATS
from core.filesystem import publish_new_file


def _office_executable():
    for variable in ("ProgramW6432", "ProgramFiles", "ProgramFiles(x86)"):
        root = os.environ.get(variable)
        if root:
            executable = Path(root) / "LibreOffice/program/soffice.exe"
            if executable.is_file():
                return str(executable)
    executable = shutil.which("soffice")
    if executable:
        return executable
    raise FileNotFoundError("Для конвертации презентаций установите LibreOffice Impress.")


def convert_presentation(source, destination, should_cancel):
    source = Path(source).resolve()
    destination = Path(destination).absolute()
    target = destination.suffix.lower()
    if source.suffix[1:].upper() not in PRESENTATION_FORMATS or target[1:].upper() not in (*PRESENTATION_FORMATS, "PDF"):
        raise ValueError("Неподдерживаемый формат презентации")
    executable = _office_executable()
    with tempfile.TemporaryDirectory(dir=destination.parent) as temporary:
        staging = Path(temporary)
        # Отдельный профиль не передаёт задание в уже открытое окно LibreOffice.
        command = [
            executable, "-env:UserInstallation=" + (staging / "profile").as_uri(),
            "--headless", "--convert-to", target[1:], "--outdir", str(staging), str(source),
        ]
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        with subprocess.Popen(command, creationflags=flags, stdin=subprocess.DEVNULL) as process:
            deadline = time.monotonic() + 300
            try:
                while process.poll() is None:
                    if should_cancel():
                        raise InterruptedError("Конвертация отменена")
                    if time.monotonic() >= deadline:
                        raise TimeoutError("LibreOffice не завершил конвертацию за пять минут.")
                    time.sleep(0.1)
            finally:
                if process.poll() is None:
                    process.kill()
                    process.wait()
        if should_cancel():
            raise InterruptedError("Конвертация отменена")
        result = staging / (source.stem + target)
        if process.returncode or not result.is_file() or not result.stat().st_size:
            raise ValueError("LibreOffice не смог преобразовать презентацию. Проверьте, открывается ли исходный файл в Impress.")
        publish_new_file(result, destination)
