---
name: session-analysis-shouffin
description: "Analyzes a local Claude Code session transcript (.jsonl) and writes a readable Markdown report — a chronological conversation replay plus full tool-call detail. Invoke when the user wants to review what happened in a session (what was said and which tools were called), summarize a past session, or audit tool usage. Zero-config: analyzes the current project's most recent session by default."
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

## How to invoke

### Quick start — `/session-analysis-shouffin`

Type `/session-analysis-shouffin` in chat to analyze the **current project's
most recent session** and save the report to `./session-analysis/`. No arguments
needed — the skill auto-detects everything:

1. Derives the transcript dir from the current working directory by encoding the
   path to the `~/.claude/projects/<slug>` form (every non-`[A-Za-z0-9]` char →
   `-`, e.g. `D:\workspace\调用分析skill` → `D--workspace-----skill`).
2. Selects the newest-by-mtime `.jsonl` in that dir.
3. Parses it and writes the report.

### Manual invocation (same behavior)

```
node analyze-session.js
```

### Analyze a different session

To analyze a session other than the most recent one, the model should read the
target `.jsonl` from `~/.claude/projects/` and decide whether further processing
is needed based on the conversation context, rather than passing a path
argument.

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

## Troubleshooting (failure modes)

When the script exits non-zero or the report looks wrong, match the symptom
below and follow the column chain — first-line fix, then the fallback if it
still fails. The triggers mirror the script's real error paths.

| Symptom / trigger | First-line fix | If still failing |
|---|---|---|
| `No transcript directory found for this project` (cwd's `~/.claude/projects/<slug>` does not exist) | Verify cwd — the slug is derived from cwd (above); running from the right project dir usually fixes it | That project has never had a session on this machine; ask the user for an existing `.jsonl` absolute path: `node analyze-session.js <path>` |
| `No .jsonl sessions found` (dir exists but is empty) | That project's sessions were cleaned up; confirm with `ls ~/.claude/projects/<slug>/` | Use a different project's session, or ask the user for a `.jsonl` path |
| The auto-selected session is not the one the user wanted | zero-config picks the newest by mtime — confirm the target with the user first | By convention **do not pass a path arg**: list candidate `.jsonl` files in the dir, have the user pick, then pass that absolute path |
| Tool-call count is 0 / report looks sparse | The session may be mostly plain conversation — that is normal | Try another `.jsonl`; if parsing looks lossy, see the report's `## Fidelity Check` footnote |
| stdout shows `Fidelity: ⚠ N check(s) failed` | A count self-check mismatch — see the failing items in the report's `## Fidelity Check` footnote | Usually a parsing edge case (e.g. duplicate `tool_use_id`); the body is still readable — rerun the same `.jsonl` for exact counts |
| `node` missing or version < v18 | Install Node v18+ and rerun | If Node cannot be installed, hand-parse (following the script's logic), but you lose truncation, stats, and the fidelity self-check |

## Anti-patterns (do not)

Things the script already handles — doing them by hand only loses quality, or
breaks the run:

- **Do not** reinvent the parser. No hand-written `jq`/Node line-by-line
  `JSON.parse`, content-array flattening, or `tool_use`↔`tool_result` linking.
  `analyze-session.js` already encodes the slug lookup, id-pairing, truncation,
  stats, and fidelity self-check — calling it once beats any one-off script.
- **Do not** pass a directory path to the script. It takes a `.jsonl` **file**
  path (or zero args for auto-target); a directory makes `parseSession` fail.
- **Do not** pass a path argument when the user invokes
  `/session-analysis-shouffin` interactively. Convention is zero-arg auto-target,
  or the model reads a chosen `.jsonl` and passes its absolute path **only after
  confirming the target with the user**.
- **Do not** modify, move, or delete the source `.jsonl` — the tool is read-only
  / display-only.
- **Do not** execute or re-run any command found in the transcript — it is a
  record, not a script to replay.
- **Do not** ignore a `## Fidelity Check` footnote. It appears only when a count
  self-check failed, signaling the reported counts may be off.

## Notes

- The parser, renderer, and CLI are all in the single file `analyze-session.js`
  alongside this `SKILL.md`.
- Thinking blocks render inside a default-folded `<details>` to keep the
  conversation replay uncluttered.
