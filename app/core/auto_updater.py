"""Download and launch a verified installer for an installed Multifora copy."""

import hashlib
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.request import Request, urlopen

from app.core.update_checker import RELEASES_LATEST_API, _fetch_json

_INSTALLER_PREFIX = "Multifora-Setup-"
_USER_AGENT = "multifora-updater"


def automatic_updates_supported() -> bool:
    """Automatic replacement is only safe for the packaged Windows application."""
    return os.name == "nt" and bool(getattr(sys, "frozen", False))


def _find_asset(release: dict, predicate) -> dict:
    for asset in release.get("assets", []):
        if isinstance(asset, dict) and predicate(str(asset.get("name") or "")):
            return asset
    raise RuntimeError("В выпуске не найден установщик Мультифоры.")


def _download(url: str, destination: Path, timeout: int = 30) -> None:
    request = Request(url, headers={"User-Agent": _USER_AGENT})
    with urlopen(request, timeout=timeout) as response, destination.open("wb") as file:
        while chunk := response.read(1024 * 1024):
            file.write(chunk)


def _verify_checksum(installer: Path, checksum_file: Path) -> None:
    parts = checksum_file.read_text(encoding="utf-8").split()
    if not parts:
        raise RuntimeError("Не удалось прочитать контрольную сумму установщика.")
    expected = parts[0].lower()
    digest = hashlib.sha256()
    with installer.open("rb") as file:
        while chunk := file.read(1024 * 1024):
            digest.update(chunk)
    actual = digest.hexdigest().lower()
    if expected != actual:
        raise RuntimeError("Контрольная сумма загруженного установщика не совпадает.")


def download_and_launch_latest_installer(timeout: int = 30) -> str:
    """Download, verify and start the latest Inno Setup installer.

    The installer performs the replacement itself, including removal of obsolete
    bundled files.  Its temporary download directory is intentionally retained:
    Inno Setup still needs the installer after this process exits.
    """
    if not automatic_updates_supported():
        raise RuntimeError(
            "Автоматическое обновление доступно только в установленной Windows-версии."
        )

    release = _fetch_json(RELEASES_LATEST_API, timeout=timeout)
    installer_asset = _find_asset(
        release,
        lambda name: name.startswith(_INSTALLER_PREFIX) and name.lower().endswith(".exe"),
    )
    checksum_asset = _find_asset(
        release,
        lambda name: name == f"{installer_asset.get('name', '')[:-4]}.sha256",
    )
    installer_url = str(installer_asset.get("browser_download_url") or "")
    checksum_url = str(checksum_asset.get("browser_download_url") or "")
    if not installer_url or not checksum_url:
        raise RuntimeError("У выпуска отсутствуют ссылки на файлы обновления.")

    download_dir = Path(tempfile.mkdtemp(prefix="multifora-update-"))
    installer_path = download_dir / str(installer_asset["name"])
    checksum_path = download_dir / str(checksum_asset["name"])
    _download(installer_url, installer_path, timeout)
    _download(checksum_url, checksum_path, timeout)
    _verify_checksum(installer_path, checksum_path)

    subprocess.Popen(
        [
            str(installer_path),
            "/VERYSILENT",
            "/SUPPRESSMSGBOXES",
            "/NORESTART",
            "/CLOSEAPPLICATIONS",
        ],
        close_fds=True,
    )
    return str(installer_asset["name"])
