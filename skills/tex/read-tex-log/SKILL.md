---
name: read-tex-log
description: >-
  Read LaTeX compiler logs (.log) with texlogsieve: filter the noise, unwrap
  79-column lines, and summarize errors, overfull/underfull boxes, undefined
  references and citations, and rerun requests. Use when a LaTeX build
  (pdflatex, lualatex, xelatex, latexmk) fails or warns and the .log must be
  read, instead of paging through the raw log.
license: MIT
---

# Read LaTeX logs with texlogsieve

[`texlogsieve`](https://ctan.org/pkg/texlogsieve) turns a raw TeX `.log` into a short
report: messages grouped per page and source file, wrapped lines rejoined, and a final
summary of boxes, undefined references/citations, and rerun requests. It ships with TeX
Live (a Lua script, `/usr/bin/texlogsieve` in the `texlive/texlive` image) — nothing to
install. Compile first (see [`compile-tex`](../compile-tex/SKILL.md)), then sieve.

## Run

Always pass `--no-heartbeat --no-color`: the default progress spinner (`/-\|`) and ANSI
colors pollute captured output.

```sh
docker run --rm -v "${PWD}:/workdir" texlive/texlive:latest \
  texlogsieve --no-heartbeat --no-color foo.log
```

```powershell
docker run --rm -v "${PWD}:/workdir" texlive/texlive:latest `
  texlogsieve --no-heartbeat --no-color foo.log
```

With a host TeX Live, drop the `docker run …` prefix. It also reads stdin:
`lualatex -interaction=nonstopmode foo.tex | texlogsieve --no-heartbeat --no-color`.

## Reading the output

- `pg N:` prefixes a message with the page it occurred on; `From file ./x.tex:` banners
  name the source file. An error keeps its `l.<n>` line reference.
- `====  Summary:  ====` lists under/overfull boxes (with offending text), undefined
  citations and references (key, page, file, line).
- `** LaTeX says you should rerun **` — not an error; rerun (or use `latexmk`).
- `** There were errors during processing! Generated PDF is probably defective **` —
  the build failed. **The exit code is 0 regardless**; detect failure from this line (or
  the compiler's exit code), not from `texlogsieve`'s.

## Useful options

| Option | Effect |
| --- | --- |
| `--minlevel=WARNING` / `-l CRITICAL` | Hide messages below that severity (`DEBUG`, `INFO`, `WARNING`, `CRITICAL`, `UNKNOWN`). `CRITICAL` ≈ errors only. |
| `--no-summary` / `--only-summary` | Drop the summary / show only the summary. |
| `--no-summary-detail` | Shorter summary: omit full box, ref, and citation details. |
| `--silence-package=PKG`, `--silence-string=TEXT`, `--silence-file=FILE` | Suppress known noise; repeatable. |
| `--no-tips` | Hide texlogsieve's own fix suggestions (TeX's help text after an error stays). |
| `-u`, `--unwrap-only` | No filtering at all; just rejoin the 79-column wrapped lines. |

The full option list is in [`references/options.md`](references/options.md).

Persistent options go into a `texlogsieverc` file (one long option per line, without
`--`) anywhere in the TeX path, e.g. next to the document.

## Workflow

1. Run with `--minlevel=CRITICAL --no-summary` — fix errors first, starting with the
   **first** one; later errors are often consequences. A stray lower-level line adjacent
   to an error may still show up.
2. Rerun with the defaults to handle warnings and the summary (undefined refs, boxes).
3. Report the relevant excerpt (message, file, `l.<n>`), not the whole report.
