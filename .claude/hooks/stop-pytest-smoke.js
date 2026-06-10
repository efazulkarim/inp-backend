#!/usr/bin/env node
// Stop hook. Smoke-runs the unit test suite when the session touched test-relevant files.
// Uses spawnSync with argv array (no shell) to avoid command injection.
"use strict";

const { spawnSync } = require("child_process");
const { spawnFileSync } = (() => {
  function spawnFileSync(cmd, args, opts) {
    const r = spawnSync(cmd, args, { ...opts, shell: false });
    if (r.error) throw r.error;
    if (r.status !== 0) {
      const e = new Error("non-zero exit: " + r.status);
      e.stdout = r.stdout;
      e.stderr = r.stderr;
      e.status = r.status;
      throw e;
    }
    return r.stdout;
  }
  return { spawnFileSync };
})();
const path = require("path");

let raw = "";
process.stdin.setEncoding("utf8");
process.stdin.on("data", (c) => (raw += c));
process.stdin.on("end", () => {
  let input = {};
  try {
    input = raw.trim() ? JSON.parse(raw) : {};
  } catch {
    process.exit(0);
  }

  const repoRoot = process.env.CLAUDE_PROJECT_DIR || path.resolve(__dirname, "..", "..");
  let changed = "";
  try {
    changed = spawnFileSync("git", ["diff", "--name-only", "HEAD"], { cwd: repoRoot, encoding: "utf8" });
  } catch {
    process.exit(0);
  }
  const touched = changed
    .split("\n")
    .map((s) => s.trim())
    .filter(Boolean);
  const relevant = touched.some(
    (p) => p.startsWith("app/") || p.startsWith("tests/") || p.startsWith("alembic/")
  );
  if (!relevant) process.exit(0);

  const r = spawnSync("pytest", ["-q", "-m", "unit", "--no-header", "--tb=line", "-x"], {
    cwd: repoRoot,
    encoding: "utf8",
    timeout: 85_000,
  });

  const tail = ((r.stdout || "") + "\n" + (r.stderr || "")).split("\n").slice(-30).join("\n");
  if (r.status === 0) {
    process.stdout.write(`\n[pytest-smoke] unit suite passed.\n${tail}\n`);
  } else {
    process.stdout.write(`\n[pytest-smoke] unit suite FAILED (exit ${r.status}).\n${tail}\n`);
  }
  process.exit(0);
});
