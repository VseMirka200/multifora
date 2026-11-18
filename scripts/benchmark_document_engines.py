"""Compare local engine trees with identical synthetic inputs on Windows."""

import argparse
import ctypes
import json
import random
import subprocess
import sys
from pathlib import Path
from statistics import median
from tempfile import TemporaryDirectory
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
CASES = ("text", "mixed", "render", "compression", "layout", "batch")


def _peak_memory():
    class MemoryCounters(ctypes.Structure):
        _fields_ = [
            ("size", ctypes.c_ulong), ("faults", ctypes.c_ulong),
            *((name, ctypes.c_size_t) for name in (
                "peak", "working_set", "quota_peak_paged", "quota_paged",
                "quota_peak_nonpaged", "quota_nonpaged", "pagefile", "peak_pagefile",
            )),
        ]

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.GetCurrentProcess.restype = ctypes.c_void_p
    psapi = ctypes.WinDLL("psapi", use_last_error=True)
    psapi.GetProcessMemoryInfo.argtypes = [ctypes.c_void_p, ctypes.POINTER(MemoryCounters), ctypes.c_ulong]
    counters = MemoryCounters()
    counters.size = ctypes.sizeof(counters)
    if not psapi.GetProcessMemoryInfo(kernel.GetCurrentProcess(), ctypes.byref(counters), counters.size):
        raise ctypes.WinError(ctypes.get_last_error())
    return counters.peak


def _fixtures(folder):
    from docx import Document
    from docx.enum.section import WD_ORIENT
    from docx.shared import Inches
    from PIL import Image
    from reportlab.lib.utils import ImageReader
    from reportlab.pdfgen.canvas import Canvas

    rng = random.Random(272)
    picture = Image.frombytes("RGB", (1600, 1200), rng.randbytes(1600 * 1200 * 3))
    png = folder / "picture.png"
    picture.save(png)
    image = ImageReader(picture)
    pdf = Canvas(str(folder / "text.pdf"))
    for index in range(100):
        text = pdf.beginText(48, 770)
        for line in range(45):
            text.textLine(f"Page {index + 1} line {line + 1} searchable synthetic document benchmark")
        pdf.drawText(text)
        pdf.showPage()
    pdf.save()

    for file, count in (("mixed", 12), ("render", 8), ("compression", 4)):
        pdf = Canvas(str(folder / f"{file}.pdf"))
        for index in range(count):
            pdf.drawImage(image, 48, 120, width=360, height=270)
            if file == "mixed" and index % 3:
                pdf.drawString(48, 740, f"Searchable page {index + 1}")
            pdf.showPage()
        pdf.save()
    document = Document()
    document.add_paragraph("First portrait section")
    section = document.add_section()
    section.orientation = WD_ORIENT.LANDSCAPE
    section.page_width, section.page_height = Inches(11), Inches(8.5)
    document.add_picture(str(png), width=Inches(7))
    section = document.add_section()
    section.orientation = WD_ORIENT.PORTRAIT
    section.page_width, section.page_height = Inches(8.5), Inches(11)
    document.add_paragraph("Second portrait section")
    document.save(folder / "layout.docx")


def _sample(engine, inputs, output, case):
    sys.path.insert(0, str(engine))
    from core.workers.office_engine import run_office
    from core.workers.pdfcraft_engine import export_pdf, optimize_pdf, render_pdf_pages

    def active():
        return False

    start = perf_counter()
    if case in {"text", "batch"}:
        export_pdf(inputs / "text.pdf", output / "export.txt", "TXT", active)
    if case in {"mixed", "batch"}:
        export_pdf(inputs / "mixed.pdf", output / "mixed.docx", "DOCX", active)
    if case == "render":
        render_pdf_pages(inputs / "render.pdf", output, active)
    if case in {"compression", "batch"}:
        settings = {"color_resolution": 150, "gray_resolution": 150, "jpeg_quality": 75}
        optimize_pdf(inputs / "compression.pdf", output / "compressed.pdf", settings, active)
    if case == "layout":
        run_office(inputs / "layout.docx", output / "layout.pdf", "PDF", active)
    return {
        "seconds": perf_counter() - start,
        "peak_bytes": _peak_memory(),
        "output_bytes": sum(path.stat().st_size for path in output.iterdir()),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compare-to", type=Path)
    parser.add_argument("--runs", type=int, default=5)
    parser.add_argument("--sample", nargs=4, metavar=("ENGINE", "INPUTS", "OUTPUT", "CASE"))
    args = parser.parse_args()
    if sys.platform != "win32":
        parser.error("This benchmark measures the Windows working set.")
    if args.sample:
        engine, inputs, output, case = args.sample
        print(json.dumps(_sample(Path(engine), Path(inputs), Path(output), case)))
        return
    if not args.compare_to or args.runs < 1:
        parser.error("Specify --compare-to with an engine tree and at least one run.")
    baseline = args.compare_to.resolve(strict=True)
    results = {}
    with TemporaryDirectory(prefix="multifora-benchmark-") as directory:
        folder = Path(directory)
        inputs = folder / "inputs"
        inputs.mkdir()
        _fixtures(inputs)
        for case in CASES:
            samples = {"baseline": [], "current": []}
            for iteration in range(args.runs):
                order = (("baseline", baseline), ("current", ROOT))
                for label, engine in (order if iteration % 2 == 0 else reversed(order)):
                    output = folder / f"{case}-{iteration}-{label}"
                    output.mkdir()
                    completed = subprocess.run(
                        [sys.executable, __file__, "--sample", str(engine), str(inputs), str(output), case],
                        check=True, stdout=subprocess.PIPE, text=True,
                    )
                    samples[label].append(json.loads(completed.stdout))
            results[case] = {
                label: {metric: median(row[metric] for row in rows) for metric in rows[0]}
                for label, rows in samples.items()
            }
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
