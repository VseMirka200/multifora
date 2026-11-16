"""Проверяет Python и закреплённые версии для Windows-сборки."""

import argparse
import struct
import sys
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path


def check_python():
    errors = []
    if sys.version_info[:2] != (3, 15):
        errors.append("Python 3.15 is required.")
    if sys.platform != "win32":
        errors.append("Windows is required.")
    if struct.calcsize("P") != 8:
        errors.append("64-bit Python is required.")
    return errors


def check_packages(path):
    errors = []
    path = Path(path)
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("-r "):
            errors.extend(check_packages(path.parent / line[3:].strip()))
            continue
        if "==" not in line:
            errors.append(f"Unsupported requirement: {line}.")
            continue
        name, expected = line.split("==", 1)
        try:
            installed = version(name)
        except PackageNotFoundError:
            errors.append(f"{line} is not installed.")
            continue
        if installed != expected:
            errors.append(f"{name}: expected {expected}, installed {installed}.")
    return errors


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--python-only", action="store_true")
    parser.add_argument("--requirements", action="append", default=[])
    args = parser.parse_args()
    errors = check_python()
    if not args.python_only:
        for path in args.requirements or ["requirements-runtime.txt", "requirements-build.txt"]:
            errors.extend(check_packages(path))
    for error in errors:
        print(error, file=sys.stderr)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
