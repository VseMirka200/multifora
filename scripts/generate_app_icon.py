"""Создаёт Windows ICO из основного SVG для EXE и ярлыков."""

from pathlib import Path

import pymupdf
from PIL import Image


def main():
    assets = Path(__file__).resolve().parents[1] / "assets"
    with pymupdf.open(assets / "icon.svg") as document:
        page = document[0]
        scale = 256 / max(page.rect.width, page.rect.height)
        pixmap = page.get_pixmap(matrix=pymupdf.Matrix(scale, scale), alpha=True)
        with Image.frombytes("RGBA", (pixmap.width, pixmap.height), pixmap.samples) as image:
            image.save(assets / "icon.ico", sizes=[(s, s) for s in (16, 24, 32, 48, 64, 128, 256)])


if __name__ == "__main__":
    main()
