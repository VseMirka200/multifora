"""Проверяет, что релизный тег относится к истории origin/main."""

import argparse
import subprocess
from pathlib import Path


def _git(cwd, *arguments):
    return subprocess.run(
        ["git", *arguments], cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace", check=False
    )


def verify_release_commit(tag: str, *, cwd: Path | None = None) -> str:
    ref = f"refs/tags/{tag}"
    if _git(cwd, "check-ref-format", ref).returncode:
        raise RuntimeError(f"Некорректный тег {ref}")
    tagged = _git(cwd, "rev-parse", "--verify", f"{ref}^{{commit}}")
    if tagged.returncode:
        raise RuntimeError(f"Не найден тег {ref}: {tagged.stderr.strip()}")
    commit = tagged.stdout.strip()
    head = _git(cwd, "rev-parse", "--verify", "HEAD^{commit}")
    if head.returncode or head.stdout.strip() != commit:
        raise RuntimeError("HEAD не соответствует релизному тегу")
    fetched = _git(cwd, "fetch", "--no-tags", "origin", "+refs/heads/main:refs/remotes/origin/main")
    if fetched.returncode:
        raise RuntimeError("Не удалось обновить origin/main: " + fetched.stderr.strip())
    if _git(cwd, "merge-base", "--is-ancestor", commit, "refs/remotes/origin/main").returncode:
        raise RuntimeError("Релизный коммит не входит в историю origin/main")
    return commit


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tag", required=True)
    args = parser.parse_args()
    try:
        print(verify_release_commit(args.tag))
    except RuntimeError as error:
        parser.exit(1, f"{error}\n")


if __name__ == "__main__":
    main()
