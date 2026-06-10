#!/usr/bin/env node
// Post-tool-use hook. Runs `ruff check --fix` on edited .py files and reports lint issues.
// Never aborts the agent — ruff failures are warnings, not blocks.
// Uses spawnSync with an argv array (no shell) to avoid command injection.
"use strict";

const { spawnSync } = require("child_process");
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
  const toolName = input.tool_name || "";
  if (!["Edit", "Write", "MultiEdit"].includes(toolName)) process.exit(0);

  const files = new Set();
  const add = (p) => {
    if (typeof p === "string" && p.endsWith(".py") && !p.includes("__pycache__")) {
      files.add(p);
    }
  };
  add(input.file_path);
  if (Array.isArray(input.edits)) for (const e of input.edits) add(e.file_path);
  if (!files.size) process.exit(0);

  const repoRoot = process.env.CLAUDE_PROJECT_DIR || path.resolve(__dirname, "..", "..");
  const issues = [];
  for (const f of files) {
    const r = spawnSync("ruff", ["check", "--fix", "--no-cache", f], {
      cwd: repoRoot,
      encoding: "utf8",
      // No `shell: true` — ruff is found via PATH (Node resolves .exe on Windows).
    });
    if (r.status !== 0) {
      issues.push({ file: f, stdout: (r.stdout || "").trim(), stderr: (r.stderr || "").trim() });
    }
  }

  if (issues.length) {
    let msg = "\nruff found issues (non-blocking):\n";
    for (const i of issues) {
      msg += `\n--- ${i.file} ---\n${i.stdout || i.stderr}\n`;
    }
    process.stdout.write(msg);
  }
  process.exit(0);
});
