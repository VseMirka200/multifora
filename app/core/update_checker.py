import json
import os
import re
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.core.app_identity import APP_VERSION

REPO = "VseMirka200/multifora"
RELEASES_LATEST_API = f"https://api.github.com/repos/{REPO}/releases/latest"
TAGS_API = f"https://api.github.com/repos/{REPO}/tags"
REPO_PAGE = f"https://github.com/{REPO}"


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


def fetch_github_latest(timeout: int = 6) -> str:
    try:
        latest = _fetch_json(RELEASES_LATEST_API, timeout=timeout)
        tag = str(latest.get("tag_name") or "").strip()
        if tag:
            return tag
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
            return tag_name

    raise RuntimeError("Не удалось получить release/tag из GitHub.")


def check_for_updates(current_version: str | None = None, timeout: int = 6) -> dict:
    current = (current_version or "").strip() or get_local_version()
    latest_version = fetch_github_latest(timeout=timeout)
    cmp = compare_versions(current, latest_version)
    return {
        "current_version": current,
        "latest_version": latest_version,
        "comparison": cmp,
    }
