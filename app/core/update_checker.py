# -*- coding: utf-8 -*-
import json
import os
import re
import subprocess
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


REPO = "VseMirka200/multifora"
RELEASES_LATEST_API = f"https://api.github.com/repos/{REPO}/releases/latest"
TAGS_API = f"https://api.github.com/repos/{REPO}/tags"
RELEASES_PAGE = f"https://github.com/{REPO}/releases/latest"
REPO_PAGE = f"https://github.com/{REPO}"


def _parse_version(version: str) -> tuple[int, ...]:
    if not version:
        return tuple()
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

    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    try:
        res = subprocess.run(
            ["git", "describe", "--tags", "--abbrev=0"],
            cwd=base_dir,
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
        tag = (res.stdout or "").strip()
        if res.returncode == 0 and tag:
            return tag
    except Exception:
        pass

    try:
        res = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=base_dir,
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
        commit = (res.stdout or "").strip()
        if res.returncode == 0 and commit:
            return f"dev-{commit}"
    except Exception:
        pass
    return "unknown"


def fetch_github_latest(timeout: int = 6) -> dict:
    try:
        latest = _fetch_json(RELEASES_LATEST_API, timeout=timeout)
        tag = str(latest.get("tag_name") or "").strip()
        html_url = str(latest.get("html_url") or RELEASES_PAGE).strip()
        if tag:
            return {"latest_version": tag, "url": html_url, "source": "release"}
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
        "comparison": cmp,
        "has_update": cmp == -1 if cmp is not None else None,
    }
