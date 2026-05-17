# chat-history-search

A Claude Code skill that searches your local chat history JSONL files to recall decisions, code patterns, and context from past sessions.

Claude Code stores every conversation as JSONL in `~/.claude/projects/`. This skill makes that archive searchable from inside any new session — the agent can grep its own past and pull the relevant Q+A exchange back into context.

## Install

Copy the `chat-history-search/` folder into your `~/.claude/skills/` directory:

```bash
git clone https://github.com/mariusSil/chat-history-search-plugin.git
mkdir -p ~/.claude/skills/chat-history-search
cp -r chat-history-search-plugin/{SKILL.md,scripts} ~/.claude/skills/chat-history-search/
```

## Usage

Once installed, Claude triggers the skill automatically when you ask things like:

- "Did we discuss X before?"
- "How did we solve Y?"
- "What was decided about Z?"

Or call the script directly:

```bash
python3 ~/.claude/skills/chat-history-search/scripts/search_chats.py "query" --limit 5
```

### Options

| Flag | Default | Use |
|------|---------|-----|
| `--limit N` | 10 | Max results |
| `--since N` | all | Only files modified in last N days |
| `--project SUBSTR` | all | Filter by project dir substring |
| `--user-only` | off | Only match user messages |
| `--verbose` | off | 1200 chars per message instead of 500 |
| `--context N` | 1 | Q+A pairs of context around each match |

See [SKILL.md](SKILL.md) for full guidance.

## How it works

1. `grep -ril` across all JSONL session files (fast even with thousands of sessions)
2. Parse matching files line-by-line as JSON
3. Find the matching message, extract the surrounding user→assistant exchange
4. Sort newest-first, truncate, print

No embeddings, no vector store, no index — just the filesystem.

## Requirements

- Python 3.8+
- Claude Code with local session files in `~/.claude/projects/`

## License

MIT
