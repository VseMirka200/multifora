# Contributing to Multifora

Thank you for helping improve Multifora. Bug reports, documentation fixes, usability improvements, and focused code changes are welcome.

## Before you start

Search the [issue tracker](https://github.com/VseMirka200/multifora/issues) before opening a new issue. For a bug, include the Multifora version, Windows version, steps to reproduce the problem, the expected result, and the actual result. Add logs or a minimal sample file when they help reproduce the issue, but remove personal or confidential data first.

For a substantial feature or behavior change, open an issue before investing in the implementation so the intended behavior and scope can be discussed.

Do not report security vulnerabilities in public issues. Follow [SECURITY.md](SECURITY.md) instead.

## Development setup

Multifora is developed for Windows and requires Python 3.11 or newer.

```powershell
git clone https://github.com/VseMirka200/multifora.git
cd multifora
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Start the application with:

```powershell
.\.venv\Scripts\python.exe multifora_start.py
```

Some document operations require Microsoft Word. PDF compression requires Ghostscript. Changes unrelated to those integrations can be developed and tested without them.

## Making a change

1. Fork the repository and create a focused branch from `main`.
2. Keep the change limited to one clear purpose.
3. Follow the existing Python and PyQt patterns in the surrounding code.
4. Add or update tests when behavior changes or a regression needs protection.
5. Update user-facing documentation when installation, behavior, or supported formats change.
6. Run the relevant tests and then the complete suite.

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests
```

## Pull requests

In the pull request description, explain the problem, the resulting behavior, and how the change was tested. Include screenshots for visible interface changes. Keep generated build output, virtual environments, caches, local settings, and personal files out of commits.

By participating, you agree to follow the project [Code of Conduct](CODE_OF_CONDUCT.md).
