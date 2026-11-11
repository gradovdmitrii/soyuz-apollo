"""
---
name: s-a-cli
description: Command-line dispatcher for S-A-Satellite - parses arguments, runs one of init, sync, doctor, commit, backup, archive, and maps errors to exit codes.
type: script
inputs: command line of python sa.py
outputs: command output on stdout, refusals and errors on stderr; exit 0 ok, 1 refused or checks failed, 2 unexpected error
side_effects: those of the chosen command
destructive: false
requires_owner: false
version: 0.2.0
origin: Soyuz-Apollo Framework | by Dmitrii Gradov | 2026-10
---
"""

from __future__ import annotations

import argparse
import traceback

from . import archive, backup, commit, common, doctor, init, sync
from .common import Refused


def build_parser() -> argparse.ArgumentParser:
    shared = argparse.ArgumentParser(add_help=False)
    shared.add_argument("--debug", action="store_true", default=argparse.SUPPRESS,
                        help="print a traceback on unexpected errors")
    parser = argparse.ArgumentParser(prog="python sa.py", parents=[shared],
                                     description="S-A-Satellite, the Soyuz-Apollo installation tool. "
                                                 "Run it from the installation root.")
    commands = parser.add_subparsers(dest="command", required=True, metavar="<command>")
    p = commands.add_parser("init", parents=[shared], help="prepare the installation; with a name, create a project")
    p.add_argument("name", nargs="?", help="new project name in kebab-case; omit to prepare the installation")
    p.add_argument("--system", action="store_true", help="create the project in system-projects/")
    p.add_argument("--adopt", action="store_true",
                   help="take over an existing project folder with its own .git; changes no files (owner command)")
    p = commands.add_parser("sync", parents=[shared], help="regenerate AGENTS.md files, .claude/skills links and client adapters")
    p.add_argument("--force", action="store_true", help="overwrite a root AGENTS.md that has no generated marker")
    p = commands.add_parser("doctor", parents=[shared], help="check the installation; read-only")
    p.add_argument("--deep", metavar="NAME",
                   help="also run the full content checks inside one project: its name, or projects/<name> or "
                        "system-projects/<name> when both exist")
    p = commands.add_parser("commit", parents=[shared], help="commit explicit paths in one repository")
    p.add_argument("paths", nargs="+", help="files or folders, all in one repository")
    p.add_argument("-m", "--message", required=True, help="commit summary")
    p.add_argument("--agent", help="harness name; default $SA_AGENT, else unknown")
    p.add_argument("--model", help="model id; default $SA_MODEL, else unknown")
    p.add_argument("--co-author", help='"Name <email>"; default $SA_CO_AUTHOR')
    p.add_argument("--core", action="store_true", help="allow a commit in the core repository .agents/")
    p = commands.add_parser("backup", parents=[shared], help="bundle every repository and zip the installation")
    p.add_argument("--dest", help="destination folder outside the installation")
    p = commands.add_parser("archive", parents=[shared], help="move a project or file to the archive (owner command)")
    actions = p.add_subparsers(dest="action", required=True, metavar="<action>")
    q = actions.add_parser("add", parents=[shared], help="copy and verify; with --remove delete the original")
    q.add_argument("path", help="project folder or file inside the installation")
    q.add_argument("--remove", action="store_true", help="delete the original after the copy is verified")
    actions.add_parser("list", parents=[shared], help="print the top-level names in the archive")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        root = common.find_root()
        if args.command == "init":
            if args.name is not None:
                return init.run_project(root, args.name, args.system, args.adopt)
            if args.system or args.adopt:
                raise Refused("--system and --adopt need a project name: python sa.py init <name> --adopt")
            return init.run_installation(root)
        if args.command == "sync":
            return sync.run(root, args.force)
        if args.command == "doctor":
            return doctor.run(root, args.deep)
        if args.command == "commit":
            return commit.run(root, args.paths, args.message, args.agent, args.model, args.co_author, args.core)
        if args.command == "archive":
            return archive.run_add(root, args.path, args.remove) if args.action == "add" else archive.run_list(root)
        return backup.run(root, args.dest)
    except Refused as exc:
        common.say(str(exc), err=True)
        return 1
    except KeyboardInterrupt:
        common.say("interrupted", err=True)
        return 2
    except Exception as exc:  # one-line cause; the traceback only with --debug
        if getattr(args, "debug", False):
            traceback.print_exc()
        common.say(f"error: {' '.join(str(exc).split()) or type(exc).__name__}", err=True)
        return 2
