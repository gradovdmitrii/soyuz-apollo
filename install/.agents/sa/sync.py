"""
---
name: s-a-sync
description: Regenerates the root AGENTS.md, the generated project headers, the .claude/skills links, and the client permission adapters from .agents/; changes only what S-A manages (STANDARD S13).
type: script
inputs: --force (overwrite a root AGENTS.md that has no generated marker)
outputs: changed paths or "no changes" on stdout, WARN lines for owner content left unchanged; exit 0 ok, 1 refused, 2 error
side_effects: writes root AGENTS.md, project headers, .claude/settings.json, .codex/config.toml, .codex/rules/s-a.rules; creates and removes managed links in .claude/skills/
destructive: false
requires_owner: false
version: 0.2.0
origin: Soyuz-Apollo Framework | by Dmitrii Gradov | 2026-10
---
"""

from __future__ import annotations

from pathlib import Path

from . import adapters, common, ownership, policy
from .common import Refused, say


def run(root: Path, force: bool = False, guarded: bool = False) -> int:
    """Regenerate everything; guarded=True when the caller (init) already ran the guard."""
    if not guarded:
        common.guard(root)
    if not common.is_initialized(root):
        raise Refused("The installation is not initialized; run: python sa.py init")
    target = root / "AGENTS.md"
    if ownership.state(root, target) not in ownership.WRITABLE and not force:
        raise Refused("AGENTS.md has no generated marker line, so it may be hand-written; nothing was changed. "
                      "Move its rules to .agents/ or a project, then run: python sa.py sync --force")
    texts = adapters.render(root, policy.load(root), policy.archive(root)[0])
    changed = []
    if write_if_changed(target, common.render_root(root)):
        changed.append("AGENTS.md")
    changed += sync_headers(root)
    changed += sync_links(root)
    changed += sync_adapters(root, texts)
    for path in changed:
        say(f"changed: {path}")
    if not changed:
        say("no changes")
    return 0


def write_if_changed(path: Path, text: str) -> bool:
    if path.is_file() and path.read_bytes() == text.encode("utf-8"):
        return False
    common.write_text(path, text)
    return True


def sync_headers(root: Path) -> list[str]:
    """Replace only the generated header of each project AGENTS.md; keep the rest byte-for-byte."""
    changed = []
    for folder, kind in common.projects(root):
        path = folder / "AGENTS.md"
        name = common.rel(root, path)
        found = ownership.state(root, path)
        if found == ownership.ABSENT:
            continue
        if found != ownership.MIXED:
            say(f"WARN {name}: no generated header markers (or not valid UTF-8); left unchanged")
            continue
        text = common.read_text(path)
        span = common.header_span(text)
        new = text[:span[0]] + common.project_header(root, folder.name, kind) + text[span[1]:]
        if new != text:
            common.write_text(path, new)
            changed.append(name)
    return changed


def sync_links(root: Path) -> list[str]:
    """Link .claude/skills/<skill> to .agents/skills/<skill>; drop managed links whose skill is gone."""
    changed = []
    links = root / ".claude" / "skills"
    for name, skill in common.skills(root).items():
        link = links / name
        found = ownership.state(root, link)
        if found == ownership.GENERATED:
            continue
        if found != ownership.ABSENT:
            what = "an owner link" if common.is_link(link) else "a real file or folder"
            say(f"WARN {common.rel(root, link)}: {what} is in the way; left unchanged")
            continue
        common.make_link(link, skill)
        changed.append(common.rel(root, link))
    if links.is_dir():
        for entry in sorted(links.iterdir()):
            if common.is_link(entry) and not entry.exists() and ownership.state(root, entry) == ownership.GENERATED:
                common.remove_link(entry)
                changed.append(common.rel(root, entry))
    return changed


def sync_adapters(root: Path, texts: dict[str, str]) -> list[str]:
    """Write each adapter that is absent or generated; owner content stays as it is (S13)."""
    changed = []
    for name, text in texts.items():
        if ownership.state(root, root / name) not in ownership.WRITABLE:
            say(f"WARN adapter {name} is owner content; {adapters.OWNER_HINT[name]}")
        elif write_if_changed(root / name, text):
            changed.append(name)
    return changed
