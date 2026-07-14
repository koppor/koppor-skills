# koppor-skills

A curated collection of [Claude Code](https://claude.com/claude-code) **skills** for
document, TeX, JabRef, and research workflows. Skills are grouped into categories under
`skills/<category>/<skill>/` and each is a self-contained `SKILL.md` (plus optional
scripts, assets, and references). The primary audience is the author, but every skill is
written to be agent-agnostic and reusable by anyone.

## Categories

| Category | Skill | What it does |
| --- | --- | --- |
| `documents` | [`check-markdown`](skills/documents/check-markdown/SKILL.md) | Lint Markdown prose with **Vale**, **textlint**, and **LanguageTool**, then apply the findings as targeted edits. |
| `documents` | [`check-tex`](skills/documents/check-tex/SKILL.md) | Lint LaTeX prose with **textlint** (latex2e); pairs with **ltex-cli** for grammar. |
| `tex` | [`compile-tex`](skills/tex/compile-tex/SKILL.md) | Compile LaTeX / plain TeX / ConTeXt to PDF via the `texlive/texlive` Docker image. |
| `jabref` | _(planned)_ | BibTeX/biblatex management, `jabkit`, PDF → BibTeX. |
| `research` | _(planned)_ | Literature and research-workflow helpers. |

## Install

These are plain skill folders — use whichever fits your setup:

- **Copy into Claude Code** — drop a skill directory into `~/.claude/skills/`, e.g.
  `~/.claude/skills/check-markdown/`. Claude discovers it on the next session.
- **skills CLI** — install the whole repo and let telemetry index it:

  ```sh
  npx skills add koppor/koppor-skills
  ```

- **Clone** and reference the scripts directly (see each `SKILL.md` for exact commands).

Per-skill prerequisites (Node, Vale, Docker, JBang, …) are listed in the skill's own
`SKILL.md`.

## Listed on skills.sh

This repo is indexed by [skills.sh](https://www.skills.sh). The directory has no submit
form — it picks up public repos installed through the skills CLI. To (re)seed the index,
run `npx skills add koppor/koppor-skills` with telemetry enabled, then search, e.g.
[skills.sh/?q=vale](https://www.skills.sh/?q=vale).

## Repository layout

```
skills/
  <category>/
    <skill-name>/
      SKILL.md            # required: the skill (YAML frontmatter + Markdown body)
      scripts/            # optional: runnable helpers referenced from SKILL.md
      assets/             # optional: bundled configs / templates
      references/         # optional: deep-dive docs loaded on demand
README.md   LICENSE   CONTRIBUTING.md
```

## Contributing / authoring skills

Conventions for adding a skill or category are in [CONTRIBUTING.md](CONTRIBUTING.md).

## Relationship to `koppor-tex-skills`

The standalone `koppor-tex-skills` plugin marketplace is being folded into this repo; its
`compile-tex` skill now lives here under `skills/tex/`. That marketplace is deprecated —
prefer this repo going forward.

## License

[MIT](LICENSE).
