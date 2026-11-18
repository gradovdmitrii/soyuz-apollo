"""
---
name: s-a-update
description: Updates a Soyuz-Apollo installation in place from the unpacked release package that contains this file - plan, apply, rollback, and verify of the downloaded ZIP.
type: script
inputs: plan --target DIR, apply --target DIR [--conflicts replace|keep], rollback --target DIR, verify --zip FILE
outputs: one fact per line on stdout; exit 0 ok, 1 refused with nothing changed, 2 rolled back automatically or unexpected error, 3 applied with problems, 4 restore failed
side_effects: apply and rollback lock the installation, replace, add and delete release files, write .agents/update-backup/ and one line in .agents/.git/info/exclude, run sa.py sync and doctor, commit the core repository; plan and verify write nothing
destructive: false
requires_owner: true
version: 0.3.0
origin: Soyuz-Apollo Framework | by Dmitrii Gradov | 2026-11
---
"""

import sys

sys.dont_write_bytecode = True

if sys.version_info < (3, 11):
    sys.stderr.write("update.py needs Python 3.11 or newer; this is Python %d.%d.\n" % tuple(sys.version_info[:2]))
    sys.exit(2)

import argparse  # noqa: E402
import hashlib  # noqa: E402
import json  # noqa: E402
import os  # noqa: E402
import re  # noqa: E402
import shutil  # noqa: E402
import subprocess  # noqa: E402
import zipfile  # noqa: E402
from contextlib import contextmanager  # noqa: E402
from datetime import datetime, timezone  # noqa: E402
from pathlib import Path  # noqa: E402

PACKAGE = Path(__file__).resolve().parent
MANIFEST = "release-manifest.json"
KIT_ROOT = ("sa.py", "LICENSE", ".ignore", "README.md", "README.en.md")
BACKUP = "update-backup"
PROTECTED = (".agents/.git/", ".agents/config/instance.toml", f".agents/{BACKUP}/")
TOOL_TRAILERS = "Agent: s-a-satellite\nModel: none\n"
TMP_SUFFIX = ".sa-update-tmp"
NOT_A_FILE = "not-a-file"
RESTART = ("required", "recommended", "no")
# Conflict detail -> (text for the owner, action when the owner chooses "replace").
CONFLICTS = {"edited": ("edited; new version in release", "replace"),
             "removed": ("edited; removed from release", "delete"),
             "taken": ("not a release file; the path belongs to a new release file", "replace")}


class Refused(Exception):
    """An expected refusal: the message is printed, nothing was changed, exit 1."""


def say(text: str = "") -> None:
    """Print English ASCII only; any other character is backslash-escaped."""
    print(str(text).encode("ascii", "backslashreplace").decode("ascii"), flush=True)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# --- package and installation ---------------------------------------------------

def is_protected(path: str) -> bool:
    low = path.lower()
    return any(low == item or (item.endswith("/") and low.startswith(item)) for item in PROTECTED)


def check_table(name: str, table: object) -> dict[str, str]:
    """A table maps safe POSIX paths inside the kit area to SHA-256 strings."""
    if not isinstance(table, dict):
        raise Refused(f"the package manifest is damaged: {name} is not a table")
    for path, digest in table.items():
        parts = path.split("/")
        if "\\" in path or ":" in path or any(part in ("", ".", "..") for part in parts) or not isinstance(digest, str):
            raise Refused(f"the package manifest is damaged: bad entry {path!r} in {name}")
        if path not in KIT_ROOT and parts[0] != ".agents":
            raise Refused(f"the package manifest is damaged: {path!r} in {name} is outside the kit")
    return table


def load_manifest() -> dict:
    """Read and verify the package: manifest format, kit paths, and the hash of every kit file."""
    try:
        manifest = json.loads((PACKAGE / MANIFEST).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise Refused(f"cannot read {MANIFEST} in the package {PACKAGE}: {exc}") from None
    if not isinstance(manifest, dict) or manifest.get("manifest") != 1:
        raise Refused(f"{MANIFEST} has an unknown format; this update.py understands manifest 1 only")
    if (not isinstance(manifest.get("version"), str) or not isinstance(manifest.get("src"), str)
            or manifest.get("restart_chat") not in RESTART or not isinstance(manifest.get("notes"), list)
            or not isinstance(manifest.get("history"), dict)):
        raise Refused("the package manifest is damaged: version, src, restart_chat, notes or history is wrong")
    kit = check_table("kit", manifest.get("kit"))
    for version, table in manifest["history"].items():
        check_table(f"history {version}", table)
    for path in sorted(kit):
        if is_protected(path):
            raise Refused(f"the package is not acceptable: its kit lists the protected path {path}")
        source = PACKAGE / path
        if not source.is_file() or sha256(source) != kit[path]:
            raise Refused(f"the package is damaged: {path} is missing or differs from the manifest; "
                          "download and unpack the release again")
    return manifest


def check_target(target: Path) -> None:
    if not (target / "AGENTS.md").is_file() or not (target / ".agents" / "VERSION").is_file():
        raise Refused(f"{target} is not a Soyuz-Apollo installation: AGENTS.md or .agents/VERSION is missing")
    if target == PACKAGE:
        raise Refused("the target is the package itself; pass the installation folder as --target")


@contextmanager
def update_lock(target: Path):
    """The OS releases the lock when the process exits, including after an interruption."""
    core = target / ".agents"
    lock_dir = core / ".git"
    if not lock_dir.is_dir():
        lock_dir = core / BACKUP
        lock_dir.mkdir(exist_ok=True)
    with (lock_dir / "s-a-update.lock").open("ab") as handle:
        handle.seek(0)
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            raise Refused(f"cannot lock {target}; another update or rollback may be running: {exc}") from None
        yield


def latest_update(target: Path) -> tuple[Path, dict] | None:
    base = target / ".agents" / BACKUP
    for folder in sorted(base.iterdir(), reverse=True) if base.is_dir() else []:
        if not folder.is_dir():
            continue
        path = folder / "journal.json"
        try:
            journal = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            continue  # the backup was not published, so it did not start changing release files
        except (OSError, ValueError) as exc:
            raise Refused(f"cannot read rollback journal {path}: {exc}") from None
        if not isinstance(journal, dict):
            raise Refused(f"invalid rollback journal {path}")
        status = journal.get("status")
        if status in ("started", "rolling-back", "applied"):
            return folder, journal
        if status not in ("failed-restored", "rolled-back"):
            raise Refused(f"unknown rollback status in {path}")
    return None


def installed_version(target: Path) -> str:
    lines = (target / ".agents" / "VERSION").read_text(encoding="utf-8-sig", errors="replace").strip().splitlines()
    return lines[0].split(" (src")[0].strip() if lines else "unknown"


def disk_hash(path: Path) -> str | None:
    """SHA-256 of a regular file; None when nothing is there; NOT_A_FILE for a folder or a link."""
    if not os.path.lexists(path):
        return None
    return sha256(path) if path.is_file() and not path.is_symlink() else NOT_A_FILE


def prepare(target: Path) -> dict:
    """Run every check and classify each path of the two tables (decision U7). Writes nothing."""
    check_target(target)
    latest = latest_update(target)
    if latest and latest[1]["status"] in ("started", "rolling-back"):
        raise Refused(f"an unfinished update or rollback is recorded in {latest[0]}; run rollback for this target first")
    manifest = load_manifest()
    source, to, new = installed_version(target), manifest["version"], manifest["kit"]
    if source == to:
        base = new  # repair: the same release with missing or changed files
    elif source in manifest["history"]:
        base = {path: digest for path, digest in manifest["history"][source].items() if not is_protected(path)}
    else:
        raise Refused(f"direct update from version {source} to {to} is not supported; "
                      "install the new release into a new folder as the README describes")
    items = []
    for path in sorted(set(base) | set(new)):
        old, fresh, disk = base.get(path), new.get(path), disk_hash(target / path)
        if disk == NOT_A_FILE:
            raise Refused(f"{path} is a folder or a link where a release file belongs; move it away, then retry")
        if fresh is not None:
            kind = "unchanged" if disk == fresh else "add" if disk is None else "replace" if disk == old else "conflict"
            detail = "" if kind != "conflict" else "edited" if old is not None else "taken"
        else:
            kind = "unchanged" if disk is None else "delete" if disk == old else "conflict"
            detail = "removed" if kind == "conflict" else ""
        items.append((path, kind, detail))
    return {"manifest": manifest, "from": source, "to": to, "items": items,
            "current": source == to and all(kind == "unchanged" for _, kind, _ in items)}


def print_plan(plan: dict) -> None:
    manifest, items = plan["manifest"], plan["items"]
    say(f"UPDATE {plan['from']} -> {plan['to']} (src {manifest['src']})")
    for kind in ("replace", "add", "delete", "conflict"):
        for path, found, detail in items:
            if found == kind:
                say(f"{kind.upper()} {path}" + (f" ({CONFLICTS[detail][0]})" if detail else ""))
    counts = {kind: sum(1 for item in items if item[1] == kind)
              for kind in ("replace", "add", "delete", "conflict", "unchanged")}
    say("SUMMARY " + ", ".join(f"{kind} {count}" for kind, count in counts.items()))
    say(f"RESTART-CHAT {manifest['restart_chat']}")
    for note in manifest["notes"]:
        say(f"NOTE {note}")


# --- git and sa -------------------------------------------------------------------

def git(repo: Path, *args: str, data: bytes | None = None) -> tuple[int, str]:
    stdin = {"input": data} if data is not None else {"stdin": subprocess.DEVNULL}
    try:
        proc = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, **stdin)
    except OSError as exc:
        return 127, f"git cannot run: {exc.strerror or exc}"
    text = (proc.stdout + proc.stderr).decode("utf-8", "replace").strip()
    return proc.returncode, text


def commit_core(target: Path, summary: str) -> None:
    """Commit everything in the core repository when it has changes. Git problems are warnings."""
    core = target / ".agents"
    if not (core / ".git").exists():
        say("WARN git: .agents has no repository; nothing committed")
        return
    code, out = git(core, "status", "--porcelain")
    if code == 0 and not out:
        return
    if code == 0:
        code, out = git(core, "add", "-A")
    if code == 0:
        code, out = git(core, "commit", "-q", "-F", "-", data=f"{summary}\n\n{TOOL_TRAILERS}".encode("utf-8"))
    if code:
        say(f"WARN git: no commit for '{summary}': {(out.splitlines() or ['unknown error'])[0]}")
        return
    say(f"COMMIT .agents {git(core, 'log', '-1', '--format=%h %s')[1]}")


def hide_backup(target: Path) -> None:
    """Add /update-backup/ to .agents/.git/info/exclude so the core repository does not see the folder."""
    git_dir = target / ".agents" / ".git"
    if not git_dir.is_dir():
        return
    exclude, line = git_dir / "info" / "exclude", f"/{BACKUP}/"
    try:
        text = exclude.read_text(encoding="utf-8") if exclude.is_file() else ""
        if line not in text.splitlines():
            exclude.parent.mkdir(exist_ok=True)
            with open(exclude, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(text + ("" if not text or text.endswith("\n") else "\n") + line + "\n")
    except (OSError, UnicodeDecodeError) as exc:
        say(f"WARN git: cannot update .agents/.git/info/exclude: {exc}")


def run_sa(target: Path, command: str) -> tuple[int, list[str]]:
    """Run python sa.py <command> in the target with this interpreter and relay its output."""
    proc = subprocess.run([sys.executable, str(target / "sa.py"), command], cwd=target, capture_output=True,
                          stdin=subprocess.DEVNULL)
    lines = (proc.stdout + proc.stderr).decode("utf-8", "replace").splitlines()
    for line in lines:
        say(f"{command.upper()} {line}")
    return proc.returncode, lines


# --- files, rollback folder, journal ---------------------------------------------

def put(source: Path | bytes, dest: Path) -> None:
    """Write through a temporary name in the same folder, then os.replace."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    temp = dest.with_name(dest.name + TMP_SUFFIX)
    try:
        if isinstance(source, bytes):
            temp.write_bytes(source)
        else:
            shutil.copyfile(source, temp)
        os.replace(temp, dest)
    finally:
        temp.unlink(missing_ok=True)


def prune(target: Path, path: str) -> None:
    """Remove the folders of a removed file that became empty, inside .agents/ only."""
    core, folder = target / ".agents", (target / path).parent
    while folder != core and folder.is_relative_to(core):
        try:
            folder.rmdir()
        except OSError:
            return
        folder = folder.parent


def write_journal(folder: Path, journal: dict) -> None:
    put((json.dumps(journal, indent=2) + "\n").encode("utf-8"), folder / "journal.json")


def make_backup(target: Path, plan: dict, actions: list[dict]) -> tuple[Path, dict]:
    """Create the rollback folder: files.zip with every file to be replaced or deleted, and journal.json."""
    now = datetime.now(timezone.utc)
    label = re.sub(r"[^a-z0-9.-]", "-", f"{plan['from']}-to-{plan['to']}".lower())
    folder = target / ".agents" / BACKUP / f"{now.strftime('%Y%m%dt%H%M%S.%fz')}-{label}"
    saved = [action["path"] for action in actions if action["kind"] in ("replace", "delete")]
    hide_backup(target)
    try:
        folder.mkdir(parents=True)
        with zipfile.ZipFile(folder / "files.zip", "w", zipfile.ZIP_STORED) as archive:
            for path in saved:
                archive.write(target / path, path)
        with zipfile.ZipFile(folder / "files.zip") as archive:
            for path in saved:
                if hashlib.sha256(archive.read(path)).hexdigest() != sha256(target / path):
                    raise OSError(f"the copy of {path} differs from the file")
        after = {action["path"]: plan["manifest"]["kit"].get(action["path"])
                 for action in actions if action["kind"] != "kept"}
        journal = {"from": plan["from"], "to": plan["to"], "src": plan["manifest"]["src"], "after": after,
                   "started": now.strftime("%Y-%m-%dT%H:%M:%SZ"), "actions": actions, "status": "started"}
        write_journal(folder, journal)
    except (OSError, zipfile.BadZipFile) as exc:
        raise Refused(f"cannot create the rollback folder {folder}: {exc}; no release file was changed") from None
    return folder, journal


def restore_plan(target: Path, folder: Path, journal: dict) -> list[tuple[str, bytes | None]]:
    """Check all files before changing any, including after a partially completed rollback."""
    after = journal.get("after")
    if after is None:
        manifest = load_manifest()
        if journal.get("src") != manifest["src"] or journal.get("to") != manifest["version"]:
            raise Refused(f"legacy rollback journal in {folder} needs its matching release package")
        after = {action["path"]: manifest["kit"].get(action["path"]) for action in journal["actions"]}
    changes, conflicts = [], []
    with zipfile.ZipFile(folder / "files.zip") as archive:
        for action in journal["actions"]:
            path, kind = action["path"], action["kind"]
            check_table("journal", {path: ""})
            if is_protected(path) or kind == "kept":
                continue
            if kind in ("replace", "delete"):
                original = archive.read(path)
                before = hashlib.sha256(original).hexdigest()
            elif kind == "add":
                original = before = None
            else:
                raise Refused(f"unknown rollback action for {path} in {folder}")
            current = disk_hash(target / path)
            if current == before:
                continue
            if current == after[path]:
                changes.append((path, original))
            else:
                conflicts.append(path)
    if conflicts:
        for path in conflicts:
            say(f"ROLLBACK-CONFLICT {path} (differs from both release states)")
        raise Refused("rollback would overwrite changes; preserve them and resolve the listed files before retrying")
    return changes


def restore(target: Path, changes: list[tuple[str, bytes | None]]) -> None:
    for path, original in changes:
        dest = target / path
        if original is None:
            dest.unlink(missing_ok=True)
            prune(target, path)
        else:
            put(original, dest)
        expected = hashlib.sha256(original).hexdigest() if original is not None else None
        if disk_hash(dest) != expected:
            raise OSError(f"restored file differs from its backup: {path}")


def restore_failed(folder: Path, exc: Exception) -> int:
    say(f"RESTORE-FAILED {exc}")
    say(f"ROLLBACK-FOLDER {folder}")
    say("MANUAL 1. Close every program that uses the installation folder.")
    say("MANUAL 2. Unpack files.zip from the rollback folder into the installation folder, replacing files.")
    say("MANUAL 3. Delete the files that journal.json in the rollback folder lists with the kind add.")
    say("MANUAL 4. In the installation folder run: python sa.py sync, then: python sa.py doctor")
    return 4


# --- commands ------------------------------------------------------------------------

def cmd_plan(target: Path) -> int:
    plan = prepare(target)
    if plan["current"]:
        say(f"ALREADY-UP-TO-DATE {plan['to']}")
        return 0
    print_plan(plan)
    return 0


def cmd_apply(target: Path, conflicts: str | None) -> int:
    plan = prepare(target)
    if plan["current"]:
        say(f"ALREADY-UP-TO-DATE {plan['to']}")
        return 0
    actions, kept = [], []
    for path, kind, detail in plan["items"]:
        if kind == "conflict" and conflicts is None:
            say(f"CONFLICT {path} ({CONFLICTS[detail][0]})")
            kept.append(path)
        elif kind == "conflict" and conflicts == "keep":
            kept.append(path)
        elif kind != "unchanged":
            actions.append({"path": path, "kind": CONFLICTS[detail][1] if kind == "conflict" else kind})
    if kept and conflicts is None:
        raise Refused(f"{len(kept)} conflicts; nothing was changed. Ask the owner, then repeat with "
                      "--conflicts replace (their versions go to the rollback folder) or --conflicts keep")
    actions += [{"path": path, "kind": "kept"} for path in kept]
    say(f"UPDATE {plan['from']} -> {plan['to']} (src {plan['manifest']['src']})")
    folder, journal = make_backup(target, plan, actions)
    say(f"ROLLBACK-FOLDER {folder}")
    commit_core(target, f"Snapshot before update to {plan['to']}")
    try:
        for action in actions:
            path, kind = action["path"], action["kind"]
            try:
                if kind in ("replace", "add"):
                    put(PACKAGE / path, target / path)
                elif kind == "delete":
                    (target / path).unlink()
                    prune(target, path)
            except OSError as exc:
                held = " (is a program holding it open?)" if isinstance(exc, PermissionError) else ""
                raise OSError(f"cannot {kind} {path}: {exc.strerror or exc}{held}") from None
        code, sync_lines = run_sa(target, "sync")
        if code:
            raise OSError(f"sa.py sync finished with exit code {code}")
        kit = plan["manifest"]["kit"]
        for path, _, _ in plan["items"]:
            if path not in kept and disk_hash(target / path) != kit.get(path):
                raise OSError(f"installed file differs from the release: {path}")
    except BaseException as exc:  # noqa: BLE001 - any failure or Ctrl+C while replacing files restores the previous state
        say(f"FAILED {exc!r}" if isinstance(exc, KeyboardInterrupt) else f"FAILED {exc}")
        try:
            restore(target, restore_plan(target, folder, journal))
        except Refused as error:
            say(f"RECOVERY-BLOCKED {error}")
            return 4
        except (OSError, KeyError, zipfile.BadZipFile) as error:
            return restore_failed(folder, error)
        if run_sa(target, "sync")[0]:
            say("WARN sa.py sync of the restored release finished with an error; run: python sa.py doctor")
        write_journal(folder, journal | {"status": "failed-restored"})
        say(f"ROLLED-BACK {exc}; the installation is at {plan['from']} again")
        return 2
    commit_core(target, f"Update Soyuz-Apollo {plan['to']} (src {plan['manifest']['src']})")
    write_journal(folder, journal | {"status": "applied"})
    problems = run_sa(target, "doctor")[0]
    for path in kept:
        say(f"KEPT {path} (core is partly old)")
    for line in sync_lines:
        match = re.fullmatch(r"changed: ((?:projects|system-projects)/[^/]+/AGENTS\.md)", line.strip())
        if match:
            say(f"HEADER-CHANGED {match.group(1)}")
    say(f"APPLIED-WITH-PROBLEMS {plan['from']} -> {plan['to']}; read the DOCTOR lines" if problems
        else f"APPLIED {plan['from']} -> {plan['to']}")
    say(f"RESTART-CHAT {plan['manifest']['restart_chat']}")
    for note in plan["manifest"]["notes"]:
        say(f"NOTE {note}")
    return 3 if problems else 0


def cmd_rollback(target: Path) -> int:
    latest = latest_update(target)
    if latest is None:
        raise Refused(f"no applied update to roll back in {target / '.agents' / BACKUP}")
    found, journal = latest
    interrupted = journal["status"] in ("started", "rolling-back")
    kept_version = {"path": ".agents/VERSION", "kind": "kept"} in journal.get("actions", [])
    if interrupted:
        say(f"INTERRUPTED the update in {found} did not finish; restoring the files it saved")
    elif installed_version(target) != journal.get("to") and not kept_version:
        raise Refused(f"the installed version is {installed_version(target)}, but the latest applied update "
                      f"in {found} was to {journal.get('to')}; nothing was changed")
    say(f"ROLLBACK {journal['to']} -> {journal['from']}")
    say(f"ROLLBACK-FOLDER {found}")
    try:
        changes = restore_plan(target, found, journal)
        write_journal(found, journal | {"status": "rolling-back"})
        restore(target, changes)
    except (OSError, KeyError, zipfile.BadZipFile) as exc:
        return restore_failed(found, exc)
    problems = run_sa(target, "sync")[0]
    commit_core(target, f"Roll back update to {journal['to']}")
    write_journal(found, journal | {"status": "rolled-back"})
    problems = run_sa(target, "doctor")[0] or problems
    say(f"ROLLED-BACK-WITH-PROBLEMS {journal['to']} -> {journal['from']}; read the SYNC and DOCTOR lines" if problems
        else f"ROLLED-BACK {journal['to']} -> {journal['from']}")
    return 3 if problems else 0


def cmd_verify(archive: Path) -> int:
    checksum = archive.with_name(archive.name + ".sha256")
    try:
        digest = hashlib.sha256(archive.read_bytes()).hexdigest()
        expected = (checksum.read_text(encoding="utf-8-sig").split() or [""])[0].lower()
        with zipfile.ZipFile(archive) as package:
            inside = package.read(MANIFEST)
        own = (PACKAGE / MANIFEST).read_bytes()
    except (OSError, KeyError, ValueError, zipfile.BadZipFile) as exc:
        raise Refused(f"cannot verify {archive}: {exc}") from None
    if digest != expected:
        raise Refused(f"checksum mismatch for {archive.name}: the file has {digest}, {checksum.name} says "
                      f"{expected or 'nothing'}; download the release again")
    if inside != own:
        raise Refused(f"{MANIFEST} inside {archive.name} differs from the one in this package; "
                      "the package was not unpacked from this ZIP")
    say(f"VERIFIED {archive.name} sha256 {digest}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python update.py",
                                     description="Update a Soyuz-Apollo installation in place from this package.")
    commands = parser.add_subparsers(dest="command", required=True, metavar="<command>")
    for name, text in (("plan", "show what apply would do; writes nothing"),
                       ("apply", "update the installation; restores it automatically on failure"),
                       ("rollback", "undo the latest applied update")):
        sub = commands.add_parser(name, help=text)
        sub.add_argument("--target", required=True, type=Path, help="installation root")
    commands.choices["apply"].add_argument("--conflicts", choices=("replace", "keep"),
                                           help="the owner's choice for edited release files")
    commands.add_parser("verify", help="check the downloaded ZIP").add_argument("--zip", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "verify":
            return cmd_verify(args.zip.resolve())
        target = args.target.resolve()
        if args.command == "plan":
            return cmd_plan(target)
        check_target(target)
        with update_lock(target):
            if args.command == "apply":
                return cmd_apply(target, args.conflicts)
            return cmd_rollback(target)
    except Refused as exc:
        say(f"REFUSED {exc}")
        return 1
    except Exception as exc:  # noqa: BLE001 - one-line cause instead of a traceback
        say(f"ERROR unexpected: {type(exc).__name__}: {exc}")
        return 2


if __name__ == "__main__":
    sys.exit(main())
