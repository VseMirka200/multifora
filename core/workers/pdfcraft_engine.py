"""Run PDFCraft exports through its isolated command-line process."""

import json
import shutil
import sys
import tempfile
from pathlib import Path

from core.workers.atomic_output import atomic_output_path
from core.workers.engine_policy import adaptive_timeout
from core.workers.office_engine import _run


class PdfCraftUnavailableError(RuntimeError):
    """The bundled PDFCraft executable is unavailable."""


def find_pdfcraft():
    root = (
        Path(sys.executable).resolve().parent
        if getattr(sys, "frozen", False)
        else Path(__file__).resolve().parents[2]
    )
    executable = root / "bin" / "pdfcraft" / "pdfcraft-cli.exe"
    return str(executable) if executable.is_file() else None


def export_pdf(source, destination, target, should_cancel):
    executable = find_pdfcraft()
    if not executable:
        raise PdfCraftUnavailableError("Встроенный движок PDFCraft не найден. Переустановите Мультифору.")
    if should_cancel():
        raise InterruptedError("Конвертация отменена")
    source = Path(source).resolve()
    if target not in {"DOCX", "TXT"}:
        raise ValueError(f"Неподдерживаемый формат: {target}")
    with tempfile.TemporaryDirectory(prefix="multifora_pdfcraft_") as folder:
        directory = Path(folder)
        output = directory / ("result." + target.lower())
        tool = "doc_export_office" if target == "DOCX" else "doc_export_text"
        steps = [
            {"tool": "doc_open", "args": {"path": str(source)}},
            {"tool": tool, "args": {"doc": 1, "path": str(output)}},
        ]
        script = directory / "steps.json"
        script.write_text(json.dumps(steps, ensure_ascii=False), encoding="utf-8")
        _run([executable, "run", "--script", str(script), "--report"], directory, should_cancel,
             adaptive_timeout(source.stat().st_size), None)
        report = json.loads((directory / "office.log").read_text(encoding="utf-8-sig"))
        if not report.get("ok") or not output.is_file() or (target != "TXT" and output.stat().st_size == 0):
            raise RuntimeError("PDFCraft не создал выходной файл")
        for step in report.get("steps", []):
            for result in step.get("result", []):
                if isinstance(result, dict) and result.get("truncated"):
                    raise RuntimeError("PDFCraft не смог полностью преобразовать документ")
        with atomic_output_path(destination) as temporary:
            shutil.copyfile(output, temporary)
            if should_cancel():
                raise InterruptedError("Конвертация отменена")


def combine_pdfs(sources, destination, should_cancel):
    executable = find_pdfcraft()
    if not executable:
        raise PdfCraftUnavailableError("Встроенный движок PDFCraft не найден. Переустановите Мультифору.")
    if should_cancel():
        raise InterruptedError("Объединение отменено")
    sources = [Path(source).resolve() for source in sources]
    with tempfile.TemporaryDirectory(prefix="multifora_pdfcraft_") as folder:
        directory = Path(folder)
        output = directory / "combined.pdf"
        _run([executable, "combine", *map(str, sources), "--out", str(output)], directory, should_cancel,
             adaptive_timeout(sum(source.stat().st_size for source in sources)), None)
        if not output.is_file() or output.stat().st_size == 0:
            raise RuntimeError("PDFCraft не создал выходной файл")
        with output.open("rb") as stream:
            if stream.read(5) != b"%PDF-":
                raise RuntimeError("PDFCraft создал некорректный PDF")
        with atomic_output_path(destination) as temporary:
            shutil.copyfile(output, temporary)
            if should_cancel():
                raise InterruptedError("Объединение отменено")


def render_pdf_pages(source, output_dir, should_cancel):
    executable = find_pdfcraft()
    if not executable:
        raise PdfCraftUnavailableError("Встроенный движок PDFCraft не найден. Переустановите Мультифору.")
    source = Path(source).resolve()
    output_dir = Path(output_dir).resolve()
    with tempfile.TemporaryDirectory(prefix="multifora_pdfcraft_") as folder:
        directory = Path(folder)
        script = directory / "steps.json"
        steps = [
            {"tool": "doc_open", "args": {"path": str(source)}},
            {"tool": "doc_export_images", "args": {"doc": 1, "folder": str(output_dir), "format": "png", "dpi": 200}},
        ]
        script.write_text(json.dumps(steps, ensure_ascii=False), encoding="utf-8")
        _run([executable, "run", "--script", str(script), "--report"], directory, should_cancel,
             adaptive_timeout(source.stat().st_size), None)
        report = json.loads((directory / "office.log").read_text(encoding="utf-8-sig"))
        if not report.get("ok"):
            raise RuntimeError("PDFCraft не смог преобразовать страницы")
        pages = sorted(output_dir.glob("*.png"))
        if not pages:
            raise RuntimeError("PDFCraft не создал изображения страниц")
        return pages


def optimize_pdf(source, destination, settings, should_cancel):
    executable = find_pdfcraft()
    if not executable:
        raise PdfCraftUnavailableError("Встроенный движок PDFCraft не найден. Переустановите Мультифору.")
    source = Path(source).resolve()
    with tempfile.TemporaryDirectory(prefix="multifora_pdfcraft_") as folder:
        directory = Path(folder)
        output = directory / "optimized.pdf"
        script = directory / "steps.json"
        color = {
            "downsample": True,
            "ppi": settings["color_resolution"],
            "above_ppi": int(settings["color_resolution"] * 1.5),
            "compression": "jpeg",
            "quality": settings["jpeg_quality"],
        }
        gray = {**color, "ppi": settings["gray_resolution"], "above_ppi": int(settings["gray_resolution"] * 1.5)}
        steps = [
            {"tool": "doc_open", "args": {"path": str(source)}},
            {"tool": "doc_optimize", "args": {"doc": 1, "path": str(output), "color": color, "gray": gray}},
        ]
        script.write_text(json.dumps(steps, ensure_ascii=False), encoding="utf-8")
        _run([executable, "run", "--script", str(script), "--report"], directory, should_cancel,
             adaptive_timeout(source.stat().st_size), None)
        report = json.loads((directory / "office.log").read_text(encoding="utf-8-sig"))
        if not report.get("ok") or not output.is_file() or output.stat().st_size == 0:
            raise RuntimeError("PDFCraft не смог сжать PDF")
        with output.open("rb") as stream:
            if stream.read(5) != b"%PDF-":
                raise RuntimeError("PDFCraft создал некорректный PDF")
        with atomic_output_path(destination) as temporary:
            shutil.copyfile(output, temporary)
            if should_cancel():
                raise InterruptedError("Сжатие отменено")
