#!/usr/bin/env node
// check-tex.mjs — Lint LaTeX prose with textlint (latex2e plugin) and emit a merged JSON
// array of findings on stdout, a human summary on stderr.
//
// Usage:  node check-tex.mjs <file-or-dir> [more files/dirs...]
//
// Findings shape (matches the check-markdown skill):
//   { file, line, column, severity, source, rule, message, fixable }
//     severity : "error" | "warning" | "suggestion"
//     source   : "textlint"
//
// Why LaTeX is its own skill:
//   - Vale has no LaTeX parser (errata-ai/vale#54) — it would flag markup as prose.
//   - `@textlint-rule/gramma` (the LanguageTool bridge) crashes on the latex2e AST.
// So this skill checks style/terminology via textlint's `latex2e` parser, which lints only
// prose nodes and ignores commands/math. For real grammar checking on LaTeX, use
// `ltex-cli` — see references/ltex.md.
//
// Exit codes: 0 = clean, 1 = findings reported, 2 = setup/tool failure.

import { spawnSync } from 'node:child_process';
import { existsSync, readdirSync, statSync } from 'node:fs';
import { dirname, extname, join, resolve } from 'node:path';
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

function ensureNodeModules() {
  if (existsSync(join(assetsDir, 'node_modules')) && existsSync(textlintBin)) return true;
  warn('textlint dependencies missing — running `npm install` (one-time)...');
  const res = runBin('npm', ['install', '--no-audit', '--no-fund'], { cwd: assetsDir, stdio: 'inherit' });
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

  const findings = [];
  for (const file of files) findings.push(...runTextlint(file));

  findings.sort((a, b) =>
    a.file.localeCompare(b.file) || (a.line ?? 0) - (b.line ?? 0) || (a.column ?? 0) - (b.column ?? 0));

  process.stdout.write(JSON.stringify(findings, null, 2) + '\n');

  const tally = (key) => findings.reduce((o, f) => ((o[f[key]] = (o[f[key]] || 0) + 1), o), {});
  const fmt = (o) => Object.entries(o).map(([k, v]) => `${k}=${v}`).join(' ') || 'none';
  warn(`${findings.length} finding(s) across ${files.length} file(s)`);
  warn(`  by severity: ${fmt(tally('severity'))}`);
  warn('note: grammar not checked here — run ltex-cli for LaTeX grammar (see references/ltex.md).');

  if (hadToolError) process.exit(2);
  process.exit(findings.length > 0 ? 1 : 0);
}

main();
