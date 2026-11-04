"""Safely download and launch an installer for the packaged Windows application.

SHA-256 verifies download integrity, NOT publisher authenticity.
The updater does not verify the publisher identity of the downloaded installer.
"""

import hashlib
import hmac
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from app.core.update_checker import (
    RELEASES_LATEST_API,
    REPO,
    _fetch_json,
    compare_versions,
    get_local_version,
)

_INSTALLER_PREFIX = "Multifora-Setup-"
_USER_AGENT = "multifora-updater"
_MAX_INSTALLER_BYTES = 750 * 1024 * 1024
_MAX_CHECKSUM_BYTES = 4096
_RELEASE_TAG_PATTERN = re.compile(r"v[0-9]+(?:\.[0-9]+){2}(?:-[A-Za-z0-9][A-Za-z0-9.-]*)?\Z")
_RELEASE_ASSET_ROOT = f"https://github.com/{REPO}/releases/download"
_ALLOWED_DOWNLOAD_HOSTS = frozenset(
    {"github.com", "release-assets.githubusercontent.com", "objects.githubusercontent.com"}
)


def automatic_updates_supported() -> bool:
    """Automatic replacement is only safe for the packaged Windows application."""
    return os.name == "nt" and bool(getattr(sys, "frozen", False))


def _find_asset(release: dict, predicate) -> dict:
    assets = release.get("assets", [])
    if not isinstance(assets, list):
        raise RuntimeError("Некорректный список файлов выпуска.")
    for asset in assets:
        if isinstance(asset, dict) and predicate(str(asset.get("name") or "")):
            return asset
    raise RuntimeError("В выпуске не найден установщик Мультифоры.")


def _approved_download_url(url: str) -> bool:
    try:
        parsed = urlsplit(url)
        if parsed.hostname == "github.com" and not parsed.path.startswith(
            f"/{REPO}/releases/download/"
        ):
            return False
        return (
            parsed.scheme == "https"
            and parsed.hostname in _ALLOWED_DOWNLOAD_HOSTS
            and parsed.username is None
            and parsed.password is None
            and parsed.port in (None, 443)
            and bool(parsed.path)
        )
    except ValueError:
        return False


class _SafeReleaseRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not _approved_download_url(newurl):
            raise RuntimeError("Недопустимый адрес перенаправления при загрузке обновления.")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _validate_release_asset(
    asset: dict, *, tag: str, expected_name: str, max_bytes: int
) -> str:
    if asset.get("name") != expected_name:
        raise RuntimeError("Имя файла выпуска не соответствует версии обновления.")
    expected_url = f"{_RELEASE_ASSET_ROOT}/{tag}/{expected_name}"
    url = asset.get("browser_download_url")
    if url != expected_url:
        raise RuntimeError("Файл обновления должен загружаться из официального GitHub Release.")
    size = asset.get("size")
    if isinstance(size, bool) or not isinstance(size, int) or not 0 < size <= max_bytes:
        raise RuntimeError("Некорректный или слишком большой файл обновления.")
    return url


def _download(
    url: str, destination: Path, timeout: int = 30, *,
    max_bytes: int = _MAX_INSTALLER_BYTES,
    expected_size: int | None = None,
) -> None:
    if not _approved_download_url(url):
        raise RuntimeError("Недопустимый адрес загрузки обновления.")
    request = Request(url, headers={"User-Agent": _USER_AGENT})
    opener = build_opener(_SafeReleaseRedirects())
    total = 0
    with opener.open(request, timeout=timeout) as response, destination.open("wb") as output:
        while chunk := response.read(min(1024 * 1024, max_bytes - total + 1)):
            total += len(chunk)
            if total > max_bytes:
                raise RuntimeError("Превышен максимальный размер загружаемого обновления.")
            output.write(chunk)
    if expected_size is not None and total != expected_size:
        raise RuntimeError("Размер скачанного файла не соответствует данным GitHub Release.")


def _verify_checksum(installer: Path, checksum_file: Path) -> None:
    parts = checksum_file.read_text(encoding="utf-8").split()
    if (
        len(parts) != 2
        or not re.fullmatch(r"[0-9a-fA-F]{64}", parts[0])
        or parts[1] != installer.name
    ):
        raise RuntimeError("Контрольная сумма установщика имеет неверный формат или имя файла.")
    expected = parts[0].lower()
    digest = hashlib.sha256()
    with installer.open("rb") as source:
        while chunk := source.read(1024 * 1024):
            digest.update(chunk)
    if not hmac.compare_digest(expected, digest.hexdigest()):
        raise RuntimeError("Контрольная сумма загруженного установщика не совпадает.")


def download_and_launch_latest_installer(
    timeout: int = 30, *, expected_tag: str | None = None
) -> str:
    """Download a bounded, checksum-verified installer after the user consents.

    The temporary directory stays until the launched installer exits. On any
    validation, download or launch failure the directory is removed.
    """
    if not automatic_updates_supported():
        raise RuntimeError(
            "Автоматическое обновление доступно только в установленной Windows-версии."
        )
    release = _fetch_json(RELEASES_LATEST_API, timeout=timeout)
    if not isinstance(release, dict):
        raise RuntimeError("Некорректный ответ GitHub о последнем выпуске.")
    tag = release.get("tag_name")
    if not isinstance(tag, str) or not _RELEASE_TAG_PATTERN.fullmatch(tag):
        raise RuntimeError("Некорректный тег GitHub Release.")
    if expected_tag is not None and tag != expected_tag:
        raise RuntimeError("Версия обновления изменилась. Сначала проверьте обновления ещё раз.")
    if compare_versions(get_local_version(), tag) != -1:
        raise RuntimeError("Доступная версия не новее установленной программы.")

    installer_name = f"{_INSTALLER_PREFIX}{tag[1:]}.exe"
    checksum_name = f"{_INSTALLER_PREFIX}{tag[1:]}.sha256"
    installer_asset = _find_asset(release, lambda name: name == installer_name)
    checksum_asset = _find_asset(release, lambda name: name == checksum_name)
    installer_url = _validate_release_asset(
        installer_asset, tag=tag, expected_name=installer_name,
        max_bytes=_MAX_INSTALLER_BYTES,
    )
    checksum_url = _validate_release_asset(
        checksum_asset, tag=tag, expected_name=checksum_name,
        max_bytes=_MAX_CHECKSUM_BYTES,
    )

    download_dir = Path(tempfile.mkdtemp(prefix="multifora-update-"))
    launched = False
    try:
        installer_path = download_dir / installer_name
        checksum_path = download_dir / checksum_name
        _download(
            installer_url, installer_path, timeout, max_bytes=_MAX_INSTALLER_BYTES,
            expected_size=installer_asset["size"],
        )
        _download(
            checksum_url, checksum_path, timeout, max_bytes=_MAX_CHECKSUM_BYTES,
            expected_size=checksum_asset["size"],
        )
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
        launched = True
        return installer_name
    finally:
        if not launched:
            shutil.rmtree(download_dir, ignore_errors=True)
