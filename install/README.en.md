# Soyuz-Apollo

## 1. What this is

Soyuz-Apollo is a folder in which you and several AI clients work on your projects under shared rules. The rules are plain Markdown files; one small Python tool, `sa.py`, handles Git, checks, and backups. Each project keeps its own rules and its own Git history.

## 2. Install

You need Windows 11, Python 3.11 or later, and Git.

1. Create an empty folder with an ASCII kebab-case path outside OneDrive and outside any Git repository, for example `C:\soyuz-apollo-november\`. In Codex, mark it as trusted before starting.
2. **Open your AI client in the installation root itself** and send the prompt card:

   ```text
   Install Soyuz-Apollo in this folder following the README instructions: https://github.com/gradovdmitrii/soyuz-apollo
   ```

   If you already unpacked `soyuz-apollo-0.4.0.zip` from the Releases page (not `Source code (zip)`) into that folder yourself, send: `Install Soyuz-Apollo following the instructions in README.en.md`.
3. **For the agent.** Verify that the folder is outside OneDrive and Git. If `sa.py` is absent, download the ZIP and `.sha256` from Releases, verify the checksum, and unpack here. Ask up to two questions: Git name and email if missing, then the first project's kebab-case name and goal. Run `python sa.py init` and `python sa.py init <name>`. Write the goal below the generated header and run `python sa.py commit projects/<name>/AGENTS.md -m "Set project purpose"`. Run `python sa.py doctor` and ask the owner to open a **new chat** in the installation root.

## 3. First session

1. Open a new chat in the installation root (the folder that holds `sa.py` and the root `AGENTS.md`). A client takes the rules and permission settings from the folder it is opened in; opened in a project, it may not see them (confirmed by a trial for Claude Code; for other clients see section 7).
2. Write, for example: "Read the installation rules and continue the `<name>` project." A correct agent reads the root `AGENTS.md`, `.agents/AGENTS.md`, and the project's `AGENTS.md`, and briefly restates the boundaries and task.
3. At the end of a task the agent commits the work with `python sa.py commit`. If the client allows commits only on your request, the agent ends the task by offering the exact commit command.

## 4. Daily work

| Action | Command |
|---|---|
| Create a project | `python sa.py init <name>` (add `--system` for a system project) |
| Work | Inside `projects/<name>/`; describe the project in its `AGENTS.md` |
| Commit | `python sa.py commit <paths> -m "<summary>"` |
| Check | `python sa.py doctor` checks the core, required document sections and project structure. Add `--deep <name>` to check one project's content. `INCOMPLETE` means some Git checks could not run. |
| Back up | `python sa.py backup`. The ZIP omits each project's top-level `tmp/` directory and lists the omissions in `backup-report.txt`. |
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

You can update in place to 0.4.0 from 0.3.0, 0.2.0 or 0.2.0-alpha.2. The update preserves the folder path, projects, Port and settings. Repeated `sa.py init` also preserves `update.py` and `release-manifest.json` in the installation root. Send this prompt card in a chat outside the installation or after temporarily switching permissions in the client UI (the `s-a` profile in Codex makes `.agents/` read-only):

```text
Update the Soyuz-Apollo installation in <installation path> following the README instructions: https://github.com/gradovdmitrii/soyuz-apollo
```

**For the agent (update; do not edit files by hand, only run `update.py`):**

1. Download the ZIP and `.sha256` from Releases, verify the checksum, and unpack into a separate temporary folder outside the installation.
2. In that folder run:

   ```text
   python update.py verify --zip <archive>
   python update.py plan --target <installation path>
   python update.py apply --target <installation path>
   ```

3. `plan` writes nothing. Ask the owner how to resolve conflicts: replace (`--conflicts replace`, default, with a backup) or keep (`--conflicts keep`).
4. A replacement or `sync` failure triggers automatic recovery. After an interruption, start with `python update.py rollback --target <installation path>`. New edits block rollback. On `RESTART-CHAT required` or `recommended`, ask the owner to open a new chat.

## 10. Limits

The rules are conventions; real protection comes from your client's permission settings. What the framework does and does not guarantee: `.agents/docs/limits.md`.
