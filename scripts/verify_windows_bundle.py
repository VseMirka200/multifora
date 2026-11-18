"""Проверяет необходимые файлы переносимой сборки."""

import argparse
from pathlib import Path

REQUIRED = (
    "Multifora.exe",
    "bin/wordcraft/wordcraft-cli.exe",
    "bin/pdfcraft/pdfcraft-cli.exe",
    "_internal/assets/icon.ico",
    "_internal/docxcompose/templates/custom.xml",
    "_internal/PySide6/plugins/platforms/qwindows.dll",
    "_internal/PySide6/plugins/platforms/qoffscreen.dll",
)
EXCLUDED = {
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


def check_bundle(bundle):
    bundle = Path(bundle)
    errors = [name for name in REQUIRED if not (bundle / name).is_file() or (bundle / name).stat().st_size == 0]
    if not (bundle / "_internal").is_dir():
        errors.append("_internal/")
    errors.extend(
        "unexpected Qt runtime binary: " + str(path.relative_to(bundle)).replace("/", "\\")
        for path in (bundle / "_internal" / "PySide6").rglob("*")
        if path.is_file() and path.name.lower() in EXCLUDED
    )
    return errors


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--bundle", required=True)
    args = parser.parse_args()
    errors = check_bundle(args.bundle)
    for error in errors:
        print(error)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
