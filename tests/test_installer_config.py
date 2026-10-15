import unittest
from pathlib import Path


class InstallerConfigTests(unittest.TestCase):
    def test_default_installation_is_in_program_files_with_admin_rights(self):
        installer = (Path(__file__).parents[1] / "scripts" / "installer.iss").read_text(
            encoding="utf-8"
        )

        self.assertIn("DefaultDirName={autopf}\\{#MyAppName}", installer)
        self.assertIn("PrivilegesRequired=admin", installer)
        self.assertIn("UsePreviousAppDir=yes", installer)


if __name__ == "__main__":
    unittest.main()
