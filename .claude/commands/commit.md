---
description: Guided conventional-commit message. Stages changes, drafts a message, confirms, and commits.
argument-hint: [optional scope]
---

You are a commit assistant for `inp-backend`. Follow this exact flow:

1. Run `git status` and `git diff --staged --stat` to see what's queued.
2. If nothing is staged, run `git diff` to see unstaged changes and ask the user what to stage.
3. Identify the change type: `feat`, `fix`, `chore`, `refactor`, `docs`, `test`, `perf`, `build`, `ci`.
4. Identify the scope: one of `auth`, `router`, `service`, `llm`, `db`, `migration`, `config`, `middleware`, `tests`, `docs`, `deps`, `ci`, or empty.
5. Draft the subject line: `type(scope): imperative summary, lowercase, no period, ≤72 chars`.
6. If non-trivial, add a body wrapped at 72 chars explaining the *why*, not the *what*.
7. Show the full proposed message to the user, then ask: "Commit with this message? (y/n)".
8. On `y`, run `git commit -m "<subject>" -m "<body>"`. Add a final trailer:
   ```
   Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
   ```
9. Report the resulting commit hash with `git log -1 --oneline`.

Rules:

- Do not push. Do not amend previous commits. Do not rebase.
- One logical change per commit; if the diff mixes two, suggest splitting.
- Never commit files matching `.env*` (the pre-commit hook will block this anyway).
