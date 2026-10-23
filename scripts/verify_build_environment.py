"""Fail before packaging if the Windows build environment has drifted."""

from __future__ import annotations

import argparse
import struct
import sys
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path


def check_python() -> list[str]:
    errors = []
    if sys.platform != "win32":
        errors.append("Windows is required for the Windows build.")
    if sys.version_info[:2] != (3, 11):
        errors.append(f"Python 3.11 is required; running {sys.version.split()[0]}.")
    if struct.calcsize("P") != 8:
        errors.append("64-bit Python is required.")
    return errors


def check_packages(requirements: Path) -> list[str]:
    errors = []
    for line in requirements.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith(("#", "-r ")):
            continue
        name, expected = line.split("==", 1)
        try:
            actual = version(name)
        except PackageNotFoundError:
            errors.append(f"{name}=={expected} is not installed.")
            continue
        if actual != expected:
            errors.append(f"{name}: expected {expected}, installed {actual}.")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--python-only", action="store_true")
    args = parser.parse_args()
    errors = check_python()
    if not args.python_only:
        errors += check_packages(Path(__file__).resolve().parents[1] / "requirements-build.txt")
    if errors:
        print("Build environment is not supported:", file=sys.stderr)
        print("\n".join(f"  - {error}" for error in errors), file=sys.stderr)
        return 1
    print("Build environment verified: Windows x64 / Python 3.11")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
