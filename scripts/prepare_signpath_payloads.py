"""Stage unsigned Windows binaries as separate, verifiable SignPath input archives.

These artifacts are for SignPath Foundation onboarding, NOT signed releases.
No SignPath API endpoint, signing identity, or signing action is assumed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import tempfile
import zipfile
from pathlib import Path

_MAX_INPUT_BYTES = 750 * 1024 * 1024
_INSTALLER_PATTERN = re.compile(
    r"Multifora-Setup-[0-9]+(?:\.[0-9]+){2}\.exe\Z"
)
_PAYLOADS = (
    ("application", "Multifora-app-unsigned.zip"),
    ("installer", "Multifora-installer-unsigned.zip"),
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _validate(path: Path, *, installer: bool) -> None:
    good_name = (
        bool(_INSTALLER_PATTERN.fullmatch(path.name))
        if installer
        else path.name == "Multifora.exe"
    )
    if not good_name or path.is_symlink() or not path.is_file():
        raise ValueError(f"Unexpected or unsafe Windows executable: {path}")
    size = path.stat().st_size
    if not 0 < size <= _MAX_INPUT_BYTES:
        raise ValueError(f"Invalid size for Windows executable: {path}")


def prepare_payloads(app: Path, installer: Path, output: Path) -> dict:
    """Write two one-file unsigned ZIP archives and a detached manifest."""
    _validate(app, installer=False)
    _validate(installer, installer=True)
    if output.exists():
        raise FileExistsError(f"SignPath staging output already exists: {output}")

    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix="signpath-staging-", dir=output.parent))
    try:
        manifest = {"signed": False, "purpose": "SignPath Foundation onboarding", "files": []}
        for (kind, archive_name), source in zip(_PAYLOADS, (app, installer), strict=True):
            archive_path = staging / archive_name
            expected = _sha256(source)
            with zipfile.ZipFile(
                archive_path, "w", compression=zipfile.ZIP_DEFLATED,
                compresslevel=6,
            ) as archive:
                archive.write(source, arcname=source.name)
            # A signing request must contain exactly the intended file; do not
            # silently include the full application bundle or an extra payload.
            with zipfile.ZipFile(archive_path) as archive:
                if archive.namelist() != [source.name] or archive.testzip() is not None:
                    raise RuntimeError("The staged SignPath archive is not valid.")
                digest = hashlib.sha256(archive.read(source.name)).hexdigest()
                if digest != expected:
                    raise RuntimeError("Staged SignPath content differs from its source.")
            manifest["files"].append(
                {
                    "kind": kind,
                    "archive": archive_name,
                    "member": source.name,
                    "sha256": expected,
                    "size": source.stat().st_size,
                }
            )
        (staging / "manifest.json").write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        os.rename(staging, output)
        return manifest
    finally:
        if staging.exists():
            shutil.rmtree(staging)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--app", type=Path, required=True)
    parser.add_argument("--installer", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    manifest = prepare_payloads(args.app, args.installer, args.output)
    for item in manifest["files"]:
        print(f"Unsigned SignPath input: {item['archive']} ({item['member']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
