#!/usr/bin/env node
// fetch-dingtalk.cjs — 调用 dws CLI 拉取日期范围内的钉钉活动数据。
// 零依赖(Node stdlib),输出 JSON 供 AI 归纳为日报/周报。
// 用法:
//   node fetch-dingtalk.cjs [--date YYYY-MM-DD]                   单日(日报)
//   node fetch-dingtalk.cjs [--start YYYY-MM-DD --end YYYY-MM-DD] 范围(周报)
//   [--dws <dws-path>]

const { execSync } = require('node:child_process');

function parseArgs(argv) {
  const args = { start: null, end: null, dws: 'dws' };
  for (let i = 2; i < argv.length; i++) {
    const a = argv[i];
    if (a === '--date') { args.start = args.end = argv[++i]; }
    else if (a === '--start') args.start = argv[++i];
    else if (a === '--end') args.end = argv[++i];
    else if (a === '--dws') args.dws = argv[++i];
  }
  if (!args.start) args.start = args.end = todayStr();
  if (!args.end) args.end = args.start;
  return args;
}

function todayStr() {
  const d = new Date();
  const p = (n) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`;
}

function iso(date, endOfDay) {
  return `${date}T${endOfDay ? '23:59:59' : '00:00:00'}+08:00`;
}

function run(cmd) {
  try {
    const out = execSync(cmd, { encoding: 'utf8', maxBuffer: 20 * 1024 * 1024, stdio: ['ignore', 'pipe', 'pipe'] });
    return { ok: true, data: JSON.parse(out) };
  } catch (e) {
    const stderr = (e.stderr || e.message || '').toString();
    let msg = stderr;
    try { if (e.stdout) { const o = JSON.parse(e.stdout); msg = o.error?.message || o.message || msg; } } catch {}
    return { ok: false, error: msg.slice(0, 300) };
  }
}

function main() {
  const args = parseArgs(process.argv);
  const { start, end, dws } = args;
  const isSingleDay = start === end;
  const result = { start, end, behavior: [], calendar: [], todo: [], report_outbox: [], errors: [] };

  // 1. 行为记录。单日用"今天";范围用"过去一周"(dws 只收模糊时间词)
  //    返回可能混入范围外记录,dws 的时间词是模糊匹配 → 按日期字段精确过滤
  const timeRange = isSingleDay ? '今天' : '过去一周';
  const b = run(`${dws} aisearch behavior --time-range "${timeRange}" --behavior-type all --format json`);
  if (b.ok) {
    result.behavior = (b.data.result || [])
      .filter((r) => {
        const d = (r.date || '').slice(0, 10); // "2026-08-05 17:19:39" → "2026-08-05"
        return d >= start && d <= end;
      })
      .map((r) => ({
        date: r.date, title: r.title || '', snippet: r.snippet || '', url: r.url || '',
      }));
  } else result.errors.push(`behavior(${timeRange}): ${b.error}`);

  // 2. 日程(精确范围)
  const c = run(`${dws} calendar event list --start "${iso(start)}" --end "${iso(end, true)}" --format json`);
  if (c.ok) {
    result.calendar = (c.data.result?.events || []).map((e) => ({
      summary: e.summary || '', start: e.start?.dateTime || '', end: e.end?.dateTime || '',
      room: e.meetingRooms?.[0]?.roomName || null,
      attendees: (e.attendees || []).map((a) => a.displayName).join(', '),
    }));
  } else result.errors.push(`calendar: ${c.error}`);

  // 3. 待办(未完成)
  const t = run(`${dws} todo task list --page 1 --size 20 --status false --format json`);
  if (t.ok) {
    result.todo = (t.data.result?.todoCards || []).map((x) => ({ subject: x.subject || '', taskId: x.taskId }));
  } else result.errors.push(`todo: ${t.error}`);

  // 4. 自己提交的日志(精确范围)。dws 返回键是中文(标题/日期/发送人/状态/钉钉链接)
  const r = run(`${dws} report outbox list --start "${iso(start)}" --end "${iso(end, true)}" --format json`);
  if (r.ok) {
    result.report_outbox = (r.data.result?.report_list || []).map((x) => ({
      title: x['标题'] || x.title || '',
      create_time: x['日期'] || x.create_time || '',
      sender: x['发送人'] || x.sender || '',
      status: x['状态'] || x.status || '',
      url: x['钉钉链接'] || x.url || '',
    }));
  } else result.errors.push(`report outbox: ${r.error}`);

  console.log(JSON.stringify(result, null, 2));
}

main();
