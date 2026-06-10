---
name: security-review
description: Multi-agent security audit pipeline — scan → verify → report. Targets OWASP API Top 10 and project-specific rules.
phases: [Scan, Verify, Report]
---

# security-review workflow

Invoke via `/security-audit` or directly. Scans auth, secrets, CORS, rate limits, webhooks, and request handling.

## Phase 1 — Scan (subagent: `security-auditor`)

**Goal**: surface every potential issue.

- Read the surface: full repo, a specific directory, a PR diff, or a single route (per the argument).
- Trace data flow per route: request → middleware → router → service → DB / external.
- For each `security-auditor` check (BLOCKER / MAJOR / MINOR), report `file:line` + problem + fix.
- Run hardcoded-secret regex pass on all source files.
- Cross-check webhook handlers (`polar_routes`, `stripe_routes`) for signature verification.

**Exit criteria**: raw findings list present.

## Phase 2 — Verify

**Goal**: drop false positives, merge duplicates, re-rank.

- For each finding, verify the claim by reading the actual line. Some "hardcoded secrets" are Pydantic field defaults — drop them.
- Merge near-duplicate findings (same root cause, multiple sites).
- Re-rank against OWASP API Top 10 (2023):
  - API1 BOLA, API2 auth, API3 BOPLA, API4 resource consumption, API5 function-level auth, API6 sensitive flow, API7 SSRF, API8 misconfig, API9 inventory, API10 unsafe third-party consumption.
- Confirm no finding cites `.env.example` (those are placeholders, not secrets).

**Exit criteria**: deduped, ranked findings.

## Phase 3 — Report

**Goal**: present a single severity-grouped report the user can act on.

Format:

```
## Security audit

Total: <N> findings (<B> blocker, <M> major, <m> minor)

### BLOCKER
- file:line — <one-line problem>. <one-line fix>.
  ```suggestion
  <exact replacement, ≤20 lines>
  ```

### MAJOR
- ...

### MINOR
- ...

### OWASP coverage
- API1 (BOLA): <findings or "clean">
- API2 (auth): ...
```

**Apply?** ask the user. On `y`, apply BLOCKER + MAJOR only. Re-scan after.

## What this workflow does NOT do

- Does not run exploit code.
- Does not propose adding a WAF or external scanner.
- Does not change JWT secret rotation, refresh-token lifetime, or auth flow architecture — those are policy decisions, surfaced to the user.
