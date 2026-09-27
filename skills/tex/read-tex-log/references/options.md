# texlogsieve options

All options of `texlogsieve` 1.6.1 (`texlogsieve --help`). Usage:
`texlogsieve [OPTION]... [INPUT FILE]`; without a file it reads stdin.

Every option can also go into a `texlogsieverc` file anywhere in the TeX path (one long
option per line, without `--`, e.g. `minlevel=CRITICAL`).

## Display

| Option | Effect |
| --- | --- |
| `--page-delay`, `--no-page-delay` | Group messages by page before display (on/off). |
| `--shipouts`, `--no-shipouts` | Report page shipouts (on/off). |
| `--file-banner`, `--no-file-banner` | Show/suppress the `From file ...` banners. |
| `--repetitions`, `--no-repetitions` | Allow/prevent repeated messages. |
| `--be-redundant`, `--no-be-redundant` | Show/suppress ordinary messages that also appear in the summary. |
| `--heartbeat`, `--no-heartbeat` | Progress spinner (on/off). Turn off when capturing output. |
| `--color`, `--no-color` | Colored output (on/off). Turn off when capturing output. |
| `--tips`, `--no-tips` | texlogsieve's own fix suggestions (on/off). |

## Summary

| Option | Effect |
| --- | --- |
| `--summary`, `--no-summary` | Final summary (on/off). |
| `--only-summary` | No message filtering; print only the final summary. |
| `--box-detail`, `--no-box-detail` | Full under/overfull box details in the summary. |
| `--ref-detail`, `--no-ref-detail` | Full undefined-reference details in the summary. |
| `--cite-detail`, `--no-cite-detail` | Full undefined-citation details in the summary. |
| `--summary-detail`, `--no-summary-detail` | Toggle the three `*-detail` options at once. |

## Filtering

| Option | Effect |
| --- | --- |
| `-l LEVEL`, `--minlevel=LEVEL` | Drop messages below `LEVEL`: `DEBUG`, `INFO`, `WARNING`, `CRITICAL`, `UNKNOWN`. |
| `-u`, `--unwrap-only` | No filtering or summary; only rejoin wrapped lines. |
| `--silence-package=PKGNAME` | Suppress messages from package `PKGNAME`. Repeatable. |
| `--silence-string=EXCERPT` | Suppress messages containing `EXCERPT`. Repeatable. |
| `--silence-file=FILENAME` | Suppress messages produced while processing `FILENAME` (recursive). Repeatable. |
| `--semisilence-file=FILENAME` | Like `--silence-file`, but not recursive. |

## Custom messages and severities

| Option | Effect |
| --- | --- |
| `--add-debug-message=MESSAGE` | Teach texlogsieve a new message at level `DEBUG`. |
| `--add-info-message=MESSAGE` | … at level `INFO`. |
| `--add-warning-message=MESSAGE` | … at level `WARNING`. |
| `--add-critical-message=MESSAGE` | … at level `CRITICAL`. |
| `--set-to-level-debug=EXCERPT` | Reset messages containing `EXCERPT` to `DEBUG`. Repeatable. |
| `--set-to-level-info=EXCERPT` | … to `INFO`. Repeatable. |
| `--set-to-level-warning=EXCERPT` | … to `WARNING`. Repeatable. |
| `--set-to-level-critical=EXCERPT` | … to `CRITICAL`. Repeatable. |

## Misc

| Option | Effect |
| --- | --- |
| `-c FILE`, `--config-file=FILE` | Read options from `FILE`, in addition to the default `texlogsieverc`. |
| `-v`, `--verbose` | Print texlogsieve's effective configuration. |
| `-h`, `--help` | Help. |
| `--version` | Version. |

The exact syntax of `MESSAGE` for the `--add-*-message` options is in the package manual:
`texdoc texlogsieve`.
