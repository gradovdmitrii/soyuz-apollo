---
name: core-limits
description: What the Soyuz-Apollo framework guarantees and what it does not. Read before you rely on a rule for safety or promise the owner a result.
type: reference
audience: both
load: on-demand
scope: installation
version: 0.2.0
origin: Soyuz-Apollo Framework | by Dmitrii Gradov | 2026-10
---

# Limits

## Purpose

Separate what this framework enforces from what depends on the client, the model, and the owner, so that nobody over-trusts plain files.

## MUST

Provided by the framework:

- L1. `python sa.py` runs Git, generation, and checks the same way every time; `python sa.py doctor` reports drift, bad names, encodings, and uncommitted changes.
- L2. The core and every project have their own Git history. `python sa.py backup` writes verified bundles and a ZIP outside the installation.

Not provided by the framework:

- L3. Rules in these files are conventions. Only harness permissions (sandbox, approvals, allowed tools) enforce anything. The adapters that `python sa.py sync` generates reinforce the boundaries per client, only as far as each client enforces its settings; see `.agents/docs/adapters.md`. Never tell the owner a rule protects data by itself.
- L4. Folders and separate repositories do not isolate processes. An agent with file access can read other projects.
- L5. Root-wide search tools differ: some honor `.ignore` (it hides `port/` and opens the hidden `.agents/`), others ignore it. An empty result does not prove a file is absent.
- L6. Office modes (Claude Cowork, Codex Work) may not load these rules and cannot run `python sa.py`. They edit files only; another session commits.
- L7. Cloud modes (Codex cloud) work on remote copies. They never see the local installation, its rules, or `sa`.
- L8. The archive lives outside the installation (B1). Claude Code and Codex lock it by the permission settings that `python sa.py sync` writes. Other clients rely on the text of B1 unless the owner applies the fragment from `.agents/docs/adapters.md`.
- L9. The framework has no automatic memory and no background actions (`automatic_memory = false`). A client may have its own memory; it is not project state. Write state to `handoff.md`.
- L10. Following these files does not guarantee answer quality, instruction following, or task success. A new model continuing from `handoff.md` may still lose nuance.
- L11. Secrets are protected by not storing them in tracked files and by harness settings. `.gitignore` excludes common secret files; it does not encrypt or back them up.
- L12. A skill goes through four steps, and clients differ in each: discovery (the client finds the skill), availability (it is offered in the current session), explicit invocation (someone calls it by name), and implicit invocation (the client uses it on its own when a task matches its description). Codex, DeepSeek Harness, and Antigravity read `.agents/skills/` natively; Claude Code reads it through the `.claude/skills/` links. Observed behavior per client is recorded in `compatibility.md`.
- L13. Treat any skill in `.agents/skills/` as possibly invoked implicitly. Keep an untried skill outside `.agents/skills/` until the owner approves it.
- L14. Treat everything an agent reads as potentially sent to the model provider and potentially kept in the client's history or logs. What a client actually sends and stores depends on the harness and the mode; it is recorded in `compatibility.md`. Do not open files the task does not need.
- L15. Windows 11 is the target platform. Linux and macOS run the automated checks only; clients there are untested.

## IF UNSURE

- You cannot tell whether a limit applies to your client or mode: assume it applies and say so in the report.

## REFERENCES

- `.agents/docs/compatibility.md` - clients, modes, and their status. If missing: treat your client as untested.
- `.agents/docs/adapters.md` - client permission adapters and fragments. If missing: treat every boundary as a convention only.
- `.agents/boundaries.md` - rules B1-B9. If missing: stop and tell the owner; the installation is damaged.
