import hashlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.request import Request

from app.core import auto_updater


def _release(tag="v1.1.0", *, installer_size=9, checksum_size=93):
    prefix = f"https://github.com/VseMirka200/multifora/releases/download/{tag}"
    version = tag[1:]
    installer = f"Multifora-Setup-{version}.exe"
    checksum = f"Multifora-Setup-{version}.sha256"
    return {
        "tag_name": tag,
        "assets": [
            {
                "name": installer,
                "size": installer_size,
                "browser_download_url": f"{prefix}/{installer}",
            },
            {
                "name": checksum,
                "size": checksum_size,
                "browser_download_url": f"{prefix}/{checksum}",
            },
        ],
    }


class AutoUpdaterTests(unittest.TestCase):
    def test_verify_checksum_accepts_matching_file(self):
        with tempfile.TemporaryDirectory() as directory:
            installer = Path(directory, "Multifora-Setup-1.1.0.exe")
            checksum = installer.with_suffix(".sha256")
            installer.write_bytes(b"installer")
            digest = hashlib.sha256(b"installer").hexdigest()
            checksum.write_text(f"{digest}  {installer.name}\n", encoding="utf-8")
            auto_updater._verify_checksum(installer, checksum)

    def test_verify_checksum_rejects_tampered_file(self):
        with tempfile.TemporaryDirectory() as directory:
            installer = Path(directory, "Multifora-Setup-1.1.0.exe")
            checksum = installer.with_suffix(".sha256")
            installer.write_bytes(b"tampered")
            checksum.write_text(f"{'0' * 64}  {installer.name}", encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "Контрольная сумма"):
                auto_updater._verify_checksum(installer, checksum)

    def test_verify_checksum_rejects_other_filename_and_invalid_digest(self):
        with tempfile.TemporaryDirectory() as directory:
            installer = Path(directory, "Multifora-Setup-1.1.0.exe")
            checksum = installer.with_suffix(".sha256")
            installer.write_bytes(b"installer")
            for value in ("abc  installer.exe", f"{'a' * 64}  other.exe"):
                with self.subTest(value=value):
                    checksum.write_text(value, encoding="utf-8")
                    with self.assertRaisesRegex(RuntimeError, "Контрольная сумма"):
                        auto_updater._verify_checksum(installer, checksum)

    def test_download_and_launch_requires_packaged_windows_app(self):
        with patch.object(
            auto_updater, "automatic_updates_supported", return_value=False
        ):
            with self.assertRaisesRegex(RuntimeError, "установленной Windows-версии"):
                auto_updater.download_and_launch_latest_installer()

    def test_download_and_launch_uses_verified_installer(self):
        release = _release()
        with (
            patch.object(auto_updater, "automatic_updates_supported", return_value=True),
            patch.object(auto_updater, "get_local_version", return_value="1.0.3"),
            patch.object(auto_updater, "_fetch_json", return_value=release),
            patch.object(auto_updater, "_download") as download,
            patch.object(auto_updater, "_verify_checksum") as verify,
            patch.object(
                auto_updater.tempfile, "mkdtemp", return_value="C:/temp/update"
            ),
            patch.object(auto_updater.subprocess, "Popen") as popen,
        ):
            name = auto_updater.download_and_launch_latest_installer(
                expected_tag="v1.1.0"
            )
        self.assertEqual(name, "Multifora-Setup-1.1.0.exe")
        self.assertEqual(download.call_count, 2)
        verify.assert_called_once()
        self.assertEqual(
            popen.call_args.args[0][1:],
            ["/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/CLOSEAPPLICATIONS"],
        )

    def test_unexpected_release_tag_fails_before_download(self):
        for tag in ("v1.1.0/../../other", "some-branch", "v../evil"):
            with self.subTest(tag=tag):
                with (
                    patch.object(
                        auto_updater, "automatic_updates_supported", return_value=True
                    ),
                    patch.object(auto_updater, "_fetch_json", return_value=_release(tag)),
                    patch.object(auto_updater, "_download") as download,
                ):
                    with self.assertRaisesRegex(RuntimeError, "тег"):
                        auto_updater.download_and_launch_latest_installer()
                    download.assert_not_called()

    def test_changed_release_version_fails_before_download(self):
        with (
            patch.object(auto_updater, "automatic_updates_supported", return_value=True),
            patch.object(auto_updater, "_fetch_json", return_value=_release()),
            patch.object(auto_updater, "_download") as download,
        ):
            with self.assertRaisesRegex(RuntimeError, "изменилась"):
                auto_updater.download_and_launch_latest_installer(
                    expected_tag="v1.2.0"
                )
            download.assert_not_called()

    def test_equal_or_older_version_is_rejected(self):
        with (
            patch.object(auto_updater, "automatic_updates_supported", return_value=True),
            patch.object(auto_updater, "get_local_version", return_value="1.1.0"),
            patch.object(auto_updater, "_fetch_json", return_value=_release()),
        ):
            with self.assertRaisesRegex(RuntimeError, "не новее"):
                auto_updater.download_and_launch_latest_installer()

    def test_untrusted_asset_url_is_rejected(self):
        release = _release()
        release["assets"][0]["browser_download_url"] = (
            "https://example.com/evil.exe"
        )
        with (
            patch.object(auto_updater, "automatic_updates_supported", return_value=True),
            patch.object(auto_updater, "get_local_version", return_value="1.0.3"),
            patch.object(auto_updater, "_fetch_json", return_value=release),
            patch.object(auto_updater, "_download") as download,
        ):
            with self.assertRaisesRegex(RuntimeError, "GitHub Release"):
                auto_updater.download_and_launch_latest_installer()
            download.assert_not_called()

    def test_oversized_release_asset_is_rejected(self):
        release = _release(installer_size=auto_updater._MAX_INSTALLER_BYTES + 1)
        with (
            patch.object(auto_updater, "automatic_updates_supported", return_value=True),
            patch.object(auto_updater, "get_local_version", return_value="1.0.3"),
            patch.object(auto_updater, "_fetch_json", return_value=release),
            patch.object(auto_updater, "_download") as download,
        ):
            with self.assertRaisesRegex(RuntimeError, "слишком большой"):
                auto_updater.download_and_launch_latest_installer()
            download.assert_not_called()

    def test_download_rejects_non_github_url(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(RuntimeError, "адрес"):
                auto_updater._download(
                    "http://example.com/installer.exe", Path(directory, "file.exe")
                )

    def test_download_rejects_oversized_stream(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(auto_updater, "build_opener") as builder:
                builder.return_value.open.return_value = io.BytesIO(b"0123456")
                with self.assertRaisesRegex(RuntimeError, "размер"):
                    auto_updater._download(
                        "https://github.com/owner/repo/releases/download/v1/file.exe",
                        Path(directory, "file.exe"), max_bytes=5,
                    )

    def test_download_rejects_truncated_stream(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(auto_updater, "build_opener") as builder:
                builder.return_value.open.return_value = io.BytesIO(b"short")
                with self.assertRaisesRegex(RuntimeError, "Размер"):
                    auto_updater._download(
                        "https://github.com/owner/repo/releases/download/v1/file.exe",
                        Path(directory, "file.exe"), expected_size=9,
                    )

    def test_redirect_to_external_host_is_rejected(self):
        request = Request(
            "https://github.com/VseMirka200/multifora/releases/download/v1.1.0/setup.exe"
        )
        handler = auto_updater._SafeReleaseRedirects()
        for target in (
            "http://release-assets.githubusercontent.com/file",
            "https://example.com/file",
            "https://github.com.evil.example/file",
        ):
            with self.subTest(target=target):
                with self.assertRaisesRegex(RuntimeError, "перенаправления"):
                    handler.redirect_request(request, None, 302, "Found", {}, target)

    def test_expected_github_cdn_redirect_is_allowed(self):
        request = Request(
            "https://github.com/VseMirka200/multifora/releases/download/v1.1.0/setup.exe"
        )
        redirect = auto_updater._SafeReleaseRedirects().redirect_request(
            request, None, 302, "Found", {},
            "https://release-assets.githubusercontent.com/asset?se=expiry",
        )
        self.assertEqual(redirect.host, "release-assets.githubusercontent.com")

    def test_failure_cleans_staging_directory_without_launch(self):
        with (
            patch.object(auto_updater, "automatic_updates_supported", return_value=True),
            patch.object(auto_updater, "get_local_version", return_value="1.0.3"),
            patch.object(auto_updater, "_fetch_json", return_value=_release()),
            patch.object(
                auto_updater.tempfile, "mkdtemp", return_value="C:/temp/update"
            ),
            patch.object(auto_updater, "_download", side_effect=OSError("network down")),
            patch.object(auto_updater.shutil, "rmtree") as cleanup,
            patch.object(auto_updater.subprocess, "Popen") as popen,
        ):
            with self.assertRaisesRegex(OSError, "network down"):
                auto_updater.download_and_launch_latest_installer()
            popen.assert_not_called()
            cleanup.assert_called_once()


if __name__ == "__main__":
    unittest.main()
