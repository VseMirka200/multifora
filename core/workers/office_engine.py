"""Conversion through office applications installed on the user's computer."""

from __future__ import annotations

import base64
import mimetypes
import os
import re
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from urllib.parse import unquote, urlsplit

from core.workers.atomic_output import atomic_output_path
from core.workers.engine_policy import adaptive_timeout

OFFICE_INPUTS = frozenset({"DOC", "DOCX", "ODT", "RTF", "HTML", "TXT"})
OFFICE_OUTPUTS = frozenset({"PDF", "DOCX", "ODT", "RTF", "TXT", "HTML"})
LIBREOFFICE_FILTERS = {
    "TXT": "txt:Text (encoded):UTF8",
    "HTML": "html:HTML (StarWriter)",
    "PDF": "pdf:writer_pdf_Export",
    "DOCX": "docx:Office Open XML Text",
    "ODT": "odt:writer8",
    "RTF": "rtf:Rich Text Format",
}


class OfficeUnavailableError(RuntimeError):
    """No installed office backend is available for the queue."""


def _registry_paths(executable):
    if os.name != "nt":
        return []
    import winreg

    result = []
    for hive in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
        for view in (winreg.KEY_WOW64_64KEY, winreg.KEY_WOW64_32KEY):
            try:
                with winreg.OpenKey(
                    hive,
                    "SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\App Paths\\" + executable,
                    0,
                    winreg.KEY_READ | view,
                ) as key:
                    result.append(winreg.QueryValueEx(key, None)[0].strip('"'))
            except OSError:
                pass
    return result


def find_word() -> str | None:
    if os.name != "nt":
        return None
    candidates = _registry_paths("WINWORD.EXE")
    candidates.append(shutil.which("winword.exe"))
    for variable in ("ProgramFiles", "ProgramFiles(x86)"):
        base = Path(os.environ.get(variable, "C:/Program Files")) / "Microsoft Office"
        for version in ("Office16", "Office15", "Office14"):
            candidates.extend([str(base / "root" / version / "WINWORD.EXE"), str(base / version / "WINWORD.EXE")])
    return next((str(Path(p).resolve()) for p in candidates if p and Path(p).is_file()), None)


def find_libreoffice() -> str | None:
    candidates = []
    for name in ("soffice.com", "soffice.exe", "soffice", "libreoffice"):
        candidates.append(shutil.which(name))
        candidates.extend(_registry_paths(name))
    for variable in ("ProgramFiles", "ProgramFiles(x86)", "LOCALAPPDATA"):
        base = Path(os.environ.get(variable, "C:/Program Files"))
        for folder in (base / "LibreOffice", base / "Programs" / "LibreOffice"):
            candidates.extend(str(folder / "program" / name) for name in ("soffice.com", "soffice.exe"))
    candidates.append("/Applications/LibreOffice.app/Contents/MacOS/soffice")
    return next((str(Path(p).resolve()) for p in candidates if p and Path(p).is_file()), None)


def _powershell():
    return shutil.which("powershell.exe") or str(
        Path(os.environ.get("WINDIR", "C:/Windows")) / "System32/WindowsPowerShell/v1.0/powershell.exe"
    )


def _word_script():
    return Path(__file__).with_name("office_word.ps1")


def _stop_owned_word(pid_file):
    if not pid_file.is_file():
        return
    subprocess.run(
        [
            _powershell(),
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(_word_script()),
            "-PidFile",
            str(pid_file),
            "-Cleanup",
        ],
        capture_output=True,
        timeout=15,
        check=False,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )


def _stop_process(process, pid_file=None):
    if process.poll() is None:
        if os.name == "nt":
            # This process owns an isolated LibreOffice profile / PowerShell instance.
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
    if pid_file is not None:
        _stop_owned_word(pid_file)


def _run(arguments, directory, should_cancel, timeout, status, pid_file=None):
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
            _stop_process(process, pid_file)
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


def run_office(source, destination, target_format, should_cancel, *, status=None) -> str:
    """Prefer Word, fall back to LibreOffice; never publish incomplete output."""
    target = target_format.upper()
    if target not in OFFICE_OUTPUTS:
        raise ValueError(f"Офисный экспорт не поддерживает {target}")
    if should_cancel():
        raise InterruptedError("Конвертация отменена пользователем")
    source = Path(source).resolve()
    if not source.is_file():
        raise FileNotFoundError(source)
    word, libreoffice = find_word(), find_libreoffice()
    backends = [("Microsoft Word", word), ("LibreOffice", libreoffice)]
    if source.suffix.lower() == ".odt":
        backends.reverse()
    backends = [(name, exe) for name, exe in backends if exe]
    if not backends:
        raise OfficeUnavailableError(
            "Для конвертации установите Microsoft Word или LibreOffice. Приложения не найдены."
        )
    failures = []
    timeout = adaptive_timeout(source.stat().st_size)
    for name, executable in backends:
        if should_cancel():
            raise InterruptedError("Конвертация отменена пользователем")
        if callable(status):
            status(f"Конвертация через {name}...")
        try:
            with tempfile.TemporaryDirectory(prefix="multifora_office_") as folder:
                directory = Path(folder)
                pid_file = None
                if name == "Microsoft Word":
                    output = directory / ("result." + target.lower())
                    pid_file = directory / "word-pid.json"
                    arguments = [
                        _powershell(),
                        "-NoProfile",
                        "-NonInteractive",
                        "-ExecutionPolicy",
                        "Bypass",
                        "-File",
                        str(_word_script()),
                        "-Source",
                        str(source),
                        "-Output",
                        str(output),
                        "-Target",
                        target,
                        "-PidFile",
                        str(pid_file),
                    ]
                else:
                    profile = directory / "profile"
                    output_dir = directory / "output"
                    output_dir.mkdir()
                    output = output_dir / (source.stem + "." + target.lower())
                    arguments = [
                        executable,
                        "-env:UserInstallation=" + profile.as_uri(),
                        "--headless",
                        "--nologo",
                        "--nodefault",
                        "--norestore",
                        "--convert-to",
                        LIBREOFFICE_FILTERS[target],
                        "--outdir",
                        str(output_dir),
                        str(source),
                    ]
                _run(arguments, directory, should_cancel, timeout, status, pid_file)
                if not output.is_file() or output.stat().st_size == 0:
                    raise RuntimeError(f"{name} не создал выходной файл")
                _normalize_export(output, target)
                if target == "PDF":
                    with output.open("rb") as stream:
                        if stream.read(5) != b"%PDF-":
                            raise RuntimeError(f"{name} создал некорректный PDF")
                if should_cancel():
                    raise InterruptedError("Конвертация отменена пользователем")
                with atomic_output_path(destination) as temporary:
                    shutil.copyfile(output, temporary)
                    if should_cancel():
                        raise InterruptedError("Конвертация отменена пользователем")
                return "; ".join(failures)
        except InterruptedError:
            raise
        except FileExistsError:
            raise
        except (OSError, RuntimeError, TimeoutError) as error:
            failures.append(f"{name}: {error}")
    raise RuntimeError("Не удалось конвертировать документ. " + "; ".join(failures))
