"""Создаёт общие цветные SVG-иконки типов файлов без подписей.

Запуск из корня проекта: python scripts/generate_file_icons.py
Обновляет восемь общих иконок категорий файлов.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    destination = ROOT / "assets" / "file_types"
    destination.mkdir(parents=True, exist_ok=True)
    colors = {
        "document": "#1769d2",
        "image": "#eab308",
        "spreadsheet": "#16834a",
        "presentation": "#f06422",
        "audio": "#d92d7c",
        "video": "#4a43d9",
        "archive": "#9a6132",
        "unknown": "#667584",
    }
    count = 0
    for category, color in colors.items():
        svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="256" height="256" viewBox="0 0 256 256">
  <path fill="{color}" d="M64 0H155L226 70V222Q226 256 192 256H64Q30 256 30 222V34Q30 0 64 0Z"/>
  <path fill="#fff" fill-opacity=".35" d="M155 0L226 70H155Z"/>
</svg>
'''
        (destination / f"{category}.svg").write_text(svg, encoding="utf-8")
        count += 1
    print(f"Updated {count} category icons in {destination}")


if __name__ == "__main__":
    main()
