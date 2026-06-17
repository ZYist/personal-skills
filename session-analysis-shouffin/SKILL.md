---
name: session-analysis-shouffin
description: Analyzes a local Claude Code session transcript (.jsonl) and writes a readable Markdown report — a chronological conversation replay plus full tool-call detail. Invoke when the user wants to review what happened in a session (what was said and which tools were called), summarize a past session, or audit tool usage. Zero-config: analyzes the current project's most recent session by default.
---

# Session Analyst

Turn an opaque `~/.claude/projects/<slug>/*.jsonl` transcript into a clear,
reviewable **Markdown report** of what was said and which tools were called —
without leaving Claude Code and without any GUI.

## When to use

- "Show me what happened in my last session."
- "Which tools did I call in that conversation?"
- "Make a readable summary/report of this session."
- Review or audit tool usage for a past session.

## How to run

Run the parser with **Node** (the only runtime required — no `npm install`):

```
node analyze-session.js
```

That's it. With **no arguments**, it analyzes the **current project's most
recent session**:

1. Derives the transcript dir from the current working directory by encoding the
   path to the `~/.claude/projects/<slug>` form (every non-`[A-Za-z0-9]` char →
   `-`, e.g. `D:\workspace\调用分析skill` → `D--workspace-----skill`).
2. Selects the newest-by-mtime `.jsonl` in that dir.
3. Parses it and writes the report.

### Explicit path override

To analyze a specific session instead of the auto-selected one, pass its path:

```
node analyze-session.js ~/.claude/projects/<slug>/<session-id>.jsonl
```

## Output

- A Markdown report written to **`./session-analysis/<YYYY-MM-DD>_<short-id>.md`**
  (relative to the cwd), containing:
  - **Conversation** — chronological replay: 👤 user prompts, 🤖 assistant text,
    interleaved tool calls/results, each with timestamps.
  - **Tool Call Summary** — per-tool counts of total / successes / failures.
  - **Tool Call Detail** — every `tool_use` with its full input and result
    (outputs truncated ~50 lines, inputs ~200 lines, with a `+N more lines`
    marker). Failed calls are marked **✗**.
- A one-line stdout summary: `Wrote <path> — N messages, M tool calls (S ok, F errors).`
  (When auto-targeting, it first prints which session it selected.)

## Requirements & guarantees

- **Node.js** (v18+; developed on v24). **No dependencies** — Node stdlib only,
  so it runs anywhere Node runs.
- **Local-only:** reads only `~/.claude/projects/`. No network, no telemetry.
- **Display only:** never executes or re-runs anything from the transcript.

## Notes

- The parser, renderer, and CLI are all in the single file `analyze-session.js`
  alongside this `SKILL.md`.
- Thinking blocks render inside a default-folded `<details>` to keep the
  conversation replay uncluttered.
