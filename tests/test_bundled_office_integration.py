"""Exercise the real bundled Writer against each supported office format."""

import zipfile

import pytest
from docx import Document

from core.workers.office_engine import find_wordcraft, run_office

FORMATS = ("DOCX", "ODT", "RTF", "TXT", "HTML")
MARKER = "MultiforaConversionMarker"


@pytest.fixture(scope="module")
def office_sources(tmp_path_factory):
    if not find_wordcraft():
        pytest.skip("Bundled WordCraft is not available")
    directory = tmp_path_factory.mktemp("office-sources")
    source = directory / "source.docx"
    document = Document()
    document.add_heading("Conversion test", 0)
    document.add_paragraph(MARKER + " Привет мир")
    document.add_table(rows=2, cols=2).cell(0, 0).text = "TableMarker"
    document.save(source)
    sources = {"DOCX": source}
    for fmt in FORMATS[1:]:
        output = directory / ("source." + fmt.lower())
        run_office(source, output, fmt, lambda: False)
        sources[fmt] = output
    return sources


@pytest.mark.parametrize("source_format", FORMATS)
@pytest.mark.parametrize("target", (*FORMATS, "PDF"))
def test_bundled_office_conversion_matrix(tmp_path, office_sources, source_format, target):
    if source_format == target:
        pytest.skip("The application skips conversion to the source format")
    source = office_sources[source_format]
    original = source.read_bytes()
    output = tmp_path / ("result." + target.lower())
    run_office(source, output, target, lambda: False)
    assert source.read_bytes() == original
    assert output.is_file() and output.stat().st_size > 0
    if target in {"DOCX", "ODT"}:
        with zipfile.ZipFile(output) as archive:
            xml = archive.read("word/document.xml" if target == "DOCX" else "content.xml")
        assert MARKER.encode() in xml
    elif target == "PDF":
        assert output.read_bytes().startswith(b"%PDF-")
    else:
        assert MARKER in output.read_text(encoding="utf-8")
