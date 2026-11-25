---
name: choose-latex-package
description: >-
  Pick the LaTeX package for a typesetting problem (cross-references, TODOs,
  quotation marks, source-code listings, tables, footnotes, URL breaks,
  widows/orphans, ligatures, glossaries, change tracking, UML, …) from the
  latextemplates GADR records (pros and cons per option) and the latex-snippets
  catalog (compiled MWEs). Use when writing or reviewing a LaTeX preamble, when
  asked "which package should I use for X", or before adding a \usepackage.
license: MIT
---

# Choose a LaTeX package

Two sources, kept by the [latextemplates](https://github.com/latextemplates) org:

- **GADR records** — [`gadr-latex-packages`](https://github.com/latextemplates/gadr-latex-packages):
  one Markdown file per problem, listing the considered packages with their pros and cons.
  Raw text: `https://raw.githubusercontent.com/latextemplates/gadr-latex-packages/main/<record>.md`.
- **Snippets** — [latex-snippets](https://latextemplates.github.io/latex-snippets/): one page
  per package with preamble, example source, and the rendered output, at
  `https://latextemplates.github.io/latex-snippets/snippets/<slug>`.

The "Pick" column is the choice of the latextemplates generator (its
[decision records](https://github.com/latextemplates/generator-latex-template/tree/main/docs/decisions)).
It assumes **LuaLaTeX** (generator default); several picks are LuaLaTeX-only. If the
document must build with pdfLaTeX, or the user's constraints differ (journal class,
no shell-escape), read the GADR record and pick from its options instead.

## Index

| Problem (GADR record) | Pick | Snippet |
| --- | --- | --- |
| [Acronyms and glossaries](https://github.com/latextemplates/gadr-latex-packages/blob/main/acronyms-and-glossaries.md) | `glossaries-extra` | [abbreviations](https://latextemplates.github.io/latex-snippets/snippets/abbreviations) |
| [Change tracking by several authors](https://github.com/latextemplates/gadr-latex-packages/blob/main/change-tracking.md) | `phfcc` | — |
| [Citation styles](https://github.com/latextemplates/gadr-latex-packages/blob/main/citation-styles.md) | `biblatex` + the style package (`biblatex-apa`, `biblatex-ieee`, …) | — |
| [Compilation speed](https://github.com/latextemplates/gadr-latex-packages/blob/main/compilation-speed.md) | depends; see record | — |
| [Compiling single chapters](https://github.com/latextemplates/gadr-latex-packages/blob/main/compiling-single-chapters.md) | `subfiles` | — |
| [Cross-references](https://github.com/latextemplates/gadr-latex-packages/blob/main/cross-references.md) | `zref-clever` (not `cleveref`: tagged PDFs) | [zref-clever](https://latextemplates.github.io/latex-snippets/snippets/zref-clever), [cleveref](https://latextemplates.github.io/latex-snippets/snippets/cleveref) |
| [Diagonal table cells](https://github.com/latextemplates/gadr-latex-packages/blob/main/diagonal-table-cells.md) | `diagbox` | [diagbox](https://latextemplates.github.io/latex-snippets/snippets/diagbox) |
| [Document version](https://github.com/latextemplates/gadr-latex-packages/blob/main/document-version.md) | `gitver` | — |
| [Footnotes in tables](https://github.com/latextemplates/gadr-latex-packages/blob/main/footnotes-in-tables.md) | `tablefootnote` | — |
| [Hyphenation](https://github.com/latextemplates/gadr-latex-packages/blob/main/hyphenation.md) | `\hyphenation{}` / `\-` + `microtype` | [hyphenation](https://latextemplates.github.io/latex-snippets/snippets/hyphenation) |
| [Image compression](https://github.com/latextemplates/gadr-latex-packages/blob/main/image-compression.md) | `graphicscache` | — |
| [Inline and compact lists](https://github.com/latextemplates/gadr-latex-packages/blob/main/inline-and-compact-lists.md) | `paralist` | [paralist](https://latextemplates.github.io/latex-snippets/snippets/paralist) |
| [Journal revisions](https://github.com/latextemplates/gadr-latex-packages/blob/main/journal-revisions.md) | depends; see record | — |
| [Ligatures](https://github.com/latextemplates/gadr-latex-packages/blob/main/ligatures.md) | `selnolig` (English), `autotype` (German) | — |
| [Log filtering](https://github.com/latextemplates/gadr-latex-packages/blob/main/log-filtering.md) | `texlogsieve`, not `silence` — see [`read-tex-log`](../read-tex-log/SKILL.md) | — |
| [Margin notes](https://github.com/latextemplates/gadr-latex-packages/blob/main/margin-notes.md) | `mindflow` | [mindflow](https://latextemplates.github.io/latex-snippets/snippets/mindflow) |
| [Numbers and units](https://github.com/latextemplates/gadr-latex-packages/blob/main/numbers-and-units.md) | `siunitx` | [siunitx](https://latextemplates.github.io/latex-snippets/snippets/siunitx) |
| [Overfull lines](https://github.com/latextemplates/gadr-latex-packages/blob/main/overfull-lines.md) | `linebreaker` (+ `microtype`) | [microtype](https://latextemplates.github.io/latex-snippets/snippets/microtype) |
| [Page numbering of a thesis](https://github.com/latextemplates/gadr-latex-packages/blob/main/page-numbering.md) | continuous from the title page | — |
| [Paragraph footnotes](https://github.com/latextemplates/gadr-latex-packages/blob/main/paragraph-footnotes.md) | `footmisc` option `para` | — |
| [Writing progress](https://github.com/latextemplates/gadr-latex-packages/blob/main/progress-bars.md) | `progressbar` | — |
| [Quotation marks](https://github.com/latextemplates/gadr-latex-packages/blob/main/quotation-marks.md) | `csquotes` with `\MakeOuterQuote{"}` | [outerquote](https://latextemplates.github.io/latex-snippets/snippets/outerquote), [csquotes](https://latextemplates.github.io/latex-snippets/snippets/csquotes), [textcmds](https://latextemplates.github.io/latex-snippets/snippets/textcmds) |
| [Short last lines](https://github.com/latextemplates/gadr-latex-packages/blob/main/short-last-lines.md) | `impnattypo` (LuaLaTeX only) | [impnattypo](https://latextemplates.github.io/latex-snippets/snippets/impnattypo) |
| [Source-code listings](https://github.com/latextemplates/gadr-latex-packages/blob/main/source-code-listings.md) | `minted`; `listings` without shell-escape | [minted](https://latextemplates.github.io/latex-snippets/snippets/minted), [listings](https://latextemplates.github.io/latex-snippets/snippets/listings) |
| [Complex table layout](https://github.com/latextemplates/gadr-latex-packages/blob/main/table-layout.md) | `tabularray` | [tabularray](https://latextemplates.github.io/latex-snippets/snippets/tabularray) |
| [Table rules](https://github.com/latextemplates/gadr-latex-packages/blob/main/table-rules.md) | `booktabs` | [booktabs](https://latextemplates.github.io/latex-snippets/snippets/booktabs) |
| [Text highlighting](https://github.com/latextemplates/gadr-latex-packages/blob/main/text-highlighting.md) | `lua-ul` (LuaLaTeX only) | — |
| [TODOs](https://github.com/latextemplates/gadr-latex-packages/blob/main/todo-package.md) | `zebra` | [todonotes](https://latextemplates.github.io/latex-snippets/snippets/todonotes), [pdfcomment](https://latextemplates.github.io/latex-snippets/snippets/pdfcomment) |
| [UML diagrams](https://github.com/latextemplates/gadr-latex-packages/blob/main/uml-diagrams.md) | depends; see record | — |
| [URL line breaks](https://github.com/latextemplates/gadr-latex-packages/blob/main/url-line-breaks.md) | `xurl` (load after `biblatex`) | [xurl](https://latextemplates.github.io/latex-snippets/snippets/xurl) |
| [Widows and orphans](https://github.com/latextemplates/gadr-latex-packages/blob/main/widows-and-orphans.md) | `lua-widow-control`; `nowidow` on pdfLaTeX | [widows-orphans](https://latextemplates.github.io/latex-snippets/snippets/widows-orphans) |

Snippets without a GADR record:
[paragraphs](https://latextemplates.github.io/latex-snippets/snippets/paragraphs) (one sentence
per line, blank line = paragraph).

## Workflow

1. Find the problem in the index. Not listed → say so and answer from general knowledge;
   do not invent a record.
2. Before recommending a package for a non-trivial case, fetch the GADR record (raw URL
   above) and check its cons against the user's setup: engine, document class, tagged-PDF
   requirement, shell-escape, journal restrictions.
3. Take the preamble and usage from the snippet page rather than writing them from memory;
   the snippets are compiled, so options and load order there are known to work.
4. Cite the record and the snippet in the answer so the user can read the trade-offs.
