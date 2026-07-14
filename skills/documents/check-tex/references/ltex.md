# Grammar checking for LaTeX with `ltex-cli`

`check-tex` handles style and terminology. For **grammar, agreement, and spelling** on
LaTeX, use [`ltex-ls`](https://github.com/valentjn/ltex-ls) (active fork:
[`ltex-ls-plus`](https://github.com/ltex-plus/ltex-ls-plus)) — LanguageTool wrapped in a
purpose-built LaTeX parser. It succeeds exactly where `@textlint-rule/gramma` crashes.

## Install

```sh
brew install ltex-ls            # macOS / Linuxbrew
```

Otherwise download a release from
<https://github.com/ltex-plus/ltex-ls-plus/releases> and put `ltex-cli` on `PATH`
(needs a JRE 17+).

## Run

```sh
ltex-cli paper.tex
```

```powershell
ltex-cli paper.tex
```

`ltex-cli` parses the LaTeX natively (commands, environments, and math are ignored) and
prints LanguageTool-style diagnostics. Supported inputs include LaTeX, Markdown, BibTeX,
ConTeXt, Org, reStructuredText, and R Sweave.

## Notes

- Output is human-readable LanguageTool text, **not** the merged JSON that
  [`check-tex.mjs`](../scripts/check-tex.mjs) emits — run it as a separate grammar pass and
  apply its findings by hand.
- It builds on a LanguageTool engine but bundles its own; you do **not** need the Docker
  server that the [`check-markdown`](../../check-markdown/references/languagetool.md) skill
  uses.
- Custom macros can still confuse the parser; add them to an `ltex` settings file if a
  command's argument is mis-read as prose.
