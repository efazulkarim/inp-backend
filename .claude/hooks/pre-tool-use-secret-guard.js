#!/usr/bin/env node
// Pre-tool-use hook. Blocks edits to .env files and detects secret patterns in file contents.
// Reads tool input from stdin as JSON, exits 0 (allow) or 2 (block with reason).
//
// Hook contract: stdout message is shown to the user. Exit code 0 = allow, 2 = block.
"use strict";

const SECRET_PATTERNS = [
  { name: "Anthropic/OpenAI", re: /\bsk-[A-Za-z0-9_-]{20,}\b/g },
  { name: "Stripe live", re: /\bsk_live_[A-Za-z0-9]{20,}\b/g },
  { name: "Stripe test", re: /\bsk_test_[A-Za-z0-9]{20,}\b/g },
  { name: "Google API key", re: /\bAIza[0-9A-Za-z_-]{30,}\b/g },
  { name: "GitHub PAT", re: /\bghp_[A-Za-z0-9]{30,}\b/g },
  { name: "GitHub fine-grained", re: /\bgithub_pat_[A-Za-z0-9_]{50,}\b/g },
  { name: "Polar access token", re: /\bpolar_oat_[A-Za-z0-9_-]{20,}\b/g },
  { name: "JWT (looks like real)", re: /\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b/g },
  { name: "Private key block", re: /-----BEGIN (?:RSA |EC |OPENSSH |DSA |PGP )?PRIVATE KEY-----/g },
  { name: "SECRET_KEY = literal", re: /\bSECRET_KEY\s*=\s*["'][^"'\s]{16,}["']/g },
];

const ENV_BASENAMES = new Set([".env", ".env.local", ".env.development", ".env.production", ".env.test"]);
const ENV_SUFFIX_RE = /^\.env(\.[A-Za-z0-9_.-]+)?$/;

function extractTargets(toolName, input) {
  const targets = [];
  const push = (path, content) => {
    if (typeof path === "string" && path.length) {
      targets.push({ path, content: content ?? null });
    }
  };
  if (!input || typeof input !== "object") return targets;
  if (toolName === "Write" || toolName === "Edit" || toolName === "MultiEdit") {
    push(input.file_path, input.content);
    if (Array.isArray(input.edits)) {
      for (const e of input.edits) push(e.file_path, e.new_text);
    }
  }
  return targets;
}

function basename(p) {
  if (!p) return "";
  const norm = p.replace(/\\/g, "/");
  const i = norm.lastIndexOf("/");
  return i === -1 ? norm : norm.slice(i + 1);
}

function isEnvFile(p) {
  const base = basename(p);
  if (ENV_BASENAMES.has(base)) return true;
  if (ENV_SUFFIX_RE.test(base)) return base !== ".env.example";
  return false;
}

function findSecretHits(content) {
  const hits = [];
  if (typeof content !== "string" || !content) return hits;
  for (const { name, re } of SECRET_PATTERNS) {
    re.lastIndex = 0;
    const matches = content.match(re);
    if (matches && matches.length) {
      hits.push({ name, sample: matches[0].slice(0, 10) + "…" });
    }
  }
  return hits;
}

let raw = "";
process.stdin.setEncoding("utf8");
process.stdin.on("data", (chunk) => (raw += chunk));
process.stdin.on("end", () => {
  let input = {};
  try {
    input = raw.trim() ? JSON.parse(raw) : {};
  } catch (e) {
    process.exit(0);
  }

  const toolName = input.tool_name || "";
  const targets = extractTargets(toolName, input);
  if (!targets.length) process.exit(0);

  const reasons = [];
  for (const t of targets) {
    if (isEnvFile(t.path)) {
      reasons.push(`Refusing to edit env file: ${t.path}. Use .env.example for new keys.`);
      continue;
    }
    const hits = findSecretHits(t.content);
    for (const h of hits) {
      reasons.push(`Possible ${h.name} in ${t.path} (sample: ${h.sample}). Move to env var.`);
    }
  }

  if (reasons.length) {
    process.stderr.write("secret-guard blocked: " + reasons.join(" | ") + "\n");
    process.exit(2);
  }
  process.exit(0);
});
