"""Validate the frozen app and bundled ArtCraft engine/license layout."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


def check_bundle(bundle: Path) -> list[str]:
    missing = []
    required = (
        "Multifora.exe",
        "bin/native/pdfcraft-cli.exe",
        "bin/native/photocraft-cli.exe",
        "bin/native/deckcraft-cli.exe",
        "bin/native/THIRD_PARTY_NOTICES.txt",
        "bin/native/licenses/pdfcraft/LICENSE-MIT",
        "bin/native/licenses/pdfcraft/LICENSE-APACHE",
        "bin/native/licenses/pdfcraft/NOTICE",
        "bin/native/licenses/pdfcraft/ATTRIBUTION.md",
        "bin/native/licenses/photocraft/LICENSE-MIT",
        "bin/native/licenses/photocraft/LICENSE-APACHE",
        "bin/native/licenses/photocraft/NOTICE",
        "bin/native/licenses/photocraft/ATTRIBUTION.md",
        "bin/native/licenses/deckcraft/LICENSE-MIT",
        "bin/native/licenses/deckcraft/LICENSE-APACHE",
        "bin/native/licenses/deckcraft/NOTICE",
        "bin/native/licenses/deckcraft/ATTRIBUTION.md",
    )
    for relative in required:
        path = bundle / relative
        if not path.is_file() or path.stat().st_size == 0:
            missing.append(relative)

    internal = bundle / "_internal"
    if not internal.is_dir():
        missing.append("_internal/")
    else:
        for name in ("icon.ico",):
            if not any(internal.rglob(name)):
                missing.append(f"_internal/**/{name}")
        for name in ("qwindows.dll", "qoffscreen.dll"):
            if not any(internal.rglob(name)):
                missing.append(f"_internal/**/{name}")

    for obsolete in (
        "bin/gswin64/gswin64c.exe",
        "bin/pandoc/pandoc.exe",
        "bin/tectonic/tectonic.exe",
        "_internal/docxcompose",
        "_internal/pdf2docx",
        "_internal/pymupdf",
        "_internal/odf",
    ):
        if (bundle / obsolete).exists():
            missing.append(f"obsolete legacy backend still bundled: {obsolete}")

    excluded_qt_binaries = {
        "qpdf.dll", "qtvirtualkeyboardplugin.dll", "qt6pdf.dll",
        "qt6virtualkeyboard.dll", "qt6quick.dll", "qt6qml.dll",
        "qt6qmlmeta.dll", "qt6qmlmodels.dll", "qt6qmlworkerscript.dll",
    }
    if internal.is_dir():
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
    print(f"ArtCraft engine bundle and license files verified: {args.bundle}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
