---
name: check-markdown
description: Lint Markdown prose with Vale, textlint, and LanguageTool, then apply the findings as targeted text improvements. Use when the user wants to check, proofread, or improve a .md file — grammar, style, terminology, passive voice, spelling, or readability.
license: MIT
---

# Check Markdown prose

Lint natural-language prose in `.md` files with three complementary tools, then **read the
findings and apply them as edits** — do not blindly auto-fix.

| Tool | Catches |
| --- | --- |
| [Vale](https://vale.sh) | House-style, wordiness, readability, spelling (write-good, proselint, Vale.Spelling) |
| [textlint](https://textlint.org) | Terminology, weak wording (write-good) |
| [LanguageTool](https://languagetool.org) | Grammar, agreement, real-word errors |

LanguageTool runs *inside* the textlint pass (rule `@textlint-rule/gramma`), so it is
markup-aware and its hits arrive in the same JSON. The bundled runner
[`scripts/check-md.mjs`](scripts/check-md.mjs) drives all three and emits one merged JSON
array — that unified output is what you act on.

> **LaTeX?** Use the sibling [`check-tex`](../check-tex/SKILL.md) skill. Vale cannot parse
> LaTeX and the grammar rule crashes on the LaTeX AST, so `.tex` needs a different setup.

## Setup

Prerequisites:

- **Node.js ≥ 18** (uses built-in `fetch`). The runner runs `npm install` in `assets/`
  automatically on first use; to do it ahead of time:
  `npm install --prefix skills/documents/check-markdown/assets`.
- **Vale** on `PATH` — style, readability, spelling. Optional: without it, Markdown is
  checked with textlint only.
  - Windows: `winget install errata-ai.Vale` (or `choco install vale`)
  - macOS: `brew install vale`
  - Linux/other: download from <https://github.com/errata-ai/vale/releases>
- **LanguageTool** — grammar. On by default; the runner auto-starts the
  `erikvl87/languagetool` Docker image if Docker is present, else falls back gracefully.
  Details and alternatives (local `.jar`): [languagetool.md](references/languagetool.md).

Vale styles download automatically on first run (`vale sync`).

## Run

Point the runner at a file or directory. Merged findings print as JSON to **stdout**; a
summary prints to **stderr**.

```sh
node skills/documents/check-markdown/scripts/check-md.mjs path/to/file.md
```

```powershell
node skills/documents/check-markdown/scripts/check-md.mjs path\to\file.md
```

Each finding:

```json
{
  "file": "path/to/file.md",
  "line": 12,
  "column": 5,
  "severity": "error",
  "source": "languagetool",
  "rule": "@textlint-rule/gramma",
  "message": "Possible agreement error: ‘they was’ → ‘they were’.",
  "fixable": false
}
```

`source` is `textlint`, `vale`, or `languagetool`. Exit code: `0` clean, `1` findings,
`2` setup/tool failure.

**Severity is normalized so it means something:**

| `severity` | Meaning | Comes from |
| --- | --- | --- |
| `error` | Very likely wrong — fix it | LanguageTool grammar, `Vale.Spelling` |
| `warning` | Style / wordiness — judgment call | `write-good`, `terminology`, most proselint |
| `suggestion` | Readability signal — usually informational | Readability metrics |

Override the LanguageTool endpoint with `LANGUAGETOOL_URL` (default
`http://localhost:8081/v2/check`). Pointing it at a **remote** host sends document text
there; the runner warns when you do.

## Act on the findings

This is the point of the skill: **you** decide what each finding is worth. Read the JSON
and triage by severity and kind, not by blindly applying every suggestion.

- **`error` → apply.** Grammar/agreement from LanguageTool, spelling from `Vale.Spelling`.
  Fix these in the source with the Edit tool.
- **`warning` → judgment call.** `write-good` (passive voice, weasel words, "so"/"just"),
  `terminology`, proselint. Rewrite for clarity **only when it genuinely improves the
  sentence and preserves meaning and the author's voice**. Prose in a specific register
  (academic, legal) may keep passive voice on purpose.
- **`suggestion` / false positives → usually skip.** Readability metrics, and any hit on
  proper nouns, code identifiers, citation keys, deliberate jargon, or quoted text.

Apply edits to the *source* file with the Edit tool — read the flagged line, fix it in
context. Prefer targeted edits over `textlint --fix`; only reach for `--fix` on clearly
safe, `"fixable": true` rules and review the diff. After editing, **re-run the runner** and
confirm the count dropped. Report a short summary of what you changed and what you
deliberately left.

## Customize

- **textlint rules** — edit [`assets/textlintrc.json`](assets/textlintrc.json); add
  packages to [`assets/package.json`](assets/package.json) and re-run `npm install`.
- **Vale styles/severity** — edit [`assets/vale.ini`](assets/vale.ini)
  (`Packages`, `BasedOnStyles`, `MinAlertLevel`), then `vale sync`.
- A repo can carry its own `.textlintrc`/`.vale.ini`; point the tools at those to honor
  project conventions.
