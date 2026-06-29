import os
import unittest
from unittest.mock import patch

from app.core import update_checker


class UpdateCheckerTests(unittest.TestCase):
    def test_get_local_version_without_env_or_git_returns_unknown(self):
        with patch.dict(os.environ, {}, clear=True):
            with patch("app.core.update_checker.subprocess.run", side_effect=FileNotFoundError):
                self.assertEqual(update_checker.get_local_version(), "unknown")

    def test_check_for_updates_uses_mocked_latest_data(self):
        latest = {"latest_version": "v1.2.0", "url": "https://example.test/release", "source": "release"}
        with patch("app.core.update_checker.fetch_github_latest", return_value=latest):
            result = update_checker.check_for_updates(current_version="v1.1.0")

        self.assertTrue(result["has_update"])
        self.assertEqual(result["latest_version"], "v1.2.0")
        self.assertEqual(result["source"], "release")
