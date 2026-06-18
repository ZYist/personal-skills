// analyze-session.test.js — node:test suite for the Session Analyst parser.
// Stdlib only (node:test + node:assert + fs/os/path). No third-party runner.
const test = require('node:test');
const assert = require('node:assert');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const {
  parseSession,
  collectToolCalls,
  renderReport,
  truncateLines,
  stripAnsi,
  verifyFidelity,
  MAX_OUTPUT_LINES,
  MAX_INPUT_LINES,
  MAX_THINKING_LINES,
  deriveProjectSlug,
  resolveTranscriptPath,
  findNewestSession,
} = require('./analyze-session.js');

// Build a JSONL file in a temp dir from an array of line objects; return its path.
function writeFixture(lines) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'session-analyst-'));
  const file = path.join(dir, 'fixture.jsonl');
  fs.writeFileSync(file, lines.map((l) => JSON.stringify(l)).join('\n') + '\n', 'utf8');
  return file;
}

test('parseSession keeps only user/assistant lines in order and normalizes assistant blocks (PARSE-01/02/04)', () => {
  const fixture = writeFixture([
    {
      type: 'user',
      message: { role: 'user', content: 'hello there' },
      uuid: 'u1', parentUuid: null, timestamp: '2026-06-17T10:00:00Z',
      sessionId: 'sess-abc', cwd: 'D:\\workspace\\x', gitBranch: 'master', version: '1.0',
    },
    {
      type: 'assistant',
      message: {
        role: 'assistant',
        content: [
          { type: 'text', text: 'Hi there' },
          { type: 'tool_use', name: 'Read', input: { file_path: '/a' }, id: 'tu_1' },
          { type: 'thinking', thinking: 'pondering the request' },
        ],
        model: 'claude-test-model',
      },
      uuid: 'a1', parentUuid: 'u1', timestamp: '2026-06-17T10:00:01Z',
      sessionId: 'sess-abc', cwd: 'D:\\workspace\\x', gitBranch: 'master', version: '1.0',
    },
    { type: 'mode', mode: 'default' }, // must be excluded
  ]);

  const { meta, messages } = parseSession(fixture);

  // PARSE-01: non-conversation lines excluded
  assert.strictEqual(messages.length, 2, 'exactly two conversation entries (mode line excluded)');

  // PARSE-04: input line order preserved
  assert.strictEqual(messages[0].role, 'user');
  assert.strictEqual(messages[0].content, 'hello there', 'user string prompt preserved');

  assert.strictEqual(messages[1].role, 'assistant');
  const blocks = messages[1].content;
  assert.strictEqual(blocks.length, 3, 'three assistant blocks in order: text, tool_use, thinking');
  // PARSE-02: text block
  assert.deepStrictEqual(blocks[0], { type: 'text', text: 'Hi there' });
  // PARSE-02: tool_use normalized to {type, id, name, input}
  assert.deepStrictEqual(blocks[1], { type: 'tool_use', id: 'tu_1', name: 'Read', input: { file_path: '/a' } });
  // PARSE-02: thinking block
  assert.deepStrictEqual(blocks[2], { type: 'thinking', thinking: 'pondering the request' });

  // meta
  assert.strictEqual(meta.sessionId, 'sess-abc');
  assert.deepStrictEqual(meta.models, ['claude-test-model'], 'models is an array with the assistant model');
});

test('parseSession normalizes user tool_result blocks and collectToolCalls links tool_use↔tool_result (PARSE-03)', () => {
  const fixture = writeFixture([
    {
      type: 'assistant',
      message: {
        role: 'assistant',
        content: [
          { type: 'tool_use', id: 'tu_9', name: 'Bash', input: { command: 'ls' } },
          { type: 'tool_use', id: 'tu_8', name: 'Read', input: { file_path: '/x' } },
        ],
        model: 'claude-test-model',
      },
      uuid: 'a1', parentUuid: null, timestamp: '2026-06-17T10:00:01Z',
      sessionId: 'sess-xyz', cwd: 'D:\\proj', gitBranch: 'master', version: '1.0',
    },
    {
      type: 'user',
      message: {
        role: 'user',
        content: [
          { type: 'tool_result', tool_use_id: 'tu_9', content: [{ type: 'text', text: 'a\nb' }], is_error: false },
        ],
      },
      uuid: 'u2', parentUuid: 'a1', timestamp: '2026-06-17T10:00:02Z',
      sessionId: 'sess-xyz', cwd: 'D:\\proj', gitBranch: 'master', version: '1.0',
    },
  ]);

  const { messages } = parseSession(fixture);

  // The user tool_result is normalized to {type, tool_use_id, text, is_error}.
  const userContent = messages[1].content;
  assert.ok(Array.isArray(userContent), 'user tool_result line content is an array');
  assert.deepStrictEqual(userContent[0], {
    type: 'tool_result', tool_use_id: 'tu_9', text: 'a\nb', is_error: false,
  });

  // collectToolCalls: one entry per tool_use, in appearance order, linked by id.
  const calls = collectToolCalls(messages);
  assert.strictEqual(calls.length, 2, 'one entry per tool_use, in appearance order');
  assert.deepStrictEqual(calls[0], {
    toolUse: { id: 'tu_9', name: 'Bash', input: { command: 'ls' } },
    toolResult: { text: 'a\nb', is_error: false },
  });
  // tu_8 has no matching tool_result in the transcript → null.
  assert.strictEqual(calls[1].toolUse.id, 'tu_8');
  assert.strictEqual(calls[1].toolResult, null);
});

test('collectToolCalls: typed-prompt user lines stay strings; mixed arrays link only tool_results', () => {
  const fixture = writeFixture([
    {
      type: 'user',
      message: { role: 'user', content: 'a typed prompt' },
      uuid: 'u0', parentUuid: null, timestamp: '2026-06-17T10:00:00Z',
      sessionId: 'sess-mix', cwd: 'D:\\p', gitBranch: 'master', version: '1.0',
    },
    {
      type: 'assistant',
      message: {
        role: 'assistant',
        content: [{ type: 'tool_use', id: 'tu_7', name: 'Glob', input: { pattern: '*.js' } }],
        model: 'claude-test-model',
      },
      uuid: 'a1', parentUuid: 'u0', timestamp: '2026-06-17T10:00:01Z',
      sessionId: 'sess-mix', cwd: 'D:\\p', gitBranch: 'master', version: '1.0',
    },
    {
      // Mixed array: a stray text block AND a tool_result. Only the tool_result links.
      type: 'user',
      message: {
        role: 'user',
        content: [
          { type: 'text', text: 'ignored note' },
          { type: 'tool_result', tool_use_id: 'tu_7', content: [{ type: 'text', text: 'hit' }], is_error: false },
        ],
      },
      uuid: 'u1', parentUuid: 'a1', timestamp: '2026-06-17T10:00:02Z',
      sessionId: 'sess-mix', cwd: 'D:\\p', gitBranch: 'master', version: '1.0',
    },
  ]);

  const { messages } = parseSession(fixture);

  // A string user prompt stays a string (not treated as a tool_result).
  assert.strictEqual(typeof messages[0].content, 'string');

  const calls = collectToolCalls(messages);
  assert.strictEqual(calls.length, 1, 'only the tool_use links');
  assert.deepStrictEqual(calls[0].toolUse, { id: 'tu_7', name: 'Glob', input: { pattern: '*.js' } });
  assert.deepStrictEqual(calls[0].toolResult, { text: 'hit', is_error: false });
});

test('renderReport: conversation replay + tool summary + truncated detail + ✗ on error (CONVO-01/03, TOOLS-01/02/03)', () => {
  const longResult = Array.from({ length: 55 }, (_, i) => `line${i + 1}`).join('\n');
  const meta = {
    sessionId: 'sess-render', cwd: 'D:\\proj', gitBranch: 'master',
    firstTs: '2026-06-17T10:00:00Z', lastTs: '2026-06-17T10:00:04Z',
    models: ['claude-test-model'],
  };
  const messages = [
    { role: 'user', uuid: 'u1', timestamp: '2026-06-17T10:00:00Z', model: undefined, content: 'hello' },
    {
      role: 'assistant', uuid: 'a1', timestamp: '2026-06-17T10:00:01Z', model: 'claude-test-model',
      content: [
        { type: 'text', text: 'hi' },
        { type: 'tool_use', id: 'tu_1', name: 'Read', input: { file_path: '/x' } },
        { type: 'thinking', thinking: 'ponder' },
      ],
    },
    { role: 'user', uuid: 'u2', timestamp: '2026-06-17T10:00:02Z', model: undefined, content: [{ type: 'tool_result', tool_use_id: 'tu_1', text: longResult, is_error: false }] },
    { role: 'assistant', uuid: 'a2', timestamp: '2026-06-17T10:00:03Z', model: 'claude-test-model', content: [{ type: 'tool_use', id: 'tu_2', name: 'Bash', input: { command: 'bad' } }] },
    { role: 'user', uuid: 'u3', timestamp: '2026-06-17T10:00:04Z', model: undefined, content: [{ type: 'tool_result', tool_use_id: 'tu_2', text: 'boom', is_error: true }] },
  ];

  const md = renderReport({ meta, messages });

  // Four sections present and in order.
  const idxTitle = md.indexOf('# Session Analysis');
  const idxConvo = md.indexOf('## Conversation');
  const idxSummary = md.indexOf('## Tool Call Summary');
  const idxDetail = md.indexOf('## Tool Call Detail');
  assert.notStrictEqual(idxTitle, -1, 'title present');
  assert.ok(idxTitle < idxConvo, 'title before conversation');
  assert.ok(idxConvo < idxSummary, 'conversation before summary');
  assert.ok(idxSummary < idxDetail, 'summary before detail');

  // Conversation: role headers with timestamps, prompt, assistant text, thinking blockquote, interleaved result.
  assert.ok(md.includes('👤 hello — 2026-06-17T10:00:00Z'), 'human header with ts + content preview');
  assert.ok(md.includes('🤖 Assistant — 2026-06-17T10:00:01Z (claude-test-model)'), 'assistant header with ts + model');
  assert.ok(md.includes('hello'), 'user prompt present');
  assert.ok(md.includes('hi'), 'assistant text present');
  assert.ok(md.includes('> [!note]- 💭 thinking'), 'thinking rendered as a collapsed callout');
  assert.ok(!md.includes('> **thinking:'), 'old blockquote shape removed');
  assert.ok(md.includes('Tool result'), 'tool result interleaved in conversation');

  // Tool Call Summary table: Read 1/1/0, Bash 1/0/1.
  const summarySection = md.slice(idxSummary, idxDetail);
  assert.ok(summarySection.includes('| Read | 1 | 1 | 0 |'), 'Read: 1 call, 1 success, 0 failures');
  assert.ok(summarySection.includes('| Bash | 1 | 0 | 1 |'), 'Bash: 1 call, 0 successes, 1 failure');

  // Tool Call Detail: Read input + result truncated to 50 lines with +N marker; Bash ✗ + error text.
  const detailSection = md.slice(idxDetail);
  assert.ok(detailSection.includes(JSON.stringify({ file_path: '/x' })), 'Read full input present');
  assert.ok(detailSection.includes('+5 more lines'), 'result truncated to MAX_OUTPUT_LINES with +N marker');
  assert.ok(detailSection.includes('✗'), 'errored Bash call marked ✗');
  assert.ok(detailSection.includes('boom'), 'error text present');
});

test('thinking blocks collapse into <details>, one per block, truncated at MAX_THINKING_LINES (CONVO-02)', () => {
  // D-04: two thinking blocks in one assistant message → two independent <details>.
  // D-03: a >50-line thinking block is truncated via truncateLines(text, MAX_THINKING_LINES).
  // D-02: default-collapsed — plain <details>, no open attribute.
  const longThinking = Array.from({ length: 55 }, (_, i) => `think-line-${i + 1}`).join('\n');
  const messages = [
    {
      role: 'assistant', uuid: 'a1', timestamp: '2026-06-17T10:00:01Z', model: 'claude-test-model',
      content: [
        { type: 'thinking', thinking: 'short one' },
        { type: 'thinking', thinking: longThinking },
      ],
    },
  ];
  const md = renderReport({ meta: null, messages });

  const calloutCount = (md.match(/> \[!note\]- 💭 thinking/g) || []).length;
  assert.strictEqual(calloutCount, 2, 'two thinking blocks → two independent callouts');
  assert.ok(md.includes('+5 more lines'), 'long (55-line) thinking truncated to 50 with +5 marker');
  assert.ok(!md.includes('<details'), 'no <details> HTML — uses Obsidian callout (no swallow risk)');
  assert.ok(!md.includes('> **thinking:'), 'old blockquote shape removed');
});

test('verifyFidelity: clean session → ok with 3 passing checks (D-08/D-09/D-10)', () => {
  // Reuses collectToolCalls + messages; zero new deps (D-08). Three checks (D-09):
  //   (a) tool-summary count == independent tool_use block count
  //   (b) reported message count == parsed message count
  //   (c) no-result tool count consistent
  const messages = [
    { role: 'user', uuid: 'u1', timestamp: 't1', model: undefined, content: 'go' },
    {
      role: 'assistant', uuid: 'a1', timestamp: 't2', model: 'm',
      content: [
        { type: 'tool_use', id: 'tu_1', name: 'Read', input: {} },
        { type: 'tool_use', id: 'tu_2', name: 'Bash', input: {} },
      ],
    },
    { role: 'user', uuid: 'u2', timestamp: 't3', model: undefined, content: [{ type: 'tool_result', tool_use_id: 'tu_1', text: 'ok', is_error: false }] },
    { role: 'user', uuid: 'u3', timestamp: 't4', model: undefined, content: [{ type: 'tool_result', tool_use_id: 'tu_2', text: 'boom', is_error: true }] },
  ];
  const fid = verifyFidelity({ meta: { sessionId: 's' }, messages });

  assert.strictEqual(fid.ok, true, 'clean session is ok');
  assert.strictEqual(fid.checks.length, 3, 'exactly three checks');
  assert.ok(fid.checks.every((c) => c.pass), 'all checks pass');
  // Each check carries the {name, expected, actual, pass} contract.
  for (const c of fid.checks) {
    assert.ok(typeof c.name === 'string' && c.name.length > 0, 'check has a name');
    assert.ok('expected' in c && 'actual' in c && typeof c.pass === 'boolean', 'check has expected/actual/pass');
  }
});

test('verifyFidelity: duplicate tool_use id with no result → mismatch detected, ok:false (D-09/D-11)', () => {
  // Honest divergence vector: two tool_use BLOCKS share id "X" with no result.
  // collectToolCalls counts per-block (2 null entries), while the independent
  // distinct-id walk sees one unmatched id ({"X"}). check (c) 2≠1 → ok:false.
  const messages = [
    {
      role: 'assistant', uuid: 'a1', timestamp: 't1', model: 'm',
      content: [
        { type: 'tool_use', id: 'X', name: 'Read', input: {} },
        { type: 'tool_use', id: 'X', name: 'Read', input: {} },
      ],
    },
  ];
  const fid = verifyFidelity({ meta: { sessionId: 's' }, messages });

  assert.strictEqual(fid.ok, false, 'duplicate-id no-result mismatch → not ok');
  const failed = fid.checks.filter((c) => !c.pass);
  assert.ok(failed.length >= 1, 'at least one failing check is named');
  assert.ok(failed.some((c) => /no-result/i.test(c.name)), 'the no-result check is the failing one');
});

test('truncation constants + truncateLines helper (TOOLS-03)', () => {
  assert.strictEqual(MAX_OUTPUT_LINES, 50);
  assert.strictEqual(MAX_INPUT_LINES, 200);
  assert.strictEqual(MAX_THINKING_LINES, 50);
  // Under the limit → unchanged.
  assert.strictEqual(truncateLines('a\nb\nc', 50), 'a\nb\nc');
  // Over the limit → first `max` lines + "+N more lines" marker.
  const out = truncateLines(Array.from({ length: 53 }, (_, i) => `l${i}`).join('\n'), 50);
  const outLines = out.split('\n');
  assert.strictEqual(outLines.length, 51, '50 content lines + 1 marker line');
  assert.strictEqual(outLines[outLines.length - 1], '+3 more lines');
});

test('deriveProjectSlug encodes cwd → projects slug (non-alnum → "-", case preserved) (TGT-01)', () => {
  // Verified against the REAL transcript dir for this project.
  assert.strictEqual(deriveProjectSlug('D:\\workspace\\调用分析skill'), 'D--workspace-----skill');
  // Forward slashes and spaces also collapse to "-".
  assert.strictEqual(deriveProjectSlug('/home/alice/my project'), '-home-alice-my-project');
  // Plain ASCII Windows path.
  assert.strictEqual(deriveProjectSlug('C:\\Users\\bob'), 'C--Users-bob');
});

test('resolveTranscriptPath points at ~/.claude/projects/<slug> (TGT-01)', () => {
  const p = resolveTranscriptPath('D:\\workspace\\调用分析skill');
  assert.ok(p.includes('D--workspace-----skill'), 'path contains the derived slug');
  assert.ok(p.includes(path.join('.claude', 'projects')), 'path is under .claude/projects');
});

test('findNewestSession returns the newest-by-mtime .jsonl, ignoring other files (TGT-02)', () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'sa-newest-'));
  const oldFile = path.join(dir, 'old.jsonl');
  const newerFile = path.join(dir, 'newer.jsonl');
  const noise = path.join(dir, 'ignore.txt');
  fs.writeFileSync(oldFile, '{}\n');
  fs.writeFileSync(newerFile, '{}\n');
  fs.writeFileSync(noise, 'not a session');
  const past = new Date(Date.now() - 60000);
  const now = new Date();
  fs.utimesSync(oldFile, past, past);
  fs.utimesSync(noise, past, past);
  fs.utimesSync(newerFile, now, now);
  assert.strictEqual(path.basename(findNewestSession(dir)), 'newer.jsonl');
  // A dir with no .jsonl → null.
  const empty = fs.mkdtempSync(path.join(os.tmpdir(), 'sa-empty-'));
  assert.strictEqual(findNewestSession(empty), null);
});

test('renderReport metadata header shows slug/session/range/counts/models/cwd/branch (TGT-04)', () => {
  const meta = {
    sessionId: 's1', cwd: 'D:\\workspace\\调用分析skill', gitBranch: 'master',
    firstTs: '2026-06-17T10:00:00Z', lastTs: '2026-06-17T10:05:00Z', models: ['glm-5.2'],
  };
  const messages = [
    { role: 'user', uuid: 'u1', timestamp: '2026-06-17T10:00:00Z', model: undefined, content: 'hi' },
    { role: 'assistant', uuid: 'a1', timestamp: '2026-06-17T10:00:01Z', model: 'glm-5.2', content: [{ type: 'tool_use', id: 't1', name: 'Read', input: {} }] },
    { role: 'user', uuid: 'u2', timestamp: '2026-06-17T10:00:02Z', model: undefined, content: [{ type: 'tool_result', tool_use_id: 't1', text: 'ok', is_error: false }] },
  ];
  const md = renderReport({ meta, messages });
  assert.ok(md.includes('s1'), 'session id present');
  assert.ok(md.includes('D--workspace-----skill'), 'project slug (derived from cwd) present');
  assert.ok(md.includes('master'), 'git branch present');
  assert.ok(md.includes('glm-5.2'), 'model present');
  assert.ok(md.includes('3 messages'), 'message count present');
  assert.ok(md.includes('1 tool call'), 'tool count present');
});

test('user text-only content arrays render text under the header; empty arrays emit no orphan header (D-14)', () => {
  const messages = [
    { role: 'user', uuid: 'u1', timestamp: 't1', model: undefined, content: [{ type: 'text', text: 'a note' }] },
    { role: 'user', uuid: 'u2', timestamp: 't2', model: undefined, content: [] },
  ];
  const md = renderReport({ meta: null, messages });
  // Text-only user array: H3 titled by the text preview; content quoted below.
  assert.ok(md.includes('### 👤 a note — t1'), 'text-only user array → H3 titled by preview');
  assert.ok(md.includes('a note'), 'user text block quoted under the header');
  // Empty user array: no orphan header at all (t2 never appears).
  assert.ok(!md.includes('t2'), 'empty user array emits no orphan header');
});

test('stripAnsi strips ANSI/VT color codes (PowerShell output) from tool_result text', () => {
  // Direct unit check on stripAnsi: SGR green-bold + reset sequences removed.
  const pwsh = '\x1b[32;1mMode \x1b[0m\x1b[32;1m Name\x1b[0m\nd---- new-dev';
  assert.strictEqual(stripAnsi(pwsh), 'Mode  Name\nd---- new-dev');
  // Non-string passthrough (no crash on undefined/null).
  assert.strictEqual(stripAnsi(undefined), undefined);
  assert.strictEqual(stripAnsi(null), null);

  // End-to-end: a tool_result carrying PowerShell-colored output flows through
  // parseSession → resultText (stripAnsi) → renderReport with ANSI gone.
  const fixture = writeFixture([
    {
      type: 'assistant',
      message: {
        role: 'assistant',
        content: [{ type: 'tool_use', id: 'tu_a', name: 'Bash', input: { command: 'ls' } }],
        model: 'claude-test-model',
      },
      uuid: 'a1', parentUuid: null, timestamp: '2026-06-18T10:00:01Z',
      sessionId: 'sess-ansi', cwd: 'D:\\proj', gitBranch: 'master', version: '1.0',
    },
    {
      type: 'user',
      message: {
        role: 'user',
        content: [
          { type: 'tool_result', tool_use_id: 'tu_a', content: [{ type: 'text', text: '---PARENT---\n\n\x1b[32;1mMode \x1b[0m\x1b[32;1m Name\x1b[0m\nd---- new-dev' }], is_error: false },
        ],
      },
      uuid: 'u1', parentUuid: 'a1', timestamp: '2026-06-18T10:00:02Z',
      sessionId: 'sess-ansi', cwd: 'D:\\proj', gitBranch: 'master', version: '1.0',
    },
  ]);

  const { messages } = parseSession(fixture);
  const tr = messages[1].content[0];
  assert.strictEqual(tr.text, '---PARENT---\n\nMode  Name\nd---- new-dev', 'ANSI stripped from tool_result text');

  const md = renderReport({ meta: null, messages });
  assert.ok(!md.includes('\x1b['), 'no ESC sequence survives into the report');
  assert.ok(!md.includes('[32;1m'), 'no visible ANSI marker leaked');
  assert.ok(md.includes('Mode  Name'), 'clean text present after stripping');
});

test('parseSession labels user messages by source: human / command / system / tool_result (CONVO-04)', () => {
  const fixture = writeFixture([
    { type: 'user', message: { role: 'user', content: 'hi' }, promptSource: 'typed', uuid: 'u1', parentUuid: null, timestamp: 't1', sessionId: 's', cwd: 'D:\\p', gitBranch: 'm', version: '1' },
    { type: 'user', message: { role: 'user', content: '<command-name>/clear</command-name>' }, uuid: 'u2', parentUuid: 'u1', timestamp: 't2', sessionId: 's', cwd: 'D:\\p', gitBranch: 'm', version: '1' },
    { type: 'user', message: { role: 'user', content: '<local-command-caveat>Caveat: generated by local commands.</local-command-caveat>' }, uuid: 'u2b', parentUuid: 'u2', timestamp: 't2b', sessionId: 's', cwd: 'D:\\p', gitBranch: 'm', version: '1' },
    { type: 'assistant', message: { role: 'assistant', content: [{ type: 'tool_use', id: 'tu_1', name: 'Bash', input: {} }], model: 'm' }, uuid: 'a1', parentUuid: 'u2b', timestamp: 't3', sessionId: 's', cwd: 'D:\\p', gitBranch: 'm', version: '1' },
    { type: 'user', message: { role: 'user', content: [{ type: 'tool_result', tool_use_id: 'tu_1', content: 'ok', is_error: false }] }, uuid: 'u3', parentUuid: 'a1', timestamp: 't4', sessionId: 's', cwd: 'D:\\p', gitBranch: 'm', version: '1' },
  ]);
  const { messages } = parseSession(fixture);
  assert.strictEqual(messages[0].source, 'human', 'typed string → human');
  assert.strictEqual(messages[1].source, 'command', 'slash command → command');
  assert.strictEqual(messages[2].source, 'system', 'caveat injection → system');
  assert.strictEqual(messages[3].source, undefined, 'assistant carries no source');
  assert.strictEqual(messages[4].source, 'tool_result', 'tool_result array → tool_result');
});

test('renderConversation: human→H3 with preview, others→H4, --- only before human turns (CONVO-04/05)', () => {
  const messages = [
    { role: 'user', uuid: 'u1', timestamp: 't1', model: undefined, source: 'human', content: '帮我看看目录' },
    { role: 'assistant', uuid: 'a1', timestamp: 't2', model: 'm', content: [{ type: 'text', text: '好的' }] },
    { role: 'user', uuid: 'u2', timestamp: 't3', model: undefined, source: 'tool_result', content: [{ type: 'tool_result', tool_use_id: 'c1', text: 'out', is_error: false }] },
    { role: 'user', uuid: 'u3', timestamp: 't4', model: undefined, source: 'system', content: '<command-name>/gsd-map-codebase</command-name>' },
    { role: 'assistant', uuid: 'a2', timestamp: 't5', model: 'm', content: [{ type: 'text', text: '开始映射' }] },
    { role: 'user', uuid: 'u4', timestamp: 't6', model: undefined, source: 'human', content: '继续下一步' },
  ];
  const md = renderReport({ meta: null, messages });

  // H3 for human turns (titled by a content preview); H4 for everything else.
  assert.ok(md.includes('### 👤 帮我看看目录 — t1'), 'human → H3 titled by preview');
  assert.ok(md.includes('#### 🤖 Assistant — t2 (m)'), 'assistant → H4');
  assert.ok(md.includes('#### 🔧 Tool Result — t3'), 'tool_result → H4');
  assert.ok(md.includes('#### ⚙️ System — t4'), 'system → H4');
  assert.ok(md.includes('### 👤 继续下一步 — t6'), 'second human → H3 titled by preview');

  // --- only before a fresh HUMAN turn (t6), never before tool_result/system/
  // assistant (they belong to the current turn).
  const idxT1 = md.indexOf('### 👤 帮我看看目录 — t1');
  const idxT4 = md.indexOf('#### ⚙️ System — t4');
  const idxT6 = md.indexOf('### 👤 继续下一步 — t6');
  assert.ok(!md.slice(0, idxT1).includes('---'), 'no separator before the first turn');
  assert.ok(!md.slice(idxT1, idxT4).includes('---'), 'no separator within a turn (before assistant/tool_result/system)');
  assert.ok(md.slice(idxT4, idxT6).includes('---'), 'separator before the next human turn');
});

test('stripAnsi covers ALL text fields, not just tool_result (user string, assistant text, thinking, input)', () => {
  // Regression: <local-command-stdout> from /model carries ANSI in a USER STRING
  // message (not a tool_result), so it bypassed the old resultText-only strip.
  const fixture = writeFixture([
    { type: 'user', message: { role: 'user', content: '<local-command-stdout>Set model to \x1b[1mglm-5.2\x1b[22m</local-command-stdout>' }, uuid: 'u1', parentUuid: null, timestamp: 't1', sessionId: 's', cwd: 'D:\\p', gitBranch: 'm', version: '1' },
    { type: 'assistant', message: { role: 'assistant', content: [{ type: 'text', text: 'done \x1b[32mok\x1b[0m' }, { type: 'thinking', thinking: 'ponder \x1b[36mblue\x1b[0m' }], model: 'm' }, uuid: 'a1', parentUuid: 'u1', timestamp: 't2', sessionId: 's', cwd: 'D:\\p', gitBranch: 'm', version: '1' },
  ]);
  const { messages } = parseSession(fixture);
  const md = renderReport({ meta: null, messages });
  assert.ok(!md.includes('\x1b['), 'no ESC sequence anywhere in the report');
  assert.ok(!md.includes('[1m') && !md.includes('[22m') && !md.includes('[32m') && !md.includes('[36m'), 'no visible ANSI markers leaked');
  assert.ok(md.includes('Set model to glm-5.2'), 'user string ANSI stripped, clean text remains');
  assert.ok(md.includes('done ok'), 'assistant text ANSI stripped');
  assert.ok(md.includes('ponder blue'), 'thinking ANSI stripped');
});

test('escapeHeadings neutralizes leading # in content so it never pollutes the outline (CONVO-05)', () => {
  // An assistant reply that uses ## as a sub-heading, plus a user prompt that
  // pastes a markdown doc. The assistant's ## must NOT become an outline node.
  const messages = [
    { role: 'user', uuid: 'u1', timestamp: 't1', model: undefined, source: 'human', content: '帮我写个报告，标题用 ## 大标题' },
    { role: 'assistant', uuid: 'a1', timestamp: 't2', model: 'm', content: [
      { type: 'text', text: '好的。\n## 第一步：收集\n内容\n### 子节\n更多内容' },
    ] },
  ];
  const md = renderReport({ meta: null, messages });
  // The report's own structural heading is intact.
  assert.ok(/^## Conversation$/m.test(md), 'structural ## Conversation still a heading');
  // Assistant content ## is escaped (backslash-prefixed), not parsed as a heading.
  assert.ok(!/^## 第一步：收集$/m.test(md), 'assistant "## 第一步" is NOT a heading');
  assert.ok(!/^### 子节$/m.test(md), 'assistant "### 子节" is NOT a heading');
  assert.ok(md.includes('\\## 第一步：收集'), 'assistant ## escaped to \\##');
  assert.ok(md.includes('\\### 子节'), 'assistant ### escaped to \\###');
});

test('fenceFor grows the code fence when content contains ``` so it never leaks (CONVO-05)', () => {
  // A tool result whose body itself contains a ``` block must NOT close the
  // outer fence early and leak its headings into the outline.
  const messages = [
    { role: 'user', uuid: 'u1', timestamp: 't1', model: undefined, source: 'human', content: 'run it' },
    { role: 'assistant', uuid: 'a1', timestamp: 't2', model: 'm', content: [{ type: 'tool_use', id: 'c1', name: 'Bash', input: {} }] },
    { role: 'user', uuid: 'u2', timestamp: 't3', model: undefined, source: 'tool_result', content: [{ type: 'tool_result', tool_use_id: 'c1', text: '## LEAKED HEADING\n```\ncode block\n```\nafter', is_error: false }] },
  ];
  const md = renderReport({ meta: null, messages });
  assert.ok(/`{4,}/.test(md), 'outer fence grew past ``` because the content contains ```');
  assert.ok(md.includes('## LEAKED HEADING'), 'leaked content still present (now safely fenced)');
  // Fences are balanced: walking lines, code-state returns to false (no leak).
  let inCode = false;
  for (const l of md.split('\n')) if (/^`{3,}/.test(l)) inCode = !inCode;
  assert.strictEqual(inCode, false, 'fences balanced — no ``` leaks into the outline');
});

test('thinking containing ``` is fenced inside its <details> so it never breaks the outline (CONVO-05)', () => {
  // Regression: a thinking block that muses about code (with ```) used to leak
  // and swallow subsequent headings. Now the thinking body is code-fenced.
  const messages = [
    { role: 'user', uuid: 'u1', timestamp: 't1', model: undefined, source: 'human', content: 'go' },
    { role: 'assistant', uuid: 'a1', timestamp: 't2', model: 'm', content: [
      { type: 'thinking', thinking: 'let me consider\n```\nsome code\n```\n## not a real heading' },
      { type: 'text', text: 'done' },
    ] },
    { role: 'user', uuid: 'u2', timestamp: 't3', model: undefined, source: 'human', content: 'next turn' },
  ];
  const md = renderReport({ meta: null, messages });
  assert.ok(md.includes('### 👤 next turn'), 'the next turn heading is NOT swallowed by leaked ```');
  let inCode = false;
  for (const l of md.split('\n')) if (/^`{3,}/.test(l)) inCode = !inCode;
  assert.strictEqual(inCode, false, 'fences balanced across the thinking block');
});

test('slash command renders as 💻 H3 (own turn), distinct from 👤 human and ⚙️ system (CONVO-06)', () => {
  const fixture = writeFixture([
    { type: 'user', message: { role: 'user', content: '帮我分析一下' }, promptSource: 'typed', uuid: 'u1', parentUuid: null, timestamp: 't1', sessionId: 's', cwd: 'D:\\p', gitBranch: 'm', version: '1' },
    { type: 'user', message: { role: 'user', content: '<command-name>/darwin-skill</command-name><command-args>优化skill</command-args>' }, uuid: 'u2', parentUuid: 'u1', timestamp: 't2', sessionId: 's', cwd: 'D:\\p', gitBranch: 'm', version: '1' },
    { type: 'assistant', message: { role: 'assistant', content: [{ type: 'text', text: 'ok' }], model: 'm' }, uuid: 'a1', parentUuid: 'u2', timestamp: 't3', sessionId: 's', cwd: 'D:\\p', gitBranch: 'm', version: '1' },
    { type: 'user', message: { role: 'user', content: '<local-command-caveat>Caveat...</local-command-caveat>' }, uuid: 'u3', parentUuid: 'a1', timestamp: 't4', sessionId: 's', cwd: 'D:\\p', gitBranch: 'm', version: '1' },
  ]);
  const { messages } = parseSession(fixture);
  const md = renderReport({ meta: null, messages });
  assert.ok(md.includes('### 👤 帮我分析一下 — t1'), 'typed human → 👤 H3');
  assert.ok(md.includes('### 💻 /darwin-skill 优化skill — t2'), 'slash command → 💻 H3 with command preview');
  assert.ok(md.includes('#### ⚙️ System — t4'), 'caveat → ⚙️ H4 (not promoted to a turn)');
  const idxHuman = md.indexOf('### 👤 帮我分析一下 — t1');
  const idxCmd = md.indexOf('### 💻 /darwin-skill 优化skill — t2');
  assert.ok(md.slice(idxHuman, idxCmd).includes('---'), '--- separates the human turn from the command turn');
});
