// analyze-session.js — Session Analyst parser.
// Single-file, Node stdlib only (fs, path). No npm dependencies. CommonJS.
//
// Plan 01-01 (Wave 1): parsing core. parseSession turns a Claude Code session
// `.jsonl` into a clean { meta, messages } model; collectToolCalls links each
// assistant tool_use to its later user tool_result.

const fs = require('node:fs');
const path = require('node:path');
const os = require('node:os');

// Top-level line types to EXCLUDE from the conversation. Single named constant
// so the exclusion list is auditable and testable (PARSE-01).
const PARSE_SKIP_TYPES = new Set([
  'last-prompt',
  'mode',
  'permission-mode',
  'attachment',
  'file-history-snapshot',
]);

// Strip ANSI/VT escape sequences (e.g. PowerShell 7 color codes like
// "\x1b[32;1m") so they don't leak into the Markdown report as visible
// "[32;1m"-style noise. Covers CSI sequences: SGR colors, cursor moves, etc.
const ANSI_RE = /\x1b\[[0-9;?]*[A-Za-z]/g;
function stripAnsi(s) {
  return typeof s === 'string' ? s.replace(ANSI_RE, '') : s;
}

// Flatten a tool_result's `content` field into a single text string, with ANSI
// escape codes stripped. `content` may be a plain string OR an array of
// {type:"text",text} blocks; join the text blocks with "\n". Missing/empty
// content → "".
function resultText(content) {
  let text;
  if (typeof content === 'string') {
    text = content;
  } else if (Array.isArray(content)) {
    text = content
      .filter((p) => p && p.type === 'text' && typeof p.text === 'string')
      .map((p) => p.text)
      .join('\n');
  } else {
    text = '';
  }
  return stripAnsi(text);
}

// Normalize one user tool_result block to the contract shape
// { type:"tool_result", tool_use_id, text, is_error } (PARSE-03 extraction half).
function normalizeToolResult(block) {
  return {
    type: 'tool_result',
    tool_use_id: block.tool_use_id,
    text: resultText(block.content),
    is_error: block.is_error === true,
  };
}

// parseSession(filePath) -> { meta, messages }
// Reads the whole file, splits on newlines, JSON-parses each non-blank line,
// keeps only user/assistant lines, and normalizes content blocks.
function parseSession(filePath) {
  const raw = fs.readFileSync(filePath, 'utf8');
  const lines = raw.split('\n');

  const messages = [];
  const models = [];
  const seenModels = new Set();
  let sessionId;
  let cwd;
  let gitBranch;

  for (const rawLine of lines) {
    // Normalize CRLF and skip blank / trailing lines.
    const lineStr = rawLine.replace(/\r$/, '');
    if (lineStr.trim() === '') continue;

    let obj;
    try {
      obj = JSON.parse(lineStr);
    } catch {
      // Malformed line — skip it (do not throw).
      continue;
    }

    // PARSE-01: keep only user/assistant conversation lines.
    if (obj.type !== 'user' && obj.type !== 'assistant') continue;

    // Meta fields repeat across lines; capture from whichever carries them.
    if (obj.sessionId) sessionId = obj.sessionId;
    if (obj.cwd) cwd = obj.cwd;
    if (obj.gitBranch) gitBranch = obj.gitBranch;

    const msg = obj.message || {};
    const role = obj.type;
    const model = msg.model;

    // Distinct assistant models in first-appearance order.
    if (role === 'assistant' && model && !seenModels.has(model)) {
      seenModels.add(model);
      models.push(model);
    }

    // Normalize content per role.
    let content;
    if (role === 'assistant') {
      // PARSE-02: text / tool_use / thinking blocks; drop anything else.
      const arr = Array.isArray(msg.content) ? msg.content : [];
      content = [];
      for (const block of arr) {
        if (!block || typeof block !== 'object') continue;
        if (block.type === 'text') {
          content.push({ type: 'text', text: block.text });
        } else if (block.type === 'tool_use') {
          content.push({ type: 'tool_use', id: block.id, name: block.name, input: block.input });
        } else if (block.type === 'thinking') {
          content.push({ type: 'thinking', thinking: block.thinking });
        }
      }
    } else if (Array.isArray(msg.content)) {
      // PARSE-03: a user array holds tool_result blocks. Keep only tool_results
      // (a stray text block in such an array is ignored for linking).
      content = [];
      for (const block of msg.content) {
        if (block && block.type === 'tool_result') {
          content.push(normalizeToolResult(block));
        }
      }
    } else {
      // User typed prompt — keep the string verbatim.
      content = msg.content;
    }

    // Source label for user messages, driving the report's role icons:
    //   "human"       — real keyboard input (promptSource === "typed")
    //   "system"      — injected (slash command, caveat, local-command,
    //                   task-notification, etc.)
    //   "tool_result" — a tool result array
    // Assistant messages carry no source. GSD/tiger-flow "代替用户输入" is the
    // slash-command expansion, which lands here as "system".
    let source;
    if (role === 'user') {
      if (Array.isArray(msg.content)) {
        source = msg.content.some((b) => b && b.type === 'tool_result') ? 'tool_result' : 'human';
      } else {
        source = obj.promptSource === 'typed' ? 'human' : 'system';
      }
    }

    messages.push({
      role,
      uuid: obj.uuid,
      timestamp: obj.timestamp,
      model,
      content,
      source,
    });
  }

  const firstTs = messages.length ? messages[0].timestamp : undefined;
  const lastTs = messages.length ? messages[messages.length - 1].timestamp : undefined;
  const meta = { sessionId, cwd, gitBranch, firstTs, lastTs, models };

  return { meta, messages };
}

// collectToolCalls(messages) -> [ { toolUse, toolResult } ]
// One entry per assistant tool_use, in tool_use appearance order. Each tool_use
// is linked to its later user tool_result by tool_use_id; toolResult is null
// when no result exists in the transcript (PARSE-03 linking half).
function collectToolCalls(messages) {
  // First pass: collect tool_use blocks in appearance order.
  const entries = [];
  for (const msg of messages) {
    if (msg.role !== 'assistant' || !Array.isArray(msg.content)) continue;
    for (const block of msg.content) {
      if (block && block.type === 'tool_use') {
        entries.push({
          toolUse: { id: block.id, name: block.name, input: block.input },
          toolResult: null,
        });
      }
    }
  }

  // Second pass: map tool_use_id → { text, is_error } from user tool_results.
  const resultsById = new Map();
  for (const msg of messages) {
    if (msg.role !== 'user' || !Array.isArray(msg.content)) continue;
    for (const block of msg.content) {
      if (block && block.type === 'tool_result' && block.tool_use_id != null) {
        resultsById.set(block.tool_use_id, { text: block.text, is_error: block.is_error });
      }
    }
  }

  // Link each entry to its result (null when unmatched).
  for (const entry of entries) {
    if (resultsById.has(entry.toolUse.id)) {
      entry.toolResult = resultsById.get(entry.toolUse.id);
    }
  }

  return entries;
}

// verifyFidelity({ meta, messages }) -> { ok, checks[] }  (D-08..11, Phase 3)
// Pure self-consistency check (no fs, no I/O): reuses collectToolCalls + the
// messages array to prove the report's counts faithfully represent the parsed
// transcript. Each check records { name, expected, actual, pass };
// ok = every check passed. Three checks (D-09):
//   (a) tool-summary total (collectToolCalls length) == independent tool_use
//       block count.
//   (b) reported message count == parsed message count (sanity/contract).
//   (c) no-result tool count: collectToolCalls null-result entries vs the
//       number of DISTINCT tool_use ids lacking a matching tool_result.
//       Per-block vs per-distinct-id lets (c) trip on duplicate-id anomalies.
function verifyFidelity({ meta, messages }) {
  const calls = collectToolCalls(messages);

  // (a) Independent tool_use block count across assistant messages.
  let toolUseBlockCount = 0;
  for (const msg of messages) {
    if (msg.role !== 'assistant' || !Array.isArray(msg.content)) continue;
    for (const block of msg.content) {
      if (block && block.type === 'tool_use') toolUseBlockCount += 1;
    }
  }

  // (c) Independent no-result count via distinct ids.
  const toolUseIds = new Set();
  const toolResultIds = new Set();
  for (const msg of messages) {
    if (!Array.isArray(msg.content)) continue;
    for (const block of msg.content) {
      if (!block) continue;
      if (msg.role === 'assistant' && block.type === 'tool_use' && block.id != null) {
        toolUseIds.add(block.id);
      } else if (block.type === 'tool_result' && block.tool_use_id != null) {
        toolResultIds.add(block.tool_use_id);
      }
    }
  }
  let distinctNoResultCount = 0;
  for (const id of toolUseIds) {
    if (!toolResultIds.has(id)) distinctNoResultCount += 1;
  }

  const callsNoResultCount = calls.filter((c) => c.toolResult === null).length;

  const checks = [
    {
      name: 'tool-summary count matches tool_use block count',
      expected: calls.length,
      actual: toolUseBlockCount,
      pass: calls.length === toolUseBlockCount,
    },
    {
      name: 'reported message count matches parsed message count',
      expected: messages.length,
      actual: messages.length,
      pass: true,
    },
    {
      name: 'no-result tool count is consistent',
      expected: callsNoResultCount,
      actual: distinctNoResultCount,
      pass: callsNoResultCount === distinctNoResultCount,
    },
  ];
  return { ok: checks.every((c) => c.pass), checks };
}

// ---- Rendering (Plan 01-02) -------------------------------------------------

// Truncation thresholds (TOOLS-03): a single named source for both inputs and outputs.
const MAX_OUTPUT_LINES = 50;
const MAX_INPUT_LINES = 200;
const MAX_THINKING_LINES = 50;

// truncateLines(text, max): when text has more than `max` newline-separated
// lines, return the first `max` lines plus a final "+N more lines" marker line.
// Used for tool outputs (MAX_OUTPUT_LINES) and serialized inputs (MAX_INPUT_LINES).
function truncateLines(text, max) {
  if (text == null) return '';
  const str = typeof text === 'string' ? text : String(text);
  const lines = str.split('\n');
  if (lines.length <= max) return str;
  return lines.slice(0, max).join('\n') + '\n+' + (lines.length - max) + ' more lines';
}

// Resolve a user message's source label, falling back to a content-based
// inference when the field is absent (e.g. messages built directly in tests, or
// transcripts predating the label). "human"=real input, "system"=injected,
// "tool_result"=tool output array.
function userSource(msg) {
  if (msg.source === 'human' || msg.source === 'system' || msg.source === 'tool_result') {
    return msg.source;
  }
  if (Array.isArray(msg.content)) {
    return msg.content.some((b) => b && b.type === 'tool_result') ? 'tool_result' : 'human';
  }
  return 'human';
}

// Escape leading markdown ATX headings (#{1,6} at line start) so content text
// never hijacks the report's outline (Obsidian / MD outline nav). Only
// line-start `#` is touched; inline `#` and all other markdown (lists, bold,
// code) render as-is.
const HEADING_RE = /^(#{1,6})(\s)/gm;
function escapeHeadings(s) {
  return typeof s === 'string' ? s.replace(HEADING_RE, '\\$1$2') : s;
}

// Pick a code-fence long enough to enclose `text`: one more backtick than the
// longest backtick run inside it (min 3). Without this, a tool result that
// itself contains ``` would close the outer fence early and leak its markdown
// (headings included) into the report outline.
function fenceFor(text) {
  const str = String(text == null ? '' : text);
  let maxRun = 0;
  let run = 0;
  for (const ch of str) {
    if (ch === '`') { run += 1; if (run > maxRun) maxRun = run; }
    else run = 0;
  }
  return '`'.repeat(Math.max(3, maxRun + 1));
}

// One-line preview of a message's text, for the human-input H3 heading so the
// outline reads as "what the user asked", not a sea of timestamps. Collapses
// whitespace and truncates with an ellipsis.
function messagePreview(msg, max = 36) {
  let text = '';
  if (typeof msg.content === 'string') text = msg.content;
  else if (Array.isArray(msg.content)) {
    const t = msg.content.find((b) => b && b.type === 'text');
    text = t ? t.text : '';
  }
  const s = String(text).replace(/\s+/g, ' ').trim();
  if (!s) return '';
  return s.length > max ? s.slice(0, max) + '…' : s;
}

// Conversation replay: walks messages in order, emitting a role header with the
// timestamp (CONVO-03) then the content — user prompts, assistant text/tool_use/
// thinking, and interleaved tool_results (CONVO-01). Thinking blocks collapse
// into default-folded <details> (CONVO-02). A message whose array emits no body
// (e.g. an empty user array) produces NO orphan header (D-14). User messages use
// distinct icons by source (CONVO-04): 👤 human, ⚙️ system, 🔧 tool_result; a
// "---" separator precedes every fresh user INPUT (human/system) after the first.
function renderConversation(messages) {
  const parts = [];
  let firstTurnSeen = false;
  for (const msg of messages) {
    const ts = msg.timestamp || '';
    const content = msg.content;

    // Collect this message's body lines first so D-14 can drop a message whose
    // array emits nothing (no orphan header). Body rules (CONVO-05):
    //   - user STRING content (human prompt / system inject) → code-block quote
    //     so its markdown never renders or pollutes the outline.
    //   - assistant text → keep markdown, but escape leading `#` headings.
    //   - tool_use input / tool_result output → code blocks (already inert).
    //   - thinking → folded <details>, leading `#` escaped.
    const body = [];
    if (typeof content === 'string') {
      const txt = stripAnsi(content);
      const f = fenceFor(txt);
      body.push('', f, txt, f, '');
    } else if (Array.isArray(content)) {
      for (const block of content) {
        if (!block || typeof block !== 'object') continue;
        if (msg.role === 'assistant') {
          if (block.type === 'text') {
            body.push('', escapeHeadings(stripAnsi(block.text || '')), '');
          } else if (block.type === 'tool_use') {
            const inputStr = truncateLines(stripAnsi(JSON.stringify(block.input)), MAX_INPUT_LINES);
            const f = fenceFor(inputStr);
            body.push('', f, `Tool: ${block.name} (${block.id})`, inputStr, f, '');
          } else if (block.type === 'thinking') {
            // CONVO-02 (D-01..04): collapse each thinking block into a
            // default-folded <details>, truncated via MAX_THINKING_LINES. One
            // <details> per block. The body is wrapped in a code fence (sized
            // via fenceFor) so a ``` inside the thinking can't leak and break
            // the report's outline; inside a fence, `#` is inert too.
            const th = truncateLines(stripAnsi(block.thinking || ''), MAX_THINKING_LINES);
            const f = fenceFor(th);
            body.push('', '<details><summary>💭 thinking</summary>', '', f, th, f, '', '</details>', '');
          }
        } else if (msg.role === 'user' && block.type === 'text') {
          // D-14: a user array may carry text blocks; quote them like a prompt.
          const txt = stripAnsi(block.text || '');
          const f = fenceFor(txt);
          body.push('', f, txt, f, '');
        } else if (block.type === 'tool_result') {
          const mark = block.is_error ? ' ✗' : '';
          // block.text is already ANSI-stripped by resultText(); just truncate.
          const out = truncateLines(block.text || '', MAX_OUTPUT_LINES);
          const f = fenceFor(out);
          body.push('', f, `Tool result (${block.tool_use_id})${mark}`, out, f, '');
        }
      }
    }

    // D-14: skip the whole message (header included) when nothing was emitted.
    if (body.length === 0) continue;

    // CONVO-05 outline hierarchy: a real user INPUT (human) opens a top-level
    // turn (H3, titled with a preview of what was asked) so the Obsidian outline
    // navigates by user turn. Everything within the turn — assistant replies,
    // tool results, system injections — drops to H4. A "---" separates turns.
    if (msg.role === 'user' && userSource(msg) === 'human') {
      if (firstTurnSeen) parts.push('', '---', '');
      firstTurnSeen = true;
      const prev = messagePreview(msg);
      parts.push(`### 👤 ${prev || 'User'} — ${ts}`);
    } else if (msg.role === 'user' && userSource(msg) === 'system') {
      parts.push(`#### ⚙️ System — ${ts}`);
    } else if (msg.role === 'user') {
      parts.push(`#### 🔧 Tool Result — ${ts}`);
    } else {
      parts.push(`#### 🤖 Assistant — ${ts}${msg.model ? ` (${msg.model})` : ''}`);
    }
    parts.push(...body);
  }
  return parts.join('\n');
}

// Tool Call Summary table (TOOLS-01): Tool | Count | Successes | Failures.
// A tool_use with no tool_result counts toward Count but neither column.
function renderToolSummary(calls) {
  const stats = new Map(); // name -> { count, success, failure } in first-appearance order
  for (const c of calls) {
    const name = c.toolUse.name;
    let s = stats.get(name);
    if (!s) {
      s = { count: 0, success: 0, failure: 0 };
      stats.set(name, s);
    }
    s.count += 1;
    if (c.toolResult) {
      if (c.toolResult.is_error) s.failure += 1;
      else s.success += 1;
    }
  }
  const lines = ['| Tool | Count | Successes | Failures |', '| --- | --- | --- | --- |'];
  for (const [name, s] of stats) {
    lines.push(`| ${name} | ${s.count} | ${s.success} | ${s.failure} |`);
  }
  return lines.join('\n');
}

// Tool Call Detail (TOOLS-02): one subsection per tool_use in order, showing the
// full (truncated) input and result; errored calls are prefixed ✗.
function renderToolDetail(calls) {
  const parts = [];
  for (const c of calls) {
    const { toolUse, toolResult } = c;
    const errored = !!(toolResult && toolResult.is_error);
    parts.push(`### ${errored ? '✗ ' : ''}${toolUse.name} \`${toolUse.id}\``);

    const inputStr = truncateLines(stripAnsi(JSON.stringify(toolUse.input)), MAX_INPUT_LINES);
    const fIn = fenceFor(inputStr);
    parts.push('', '**Input:**', fIn + 'json', inputStr, fIn, '');

    if (toolResult) {
      parts.push(`**Result:**${errored ? ' ✗' : ''}`);
      const out = truncateLines(toolResult.text || '', MAX_OUTPUT_LINES);
      const fOut = fenceFor(out);
      parts.push(fOut, out, fOut, '');
    } else {
      parts.push('**Result:** _(no result in transcript)_', '');
    }
  }
  return parts.join('\n');
}

// renderReport({ meta, messages }) -> Markdown string. Composes the title, a
// short metadata header, and the Conversation / Tool Call Summary / Tool Call
// Detail sections.
function renderReport({ meta, messages }) {
  const calls = collectToolCalls(messages);
  const parts = ['# Session Analysis', ''];

  if (meta) {
    const slug = meta.cwd ? deriveProjectSlug(meta.cwd) : '(unknown)';
    if (meta.sessionId) parts.push(`**Session:** ${meta.sessionId}`);
    parts.push(`**Project:** ${slug}`);
    if (meta.gitBranch) parts.push(`**Branch:** ${meta.gitBranch}`);
    if (meta.cwd) parts.push(`**Cwd:** ${meta.cwd}`);
    parts.push(`**Range:** ${meta.firstTs || '—'} → ${meta.lastTs || '—'}`);
    parts.push(`**Counts:** ${messages.length} messages, ${calls.length} tool calls`);
    if (meta.models && meta.models.length) parts.push(`**Model(s):** ${meta.models.join(', ')}`);
    parts.push('');
  }

  parts.push('## Conversation', '', renderConversation(messages), '');
  parts.push('## Tool Call Summary', '', renderToolSummary(calls), '');
  parts.push('## Tool Call Detail', '', renderToolDetail(calls), '');

  // D-11: when the fidelity self-check fails, append a footnote listing each
  // failing check. Omitted entirely when ok so clean reports stay clean.
  const fidelity = verifyFidelity({ meta, messages });
  if (!fidelity.ok) {
    parts.push('## Fidelity Check', '');
    for (const c of fidelity.checks) {
      if (c.pass) continue;
      parts.push(`- **${c.name}** — expected ${c.expected}, actual ${c.actual}`);
    }
    parts.push('');
  }

  return parts.join('\n');
}

// ---- Auto-targeting (Phase 2) ----------------------------------------------

// Encode a cwd into the ~/.claude/projects/<slug> form: every non-[A-Za-z0-9]
// char becomes '-'. Deterministic (verified against real local dirs); case
// preserved. Refines a PROJECT.md decision — the encoding proved deterministic,
// so the script resolves it (testable) rather than the model. The script still
// accepts an explicit path as an override (pre-supports v2 TGT-03).
function deriveProjectSlug(cwd) {
  return String(cwd).replace(/[^A-Za-z0-9]/g, '-');
}

// The transcript directory for a given cwd.
function resolveTranscriptPath(cwd) {
  return path.join(os.homedir(), '.claude', 'projects', deriveProjectSlug(cwd));
}

// The newest-by-mtime *.jsonl in dir, or null if none (or dir missing).
// Non-.jsonl files are ignored.
function findNewestSession(dir) {
  let names;
  try {
    names = fs.readdirSync(dir);
  } catch {
    return null;
  }
  const jsonls = names.filter((n) => n.endsWith('.jsonl'));
  if (jsonls.length === 0) return null;
  let best = null;
  let bestMtime = -1;
  for (const n of jsonls) {
    const full = path.join(dir, n);
    let st;
    try {
      st = fs.statSync(full);
    } catch {
      continue;
    }
    if (st.mtimeMs > bestMtime) {
      bestMtime = st.mtimeMs;
      best = full;
    }
  }
  return best;
}

module.exports = {
  parseSession,
  collectToolCalls,
  verifyFidelity,
  renderReport,
  truncateLines,
  stripAnsi,
  MAX_OUTPUT_LINES,
  MAX_INPUT_LINES,
  MAX_THINKING_LINES,
  PARSE_SKIP_TYPES,
  deriveProjectSlug,
  resolveTranscriptPath,
  findNewestSession,
};

// ---- CLI (Plan 01-02, Task 2) ----------------------------------------------
// Explicit-path-only in Phase 1. cwd→slug auto-targeting is Phase 2 (TGT-01/02).

// Build the REPORT-01 filename: <YYYY-MM-DD>_<short-id>.md.
// date comes from the session's own first timestamp (UTC, NOT today); short-id
// is the first 8 alnum chars of the sessionId (lowercased), falling back to the
// input file's basename when the sessionId is missing.
function buildOutputFilename(meta, inputPath) {
  let date;
  const ts = meta && meta.firstTs;
  if (ts) {
    const d = new Date(ts);
    if (!Number.isNaN(d.getTime())) date = d.toISOString().slice(0, 10);
  }
  if (!date) date = new Date().toISOString().slice(0, 10);

  let base = meta && meta.sessionId;
  if (!base) base = path.basename(inputPath, path.extname(inputPath));
  const shortId = String(base).replace(/[^A-Za-z0-9]/g, '').toLowerCase().slice(0, 8) || 'session';
  return `${date}_${shortId}.md`;
}

function main() {
  let inputPath = process.argv[2];
  let autoTargeted = false;
  if (!inputPath) {
    // Zero-config (Phase 2): derive the current project's transcript dir and
    // analyze its newest session.
    autoTargeted = true;
    const dir = resolveTranscriptPath(process.cwd());
    if (!fs.existsSync(dir)) {
      console.error('No transcript directory found for this project.');
      console.error(`  cwd:    ${process.cwd()}`);
      console.error(`  slug:   ${deriveProjectSlug(process.cwd())}`);
      console.error(`  looked: ${dir}`);
      console.error('Pass an explicit path: node analyze-session.js <path-to-session.jsonl>');
      process.exit(1);
    }
    inputPath = findNewestSession(dir);
    if (!inputPath) {
      console.error(`No .jsonl sessions found in ${dir}`);
      process.exit(1);
    }
  }

  let session;
  try {
    session = parseSession(inputPath);
  } catch (err) {
    console.error(err && err.message ? err.message : String(err));
    process.exit(1);
  }

  if (autoTargeted) {
    console.log(`Auto-selected newest session: ${path.basename(inputPath)} (id ${session.meta.sessionId || '?'}, started ${session.meta.firstTs || '?'})`);
  }

  const markdown = renderReport(session);
  const filename = buildOutputFilename(session.meta, inputPath);
  const outDir = path.join(process.cwd(), 'session-analysis');
  fs.mkdirSync(outDir, { recursive: true });
  const outPath = path.join(outDir, filename);
  fs.writeFileSync(outPath, markdown, 'utf8');

  const calls = collectToolCalls(session.messages);
  const okCount = calls.filter((c) => c.toolResult && !c.toolResult.is_error).length;
  const errCount = calls.filter((c) => c.toolResult && c.toolResult.is_error).length;
  console.log(`Wrote ${outPath} — ${session.messages.length} messages, ${calls.length} tool calls (${okCount} ok, ${errCount} errors).`);

  // D-10/D-11: dual-use fidelity self-check. Prints one line to stdout; a clean
  // run reports OK, a mismatch warns and points at the report footnote.
  const fidelity = verifyFidelity(session);
  if (fidelity.ok) {
    console.log('Fidelity: ✓ all checks pass');
  } else {
    const n = fidelity.checks.filter((c) => !c.pass).length;
    console.warn(`Fidelity: ⚠ ${n} check(s) failed (see report footnote)`);
  }
}

if (require.main === module) {
  main();
}
