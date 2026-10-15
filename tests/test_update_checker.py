import os
import unittest
from unittest.mock import patch

from app.core import update_checker
from app.core.app_identity import APP_VERSION


class UpdateCheckerTests(unittest.TestCase):
    def test_get_local_version_uses_app_version_and_environment_override(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(update_checker.get_local_version(), APP_VERSION)
        with patch.dict(os.environ, {"MULTIFORA_VERSION": "v2.0.0"}, clear=True):
            self.assertEqual(update_checker.get_local_version(), "v2.0.0")

    def test_fetch_latest_release_returns_tag(self):
        release = {
            "tag_name": "v1.2.0",
        }
        with patch("app.core.update_checker._fetch_json", return_value=release):
            result = update_checker.fetch_github_latest()

        self.assertEqual(result, "v1.2.0")

    def test_check_for_updates_uses_mocked_latest_data(self):
        latest = "v1.2.0"
        with patch("app.core.update_checker.fetch_github_latest", return_value=latest):
            result = update_checker.check_for_updates(current_version="v1.1.0")

        self.assertEqual(result["comparison"], -1)
        self.assertEqual(result["latest_version"], "v1.2.0")


if __name__ == "__main__":
    unittest.main()
