import os
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from core.workers import office_engine as engine


def _source(tmp_path, suffix=".docx"):
    source = tmp_path / ("исходный документ" + suffix)
    source.write_bytes(b"source remains unchanged")
    return source


def _successful_run(arguments, _directory, *_args):
    if "-Output" in arguments:
        output = Path(arguments[arguments.index("-Output") + 1])
    else:
        output = Path(arguments[arguments.index("--outdir") + 1]) / (Path(arguments[-1]).stem + ".pdf")
    output.write_bytes(b"%PDF-1.7\ncomplete")


def test_detects_libreoffice_from_path(tmp_path):
    executable = tmp_path / "soffice.com"
    executable.write_bytes(b"exe")
    with (
        patch.object(
            engine.shutil, "which", side_effect=lambda name: str(executable) if name == "soffice.com" else None
        ),
        patch.object(engine, "_registry_paths", return_value=[]),
    ):
        assert engine.find_libreoffice() == str(executable.resolve())


def test_detects_libreoffice_in_program_files(tmp_path):
    executable = tmp_path / "LibreOffice/program/soffice.com"
    executable.parent.mkdir(parents=True)
    executable.write_bytes(b"exe")
    with (
        patch.dict(os.environ, {"ProgramFiles": str(tmp_path)}),
        patch.object(engine.shutil, "which", return_value=None),
        patch.object(engine, "_registry_paths", return_value=[]),
    ):
        assert engine.find_libreoffice() == str(executable.resolve())


@pytest.mark.skipif(os.name != "nt", reason="Windows registry detection")
def test_detects_word_from_registry(tmp_path):
    executable = tmp_path / "WINWORD.EXE"
    executable.write_bytes(b"exe")
    with patch.object(engine, "_registry_paths", return_value=[str(executable)]):
        assert engine.find_word() == str(executable.resolve())


def test_missing_office_reports_installation_requirement(tmp_path):
    source = _source(tmp_path)
    output = tmp_path / "output.pdf"
    with (
        patch.object(engine, "find_word", return_value=None),
        patch.object(engine, "find_libreoffice", return_value=None),
    ):
        with pytest.raises(engine.OfficeUnavailableError, match=r"Word.*LibreOffice"):
            engine.run_office(source, output, "PDF", lambda: False)
    assert not output.exists()


@pytest.mark.parametrize("suffix,preferred", [(".docx", "-Output"), (".odt", "--outdir")])
def test_selects_native_office_without_modifying_source(tmp_path, suffix, preferred):
    source = _source(tmp_path, suffix)
    output = tmp_path / "output.pdf"
    with (
        patch.object(engine, "find_word", return_value="word"),
        patch.object(engine, "find_libreoffice", return_value="libreoffice"),
        patch.object(engine, "_run", side_effect=_successful_run) as run,
    ):
        assert engine.run_office(source, output, "PDF", lambda: False) == ""
    assert preferred in run.call_args.args[0]
    assert output.read_bytes().startswith(b"%PDF-")
    assert source.read_bytes() == b"source remains unchanged"


def test_word_failure_falls_back_to_isolated_libreoffice(tmp_path):
    source = _source(tmp_path)
    output = tmp_path / "output.pdf"

    def run(arguments, directory, *args):
        if "-Output" in arguments:
            raise RuntimeError("Word cannot open document")
        assert any(arg.startswith("-env:UserInstallation=file:") for arg in arguments)
        assert "--headless" in arguments
        _successful_run(arguments, directory, *args)

    with (
        patch.object(engine, "find_word", return_value="word"),
        patch.object(engine, "find_libreoffice", return_value="libreoffice"),
        patch.object(engine, "_run", side_effect=run) as process,
    ):
        warning = engine.run_office(source, output, "PDF", lambda: False)
    assert "Word cannot open document" in warning
    assert process.call_count == 2
    assert output.is_file()


def test_cancellation_never_starts_fallback_or_publishes_output(tmp_path):
    source = _source(tmp_path)
    with (
        patch.object(engine, "find_word", return_value="word"),
        patch.object(engine, "find_libreoffice", return_value="libreoffice"),
        patch.object(engine, "_run", side_effect=InterruptedError("cancelled")) as run,
    ):
        with pytest.raises(InterruptedError):
            engine.run_office(source, tmp_path / "out.pdf", "PDF", lambda: False)
    assert run.call_count == 1
    assert not (tmp_path / "out.pdf").exists()


def test_empty_result_is_not_published(tmp_path):
    source = _source(tmp_path)
    with (
        patch.object(engine, "find_word", return_value=None),
        patch.object(engine, "find_libreoffice", return_value="libreoffice"),
        patch.object(engine, "_run"),
    ):
        with pytest.raises(RuntimeError, match="не создал"):
            engine.run_office(source, tmp_path / "out.pdf", "PDF", lambda: False)
    assert not (tmp_path / "out.pdf").exists()


def test_existing_destination_is_preserved(tmp_path):
    source = _source(tmp_path)
    output = tmp_path / "out.pdf"
    output.write_bytes(b"existing")
    with (
        patch.object(engine, "find_word", return_value="word"),
        patch.object(engine, "find_libreoffice", return_value=None),
        patch.object(engine, "_run", side_effect=_successful_run),
    ):
        with pytest.raises(FileExistsError):
            engine.run_office(source, output, "PDF", lambda: False)
    assert output.read_bytes() == b"existing"
    assert not list(tmp_path.glob(".__multifora_*"))


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
    stop.assert_called_once_with(process, None)


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
