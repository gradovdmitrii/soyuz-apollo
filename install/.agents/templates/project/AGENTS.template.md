---
name: template-project-agents
description: Source for projects/<name>/AGENTS.md. python sa.py init creates the file; python sa.py sync refreshes the generated header.
type: template
audience: both
load: on-demand
scope: project
version: 0.2.0
origin: Soyuz-Apollo Framework | by Dmitrii Gradov | 2026-10
---

# Template: project AGENTS.md

## Purpose

`init` strips this passport, fills `{{name}}` and `{{kind}}`, and renders the include. Later, `sync` rewrites only the text between the `s-a:begin` and `s-a:end` markers; the local rules below them belong to the owner.

<!-- s-a:template-start -->
<!-- s-a:begin generated from .agents/templates/project/AGENTS.template.md -->
# Project: {{name}}

This is a {{kind}} inside a Soyuz-Apollo installation; the installation root is `../../`. If the root `AGENTS.md` is not already in your context, read `../../AGENTS.md` and `../../.agents/AGENTS.md` now. If you cannot read them, these boundaries still apply:

<!-- s-a:include .agents/boundaries.md -->

If the local rules below still contain `TODO:` lines, ask the owner for the project purpose before substantial work.
<!-- s-a:end generated -->

# Local rules

<!-- Owner: replace each TODO line. Any language. Delete lines you do not need. -->

- Purpose: TODO: what this project is for
- Done when: TODO: how the owner checks a result
- Results: TODO: where results go; default: inside this project
- Local defaults: TODO: exceptions to the manual's DEFAULT section, or "none"
- Project skills: TODO: `.agents/skills/` inside this project, or "none"
<!-- s-a:template-end -->
