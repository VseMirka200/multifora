import hashlib
import os
import tempfile
import unittest
from unittest.mock import patch

from app.core import update_checker
from app.core.app_identity import APP_VERSION


class _BytesResponse:
    def __init__(self, payload: bytes):
        self._payload = payload
        self._offset = 0

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self, size=-1):
        if size is None or size < 0:
            size = len(self._payload) - self._offset
        chunk = self._payload[self._offset : self._offset + size]
        self._offset += len(chunk)
        return chunk


class UpdateCheckerTests(unittest.TestCase):
    def test_get_local_version_uses_app_version_and_environment_override(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(update_checker.get_local_version(), APP_VERSION)
        with patch.dict(os.environ, {"MULTIFORA_VERSION": "v2.0.0"}, clear=True):
            self.assertEqual(update_checker.get_local_version(), "v2.0.0")

    def test_fetch_latest_release_selects_windows_installer_and_checksum(self):
        release = {
            "tag_name": "v1.2.0",
            "html_url": "https://example.test/release",
            "assets": [
                {
                    "name": "Multifora-v1.2.0-windows-x64.zip",
                    "browser_download_url": "https://example.test/archive",
                },
                {
                    "name": "Multifora-Setup-1.2.0.exe",
                    "browser_download_url": "https://example.test/installer",
                    "size": 123,
                },
                {
                    "name": "Multifora-Setup-1.2.0.sha256",
                    "browser_download_url": "https://example.test/checksum",
                },
            ],
        }
        with patch("app.core.update_checker._fetch_json", return_value=release):
            result = update_checker.fetch_github_latest()

        self.assertEqual(result["installer"]["name"], "Multifora-Setup-1.2.0.exe")
        self.assertEqual(
            result["installer"]["checksum"]["url"],
            "https://example.test/checksum",
        )

    def test_check_for_updates_uses_mocked_latest_data(self):
        latest = {
            "latest_version": "v1.2.0",
            "url": "https://example.test/release",
            "source": "release",
            "installer": {"name": "Multifora-Setup-1.2.0.exe"},
        }
        with patch("app.core.update_checker.fetch_github_latest", return_value=latest):
            result = update_checker.check_for_updates(current_version="v1.1.0")

        self.assertTrue(result["has_update"])
        self.assertEqual(result["latest_version"], "v1.2.0")
        self.assertEqual(result["source"], "release")
        self.assertEqual(result["installer"], latest["installer"])

    def test_download_installer_verifies_checksum_before_publishing_file(self):
        payload = b"installer contents"
        digest = hashlib.sha256(payload).hexdigest()
        update = {
            "latest_version": "v1.2.0",
            "installer": {
                "name": "Multifora-Setup-1.2.0.exe",
                "url": "https://example.test/installer",
                "checksum": {"url": "https://example.test/checksum"},
            },
        }
        responses = [
            _BytesResponse(f"{digest}  Multifora-Setup-1.2.0.exe".encode("ascii")),
            _BytesResponse(payload),
        ]
        with (
            tempfile.TemporaryDirectory() as tmp_dir,
            patch(
                "app.core.update_checker.urlopen",
                side_effect=responses,
            ),
        ):
            result = update_checker.download_update_installer(
                update,
                destination_dir=tmp_dir,
            )
            with open(result["path"], "rb") as stream:
                self.assertEqual(stream.read(), payload)

        self.assertEqual(result["sha256"], digest)
        self.assertEqual(result["version"], "v1.2.0")

    def test_download_installer_removes_file_when_checksum_is_wrong(self):
        update = {
            "latest_version": "v1.2.0",
            "installer": {
                "name": "Multifora-Setup-1.2.0.exe",
                "url": "https://example.test/installer",
                "digest": f"sha256:{'0' * 64}",
            },
        }
        with (
            tempfile.TemporaryDirectory() as tmp_dir,
            patch(
                "app.core.update_checker.urlopen",
                return_value=_BytesResponse(b"damaged installer"),
            ),
        ):
            with self.assertRaisesRegex(RuntimeError, "Контрольная сумма"):
                update_checker.download_update_installer(update, destination_dir=tmp_dir)
            self.assertEqual(os.listdir(tmp_dir), [])

    def test_launch_installer_starts_downloaded_executable_on_windows(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            installer_path = os.path.join(tmp_dir, "Multifora-Setup-1.2.0.exe")
            with open(installer_path, "wb") as stream:
                stream.write(b"test")
            with (
                patch("app.core.update_checker.os.name", "nt"),
                patch("app.core.update_checker.subprocess.Popen") as popen,
            ):
                update_checker.launch_update_installer(installer_path)

        popen.assert_called_once_with([os.path.abspath(installer_path)], close_fds=True)


if __name__ == "__main__":
    unittest.main()
