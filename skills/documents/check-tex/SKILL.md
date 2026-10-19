---
name: check-tex
description: Lint LaTeX prose with TeXtidote (spelling, grammar via LanguageTool, LaTeX style), textlint's latex2e parser (terminology, wordiness, passive voice), and typos (misspellings, also in comments), then apply the findings as targeted edits. Use when the user wants to check, proofread, or improve a .tex file.
license: MIT
---

# Check LaTeX prose

Lint the natural-language prose in `.tex` files, then **read the findings and apply them as
edits** — do not blindly auto-fix. The bundled runner
[`scripts/check-tex.mjs`](scripts/check-tex.mjs) drives three tools and emits one merged
JSON array:

| Tool | Catches |
| --- | --- |
| [TeXtidote](https://github.com/sylvainhalle/textidote) | Spelling and grammar (LanguageTool on the LaTeX source), LaTeX style (`sh:` rules) |
| [textlint](https://textlint.org) (`latex2e`) | Terminology, wordiness, passive voice (write-good) |
| [typos](https://github.com/crate-ci/typos) | Common misspellings, also in comments, which TeXtidote skips (English only) |

## Why LaTeX is separate from Markdown

The [`check-markdown`](../check-markdown/SKILL.md) toolchain does not transfer to LaTeX:

- **Vale** has no LaTeX parser ([errata-ai/vale#54](https://github.com/errata-ai/vale/issues/54)) —
  it would flag markup as prose.
- **`@textlint-rule/gramma`** (the LanguageTool bridge) *crashes* on the latex2e AST.

So this skill checks **style and terminology** through `textlint-plugin-latex2e`, which
parses the LaTeX AST and lints only prose nodes — commands, environments, and math are
ignored — and **spelling and grammar** through TeXtidote, which removes the markup itself
and maps the findings back to the source lines. An alternative for grammar is `ltex-cli`
(LanguageTool with a native LaTeX parser): [references/ltex.md](references/ltex.md).

## Setup

- **Node.js ≥ 18**. The runner runs `npm install` in `assets/` automatically on first use;
  to do it ahead of time: `npm install --prefix skills/documents/check-tex/assets`.
- **TeXtidote** — spelling and grammar. Optional: taken from `PATH`, else run in the
  [`danteev/texlive`](https://hub.docker.com/r/danteev/texlive) Docker image (large; pick
  another tag with `TEXTIDOTE_IMAGE`, e.g. `danteev/texlive:2026-C`); without either,
  TeXtidote is skipped.
  - A `.textidote` file in the file's directory or an ancestor (up to the repository root)
    is used: the runner starts TeXtidote there, so the repository's options (`--check`,
    `--dict`, `--replace`, `--remove-macros`, …) apply.
  - Without `.textidote`, the language comes from `CHECK_TEX_LANG`, else from
    `% !TeX spellcheck = <lang>` in the file, else English.
  - Files without `\begin{document}` (chapters pulled in by `\include`) are checked with
    `--read-all`.
- **typos** — common misspellings, also in code spans and comments. Optional: taken from
  `PATH`, else run through `pipx run typos` or `uvx typos`; without any of them, typos is
  skipped. It knows English only; a repository's `.typos.toml` (excluded files, allowed
  words) applies, also to files named on the command line.
  - Windows/macOS/Linux: `pipx install typos` (or `cargo install typos-cli`)
  - macOS: `brew install typos-cli`

## Run

```sh
node skills/documents/check-tex/scripts/check-tex.mjs path/to/paper.tex
```

```powershell
node skills/documents/check-tex/scripts/check-tex.mjs path\to\paper.tex
```

Findings print as JSON to **stdout**, a summary to **stderr**. Each finding:

```json
{
  "file": "paper.tex",
  "line": 4,
  "column": 17,
  "severity": "warning",
  "source": "textlint",
  "rule": "write-good",
  "message": "\"clearly\" is a weasel word and can weaken meaning",
  "fixable": false
}
```

`source` is `textlint`, `textidote`, or `typos`. Exit code: `0` clean, `1` findings,
`2` setup/tool failure. Severity is normalized: TeXtidote's spelling and grammar rules
(LanguageTool categories `TYPOS` and `GRAMMAR`) and typos report as `error`; `write-good`,
`terminology`, TeXtidote's `sh:` rules, and other LanguageTool rules as `warning` (style /
judgment call).

**Caveats:**

- Comments inside math environments are not parsed into the AST, so text hidden there is
  not checked. Regular prose paragraphs are fine.
- A single unbalanced `$` — e.g., `replace=\regexp{$1}` in a biblatex source map — makes
  textlint's parser fail on the whole file: one finding `Failed to parse text by plugin:
  latex2e` at line 1 and nothing else. Rewrite that code without `$`.

## Act on the findings

Read the JSON and triage — same philosophy as `check-markdown`:

- **`error` → apply.** Spelling and grammar from TeXtidote, misspellings from typos — but
  check proper nouns, macro names, and non-English text (typos knows English only); add
  real words to the repository's word list (`.textidote` `--dict`, `.typos.toml`).
- **`warning` → judgment call.** `write-good` (passive voice, weasel words, wordiness) and
  `terminology`. Rewrite only when it genuinely improves the sentence and preserves the
  author's meaning and voice. Academic prose may keep passive voice on purpose.
- **False positives → skip.** Macro names, labels, citation keys, and jargon the latex2e
  parser exposed as prose.

Apply edits to the source `.tex` with the Edit tool, then **re-run** and confirm the count
dropped.

## Customize

Edit [`assets/textlintrc.json`](assets/textlintrc.json) to add rules; add packages to
[`assets/package.json`](assets/package.json) and re-run `npm install`.
