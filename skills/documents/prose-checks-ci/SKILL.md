---
name: prose-checks-ci
description: Set up spell checking and prose linting for LaTeX and Markdown in GitHub Actions CI with aspell, TeXtidote, textlint (latex2e), Vale, typos, and markdownlint, including the DANTE e.V. TeX Live Docker image, word lists, PR annotations, and the pitfalls of each tool. Use when adding or debugging spell check, grammar, or style checks of .tex or .md files in a CI workflow.
license: MIT
---

# Prose checks in GitHub Actions CI

This skill sets up and debugs **CI checks of the prose** in LaTeX and Markdown
repositories. For checking a single file locally and editing it, use the sibling skills
[`prose-check-tex`](../prose-check-tex/SKILL.md) (TeXtidote, textlint, typos, aspell) and
[`prose-check-markdown`](../prose-check-markdown/SKILL.md) (Vale, textlint, LanguageTool, typos,
aspell, markdownlint); they use a repository's `.textidote`, `.typos.toml`, `.aspell.conf`,
`.aspell.<lang>.pws`, and `.markdownlint*`, so local and CI results match.

The knowledge comes from the CI of the
[latextemplates](https://github.com/latextemplates) (theses and papers, English and
German, `.tex` plus Markdown chapters).

## Which tool for what

| Tool | Checks | LaTeX | Markdown | Languages | Fails CI? |
| --- | --- | --- | --- | --- | --- |
| [aspell](http://aspell.net) | spelling | `--mode=tex` | `--mode=markdown` | dictionary per language (en, de, …) | yes, on chosen files |
| [TeXtidote](https://github.com/sylvainhalle/textidote) | spelling, grammar (LanguageTool), LaTeX style | yes | yes (`.md`) | en, de, … | usually report only |
| [textlint](https://textlint.org) | terminology, passive voice, wordiness | `textlint-plugin-latex2e` | yes | English rules | report only (annotations) |
| [Vale](https://vale.sh) | house style, readability | **no** LaTeX parser ([vale#54](https://github.com/errata-ai/vale/issues/54)) | yes | English styles | your choice; PR review comments via reviewdog |
| [typos](https://github.com/crate-ci/typos) | known misspellings, also in comments and code | yes (as text) | yes | **English only** | yes |
| [markdownlint](https://github.com/DavidAnson/markdownlint) | Markdown structure | — | yes | — | yes |

aspell and TeXtidote skip LaTeX comments; **typos does not**, so it finds the typos in
preamble comments that the other tools never see (`enviornment`, `paramters`, …).

## Runtime: the DANTE e.V. image

[`danteev/texlive`](https://hub.docker.com/r/danteev/texlive) ships TeX Live plus
`aspell` with English and German dictionaries and `textidote` on the `PATH`, so a job needs
no `apt-get` and no `textidote.jar` download. Pin a tag (e.g. `2026-C`); `edge` is the
moving one. The linters do not depend on the TeX Live year.

```yaml
  spell-check:
    runs-on: ubuntu-latest
    container: danteev/texlive:2026-C
    defaults:
      run:
        shell: bash   # container jobs run steps with sh by default: [[ ]] and arrays fail
```

Without `defaults: run: shell: bash`, a container job fails with
`Syntax error: word unexpected (expecting "then")`.

Run the same image locally (files belong to you, `HOME` is writable):

```sh
docker run --rm -u "$(id -u):$(id -g)" -e HOME=/tmp -v "$PWD:/w" -w /w danteev/texlive:2026-C \
  aspell --mode=tex -l en_US --conf=./.aspell.conf -p ./.aspell.en.pws list < paper.tex
```

```powershell
Get-Content paper.tex | docker run --rm -i -v "${PWD}:/w" -w /w danteev/texlive:2026-C `
  aspell --mode=tex -l en_US --conf=./.aspell.conf -p ./.aspell.en.pws list
```

## aspell

- `aspell list` prints the unknown words; collect them per file and fail when a file of
  the document's language has any. Write a table to `$GITHUB_STEP_SUMMARY`.
- **Language per file**: choose the dictionary from the file name, e.g. `*-de.tex`,
  `*.de.md`, `chapters-de/*` → `-l de_DE --run-together` (German compounds), else
  `-l en_US`, each with its own word list `-p ./.aspell.<lang>.pws`.
- **Word list format**: first line `personal_ws-1.1 en <count> utf-8`, then one word per
  line. aspell word lists cannot contain hyphenated words.
- **`.aspell.conf`** tells the TeX filter which arguments to skip: `add-tex-command
  <name> <args>` with `p` = skip, `P` = check, `o`/`O` = optional argument. Examples:
  `add-tex-command zcref op`, `add-tex-command setupRefEnum opp`, `add-tex-command
  defRQ Pp` (check the title, skip the label).
- **`@` splits macro names**: in `\makeatletter` code, `\FV@StepLineNo` or
  `\protected@edef` become the "words" `StepLineNo`, `edef`. Add them to the word list.
- **Nested braces in a skipped argument are checked**: `\zcsetup{countertype={FancyVerbLine=line}}`
  reports `FancyVerbLine` although `zcsetup` is `p`. Add the word to the word list.
- **Markdown with LaTeX in it**: aspell's Markdown mode does not know `\LaTeX{}`,
  `<#sec:x>`, or `{#sec:x}`. Strip them first:

  ```sh
  sed -E 's/\\[A-Za-z]+//g; s/<#[^>]*>//g; s/\{#[^}]*\}//g' chapter.md \
    | aspell --mode=markdown -l en_US --encoding=utf-8 --conf=./.aspell.conf -p ./.aspell.en.pws list
  ```

  ```powershell
  (Get-Content chapter.md -Raw) -replace '\\[A-Za-z]+','' -replace '<#[^>]*>','' -replace '\{#[^}]*\}','' |
    aspell --mode=markdown -l en_US --encoding=utf-8 --conf=./.aspell.conf -p ./.aspell.en.pws list
  ```

## TeXtidote

- Options in a `.textidote` file in the repository root; run
  `textidote --output singleline --no-color main.tex` for CI logs, `--output html` for a
  report to upload as artifact.
- Drop what is not prose: `--remove listing,minted,lstlisting,verbatim,tikzpicture,equation,align,tabular,…`
  (environments) and `--remove-macros include,input,label,includegraphics,…` (macros
  with their arguments).
- Files pulled in by `\include` mix up its text positions: remove the `\include` macros
  (as above) and check each chapter on its own with `--read-all chapter.tex`. TeXtidote
  checks only the text between `\begin{document}` and `\end{document}` unless
  `--read-all` is given, and chapter files have no `\begin{document}`.
- Feed the aspell word lists into TeXtidote's dictionary (`--dict`), generated from the
  `.pws` files without their header line, plus hyphenated words aspell cannot hold.
- **Replacements file** (`--replace`): one `regex<TAB>replacement` per line, applied
  before checking. Turn macros into plain words so sentences stay sentences, e.g.
  `\\[Zz]cref(\[[^]]*\])?\{[^}]*\}<TAB>Section 1`, `\\refRQ\{[^}]*\}<TAB>RQ1`. For `^`
  and `$` to match per line, write `(?m)`: `(?m)^: <TAB>` (a Markdown table caption).
- **Heading and structure checks (`sh:` rules) run on the raw source**, so neither
  replacements nor `--remove-macros` silence them. Wrap such code in
  `% textidote: ignore begin` … `% textidote: ignore end`.

## textlint

```sh
npx --yes --package textlint --package textlint-plugin-latex2e \
  --package textlint-filter-rule-allowlist --package textlint-rule-terminology \
  --package textlint-rule-write-good textlint --format github paper.tex chapter.md
```

```powershell
npx --yes --package textlint --package textlint-plugin-latex2e `
  --package textlint-filter-rule-allowlist --package textlint-rule-terminology `
  --package textlint-rule-write-good textlint --format github paper.tex chapter.md
```

- `--format github` turns findings into PR annotations. **Annotations of level
  `failure` mark the file with a red ✗ in the PR's file tree even if the job is green**
  (e.g. `|| true`); users then ask what is wrong. Look them up with
  `gh api repos/<o>/<r>/check-runs/<id>/annotations`.
- **One unbalanced `$` breaks the whole file**: the latex2e parser reports
  `Failed to parse text by plugin: latex2e` at line 1 and checks nothing in that file. A
  classic source is a biblatex source map with `replace=\regexp{$1}`; rewrite it without
  back-references (two `\step`s that delete with `replace={}`). Find the line by
  bisecting with `latex-utensils` (`latexParser.parse`) — but prefixes of a file with an
  open brace fail too, so remove blocks rather than truncating.
- `terminology` wants "Markdown", "API", …: write package names as code
  (`` `markdown` package ``) or add a pattern to `filters.allowlist.allow`.
- `write-good` flags passive voice ("is written", "is referenced"); rephrase in example
  texts, accept it in academic prose.

## Vale

```yaml
permissions:
  contents: read
  pull-requests: write   # github-pr-review posts review comments
  checks: write          # github-check / github-pr-check write a check run
jobs:
  vale:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
      - uses: vale-cli/vale-action@v3.0.0
        with:
          files: all
          # On a PR: review comments (with suggested fixes) on changed lines,
          # check annotations for the rest. On push there is no PR to review.
          reporter: ${{ github.event_name == 'pull_request' && 'github-pr-review' || 'github-check' }}
          filter_mode: nofilter
          fail_on_error: false
```

- **Findings as PR comments need `reporter: github-pr-review`** (the action's default
  `github-pr-check` only writes a check run). reviewdog can comment only on lines inside the
  diff; with `filter_mode: nofilter` the findings outside the diff fall back to check
  annotations, so the whole file is still checked. Example:
  [JabRef/user-documentation `lint.yaml`](https://github.com/JabRef/user-documentation/blob/db7796b0270d1cf0c3dd4c1617393989c2f0d55b/.github/workflows/lint.yaml#L51).
- `github-pr-review` on a `push` event has no PR and fails the step (JabRef wraps it in
  `continue-on-error: true`); the `reporter:` expression above avoids that.
- A PR from a fork runs with a read-only token: no review comments, no check runs.
  Only the default `github-pr-annotations` reporter (workflow-command annotations
  through the log) works there.
- `fail_on_error: false` keeps the job green; rules in `.vale.ini`, accepted words in
  `.vale/styles/config/vocabularies/<Vocab>/accept.txt`.

## typos

```yaml
      - uses: crate-ci/typos@7f9d0819ca1c008ade73f4b41fa9d258d48f605b # v1.51.1 (SHA-pinned)
```

```sh
typos --format brief .
```

```powershell
typos --format brief .
```

- **English only**: in German text, `ist`, `oder`, `ein`, `Ende`, `als` are "typos".
  Exclude German files, and expect German comments in English files to show up too.
- Configure `.typos.toml` (typos also reads `typos.toml` and `_typos.toml`, but no YAML;
  the hidden name matches `.textidote` and `.markdownlint.yml`): `[files] extend-exclude` for German files, `*.bib`, `*.bst`,
  vendored `*.cls`/`*.sty`, word lists, and submodules; `[default.extend-words]` for
  names such as `Heros` (TeX Gyre Heros). `2\textsuperscript{nd}` reports `nd`.
- It finds what the others miss: misspellings in comments and code identifiers, and
  German leftovers in English files (`\floatname{algorithm}{Algorithmus}` in an English
  document).

## markdownlint

- Configure `.markdownlint.yml` and recommend the VS Code extension
  `davidanson.vscode-markdownlint` in `.vscode/extensions.json`.
- When link reference definitions are generated conditionally (templates), turn off
  `MD053` (unused link definitions).
- Fenced code blocks inside list items must be indented to the list item's content.

## Debugging checklist

1. Reproduce in the same image locally (commands above) before changing the workflow.
2. A finding in macro code → `.aspell.conf` (`add-tex-command`) or the word list; a
   finding in a sentence → fix the text.
3. A red ✗ on a file with a green job → textlint annotations.
4. A file with zero textlint findings that should have some → check for
   `Failed to parse text by plugin` (unbalanced `$`).
5. TeXtidote heading findings that replacements do not silence → ignore markers.
