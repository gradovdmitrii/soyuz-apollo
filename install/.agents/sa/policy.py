"""
---
name: s-a-policy
description: Loads and checks the permission policy .agents/policy.toml and the archive path from .agents/config/instance.toml.
type: script
inputs: none; imported by sync, doctor and archive
outputs: none
side_effects: none; reads .agents/policy.toml and .agents/config/instance.toml
destructive: false
requires_owner: false
version: 0.2.0
origin: Soyuz-Apollo Framework | by Dmitrii Gradov | 2026-10
---
"""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

from . import common
from .common import Refused

POLICY = ".agents/policy.toml"
INSTANCE = ".agents/config/instance.toml"
ARCHIVE = "{archive}"
SECTIONS = {"read_deny": ("paths", "globs"), "write_deny": ("paths",),
            "command_deny": ("prefix", "why"), "command_ask": ("prefix", "why")}


class PolicyError(Refused):
    """policy.toml or the archive path cannot be used; sync and archive refuse, doctor reports it."""

    def __init__(self, path: str, problem: str) -> None:
        super().__init__(f"{path}: {problem}")
        self.path, self.problem = path, problem


@dataclass(frozen=True)
class Rule:
    prefix: tuple[str, ...]
    why: str


@dataclass(frozen=True)
class Policy:
    read_paths: tuple[str, ...]
    read_globs: tuple[str, ...]
    write_paths: tuple[str, ...]
    deny: tuple[Rule, ...]
    ask: tuple[Rule, ...]


def load(root: Path) -> Policy:
    """Parse and check .agents/policy.toml; every problem raises PolicyError."""
    data = parse(root, POLICY, missing="missing; restore it from the release")
    for key, value in data.items():
        if key not in SECTIONS:
            raise invalid(f"unknown key {key}")
        if not isinstance(value, list if key.startswith("command_") else dict):
            raise invalid(f"{key} has the wrong form; compare with the release copy")
    read, write = data.get("read_deny", {}), data.get("write_deny", {})
    for name, table in (("read_deny", read), ("write_deny", write)):
        unknown = sorted(set(table) - set(SECTIONS[name]))
        if unknown:
            raise invalid(f"unknown key {name}.{unknown[0]}")
    result = Policy(strings(read, "paths", "read_deny"), strings(read, "globs", "read_deny"),
                    strings(write, "paths", "write_deny"), rules(data, "command_deny"), rules(data, "command_ask"))
    for item in result.read_paths:
        if item != ARCHIVE and not Path(item).is_absolute():
            raise invalid(f"read_deny.paths entry {item!r} must be {ARCHIVE} or an absolute path")
    for item in result.write_paths:
        parts = PurePosixPath(item).parts
        if "\\" in item or PurePosixPath(item).is_absolute() or not parts or ".." in parts or item != "/".join(parts):
            raise invalid(f"write_deny.paths entry {item!r} must be a plain path relative to the root, like .agents")
    for entries in (result.read_paths, result.read_globs + result.write_paths):
        if len(set(entries)) != len(entries):
            raise invalid("an entry is listed twice in read_deny or write_deny")
    return result


def invalid(problem: str) -> PolicyError:
    return PolicyError(POLICY, f"invalid: {problem}")


def strings(table: dict[str, Any], key: str, where: str) -> tuple[str, ...]:
    value = table.get(key, [])
    if not isinstance(value, list) or not all(isinstance(item, str) and item.strip() for item in value):
        raise invalid(f"{where}.{key} must be a list of non-empty strings")
    return tuple(value)


def rules(data: dict[str, Any], key: str) -> tuple[Rule, ...]:
    found = []
    for item in data.get(key, []):
        if not isinstance(item, dict) or sorted(item) != sorted(SECTIONS[key]):
            raise invalid(f"every [[{key}]] needs exactly prefix and why")
        prefix = strings(item, "prefix", key)
        if not prefix or any(len(word.split()) != 1 for word in prefix):
            raise invalid(f"{key}.prefix must be one or more words without spaces")
        if not isinstance(item["why"], str) or not item["why"].strip():
            raise invalid(f"{key}.why must be a non-empty string")
        found.append(Rule(prefix, item["why"]))
    return tuple(found)


def archive(root: Path) -> tuple[Path, bool]:
    """The archive folder and whether paths.archive is set; it must be absolute and must not overlap the root."""
    value = parse(root, INSTANCE, missing="").get("paths", {})
    value = value.get("archive", "") if isinstance(value, dict) else None
    if not isinstance(value, str):
        raise PolicyError(INSTANCE, "paths.archive must be a string")
    value = value.strip()
    folder = Path(os.path.normpath(value)) if value else root.parent / f"{root.name}-archive"
    if not folder.is_absolute():
        raise PolicyError(INSTANCE, f"paths.archive {value!r} is not an absolute path; "
                                    "set an absolute folder outside the installation")
    if folder.is_relative_to(root) or root.is_relative_to(folder):
        raise PolicyError(INSTANCE, f"the archive {folder} overlaps the installation {root}; "
                                    "set paths.archive to a folder outside it")
    return folder, bool(value)


def parse(root: Path, name: str, missing: str) -> dict[str, Any]:
    """TOML of a file below the root; an absent file is {} when missing is empty, else a PolicyError."""
    try:
        return tomllib.loads(common.read_text(root / name))
    except FileNotFoundError:
        if missing:
            raise PolicyError(name, missing) from None
        return {}
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
        raise PolicyError(name, f"not valid TOML: {exc}") from None
