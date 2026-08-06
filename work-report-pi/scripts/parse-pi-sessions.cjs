#!/usr/bin/env node
// parse-pi-sessions.cjs — 解析 pi agent 会话缓存,抽取日期范围内的本机活动。
// 零依赖(Node stdlib),输出 JSON 供 AI 归纳为日报/周报。
// 用法:
//   node parse-pi-sessions.cjs [--date YYYY-MM-DD]           单日(日报)
//   node parse-pi-sessions.cjs [--start YYYY-MM-DD --end YYYY-MM-DD]  范围(周报)
//   [--project <slug>] [--limit N]

const fs = require('node:fs');
const path = require('node:path');
const os = require('node:os');

const SESSIONS_ROOT = path.join(os.homedir(), '.pi', 'agent', 'sessions');

function parseArgs(argv) {
  const args = { start: null, end: null, project: null, limit: 1000 }; // 默认 1000,减少密集活动日漏报
  for (let i = 2; i < argv.length; i++) {
    const a = argv[i];
    if (a === '--date') { args.start = args.end = argv[++i]; }
    else if (a === '--start') args.start = argv[++i];
    else if (a === '--end') args.end = argv[++i];
    else if (a === '--project') args.project = argv[++i];
    else if (a === '--limit') args.limit = parseInt(argv[++i], 10) || 1000;
  }
  if (!args.start) args.start = args.end = todayStr(); // 默认今天
  if (!args.end) args.end = args.start;
  return args;
}

function todayStr() {
  const d = new Date();
  const p = (n) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`;
}

// 日期字符串 → 本地 0 点时间戳
function dayTs(dateStr) {
  const [y, m, d] = dateStr.split('-').map(Number);
  return new Date(y, m - 1, d).getTime();
}

function timeFromTs(ts) {
  if (!ts) return null;
  const t = typeof ts === 'number' ? new Date(ts) : new Date(ts);
  return isNaN(t.getTime()) ? null : t;
}

function textBlocks(content) {
  if (!Array.isArray(content)) return [];
  return content.filter((b) => b && b.type === 'text' && typeof b.text === 'string').map((b) => b.text);
}

function clean(s) {
  return s.replace(/\x1b\[[0-9;?]*[A-Za-z]/g, '').replace(/\s+/g, ' ').trim();
}

function toolSummary(name, args) {
  if (!args || typeof args !== 'object') return name;
  const cmd = args.command || args.prompt || args.path || args.pattern || args.url || '';
  const s = clean(String(cmd));
  const head = s.length > 100 ? s.slice(0, 100) + '…' : s;
  return head ? `${name}(${head})` : name;
}

// 按内容时间戳过滤,不信任文件名(跨天/时区)
function parseFile(file, startTs, endTs) {
  const out = [];
  const lines = fs.readFileSync(file, 'utf8').split('\n');
  for (const line of lines) {
    if (!line.trim()) continue;
    let obj;
    try { obj = JSON.parse(line); } catch { continue; }
    if (!obj || obj.type !== 'message' || !obj.message) continue;

    const t = timeFromTs(obj.message.timestamp || obj.timestamp);
    if (!t) continue;
    const ms = t.getTime();
    if (ms < startTs || ms > endTs) continue;

    const time = t.toTimeString().slice(0, 8);
    const day = `${t.getFullYear()}-${String(t.getMonth() + 1).padStart(2, '0')}-${String(t.getDate()).padStart(2, '0')}`;
    const role = obj.message.role;
    if (role === 'user') {
      const text = clean(textBlocks(obj.message.content).join(' '));
      if (text && text.length > 1) out.push({ day, time, type: 'user', text });
    } else if (role === 'assistant') {
      const calls = (obj.message.content || []).filter((b) => b && b.type === 'toolCall');
      for (const c of calls) out.push({ day, time, type: 'tool', name: c.name, summary: toolSummary(c.name, c.arguments) });
    } else if (role === 'toolResult') {
      const text = clean(textBlocks(obj.message.content).join(' ')).slice(0, 80);
      out.push({ day, time, type: 'toolResult', name: obj.message.toolName, err: !!obj.message.isError, text: text || (obj.message.isError ? '(错误)' : '') });
    }
  }
  return out;
}

function main() {
  const args = parseArgs(process.argv);
  const startTs = dayTs(args.start);
  const endTs = dayTs(args.end) + 24 * 3600 * 1000 - 1; // 含结束日整天

  if (!fs.existsSync(SESSIONS_ROOT)) {
    console.log(JSON.stringify({ error: `sessions 目录不存在: ${SESSIONS_ROOT}`, events: [] }));
    return;
  }
  const projects = fs.readdirSync(SESSIONS_ROOT, { withFileTypes: true })
    .filter((d) => d.isDirectory())
    .map((d) => d.name)
    .filter((n) => !args.project || n.includes(args.project));

  let events = [];
  const perProject = {};
  for (const proj of projects) {
    const dir = path.join(SESSIONS_ROOT, proj);
    const files = fs.readdirSync(dir).filter((f) => f.endsWith('.jsonl'));
    let evs = [];
    for (const f of files) evs = evs.concat(parseFile(path.join(dir, f), startTs, endTs));
    for (const e of evs) { e.project = proj; events.push(e); }
    if (evs.length) perProject[proj] = evs.length;
  }
  events.sort((a, b) => (a.time < b.time ? -1 : 1));

  const userMsgs = events.filter((e) => e.type === 'user');
  const toolCalls = events.filter((e) => e.type === 'tool');
  const toolErrors = events.filter((e) => e.type === 'toolResult' && e.err);
  const totalEvents = events.length; // 截断前的全量,用于 truncated 判断

  // 按天聚合(周报用)
  const dayMap = {};
  for (const e of events) {
    const d = dayMap[e.day] || (dayMap[e.day] = { date: e.day, user: 0, tool: 0, errors: 0 });
    if (e.type === 'user') d.user++;
    else if (e.type === 'tool') d.tool++;
    else if (e.type === 'toolResult' && e.err) d.errors++;
  }
  const daysAgg = Object.values(dayMap).sort((a, b) => (a.date < b.date ? -1 : 1));

  const truncated = totalEvents > args.limit; // 事件明细被截断 → 必须提示,否则日报漏报
  events = events.slice(0, args.limit); // limit 只截断输出,counts 用全量

  console.log(JSON.stringify({
    start: args.start, end: args.end,
    projects_scanned: Object.keys(perProject),
    counts: { user_messages: userMsgs.length, tool_calls: toolCalls.length, tool_errors: toolErrors.length },
    truncated,
    hint: truncated ? `事件明细被截断(共 ${totalEvents} 条 > limit ${args.limit}),用户消息可能遗漏,请用更大 --limit 重跑(如 --limit 5000)` : null,
    days: daysAgg,
    events,
  }, null, 2));
}

main();
