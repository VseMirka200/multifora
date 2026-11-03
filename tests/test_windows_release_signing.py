"""Static and Windows regression checks for optional Authenticode release signing."""

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RELEASE_WORKFLOW = ROOT / ".github" / "workflows" / "release.yml"
SIGN_SCRIPT = ROOT / "scripts" / "sign_windows_artifact.ps1"
VERIFY_SCRIPT = ROOT / "scripts" / "verify_authenticode.ps1"


class ReleaseSigningWorkflowTests(unittest.TestCase):
    def test_exe_signed_before_installer_build_and_hashes(self):
        workflow = RELEASE_WORKFLOW.read_text(encoding="utf-8")
        self.assertLess(
            workflow.index("Подписать и проверить Multifora.exe"),
            workflow.index("      - name: Собрать установщик Windows"),
        )
        self.assertLess(
            workflow.index("Подписать и проверить установщик Windows"),
            workflow.index("      - name: Упаковать файлы и подготовить данные выпуска"),
        )
        self.assertIn("sha256sum -c", workflow)
        self.assertIn('gh release view "$TAG"', workflow)

    def test_signature_is_opt_in_and_requires_expected_identity(self):
        workflow = RELEASE_WORKFLOW.read_text(encoding="utf-8")
        self.assertEqual(workflow.count("vars.MULTIFORA_SIGN_RELEASE == 'true'"), 2)
        self.assertIn("MULTIFORA_SIGNER_CERT_SHA256", workflow)
        self.assertIn("MULTIFORA_CODESIGN_PFX_BASE64", workflow)
        self.assertIn("MULTIFORA_CODESIGN_PFX_PASSWORD", workflow)
        self.assertIn("Missing signing secrets", workflow)
        self.assertIn("this release will be UNSIGNED", workflow)

    def test_signing_never_passes_password_in_signtool_arguments(self):
        script = SIGN_SCRIPT.read_text(encoding="utf-8")
        self.assertIn("Import-PfxCertificate", script)
        self.assertIn("/sha1 $signerCertificate.Thumbprint", script)
        self.assertNotIn("/p $pfxPassword", script)
        self.assertIn("verify_authenticode.ps1", script)
        self.assertIn("Remove-Item -LiteralPath $temporaryDir -Recurse -Force", script)

    def test_signature_verification_rejects_bad_status_or_wrong_signer(self):
        script = VERIFY_SCRIPT.read_text(encoding="utf-8")
        self.assertIn("Get-AuthenticodeSignature", script)
        self.assertIn("[System.Management.Automation.SignatureStatus]::Valid", script)
        self.assertIn("$signature.SignerCertificate.RawData", script)
        self.assertIn("$ExpectedCertificateSha256.ToUpperInvariant()", script)

    @unittest.skipUnless(
        os.name == "nt" and shutil.which("pwsh"),
        "Authenticode verification requires Windows PowerShell 7",
    )
    def test_unsigned_binary_is_rejected_by_verifier(self):
        with tempfile.TemporaryDirectory() as directory:
            file_path = Path(directory) / "unsigned.exe"
            file_path.write_bytes(b"MZ" + bytes(2048))
            result = subprocess.run(
                [
                    "pwsh",
                    "-NoProfile",
                    "-NonInteractive",
                    "-File",
                    str(VERIFY_SCRIPT),
                    "-FilePath",
                    str(file_path),
                    "-ExpectedCertificateSha256",
                    "0" * 64,
                ],
                capture_output=True,
                text=True,
                check=False,
                timeout=30,
            )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Authenticode verification failed", result.stderr)


if __name__ == "__main__":
    unittest.main()
