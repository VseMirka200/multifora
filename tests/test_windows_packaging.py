"""Portable sanity tests for the Windows bundle layout validator."""

from pathlib import Path

from scripts.verify_windows_bundle import check_bundle


def test_bundle_validator_reports_missing_files(tmp_path: Path):
    assert "Multifora.exe" in check_bundle(tmp_path)
    assert "_internal/" in check_bundle(tmp_path)


def test_bundle_validator_accepts_complete_layout(tmp_path: Path):
    contents = (
        "Multifora.exe",
        "bin/gswin64/gswin64c.exe",
        "bin/gswin64/gsdll64.dll",
        "_internal/assets/icon.ico",
        "_internal/pymupdf/layout/resources/onnx/layout_rf2.4.1+imf1.yaml",
        "_internal/docxcompose/templates/custom.xml",
        "_internal/PyQt6/Qt6/plugins/platforms/qwindows.dll",
        "_internal/PyQt6/Qt6/plugins/platforms/qoffscreen.dll",
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
    spec = (root / "Multifora.spec").read_text(encoding="utf-8")
    assert "python -m PyInstaller --noconfirm --clean Multifora.spec" in workflow
    assert "python scripts/verify_windows_bundle.py --bundle dist/Multifora" in workflow
    assert "collect_data_files('docxcompose')" in spec
