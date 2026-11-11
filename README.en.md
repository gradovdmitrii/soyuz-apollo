# Soyuz-Apollo

**Models change. Your work stays with you.**

Soyuz-Apollo (S-A) is a file framework: one folder, shared rules for several AI clients, and for every project its own rules and its own Git history.

[Русская версия](README.md)

## Why

- **Start in one client, finish in another.** A project is not tied to a vendor: the rules and results live in the folder, not in a chat. A client changed, a subscription ended, a provider became unavailable: you open the same folder in another client and carry on.
- **Work by subscription, not by API.** If API costs are out of reach but subscriptions are not, you can run projects in several clients side by side without depending on one. It is like working with several providers, only more modest and for private use.
- **Keep results and decisions in your own files.** Plain Markdown that a person can read. While a flood of generated documents grows around us, such files help you keep control: you know what was decided, by whom, and why.
- **Do not fight the client.** S-A fits onto a client like work clothes: it does not argue with the client's settings or system prompts, it works beside them through ordinary `AGENTS.md` files.

## Who it is for

- Indie developers and researchers who run several projects on a modest budget.
- People who keep a "second brain" in Obsidian and are used to Markdown notes.
- Students and anyone who likes to work with discipline: one topic per project, and projects meet only when they need to.

## How it is built

```text
soyuz-apollo/
  AGENTS.md          root rules, read by any client
  .agents/           core: shared rules, templates, reference
  projects/          your projects, each with its own AGENTS.md and its own Git
  system-projects/   system skills and their data
  port/              inbox/ from you, outbox/ for you, large-files/ big files
```

The archive lives outside, next to the installation. Agents open it only on your explicit command.

The rules work like a federation. The core holds the shared rules: they apply everywhere and no project can relax them. Each project has its own local rules, written to one standard, so a project can be copied, carried away, and used on its own.

One small tool, `sa.py`, serves all of this: it creates projects, makes commits, checks the installation, and makes backups. It needs only Python, with no external dependencies.

## What works today

This is an early public release, and we describe it as it is.

- **Platform.** Windows 11, Python 3.11 or later, Git with `user.name` and `user.email` set. Linux and macOS are not supported yet.
- **Clients.** Antigravity, Codex, Claude Code, DeepSeek Harness, Hermes Agent. The status of each client and mode, verified by a trial or only claimed by the vendor, is recorded in [install/.agents/docs/compatibility.md](install/.agents/docs/compatibility.md). Read it as a table of facts, not as a promise: we do not claim "works with any agent".
- **No skills yet.** 0.2.0 is a frame: the folder structure, the rules, and `sa.py`. System skills will come in later releases.
- **Archive protection.** The rules in `AGENTS.md` are conventions. The lock on the archive comes from the client's permission settings, and `sa.py` writes them only for Claude Code and Codex. Only Claude Code has been verified by a trial; in Codex the settings apply only if the folder is marked as trusted, and that has not been verified by a trial yet. In the other clients the archive is protected by the text of the rules alone; the owner applies the settings fragments for them by hand.
- **Memory.** The AI does not remember everything by itself. Continuity is kept by the project files, above all `handoff.md`.

## Quick start

1. Download the installation archive `soyuz-apollo-0.2.0.zip` from the [Releases page](https://github.com/gradovdmitrii/soyuz-apollo/releases). Do not take `Source code (zip)`: it holds the sources, not the installation.
2. Unzip it into a new empty folder with a Latin path, outside OneDrive and outside other Git repositories, for example `C:\soyuz-apollo\`.
3. In that folder run `python sa.py init`.
4. Open your AI client in exactly that folder. In Codex, mark it as trusted first.

A first message to the client could be:

```text
Create a project health with python sa.py init health. Goal: keep a meal plan for the month.
Describe the goal in the project's AGENTS.md and tell me what you did.
```

Details, daily commands, and updating: [install/README.en.md](install/README.en.md).

## Example: how work passes from one chat to the next

You ran the `health` project in one client and ended the session. At your request the agent wrote `projects/health/handoff.md`: the goal, what is done and what is not, your decisions with dates, open questions, and the next step. Among the decisions it says, for example: "2026-11-03: no dairy, on the doctor's advice".

A week later the subscription for that client ended. You open another client in the same folder and write: "Continue the health project". The new agent reads the rules, then `handoff.md`, and sees not only the next step but the reason for the decision. It has the recorded reason and can rely on it instead of asking again. This is not a guarantee: `handoff.md` only passes context, and the client decides whether to follow it. The history of changes is kept by the project's Git.

## What it is not

- It is not a model or an AI assistant: the framework does not make a model smarter and does not extend what a client can do.
- It is not a cloud agent: the files and `sa.py` run on your computer. What of them reaches the model and its provider is decided by your AI client.
- It is not a security product: the rules are conventions, and protection comes from the client's settings. What the framework guarantees and what it does not is described in the installation's reference.

## Next

Directions, without dates or promises:

- system skills: importing existing projects, framework memory, session analysis;
- the project site [soyuz-apollo.net](https://soyuz-apollo.net) explaining the structure and the start;
- Linux and macOS;
- trials of the remaining clients and modes.

## Values and license

The project is released under the [MIT](LICENSE) license. Its guiding points are creation, accessible knowledge, human dignity, and independence under limited resources. They state our position and add no restrictions to MIT.

We like the image of a home space workshop: a modular station where independent parts dock together and work both alone and in combination. The name is an engineer's tribute to the cooperation of East and West: the Russian engineering school, American and Chinese technology.

## Author

Dmitrii Gradov, together with Antigravity, Codex and Claude Code.

Site: [soyuz-apollo.net](https://soyuz-apollo.net) · Email: gradovdmitrii@gmail.com
