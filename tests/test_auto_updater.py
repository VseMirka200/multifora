import hashlib
import unittest
from unittest.mock import MagicMock, patch

from app.core import auto_updater


class AutoUpdaterTests(unittest.TestCase):
    def test_verify_checksum_accepts_matching_file(self):
        installer = MagicMock()
        installer.open.return_value.__enter__.return_value.read.side_effect = [b"installer", b""]
        checksum = MagicMock()
        checksum.read_text.return_value = hashlib.sha256(b"installer").hexdigest()

        auto_updater._verify_checksum(installer, checksum)

    def test_verify_checksum_rejects_tampered_file(self):
        installer = MagicMock()
        installer.open.return_value.__enter__.return_value.read.side_effect = [b"tampered", b""]
        checksum = MagicMock()
        checksum.read_text.return_value = "0" * 64

        with self.assertRaisesRegex(RuntimeError, "Контрольная сумма"):
            auto_updater._verify_checksum(installer, checksum)

    def test_download_and_launch_requires_packaged_windows_app(self):
        with patch.object(auto_updater, "automatic_updates_supported", return_value=False):
            with self.assertRaisesRegex(RuntimeError, "установленной Windows-версии"):
                auto_updater.download_and_launch_latest_installer()

    def test_download_and_launch_uses_verified_installer(self):
        release = {
            "assets": [
                {
                    "name": "Multifora-Setup-1.1.0.exe",
                    "browser_download_url": "https://example.test/setup.exe",
                },
                {
                    "name": "Multifora-Setup-1.1.0.sha256",
                    "browser_download_url": "https://example.test/setup.sha256",
                },
            ]
        }

        with (
            patch.object(auto_updater, "automatic_updates_supported", return_value=True),
            patch.object(auto_updater, "_fetch_json", return_value=release),
            patch.object(auto_updater, "_download"),
            patch.object(auto_updater, "_verify_checksum"),
            patch.object(auto_updater.tempfile, "mkdtemp", return_value="C:/temp/update"),
            patch.object(auto_updater.subprocess, "Popen") as popen,
        ):
            name = auto_updater.download_and_launch_latest_installer()

        self.assertEqual(name, "Multifora-Setup-1.1.0.exe")
        self.assertEqual(
            popen.call_args.args[0][1:],
            ["/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/CLOSEAPPLICATIONS"],
        )
