#!/usr/bin/env python3
"""
Search through Claude Code local chat history JSONL files.

Usage:
  python3 search_chats.py "query string" [options]

Options:
  --limit N          Max results to return (default: 10)
  --context N        Lines of context around match (default: 1 = show Q+A pair)
  --project PATTERN  Filter by project dir substring (e.g. "AI-Organisation")
  --since DAYS       Only search files modified in last N days
  --user-only        Only search user messages (skip assistant)
  --verbose          Show full message text (default: truncated to 500 chars)
"""

import json
import sys
import os
import re
import argparse
from pathlib import Path
from datetime import datetime, timedelta, timezone
import subprocess

PROJECTS_DIR = Path.home() / ".claude" / "projects"

def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("query", help="Search query (supports regex)")
    p.add_argument("--limit", type=int, default=10)
    p.add_argument("--context", type=int, default=1, help="Q+A pairs of context (1 = just the matching exchange)")
    p.add_argument("--project", default=None, help="Filter by project path substring")
    p.add_argument("--since", type=int, default=None, help="Only files modified in last N days")
    p.add_argument("--user-only", action="store_true")
    p.add_argument("--verbose", action="store_true")
    return p.parse_args()

def extract_text(content):
    """Extract plain text from message content (str or list of blocks)."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict):
                if block.get("type") == "text":
                    parts.append(block.get("text", ""))
                elif block.get("type") == "tool_result":
                    inner = block.get("content", "")
                    parts.append(extract_text(inner))
        return " ".join(parts)
    return str(content)

def grep_files(query, project_filter=None, since_days=None):
    """Use grep to quickly find JSONL files containing the query."""
    search_root = str(PROJECTS_DIR)

    cmd = ["grep", "-ril", "--include=*.jsonl", query, search_root]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        files = [Path(f) for f in result.stdout.strip().split("\n") if f]
    except subprocess.TimeoutExpired:
        print("WARNING: grep timed out, falling back to limited search", file=sys.stderr)
        files = list(PROJECTS_DIR.rglob("*.jsonl"))[:100]

    if project_filter:
        files = [f for f in files if project_filter.lower() in str(f).lower()]

    if since_days:
        cutoff = datetime.now().timestamp() - (since_days * 86400)
        files = [f for f in files if f.stat().st_mtime > cutoff]

    return files

def parse_session(filepath):
    """Parse a JSONL file into a list of message dicts."""
    messages = []
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                    if obj.get("type") in ("user", "assistant"):
                        messages.append(obj)
                except json.JSONDecodeError:
                    continue
    except Exception:
        pass
    return messages

def project_name_from_path(filepath):
    """Convert ~/.claude/projects/dir-name/session.jsonl → readable project name."""
    parts = filepath.parts
    projects_idx = next((i for i, p in enumerate(parts) if p == "projects"), None)
    if projects_idx and projects_idx + 1 < len(parts):
        raw = parts[projects_idx + 1]
        # Strip leading OS path prefix: -Users-<name>- or -home-<name>- → ~/
        home_prefix = f"-Users-{Path.home().name}-"
        home_prefix_linux = f"-home-{Path.home().name}-"
        for prefix in (home_prefix, home_prefix_linux):
            if raw.startswith(prefix):
                raw = raw[len(prefix):]
                break
        clean = "~/" + raw.replace("-", "/")
        return clean
    return str(filepath.parent.name)

def search_messages(messages, query, user_only=False):
    """Find messages matching query, return list of (index, message)."""
    pattern = re.compile(query, re.IGNORECASE)
    matches = []
    for i, msg in enumerate(messages):
        if user_only and msg.get("type") != "user":
            continue
        content = msg.get("message", {}).get("content", "")
        text = extract_text(content)
        if pattern.search(text):
            matches.append((i, msg))
    return matches

def format_result(filepath, messages, match_idx, match_msg, context_pairs, verbose):
    """Format a single search result with context."""
    project = project_name_from_path(filepath)
    session_id = match_msg.get("sessionId", "?")[:8]
    ts = match_msg.get("timestamp", "")
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        ts_fmt = dt.strftime("%Y-%m-%d %H:%M")
    except Exception:
        ts_fmt = ts[:16]

    # Find the Q+A exchange: go back to find the user message before this match
    # and forward to find the assistant response
    start = match_idx
    # Walk back to find user message
    for j in range(match_idx, max(-1, match_idx - 3), -1):
        if messages[j].get("type") == "user":
            start = j
            break

    # Collect the exchange: from start, take up to (1 + context_pairs * 2) messages
    end = min(len(messages), start + 2 + (context_pairs - 1) * 2)
    exchange = messages[start:end]

    lines = []
    lines.append(f"\n{'='*70}")
    lines.append(f"  Project : {project}")
    lines.append(f"  Session : {session_id}  |  {ts_fmt}")
    lines.append(f"{'='*70}")

    for msg in exchange:
        role = msg.get("type", "?").upper()
        content = msg.get("message", {}).get("content", "")
        text = extract_text(content).strip()
        if not text:
            continue
        max_len = 1200 if verbose else 500
        if len(text) > max_len:
            text = text[:max_len] + f"... [+{len(text)-max_len} chars]"
        lines.append(f"\n[{role}]\n{text}")

    return "\n".join(lines)

def main():
    args = parse_args()

    print(f"Searching {PROJECTS_DIR} for: '{args.query}'", file=sys.stderr)

    files = grep_files(args.query, args.project, args.since)
    print(f"Found {len(files)} matching files", file=sys.stderr)

    results = []
    seen_sessions = set()

    for filepath in files:
        if len(results) >= args.limit:
            break

        session_id = filepath.stem
        if session_id in seen_sessions:
            continue
        seen_sessions.add(session_id)

        messages = parse_session(filepath)
        matches = search_messages(messages, args.query, args.user_only)

        for match_idx, match_msg in matches:
            if len(results) >= args.limit:
                break
            result = format_result(filepath, messages, match_idx, match_msg, args.context, args.verbose)
            ts = match_msg.get("timestamp", "0")
            results.append((ts, result))

    # Sort by most recent first
    results.sort(key=lambda x: x[0], reverse=True)

    if not results:
        print(f"\nNo results found for '{args.query}'")
        print("Try: broader terms, --since 90, or remove --user-only flag")
        return

    print(f"\n{'#'*70}")
    print(f"  CHAT HISTORY SEARCH — '{args.query}'")
    print(f"  Found {len(results)} result(s) | showing most recent first")
    print(f"{'#'*70}")

    for _, result in results:
        print(result)

    print(f"\n{'='*70}")
    print(f"Done. {len(results)} result(s) shown. Use --limit N for more, --verbose for full text.")

if __name__ == "__main__":
    main()
