"""Сравнивает появление окна и первую конвертацию из исходников в Windows."""

import argparse
import json
import os
import struct
import subprocess
import sys
from pathlib import Path
from statistics import median
from tempfile import TemporaryDirectory
from time import perf_counter_ns
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def _write_bitmap(path: Path) -> None:
    header = struct.pack("<2sIHHI", b"BM", 58, 0, 0, 54)
    bitmap_info = struct.pack("<IiiHHIIiiII", 40, 1, 1, 1, 24, 0, 4, 0, 0, 0, 0)
    path.write_bytes(header + bitmap_info + bytes((0, 0, 255, 0)))


def _sample(tree: Path, work: Path, started: int, preload: bool) -> dict[str, float]:
    sys.path.insert(0, str(tree))
    os.environ["USERPROFILE"] = str(work)
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication

    import multifora_start as startup
    from core.operation_requests import ConversionRequest

    if (tree / "core/file_models.py").is_file():
        from core.file_models import FileItem
    else:
        from app.core.models import FileItem

    timestamps = {}
    errors = []
    window = None

    class BenchmarkWindow(startup.MultiforaMainWindow):
        def __init__(self):
            super().__init__()
            nonlocal window
            window = self

        def paintEvent(self, event):
            super().paintEvent(event)
            if "visible" not in timestamps:
                timestamps["visible"] = perf_counter_ns()
                QTimer.singleShot(0, self.start_sample)

        def _preload_file_worker_async(self):
            if preload:
                super()._preload_file_worker_async()

        def start_sample(self):
            source = FileItem(str(work / "sample.bmp"))
            request = ConversionRequest("auto_image", "PNG", "alongside", "")
            if not self._start_operation(request, [source]):
                errors.append("Первая операция отклонена")
                QApplication.quit()
                return
            timestamps["worker_ready"] = perf_counter_ns()

        def on_operation_error(self, message):
            errors.append(message)

        def on_operation_finished(self, result):
            timestamps["result"] = perf_counter_ns()
            errors.extend(str(error) for error in result.errors)
            if len(result.new_files) != 1 or not (work / "sample.png").is_file():
                errors.append("Файл результата отсутствует")
            QApplication.quit()

    # Изолируем системную регистрацию и IPC, сохраняя обычные main и _start_operation.
    with (
        patch.object(startup, "MultiforaMainWindow", BenchmarkWindow),
        patch.object(startup, "collect_startup_files", return_value=[]),
        patch.object(startup, "is_first_instance", return_value=True),
        patch.object(startup, "_ensure_ipc_token"),
        patch.object(BenchmarkWindow, "create_ipc_server"),
        patch.object(BenchmarkWindow, "check_updates_on_startup"),
        patch.object(BenchmarkWindow, "process_startup_queue"),
        patch.object(sys, "argv", [str(tree / "multifora_start.py")]),
    ):
        try:
            startup.main()
        except SystemExit as error:
            if error.code:
                raise
        finally:
            if window is not None and window.file_worker is not None:
                window.file_worker.wait(5000)
    if errors or "result" not in timestamps:
        raise RuntimeError(f"Первая конвертация не завершилась: {errors}")

    return {
        "window_ms": (timestamps["visible"] - started) / 1e6,
        "first_operation_ready_ms": (timestamps["worker_ready"] - started) / 1e6,
        "first_operation_result_ms": (timestamps["result"] - started) / 1e6,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    comparison = parser.add_mutually_exclusive_group()
    comparison.add_argument("--compare-to", type=Path)
    comparison.add_argument("--compare-preload", action="store_true")
    parser.add_argument("--runs", type=int, default=9)
    parser.add_argument("--sample", nargs=4, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if sys.platform != "win32":
        parser.error("Этот сценарий измеряется в Windows.")
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    if args.sample:
        tree, work, started, preload = args.sample
        print(json.dumps(_sample(Path(tree), Path(work), int(started), preload == "1")))
        return
    if (args.compare_to is None and not args.compare_preload) or args.runs < 1:
        parser.error("Укажите --compare-to или --compare-preload и положительное число повторов.")

    if args.compare_preload:
        variants = (("preload", ROOT, "1"), ("lazy", ROOT, "0"))
    else:
        variants = (("baseline", args.compare_to.resolve(strict=True), "1"), ("current", ROOT, "1"))
    samples = {label: [] for label, _tree, _preload in variants}
    with TemporaryDirectory(prefix="multifora-startup-") as directory:
        for attempt in range(args.runs + 1):
            for label, tree, preload in variants if attempt % 2 == 0 else reversed(variants):
                work = Path(directory) / f"{label}-{attempt}"
                work.mkdir()
                _write_bitmap(work / "sample.bmp")
                output = subprocess.check_output(
                    [sys.executable, __file__, "--sample", str(tree), str(work), str(perf_counter_ns()), preload],
                    text=True,
                    timeout=20,
                )
                if attempt:
                    samples[label].append(json.loads(output))

    summary = {
        label: {key: round(median(sample[key] for sample in trials), 2) for key in trials[0]}
        for label, trials in samples.items()
    }
    print(json.dumps({"median_ms": summary, "samples": samples}, indent=2))


if __name__ == "__main__":
    main()
