---
name: run-with-gg
description: Run a CLI that is not installed — Java, Node.js, Gradle, Maven, JBang, or any GitHub release binary or jar such as typos, Vale, or TeXtidote — through gg.cmd, without installing it, on Windows, macOS, and Linux. Use when a command is not found, or a task needs a specific Java or tool version.
license: MIT
---

# Run tools with gg.cmd

[gg.cmd](https://github.com/eirikb/gg) is one file that runs other tools without installing
them: it downloads a tool on first use, caches it in `~/.cache/gg`
(`%UserProfile%\.cache\gg` on Windows), and puts it on `PATH` for that one command. The file
is a shell script and a batch file at once, so the same `gg.cmd` works on Windows, macOS, and
Linux. It needs neither `curl` nor a package manager.

## Get gg.cmd

```sh
curl -L ggcmd.io > gg.cmd
```

```powershell
Invoke-WebRequest ggcmd.io -OutFile gg.cmd
```

Put it on `PATH` or into the repository root (like `gradlew`). In a repository, mark it
executable for Unix users: `git update-index --chmod=+x gg.cmd`.

## Run a tool

On Unix, call it through `sh`, which works even if the file is not executable:

```sh
sh ./gg.cmd node --version
sh ./gg.cmd java@21 -version
sh ./gg.cmd gradle@8:java@21 build
sh ./gg.cmd gh/crate-ci/typos@1.51.1 --format brief .
```

```powershell
.\gg.cmd node --version
.\gg.cmd java@21 -version
.\gg.cmd gradle@8:java@21 build
.\gg.cmd gh/crate-ci/typos@1.51.1 --format brief .
```

- **Built-in tools**: `node` (also `npm`, `npx`), `java`, `gradle`, `maven`, `jbang`, `go`,
  `python`, `ruby`, `flutter`, and others; `gg.cmd tools` lists them.
- **Any GitHub release**: `gh/<owner>/<repo>@<tag>` picks the asset for the current OS and
  architecture, e.g., `gh/errata-ai/vale@3.24.0`. A release that ships a jar runs on Java:
  `gh/sylvainhalle/textidote@v0.9:java@21`.
- **Chains**: `tool@version:java@21` runs `tool` with that Java on `PATH`.
- **Versions**: `@21` (any 21.x.y), `@21.0` (any 21.0.z), `@21.0.4` (exact), `@^1.2.0`,
  `@~1.2.0`.

## What goes wrong

- **Pin `gh/` tools.** Without a version, gg may not pick the latest release: for typos it
  picked 1.13.10 while 1.51.1 was current; `@latest` did the same. Always give the tag.
- **The default Java is the newest.** Older programs can fail on it. LanguageTool, and with
  it TeXtidote, stops on Java 27 with `JAXP00010004: The accumulated size of entities ...
  exceeded the "100,000" limit set by "jdk.xml.totalEntitySizeLimit"`. Chain `java@21`, or
  pass `-Djdk.xml.totalEntitySizeLimit=0`.
- **The first run downloads.** A JDK is about 200 MB; the cache grows to gigabytes with
  several JDKs. `gg.cmd clean-cache` empties it. `-l` uses `.cache/gg` in the current
  directory instead.
- **Output.** When stdout is not a terminal, gg writes a newline before the tool's output; a
  parser of the tool's JSON must skip leading whitespace.
- **GitHub API limits.** gg looks up releases through the GitHub API; in CI, set
  `GG_GITHUB_TOKEN` (the `eirikb/gg/action` does it).

## In scripts

To fall back to gg when a tool is not on `PATH`, look for `gg.cmd` on `PATH` (or a path in
an environment variable such as `GG_CMD`), then run `sh <path> <tool>@<version> ...` on Unix
and `<path> <tool>@<version> ...` on Windows. The runners of the
[`prose-check-tex`](../../documents/prose-check-tex/SKILL.md) and
[`prose-check-markdown`](../../documents/prose-check-markdown/SKILL.md) skills do this for
typos, Vale, and TeXtidote.
