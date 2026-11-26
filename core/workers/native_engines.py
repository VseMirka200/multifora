"""Native ArtCraft conversion engines used by Multifora.

All document/image conversion, PDF composition and optimization is delegated to the
upstream PdfCraft, PhotoCraft and DeckCraft command-line engines. Python only routes
files, manages temporary outputs and propagates cancellation.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Callable

from core.workers.atomic_output import atomic_output_path


ENGINE_FILES = {
    "pdf": "pdfcraft-cli.exe",
    "photo": "photocraft-cli.exe",
    "deck": "deckcraft-cli.exe",
}


class NativeEngineError(RuntimeError):
    """A native conversion engine is missing or rejected an operation."""


def _candidate_roots() -> list[Path]:
    roots: list[Path] = []
    executable = Path(sys.argv[0]).resolve() if sys.argv and sys.argv[0] else None
    if executable:
        roots.append(executable.parent)
    frozen_root = getattr(sys, "_MEIPASS", None)
    if frozen_root:
        roots.append(Path(frozen_root))
    roots.append(Path(__file__).resolve().parents[2])
    unique: list[Path] = []
    for root in roots:
        if root not in unique:
            unique.append(root)
    return unique


def engine_path(engine: str) -> str:
    if engine not in ENGINE_FILES:
        raise NativeEngineError(f"Неизвестный движок ArtCraft: {engine}")
    env_name = {
        "pdf": "MULTIFORA_PDFCRAFT_CLI",
        "photo": "MULTIFORA_PHOTOCRAFT_CLI",
        "deck": "MULTIFORA_DECKCRAFT_CLI",
    }[engine]
    override = os.environ.get(env_name)
    if override and Path(override).is_file():
        return str(Path(override).resolve())
    filename = ENGINE_FILES[engine]
    for root in _candidate_roots():
        for candidate in (root / "bin" / "native" / filename, root / filename):
            if candidate.is_file():
                return str(candidate)
    resolved = shutil.which(filename) or shutil.which(filename.removesuffix(".exe"))
    if resolved:
        return resolved
    raise NativeEngineError(
        f"Не найден {filename}. Выполните scripts\\build_native_engines.ps1 "
        "или переустановите Multifora с комплектом движков ArtCraft."
    )


def run_engine(
    engine: str,
    arguments: list[str],
    *,
    cancel_check: Callable[[], bool] | None = None,
    cancel_owner=None,
) -> str:
    executable = engine_path(engine)
    command = [executable, *map(str, arguments)]
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        creationflags=flags,
    )
    cancel_action = process.terminate
    register = getattr(cancel_owner, "_set_active_cancel_action", None)
    clear = getattr(cancel_owner, "_clear_active_cancel_action", None)
    if callable(register):
        register(cancel_action)
    try:
        while True:
            try:
                stdout, stderr = process.communicate(timeout=0.2)
                break
            except subprocess.TimeoutExpired:
                if cancel_check and cancel_check():
                    process.terminate()
                    try:
                        stdout, stderr = process.communicate(timeout=1.0)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        stdout, stderr = process.communicate()
                    raise InterruptedError("Операция отменена пользователем")
        if process.returncode:
            detail = (stderr or stdout or "движок не сообщил причину ошибки").strip()
            raise NativeEngineError(
                f"{Path(executable).name}: {detail[-4000:]}"
            )
        return stdout
    finally:
        if callable(clear):
            clear(cancel_action)


def _assert_output(path: str) -> None:
    if not os.path.isfile(path) or os.path.getsize(path) == 0:
        raise NativeEngineError("Движок не создал выходной файл")


def _pdf_page_count(path: str, owner) -> int:
    output = run_engine(
        "pdf", ["info", path], cancel_check=owner._should_cancel, cancel_owner=owner
    )
    try:
        data = json.loads(output)
    except json.JSONDecodeError as error:
        raise NativeEngineError("PdfCraft вернул некорректный отчёт info") from error
    pages = data.get("pages")
    if isinstance(pages, list):
        count = len(pages)
    elif isinstance(pages, int):
        count = pages
    else:
        count = data.get("page_count") or data.get("pageCount")
    if not isinstance(count, int) or count < 1:
        raise NativeEngineError("PdfCraft не сообщил количество страниц PDF")
    return count


def _pdf_export_office(source: str, target: str, output: str, owner) -> str:
    steps = [
        {"tool": "doc_open", "args": {"path": source}},
        {"tool": "doc_export_office", "args": {"doc": 1, "path": output}},
    ]
    with tempfile.TemporaryDirectory(prefix="multifora-pdfcraft-") as directory:
        script = Path(directory, "export.json")
        script.write_text(json.dumps(steps, ensure_ascii=False), encoding="utf-8")
        run_engine(
            "pdf", ["run", "--script", str(script), "--report"],
            cancel_check=owner._should_cancel, cancel_owner=owner,
        )
    _assert_output(output)
    return output


def _pdf_to_images(file, source: str, output_path: str, owner) -> list[str]:
    extension = Path(output_path).suffix.lower()
    if extension not in {".png", ".jpg", ".jpeg", ".tif", ".tiff"}:
        raise NativeEngineError(
            "PdfCraft экспортирует страницы PDF в PNG, JPG или TIFF. "
            "Выберите один из этих форматов."
        )
    page_count = _pdf_page_count(source, owner)
    base = Path(output_path)
    outputs: list[str] = []
    try:
        for page in range(1, page_count + 1):
            if owner._should_cancel():
                raise InterruptedError("Операция отменена пользователем")
            if page == 1:
                destination = output_path
            else:
                reference_path = str(base.with_name(f"{base.stem}_page_{page}{base.suffix}"))
                reference = type(file)(reference_path)
                destination = owner._conversion_output_path(
                    file, extension, reference_file=reference
                )
            with atomic_output_path(destination) as temporary:
                run_engine(
                    "pdf",
                    ["render", source, "--page", str(page), "--dpi", "200", "--out", temporary],
                    cancel_check=owner._should_cancel,
                    cancel_owner=owner,
                )
            outputs.append(destination)
            owner.progress.emit(int(page / page_count * 100))
        return outputs
    except Exception:
        for path in outputs:
            try:
                os.remove(path)
            except OSError:
                pass
        raise


def _image_to_pdf(source: str, output_path: str, owner) -> str:
    source_ext = Path(source).suffix.lower()
    pdfcraft_inputs = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".gif", ".bmp", ".jp2", ".j2k", ".jpx", ".pcx"}
    with tempfile.TemporaryDirectory(prefix="multifora-image-pdf-") as directory:
        input_for_pdf = source
        if source_ext not in pdfcraft_inputs:
            raster = str(Path(directory, "source.png"))
            run_engine(
                "photo", ["convert", source, raster],
                cancel_check=owner._should_cancel, cancel_owner=owner,
            )
            _assert_output(raster)
            input_for_pdf = raster
        run_engine(
            "pdf", ["batch", input_for_pdf, "--steps", "convert", "--out-dir", directory],
            cancel_check=owner._should_cancel, cancel_owner=owner,
        )
        generated = Path(directory, Path(input_for_pdf).stem + ".pdf")
        _assert_output(str(generated))
        with atomic_output_path(output_path) as temporary:
            shutil.copyfile(generated, temporary)
    return output_path


def convert_file(owner, file, target_format: str, output_path: str):
    source = str(file.path)
    source_ext = Path(source).suffix.lower()
    target_ext = Path(output_path).suffix.lower()
    target = str(target_format or "").upper()
    if owner._should_cancel():
        raise InterruptedError("Операция отменена пользователем")

    # DeckCraft owns PowerPoint/native deck conversion and presentation exports.
    if source_ext in {".pptx", ".deckcraft"}:
        if target_ext in {".pptx", ".potx", ".ppsx", ".deckcraft", ".pdf", ".png", ".jpg", ".jpeg", ".gif", ".txt", ".md", ".rtf"}:
            with atomic_output_path(output_path) as temporary:
                run_engine(
                    "deck", ["convert", source, temporary],
                    cancel_check=owner._should_cancel, cancel_owner=owner,
                )
            return output_path
        if target_ext in {".docx", ".html"}:
            with tempfile.TemporaryDirectory(prefix="multifora-deckcraft-") as directory:
                intermediate = str(Path(directory, "presentation.pdf"))
                run_engine(
                    "deck", ["convert", source, intermediate],
                    cancel_check=owner._should_cancel, cancel_owner=owner,
                )
                return _pdf_export_office(intermediate, target, output_path, owner)
        raise NativeEngineError(f"DeckCraft не поддерживает выходной формат {target_ext}")

    # PdfCraft exports editable office/text formats from PDF, and renders every PDF page.
    if source_ext == ".pdf":
        if target_ext in {".png", ".jpg", ".jpeg", ".tif", ".tiff"}:
            return _pdf_to_images(file, source, output_path, owner)
        if target_ext == ".txt":
            text = run_engine(
                "pdf", ["text", source],
                cancel_check=owner._should_cancel, cancel_owner=owner,
            )
            with atomic_output_path(output_path) as temporary:
                Path(temporary).write_text(text, encoding="utf-8")
            return output_path
        if target_ext in {".docx", ".pptx", ".html", ".rtf", ".md"}:
            return _pdf_export_office(source, target, output_path, owner)
        raise NativeEngineError(f"PdfCraft не поддерживает выходной формат {target_ext}")

    # PdfCraft's batch importer creates a standards-based PDF from text files.
    if source_ext in {".txt", ".text"} and target_ext == ".pdf":
        with tempfile.TemporaryDirectory(prefix="multifora-pdfcraft-") as directory:
            run_engine(
                "pdf", ["batch", source, "--steps", "convert", "--out-dir", directory],
                cancel_check=owner._should_cancel, cancel_owner=owner,
            )
            generated = Path(directory, Path(source).stem + ".pdf")
            _assert_output(str(generated))
            with atomic_output_path(output_path) as temporary:
                shutil.copyfile(generated, temporary)
        return output_path

    # Image-to-PDF uses PdfCraft's native PDF creator. PhotoCraft rasterizes
    # layered/read-only image sources first when PdfCraft has no direct importer.
    if target_ext == ".pdf":
        return _image_to_pdf(source, output_path, owner)

    # All other raster and layered image conversions are handled by PhotoCraft.
    quality_args = ["--quality", str(max(1, min(100, int(getattr(owner, "compression_level", 90)))))]
    with atomic_output_path(output_path) as temporary:
        args = ["convert", source, temporary]
        if target_ext in {".jpg", ".jpeg", ".webp"}:
            args.extend(quality_args)
        run_engine(
            "photo", args,
            cancel_check=owner._should_cancel, cancel_owner=owner,
        )
    return output_path


def merge_pdfs(owner, files, output_path: str) -> str:
    with atomic_output_path(output_path) as temporary:
        run_engine(
            "pdf",
            ["combine", *[str(file.path) for file in files], "--out", temporary],
            cancel_check=owner._should_cancel, cancel_owner=owner,
        )
    return output_path


def compress_pdf(owner, source: str, output_path: str, ppi: int, quality: int) -> str:
    with tempfile.TemporaryDirectory(prefix="multifora-pdf-optimize-") as directory:
        run_engine(
            "pdf",
            ["batch", source, "--steps", "optimize", "--out-dir", directory,
             "--ppi", str(ppi), "--quality", str(quality)],
            cancel_check=owner._should_cancel, cancel_owner=owner,
        )
        generated = Path(directory, Path(source).name)
        _assert_output(str(generated))
        with atomic_output_path(output_path) as temporary:
            shutil.copyfile(generated, temporary)
    return output_path


def compress_image(owner, source: str, output_path: str, quality: int) -> str:
    with atomic_output_path(output_path) as temporary:
        run_engine(
            "photo",
            ["convert", source, temporary, "--quality", str(max(1, min(100, int(quality))))],
            cancel_check=owner._should_cancel, cancel_owner=owner,
        )
    return output_path
