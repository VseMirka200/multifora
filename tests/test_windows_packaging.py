"""Portable sanity tests for the Windows bundle layout validator."""

from pathlib import Path
from unittest.mock import patch

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


def test_release_build_uses_spec_with_docxcompose_resources():
    root = Path(__file__).resolve().parents[1]
    workflow = (root / ".github/workflows/release.yml").read_text(encoding="utf-8")
    build = (root / "scripts/build_app.bat").read_text(encoding="utf-8")
    spec = (root / "Multifora.spec").read_text(encoding="utf-8")
    assert "scripts\\build_app.bat --no-pause" in workflow
    assert 'PyInstaller --noconfirm --clean "Multifora.spec"' in build
    assert '"scripts\\verify_windows_bundle.py"' in build
    assert "verify_windows_runtime.ps1" in workflow
    assert "collect_data_files('docxcompose')" in spec


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
    requirements.write_text("# Lock\n-r shared-fixture.txt\nfirst==1.0\nsecond==2.0\nthird==3.0\n")
    with patch(
        "scripts.verify_build_environment.version",
        side_effect=["1.0", "2.1", PackageNotFoundError("third")],
    ):
        assert check_packages(requirements) == [
            "second: expected 2.0, installed 2.1.",
            "third==3.0 is not installed.",
        ]
