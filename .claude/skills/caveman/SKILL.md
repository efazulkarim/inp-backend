---
name: caveman
description: No-op. Documents that caveman mode is wired globally via ~/.claude/settings.json (SessionStart + UserPromptSubmit hooks). Project files do not need to re-enable it. Switch level with /caveman lite|full|ultra or say "stop caveman".
---

# Caveman mode — `inp-backend`

Caveman mode is a **global** Claude Code plugin. It is configured in `~/.claude/settings.json` (outside this repo) and is not project-specific.

If the user asks to change the level, run `/caveman lite`, `/caveman full`, or `/caveman ultra`. To turn it off: `/caveman off` or "stop caveman" / "normal mode".

Project files in `.claude/` are not modified by caveman hooks; only the message rendering style changes.

For project-level rules on writing style, see `.claude/CLAUDE.md` ("What to defer to globals").
