#!/usr/bin/env node
// SessionStart hook. Prints a short, dense project grounding line so the model has immediate context.
// Uses spawnSync (argv array, no shell) and fs.readdirSync — no string-interpolated commands.
"use strict";

const { spawnSync } = require("child_process");
const fs = require("fs");
const path = require("path");

const repoRoot = process.env.CLAUDE_PROJECT_DIR || path.resolve(__dirname, "..", "..");

function safeRun(cmd, args) {
  try {
    const r = spawnSync(cmd, args, { cwd: repoRoot, encoding: "utf8" });
    if (r.status !== 0) return "(unavailable)";
    return (r.stdout || "").trim();
  } catch {
    return "(unavailable)";
  }
}

const lastCommit = safeRun("git", ["log", "-1", "--oneline"]);
const branch = safeRun("git", ["rev-parse", "--abbrev-ref", "HEAD"]);

let routerCount = "(?)";
try {
  const entries = fs.readdirSync(path.join(repoRoot, "app", "routers"));
  routerCount = String(entries.filter((n) => n.endsWith(".py")).length);
} catch {}

let alembicHead = "(no migrations)";
try {
  const r = spawnSync("alembic", ["heads"], { cwd: repoRoot, encoding: "utf8" });
  if (r.status === 0) {
    const out = (r.stdout || "").trim();
    if (out) alembicHead = out.split("\n")[0];
  }
} catch {}

let pythonVer = "?";
try {
  const r = spawnSync("python", ["--version"], { encoding: "utf8" });
  if (r.status === 0) pythonVer = (r.stdout || r.stderr || "").replace(/^Python\s+/, "").trim();
} catch {}

const lines = [
  "InsightPilot backend (FastAPI / Python " + pythonVer + ")",
  "branch: " + branch,
  "last commit: " + lastCommit,
  "routers: " + routerCount,
  "alembic head: " + alembicHead,
];
process.stdout.write(lines.join("\n") + "\n");
process.exit(0);
