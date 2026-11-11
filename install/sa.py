"""
---
name: s-a-satellite
description: Facade of S-A-Satellite, the Soyuz-Apollo tool - run python sa.py <command> from the installation root; python sa.py --help lists the commands.
type: script
inputs: init [name] [--system] [--adopt], sync [--force], doctor, commit <paths> -m <message>, backup [--dest DIR], archive add <path> [--remove], archive list
outputs: command output; exit 0 ok, 1 refused or checks failed, 2 unexpected error
side_effects: those of the chosen command; never writes Python bytecode
destructive: false
requires_owner: false
version: 0.2.0
origin: Soyuz-Apollo Framework | by Dmitrii Gradov | 2026-10
---
"""

import sys

sys.dont_write_bytecode = True

if sys.version_info < (3, 11):
    sys.stderr.write("S-A-Satellite needs Python 3.11 or newer; this is Python %d.%d.\n" % tuple(sys.version_info[:2]))
    sys.exit(2)

from pathlib import Path  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent / ".agents"))

if __name__ == "__main__":
    try:
        import sa.cli
    except ImportError as exc:
        sys.stderr.write("error: cannot load .agents/sa (%s); the installation is damaged.\n" % exc)
        sys.exit(2)
    sys.exit(sa.cli.main())
