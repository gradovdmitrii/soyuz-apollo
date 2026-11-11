"""
---
name: s-a-commit
description: Commits explicit paths to the repository that owns them, adding executor trailers.
type: script
inputs: paths (one repository), -m message, --agent, --model, --co-author, --core
outputs: <repo> <short hash> <summary> on stdout; exit 0 ok, 1 refused or nothing to commit, 2 git error
side_effects: git add and git commit in one repository
destructive: false
requires_owner: false
version: 0.2.0
origin: Soyuz-Apollo Framework | by Dmitrii Gradov | 2026-10
---
"""

from __future__ import annotations

import os
from pathlib import Path

from . import common
from .common import GitError, Refused, say


def run(root: Path, paths: list[str], message: str, agent: str | None, model: str | None,
        co_author: str | None, core: bool) -> int:
    common.require_git()
    if not message.strip():
        raise Refused("The commit message is empty.")
    repos: dict[Path, list[str]] = {}
    for arg in paths:
        path = common.user_path(root, arg)
        if path.is_relative_to(root / "port"):
            raise Refused(f"{arg}: port/ is transit only and has no repository; move the file into a project first.")
        repo = find_repo(root, path)
        if repo is None:
            raise Refused(f"{arg}: no repository owns this path; create a project with: python sa.py init <name>")
        repos.setdefault(repo, []).append(path.relative_to(repo).as_posix())
    if len(repos) > 1:
        names = ", ".join(common.rel(root, repo) for repo in repos)
        raise Refused(f"one repository per commit; these paths belong to: {names}")
    repo, rels = next(iter(repos.items()))
    if repo == root / ".agents" and not core:
        raise Refused(".agents/ is the core repository; core changes need --core (core changes come with a new release).")
    trailers = [f"Agent: {agent or os.environ.get('SA_AGENT') or 'unknown'}",
                f"Model: {model or os.environ.get('SA_MODEL') or 'unknown'}"]
    co_author = co_author or os.environ.get("SA_CO_AUTHOR")
    if co_author:
        trailers.append(f"Co-Authored-By: {co_author}")
    full = message.strip() + "\n\n" + "\n".join(trailers) + "\n"
    # --literal-pathspecs: a path is the exact file or folder named, never a glob such as plan[1].md
    added = common.git("--literal-pathspecs", "add", "--", *rels, repo=repo)
    if added.returncode:
        raise Refused(f"git add refused the paths: {common.git_message(added)}")
    if common.git("--literal-pathspecs", "diff", "--cached", "--quiet", "--", *rels, repo=repo).returncode == 0:
        raise Refused("nothing to commit for the given paths")
    result = common.git("--literal-pathspecs", "commit", "-q", "-F", "-", "--", *rels, repo=repo,
                        data=full.encode("utf-8"))
    if result.returncode:
        raise GitError(f"git commit failed in {common.rel(root, repo)}: {common.git_message(result)}")
    say(f"{common.rel(root, repo)} {common.git_ok('log', '-1', '--format=%h %s', repo=repo)}")
    return 0


def find_repo(root: Path, path: Path) -> Path | None:
    """Nearest folder with .git at or above the path (its parent if it is a file or deleted), below the root."""
    current = path if path.is_dir() else path.parent
    while current != root and current.is_relative_to(root):
        if (current / ".git").exists():
            return current
        current = current.parent
    return None
