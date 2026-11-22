---
name: magic-merge-commit
description: Fix Git merge conflicts after a squash merge on GitHub — a stacked pull request whose base branch was squash-merged into main no longer merges main cleanly. Creates a "magic" merge commit with jbang (or gg.cmd) that links the branch to the squashed commit. Use when merging or rebasing onto main conflicts with the branch's own, already squash-merged commits.
license: MIT
---

# Magic merge commit after a squash merge

Branch B was started from branch A (PR #A). PR #A was **squash-merged** into `main`. Git
sees no link between A's commits, which are still in B, and the squash commit in `main`, so
`git merge main` in B shows conflicts on lines that are in fact identical.
[magic-merge-commit](https://github.com/koppor/magic-merge-commit) builds a commit whose tree
is "A's last commit merged with the squash commit" and whose two parents are A's last commit
and the squash commit. It merges this commit into B. After that, `main` merges into B without
those conflicts.

Background: [blog post](https://blog.flupp.de/posts/git-and-squashed-prs/),
[demo repository](https://github.com/koppor/squash-merge-demo).

## Check first

Run nothing before all of these hold:

- The current branch is B, **not** `main` and not `create-merge-commit-support`.
- The working tree is clean (`git status`): the tool checks out several branches.
- The default branch is called `main` and the GitHub remote is called `origin`. Both names
  are hard-coded.
- The squash commit's subject still ends with ` (#<A>)`, as GitHub writes it by default. The
  tool finds the commit by this text only.
- You have the number of the **squash-merged** PR (#A), not the one of B. Ask the user if it
  is unclear; `gh pr list --state merged --search <branch-of-A>` helps.

## Run

The tool reads the GitHub token from `GITHUB_TOKEN`. Take it from the GitHub CLI if it is not
set.

```sh
export GITHUB_TOKEN="${GITHUB_TOKEN:-$(gh auth token)}"
jbang do@koppor/magic-merge-commit <pr-number-of-A>
```

```powershell
if (-not $env:GITHUB_TOKEN) { $env:GITHUB_TOKEN = gh auth token }
jbang do@koppor/magic-merge-commit <pr-number-of-A>
```

Without jbang, run it through [gg.cmd](../../tools/run-with-gg/SKILL.md):
`sh ./gg.cmd jbang do@koppor/magic-merge-commit <pr>` on Unix,
`.\gg.cmd jbang do@koppor/magic-merge-commit <pr>` on Windows. jbang fetches Java 21 itself
if none is found.

## What goes wrong

- **jbang trust question.** On first use, jbang asks whether to trust the source, in the
  terminal or in a desktop dialog. The user has to answer it; do not trust on their behalf.
  Without a terminal or dialog, run, after the user agrees,
  `jbang trust add https://github.com/koppor/magic-merge-commit/`.
- **First run is slow.** jbang downloads JGit, the GitHub API client, and maybe a JDK;
  give the command a few minutes before calling it hung.
- **`Could not find PR squash-merge commit`.** The squash commit's subject lacks
  ` (#<A>)` (edited title, or merged by another tool), or the number is the one of B.
- **Side effects on other branches.** The tool fetches `origin`, checks out A's branch (and
  creates it locally if missing) and merges `origin/<A>` into it, then merges `origin/main`
  into the local `main` — both with `--no-ff`, so each can get an extra merge commit. Check
  `git log --oneline -3 main` afterwards; tell the user before resetting anything.
- **`Not merged`.** The merge of the magic commit into B conflicted. The tool stops with exit
  code 1 and leaves the merge state and the helper branch `create-merge-commit-support`.
  Resolve and commit, or `git merge --abort`. The next run deletes the helper branch.
- **Several stacked layers.** Run the tool once per squash-merged PR, bottom-up, in each
  upper layer's branch.

## After running

```sh
git log --graph --oneline -8
git merge origin/main
```

The graph shows `Magic merge commit for PR #<A>` with two parents and `Merge into <B>`.
`git merge origin/main` now runs without the spurious conflicts; real conflicts with later
changes in `main` can remain. The tool does not push: ask the user before `git push`.
