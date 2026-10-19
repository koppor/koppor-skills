#!/usr/bin/env node
// check-tex.mjs — Lint LaTeX prose with textlint (latex2e plugin), TeXtidote, and typos and emit a merged JSON
// array of findings on stdout, a human summary on stderr.
//
// Usage:  node check-tex.mjs <file-or-dir> [more files/dirs...]
//
// Findings shape (matches the check-markdown skill):
//   { file, line, column, severity, source, rule, message, fixable }
//     severity : "error" | "warning" | "suggestion"
//     source   : "textlint" | "textidote" | "typos"
//
// Why LaTeX is its own skill:
//   - Vale has no LaTeX parser (errata-ai/vale#54) — it would flag markup as prose.
//   - `@textlint-rule/gramma` (the LanguageTool bridge) crashes on the latex2e AST.
// So this skill checks style/terminology via textlint's `latex2e` parser, which lints only
// prose nodes and ignores commands/math. TeXtidote (LanguageTool on the LaTeX source,
// plus LaTeX style rules) checks spelling and grammar; it runs from PATH or in the
// danteev/texlive Docker image. typos finds misspellings, also in comments.
// For more grammar checking, `ltex-cli` — see references/ltex.md.
//
// Exit codes: 0 = clean, 1 = findings reported, 2 = setup/tool failure.

import { spawnSync } from 'node:child_process';
import { existsSync, readdirSync, readFileSync, statSync } from 'node:fs';
import { basename, dirname, extname, join, relative, resolve, sep } from 'node:path';
import { fileURLToPath } from 'node:url';

const scriptDir = dirname(fileURLToPath(import.meta.url));
const skillDir = resolve(scriptDir, '..');
const assetsDir = join(skillDir, 'assets');
const textlintConfig = join(assetsDir, 'textlintrc.json');
const textlintBin = join(assetsDir, 'node_modules', 'textlint', 'bin', 'textlint.js');

const isWin = process.platform === 'win32';
const TEX_EXT = new Set(['.tex', '.latex', '.ltx']);
const TEXTLINT_STYLE_RULES = new Set(['write-good', 'terminology']);

let hadToolError = false;
const warn = (msg) => process.stderr.write(`check-tex: ${msg}\n`);

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

function runBin(cmd, args, opts = {}) {
  if (isWin) {
    const q = (s) => (/[\s"&|<>^]/.test(s) ? `"${String(s).replace(/"/g, '\\"')}"` : s);
    return run([cmd, ...args].map(q).join(' '), [], { shell: true, ...opts });
  }
  return run(cmd, args, opts);
}

function commandExists(cmd) {
  const probe = isWin
    ? run('where', [cmd], { cwd: process.cwd() })
    : run('command', ['-v', cmd], { cwd: process.cwd(), shell: true });
  return probe.status === 0;
}

function ensureNodeModules() {
  if (existsSync(join(assetsDir, 'node_modules')) && existsSync(textlintBin)) return true;
  warn('textlint dependencies missing — running `npm install` (one-time)...');
  const res = runBin('npm', ['install', '--no-audit', '--no-fund'], { cwd: assetsDir, stdio: ['ignore', 2, 2] });
  if (!res.ok || !existsSync(textlintBin)) {
    warn(`npm install failed — run it manually:  npm install --prefix "${assetsDir}"`);
    return false;
  }
  return true;
}

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
    } else if (TEX_EXT.has(extname(abs).toLowerCase())) {
      out.push(abs);
    }
  };
  paths.forEach(walk);
  return [...new Set(out)];
}

const textlintLevel = (n) => (n === 2 ? 'error' : n === 1 ? 'warning' : 'suggestion');
const normalizeSeverity = (rule, reported) => (TEXTLINT_STYLE_RULES.has(rule) ? 'warning' : reported);

function runTextlint(file) {
  const res = run(process.execPath, [textlintBin, '--config', textlintConfig, '-f', 'json', file]);
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
      findings.push({
        file,
        line: m.line ?? null,
        column: m.column ?? null,
        severity: normalizeSeverity(rule, textlintLevel(m.severity)),
        source: 'textlint',
        rule,
        message: (m.message || '').trim(),
        fixable: Boolean(m.fix),
      });
    }
  }
  return findings;
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

// ── TeXtidote ────────────────────────────────────────────────────────────────
// https://github.com/sylvainhalle/textidote runs LanguageTool on LaTeX (spelling, grammar)
// and adds LaTeX style rules (sh:*). Taken from PATH, else from the danteev/texlive Docker
// image (override with TEXTIDOTE_IMAGE). TeXtidote reads a `.textidote` file in its working
// directory (options such as --check, --dict, --replace, --remove-macros), so it runs in
// the nearest ancestor directory containing one — the repository's settings apply.
const textidoteImage = process.env.TEXTIDOTE_IMAGE || 'danteev/texlive:latest';
let textidoteMode;
function resolveTextidote() {
  if (textidoteMode !== undefined) return textidoteMode;
  if (commandExists('textidote')) textidoteMode = 'path';
  else if (commandExists('docker')) textidoteMode = 'docker';
  else textidoteMode = null;
  return textidoteMode;
}

function findTextidoteRoot(file) {
  let dir = dirname(file);
  for (;;) {
    if (existsSync(join(dir, '.textidote'))) return { root: dir, config: true };
    if (existsSync(join(dir, '.git')) || dirname(dir) === dir) break;
    dir = dirname(dir);
  }
  return { root: dirname(file), config: false };
}

// Language when the repository has no .textidote: CHECK_TEX_LANG, else "% !TeX spellcheck = <lang>", else en
function detectLanguage(text) {
  if (process.env.CHECK_TEX_LANG) return process.env.CHECK_TEX_LANG;
  const m = text.match(/^%\s*!TeX spellcheck\s*=\s*([A-Za-z]{2})/m);
  return m ? m[1].toLowerCase() : 'en';
}

function textidoteSeverity(rule) {
  const id = rule?.id || '';
  const category = rule?.category?.id || '';
  if (id.startsWith('lt:') && (category === 'TYPOS' || category === 'GRAMMAR' || id.includes('MORFOLOGIK'))) return 'error';
  return 'warning';
}

// TeXtidote 0.9's JSON has the rule IDs, but its offsets point to the start of the line;
// the singleline output has the exact positions. Both list the matches in the same order.
const SEPARATOR = '@@check-tex@@';
const SINGLELINE = /\(L(\d+)C(\d+)-L\d+C\d+\): /;

function runTextidote(file) {
  const mode = resolveTextidote();
  if (!mode) return [];
  const text = readFileSync(file, 'utf8');
  const { root, config } = findTextidoteRoot(file);
  const rel = relative(root, file).split(sep).join('/');
  const args = [];
  // Without \begin{document} (an \include'd chapter), TeXtidote would skip the whole file
  if (!text.includes('\\begin{document}')) args.push('--read-all');
  if (!config) args.push('--check', detectLanguage(text));
  let jsonOut;
  let singleOut;
  if (mode === 'path') {
    const json = runBin('textidote', ['--output', 'json', ...args, rel], { cwd: root });
    jsonOut = json.stdout;
    singleOut = runBin('textidote', ['--output', 'singleline', '--no-color', ...args, rel], { cwd: root }).stdout;
    if (!jsonOut.includes('{')) {
      warn(`TeXtidote failed on ${file}: ${json.stderr.trim().split('\n').slice(-3).join(' ') || 'no output'}`);
      hadToolError = true;
      return [];
    }
  } else {
    const user = isWin ? [] : ['-u', `${process.getuid()}:${process.getgid()}`];
    const a = args.join(' ');
    const script = `textidote --output json ${a} "$1"; echo ${SEPARATOR}; textidote --output singleline --no-color ${a} "$1"`;
    const res = runBin('docker', ['run', '--rm', ...user, '-e', 'HOME=/tmp', '-v', `${root}:/w`, '-w', '/w',
      textidoteImage, 'sh', '-c', script, 'sh', rel], { cwd: root });
    const parts = res.stdout.split(SEPARATOR);
    if (parts.length !== 2 || !parts[0].includes('{')) {
      warn(`TeXtidote failed on ${file}: ${res.stderr.trim().split('\n').slice(-3).join(' ') || 'no output'}`);
      hadToolError = true;
      return [];
    }
    [jsonOut, singleOut] = parts;
  }
  let parsed;
  try {
    parsed = JSON.parse(jsonOut.slice(jsonOut.indexOf('{')));
  } catch {
    warn(`TeXtidote produced unparseable output on ${file}`);
    hadToolError = true;
    return [];
  }
  const positions = singleOut.split('\n').map((l) => l.match(SINGLELINE)).filter(Boolean);
  const matches = parsed.matches || [];
  if (positions.length !== matches.length) warn(`TeXtidote positions incomplete for ${file}; lines may be approximate`);
  return matches.map((m, i) => ({
    file,
    line: positions[i] ? Number(positions[i][1]) : text.slice(0, m.offset ?? 0).split('\n').length,
    column: positions[i] ? Number(positions[i][2]) : null,
    severity: textidoteSeverity(m.rule),
    source: 'textidote',
    rule: m.rule?.id || 'textidote',
    message: (m.message || '').trim(),
    fixable: false,
  }));
}

function main() {
  const paths = process.argv.slice(2);
  if (paths.length === 0) {
    warn('usage: node check-tex.mjs <file-or-dir> [...]');
    process.exit(2);
  }

  const files = collectFiles(paths);
  if (files.length === 0) {
    warn('no LaTeX (.tex/.latex/.ltx) files found. For Markdown, use the check-markdown skill.');
    process.exit(2);
  }

  if (!ensureNodeModules()) process.exit(2);

  if (!resolveTextidote()) warn('TeXtidote not found (PATH, Docker) — spelling and grammar are not checked by TeXtidote.');
  if (!resolveTypos()) warn('typos not found (PATH, pipx, uvx) — misspellings are not checked by typos.');

  const findings = [];
  for (const file of files) {
    findings.push(...runTextlint(file));
    findings.push(...runTextidote(file));
    findings.push(...runTypos(file));
  }

  findings.sort((a, b) =>
    a.file.localeCompare(b.file) || (a.line ?? 0) - (b.line ?? 0) || (a.column ?? 0) - (b.column ?? 0));

  process.stdout.write(JSON.stringify(findings, null, 2) + '\n');

  const tally = (key) => findings.reduce((o, f) => ((o[f[key]] = (o[f[key]] || 0) + 1), o), {});
  const fmt = (o) => Object.entries(o).map(([k, v]) => `${k}=${v}`).join(' ') || 'none';
  warn(`${findings.length} finding(s) across ${files.length} file(s)`);
  warn(`  by source:   ${fmt(tally('source'))}`);
  warn(`  by severity: ${fmt(tally('severity'))}`);

  if (hadToolError) process.exit(2);
  process.exit(findings.length > 0 ? 1 : 0);
}

main();
