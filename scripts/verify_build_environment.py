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


def _read_requirements(
    requirements: Path, seen: set[Path] | None = None
) -> list[tuple[str, str]]:
    requirements = requirements.resolve()
    seen = set() if seen is None else seen
    if requirements in seen:
        return []
    seen.add(requirements)

    packages = []
    for line in requirements.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith(("-r ", "--requirement ")):
            include = line.split(maxsplit=1)[1]
            packages.extend(_read_requirements(requirements.parent / include, seen))
            continue
        name, expected = line.split("==", 1)
        packages.append((name, expected))
    return packages


def check_packages(requirements: Path) -> list[str]:
    errors = []
    for name, expected in _read_requirements(requirements):
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
    parser.add_argument("--requirements", action="append", type=Path)
    args = parser.parse_args()
    errors = check_python()
    if not args.python_only:
        requirement_files = args.requirements or [
            Path(__file__).resolve().parents[1] / "requirements.txt"
        ]
        for requirements in requirement_files:
            errors += check_packages(requirements)
    if errors:
        print("Build environment is not supported:", file=sys.stderr)
        print("\n".join(f"  - {error}" for error in errors), file=sys.stderr)
        return 1
    print("Build environment verified: Windows x64 / Python 3.11")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
