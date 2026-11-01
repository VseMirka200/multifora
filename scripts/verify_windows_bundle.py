"""Validate the layout of a frozen/installed Windows build.

Runs without third-party modules; this lets CI check the packaging itself.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def check_bundle(bundle: Path) -> list[str]:
    # PyMuPDF data is collected by Multifora.spec. Its optional layout resources
    # vary across releases, so no version-specific model filename is required.
    missing = []
    for relative in (
        "Multifora.exe",
        "bin/gswin64/gswin64c.exe",
        "bin/gswin64/gsdll64.dll",
        "bin/pandoc/pandoc.exe",
        "bin/tectonic/tectonic.exe",
        "_internal/docxcompose/templates/custom.xml",
    ):
        path = bundle / relative
        if not path.is_file() or path.stat().st_size == 0:
            missing.append(relative)

    internal = bundle / "_internal"
    if not internal.is_dir():
        missing.append("_internal/")
    else:
        missing.extend(
            f"_internal/**/{name}"
            for name in ("icon.ico",)
            if not any(internal.rglob(name))
        )
        missing.extend(
            f"_internal/**/{name}"
            for name in ("qwindows.dll", "qoffscreen.dll")
            if not any(internal.rglob(name))
        )
        excluded_qt_binaries = {
            "qpdf.dll",
            "qtvirtualkeyboardplugin.dll",
            "qt6pdf.dll",
            "qt6virtualkeyboard.dll",
            "qt6quick.dll",
            "qt6qml.dll",
            "qt6qmlmeta.dll",
            "qt6qmlmodels.dll",
            "qt6qmlworkerscript.dll",
        }
        missing.extend(
            f"unexpected Qt runtime binary: {path.relative_to(bundle)}"
            for path in internal.rglob("*")
            if path.is_file() and path.name.lower() in excluded_qt_binaries
        )
    return missing


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, required=True)
    args = parser.parse_args(argv)
    missing = check_bundle(args.bundle)
    if missing:
        print("Incomplete Windows bundle:", file=sys.stderr)
        for item in missing:
            print(f"  - {item}", file=sys.stderr)
        return 1
    print(f"Bundle contents verified: {args.bundle}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
