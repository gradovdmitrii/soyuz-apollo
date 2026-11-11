---
name: core-standard
description: File format rules for Soyuz-Apollo - passports, sections, writing, naming, encoding, generated files, scripts. Read before creating or editing any file in .agents/, any SKILL.md, or any script.
type: reference
audience: agent
load: on-demand
scope: installation
version: 0.2.0
origin: Soyuz-Apollo Framework | by Dmitrii Gradov | 2026-10
---

# Standard

## Purpose

One format for every system file, so that agents and `python sa.py doctor` can understand a file from its first lines. Applies to the files listed in S1. Does not apply to the owner's notes and documents inside projects.

## MUST

### S1. Scope

| Files | Passport | Checked by `doctor` |
|---|---|---|
| Every `.md` and `.py` in `.agents/` | required | ERROR if missing |
| Every `SKILL.md`, anywhere | required (skill form, S3) | ERROR if missing |
| Every `.py` script in `system-projects/` | required (script form, S9) | ERROR if missing |
| Every `.ps1` and `.sh` script in `system-projects/` | required (comment form, S9) | not checked in 0.2 |
| Scripts in `projects/` | recommended | INFO |
| Generated files (S8) | marker instead of passport | ERROR if marker missing |
| Root `README.md`, `README.en.md`, `LICENSE`; project notes and documents | not used | - |

### S2. Passport (front matter)

- Put the passport at the very top, between two `---` lines.
- One field per line: `key: value`. No multi-line values, no quotes, no nested keys (except `metadata:` in S3).
- Fields, in this order:

| Field | Value |
|---|---|
| `name` | Unique id, kebab-case ASCII (`core-manual`). For a skill: equal to its folder name |
| `description` | One line: what the file is and when to read it |
| `type` | `boundaries`, `guide`, `procedure`, `skill`, `reference`, `template`, `script` |
| `audience` | `agent`, `human`, `both` |
| `load` | `always` (in context every session) or `on-demand` |
| `scope` | `installation`, `project`, `skill` |
| `version` | Framework version of the last change (`0.2.0`) |
| `origin` | `Soyuz-Apollo Framework \| by <Author> \| <YYYY-MM>`; third-party files keep their own origin |

Example:

```yaml
---
name: core-manual
description: How to work in a Soyuz-Apollo installation. Read at the start of every session.
type: guide
audience: agent
load: always
scope: installation
version: 0.2.0
origin: Soyuz-Apollo Framework | by Dmitrii Gradov | 2026-10
---
```

### S3. Skill form (`SKILL.md`)

The Agent Skills specification allows only `name`, `description`, `license`, `compatibility`, `metadata`, `allowed-tools` at the top level. Put all other passport fields under `metadata:` as strings, indented by two spaces:

```yaml
---
name: chronicle
description: Keeps a dated chronicle of project events. Use when the owner asks to record or review what happened.
metadata:
  type: skill
  audience: agent
  load: on-demand
  scope: installation
  version: 0.2.0
  origin: Soyuz-Apollo Framework | by Dmitrii Gradov | 2026-10
---
```

- `name`: lowercase letters, digits, single hyphens; equal to the folder name.
- `description`: up to 1024 characters; say what the skill does and when to use it.
- Keep `SKILL.md` under 500 lines; move details to `references/`.

### S4. Sections

Use only these section names, in this order. Each type has required sections; add optional ones only when they have content. Never leave an empty section.

| Section | Holds |
|---|---|
| `Purpose` | Why the file exists, in 1-3 sentences |
| `MUST` | Numbered rules that cannot be skipped |
| `ROUTES` | Where things are (table of paths) |
| `STEPS` | Ordered procedures |
| `DEFAULT` | Behavior that project rules may change |
| `EXAMPLES` | Concrete inputs and outputs |
| `IF UNSURE` | What to do when a case is not covered |
| `REFERENCES` | Other files, each with a fallback (S6) |

| Type | Required | Optional |
|---|---|---|
| `boundaries` | Purpose, MUST, IF UNSURE | - |
| `guide` | Purpose, IF UNSURE | ROUTES, STEPS, DEFAULT, EXAMPLES, REFERENCES |
| `procedure`, `skill` | Purpose, STEPS, IF UNSURE | MUST, DEFAULT, EXAMPLES, REFERENCES |
| `reference` | Purpose, MUST | any |
| `template` | Purpose | any |
| `script` | passport in docstring (S9) | - |

### S5. Writing for agents

1. Write in English. Russian goes only into display names (`.agents/docs/glossary.md`) and human documents.
2. Use the imperative: "Read", "Ask", "Never".
3. One rule per line or list item; aim for 25 words or fewer.
4. Put the most important rule first in every section.
5. Give every hard rule a stable id (`B4`, `S5`) so it can be quoted.
6. Write paths relative to the installation root, with forward slashes, in backticks: `projects/<name>/AGENTS.md`.
7. Use plain terms. No metaphors; terms not obvious to a model go to the glossary.
8. Add at least one example to every `procedure`, `skill`, and every non-obvious rule.
9. Never put history, editorial notes, or "changed for ..." remarks in working files. History lives in Git and in the source repository CHANGELOG.
10. Never link to external URLs from core files.

### S6. References

Every reference names the file and what to do if it is missing:

```text
See `.agents/docs/glossary.md` for terms. If missing: use the English keys as written and report it.
```

### S7. Names and paths

- Use kebab-case ASCII for every file and folder: `system-projects/chronicle/`, `2026-10-30-plan.md`, `docs/standard.md`.
- Exact rule (checked by `doctor`): an optional leading dot, then lowercase words of `a-z` and `0-9` joined by single hyphens, then optional extensions of the same form: `^\.?[a-z0-9]+(-[a-z0-9]+)*(\.[a-z0-9]+(-[a-z0-9]+)*)*$`.
- Exceptions:
  - names that clients or specifications require: `AGENTS.md`, `README.md`, `README.en.md`, `SKILL.md`, `LICENSE`, `VERSION`, and templates derived from them (`AGENTS.template.md`);
  - Python modules use snake_case, `^[a-z0-9_]+\.py$` (`init_project.py`, `__init__.py`), because Python cannot import names with hyphens.
- Brand names are for people (`S-A-Satellite`); ids are for files (`s-a-satellite`).
- Prefix dated documents with the date: `YYYY-MM-DD-<topic>.md`.
- Inside `projects/<name>/`, the owner's notes and documents may use any language and spaces. Scripts and configs there still follow this rule.

### S8. Generated files

- Files produced by `python sa.py sync` or `python sa.py init` start with a marker line instead of a passport:

```text
<!-- GENERATED by s-a-satellite from <source>. Do not edit. Edit the source, then run: python sa.py sync -->
```

- A file with an owner-editable part keeps the generated part between markers. `sync` replaces only the text between them:

```text
<!-- s-a:begin generated from <source> -->
...
<!-- s-a:end generated -->
```

- Templates carry a passport. The tool strips it when it creates a file from the template.
- Name a template after its target plus `.template`: `AGENTS.template.md` -> `AGENTS.md`, `gitignore.template` -> `.gitignore`. Never give a template the live file name; clients and Git would apply it where it lies.
- Placeholders that a person must fill are lines that start with `TODO:`.

### S9. Scripts

- Python 3.11+, standard library only, type hints.
- Scripts use their own field set instead of S2: `name`, `description`, `type: script`, `inputs`, `outputs`, `side_effects`, `destructive`, `requires_owner`, `version`, `origin`. They have no `audience`, `load`, or `scope`.
- For `.ps1` and `.sh`, write the same fields at the top as a comment block: every line starts with `# `, and the block opens and closes with `# ---`.
- Put the passport as the first lines of the module docstring:

```python
"""
---
name: s-a-commit
description: Commits explicit paths to the repository that owns them, adding executor trailers.
type: script
inputs: paths (one repository), -m message, --agent, --model, --core
outputs: commit hash on stdout; exit 0 ok, 1 refused, 2 git error
side_effects: git add and git commit in one repository
destructive: false
requires_owner: false
version: 0.2.0
origin: Soyuz-Apollo Framework | by Dmitrii Gradov | 2026-10
---
"""
```

- Open every text file with `encoding="utf-8"`.
- Use `pathlib`; never build paths by joining strings.
- Never use `shell=True`; pass arguments as a list.
- Print messages in English ASCII, so they survive any console code page.
- Return exit codes: 0 success, 1 refused or checks failed, 2 unexpected error.
- A script with `destructive: true` must ask for, or receive, an explicit owner confirmation flag.

### S10. Encoding and line endings

- Text files: UTF-8 without BOM, LF line endings, final newline.
- Exceptions: `.cmd` and `.bat` use CRLF.
- Writers, in order of preference: the harness file tools; Python with `encoding="utf-8"`; PowerShell 7 with `-Encoding utf8NoBOM`. Never write text files with Windows PowerShell 5.1 cmdlets: `-Encoding utf8` there adds a BOM (verified on 5.1.26100).
- Every repository (core, each project) contains the three files from S11.

### S11. Repository files

`.gitattributes`:

```text
* text=auto eol=lf
*.cmd text eol=crlf
*.bat text eol=crlf
```

`.editorconfig`:

```text
root = true

[*]
charset = utf-8
end_of_line = lf
insert_final_newline = true
trim_trailing_whitespace = true

[*.md]
trim_trailing_whitespace = false

[*.{cmd,bat}]
end_of_line = crlf
```

`.gitignore` for the core (`.agents/`):

```text
__pycache__/
*.pyc
config/instance.toml
```

`.gitignore` for a project:

```text
__pycache__/
*.pyc
.venv/
.env
.env.*
*.key
*.pem
tmp/
```

### S12. Size budgets

| File | Limit | `doctor` |
|---|---|---|
| Root `AGENTS.md` (generated) | 4 KB | WARN above |
| `.agents/AGENTS.md` | 6 KB | WARN above |
| Project `AGENTS.md` | 6 KB | WARN above |
| `SKILL.md` | 500 lines | WARN above |

### S13. Ownership and safe overwrite

- S-A changes a file, a link, or a setting automatically only when it can prove that S-A manages it. No proof means no automatic overwrite and no deletion.
- Four states:

| State | Proof | What `init` and `sync` may do |
|---|---|---|
| source | passport `origin: Soyuz-Apollo Framework ...` in a release file | nothing: `origin` is provenance, not write permission |
| generated | the GENERATED marker of S8 in the file; in JSON, where comments are impossible, the field `env.SA_ADAPTER` | create the file if it is absent; regenerate the whole file |
| mixed | the markers `s-a:begin` and `s-a:end` | replace only the text between the markers |
| owner | no proof | leave it unchanged and report the conflict |

- More proofs:
  - a link in `.claude/skills/` is managed only when its target is `.agents/skills/<same name>`; a link with any other target is owner content, even when it is broken;
  - a Git repository is managed only when its local `.git/config` has `soyuz-apollo.managed = true`, which `sa init` sets when it creates the repository. Only then does `sa` set its local Git keys. The first commit signed `Agent: s-a-satellite` is provenance, not proof.
- New outputs (backup and archive folders) are created as new folders only; an existing target is a refusal.
- Taking over an owner file is allowed only where a command documents it, and only on an explicit owner command. In 0.2 there are exactly two: `python sa.py sync --force` (the root `AGENTS.md` only) and `python sa.py init <name> --adopt` (marks an existing project repository as managed and sets its Git keys; changes no files). Agents never pass these flags on their own.
- Never merge foreign configuration files. Never keep a separate manifest for ownership.

## IF UNSURE

- A file does not fit any `type`: use `reference` and tell the owner.
- A rule here conflicts with a client or specification requirement: follow the client or specification for that file, and report the conflict.

## REFERENCES

- `.agents/docs/glossary.md` - terms and Russian display names. If missing: use English keys as written.
- `.agents/AGENTS.md` - operating manual. If missing: stop and tell the owner; the installation is damaged.
