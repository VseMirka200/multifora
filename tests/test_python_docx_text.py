import pytest
from docx import Document
from PIL import Image

from core.document_engine.office import run_office
from core.document_engine.structured_text import export_text


def test_export_preserves_paragraph_and_table_order(tmp_path):
    doc = Document()
    doc.add_paragraph("До таблицы")
    table = doc.add_table(rows=1, cols=2)
    table.cell(0, 0).text = "Первая"
    table.cell(0, 1).text = "Вторая"
    doc.add_paragraph("После таблицы")
    source = tmp_path / "тест.docx"
    doc.save(source)
    target = tmp_path / "результат.txt"
    export_text(source, target, "DOCX", lambda: False)
    assert target.read_text(encoding="utf-8") == "До таблицы\nПервая\tВторая\nПосле таблицы"


def test_cancel_keeps_existing_file(tmp_path):
    source = tmp_path / "test.docx"
    Document().save(source)
    target = tmp_path / "out.txt"
    target.write_text("existing", encoding="utf-8")
    with pytest.raises(InterruptedError):
        export_text(source, target, "DOCX", lambda: True)
    assert target.read_text(encoding="utf-8") == "existing"


def test_docx_to_html_embeds_images_and_keeps_inline_format(tmp_path):
    picture = tmp_path / "picture.png"
    Image.new("RGB", (12, 12), "blue").save(picture)
    source = tmp_path / "source.docx"
    doc = Document()
    doc.add_paragraph().add_run("Жирный & текст").bold = True
    doc.add_picture(str(picture))
    doc.save(source)
    output = tmp_path / "output.html"
    run_office(source, output, "HTML", lambda: False)
    result = output.read_text(encoding="utf-8")
    assert "<strong>Жирный &amp; текст</strong>" in result
    assert '<img src="data:image/png;base64,' in result


def test_roundtrip_odt_retains_document_elements(tmp_path):
    picture = tmp_path / "picture.png"
    Image.new("RGB", (12, 12), "blue").save(picture)
    source = tmp_path / "Исходник.docx"
    document = Document()
    document.add_heading("Заголовок", 1)
    document.add_paragraph().add_run("Выделенный текст").bold = True
    table = document.add_table(rows=1, cols=2)
    table.cell(0, 0).text = "Первая"
    table.cell(0, 1).text = "Вторая"
    document.add_picture(str(picture))
    document.save(source)

    odt = tmp_path / "Средний.odt"
    result = tmp_path / "Результат.docx"
    run_office(source, odt, "ODT", lambda: False)
    run_office(odt, result, "DOCX", lambda: False)
    converted = Document(result)
    assert converted.paragraphs[0].text == "Заголовок"
    assert converted.paragraphs[1].runs[0].bold
    assert [cell.text for cell in converted.tables[0].rows[0].cells] == ["Первая", "Вторая"]
    assert len(converted.inline_shapes) == 1
