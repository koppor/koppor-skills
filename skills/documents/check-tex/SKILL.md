---
name: check-tex
description: Lint LaTeX prose with textlint's latex2e parser (terminology, wordiness, passive voice), then apply the findings as targeted edits. Use when the user wants to check, proofread, or improve a .tex file. For grammar, pairs with ltex-cli (LanguageTool for LaTeX).
license: MIT
---

# Check LaTeX prose

Lint the natural-language prose in `.tex` files, then **read the findings and apply them as
edits** — do not blindly auto-fix. The bundled runner
[`scripts/check-tex.mjs`](scripts/check-tex.mjs) drives textlint with the `latex2e` parser
and emits one merged JSON array.

## Why LaTeX is separate from Markdown

The [`check-markdown`](../check-markdown/SKILL.md) toolchain does not transfer to LaTeX:

- **Vale** has no LaTeX parser ([errata-ai/vale#54](https://github.com/errata-ai/vale/issues/54)) —
  it would flag markup as prose.
- **`@textlint-rule/gramma`** (the LanguageTool bridge) *crashes* on the latex2e AST.

So this skill checks **style and terminology** through `textlint-plugin-latex2e`, which
parses the LaTeX AST and lints only prose nodes — commands, environments, and math are
ignored. For **grammar**, use `ltex-cli` (LanguageTool with a native LaTeX parser):
[references/ltex.md](references/ltex.md).

## Setup

- **Node.js ≥ 18**. The runner runs `npm install` in `assets/` automatically on first use;
  to do it ahead of time: `npm install --prefix skills/documents/check-tex/assets`.

That is the only prerequisite — no Vale, no Docker.

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

Exit code: `0` clean, `1` findings, `2` setup/tool failure. Severity is normalized:
`write-good` and `terminology` report as `warning` (style / judgment call).

**Caveat:** comments inside math environments are not parsed into the AST, so text hidden
there is not checked. Regular prose paragraphs are fine.

## Act on the findings

Read the JSON and triage — same philosophy as `check-markdown`:

- **`warning` → judgment call.** `write-good` (passive voice, weasel words, wordiness) and
  `terminology`. Rewrite only when it genuinely improves the sentence and preserves the
  author's meaning and voice. Academic prose may keep passive voice on purpose.
- **False positives → skip.** Macro names, labels, citation keys, and jargon the latex2e
  parser exposed as prose.

Apply edits to the source `.tex` with the Edit tool, then **re-run** and confirm the count
dropped. For grammar/agreement/spelling, run `ltex-cli` separately
([references/ltex.md](references/ltex.md)) and apply those too.

## Customize

Edit [`assets/textlintrc.json`](assets/textlintrc.json) to add rules; add packages to
[`assets/package.json`](assets/package.json) and re-run `npm install`.
