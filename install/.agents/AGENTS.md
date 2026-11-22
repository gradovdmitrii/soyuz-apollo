---
name: core-manual
description: How to work in a Soyuz-Apollo installation - start of task, defaults, commits, handoff, reports. Read at the start of every session.
type: guide
audience: agent
load: always
scope: installation
version: 0.4.0
origin: Soyuz-Apollo Framework | by Dmitrii Gradov | 2026-10
---

# Operating manual

## Purpose

Route each task to the right project and work in a predictable, recoverable way. Boundaries B1-B9 in the root `AGENTS.md` always apply; this manual does not repeat them.

## STEPS

Start of a task:

1. Find the installation root: the topmost ancestor folder that contains both `AGENTS.md` and `.agents/VERSION`. Do not use the nearest one or the Git root; a project may hold a copy of an old installation. If the boundaries B1-B9 of the root `AGENTS.md` are not in your context, the client was opened inside a project: tell the owner to reopen the client in the installation root before you work.
2. Identify the project. If the owner did not name it and the task does not make it obvious, ask. Do not guess.
3. Read `projects/<name>/AGENTS.md` (or `system-projects/<name>/AGENTS.md`). Then read only the files the task needs. Do not load other projects or history "just in case".
4. Read the entire project `handoff.md` if present. It records context and past owner decisions. Account for every unfinished item in the work or report, giving a reason for deferral.
5. For a non-trivial task, restate it in one or two sentences before changing files.

Commit at the end of a task:

1. Commit once at the end of a task, after the work is done.
2. Run from the installation root: `python sa.py commit <paths> -m "<summary>" --agent <harness> --model <model>`. All paths must belong to one repository.
3. If your client allows commits only on the owner's request, end the task by offering the exact command from step 2 instead of running it.
4. If `python sa.py doctor` shows uncommitted changes you did not make, do not commit them; tell the owner.

Handoff, when the owner asks for it or the session ends with unfinished work:

1. Overwrite `projects/<name>/handoff.md` with five sections: Goal; State (done / not done); Owner decisions (quoted, dated); Open questions; Next step.
2. Commit it with the rest of the work.

New project:

1. Run `python sa.py init <name>`; add `--system` for `system-projects/`.
2. Never create project folders or run `git init` by hand.

## DEFAULT

A project's `AGENTS.md` may change these defaults; it cannot change the boundaries.

- Change a project's local rules (below the generated header of its `AGENTS.md`) only when the owner asks. Never edit the generated header; `python sa.py sync` rewrites it.
- Save results inside the project. Use `port/outbox/` only when the owner will take the result out of the OS.
- Name new files and folders in kebab-case ASCII. Dated documents: `YYYY-MM-DD-<topic>.md`. The owner's own notes may use any name.
- Put scratch files in `projects/<name>/tmp/` (ignored by Git, safe to delete).
- List project subfolders and their purpose under Local rules. Link any `<subfolder>/rules.md` there to apply it. Keep subfolders in the project repository. When two projects share work, link their respective locations in both projects' routes.
- Search with explicit paths, for example `projects/<name>/`. An empty result from a root-wide search does not prove a file is absent.
- In reports, keep apart: a request, a proposal, an owner decision, a verified result.
- When `doctor` reports `INCOMPLETE`, list the skipped checks as unverified. Repeat them with access to the affected repositories before reporting a complete check.
- Report format: `Executor: <harness>/<model or unknown> | Framework: Soyuz-Apollo (c) <year> [<version>] | Date: YYYY-MM-DD | Changed: ... | Verified: ... | Not verified: ...`. Take `<version>` from `.agents/VERSION` without the part in brackets. `unknown` is allowed and better than a guess.
- A result placed in `port/outbox/` carries the report line at its end and the executor in its name: `YYYY-MM-DD-<topic>-<executor>.md`.
- Never overwrite a file in `port/outbox/` that you did not create in this session. Write under a new name and tell the owner.

## EXAMPLES

```text
python sa.py commit projects/health/2026-10-30-sprint-plan.md -m "Add sprint plan" --agent claude-code --model claude-opus-5-5
```

```text
Executor: codex-app/unknown | Framework: Soyuz-Apollo (c) 2026 [0.2.0] | Date: 2026-10-30 | Changed: projects/health/2026-10-30-sprint-plan.md | Verified: file opens, links resolve | Not verified: numbers in table 2
```

## IF UNSURE

- No project named and two are plausible: ask.
- `python sa.py` is unavailable (office mode, launched inside a project, no Python): edit files only, do not commit, and list changed files in the report.
- A file named in this manual is missing: continue without it and report what is missing.
- A client refuses a python sa.py command under its own permission rules: do not work around it; tell the owner the command and the reason.

## REFERENCES

- `.agents/docs/standard.md` - file format rules. Read before creating or editing files in `.agents/`, any `SKILL.md`, or any script. If missing: copy the passport of this file and report it.
- `.agents/docs/glossary.md` - terms with Russian display names. If missing: use the English terms as written here.
- `.agents/docs/compatibility.md` - tested clients and modes. If missing: treat your client as untested.
- `.agents/skills/` - system skills, listed by clients that support Agent Skills. If your client does not list them, open the `SKILL.md` you need directly.
