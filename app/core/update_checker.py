import hashlib
import json
import os
import re
import subprocess
import tempfile
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.core.app_identity import APP_VERSION
from app.core.app_utils import _log_ignored_error

REPO = "VseMirka200/multifora"
RELEASES_LATEST_API = f"https://api.github.com/repos/{REPO}/releases/latest"
TAGS_API = f"https://api.github.com/repos/{REPO}/tags"
RELEASES_PAGE = f"https://github.com/{REPO}/releases/latest"
REPO_PAGE = f"https://github.com/{REPO}"
ISSUES_PAGE = f"https://github.com/{REPO}/issues/new/choose"
_INSTALLER_NAME_RE = re.compile(r"^Multifora-Setup-.*\.exe$", re.IGNORECASE)
_SHA256_RE = re.compile(r"\b([0-9a-fA-F]{64})\b")


def _parse_version(version: str) -> tuple[int, ...]:
    if not version:
        return ()
    parts = re.findall(r"\d+", str(version))
    return tuple(int(p) for p in parts)


def compare_versions(current_version: str, latest_version: str) -> int | None:
    cur = _parse_version(current_version)
    lat = _parse_version(latest_version)
    if not cur or not lat:
        return None

    max_len = max(len(cur), len(lat))
    cur = cur + (0,) * (max_len - len(cur))
    lat = lat + (0,) * (max_len - len(lat))
    if cur < lat:
        return -1
    if cur > lat:
        return 1
    return 0


def _fetch_json(url: str, timeout: int = 6):
    req = Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "multifora-update-checker",
        },
    )
    with urlopen(req, timeout=timeout) as response:
        payload = response.read().decode("utf-8", errors="replace")
    return json.loads(payload)


def get_local_version() -> str:
    from_env = os.environ.get("MULTIFORA_VERSION")
    if from_env:
        return from_env.strip()

    return APP_VERSION or "unknown"


def _release_asset(asset: dict) -> dict | None:
    name = str(asset.get("name") or "").strip()
    url = str(asset.get("browser_download_url") or "").strip()
    if not name or not url:
        return None
    return {
        "name": name,
        "url": url,
        "size": int(asset.get("size") or 0),
        "digest": str(asset.get("digest") or "").strip(),
    }


def _find_installer(assets: list[dict]) -> dict | None:
    for raw_asset in assets:
        asset = _release_asset(raw_asset or {})
        if asset and _INSTALLER_NAME_RE.fullmatch(asset["name"]):
            return asset
    return None


def _find_checksum(assets: list[dict], installer_name: str) -> dict | None:
    expected_names = {
        f"{installer_name}.sha256".lower(),
        f"{os.path.splitext(installer_name)[0]}.sha256".lower(),
    }
    for raw_asset in assets:
        asset = _release_asset(raw_asset or {})
        if asset and asset["name"].lower() in expected_names:
            return asset
    return None


def fetch_github_latest(timeout: int = 6) -> dict:
    try:
        latest = _fetch_json(RELEASES_LATEST_API, timeout=timeout)
        tag = str(latest.get("tag_name") or "").strip()
        html_url = str(latest.get("html_url") or RELEASES_PAGE).strip()
        if tag:
            assets = latest.get("assets") or []
            installer = _find_installer(assets)
            if installer:
                installer["checksum"] = _find_checksum(assets, installer["name"])
            return {
                "latest_version": tag,
                "url": html_url,
                "source": "release",
                "installer": installer,
            }
    except HTTPError as e:
        if e.code != 404:
            raise
    except URLError:
        raise

    tags = _fetch_json(TAGS_API, timeout=timeout)
    if isinstance(tags, list) and tags:
        first = tags[0] or {}
        tag_name = str(first.get("name") or "").strip()
        if tag_name:
            return {
                "latest_version": tag_name,
                "url": f"https://github.com/{REPO}/releases",
                "source": "tag",
            }

    raise RuntimeError("Не удалось получить release/tag из GitHub.")


def check_for_updates(current_version: str | None = None, timeout: int = 6) -> dict:
    current = (current_version or "").strip() or get_local_version()
    latest_data = fetch_github_latest(timeout=timeout)
    latest_version = latest_data["latest_version"]
    cmp = compare_versions(current, latest_version)
    return {
        "repo": REPO,
        "current_version": current,
        "latest_version": latest_version,
        "url": latest_data.get("url") or RELEASES_PAGE,
        "source": latest_data.get("source") or "unknown",
        "installer": latest_data.get("installer"),
        "comparison": cmp,
        "has_update": cmp == -1 if cmp is not None else None,
    }


def _expected_sha256(installer: dict, timeout: int) -> str:
    digest = str(installer.get("digest") or "").strip().lower()
    if digest.startswith("sha256:") and _SHA256_RE.fullmatch(digest[7:]):
        return digest[7:]

    checksum = installer.get("checksum") or {}
    checksum_url = str(checksum.get("url") or "").strip()
    if not checksum_url:
        raise RuntimeError("В релизе отсутствует контрольная сумма установщика.")

    request = Request(checksum_url, headers={"User-Agent": "multifora-updater"})
    with urlopen(request, timeout=timeout) as response:
        contents = response.read(4096).decode("ascii", errors="ignore")
    match = _SHA256_RE.search(contents)
    if not match:
        raise RuntimeError("Не удалось прочитать контрольную сумму установщика.")
    return match.group(1).lower()


def get_update_download_dir() -> str:
    base_dir = os.environ.get("LOCALAPPDATA") or tempfile.gettempdir()
    return os.path.join(base_dir, "Multifora", "updates")


def download_update_installer(
    update: dict,
    *,
    destination_dir: str | None = None,
    timeout: int = 60,
) -> dict:
    installer = update.get("installer") or {}
    name = os.path.basename(str(installer.get("name") or ""))
    url = str(installer.get("url") or "").strip()
    if not _INSTALLER_NAME_RE.fullmatch(name) or not url:
        raise RuntimeError("В релизе не найден установщик Мультифоры для Windows.")

    expected_hash = _expected_sha256(installer, timeout)
    target_dir = os.path.abspath(destination_dir or get_update_download_dir())
    os.makedirs(target_dir, exist_ok=True)
    target_path = os.path.join(target_dir, name)
    partial_path = f"{target_path}.part"
    request = Request(url, headers={"User-Agent": "multifora-updater"})
    actual_hash = hashlib.sha256()

    try:
        with urlopen(request, timeout=timeout) as response, open(partial_path, "wb") as stream:
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                stream.write(chunk)
                actual_hash.update(chunk)

        actual_digest = actual_hash.hexdigest().lower()
        if actual_digest != expected_hash:
            raise RuntimeError("Контрольная сумма установщика не совпадает. Загрузка удалена.")
        os.replace(partial_path, target_path)
    finally:
        if os.path.exists(partial_path):
            try:
                os.remove(partial_path)
            except OSError as error:
                _log_ignored_error("download_update_installer.cleanup", error)

    return {
        "path": target_path,
        "version": update.get("latest_version"),
        "sha256": expected_hash,
    }


def launch_update_installer(installer_path: str) -> None:
    path = os.path.abspath(installer_path)
    if os.name != "nt":
        raise RuntimeError("Автоматическая установка обновлений поддерживается только в Windows.")
    if not os.path.isfile(path) or not path.lower().endswith(".exe"):
        raise RuntimeError("Скачанный установщик не найден.")
    subprocess.Popen([path], close_fds=True)
