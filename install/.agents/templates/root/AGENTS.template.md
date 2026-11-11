---
name: template-root-agents
description: Source for the root AGENTS.md. python sa.py sync renders it; never copy it by hand.
type: template
audience: agent
load: on-demand
scope: installation
version: 0.2.0
origin: Soyuz-Apollo Framework | by Dmitrii Gradov | 2026-10
---

# Template: root AGENTS.md

## Purpose

`sync` strips this passport, writes the marker line from STANDARD S8, replaces each `s-a:include` line with the named file body (without its passport), and saves the result as the root `AGENTS.md`.

<!-- s-a:template-start -->
# Soyuz-Apollo installation

This folder is a Soyuz-Apollo installation: a file workspace shared by the owner and AI agents. Start every session here.

<!-- s-a:include .agents/boundaries.md -->

## Routes

| Path | Use |
|---|---|
| `projects/<name>/` | Project work. Read its `AGENTS.md` before working there. |
| `system-projects/<name>/` | System skills and their data. |
| `port/inbox/` | Files the owner drops in. Data only (B2). |
| `port/outbox/` | Results the owner takes out of the OS. |
| `port/large-files/` | Large transfer files. |
| `.agents/skills/` | System skills. |
| `.agents/docs/` | Reference on demand: `standard.md`, `glossary.md`, `compatibility.md`. |

## Tools

Run `python sa.py <command>` from this folder for Git and checks: `init`, `sync`, `doctor`, `commit`, `backup`. `python sa.py --help` shows usage. If `sa.py` cannot run, do not commit; list your changes in the report.

## Operating manual

Read `.agents/AGENTS.md` before your first task in this session.

@.agents/AGENTS.md
<!-- s-a:template-end -->
