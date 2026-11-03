"""Fail closed when a release tag is not from the protected main history.

This checks Git ancestry, not who created the tag. The tag creation policy
and publishing credentials must be protected separately in GitHub settings.
"""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path


def _git(*arguments: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *arguments],
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )


def _commit(revision: str, *, cwd: Path | None = None) -> str:
    result = _git("rev-parse", "--verify", f"{revision}^{{commit}}", cwd=cwd)
    if result.returncode != 0:
        raise RuntimeError(f"Не удалось определить коммит Git для {revision!r}.")
    commit = result.stdout.strip()
    if not commit:
        raise RuntimeError(f"Git не вернул коммит для {revision!r}.")
    return commit


def verify_release_commit(tag: str, *, cwd: Path | None = None) -> str:
    """Verify that the checked-out tag commit is reachable from fresh origin/main."""
    if not tag or not tag.startswith("v") or tag != tag.strip():
        raise RuntimeError("Ожидалось корректное имя тега выпуска, начинающееся с v.")

    checked_out = _commit("HEAD", cwd=cwd)
    tagged_commit = _commit(f"refs/tags/{tag}", cwd=cwd)
    if checked_out != tagged_commit:
        raise RuntimeError(
            f"Тег {tag} указывает не на проверяемый коммит HEAD. Выпуск запрещён."
        )

    # Never trust the possibly stale local remote-tracking ref from checkout.
    fetch = _git(
        "fetch",
        "--no-tags",
        "origin",
        "+refs/heads/main:refs/remotes/origin/main",
        cwd=cwd,
    )
    if fetch.returncode != 0:
        raise RuntimeError(
            "Не удалось обновить origin/main. Выпуск запрещён до проверки истории."
        )

    main_commit = _commit("refs/remotes/origin/main", cwd=cwd)
    ancestry = _git(
        "merge-base", "--is-ancestor", tagged_commit, main_commit, cwd=cwd
    )
    if ancestry.returncode != 0:
        raise RuntimeError(
            f"Коммит тега {tag} не входит в историю защищённой ветки main. "
            "Выпуск запрещён."
        )
    return tagged_commit


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Проверить принадлежность тега выпуска защищённой ветке main."
    )
    parser.add_argument("--tag", required=True, help="Имя тега выпуска, например v1.0.4")
    args = parser.parse_args()
    try:
        commit = verify_release_commit(args.tag)
    except RuntimeError as error:
        parser.exit(1, f"Ошибка проверки выпуска: {error}\n")
    print(f"Тег {args.tag} указывает на проверенный коммит main: {commit}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
