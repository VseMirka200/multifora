"""Portable sanity tests for the Windows bundle layout validator."""

from pathlib import Path
from unittest.mock import patch

from scripts.measure_bundle import collect_bundle_metrics
from scripts.measure_bundle import main as measure_bundle
from scripts.verify_build_environment import check_packages, check_python
from scripts.verify_windows_bundle import check_bundle


def test_bundle_validator_reports_missing_files(tmp_path: Path):
    assert "Multifora.exe" in check_bundle(tmp_path)
    assert "_internal/" in check_bundle(tmp_path)


def test_bundle_validator_accepts_complete_layout(tmp_path: Path):
    # Current PyMuPDF releases do not ship the old version-specific layout YAML.
    contents = (
        "Multifora.exe",
        "bin/gswin64/gswin64c.exe",
        "bin/gswin64/gsdll64.dll",
        "bin/pandoc/pandoc.exe",
        "bin/tectonic/tectonic.exe",
        "_internal/assets/icon.ico",
        "_internal/docxcompose/templates/custom.xml",
        "_internal/PySide6/plugins/platforms/qwindows.dll",
        "_internal/PySide6/plugins/platforms/qoffscreen.dll",
    )
    for relative in contents:
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"not empty")
    assert check_bundle(tmp_path) == []
    (tmp_path / "bin/gswin64/gsdll64.dll").unlink()
    assert check_bundle(tmp_path) == ["bin/gswin64/gsdll64.dll"]


def test_bundle_validator_requires_docx_merge_template(tmp_path: Path):
    assert "_internal/docxcompose/templates/custom.xml" in check_bundle(tmp_path)


def test_bundle_validator_rejects_excluded_qt_runtime(tmp_path: Path):
    internal = tmp_path / "_internal" / "PySide6"
    internal.mkdir(parents=True)
    (internal / "Qt6Quick.dll").write_bytes(b"not empty")

    assert "unexpected Qt runtime binary: _internal\\PySide6\\Qt6Quick.dll" in (check_bundle(tmp_path))


def test_release_build_uses_spec_with_docxcompose_resources():
    root = Path(__file__).resolve().parents[1]
    workflow = (root / ".github/workflows/release.yml").read_text(encoding="utf-8")
    build = (root / "scripts/build_app.bat").read_text(encoding="utf-8")
    spec = (root / "Multifora.spec").read_text(encoding="utf-8")
    assert "scripts\\build_app.bat --no-pause" in workflow
    assert 'PyInstaller --noconfirm --clean "Multifora.spec"' in build
    assert '"scripts\\verify_windows_bundle.py"' in build
    assert '"scripts\\measure_bundle.py"' in build
    assert "dist/bundle-metrics.json" in workflow
    assert "dist/runtime-metrics.json" in workflow
    assert "verify_windows_runtime.ps1" in workflow
    assert "collect_data_files('docxcompose')" in spec
    assert "excludes=['mupdf-devel/**']" in spec
    assert "'pdf2docx.gui', 'tkinter', '_tkinter'" in spec
    assert "excluded_qt_runtime_binaries" in spec
    assert '-r "requirements-runtime.txt" -r "requirements-build.txt"' in build


def test_bundle_metrics_are_deterministic_and_group_large_components(
    tmp_path: Path,
):
    bundle = tmp_path / "Multifora"
    files = {
        "Multifora.exe": b"exe",
        "_internal/cv2/cv2.pyd": b"opencv",
        "_internal/cv2/data.xml": b"data",
        "bin/pandoc/pandoc.exe": b"pandoc",
    }
    for relative, contents in files.items():
        target = bundle / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(contents)

    metrics = collect_bundle_metrics(bundle)

    assert metrics["total_bytes"] == sum(map(len, files.values()))
    assert metrics["file_count"] == len(files)
    assert metrics["groups"]["_internal/cv2"] == {
        "bytes": len(b"opencvdata"),
        "files": 2,
    }
    assert metrics["groups"]["bin/pandoc"] == {
        "bytes": len(b"pandoc"),
        "files": 1,
    }


def test_bundle_metrics_fail_a_regressed_budget_but_write_artifact(
    tmp_path: Path,
):
    bundle = tmp_path / "Multifora"
    bundle.mkdir()
    (bundle / "Multifora.exe").write_bytes(b"too large")
    output = tmp_path / "bundle-metrics.json"

    result = measure_bundle(
        [
            "--bundle",
            str(bundle),
            "--output",
            str(output),
            "--max-mib",
            "0",
            "--max-files",
            "10",
        ]
    )

    assert result == 1
    assert output.is_file()


def test_build_environment_rejects_wrong_python_before_packaging():
    with (
        patch("scripts.verify_build_environment.sys.version_info", (3, 15)),
        patch("scripts.verify_build_environment.sys.platform", "win32"),
        patch("scripts.verify_build_environment.struct.calcsize", return_value=8),
    ):
        assert len(check_python()) == 1
        assert "Python 3.11 is required" in check_python()[0]


def test_build_environment_accepts_supported_python():
    with (
        patch("scripts.verify_build_environment.sys.version_info", (3, 11)),
        patch("scripts.verify_build_environment.sys.platform", "win32"),
        patch("scripts.verify_build_environment.struct.calcsize", return_value=8),
    ):
        assert check_python() == []


def test_build_environment_rejects_32_bit_python():
    with (
        patch("scripts.verify_build_environment.sys.version_info", (3, 11)),
        patch("scripts.verify_build_environment.sys.platform", "win32"),
        patch("scripts.verify_build_environment.struct.calcsize", return_value=4),
    ):
        assert check_python() == ["64-bit Python is required."]


def test_build_environment_detects_missing_and_changed_packages(tmp_path: Path):
    from importlib.metadata import PackageNotFoundError

    requirements = tmp_path / "requirements.txt"
    shared = tmp_path / "shared-fixture.txt"
    shared.write_text("first==1.0\n", encoding="utf-8")
    requirements.write_text("# Lock\n-r shared-fixture.txt\nsecond==2.0\nthird==3.0\n")
    with patch(
        "scripts.verify_build_environment.version",
        side_effect=["1.0", "2.1", PackageNotFoundError("third")],
    ):
        assert check_packages(requirements) == [
            "second: expected 2.0, installed 2.1.",
            "third==3.0 is not installed.",
        ]
