#!/usr/bin/env node
// check-md.mjs — Lint Markdown with textlint + Vale (+ LanguageTool), typos, aspell, and
// markdownlint and emit a single
// merged JSON array of findings on stdout, a human summary on stderr.
//
// Usage:  node check-md.mjs <file-or-dir> [more files/dirs...]
//
// Findings are normalized to one shape:
//   { file, line, column, severity, source, rule, message, fixable }
//     severity : "error" | "warning" | "suggestion"
//     source   : "textlint" | "vale" | "languagetool" | "typos" | "aspell" | "markdownlint"
//
// Severity policy (see normalizeSeverity): grammar (LanguageTool) and spelling
// (Vale.Spelling) stay `error`; wordiness/style (write-good, terminology, proselint)
// is `warning`; readability is `suggestion`. So `error` means "very likely wrong".
//
// LanguageTool runs inside textlint (rule `@textlint-rule/gramma`), so it is markup-aware.
// The server is auto-detected and, if a local one is absent, auto-started via Docker; if
// neither works the grammar rule is dropped and the run continues (textlint + Vale). Text
// is never sent to a remote host unless you explicitly point LANGUAGETOOL_URL at one.
//
// For LaTeX (.tex) use the sibling `prose-check-tex` skill — Vale cannot parse LaTeX and the
// gramma rule crashes on the LaTeX AST.
//
// Exit codes: 0 = clean, 1 = findings reported, 2 = setup/tool failure.

import { spawnSync } from 'node:child_process';
import { existsSync, readdirSync, statSync, readFileSync, writeFileSync } from 'node:fs';
import { basename, dirname, extname, join, relative, resolve, sep } from 'node:path';
import { fileURLToPath } from 'node:url';

const scriptDir = dirname(fileURLToPath(import.meta.url));
const skillDir = resolve(scriptDir, '..');
const assetsDir = join(skillDir, 'assets');
const baseTextlintConfig = join(assetsDir, 'textlintrc.json');
const mdTextlintConfig = join(assetsDir, '.textlintrc.md.json');
const valeConfig = join(assetsDir, 'vale.ini');
const valeStylesDir = join(assetsDir, 'styles');
const textlintBin = join(assetsDir, 'node_modules', 'textlint', 'bin', 'textlint.js');

const LT_URL = process.env.LANGUAGETOOL_URL || 'http://localhost:8081/v2/check';
const isWin = process.platform === 'win32';

const MD_EXT = new Set(['.md', '.markdown', '.mdown', '.mkd']);
const GRAMMA_KEY = '@textlint-rule/gramma';

let hadToolError = false;

function warn(msg) {
  process.stderr.write(`prose-check-markdown: ${msg}\n`);
}

function isRemoteHost(url) {
  try {
    const h = new URL(url).hostname;
    return !['localhost', '127.0.0.1', '::1', '[::1]'].includes(h);
  } catch {
    return false;
  }
}

// Run a command, never throwing. Returns { status, stdout, stderr, ok }.
function run(cmd, args, opts = {}) {
  const res = spawnSync(cmd, args, {
    encoding: 'utf8',
    maxBuffer: 64 * 1024 * 1024,
    cwd: assetsDir,
    ...opts,
  });
  if (res.error) return { status: null, stdout: '', stderr: String(res.error.message), ok: false };
  return { status: res.status, stdout: res.stdout || '', stderr: res.stderr || '', ok: res.status === 0 };
}

// Native binaries (vale, docker, npm) need a shell on Windows to honor PATHEXT; when shell
// is on, Node does not quote args, so quote them ourselves. On POSIX, spawn directly.
function runBin(cmd, args, opts = {}) {
  if (isWin) {
    const q = (s) => (/[\s"&|<>^]/.test(s) ? `"${String(s).replace(/"/g, '\\"')}"` : s);
    const line = [cmd, ...args].map(q).join(' ');
    return run(line, [], { shell: true, ...opts });
  }
  return run(cmd, args, opts);
}

const vale = (args, opts = {}) => runBin('vale', args, opts);

function commandExists(cmd) {
  const probe = isWin
    ? run('where', [cmd], { cwd: process.cwd() })
    : run('command', ['-v', cmd], { cwd: process.cwd(), shell: true });
  return probe.status === 0;
}

// Install the pinned textlint toolchain on first use.
function ensureNodeModules() {
  // markdownlint-cli2 is checked, too: an install from before it was added lacks it
  if (existsSync(textlintBin) && existsSync(markdownlintBin)) return true;
  warn('textlint dependencies missing — running `npm install` (one-time)...');
  const res = runBin('npm', ['install', '--no-audit', '--no-fund'], { cwd: assetsDir, stdio: ['ignore', 2, 2] });
  if (!res.ok || !existsSync(textlintBin) || !existsSync(markdownlintBin)) {
    warn(`npm install failed — run it manually:  npm install --prefix "${assetsDir}"`);
    return false;
  }
  return true;
}

// ── Input expansion ──────────────────────────────────────────────────────────
function collectFiles(paths) {
  const out = [];
  const walk = (p) => {
    const abs = resolve(p);
    if (!existsSync(abs)) { warn(`path not found: ${p}`); return; }
    if (statSync(abs).isDirectory()) {
      for (const entry of readdirSync(abs)) {
        if (entry === 'node_modules' || entry.startsWith('.')) continue;
        walk(join(abs, entry));
      }
    } else if (MD_EXT.has(extname(abs).toLowerCase())) {
      out.push(abs);
    }
  };
  paths.forEach(walk);
  return [...new Set(out)];
}

// ── LanguageTool availability ────────────────────────────────────────────────
async function ping(url) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 3000);
  try {
    const res = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: new URLSearchParams({ language: 'en-US', text: 'ok' }),
      signal: controller.signal,
    });
    return res.ok;
  } catch {
    return false;
  } finally {
    clearTimeout(timer);
  }
}

async function ensureLanguageTool() {
  if (isRemoteHost(LT_URL)) {
    warn(`LANGUAGETOOL_URL points at a remote host (${new URL(LT_URL).hostname}); document text will be sent there.`);
    return ping(LT_URL);
  }
  if (await ping(LT_URL)) return true;
  // Start the community Docker image, mapping the endpoint's host port -> container 8010.
  if (commandExists('docker')) {
    const m = LT_URL.match(/:(\d+)\//);
    const hostPort = m ? m[1] : '8081';
    warn(`LanguageTool not reachable at ${LT_URL}; starting erikvl87/languagetool via Docker...`);
    runBin('docker', ['run', '-d', '--rm', '-p', `${hostPort}:8010`, 'erikvl87/languagetool'], { cwd: process.cwd() });
    for (let i = 0; i < 30; i++) {
      await new Promise((r) => setTimeout(r, 1000));
      if (await ping(LT_URL)) return true;
    }
  }
  return false;
}

// Build the effective textlint config: keep gramma iff LanguageTool is reachable.
async function buildTextlintConfig() {
  let config;
  try {
    config = JSON.parse(readFileSync(baseTextlintConfig, 'utf8'));
  } catch (e) {
    warn(`cannot read ${baseTextlintConfig}: ${e.message}`);
    hadToolError = true;
    return baseTextlintConfig;
  }
  if (config.rules && config.rules[GRAMMA_KEY]) {
    if (await ensureLanguageTool()) {
      if (config.rules[GRAMMA_KEY] === true) config.rules[GRAMMA_KEY] = {};
      config.rules[GRAMMA_KEY].api_url = LT_URL;
    } else {
      warn('LanguageTool unavailable — continuing without grammar checks (textlint + Vale only).');
      delete config.rules[GRAMMA_KEY];
    }
  }
  writeFileSync(mdTextlintConfig, JSON.stringify(config, null, 2));
  return mdTextlintConfig;
}

// ── Severity policy ──────────────────────────────────────────────────────────
// error = very likely wrong (grammar, spelling); warning = style/wordiness;
// suggestion = readability. Vale styles already carry sensible levels; textlint's
// style rules default to "error", so downgrade them here.
const TEXTLINT_STYLE_RULES = new Set(['write-good', 'terminology']);
function normalizeSeverity(source, rule, reported) {
  if (source === 'textlint' && TEXTLINT_STYLE_RULES.has(rule)) return 'warning';
  if (source === 'vale') {
    // Only spelling is a hard error; Vale packages mark many style rules `error` too.
    if (rule === 'Vale.Spelling') return 'error';
    return reported === 'error' ? 'warning' : reported;
  }
  return reported; // LanguageTool grammar keeps its reported severity.
}

// ── Runners ──────────────────────────────────────────────────────────────────
const textlintLevel = (n) => (n === 2 ? 'error' : n === 1 ? 'warning' : 'suggestion');

function runTextlint(file, configPath) {
  const res = run(process.execPath, [textlintBin, '--config', configPath, '-f', 'json', file]);
  if (!res.stdout.trim()) {
    if (res.status !== 0) {
      warn(`textlint failed on ${file}: ${res.stderr.trim() || 'no output'}`);
      hadToolError = true;
    }
    return [];
  }
  let parsed;
  try {
    parsed = JSON.parse(res.stdout);
  } catch {
    warn(`textlint produced unparseable output on ${file}`);
    hadToolError = true;
    return [];
  }
  const findings = [];
  for (const entry of parsed) {
    for (const m of entry.messages || []) {
      const rule = m.ruleId || 'textlint';
      const source = rule.includes('gramma') ? 'languagetool' : 'textlint';
      findings.push({
        file,
        line: m.line ?? null,
        column: m.column ?? null,
        severity: normalizeSeverity(source, rule, textlintLevel(m.severity)),
        source,
        rule,
        message: (m.message || '').trim(),
        fixable: Boolean(m.fix),
      });
    }
  }
  return findings;
}

function runVale(file) {
  const res = vale(['--config', valeConfig, '--output=JSON', file]);
  if (!res.stdout.trim()) {
    if (res.status !== 0 && res.status !== 1) {
      warn(`Vale failed on ${file}: ${res.stderr.trim() || 'no output'}`);
      hadToolError = true;
    }
    return [];
  }
  let parsed;
  try {
    parsed = JSON.parse(res.stdout);
  } catch {
    warn(`Vale produced unparseable output on ${file}`);
    hadToolError = true;
    return [];
  }
  const findings = [];
  for (const [fname, alerts] of Object.entries(parsed)) {
    for (const a of alerts) {
      const rule = a.Check || 'vale';
      findings.push({
        file: fname,
        line: a.Line ?? null,
        column: Array.isArray(a.Span) ? a.Span[0] : null,
        severity: normalizeSeverity('vale', rule, (a.Severity || 'suggestion').toLowerCase()),
        source: 'vale',
        rule,
        message: (a.Message || '').trim(),
        fixable: Boolean(a.Action && a.Action.Name),
      });
    }
  }
  return findings;
}

function ensureValeStyles() {
  if (!commandExists('vale')) return false;
  const hasStyles = existsSync(valeStylesDir) && readdirSync(valeStylesDir).length > 0;
  if (!hasStyles) {
    warn('Vale styles missing — running `vale sync` (one-time download)...');
    const res = vale(['--config', valeConfig, 'sync']);
    if (!res.ok) warn(`vale sync failed: ${res.stderr.trim()}`);
  }
  return true;
}

// ── typos ────────────────────────────────────────────────────────────────────
// https://github.com/crate-ci/typos finds common misspellings (English only), also in
// comments and code. Taken from PATH, else via `pipx run typos` or `uvx typos`.
// typos finds the repository's .typos.toml by walking up from the file;
// --force-exclude applies its extend-exclude (e.g., German files) to named files, too.
let typosCmd;
function resolveTypos() {
  if (typosCmd !== undefined) return typosCmd;
  if (commandExists('typos')) typosCmd = ['typos'];
  else if (commandExists('pipx')) typosCmd = ['pipx', 'run', 'typos'];
  else if (commandExists('uvx')) typosCmd = ['uvx', 'typos'];
  else typosCmd = null;
  return typosCmd;
}

function runTypos(file) {
  const cmd = resolveTypos();
  if (!cmd) return [];
  const res = runBin(cmd[0], [...cmd.slice(1), '--format', 'json', '--force-exclude', basename(file)],
    { cwd: dirname(file) });
  // Exit code 2 means "typos found"; anything else besides 0 is a tool failure.
  if (res.status !== 0 && res.status !== 2) {
    warn(`typos failed on ${file}: ${res.stderr.trim() || 'no output'}`);
    hadToolError = true;
    return [];
  }
  const findings = [];
  for (const line of res.stdout.split('\n')) {
    if (!line.trim().startsWith('{')) continue;
    let t;
    try { t = JSON.parse(line); } catch { continue; }
    if (t.type !== 'typo') continue;
    findings.push({
      file,
      line: t.line_num ?? null,
      column: t.byte_offset != null ? t.byte_offset + 1 : null, // bytes, not characters
      severity: 'error',
      source: 'typos',
      rule: 'typos',
      message: `"${t.typo}" should be ${(t.corrections || []).map((c) => `"${c}"`).join(' or ') || 'removed'}`,
      fixable: (t.corrections || []).length === 1,
    });
  }
  return findings;
}

// ── aspell ───────────────────────────────────────────────────────────────────
// http://aspell.net checks spelling against a dictionary per language, as the CI setup of
// the prose-checks-ci skill does. Taken from PATH, else from the danteev/texlive Docker
// image (ASPELL_IMAGE). The repository's .aspell.conf (add-tex-command ...) and word list
// .aspell.<lang>.pws apply, so local and CI findings match.
const aspellImage = process.env.ASPELL_IMAGE || 'danteev/texlive:latest';
let aspellMode;
function resolveAspell() {
  if (aspellMode !== undefined) return aspellMode;
  if (commandExists('aspell')) aspellMode = 'path';
  else if (commandExists('docker')) aspellMode = 'docker';
  else aspellMode = null;
  return aspellMode;
}

function findRepoRoot(file) {
  let dir = dirname(file);
  for (;;) {
    if (existsSync(join(dir, '.git'))) return dir;
    if (dirname(dir) === dir) return dirname(file);
    dir = dirname(dir);
  }
}

// lang: two-letter code, e.g., "en" or "de"; filterMode: aspell's "tex" or "markdown" filter
function runAspell(file, text, lang, filterMode) {
  const mode = resolveAspell();
  if (!mode) return [];
  const root = findRepoRoot(file);
  const dict = { en: 'en_US', de: 'de_DE' }[lang] || lang;
  const args = ['-a', `--mode=${filterMode}`, '-l', dict, '--encoding=utf-8'];
  if (lang === 'de') args.push('--run-together'); // German compounds
  if (existsSync(join(root, '.aspell.conf'))) args.push('--conf=./.aspell.conf');
  if (existsSync(join(root, `.aspell.${lang}.pws`))) args.push('-p', `./.aspell.${lang}.pws`);
  // Pipe mode: "!" reports only misspellings; "^" makes each line plain text; aspell ends
  // the output of each input line with an empty line
  const input = '!\n' + text.split('\n').map((l) => `^${l}`).join('\n') + '\n';
  const user = isWin ? [] : ['-u', `${process.getuid()}:${process.getgid()}`];
  const res = mode === 'path'
    ? runBin('aspell', args, { cwd: root, input })
    : runBin('docker', ['run', '--rm', '-i', ...user, '-e', 'HOME=/tmp', '-v', `${root}:/w`, '-w', '/w',
      aspellImage, 'aspell', ...args], { cwd: root, input });
  if (!res.ok) {
    warn(`aspell failed on ${file}: ${res.stderr.trim().split('\n').slice(-3).join(' ') || 'no output'}`);
    hadToolError = true;
    return [];
  }
  const findings = [];
  let line = 1;
  for (const out of res.stdout.split('\n').slice(1)) {
    if (out === '') { line++; continue; }
    // "& <word> <count> <offset>: <suggestions>" or "# <word> <offset>"; the offset counts the "^"
    const m = out.match(/^[&#] (\S+) (?:\d+ )?(\d+)(?:: (.*))?$/);
    if (!m) continue;
    const suggestions = m[3] ? m[3].split(', ').slice(0, 5) : [];
    findings.push({
      file,
      line,
      column: Number(m[2]),
      severity: 'error',
      source: 'aspell',
      rule: `aspell-${dict}`,
      message: `"${m[1]}" is not in the ${dict} dictionary${suggestions.length ? `; suggestions: ${suggestions.join(', ')}` : ''}`,
      fixable: false,
    });
  }
  return findings;
}

// aspell's Markdown filter does not know LaTeX in Markdown (\LaTeX{}, <#sec:x>, {#sec:x});
// blank it out with spaces, so the columns stay right
const stripLatex = (text) => text.replace(/\\[A-Za-z]+|<#[^>]*>|\{#[^}]*\}/g, (m) => ' '.repeat(m.length));

// ── markdownlint ─────────────────────────────────────────────────────────────
// https://github.com/DavidAnson/markdownlint-cli2 checks the Markdown structure (headings,
// lists, blank lines). It runs in the repository root, so the repository's .markdownlint*
// configuration applies; without one, assets/markdownlint.jsonc turns off the line length.
const markdownlintBin = join(assetsDir, 'node_modules', 'markdownlint-cli2', 'markdownlint-cli2-bin.mjs');
const MARKDOWNLINT_CONFIGS = ['.markdownlint-cli2.jsonc', '.markdownlint-cli2.yaml', '.markdownlint-cli2.cjs',
  '.markdownlint-cli2.mjs', '.markdownlint.jsonc', '.markdownlint.json', '.markdownlint.yaml', '.markdownlint.yml',
  '.markdownlint.cjs', '.markdownlint.mjs'];

function runMarkdownlint(file) {
  const root = findRepoRoot(file);
  const hasConfig = MARKDOWNLINT_CONFIGS.some((c) => existsSync(join(root, c)));
  const rel = relative(root, file).split(sep).join('/');
  const args = [markdownlintBin, ...(hasConfig ? [] : ['--config', join(assetsDir, 'markdownlint.jsonc')]), `:${rel}`];
  const res = run(process.execPath, args, { cwd: root });
  // Exit code 1 means "issues found"
  if (res.status !== 0 && res.status !== 1) {
    warn(`markdownlint failed on ${file}: ${res.stderr.trim().split('\n').slice(-3).join(' ') || 'no output'}`);
    hadToolError = true;
    return [];
  }
  const findings = [];
  // "<file>:<line>[:<column>] error <rule>/<alias> <description> [<detail>] [Context: ...]"
  for (const out of res.stderr.split('\n')) {
    const m = out.match(/^(.+?):(\d+)(?::(\d+))? (?:error|warning) (\S+) (.*)$/);
    if (!m) continue;
    findings.push({
      file,
      line: Number(m[2]),
      column: m[3] ? Number(m[3]) : null,
      severity: 'warning',
      source: 'markdownlint',
      rule: m[4],
      message: m[5].trim(),
      fixable: false,
    });
  }
  return findings;
}

// ── Main ─────────────────────────────────────────────────────────────────────
async function main() {
  const paths = process.argv.slice(2);
  if (paths.length === 0) {
    warn('usage: node check-md.mjs <file-or-dir> [...]');
    process.exit(2);
  }

  const files = collectFiles(paths);
  if (files.length === 0) {
    warn('no Markdown (.md/.markdown) files found. For LaTeX, use the prose-check-tex skill.');
    process.exit(2);
  }

  if (!ensureNodeModules()) process.exit(2);

  const textlintConfig = await buildTextlintConfig();
  const valeUsable = ensureValeStyles();
  if (!valeUsable) warn('Vale not found on PATH — Markdown will be checked with textlint only.');

  if (!resolveTypos()) warn('typos not found (PATH, pipx, uvx) — misspellings are not checked by typos.');
  if (!resolveAspell()) warn('aspell not found (PATH, Docker) — spelling is not checked by aspell.');

  const findings = [];
  for (const file of files) {
    findings.push(...runTextlint(file, textlintConfig));
    if (valeUsable) findings.push(...runVale(file));
    findings.push(...runTypos(file));
    findings.push(...runAspell(file, stripLatex(readFileSync(file, 'utf8')), process.env.CHECK_MD_LANG || 'en', 'markdown'));
    findings.push(...runMarkdownlint(file));
  }

  findings.sort((a, b) =>
    a.file.localeCompare(b.file) || (a.line ?? 0) - (b.line ?? 0) || (a.column ?? 0) - (b.column ?? 0));

  process.stdout.write(JSON.stringify(findings, null, 2) + '\n');

  const tally = (key) => findings.reduce((o, f) => ((o[f[key]] = (o[f[key]] || 0) + 1), o), {});
  const fmt = (o) => Object.entries(o).map(([k, v]) => `${k}=${v}`).join(' ') || 'none';
  warn(`${findings.length} finding(s) across ${files.length} file(s)`);
  warn(`  by source:   ${fmt(tally('source'))}`);
  warn(`  by severity: ${fmt(tally('severity'))}`);

  // exitCode, not exit(): exit() would end the process before a piped stdout is flushed
  process.exitCode = hadToolError ? 2 : findings.length > 0 ? 1 : 0;
}

main().catch((e) => {
  warn(`fatal: ${e.stack || e.message}`);
  process.exit(2);
});
