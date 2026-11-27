"""Conservative source-reviewed routes. Candidate support still requires native build testing."""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from core.conversion_formats import format_for_path

WORD_INPUTS = ("DOC", "DOCX", "ODT", "RTF", "HTML", "MD", "TEX", "TXT")
WORD_OUTPUTS = ("DOCX", "PDF", "ODT", "RTF", "HTML", "MD", "TEX", "TXT")
DECK_INPUTS = ("PPT", "PPTX", "POT", "PPS", "DECKCRAFT")
DECK_OUTPUTS = ("PPTX", "PDF", "PNG", "DECKCRAFT")
GRID_INPUTS = ("XLS", "XLSX", "XLSB", "ODS", "CSV", "TSV")
GRID_OUTPUTS = ("XLSX", "CSV", "TSV", "HTML", "PDF", "JSON")
PHOTO_INPUTS = ("JPG", "JPEG", "PNG", "WEBP", "BMP", "TIFF", "GIF", "ICO", "TGA", "QOI", "PNM", "PPM", "PGM", "PBM", "PSD", "PSB", "ORA", "XCF", "KRA", "PCRAFT")
PHOTO_OUTPUTS = ("JPG", "JPEG", "PNG", "WEBP", "BMP", "TIFF", "GIF", "ICO", "TGA", "QOI", "PNM", "PSD", "PSB", "ORA", "PCRAFT")
VECTOR_INPUTS = ("SVG", "SVGZ", "AI", "EPS", "VECTORCRAFT")
VECTOR_OUTPUTS = ("SVG", "PDF", "PNG", "JPG", "JPEG", "WEBP", "EPS", "AI")
PDF_OUTPUTS = ("PNG", "JPG", "JPEG", "TIFF", "WEBP", "BMP")

@dataclass(frozen=True)
class Route:
    engine: str
    operation: str = "convert"


def route(source: str, target: str) -> Route | None:
    source, target = source.upper(), target.upper()
    if source == target or {source, target} == {"JPG", "JPEG"}:
        return None
    if source == "PDF" and target in PDF_OUTPUTS:
        return Route("pdfcraft", "render_pages")
    if source in WORD_INPUTS and target in WORD_OUTPUTS:
        return Route("wordcraft")
    if source in DECK_INPUTS and target in DECK_OUTPUTS:
        return Route("deckcraft", "render_pages" if target == "PNG" else "convert")
    if source in GRID_INPUTS and target in GRID_OUTPUTS:
        return Route("gridcraft")
    if source in VECTOR_INPUTS and target in VECTOR_OUTPUTS:
        return Route("vectorcraft")
    if source in PHOTO_INPUTS and target in PHOTO_OUTPUTS:
        return Route("photocraft")
    return None


def route_for_path(path: str, target: str) -> Route | None:
    return route(format_for_path(path) or Path(path).suffix.lstrip(".").upper(), target)
