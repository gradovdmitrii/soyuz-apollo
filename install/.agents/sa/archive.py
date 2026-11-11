"""
---
name: s-a-archive
description: Owner command - moves a project or a file of the installation into the archive outside it (verified git bundle, copy verified by size and SHA-256, original deleted only with --remove), or lists the archive by top-level names.
type: script
inputs: add <path> [--remove]; list
outputs: add - verification lines and the next step; list - top-level names in the archive; exit 0 ok, 1 refused or not verified, 2 error
side_effects: add creates <archive>/<YYYY-MM-DD>-<name>/ with a copy and, for a repository, <name>.bundle; --remove deletes the original after verification
destructive: true
requires_owner: true
version: 0.2.0
origin: Soyuz-Apollo Framework | by Dmitrii Gradov | 2026-10
---
"""

from __future__ import annotations

import hashlib
import os
import shutil
import stat
from datetime import date
from pathlib import Path

from . import common, policy
from .common import Refused, say

Manifest = dict[str, tuple[str, int, str]]


def run_list(root: Path) -> int:
    """Print the names directly in the archive; never open them."""
    folder, _ = policy.archive(root)
    names = sorted(os.listdir(folder)) if folder.is_dir() else []
    for name in names:
        say(name)
    if not names:
        say(f"archive: {folder} is empty or does not exist yet")
    return 0


def run_add(root: Path, arg: str, remove: bool) -> int:
    archive, _ = policy.archive(root)
    if common.is_link(Path(os.path.abspath(arg))):
        raise Refused(f"{arg}: is a link; archive the folder or file itself. Nothing was changed.")
    source = common.user_path(root, arg)
    if source == root:
        raise Refused(f"{arg}: is the installation root; archive one project or file. Nothing was changed.")
    name = common.rel(root, source)
    areas = [root / "projects", root / "system-projects"]
    if not any(source.is_relative_to(area) and source != area for area in areas):
        raise Refused(f"{name}: only projects and files inside projects/ or system-projects/ go to the archive; "
                      "core, root and port files stay. Nothing was changed.")
    if not source.exists():
        raise Refused(f"{name}: not found")
    dest = archive / f"{date.today().isoformat()}-{source.name}"
    copy, bundle = dest / source.name, dest / f"{source.name}.bundle"
    repo = source.is_dir() and (source / ".git").exists() and has_commits(source)
    if dest.exists() or common.is_link(dest):
        expected = sorted([copy.name, bundle.name] if repo else [copy.name])
        if not remove or common.is_link(dest) or not dest.is_dir() or sorted(os.listdir(dest)) != expected:
            raise Refused(f"{dest} already exists; nothing was changed. "
                          "To archive this path again today, move that folder out of the archive first.")
        say(f"reusing {dest} from an earlier run; verifying it again")
        if repo:
            verify_bundle(source, bundle)
    else:
        dest.mkdir(parents=True)
        if repo:
            if common.git("bundle", "create", str(bundle), "--all", repo=source).returncode:
                raise Refused(f"git bundle create failed for {name}; the original is unchanged.")
            verify_bundle(source, bundle)
        copy_original(source, copy)
    files, size = verify(source, copy)
    say(f"copy {copy}: {files} files, {size} bytes, verified (paths, sizes, SHA-256)")
    if not remove:
        say(f"verified; to remove the original run: python sa.py archive add {name} --remove")
        return 0
    delete(source)
    say(f"removed: {name}")
    return 0


def has_commits(repo: Path) -> bool:
    common.require_git()
    if common.git("rev-list", "-n", "1", "--all", repo=repo).stdout.strip():
        return True
    say(f"WARN {repo.name}: no commits; bundle skipped, the copy keeps .git")
    return False


def verify_bundle(source: Path, bundle: Path) -> None:
    if common.git("bundle", "verify", str(bundle), repo=source).returncode:
        raise Refused(f"{bundle} does not verify; the original is unchanged.")
    say(f"bundle {bundle}: verified")


def copy_original(source: Path, copy: Path) -> None:
    """Copy without following links: symlinks stay symlinks, junctions are recreated as junctions."""
    if not source.is_dir():
        shutil.copy2(source, copy)
        return
    shutil.copytree(source, copy, symlinks=True, ignore=junctions)
    for path, kind in common.walk(source, skip=()):
        if kind == "link" and not os.path.islink(path):
            common.make_link(copy / path.relative_to(source), Path(common.link_target(path) or ""))


def junctions(folder: str, names: list[str]) -> set[str]:
    """copytree follows junctions (they are not symlinks to Python); copy_original recreates them instead."""
    return {name for name in names
            if not os.path.islink(Path(folder) / name) and common.link_target(Path(folder) / name) is not None}


def verify(source: Path, copy: Path) -> tuple[int, int]:
    """Same relative paths, sizes and SHA-256 for every file, same targets for links; return files and bytes."""
    expected, found = manifest(source), manifest(copy)
    if expected != found:
        differ = sorted(key for key in expected.keys() | found.keys() if expected.get(key) != found.get(key))
        shown = ", ".join(item or source.name for item in differ[:5]) + (", ..." if len(differ) > 5 else "")
        raise Refused(f"the copy in {copy} differs from the original in {len(differ)} paths ({shown}); "
                      "the original is unchanged.")
    files = [entry for entry in expected.values() if entry[0] == "file"]
    return len(files), sum(entry[1] for entry in files)


def manifest(top: Path) -> Manifest:
    """Relative path -> (kind, size, SHA-256 or link target) for top and everything below it, links not followed."""
    entries = [(top, "file")] if not top.is_dir() else list(common.walk(top, skip=()))
    result: Manifest = {}
    for path, kind in entries:
        key = "" if path == top else path.relative_to(top).as_posix()
        if kind == "file":
            with open(path, "rb") as handle:
                result[key] = (kind, path.stat().st_size, hashlib.file_digest(handle, "sha256").hexdigest())
        else:
            target = (common.link_target(path) or "") if kind == "link" else ""
            result[key] = (kind, 0, target)
    return result


def delete(source: Path) -> None:
    """Delete the original without following links; read-only files (Git objects on Windows) are made writable."""
    if not source.is_dir():
        unlink(source)
        return
    for path, kind in reversed(list(common.walk(source, skip=()))):
        if kind == "link":
            common.remove_link(path)
        elif kind == "dir":
            path.rmdir()
        else:
            unlink(path)
    source.rmdir()


def unlink(path: Path) -> None:
    try:
        path.unlink()
    except PermissionError:
        os.chmod(path, stat.S_IWRITE)
        path.unlink()
