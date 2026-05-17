---
name: chat-history-search
description: Search through Claude Code local chat history JSONL files to find information from past conversations. Use when the user asks "did we discuss X before", "what did we decide about Y", "how did we solve Z", or when context from a previous session would be useful. Searches all local session files efficiently via grep + JSON parsing.
---

## Overview

Claude Code stores every conversation as JSONL files in `~/.claude/projects/<project-dir>/<session-id>.jsonl`. Each line is a JSON object with `type` (user/assistant), `message.content`, `timestamp`, `cwd`, and `sessionId`. The search script uses `grep -ril` for fast file filtering across all sessions, then parses matching files to extract Q+A exchange context.

## When to Use

- User asks about something discussed in a previous conversation
- User wants to recall a decision, code pattern, or answer from a past session
- Phrases like "did we talk about", "how did we solve", "what was decided about", "find past conversation about"
- Resuming context after a session gap without the original chat open

## How to Run

```bash
python3 ~/.claude/skills/chat-history-search/scripts/search_chats.py "QUERY" [OPTIONS]
```

### Key options

| Flag | Default | Use |
|------|---------|-----|
| `--limit N` | 10 | Max results to show |
| `--since N` | all time | Only files modified in last N days |
| `--project SUBSTR` | all projects | Filter by project dir path substring |
| `--user-only` | off | Only match user messages (not assistant) |
| `--verbose` | off | Show 1200 chars instead of 500 per message |
| `--context N` | 1 | Q+A pairs of exchange context to show |

### Query tips

- Single keyword is fastest and most reliable
- Regex is supported: `"invoice.*2024"`, `"stripe|paypal"`, `"deploy.*prod"`
- If exact phrase fails, try one distinctive word — grep requires exact substring match
- For multi-word topics, use the most unique single term first, then refine with `--project` or `--since`

### Typical workflows

**"What did we decide about the auth flow?"**
```bash
python3 ~/.claude/skills/chat-history-search/scripts/search_chats.py "auth" --project "my-app" --limit 5
```

**"How did we configure weasyprint?"**
```bash
python3 ~/.claude/skills/chat-history-search/scripts/search_chats.py "weasyprint" --limit 5 --verbose
```

**"Did we discuss Stripe integration before?"**
```bash
python3 ~/.claude/skills/chat-history-search/scripts/search_chats.py "Stripe" --limit 5 --since 60
```

**Search only a specific project:**
```bash
python3 ~/.claude/skills/chat-history-search/scripts/search_chats.py "deploy" --project "my-project" --limit 5
```

## Output Format

Results are sorted newest-first. Each result shows:
- Project path (human-readable, e.g. `~/Development/my-project`)
- Session ID (first 8 chars) + timestamp
- The Q+A exchange around the match (truncated to 500 chars by default)

## After Searching

Synthesize the results — extract the relevant decision, answer, or code snippet from the raw exchange and present it clearly. Don't dump raw output verbatim.

If 0 results:
1. Try a shorter or different keyword
2. Add `--since 180` to widen the time window
3. Check the correct project with `--project`
