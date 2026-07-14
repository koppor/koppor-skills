#!/usr/bin/env node
// check-md.mjs — Lint Markdown with textlint + Vale (+ LanguageTool) and emit a single
// merged JSON array of findings on stdout, a human summary on stderr.
//
// Usage:  node check-md.mjs <file-or-dir> [more files/dirs...]
//
// Findings are normalized to one shape:
//   { file, line, column, severity, source, rule, message, fixable }
//     severity : "error" | "warning" | "suggestion"
//     source   : "textlint" | "vale" | "languagetool"
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
// For LaTeX (.tex) use the sibling `check-tex` skill — Vale cannot parse LaTeX and the
// gramma rule crashes on the LaTeX AST.
//
// Exit codes: 0 = clean, 1 = findings reported, 2 = setup/tool failure.

import { spawnSync } from 'node:child_process';
import { existsSync, readdirSync, statSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname, extname, join, resolve } from 'node:path';
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
  process.stderr.write(`check-md: ${msg}\n`);
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
  if (existsSync(join(assetsDir, 'node_modules')) && existsSync(textlintBin)) return true;
  warn('textlint dependencies missing — running `npm install` (one-time)...');
  const res = runBin('npm', ['install', '--no-audit', '--no-fund'], { cwd: assetsDir, stdio: 'inherit' });
  if (!res.ok || !existsSync(textlintBin)) {
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

// ── Main ─────────────────────────────────────────────────────────────────────
async function main() {
  const paths = process.argv.slice(2);
  if (paths.length === 0) {
    warn('usage: node check-md.mjs <file-or-dir> [...]');
    process.exit(2);
  }

  const files = collectFiles(paths);
  if (files.length === 0) {
    warn('no Markdown (.md/.markdown) files found. For LaTeX, use the check-tex skill.');
    process.exit(2);
  }

  if (!ensureNodeModules()) process.exit(2);

  const textlintConfig = await buildTextlintConfig();
  const valeUsable = ensureValeStyles();
  if (!valeUsable) warn('Vale not found on PATH — Markdown will be checked with textlint only.');

  const findings = [];
  for (const file of files) {
    findings.push(...runTextlint(file, textlintConfig));
    if (valeUsable) findings.push(...runVale(file));
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

main().catch((e) => {
  warn(`fatal: ${e.stack || e.message}`);
  process.exit(2);
});
