import unittest
from unittest.mock import patch

from core.workers.conversion.pdf_layout import PdfLayout
from core.workers.conversion.tectonic_pdf import (
    TectonicUnavailableError,
    _resource_failure,
    _timeout_error,
    build_tex,
    escape_tex,
    find_tectonic,
    render_pdf,
)


class TectonicPdfTests(unittest.TestCase):
    def test_unavailable_temp_directory_is_classified_as_common_failure(self):
        with (
            patch("core.workers.conversion.tectonic_pdf.find_tectonic", return_value="engine"),
            patch("core.workers.conversion.tectonic_pdf._bundled_cache_environment", return_value=None),
            patch(
                "core.workers.conversion.tectonic_pdf.tempfile.TemporaryDirectory",
                side_effect=PermissionError("denied"),
            ),
        ):
            with self.assertRaises(TectonicUnavailableError):
                render_pdf(PdfLayout(markup="test"), "output.pdf", lambda: False)

    def test_distinguishes_download_failure_from_document_error(self):
        self.assertTrue(_resource_failure('failed to download "cmmi5.tfm"; please check your network connection'))
        self.assertFalse(_resource_failure("Undefined control sequence in document.tex"))

    def test_timeout_distinguishes_resource_failure_from_large_document(self):
        self.assertIsInstance(_timeout_error("downloading package", 120, bundled=False), TectonicUnavailableError)
        self.assertIsInstance(_timeout_error("processing document", 300, bundled=True), TimeoutError)

    def test_text_and_style_are_escaped_and_rendered(self):
        layout = PdfLayout(
            markup='<p><span style="font-weight:bold;font-size:16pt;color:#aabbcc">A &amp; B_1</span></p>'
        )
        source, assets = build_tex(layout)
        self.assertIn(r"\textbf{", source)
        self.assertIn(r"\fontsize{16}{19.2}", source)
        self.assertIn(r"\textcolor[HTML]{AABBCC}", source)
        self.assertIn(r"A \& B\_1", source)
        self.assertFalse(assets)

    def test_list_fonts_page_break_and_paragraph_spacing(self):
        layout = PdfLayout(
            markup=(
                '<p style="font-family:Times New Roman;font-size:14pt;line-height:1.15" '
                'data-list-label="•" data-list-left="36" data-list-hanging="18" '
                'data-page-break-before="true">Text</p>'
            )
        )
        source, _ = build_tex(layout)
        self.assertIn(r"\fontspec{Times New Roman}", source)
        self.assertIn(r"\fontsize{14}{16.1}\selectfont", source)
        self.assertIn(r"\leftskip=36pt", source)
        self.assertIn(r"\textbullet{}", source)
        self.assertIn(r"\ifdim\pagetotal>0pt\newpage\fi", source)
        self.assertIn(r"\pagestyle{empty}", source)

    def test_headings_and_styled_paragraphs_do_not_put_paragraph_breaks_in_text_commands(self):
        layout = PdfLayout(markup='<h1>Heading</h1><p style="font-weight:bold">Body</p><strong><p>Title</p></strong>')
        source, _ = build_tex(layout)
        self.assertIn("\\textbf{Heading}\\par", source)
        self.assertIn("\\textbf{Body}\\par", source)
        self.assertIn("{\\bfseries \\par", source)
        self.assertNotIn("\\textbf{\\par", source)

    def test_embedded_image_is_given_a_safe_name(self):
        layout = PdfLayout(
            markup='<p><img src="image0.png" style="width:100pt;height:50pt"></p>', assets={"image0.png": b"image"}
        )
        source, assets = build_tex(layout)
        self.assertIn(r"\includegraphics[width=100pt,height=50pt,keepaspectratio]{asset0.png}", source)
        self.assertEqual(assets, {"asset0.png": b"image"})

    def test_missing_image_adds_warning(self):
        layout = PdfLayout(markup='<img src="https://example.com/missing.png">')
        build_tex(layout)
        self.assertTrue(any("изображение" in warning for warning in layout.warnings))

    def test_tex_special_characters_cannot_be_interpreted_as_commands(self):
        self.assertEqual(escape_tex(r"\input{x} %"), r"\textbackslash{}input\{x\} \%")

    def test_windows_bundle_contains_the_tectonic_executable(self):
        import os

        if os.name != "nt":
            self.skipTest("В проект включён исполняемый файл Windows")
        self.assertTrue(find_tectonic().lower().endswith("tectonic.exe"))


if __name__ == "__main__":
    unittest.main()
