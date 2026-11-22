"""
---
name: s-a-backup
description: Backs up the installation outside it with verified Git bundles and a ZIP that skips links, bytecode caches and project tmp directories.
type: script
inputs: --dest DIR (default paths.backup from instance.toml, else <root>-backup next to the installation)
outputs: <dest>/<timestamp>/ with *.bundle, installation.zip, backup-report.txt; exit 0 ok, 1 refused or a bundle failed
side_effects: writes only into the destination folder outside the installation
destructive: false
requires_owner: false
version: 0.4.0
origin: Soyuz-Apollo Framework | by Dmitrii Gradov | 2026-10
---
"""

from __future__ import annotations

import tomllib
import zipfile
from datetime import datetime
from pathlib import Path

from . import common
from .common import Refused, say

NOTE = "The archive lives outside the installation and is not included."


def run(root: Path, dest_arg: str | None) -> int:
    common.require_git()
    dest = destination(root, dest_arg)
    if dest.is_relative_to(root):
        raise Refused(f"The backup destination {dest} is inside the installation; choose a folder outside it.")
    out = dest / datetime.now().strftime("%Y-%m-%d-%H%M%S")
    try:
        out.mkdir(parents=True)
    except FileExistsError:
        raise Refused(f"{out} already exists; wait a second and retry.") from None
    lines = ["Soyuz-Apollo backup", f"Installation: {root}", f"Version: {common.version(root)}",
             f"Created: {out.name}", "", "Bundles:"]
    failed = False
    for repo_id, repo in repositories(root):
        name = common.rel(root, repo)
        if not common.git("rev-list", "-n", "1", "--all", repo=repo).stdout.strip():
            say(f"WARN {name}: no commits; bundle skipped")
            lines.append(f"  {repo_id}: skipped, no commits ({name})")
            continue
        bundle = out / f"{repo_id}.bundle"
        status = "verified"
        if common.git("bundle", "create", str(bundle), "--all", repo=repo).returncode:
            status = "FAILED to create"
        elif common.git("bundle", "verify", str(bundle), repo=repo).returncode:
            status = "FAILED to verify"
        failed = failed or status != "verified"
        say(f"bundle {bundle.name}: {status}")
        lines.append(f"  {bundle.name}: {status} ({name})")
    files, links, skipped_tmp, errors = write_zip(root, out / "installation.zip")
    size = (out / "installation.zip").stat().st_size
    say(f"zip installation.zip: {files} files, {size} bytes, {len(links)} links skipped")
    lines += ["", f"Archive: installation.zip, {size} bytes, {files} files", "Skipped links:"]
    lines += [f"  {link}" for link in links] or ["  none"]
    lines.append("Skipped project tmp directories:")
    lines += [f"  {name}" for name in skipped_tmp] or ["  none"]
    if errors:
        lines += ["Unreadable files (not in the zip):"] + [f"  {error}" for error in errors]
        say(f"WARN {len(errors)} unreadable files were left out; see backup-report.txt")
    lines += ["", NOTE]
    common.write_text(out / "backup-report.txt", "\n".join(lines) + "\n")
    say(f"backup: {out}")
    return 1 if failed else 0


def destination(root: Path, dest_arg: str | None) -> Path:
    if dest_arg:
        return (Path.cwd() / dest_arg).resolve()
    try:
        with open(root / ".agents" / "config" / "instance.toml", "rb") as handle:
            configured = str(tomllib.load(handle).get("paths", {}).get("backup", "")).strip()
    except (OSError, tomllib.TOMLDecodeError):
        configured = ""
    if configured:
        return (root / configured).resolve()
    return root.parent / f"{root.name}-backup"


def repositories(root: Path) -> list[tuple[str, Path]]:
    repos = [("core", root / ".agents")] if (root / ".agents" / ".git").exists() else []
    repos += [(f"{folder.parent.name}-{folder.name}", folder)
              for folder, _ in common.projects(root) if (folder / ".git").exists()]
    return repos


def write_zip(root: Path, target: Path) -> tuple[int, list[str], list[str], list[str]]:
    """Return the number of files stored, skipped links, skipped scratch directories, and read errors."""
    files, links, skipped_tmp, errors = 0, [], [], []
    project_areas = {root / area for area, _ in common.PROJECT_AREAS}

    def keep(path: Path) -> bool:
        if (path.name == "tmp" and path.parent.parent in project_areas
                and not common.is_link(path) and path.is_dir()):
            skipped_tmp.append(common.rel(root, path))
            return False
        return True

    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED, allowZip64=True, strict_timestamps=False) as archive:
        for path, kind in common.walk(root, skip=("__pycache__",), keep=keep):
            name = common.rel(root, path)
            if kind == "link":
                links.append(name)
                continue
            try:
                archive.write(path, name + "/" if kind == "dir" else name)
            except OSError as exc:
                errors.append(f"{name}: {exc.strerror or exc}")
                continue
            files += kind == "file"
    return files, links, skipped_tmp, errors
