# ruff: noqa: E501
import io
import unittest
from zipfile import ZipFile

from core.workers.conversion.pdf_layout import docx_layout, epub_layout, fb2_layout, markdown_layout, odt_layout


def document_zip(files):
    output = io.BytesIO()
    with ZipFile(output, "w") as archive:
        for name, content in files.items():
            archive.writestr(name, content)
    output.seek(0)
    return output


class PdfLayoutTests(unittest.TestCase):
    def test_docx_preserves_list_numbering_font_and_saved_page_break(self):
        source = document_zip(
            {
                "word/document.xml": """<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>
            <w:p><w:pPr><w:numPr><w:ilvl w:val="0"/><w:numId w:val="1"/></w:numPr></w:pPr><w:r><w:rPr><w:rFonts w:ascii="Times New Roman"/><w:sz w:val="28"/></w:rPr><w:t>First</w:t></w:r></w:p>
            <w:p><w:pPr><w:numPr><w:ilvl w:val="0"/><w:numId w:val="1"/></w:numPr></w:pPr><w:r><w:lastRenderedPageBreak/><w:t>Second</w:t></w:r></w:p>
            <w:p><w:pPr><w:numPr><w:ilvl w:val="0"/><w:numId w:val="2"/></w:numPr></w:pPr><w:r><w:t>Bullet</w:t></w:r></w:p>
            </w:body></w:document>""",
                "word/numbering.xml": """<w:numbering xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
            <w:abstractNum w:abstractNumId="1"><w:lvl w:ilvl="0"><w:start w:val="3"/><w:numFmt w:val="decimal"/><w:lvlText w:val="%1."/><w:pPr><w:ind w:left="720" w:hanging="360"/></w:pPr></w:lvl></w:abstractNum>
            <w:abstractNum w:abstractNumId="2"><w:lvl w:ilvl="0"><w:numFmt w:val="bullet"/><w:lvlText w:val="&#xf0b7;"/></w:lvl></w:abstractNum>
            <w:num w:numId="1"><w:abstractNumId w:val="1"/></w:num><w:num w:numId="2"><w:abstractNumId w:val="2"/></w:num></w:numbering>""",
            }
        )
        layout = docx_layout(source)
        self.assertIn('data-list-label="3."', layout.markup)
        self.assertIn('data-list-label="4."', layout.markup)
        self.assertIn('data-list-label="•"', layout.markup)
        self.assertIn('data-page-break-before="true"', layout.markup)
        self.assertIn("font-family:Times New Roman", layout.markup)
        self.assertIn("font-size:14pt", layout.markup)

    def test_docx_preserves_order_style_image_and_page_size(self):
        source = document_zip(
            {
                "word/document.xml": """<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"><w:body><w:p><w:pPr><w:pStyle w:val="Title"/></w:pPr><w:r><w:t>Привет</w:t></w:r><w:r><w:drawing><wp:inline><wp:extent cx="1270000" cy="635000"/><a:blip r:embed="r1"/></wp:inline></w:drawing></w:r></w:p><w:tbl><w:tr><w:tc><w:p><w:r><w:t>Ячейка</w:t></w:r></w:p></w:tc></w:tr></w:tbl><w:sectPr><w:pgSz w:w="12240" w:h="15840"/><w:pgMar w:left="1440" w:top="1440" w:right="1440" w:bottom="1440"/></w:sectPr></w:body></w:document>""",
                "word/styles.xml": """<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:style w:styleId="Title"><w:rPr><w:b/><w:sz w:val="32"/></w:rPr></w:style></w:styles>""",
                "word/_rels/document.xml.rels": """<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="r1" Target="media/picture.png"/></Relationships>""",
                "word/media/picture.png": b"image bytes",
            }
        )
        layout = docx_layout(source)
        self.assertIn("font-weight:bold", layout.markup)
        self.assertIn("font-size:16pt", layout.markup)
        self.assertLess(layout.markup.index("Привет"), layout.markup.index("Ячейка"))
        self.assertIn('src="image0.png"', layout.markup)
        self.assertEqual(layout.assets["image0.png"], b"image bytes")
        self.assertEqual((layout.width, layout.height), (612, 792))
        self.assertEqual(layout.margins, (72, 72, 72, 72))

    def test_odt_preserves_text_style_and_image(self):
        source = document_zip(
            {
                "content.xml": """<office:document-content xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0" xmlns:style="urn:oasis:names:tc:opendocument:xmlns:style:1.0" xmlns:fo="urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0" xmlns:draw="urn:oasis:names:tc:opendocument:xmlns:drawing:1.0" xmlns:xlink="http://www.w3.org/1999/xlink"><office:automatic-styles><style:style style:name="bold"><style:text-properties fo:font-weight="bold"/></style:style></office:automatic-styles><office:body><office:text><text:p>Текст <text:span text:style-name="bold">важно</text:span><draw:frame><draw:image xlink:href="Pictures/p.png"/></draw:frame></text:p></office:text></office:body></office:document-content>""",
                "Pictures/p.png": b"image bytes",
            }
        )
        layout = odt_layout(source)
        self.assertIn("font-weight:bold", layout.markup)
        self.assertIn("Текст", layout.markup)
        self.assertEqual(layout.assets["image0.png"], b"image bytes")
        self.assertTrue(layout.warnings)

    def test_markdown_headings_lists_and_emphasis(self):
        layout = markdown_layout("# Заголовок\n- **Важный** пункт\n- *Курсив*")
        self.assertIn("<h1>Заголовок</h1>", layout.markup)
        self.assertIn("<li><strong>Важный</strong> пункт</li>", layout.markup)
        self.assertIn("<em>Курсив</em>", layout.markup)

    def test_epub_retains_chapter_order_and_embedded_image(self):
        source = document_zip(
            {
                "META-INF/container.xml": '<container><rootfiles><rootfile full-path="book/content.opf"/></rootfiles></container>',
                "book/content.opf": '<package><manifest><item id="a" href="chapters/a.xhtml"/><item id="b" href="chapters/b.xhtml"/></manifest><spine><itemref idref="b"/><itemref idref="a"/></spine></package>',
                "book/chapters/a.xhtml": "<html><body><p>Second</p></body></html>",
                "book/chapters/b.xhtml": '<html><body><p>First</p><img src="../images/p.png"/></body></html>',
                "book/images/p.png": b"picture",
            }
        )
        layout = epub_layout(source)
        self.assertLess(layout.markup.index("First"), layout.markup.index("Second"))
        self.assertIn('src="epub-image-0.png"', layout.markup)
        self.assertEqual(layout.assets["epub-image-0.png"], b"picture")

    def test_fb2_retains_text_style_and_image(self):
        source = io.BytesIO(
            b"""<FictionBook xmlns="http://www.gribuser.ru/xml/fictionbook/2.0" xmlns:l="http://www.w3.org/1999/xlink"><body><section><p>Hello <strong>world</strong></p><image l:href="#cover"/></section></body><binary id="cover" content-type="image/png">cGljdHVyZQ==</binary></FictionBook>"""
        )
        layout = fb2_layout(source)
        self.assertIn("<strong>world</strong>", layout.markup)
        self.assertIn('src="fb2-image-0.png"', layout.markup)
        self.assertEqual(layout.assets["fb2-image-0.png"], b"picture")


if __name__ == "__main__":
    unittest.main()
