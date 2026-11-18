from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from core.workers import office_engine as engine


def _source(tmp_path, suffix=".docx"):
    source = tmp_path / ("исходный документ" + suffix)
    source.write_bytes(b"source remains unchanged")
    return source


def _successful_run(arguments, _directory, *_args):
    Path(arguments[3]).write_bytes(b"%PDF-1.7\ncomplete")


def test_detects_bundled_wordcraft(tmp_path):
    executable = tmp_path / "bin/wordcraft/wordcraft-cli.exe"
    executable.parent.mkdir(parents=True)
    executable.write_bytes(b"exe")
    with (
        patch.object(engine.sys, "frozen", True, create=True),
        patch.object(engine.sys, "executable", str(tmp_path / "Multifora.exe")),
    ):
        assert engine.find_wordcraft() == str(executable.resolve())


def test_missing_engine_reports_problem(tmp_path):
    with patch.object(engine, "find_wordcraft", return_value=None):
        with pytest.raises(engine.OfficeUnavailableError, match="WordCraft"):
            engine.run_office(_source(tmp_path), tmp_path / "out.pdf", "PDF", lambda: False)


def test_converts_without_modifying_source(tmp_path):
    source = _source(tmp_path)
    output = tmp_path / "output.pdf"
    with (
        patch.object(engine, "find_wordcraft", return_value="wordcraft"),
        patch.object(engine, "_run", side_effect=_successful_run) as run,
    ):
        assert engine.run_office(source, output, "PDF", lambda: False) == ""
    assert run.call_args.args[0][1] == "convert"
    assert output.read_bytes().startswith(b"%PDF-")
    assert source.read_bytes() == b"source remains unchanged"


def test_cancellation_does_not_publish_output(tmp_path):
    source = _source(tmp_path)
    with (
        patch.object(engine, "find_wordcraft", return_value="wordcraft"),
        patch.object(engine, "_run", side_effect=InterruptedError("cancelled")),
    ):
        with pytest.raises(InterruptedError):
            engine.run_office(source, tmp_path / "out.pdf", "PDF", lambda: False)
    assert not (tmp_path / "out.pdf").exists()


def test_empty_result_is_not_published(tmp_path):
    with patch.object(engine, "find_wordcraft", return_value="wordcraft"), patch.object(engine, "_run"):
        with pytest.raises(RuntimeError, match="WordCraft"):
            engine.run_office(_source(tmp_path), tmp_path / "out.pdf", "PDF", lambda: False)


def test_existing_destination_is_preserved(tmp_path):
    source = _source(tmp_path)
    output = tmp_path / "out.pdf"
    output.write_bytes(b"existing")
    with (
        patch.object(engine, "find_wordcraft", return_value="wordcraft"),
        patch.object(engine, "_run", side_effect=_successful_run),
    ):
        with pytest.raises(FileExistsError):
            engine.run_office(source, output, "PDF", lambda: False)
    assert output.read_bytes() == b"existing"


@pytest.mark.parametrize("cancelled", [True, False])
def test_worker_stops_its_process_on_cancel_or_timeout(tmp_path, cancelled):
    process = Mock()
    process.poll.return_value = None
    with (
        patch.object(engine.subprocess, "Popen", return_value=process),
        patch.object(engine, "_stop_process") as stop,
        patch.object(engine.time, "monotonic", side_effect=[0, 100]),
    ):
        with pytest.raises(InterruptedError if cancelled else TimeoutError):
            engine._run(["office"], tmp_path, lambda: cancelled, 1, None)
    stop.assert_called_once_with(process)


def test_unicode_text_export_is_normalized_to_utf8(tmp_path):
    output = tmp_path / "output.txt"
    output.write_bytes("Привет\r\n\r\nМир".encode("utf-16"))
    engine._normalize_export(output, "TXT")
    assert output.read_bytes() == "Привет\n\nМир".encode()


def test_html_export_embeds_images_before_temporary_directory_disappears(tmp_path):
    assets = tmp_path / "result_files"
    assets.mkdir()
    (assets / "image.png").write_bytes(b"image")
    output = tmp_path / "result.html"
    output.write_text('<meta charset="utf-8"><img src="result_files/image.png">Привет', encoding="utf-8")
    engine._normalize_export(output, "HTML")
    result = output.read_text(encoding="utf-8")
    assert '<meta charset="utf-8">' in result
    assert 'src="data:image/png;base64,aW1hZ2U="' in result
    assert "Привет" in result
