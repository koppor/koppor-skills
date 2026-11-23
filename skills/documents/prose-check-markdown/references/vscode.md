# Same checks in VS Code

The runner is editor-agnostic. VS Code extensions show similar findings while typing, but
they keep their own word lists and rule settings. Without the settings below, the editor
and the runner disagree.

## Extensions

| Tool | Extension | Reads by default |
| --- | --- | --- |
| LanguageTool | [`ltex-plus.vscode-ltex-plus`](https://marketplace.visualstudio.com/items?itemName=ltex-plus.vscode-ltex-plus) (LTeX+) | its bundled LanguageTool, `ltex.*` settings |
| markdownlint | [`DavidAnson.vscode-markdownlint`](https://marketplace.visualstudio.com/items?itemName=DavidAnson.vscode-markdownlint) | the repository's `.markdownlint*` file |
| Vale | [`ChrisChinchilla.vale-vscode`](https://marketplace.visualstudio.com/items?itemName=ChrisChinchilla.vale-vscode) | the workspace's `.vale.ini` |
| textlint | [`3w36zj6.textlint`](https://marketplace.visualstudio.com/items?itemName=3w36zj6.textlint) | the workspace's `.textlintrc*` |
| typos | [`tekumara.typos-vscode`](https://marketplace.visualstudio.com/items?itemName=tekumara.typos-vscode) | the repository's `.typos.toml` |

aspell has no matching extension. A repository can recommend the extensions in
`.vscode/extensions.json`:

```json
{
  "recommendations": [
    "ltex-plus.vscode-ltex-plus",
    "DavidAnson.vscode-markdownlint",
    "ChrisChinchilla.vale-vscode",
    "tekumara.typos-vscode"
  ]
}
```

## Keep editor and runner in step

- **Word lists.** LTeX+'s quick fix "Add to dictionary" writes to `ltex.dictionary` in the
  *user* settings, which the runner never reads. Add real words to the repository's
  `.aspell.<lang>.pws` (and `.typos.toml`) instead, and let LTeX+ read that file: an
  entry starting with `:` is a path to an external file, one word per line. The
  `personal_ws-1.1` header line of a `.pws` file becomes one harmless extra "word".

  ```json
  "ltex.dictionary": { "en-US": [":${workspaceFolder}/.aspell.en.pws"] }
  ```

  If `${workspaceFolder}` is not expanded in your LTeX+ version, use a path relative to
  the workspace or an absolute one.
- **Same LanguageTool.** LTeX+ uses its bundled LanguageTool, which can differ in
  version from the runner's Docker server. Point both at the same server:
  `"ltex.languageToolHttpServerUri": "http://localhost:8081"` (without `/v2/check`,
  LTeX+ appends it). Start the server as in [languagetool.md](languagetool.md).
- **Disabled rules.** `ltex.disabledRules` and `ltex.hiddenFalsePositives` affect only the
  editor. A rule that is wrong for the whole repository belongs in the runner's
  configuration too (see "Customize" in [SKILL.md](../SKILL.md)).
- **Language.** `ltex.language` defaults to `en-US`. For German text set `de-DE` (the bare
  `de` checks grammar only, no spelling) and run the runner with `CHECK_MD_LANG=de`.
- **Vale.** The runner always uses the skill's `assets/vale.ini`. To see the same alerts,
  set `vale.valeCLI.config` to that file, or give the repository its own `.vale.ini`.
- **markdownlint.** Without a `.markdownlint*` file in the repository, the extension
  checks all rules including line length (MD013), but the runner turns MD013 off. Add a
  `.markdownlint.jsonc` to the repository so both apply the same rules.

## What the agent sees

An agent running this skill does not see the editor's Problems panel. Run the runner for
findings, or paste the editor's diagnostics into the conversation.
