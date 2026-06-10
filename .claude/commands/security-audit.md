---
description: Run the security-review skill chain: scan → verify → report. Audit auth, secrets, CORS, rate limits, webhooks.
argument-hint: [optional path or glob]
---

You are invoking the **security-review** workflow. The workflow file is `.claude/workflows/security-review.md` — read it first, then execute its phases in order.

Argument: optional path/glob. If absent, audit the full repo.

Execution:

1. **Scan** — invoke the `security-auditor` subagent on the target. It produces a severity-tagged findings list.
2. **Verify** — cross-check findings against OWASP API Top 10 (2023). Drop false positives. Merge duplicates.
3. **Report** — output a single severity-grouped list. Include:
   - Total findings by severity.
   - Each finding: `file:line` + one-line problem + one-line fix.
   - For BLOCKER/MAJOR, the exact remediation (one snippet, ≤20 lines).
4. **Apply** — ask "Apply the BLOCKER + MAJOR fixes? (y/n)". On `y`, apply and re-run the scan.

Project rules enforced (from `.claude/rules/auth-security.md` and `security-and-hardening` skill):

- Webhook handlers always verify signature (Polar `webhook-signature`, Stripe `stripe-signature`).
- `SECRET_KEY` and provider keys come from env, never hardcoded.
- `JWT_ALGORITHM` is pinned to HS256 (or HS384/HS512).
- CORS `allowed_origins` is an explicit list, not `*` in any non-dev env.
- `SecurityHeadersMiddleware` is innermost; `RateLimitingMiddleware` is outermost.
- Webhooks are exempt from rate limiting.

Do not run exploit code. This is static review.
