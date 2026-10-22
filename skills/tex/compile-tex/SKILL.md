---
name: compile-tex
description: >-
  Compile LaTeX, plain TeX, and ConTeXt documents to PDF using the
  texlive/texlive Docker image. Agent-agnostic notes on the bits a fresh
  agent gets wrong without the doc: working directory, scheme and
  -doc/-src semantics, the latest tag's weekly rebuild, the non-root
  texlive user, the latexmk and arara wrappers, LuaLaTeX as the
  modern default engine, and the danteev/texlive image as the fallback
  when a document needs tools beyond TeX Live (PlantUML, Mermaid,
  Inkscape, Gnuplot, Graphviz, TikZ-UML, Pandoc, ...).
license: MIT
---

# Compile TeX documents with the texlive/texlive Docker image

Build LaTeX, plain TeX, and ConTeXt documents to PDF using the
[Island of TeX](https://gitlab.com/islandoftex/images/texlive)
`texlive/texlive` image — no host TeX Live install. This file collects the
bits a general-purpose agent (or human) tends to get wrong without
documentation; ordinary `pdflatex foo.tex`–level usage is taken for granted.

## Image-specific facts

- **Working directory:** `/workdir`. Mount the project source there
  (`-v "${PWD}:/workdir"`); do not invent `/data`, `/tex`, or similar.
- **Default user:** `root`. The unprivileged `texlive` user has shipped
  since 2025-02 — use `--user texlive` (or `-u "$(id -u):$(id -g)"`) on
  Linux hosts to avoid root-owned output files. Unnecessary on macOS/Windows.
- **`latest` tag is rebuilt weekly.** Pass `--pull=always` to `docker run`
  so the local cache does not go stale. Omit for historic and dated tags
  (those change rarely).
- **Schemes:** `minimal`, `basic`, `small`, `medium`, `full` (default for
  `latest`), and `context`. Tag form: `latest-<scheme>`, e.g.
  `latest-medium`. Smaller schemes pull faster but ship fewer CTAN
  packages and may omit `latexmk`, `arara`, or `context`.
- **Dated snapshots (reproducible):** `TL<year>-YYYY-MM-DD-<scheme>[-doc][-src]`,
  e.g. `TL2026-2026-10-18-full` or `TL2026-2026-10-18` (the bare form is
  the `full`-scheme alias). The first year is the TeX Live release; the
  date is the build date. Pin to one when you need byte-for-byte
  reproducibility.
- **Historic tags:** `TL<year>-historic[-doc][-src]`, e.g. `TL2024-historic`.
  Built for TeX Live `2013`–`2025` (full scheme only — no scheme
  variants). Rebuilt monthly for OS updates only; TeX Live contents are
  frozen.
- **Architectures:** `linux/amd64` and `linux/arm64/v8` (multi-arch
  manifests for `latest`, dated, and historic tags).
- **`-doc` and `-src` flavors** add *documentation* and *source* files for
  already-installed packages. They do **not** add more packages. If a
  package is missing, switch to a larger scheme or run
  `tlmgr install <pkg>` (plus `tlmgr path add` for new binaries on
  non-`full` schemes).

## Engine choice

Default to **LuaLaTeX** (`lualatex`) for new documents: native UTF-8,
OpenType / system fonts via `fontspec`, embedded Lua, active upstream
development. For plain TeX, the equivalent default is `luatex`.

Pick a different engine only with a concrete reason:

- `pdflatex` / `pdftex` — legacy documents tied to the classic 8-bit
  toolchain, or packages that only work there.
- `latex` / `tex` — DVI output specifically (e.g. `dvips` workflows).

ConTeXt sources (`\starttext`, `.mkiv`/`.mkxl`) → `context`.

Magic comments are honored by editors and respected by `latexmk` with the
matching configuration: `% !TEX program=lualatex`, `% !TEX root=main.tex`.

## Build tools

The `full` scheme (default for `latest`) ships every tool below. Smaller
schemes drop the heavier ones — pick a tag at least at the listed minimum
scheme, or run `tlmgr install <pkg>` inside the container.

| Tool | Use when | Min scheme |
| --- | --- | --- |
| `lualatex foo.tex` (or `pdflatex`, `latex`) | LaTeX, single-pass, no bibliography/index. | `basic` |
| `luatex foo.tex` (or `pdftex`, `tex`) | Plain TeX, single-pass. | `basic` |
| `latexmk -lualatex foo.tex` (or `-pdf`) | Multi-pass; auto-runs Biber/BibTeX/makeindex; honors `latexmkrc`. | `small` |
| `context foo.tex` | ConTeXt sources. | `medium` (or `latest-context`) |
| `arara foo.tex` | Source declares its build steps as `% arara: …` directives. | `medium` |

[`arara`](https://gitlab.com/islandoftex/arara) is part of the Island of
TeX. The source declares the pipeline as magic comments:

```tex
% arara: lualatex
% arara: biber
% arara: lualatex
% arara: lualatex
```

When such directives (or an `.araraconfig.yaml`) exist, prefer `arara` —
the source documents its own build.

## Run

Mount the project at `/workdir`; use `--pull=always` for `latest`:

```sh
docker run --rm --pull=always -v "${PWD}:/workdir" texlive/texlive:latest \
  latexmk -lualatex -interaction=nonstopmode -halt-on-error foo.tex
```

PowerShell:

```powershell
docker run --rm --pull=always -v "${PWD}:/workdir" texlive/texlive:latest `
  latexmk -lualatex -interaction=nonstopmode -halt-on-error foo.tex
```

Swap `latexmk -lualatex foo.tex` for any row in the Build tools table
(`lualatex foo.tex`, `arara foo.tex`, `context foo.tex`, …).

## File ownership on Linux

Run as the caller's UID/GID:

```sh
docker run --rm --pull=always -u "$(id -u):$(id -g)" -v "${PWD}:/workdir" \
  texlive/texlive:latest latexmk -lualatex foo.tex
```

…or use the unprivileged `texlive` user shipped in the image:

```sh
docker run --rm --pull=always --user texlive -v "${PWD}:/workdir" \
  texlive/texlive:latest latexmk -lualatex foo.tex
```

Unnecessary on macOS and Windows Docker Desktop.

## Error reporting

Extract the actual error from `foo.log`: search for lines starting with
`! ` together with the `l.<n>` line reference. Show that; do not paste the
full log. For a filtered summary use
[`read-tex-log`](../read-tex-log/SKILL.md) (`texlogsieve`).

With `-interaction=nonstopmode`, some fatal states appear as repeated
non-`!` lines (e.g. a NUL-corrupted `.aux` yields many
`Text line contains an invalid character` messages and a final
`==> Fatal error occurred`). If a `! `-grep finds nothing, check the last
lines of the log for `Fatal error` and `That makes 100 errors`.

## Fallback: `danteev/texlive` when TeX Live is not enough

Some documents call external tools through `--shell-escape` or need
packages that are not on CTAN. The plain `texlive/texlive` image does not
ship them; switch to [`danteev/texlive`](https://github.com/dante-ev/docker-texlive)
(Docker Hub `danteev/texlive`, mirror `ghcr.io/dante-ev/texlive`). It is
the Island of TeX `full` image plus:

| Need | Tool in the image |
| --- | --- |
| `plantuml` package | PlantUML (`plantuml`, `$PLANTUML_JAR`), Graphviz, Inkscape |
| `ltmermaid` / `mermaid.sty` | Mermaid CLI (`mmdc`) with Node.js and Chromium |
| `tikz-uml` | TikZ-UML (`tikz-uml.sty`, not in TeX Live) |
| `gnuplottex`, `pgfplots` with `gnuplot` | Gnuplot |
| `svg` package (`\includesvg`) | Inkscape |
| xfig figures | fig2dev |
| TeX ↔ Markdown/HTML conversion | Pandoc (recent release), LaTeXML, panflute |
| Bibliography tooling | bibtool |
| Spelling / grammar | aspell (en, de), TeXtidote (`textidote`) |
| PDF inspection | poppler-utils (`pdftotext`, `pdftoppm`, …) |
| Dependency listing | DEPP (`depp`) |
| Python packages | `pip3` |

`minted` works in both images (Python 3 with Pygments is in the base).

Facts that differ from `texlive/texlive`:

- **Tags:** `latest` (last release), `edge` (built on the 1st and 15th
  from upstream `latest`), `YYYY-MM-DD` (dated builds), and release tags
  `YYYY-R` where `YYYY` is the TeX Live year and `R` a letter, e.g.
  `2026-C`. Releases pin a dated upstream image, so `2026-C` is the
  reproducible choice. There are no scheme, `-doc`, or `-src` variants:
  the image is always `full`.
- **Size:** several GB (Inkscape, Chromium, Java). Pull once; prefer a
  release tag over `latest`/`edge` unless the newest TeX Live is needed.
- **Same conventions otherwise:** `/workdir` is the working directory,
  `root` is the default user and the `texlive` user exists, `latexmk`,
  `arara`, `context`, and `texlogsieve` are present, and `LANG` is
  `C.UTF-8`. Everything above about engines and build tools applies.
- **`/etc/latexmkrc`** makes `latexmk` ignore luaotfload's font caches so
  a LuaLaTeX build does not get an extra rerun in every fresh container.

Shell escape is required for PlantUML, Mermaid, Gnuplot, SVG, and minted:

```sh
docker run --rm -v "${PWD}:/workdir" danteev/texlive:2026-C \
  latexmk -lualatex -shell-escape -interaction=nonstopmode -halt-on-error foo.tex
```

```powershell
docker run --rm -v "${PWD}:/workdir" danteev/texlive:2026-C `
  latexmk -lualatex -shell-escape -interaction=nonstopmode -halt-on-error foo.tex
```

Add `--pull=always` for `latest` or `edge`. In GitHub Actions, the same
image backs [`dante-ev/latex-action`](https://github.com/dante-ev/latex-action).

## Housekeeping

- `latexmk -c foo.tex` — remove auxiliary files, keep the PDF.
- `latexmk -C foo.tex` — remove the PDF too.
- `context --purge foo.tex` — ConTeXt equivalent.
