"""Создаёт единый SVG-набор значков с подписями форматов.

Запуск из корня проекта: python scripts/generate_file_icons.py
Обновляет SVG-варианты; исходные ICO-изображения сохраняются.
"""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.core.conversion_formats import FILE_TYPE_EXTENSIONS


def main():
    destination = ROOT / "assets" / "files extension"
    destination.mkdir(parents=True, exist_ok=True)
    colors = {}

    def group(extensions, color):
        colors.update({extension.lstrip("."): color for extension in extensions})

    group(FILE_TYPE_EXTENSIONS["document"], "#1769d2")
    group(FILE_TYPE_EXTENSIONS["image"], "#7c3aed")
    group(FILE_TYPE_EXTENSIONS["archive"], "#9a6132")
    group("docx docm dot dotx dotm odt rtf".split(), "#1769d2")
    group("txt md markdown log csv tsv json xml yaml yml ini cfg toml sql py js ts css html htm bat ps1 sh".split(), "#667584")
    group("xls xlsx xlsm xlsb xlt xltx ods".split(), "#16834a")
    group("ppt pptx pptm pps ppsx pot potx odp".split(), "#f06422")
    group("mp3 wav flac aac m4a ogg opus wma aiff aif mid midi".split(), "#d92d7c")
    group("mp4 mkv avi mov webm wmv m4v mpg mpeg flv 3gp".split(), "#4a43d9")
    group("zip rar 7z tar gz bz2 xz tgz zst cab iso".split(), "#9a6132")
    group(FILE_TYPE_EXTENSIONS["document"], "#1769d2")
    colors["_unknown"] = "#667584"
    short_labels = {"markdown": "MD", "targa": "TGA"}
    count = 0
    for extension, color in sorted(colors.items()):
        label = "" if extension == "_unknown" else short_labels.get(extension, extension.upper())
        font_size = min(62, int(235 / max(1, len(label))))
        text = (
            f'<text x="128" y="186" text-anchor="middle" fill="#fff" '
            f'font-family="Arial, sans-serif" font-weight="700" font-size="{font_size}">{label}</text>'
            if label else ""
        )
        svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="256" height="256" viewBox="0 0 256 256">
  <path fill="{color}" d="M64 0H155L226 70V222Q226 256 192 256H64Q30 256 30 222V34Q30 0 64 0Z"/>
  <path fill="#fff" fill-opacity=".35" d="M155 0L226 70H155Z"/>
  {text}
</svg>
'''
        (destination / f"{extension}.svg").write_text(svg, encoding="utf-8")
        count += 1
    print(f"Updated {count} extension icons in {destination}")


if __name__ == "__main__":
    main()
