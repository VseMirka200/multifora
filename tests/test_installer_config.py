import unittest
from pathlib import Path


class InstallerConfigTests(unittest.TestCase):
    def test_default_installation_is_in_program_files_with_admin_rights(self):
        installer = (Path(__file__).parents[1] / "scripts" / "installer.iss").read_text(encoding="utf-8")

        self.assertIn("DefaultDirName={autopf}\\{#MyAppName}", installer)
        self.assertIn("PrivilegesRequired=admin", installer)
        self.assertIn("UsePreviousAppDir=yes", installer)

    def test_installer_shows_and_installs_license_and_program_info(self):
        installer = (Path(__file__).parents[1] / "scripts" / "installer.iss").read_text(encoding="utf-8")

        self.assertIn("LicenseFile=..\\LICENSE", installer)
        self.assertIn("InfoAfterFile=..\\docs\\project\\INSTALLER_INFO.txt", installer)
        self.assertIn('Source: "..\\LICENSE"; DestDir: "{app}"', installer)

    def test_silent_install_script_uses_inno_setup_silent_flags(self):
        script = (Path(__file__).parents[1] / "scripts" / "install_silently.bat").read_text(encoding="utf-8")

        self.assertIn("Multifora-Setup-*.exe", script)
        self.assertIn("/VERYSILENT", script)
        self.assertIn("/SUPPRESSMSGBOXES", script)
        self.assertIn("/NORESTART", script)
        self.assertIn("/SP-", script)

    def test_installer_copies_complete_bundle_and_requires_office_helper(self):
        root = Path(__file__).parents[1]
        installer = (root / "scripts" / "installer.iss").read_text(encoding="utf-8")
        packaging = (root / "scripts" / "build_installer.bat").read_text(encoding="utf-8")
        self.assertIn('#define MyAppSource "..\\dist\\Multifora"', installer)
        self.assertIn('Source: "{#MyAppSource}\\*"', installer)
        self.assertIn("recursesubdirs", installer)
        self.assertIn("core/workers/office_word.ps1", (root / "Multifora.spec").read_text(encoding="utf-8"))
        self.assertIn("office_word.ps1", packaging)


if __name__ == "__main__":
    unittest.main()
