"""Готовит и проверяет автономный набор ресурсов Tectonic для сборки."""

from __future__ import annotations

import hashlib
import io
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.workers.conversion.pdf_layout import PdfLayout  # noqa: E402
from core.workers.conversion.tectonic_pdf import FONT_CHOICE, build_tex  # noqa: E402


def _sample():
    from PIL import Image

    assets = {}
    for name, fmt in (("sample.png", "PNG"), ("sample.jpg", "JPEG"), ("sample.pdf", "PDF")):
        with Image.new("RGB", (4, 4), "red") as image:
            stream = io.BytesIO()
            image.save(stream, fmt)
            assets[name] = stream.getvalue()
    sizes = "".join(
        f'<span style="font-size:{size}pt">R <b>B</b> <i>I</i> <b><i>BI</i></b> <code>M</code> </span>'
        for size in (5, 6, 7, 8, 9, 10, 11, 12, 14, 17, 20, 24, 36, 48, 72)
    )
    markup = (
        "<h1>Multifora Привет</h1><p><strong>Bold</strong> <em>Italic</em> "
        '<u>underline</u> <span style="color:#aabbcc">color</span> <code>code</code></p>'
        + sizes
        + "<ul><li>List</li></ul><table><tr><td>Table</td><td>Cell</td></tr></table>"
        '<p><img src="sample.png"><img src="sample.jpg"><img src="sample.pdf"></p>'
    )
    return build_tex(PdfLayout(markup=markup, assets=assets))


def _compile(executable: Path, work: Path, cache: Path, *, offline: bool):
    environment = os.environ.copy()
    environment["TECTONIC_CACHE_DIR"] = str(cache)
    args = [
        str(executable),
        "--untrusted",
        *(["--only-cached"] if offline else []),
        "--outdir",
        str(work),
        str(work / "document.tex"),
    ]
    result = subprocess.run(args, cwd=work, env=environment, capture_output=True, timeout=900, check=False)
    output = work / "document.pdf"
    if result.returncode or not output.is_file() or not output.stat().st_size:
        detail = result.stderr.decode("utf-8", errors="replace")[-4000:]
        raise RuntimeError("Tectonic не подготовил ресурсы" + (f":\n{detail}" if detail else ""))


def prepare(executable: Path, destination: Path, initial_cache: Path | None = None) -> None:
    executable = executable.resolve()
    destination = destination.resolve()
    if not executable.is_file():
        raise FileNotFoundError(f"Не найден Tectonic: {executable}")
    if destination.exists():
        raise FileExistsError(f"Каталог кэша уже существует: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    source, assets = _sample()
    with tempfile.TemporaryDirectory(prefix="tectonic-prepare-", dir=destination.parent) as folder:
        work = Path(folder) / "work"
        seed = Path(folder) / "seed"
        work.mkdir()
        if initial_cache is not None:
            shutil.copytree(initial_cache, seed)
            (seed / ".multifora-cache-id").unlink(missing_ok=True)
        else:
            seed.mkdir()
        (work / "document.tex").write_text(source, encoding="utf-8")
        for name, data in assets.items():
            (work / name).write_bytes(data)
        print("Подготовка ресурсов Tectonic; может потребоваться подключение к интернету...", flush=True)
        _compile(executable, work, seed, offline=False)
        (work / "document.pdf").unlink()
        if FONT_CHOICE not in source:
            raise RuntimeError("Не удалось подготовить проверку резервного шрифта")
        (work / "document.tex").write_text(source.replace(FONT_CHOICE, ""), encoding="utf-8")
        _compile(executable, work, seed, offline=False)
        (work / "document.pdf").unlink()
        # Проверяем копию, чтобы сборка не зависела от системного кэша.
        offline_cache = Path(folder) / "offline-cache"
        shutil.copytree(seed, offline_cache)
        print("Проверка автономной работы Tectonic...", flush=True)
        _compile(executable, work, offline_cache, offline=True)
        (work / "document.pdf").unlink()
        (work / "document.tex").write_text(source, encoding="utf-8")
        _compile(executable, work, offline_cache, offline=True)
        for lock in seed.rglob("*.lock"):
            lock.unlink()
        digest = hashlib.sha256()
        for path in sorted(p for p in seed.rglob("*") if p.is_file() and not p.name.endswith(".lock")):
            digest.update(path.relative_to(seed).as_posix().encode("utf-8"))
            with path.open("rb") as stream:
                for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                    digest.update(chunk)
        (seed / ".multifora-cache-id").write_text(digest.hexdigest(), encoding="ascii")
        os.rename(seed, destination)


if __name__ == "__main__":
    if len(sys.argv) not in (3, 4):
        raise SystemExit("Использование: prepare_tectonic_cache.py TECTONIC CACHE_DIRECTORY [INITIAL_CACHE]")
    try:
        prepare(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]) if len(sys.argv) == 4 else None)
    except (OSError, RuntimeError, subprocess.TimeoutExpired) as error:
        raise SystemExit(f"Ошибка подготовки Tectonic: {error}") from error
