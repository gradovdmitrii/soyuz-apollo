"""
---
name: s-a-init
description: Prepares a fresh installation (core repository, instance.toml, workspace folders), creates a new project repository from the templates, or adopts an existing project repository.
type: script
inputs: optional project name (kebab-case), --system, --adopt
outputs: created or adopted paths and commit hashes on stdout; exit 0 ok, 1 refused, 2 error
side_effects: creates folders and files; git init, soyuz-apollo.managed and local Git settings, a first commit in .agents/ or in the new project; runs sync; removes package-only files update.py and release-manifest.json from the root; --adopt writes only the project's .git/config
destructive: false
requires_owner: false
version: 0.3.0
origin: Soyuz-Apollo Framework | by Dmitrii Gradov | 2026-10
---
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from . import common, ownership, sync
from .common import Refused, say

WORKSPACE = ("projects", "system-projects", "port/inbox", "port/outbox", "port/large-files")
REPO_FILES = (".gitignore", ".gitattributes", ".editorconfig")
PACKAGE_ONLY = ("update.py", "release-manifest.json")


def is_package_file(path: Path) -> bool:
    """True only for the release tools: update.py with its passport, or a release manifest (U13)."""
    if common.is_link(path) or not path.is_file():
        return False
    try:
        text = path.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeDecodeError):
        return False
    if path.name == "update.py":
        return "\nname: s-a-update\n" in text[:400]
    try:
        data = json.loads(text)
    except ValueError:
        return False
    return isinstance(data, dict) and data.get("manifest") == 1 and isinstance(data.get("kit"), dict)


def clean_package_files(root: Path) -> None:
    """Remove release-package files that unpacking leaves in the root; any other file of that name stays."""
    for name in PACKAGE_ONLY:
        path = root / name
        if is_package_file(path):
            path.unlink()


def run_installation(root: Path) -> int:
    common.guard(root)
    if common.is_initialized(root):
        say("already initialized")
        repos = [root / ".agents"] + [folder for folder, _ in common.projects(root)]
        for repo in repos:
            if ownership.state(root, repo) == ownership.GENERATED and common.configure_repo(repo):
                say(f"configured: {common.rel(root, repo)} (local Git settings)")
        code = sync.run(root, guarded=True)
        if code == 0:
            clean_package_files(root)
        return code
    in_the_way = [area for area in WORKSPACE if not workspace_ok(root, area)]
    if in_the_way:
        raise Refused(f"A file or link is in the way of the workspace folders {', '.join(in_the_way)}; "
                      "move or rename it, then run python sa.py init again. Nothing was changed.")
    missing = common.missing_identity(root)
    if missing:
        raise Refused(common.identity_help(missing))
    created = []
    for area in WORKSPACE:
        if not (root / area).is_dir():
            (root / area).mkdir(parents=True, exist_ok=True)
            created.append(area + "/")
    config = root / ".agents" / "config" / "instance.toml"
    if not config.exists():
        name = root.name.replace("\\", "\\\\").replace('"', '\\"')
        text = common.read_text(config.with_name("instance.example.toml")).replace("\r\n", "\n")
        common.write_text(config, re.sub(r'^name = ""', lambda _: f'name = "{name}"', text, count=1, flags=re.M))
        created.append(".agents/config/instance.toml")
    core = root / ".agents"
    if not (core / ".git").exists():
        message = f"Install Soyuz-Apollo {common.version(root)}\n\n{common.TOOL_TRAILERS}"
        common.git_ok("init", "-q", "-b", "main", repo=core)
        ownership.mark_managed(core)
        common.configure_repo(core)
        common.git_ok("add", "-A", repo=core)
        common.git_ok("commit", "-q", "-F", "-", repo=core, data=message.encode("utf-8"))
        created.append(f".agents/.git (commit {common.git_ok('rev-parse', '--short', 'HEAD', repo=core)})")
    code = sync.run(root, guarded=True)
    if code == 0:
        clean_package_files(root)
    for item in created:
        say(f"created: {item}")
    say(f"init: installation ready at {root}; next: python sa.py init <name>")
    return code


def workspace_ok(root: Path, area: str) -> bool:
    """A workspace folder exists as a folder, or nothing stands where init would create it."""
    return (root / area).is_dir() or ownership.state(root, root / area) == ownership.ABSENT


def run_project(root: Path, name: str, system: bool, adopt: bool = False) -> int:
    common.guard(root)
    if not common.SLUG.fullmatch(name):
        raise Refused(f"Invalid project name {name!r}: use lowercase ASCII words joined by hyphens, "
                      "for example: health or tax-2026.")
    area, kind = ("system-projects", "system project") if system else ("projects", "project")
    if not workspace_ok(root, area):
        raise Refused(f"A file or link is in the way of the workspace folder {area}; move or rename it, "
                      "then retry. Nothing was changed.")
    target = root / area / name
    if adopt:
        return adopt_project(root, target, kind)
    if target.exists() and (not target.is_dir() or any(target.iterdir())):
        command = f"python sa.py init {name}{' --system' if system else ''} --adopt"
        hint = f" To take over its own repository run: {command}" if (target / ".git").exists() else ""
        raise Refused("Folder exists and is not empty. Importing existing projects is a separate skill; "
                      f"nothing was changed.{hint}")
    missing = common.missing_identity(root)
    if missing:
        raise Refused(common.identity_help(missing))
    templates = root / ".agents" / "templates" / "project"
    files = {"AGENTS.md": common.render_project(root, name, kind)}
    for file_name in REPO_FILES:
        text = common.read_text(templates / f"{file_name[1:]}.template")
        files[file_name] = common.split_passport(text)[1].replace("\r\n", "\n")
    target.mkdir(parents=True, exist_ok=True)
    for file_name, text in files.items():
        common.write_text(target / file_name, text)
    message = f"Create project {name}\n\n{common.TOOL_TRAILERS}"
    common.git_ok("init", "-q", "-b", "main", repo=target)
    ownership.mark_managed(target)
    common.configure_repo(target)
    common.git_ok("add", "--", *files, repo=target)
    common.git_ok("commit", "-q", "-F", "-", repo=target, data=message.encode("utf-8"))
    short = common.git_ok("rev-parse", "--short", "HEAD", repo=target)
    say(f"created: {area}/{name}/ ({kind}) with {', '.join(files)}; commit {short} Create project {name}")
    say(f"next: replace the TODO: lines under Local rules in {area}/{name}/AGENTS.md")
    return 0


def adopt_project(root: Path, target: Path, kind: str) -> int:
    """Take over an existing project repository (S13): mark it managed and set its Git keys; no file changes."""
    name = common.rel(root, target)
    if common.is_link(target) or not target.is_dir():
        raise Refused(f"{name}/ is not an existing project folder; --adopt takes over a folder that has "
                      "its own .git. Nothing was changed.")
    if not (target / ".git").exists():
        raise Refused(f"{name}/ has no .git of its own; --adopt takes over an existing repository only. "
                      "Nothing was changed.")
    ownership.mark_managed(target)
    common.configure_repo(target)
    say(f"adopted: {name}/ ({kind}); soyuz-apollo.managed and local Git settings set; no files changed, no commit")
    if ownership.state(root, target / "AGENTS.md") == ownership.MIXED:
        say(f"header: {name}/AGENTS.md has the generated header markers; run: python sa.py sync")
        return 0
    say(f"next: add the generated header with these two lines at the top of {name}/AGENTS.md, "
        "then run: python sa.py sync")
    say(common.BEGIN)
    say(common.END)
    return 0
