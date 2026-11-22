"""
---
name: s-a-doctor
description: Check an installation, including generated files, repositories, passports and document sections. Check project content with --deep.
type: script
inputs: optional project name for --deep (content checks inside that project)
outputs: one line per finding and a summary with INCOMPLETE if Git checks were skipped; exit 1 for any ERROR, otherwise 0
side_effects: none; never creates, changes or deletes files (git runs with --no-optional-locks)
destructive: false
requires_owner: false
version: 0.4.0
origin: Soyuz-Apollo Framework | by Dmitrii Gradov | 2026-10
---
"""

from __future__ import annotations

import os
import re
import sys
import tomllib
from collections.abc import Callable, Iterator
from pathlib import Path

from . import adapters, common, ownership, policy
from .common import Refused, say

LEVELS = ("ERROR", "WARN", "INFO")
FORBIDDEN = {"claude.md", "claude.local.md", ".hermes.md", "hermes.md", "agents.override.md"}
SCRIPT_EXT = {".py", ".ps1", ".sh", ".toml", ".json", ".yaml", ".yml"}
PASSPORT_FIELDS = ("name", "description", "type", "audience", "load", "scope", "version", "origin")
SCRIPT_FIELDS = ("name", "description", "type", "inputs", "outputs", "side_effects", "destructive",
                 "requires_owner", "version", "origin")
SKILL_TOP = {"name", "description", "license", "compatibility", "metadata", "allowed-tools"}
ALLOWED = {
    "type": {"boundaries", "guide", "procedure", "skill", "reference", "template", "script"},
    "audience": {"agent", "human", "both"},
    "load": {"always", "on-demand"},
    "scope": {"installation", "project", "skill"},
    "destructive": {"true", "false"},
    "requires_owner": {"true", "false"},
}
VERSION_RE = re.compile(r"\d+\.\d+\.\d+(-[0-9A-Za-z.]+)?")
TODO_LINE = re.compile(r"\bTODO:")
COMMENT = re.compile(r"<!--.*?-->", re.S)
BUDGETS = {"AGENTS.md": 4096, ".agents/AGENTS.md": 6144}
PROJECT_BUDGET = 6144
SKILL_LINES = 500
SECTION_ORDER = ("Purpose", "MUST", "ROUTES", "STEPS", "DEFAULT", "EXAMPLES", "IF UNSURE", "REFERENCES")
PROCEDURE_SECTIONS = (("Purpose", "STEPS", "EXAMPLES", "IF UNSURE"), ("MUST", "DEFAULT", "REFERENCES"))
# Required and optional H2 sections (S4).
SECTION_RULES = {
    "boundaries": (("Purpose", "MUST", "IF UNSURE"), ()),
    "guide": (("Purpose", "IF UNSURE"), ("ROUTES", "STEPS", "DEFAULT", "EXAMPLES", "REFERENCES")),
    "procedure": PROCEDURE_SECTIONS,
    "skill": PROCEDURE_SECTIONS,
    "reference": (("Purpose", "MUST"), SECTION_ORDER),
    "template": (("Purpose",), SECTION_ORDER),
}
SECTION_HEADING = re.compile(r" {0,3}##(?:[ \t]+(.*?))?(?:[ \t]+#+)?[ \t]*$")
SECTION_FENCE = re.compile(r" {0,3}(`{3,}|~{3,})(.*)")


class Report:
    def __init__(self) -> None:
        self.items: list[tuple[str, str, str, str]] = []
        self.incomplete = 0

    def add(self, level: str, code: str, path: str, message: str) -> None:
        self.items.append((level, code, path, message))

    def unchecked(self, code: str, path: str, message: str) -> None:
        self.incomplete += 1
        self.add("WARN", code, path, message)

    def finish(self) -> int:
        for level, code, path, message in self.items:
            say(f"[{level}] {code} {path}: {message}")
        counts = [sum(1 for item in self.items if item[0] == level) for level in LEVELS]
        summary = f"doctor: {counts[0]} errors, {counts[1]} warnings, {counts[2]} info"
        if self.incomplete:
            noun = "check" if self.incomplete == 1 else "checks"
            summary += f" (INCOMPLETE: {self.incomplete} {noun} could not run)"
        say(summary)
        return 1 if counts[0] else 0


def run(root: Path, deep: str | None = None) -> int:
    """Check the installation; with deep=<project name> also run the content checks inside that project."""
    deep_folders = []
    if deep:
        wanted = deep.replace("\\", "/").strip("/")
        deep_folders = [folder for folder, _ in common.projects(root)
                        if wanted in (folder.name, common.rel(root, folder))]
        if not deep_folders:
            raise Refused(f"doctor --deep: no project named {deep!r} in projects/ or system-projects/")
        if len(deep_folders) > 1:
            choices = ", ".join(common.rel(root, folder) for folder in deep_folders)
            raise Refused(f"doctor --deep: {deep!r} is ambiguous; name one of: {choices}")
    report = Report()
    git_found = check_environment(report, root)
    check_root(report, root)
    check_generated(report, root)
    check_adapters(report, root)
    check_tree(report, root, deep_folders)
    if git_found:
        check_repositories(report, root)
    check_links(report, root)
    return report.finish()


def check_environment(report: Report, root: Path) -> bool:
    if sys.version_info < (3, 11):
        report.add("ERROR", "ENV-PYTHON", ".", f"Python {sys.version_info[0]}.{sys.version_info[1]}; 3.11+ required")
    if not common.has_git():
        report.add("ERROR", "ENV-GIT", ".", "git executable not found on PATH")
        return False
    for key in common.missing_identity(root):
        report.add("ERROR", "ENV-GIT", ".", f'{key} is not set; run: git config --global {key} "<value>"')
    return True


def check_root(report: Report, root: Path) -> None:
    for problem in common.guard_problems(root):
        report.add("ERROR", "ROOT-GUARD", ".", problem)
    if not (root / ".agents" / ".git").exists():
        report.add("ERROR", "ROOT-INIT", ".agents", "no .git; run: python sa.py init")
    config = root / ".agents" / "config" / "instance.toml"
    if not config.is_file():
        report.add("ERROR", "ROOT-INIT", common.rel(root, config), "missing; run: python sa.py init")
        return
    try:
        tomllib.loads(config.read_text(encoding="utf-8"))
    except (tomllib.TOMLDecodeError, UnicodeDecodeError) as exc:
        report.add("ERROR", "ROOT-INIT", common.rel(root, config), f"not valid TOML: {exc}")


def check_generated(report: Report, root: Path) -> None:
    agents = root / "AGENTS.md"
    found = ownership.state(root, agents)
    if found == ownership.ABSENT:
        report.add("ERROR", "GEN-STALE", "AGENTS.md", "missing; run: python sa.py sync")
    elif found != ownership.GENERATED:
        report.add("ERROR", "GEN-STALE", "AGENTS.md", "no generated marker line; run: python sa.py sync --force")
    else:
        fresh = rendered(report, "AGENTS.md", lambda: common.render_root(root))
        if fresh is not None and agents.read_bytes() != fresh.encode("utf-8"):
            report.add("ERROR", "GEN-STALE", "AGENTS.md", "differs from a fresh render; run: python sa.py sync")
    for name, budget in BUDGETS.items():
        path = root / name
        if path.is_file() and path.stat().st_size > budget:
            report.add("WARN", "SIZE", name, f"{path.stat().st_size} bytes; budget {budget}")
    for folder, kind in common.projects(root):
        path = folder / "AGENTS.md"
        name = common.rel(root, path)
        if not path.is_file():
            report.add("ERROR", "GEN-STALE", name, "missing; the project has no generated header")
            continue
        if path.stat().st_size > PROJECT_BUDGET:
            report.add("WARN", "SIZE", name, f"{path.stat().st_size} bytes; budget {PROJECT_BUDGET}")
        try:
            text = common.read_text(path)
        except UnicodeDecodeError:
            continue  # reported as ENC by check_tree, which checks every project's AGENTS.md
        span = common.header_span(text)
        if span is None:
            report.add("ERROR", "GEN-STALE", name, "no s-a:begin/s-a:end header markers")
            continue
        fresh = rendered(report, name, lambda: common.project_header(root, folder.name, kind))
        if fresh is not None and text[span[0]:span[1]] != fresh:
            report.add("ERROR", "GEN-STALE", name, "header differs from a fresh render; run: python sa.py sync")
        if TODO_LINE.search(COMMENT.sub("", text[span[1]:])):
            report.add("INFO", "PROJ-TODO", name, "local rules still contain TODO: lines")


def check_adapters(report: Report, root: Path) -> None:
    """POLICY, ARCHIVE, and each client adapter: missing, owner content, or differing from a fresh render."""
    rules = archive = None
    try:
        rules = policy.load(root)
    except policy.PolicyError as exc:
        report.add("ERROR", "POLICY", exc.path, exc.problem)
    try:
        archive, configured = policy.archive(root)
        if not configured:
            report.add("INFO", "ARCHIVE", policy.INSTANCE, f"paths.archive is empty; using default {archive}")
    except policy.PolicyError as exc:
        report.add("ERROR", "ARCHIVE", exc.path, exc.problem)
    fresh = adapters.render(root, rules, archive) if rules is not None and archive is not None else {}
    for name in adapters.PATHS:
        found = ownership.state(root, root / name)
        if found == ownership.ABSENT:
            report.add("WARN", "ADAPTER-MISSING", name, "missing; run: python sa.py sync")
        elif found != ownership.GENERATED:
            report.add("WARN", "ADAPTER-OWNER", name, "exists without the S-A marker, so sync leaves it unchanged; "
                       + adapters.OWNER_HINT[name])
        elif name in fresh and (root / name).read_bytes() != fresh[name].encode("utf-8"):
            report.add("ERROR", "GEN-STALE", name, "differs from a fresh render; run: python sa.py sync")


def rendered(report: Report, name: str, render: Callable[[], str]) -> str | None:
    try:
        return render()
    except (OSError, RuntimeError, UnicodeDecodeError) as exc:
        report.add("ERROR", "GEN-STALE", name, f"cannot render from the template: {exc}")
        return None


def check_tree(report: Report, root: Path, deep: list[Path] | None = None) -> None:
    """Core and root areas get every check. A project gets only its state checks (a forbidden instruction file
    directly in its root); its content is checked only for the projects named in deep (doctor --deep)."""
    content_names = 0
    deep = deep or []
    for path, kind in common.walk(root, keep=tracked_filter(report, root, deep)):
        parts = path.relative_to(root).parts
        name, area, rel = path.name, parts[0], "/".join(parts)
        suffix = path.suffix.lower()
        in_project = area in ("projects", "system-projects") and len(parts) > 2
        if in_project and not any(path.is_relative_to(folder) for folder in deep):
            if kind != "dir" and len(parts) == 3 and name.lower() in FORBIDDEN:
                report.add("ERROR", "FORBIDDEN", rel,
                           "overrides AGENTS.md in some clients; move its rules into AGENTS.md and delete it")
            if kind == "file" and len(parts) == 3 and name == "AGENTS.md":
                check_file(report, path, parts, suffix)  # the project's rules file is part of its state
            continue
        if kind != "dir" and name.lower() in FORBIDDEN:
            report.add("WARN" if area == "port" else "ERROR", "FORBIDDEN", rel,
                       "overrides AGENTS.md in some clients; move its rules into AGENTS.md and delete it")
        if needs_name_check(parts, kind, suffix) and not valid_name(name):
            report.add("ERROR", "NAME", rel, "name is not kebab-case ASCII (STANDARD S7)")
        elif in_project and not name.isascii():
            content_names += 1
        if kind == "file" and area != "port":
            check_file(report, path, parts, suffix)
    if content_names:
        report.add("INFO", "NAME-CONTENT", "--deep", f"{content_names} non-ASCII content paths in the "
                   "deep-checked project(s) (owner content, allowed)")


def tracked_filter(report: Report, root: Path, deep: list[Path]) -> Callable[[Path], bool]:
    """Skip the root __pycache__. Inside a project keep only what its Git tracks or would track (a folder without
    .git keeps nothing), and only its root level, except in the projects named in deep. A forbidden file name at the
    project root level is always kept, so R4 holds without .git or with ignored files."""
    fold = str.lower if os.name == "nt" else str
    allowed: set[str] = set()
    for folder in deep:
        if not (folder / ".git").exists() or not common.has_git():
            continue
        base = common.rel(root, folder)
        listed, reason = git_read("ls-files", "-z", "--cached", "--others", "--exclude-standard", repo=folder)
        if listed is None:
            report.unchecked("PROJ-INDEX", base, f"project content could not be checked: {reason}")
            continue
        for item in filter(None, listed.split("\0")):
            parts = fold(f"{base}/{item}").split("/")
            allowed.update("/".join(parts[:end]) for end in range(3, len(parts) + 1))

    def keep(path: Path) -> bool:
        parts = path.relative_to(root).parts
        if parts[0] == "__pycache__":
            return False
        if len(parts) < 3 or parts[0] not in ("projects", "system-projects"):
            return True
        if len(parts) > 3 and not any(path.is_relative_to(folder) for folder in deep):
            return False
        if len(parts) == 3 and (path.name.lower() in FORBIDDEN or not any(path.is_relative_to(f) for f in deep)):
            return True  # project root level: the forbidden-name check never depends on Git
        return fold("/".join(parts)) in allowed

    return keep


def needs_name_check(parts: tuple[str, ...], kind: str, suffix: str) -> bool:
    """Port content is transit data (B2): only the folders directly in port/ follow S7."""
    area, depth = parts[0], len(parts)
    return (depth == 1 or area == ".agents"
            or (depth == 2 and kind == "dir" and area in ("port", "projects", "system-projects"))
            or (kind != "dir" and suffix in SCRIPT_EXT and area != "port"))


def valid_name(name: str) -> bool:
    return (name in common.NAME_EXCEPTIONS or name.replace(".template", "", 1) in common.NAME_EXCEPTIONS
            or common.KEBAB.fullmatch(name) is not None or common.SNAKE_PY.fullmatch(name) is not None)


def check_file(report: Report, path: Path, parts: tuple[str, ...], suffix: str) -> None:
    """Check encoding, passport, document sections and skill size for one file."""
    area, rel, name = parts[0], "/".join(parts), path.name
    encoded = suffix == ".md" or area == ".agents"
    kind = ("skill" if name == "SKILL.md" else "file" if suffix == ".md" and area == ".agents"
            else "script" if suffix == ".py" and area in (".agents", "system-projects") else None)
    if not encoded and kind is None:
        return
    try:
        data = path.read_bytes()
    except OSError as exc:
        report.add("ERROR", "ENC", rel, f"cannot read: {exc.strerror or exc}")
        return
    if encoded and (suffix == ".md" or b"\0" not in data[:8192]):
        if data.startswith(b"\xef\xbb\xbf"):
            report.add("ERROR", "ENC", rel, "starts with a UTF-8 BOM; save as UTF-8 without BOM")
        try:
            data.decode("utf-8")
        except UnicodeDecodeError:
            report.add("ERROR", "ENC", rel, "not valid UTF-8")
        if b"\r\n" in data and suffix not in (".cmd", ".bat"):
            report.add("WARN", "ENC-CRLF", rel, "CRLF line endings; use LF")
    if kind is None:
        return
    text = data.decode("utf-8-sig", "replace")
    if kind == "skill":
        if area != ".agents" and not common.SLUG.fullmatch(path.parent.name):
            report.add("ERROR", "NAME", "/".join(parts[:-1]), "skill folder is not kebab-case ASCII")
        if text.count("\n") > SKILL_LINES:
            report.add("WARN", "SIZE", rel, f"{text.count(chr(10))} lines; budget {SKILL_LINES}")
    if kind == "script":
        lines, body = common.python_passport(text), ""
    else:
        lines, body = common.split_passport(text)
    if lines is None:
        where = " in the module docstring (S9)" if kind == "script" else " (S2)"
        report.add("ERROR", "PASSPORT", rel, "missing passport" + where)
        if kind == "skill":
            check_sections(report, rel, body, "skill")
        return
    top, meta, bad = common.parse_passport(lines)
    problems = [f"malformed line {line.strip()!r}" for line in bad]
    problems += [f"field {key} must be one plain line without quotes or | > (S2)"
                 for key, value in [*top.items(), *meta.items()] if value[:1] in ("'", '"', "|", ">")]
    if kind == "skill":
        problems += [f"top-level key {key} is not allowed in SKILL.md; move it under metadata"
                     for key in top if key not in SKILL_TOP]
        problems += field_problems(top, ("name", "description"))
        problems += field_problems(meta, PASSPORT_FIELDS[2:])
        if top.get("name") != path.parent.name:
            problems.append(f"name {top.get('name', '')!r} differs from the folder {path.parent.name!r}")
        if len(top.get("name", "")) > 64 or len(top.get("description", "")) > 1024:
            problems.append("name over 64 or description over 1024 characters")
    else:
        problems += field_problems(top, SCRIPT_FIELDS if kind == "script" else PASSPORT_FIELDS)
    if problems:
        report.add("ERROR", "PASSPORT", rel, "; ".join(problems))
    if kind == "skill":
        check_sections(report, rel, body, "skill")
    elif kind == "file" and not (top.get("scope") == "skill" and skill_support_document(parts)):
        check_sections(report, rel, body, top.get("type", ""))


def skill_support_document(parts: tuple[str, ...]) -> bool:
    """S4 allows subject headings in the README and references of an installed skill."""
    return (parts[:2] == (".agents", "skills") and
            ((len(parts) == 4 and parts[3] == "README.md") or (len(parts) >= 5 and parts[3] == "references")))


def document_sections(body: str, template: bool) -> Iterator[tuple[str, bool]]:
    """Yield each H2 and whether it contains text. A fenced example counts as content under its own heading."""
    heading = None
    has_text = in_template = in_comment = False
    fence = ""
    for line in body.splitlines():
        stripped = line.strip()
        if in_template:
            in_template = stripped != common.TEMPLATE_END
            continue
        marker = SECTION_FENCE.fullmatch(line)
        if fence:
            if marker and marker[1].startswith(fence) and not marker[2].strip():
                fence = ""
            elif stripped:
                has_text = True
            continue
        if in_comment:
            in_comment = "-->" not in line
            continue
        if template and stripped == common.TEMPLATE_START:
            in_template = True
            continue
        if stripped.startswith("<!--"):
            in_comment = "-->" not in stripped[4:]
            continue
        if marker and (marker[1][0] == "~" or "`" not in marker[2]):
            fence = marker[1]
            continue
        found = SECTION_HEADING.fullmatch(line)
        if found:
            if heading is not None:
                yield heading, has_text
            heading = found[1] or ""
            has_text = False
        elif stripped:
            has_text = True
    if heading is not None:
        yield heading, has_text


def check_sections(report: Report, rel: str, body: str, doc_type: str) -> None:
    if doc_type not in SECTION_RULES:
        return
    required, optional = SECTION_RULES[doc_type]
    seen = set()
    last = -1
    for heading, has_text in document_sections(body, doc_type == "template"):
        if heading not in required and heading not in optional:
            report.add("WARN", "SECTION", rel, f"unexpected section {heading!r} for {doc_type} (S4)")
            continue
        order = SECTION_ORDER.index(heading)
        if heading in seen:
            report.add("WARN", "SECTION", rel, f"duplicate section {heading!r} (S4)")
        elif order < last:
            report.add("WARN", "SECTION", rel, f"out-of-order section {heading!r} (S4)")
        if not has_text:
            report.add("WARN", "SECTION", rel, f"empty section {heading!r} (S4)")
        seen.add(heading)
        last = max(order, last)
    for heading in required:
        if heading not in seen:
            report.add("ERROR", "SECTION", rel, f"missing required section {heading!r} (S4)")


def field_problems(fields: dict[str, str], required: tuple[str, ...]) -> list[str]:
    problems = [f"missing field {key}" for key in required if not fields.get(key)]
    for key, allowed in ALLOWED.items():
        if fields.get(key) and fields[key] not in allowed:
            problems.append(f"{key} {fields[key]!r} is not one of {'|'.join(sorted(allowed))}")
    if fields.get("name") and not common.SLUG.fullmatch(fields["name"]):
        problems.append(f"name {fields['name']!r} is not kebab-case")
    if fields.get("version") and not VERSION_RE.fullmatch(fields["version"]):
        problems.append(f"version {fields['version']!r} is not like 0.2.0")
    return problems


def check_repositories(report: Report, root: Path) -> None:
    core = root / ".agents"
    if (core / ".git").exists():
        check_repo_settings(report, root, core)
        files = dirty_files(report, root, core)
        if files:
            report.add("WARN", "CORE-DIRTY", ".agents", "uncommitted changes: " + ", ".join(files))
    for folder, kind in common.projects(root):
        name = common.rel(root, folder)
        if not (folder / ".git").exists():
            report.add("ERROR", "PROJ-NOGIT", name, "no .git; create projects with: python sa.py init <name>")
            continue
        # Read the local marker separately: a missing key has a defined default, an unreadable config does not.
        if ownership.blocked(root, folder):
            managed, reason = "false", ""
        else:
            managed, reason = git_read("config", "--local", "--type=bool", "--default=false", "--get",
                                       ownership.MANAGED_KEY, repo=folder)
        if managed is None:
            report.unchecked("REPO-GITCFG", name, f"repository management and Git settings could not be checked: {reason}")
        elif managed.strip() == "true":
            check_repo_settings(report, root, folder)
        else:
            flags = " --system" if kind == "system project" else ""
            report.add("INFO", "REPO-UNMANAGED", name, "no soyuz-apollo.managed in its .git/config, so S-A leaves "
                       f"its Git settings alone; to take it over: python sa.py init {folder.name}{flags} --adopt")
        files = dirty_files(report, root, folder)
        if files:
            report.add("INFO", "PROJ-DIRTY", name, f"{len(files)} uncommitted files")


def check_repo_settings(report: Report, root: Path, repo: Path) -> None:
    """Line endings are guaranteed by .gitattributes; the local Git settings only add robustness."""
    name, attrs = common.rel(root, repo), repo / ".gitattributes"
    if not attrs.is_file() or "* text=auto eol=lf" not in common.read_text(attrs).splitlines():
        report.add("ERROR", "REPO-EOL", name, ".gitattributes must contain the line: * text=auto eol=lf")
    listed, reason = git_read("config", "--list", "-z", repo=repo)
    if listed is None:
        report.unchecked("REPO-GITCFG", name, f"Git settings could not be checked: {reason}")
        return
    config = {key.lower(): value.strip()
              for key, _, value in (item.partition("\n") for item in listed.split("\0") if item)}
    for key, value in common.REPO_CONFIG:
        if config.get(key, "").lower() != value and (key != "core.longpaths" or os.name == "nt"):
            level = "WARN" if key == "core.longpaths" else "INFO"
            report.add(level, "REPO-GITCFG", name, f"{key} is not {value} for this repository; run: python sa.py init")


def dirty_files(report: Report, root: Path, repo: Path) -> list[str]:
    listed, reason = git_read("--no-optional-locks", "-c", "core.quotepath=false", "status", "--porcelain",
                              "--untracked-files=all", repo=repo)
    if listed is None:
        report.unchecked("CORE-DIRTY" if repo.name == ".agents" else "PROJ-DIRTY", common.rel(root, repo),
                         f"uncommitted changes could not be checked: {reason}")
        return []
    return [line[3:] for line in listed.splitlines() if line.strip()]


def git_read(*args: str, repo: Path) -> tuple[str | None, str]:
    """Run a read-only git command: (stdout, "") or (None, reason) when Git cannot run there or fails (U12)."""
    try:
        result = common.git(*args, repo=repo)
    except OSError as exc:
        return None, exc.strerror or str(exc)
    if result.returncode:
        return None, common.git_message(result)
    return result.stdout, ""


def check_links(report: Report, root: Path) -> None:
    skills = common.skills(root)
    links = root / ".claude" / "skills"
    for name in skills:
        link = links / name
        found = ownership.state(root, link)
        if found == ownership.ABSENT:
            report.add("WARN", "LINKS", common.rel(root, link), "link is missing; run: python sa.py sync")
        elif found != ownership.GENERATED:
            problem = "owner link" if common.is_link(link) else "a real file or folder is in the way"
            report.add("WARN", "LINKS", common.rel(root, link), f"{problem}, left unchanged")
    if links.is_dir():
        for entry in sorted(links.iterdir()):
            if entry.name in skills:
                continue
            if not common.is_link(entry):
                problem = "no matching skill in .agents/skills/"
            elif ownership.state(root, entry) == ownership.GENERATED:
                problem = "its skill is gone; run: python sa.py sync"
            else:
                problem = "owner link, left unchanged"
            report.add("WARN", "LINKS", common.rel(root, entry), problem)
