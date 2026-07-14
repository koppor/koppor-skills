# Authoring skills for koppor-skills

This repo is a **catalog of Claude Code skills**. A skill is a folder with a `SKILL.md`
that any documentation-consuming agent can read. This guide is the blueprint every skill
here follows so the collection stays consistent and stays discoverable on
[skills.sh](https://www.skills.sh).

## Layout

```
skills/<category>/<skill-name>/SKILL.md
```

- **Category** — a topic folder directly under `skills/`. Current: `documents`, `tex`,
  `jabref` (planned), `research` (planned). Add a new one by creating the folder and
  listing it in [README.md](README.md).
- **Skill name** — kebab-case. The folder name **must equal** the `name:` in the
  frontmatter.
- Optional siblings of `SKILL.md`:
  - `scripts/` — runnable helpers (Node/POSIX/PowerShell). Referenced from `SKILL.md` by
    relative path.
  - `assets/` — bundled configs, templates, pinned dependency manifests.
  - `references/` — deep-dive docs the agent loads only when needed (keeps `SKILL.md`
    lean).

## Frontmatter

```yaml
---
name: <kebab-case, equals the folder name>
description: <what it does>. Use when <trigger conditions>.
license: MIT
---
```

- **`name`** (required) — unique, kebab-case.
- **`description`** (required) — one line. Formula: **"`<what it does>`. Use when
  `<trigger>`."** Front-load the concrete nouns a user would search for — tool names,
  file types, verbs. This text is what skills.sh indexes (see below).
- **`license`** — `MIT` for skills in this repo.

## The body

Plain Markdown after the frontmatter:

- Start with an `# H1` title, then task-focused sections (`## Setup`, `## Run`, …).
- Be precise and command-accurate. Prefer the "bits an agent gets wrong" over restating
  the obvious — assume the reader knows the basics of the underlying tool.
- Give **both** POSIX `sh` and **PowerShell** command blocks for anything a user runs;
  contributors and users here are on Windows and Unix.
- Use tables for tool/option matrices. Show real, copy-pasteable commands.
- Reference bundled files by relative path, e.g.
  [`scripts/check-md.mjs`](skills/documents/check-markdown/scripts/check-md.mjs).
- Keep secrets and machine-specific paths out; make scripts resolve their own location.

## Scripts

- Cross-platform first: a Node script (`.mjs`) or one that resolves paths relative to
  itself runs everywhere. Avoid hard-coding separators or drive letters.
- Fail soft: when an optional tool is missing, warn and continue rather than aborting the
  whole run.
- Emit machine-readable output (JSON) when the intent is for the agent to act on results.

## Discoverability on skills.sh

skills.sh indexes public GitHub repos that users install via the skills CLI
(`npx skills add <owner>/<repo>`); there is no manual submission. Its search matches a
skill's **`name`**, **`description`**, and the **`owner/repo`** slug — not the README body
or GitHub topics. So put the words people will search (tool names like *Vale*,
*LanguageTool*, file types, key verbs) into the `description`.

## Before opening a PR

- Folder name == `name`; frontmatter has `name` + `description`.
- Every runnable command shown for both `sh` and PowerShell.
- Scripts run from a clean checkout (document any `npm install` / prerequisites).
- New category added to the README table.
