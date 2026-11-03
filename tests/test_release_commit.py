"""Regression tests for the release-tag ancestry gate."""

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from scripts.verify_release_commit import verify_release_commit


def _git(cwd: Path, *arguments: str) -> str:
    completed = subprocess.run(
        ["git", *arguments],
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=True,
    )
    return completed.stdout.strip()


@unittest.skipUnless(shutil.which("git"), "Git required for release ancestry tests")
class ReleaseCommitTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="multifora-release-test-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.remote = self.root / "remote.git"
        self.checkout = self.root / "checkout"

        _git(self.root, "init", "--bare", str(self.remote))
        _git(self.root, "init", "-b", "main", str(self.checkout))
        _git(self.checkout, "config", "user.name", "Multifora Test")
        _git(self.checkout, "config", "user.email", "release-test@example.invalid")
        _git(self.checkout, "config", "commit.gpgsign", "false")
        _git(self.checkout, "remote", "add", "origin", str(self.remote))
        self._commit("approved main commit")
        _git(self.checkout, "push", "-u", "origin", "main")

    def _commit(self, text: str) -> str:
        (self.checkout / "content.txt").write_text(text, encoding="utf-8")
        _git(self.checkout, "add", "content.txt")
        _git(self.checkout, "commit", "-m", text)
        return _git(self.checkout, "rev-parse", "HEAD")

    def test_tag_on_main_is_allowed(self) -> None:
        commit = _git(self.checkout, "rev-parse", "HEAD")
        _git(self.checkout, "tag", "v1.0.4")
        _git(self.checkout, "checkout", "--detach", "v1.0.4")
        self.assertEqual(
            verify_release_commit("v1.0.4", cwd=self.checkout), commit
        )

    def test_annotated_tag_on_main_is_allowed(self) -> None:
        commit = _git(self.checkout, "rev-parse", "HEAD")
        _git(self.checkout, "tag", "-a", "v1.0.4", "-m", "release")
        _git(self.checkout, "checkout", "--detach", "v1.0.4")
        self.assertEqual(
            verify_release_commit("v1.0.4", cwd=self.checkout), commit
        )

    def test_older_main_ancestor_is_allowed(self) -> None:
        old_commit = _git(self.checkout, "rev-parse", "HEAD")
        _git(self.checkout, "tag", "v1.0.4")
        self._commit("new approved main commit")
        _git(self.checkout, "push", "origin", "main")
        _git(self.checkout, "checkout", "--detach", "v1.0.4")
        self.assertEqual(
            verify_release_commit("v1.0.4", cwd=self.checkout), old_commit
        )

    def test_unmerged_feature_branch_is_rejected(self) -> None:
        _git(self.checkout, "checkout", "-b", "feature/unmerged")
        self._commit("unreviewed change")
        _git(self.checkout, "tag", "v1.0.4")
        _git(self.checkout, "checkout", "--detach", "v1.0.4")
        with self.assertRaisesRegex(RuntimeError, "не входит в историю"):
            verify_release_commit("v1.0.4", cwd=self.checkout)

    def test_checkout_different_from_tag_is_rejected(self) -> None:
        _git(self.checkout, "tag", "v1.0.4")
        self._commit("another commit on main")
        _git(self.checkout, "push", "origin", "main")
        with self.assertRaisesRegex(RuntimeError, "HEAD"):
            verify_release_commit("v1.0.4", cwd=self.checkout)

    def test_unavailable_main_fails_closed(self) -> None:
        _git(self.checkout, "tag", "v1.0.4")
        _git(self.checkout, "checkout", "--detach", "v1.0.4")
        _git(self.checkout, "remote", "remove", "origin")
        with self.assertRaisesRegex(RuntimeError, "Не удалось обновить origin/main"):
            verify_release_commit("v1.0.4", cwd=self.checkout)

    def test_unknown_tag_is_rejected(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "refs/tags"):
            verify_release_commit("v9.9.9", cwd=self.checkout)


class ReleaseWorkflowTests(unittest.TestCase):
    def test_ancestry_gate_runs_before_windows_build(self) -> None:
        workflow = (
            Path(__file__).resolve().parents[1]
            / ".github"
            / "workflows"
            / "release.yml"
        ).read_text(encoding="utf-8")
        gate = 'python scripts/verify_release_commit.py --tag "$GITHUB_REF_NAME"'
        self.assertIn(gate, workflow)
        self.assertLess(workflow.index(gate), workflow.index("  build-windows:"))
        self.assertIn("needs: prepare-release", workflow)


if __name__ == "__main__":
    unittest.main()
