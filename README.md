<p align="center">
  <img src="assets/icon.svg" alt="Multifora application icon" width="160" height="160">
</p>

<h1 align="center">Multifora</h1>

<p align="center">Batch file tools for Windows</p>

<p align="center">
  <a href="https://github.com/VseMirka200/multifora/releases/latest"><img alt="Download" src="https://img.shields.io/badge/DOWNLOAD-LATEST-1f883d?style=for-the-badge"></a>
  <a href="https://github.com/VseMirka200/multifora"><img alt="Source code" src="https://img.shields.io/badge/SOURCE-GITHUB-6f42c1?style=for-the-badge"></a>
  <a href="https://github.com/VseMirka200/multifora/releases"><img alt="Releases" src="https://img.shields.io/badge/RELEASES-VIEW-0969da?style=for-the-badge"></a>
  <a href="https://github.com/VseMirka200/multifora/issues"><img alt="Issues" src="https://img.shields.io/badge/ISSUES-OPEN-57606a?style=for-the-badge"></a>
  <a href="https://github.com/VseMirka200/multifora/issues/new"><img alt="Report a bug" src="https://img.shields.io/badge/REPORT_A_BUG-CREATE-d1242f?style=for-the-badge"></a>
</p>

Multifora is a Windows desktop application for working with many files at once. It combines common document and image operations in one PyQt interface and previews changes before they are applied.

## Features

- Batch rename files with reusable templates, numbering, preview, undo, and redo.
- Convert documents and images between supported formats.
- Merge PDF and Word documents into PDF, or combine DOCX files into one DOCX document.
- Compress PDF files and images with configurable quality settings.
- Remove selected metadata fields or all metadata from PDF, DOC, DOCX, and ODT files.
- Add files and folders by using the picker, drag and drop, command-line arguments, or the Windows context menu.
- Search, filter, sort, and reorder the file queue.
- Use light, dark, or system appearance settings.
- Check GitHub Releases for application updates.

## Download

Download the newest packaged build from [GitHub Releases](https://github.com/VseMirka200/multifora/releases/latest), extract it, and run `Multifora.exe`.

The application targets Windows. Microsoft Word is required for conversions that use Word automation, including DOC or DOCX to PDF. [Ghostscript](https://ghostscript.com/releases/gsdnld.html) enables PDF compression; its executable can also be selected in the application settings.

## Run from source

You need Windows and Python 3.11 or newer.

```powershell
git clone https://github.com/VseMirka200/multifora.git
cd multifora
.\start_multifora.bat
```

The launcher creates `.venv`, installs the packages from `requirements.txt`, and starts the application. To set up the environment manually:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe multifora_start.py
```

## Build the Windows application

Run the build script from the repository root:

```powershell
.\scripts\build_app.bat
```

The script installs PyInstaller, generates the Windows icon, and writes the packaged application to `dist\Multifora`.

## Development

Run the test suite with:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests
```

Please read [CONTRIBUTING.md](CONTRIBUTING.md) before submitting a change. Participation in this project is governed by the [Code of Conduct](CODE_OF_CONDUCT.md). Security issues should follow the private reporting process in [SECURITY.md](SECURITY.md).

## Project links

- [Latest release](https://github.com/VseMirka200/multifora/releases/latest)
- [Issue tracker](https://github.com/VseMirka200/multifora/issues)
- [Contributing guide](CONTRIBUTING.md)
- [Security policy](SECURITY.md)
- [Code of Conduct](CODE_OF_CONDUCT.md)
