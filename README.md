# koppor-skills

A curated collection of [Claude Code](https://claude.com/claude-code) **skills** for
document, TeX, JabRef, and research workflows. Skills are grouped into categories under
`skills/<category>/<skill>/` and each is a self-contained `SKILL.md` (plus optional
scripts, assets, and references). The primary audience is the author, but every skill is
written to be agent-agnostic and reusable by anyone.

## Categories

| Category | Skill | What it does |
| --- | --- | --- |
| `documents` | [`prose-check-markdown`](skills/documents/prose-check-markdown/SKILL.md) | Check Markdown prose with **Vale**, **textlint**, **LanguageTool**, **typos**, **aspell**, and **markdownlint**, then report the findings or apply them as targeted edits. |
| `documents` | [`prose-check-tex`](skills/documents/prose-check-tex/SKILL.md) | Check LaTeX prose with **TeXtidote**, **textlint** (latex2e), **typos**, and **aspell**, then report the findings or apply them as targeted edits. |
| `documents` | [`prose-checks-ci`](skills/documents/prose-checks-ci/SKILL.md) | Set up spell checking and prose linting of LaTeX and Markdown in **GitHub Actions** with **aspell**, **TeXtidote**, **textlint**, **Vale**, **typos**, and **markdownlint**. |
| `tex` | [`compile-tex`](skills/tex/compile-tex/SKILL.md) | Compile LaTeX / plain TeX / ConTeXt to PDF via the `texlive/texlive` Docker image, with `danteev/texlive` as the fallback for PlantUML, Mermaid, Inkscape, and other non-TeX-Live tools. |
| `tex` | [`read-tex-log`](skills/tex/read-tex-log/SKILL.md) | Summarize LaTeX `.log` files (errors, boxes, undefined refs/cites) with **texlogsieve**. |
| `tools` | [`run-with-gg`](skills/tools/run-with-gg/SKILL.md) | Run Java, Node.js, Gradle, or any GitHub release binary without installing it, with **gg.cmd**. |
| `jabref` | _(planned)_ | BibTeX/biblatex management, `jabkit`, PDF → BibTeX. |
| `research` | _(planned)_ | Literature and research-workflow helpers. |

## Install

These are plain skill folders — use whichever fits your setup:

- **Copy into Claude Code** — drop a skill directory into `~/.claude/skills/`, e.g.
  `~/.claude/skills/prose-check-markdown/`. Claude discovers it on the next session.
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

The standalone [`claude-tex-skills`](https://github.com/koppor/claude-tex-skills) plugin
marketplace (`koppor-tex-skills`) is archived. Its `compile-tex` skill lives here under
`skills/tex/` and is no longer mirrored — this repo is the only maintained copy.

## License

[MIT](LICENSE).
