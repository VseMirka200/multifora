"""Небольшие PDF-файлы для интеграционных тестов Ghostscript."""

import subprocess

from app.core.deps import ensure_ghostscript_detected


def run(*arguments):
    found, executable = ensure_ghostscript_detected()
    if not found:
        raise RuntimeError("Ghostscript is required")
    subprocess.run([executable, "-q", "-dBATCH", "-dNOPAUSE", *map(str, arguments)], check=True, capture_output=True)


def create_pdf(path, labels):
    pages = []
    for text in labels:
        safe = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        pages.append(f"/Helvetica findfont 10 scalefont setfont 5 36 moveto ({safe}) show showpage")
    run("-sDEVICE=pdfwrite", "-r72", "-g72x72", f"-sOutputFile={path}", "-c", " ".join(pages))


def read_pdf_text(path, output):
    run("-sDEVICE=txtwrite", "-dTextFormat=3", f"-sOutputFile={output}", path)
    return output.read_text(encoding="utf-8")
