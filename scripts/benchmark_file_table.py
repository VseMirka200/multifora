"""Замеряет отзывчивость таблицы файлов на одинаковых синтетических данных."""

import argparse
import json
import os
import sys
from functools import partial
from pathlib import Path
from statistics import median
from time import perf_counter


def measure_table(runs: int, tree: Path) -> dict:
    from PySide6.QtWidgets import QApplication

    if (tree / "core/file_models.py").is_file():
        from core.file_models import FileItem
    else:
        from app.core.models import FileItem
    if (tree / "app/ui/file_table.py").is_file():
        from app.ui.file_table import FileListWidget
    else:
        from app.ui.ui_components import FileListWidget

    app = QApplication([])
    measurements = {}
    for count in (100, 1000, 5000, 10_000):
        files = [FileItem(f"bench/Отчёт-{index:05d}.pdf") for index in range(count)]
        for item in files:
            item.is_file = True
            item.file_type = "document"
        filtered = files[::2]
        durations = {"load": [], "filter": [], "check_all": []}
        table = FileListWidget()
        table.resize(900, 600)
        table.show()
        app.processEvents()
        for attempt in range(runs + 1):
            table.clearSelection()
            table.clear()
            for scenario, action in (
                ("load", partial(table.set_files, files)),
                ("filter", partial(table.set_files, filtered)),
                ("check_all", table.selectAll),
            ):
                start = perf_counter()
                action()
                app.processEvents()
                elapsed_ms = (perf_counter() - start) * 1000
                if attempt:
                    durations[scenario].append(round(elapsed_ms, 3))
        measurements[count] = {
            scenario: {"median_ms": median(samples), "samples_ms": samples}
            for scenario, samples in durations.items()
        }
        table.close()
    return measurements


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tree", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--runs", type=int, default=7)
    args = parser.parse_args()
    if args.runs < 1:
        parser.error("--runs must be positive")
    tree = args.tree.resolve(strict=True)
    sys.path.insert(0, str(tree))
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    print(json.dumps(measure_table(args.runs, tree), indent=2))


if __name__ == "__main__":
    main()
