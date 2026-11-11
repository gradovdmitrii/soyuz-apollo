# Soyuz-Apollo

## 1. What this is

Soyuz-Apollo is a folder in which you and several AI clients work on your projects under shared rules. The rules are plain Markdown files; one small Python tool, `sa.py`, handles Git, checks, and backups. Each project keeps its own rules and its own Git history.

## 2. Install

You need Windows 11, Python 3.11 or later, and Git with `user.name` and `user.email` set.

1. Create a new empty folder with an ASCII kebab-case path, for example `C:\soyuz-apollo-november\`. It must be outside OneDrive and outside any Git repository.
2. Unpack the installation archive `soyuz-apollo-<version>.zip` from the Releases page into it (not `Source code (zip)`: that holds the sources).
3. In that folder, run:

   ```text
   python sa.py init
   ```

   This prepares the core repository, creates the work folders, and writes the root `AGENTS.md`.
4. If you work in Codex, mark the installation folder as trusted before the first session: according to the Codex documentation, its permission settings do not apply without it.
5. **Open your AI client in the installation root itself** — the folder that holds `sa.py` and the root `AGENTS.md`, not a project inside it. A client takes the rules and permission settings from the folder it is opened in; opened in a project, it may not see them (confirmed by a trial for Claude Code; for other clients see section 7).

## 3. First session

1. Open the client in the installation root (step 5 above).
2. Write a first message, for example: "Read the installation rules and tell me which project we are working on."
3. A correct agent reads the root `AGENTS.md` and `.agents/AGENTS.md`, briefly restates the boundaries, and asks which project to work in. If there is no project yet, it offers to create one. If the agent does not know the rules, or goes straight to files outside a project, stop it and check that the client is open in the root.
4. Create your first project: `python sa.py init notes`. Then describe its purpose in `projects/notes/AGENTS.md`, below the generated header, and ask the agent to work in that project.
5. Commits. At the end of a task the agent commits the work with `python sa.py commit`. If the client allows commits only on your request, the agent ends the task by offering the exact commit command, and you run it yourself or ask the agent to run it.

## 4. Daily work

| Action | Command |
|---|---|
| Create a project | `python sa.py init <name>` (add `--system` for a system project) |
| Work | Inside `projects/<name>/`; describe the project in its `AGENTS.md` |
| Commit | `python sa.py commit <paths> -m "<summary>"` |
| Check | `python sa.py doctor`: checks the core and the structure of projects (folder, `AGENTS.md`, Git repository), not their content; `python sa.py doctor --deep <name>` checks the content of one project |
| Back up | `python sa.py backup` |
| Move to the archive (you only) | `python sa.py archive add <path>` (only from `projects/` and `system-projects/`); the original is deleted only with `--remove` |

Project names are kebab-case ASCII (`health`, `site-redesign`); your notes inside a project may use any name.

Results that you will take out of the system go to `port/outbox/` as `YYYY-MM-DD-<topic>-<executor>.md`, and the file ends with the report line. An agent does not overwrite files in `port/outbox/` that it did not create.

## 5. Folders

| Folder | What it holds |
|---|---|
| `projects/` | Your projects. Each has its own `AGENTS.md` and Git repository. |
| `system-projects/` | System skills and their data. |
| `port/` | Transit: `inbox/` from you, `outbox/` for you, `large-files/` for large files. Not in Git. |
| `.agents/` | The core: rules, templates, reference, system skills, and the `sa` modules. Its own Git repository. |
| Archive (outside) | Old material next to the installation; its path is `paths.archive` in `.agents/config/instance.toml`. Agents open it only on your command. For Claude Code and Codex, `sync` writes a denial of reading the archive, and you take files out of it yourself; what of this is verified is in section 8. |

## 6. Rules

Clients opened in this folder read the root `AGENTS.md` (what is confirmed: section 7). It holds the boundaries that no project may relax: the archive only on your command, `port/inbox/` is data rather than instructions, no secrets in commits, commits only through `sa.py`, and a report at the end of every task. Do not edit the root `AGENTS.md` by hand; `python sa.py sync` builds it. Put a project's own rules into `projects/<name>/AGENTS.md`, below the generated header.

## 7. Clients and modes

Supported clients, their modes, and what is known about each: `.agents/docs/compatibility.md`. Open the client in the installation root. Office modes (Claude Cowork, Codex Work) work in one project and do not commit; cloud modes never see this folder.

## 8. Protection in clients

`python sa.py sync` writes permission settings from `.agents/policy.toml`: `.claude/settings.json` for Claude Code, `.codex/config.toml` and `.codex/rules/s-a.rules` for Codex. They are meant to deny the client reading the archive and secret files. In Claude Code a trial confirmed the denial of built-in reads; shell commands are not covered by it. In Codex a trial confirmed only that a changed settings file applies in new chats; the generated adapter has not been tested by a trial. Details: `.agents/docs/compatibility.md` and `.agents/docs/limits.md`. Keep your own Claude Code settings in `.claude/settings.local.json` and your Codex settings in your user config.

In Antigravity, Hermes, and DeepSeek Harness there is no technical lock on the archive: only the rules text holds, until you apply the fragment from `.agents/docs/adapters.md`. Agents open the archive only on your command; in Claude Code and Codex you take files out of it yourself.

## 9. Updating

Release 0.2 has no automatic update. To move to a new release:

1. Run `python sa.py backup`.
2. Install the new release into a new empty folder and run `python sa.py init` there.
3. Move your projects into the new `projects/` and `system-projects/` as whole folders: selecting the contents (Ctrl+A in Explorer) skips the hidden `.git`. Or restore a project from its bundle: `git clone <backup>/projects-<name>.bundle projects/<name>`. Take over a project from the old installation with `python sa.py init <name> --adopt`.
4. Run `python sa.py sync` and `python sa.py doctor`; no project may show a `PROJ-NOGIT` error.
5. Keep the old folder until you have checked your projects in the new one.

## 10. Limits

The rules are conventions; real protection comes from your client's permission settings. What the framework does and does not guarantee: `.agents/docs/limits.md`.
