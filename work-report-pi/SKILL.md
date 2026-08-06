---
name: work-report-pi
description: "生成日报/周报（汇总本机 pi 会话缓存 + 钉钉记录），仅终端输出不提交钉钉。Use when the user wants to generate a daily work report (日报) or weekly report (周报) summarizing activities from the local pi session cache and DingTalk records. Output to terminal only — never submits to DingTalk. 触发词：日报、写日报、今日工作、今天干了啥、生成日报、写周报、周报、总结今天的工作、daily report"
---

# Daily Report (pi) — 日报/周报生成(仅终端输出)

从本机 pi 会话缓存 + 钉钉记录两个数据源,生成"重点+成果"式日报/周报,**只输出到终端,禁止提交到钉钉**。

## Always Read

1. `rules/skill-rules.md` — 数据源路径、生成约束
2. `references/gotchas.md` — 已知坑点(搜索权益/噪音/格式)

## Common Tasks

| 任务 | 读取 | 执行 |
|------|------|------|
| 生成今日日报 | rules + gotchas | → `workflows/generate.md` |
| 生成周报(本周/指定范围) | rules + gotchas | → `workflows/weekly.md` |
| 指定日期生成(如昨天) | rules | → `workflows/generate.md`(传 `--date YYYY-MM-DD`) |
| 只看本机/只看钉钉数据 | rules | → `workflows/generate.md`(跳过对应脚本) |
| Other / 未列出 | rules + gotchas | 检查 `workflows/` 找最近匹配 |

## Known Gotchas

- **禁止提交钉钉**:本 skill 只输出到终端。用户没有明确说"提交",绝不调用任何 dws 写操作 → `references/gotchas.md#no-submit`
- 钉钉消息查询必须用 `dws aisearch behavior`,禁止 `chat message list-all`(需"消息搜索权益")→ `references/gotchas.md#search-rights`
- pi 会话缓存含大量 thinking 噪音,只抽 user/toolCall/toolResult → `references/gotchas.md#thinking-noise`
- pi 与 Claude Code 的 jsonl 格式不同,勿用旧解析器 → `references/gotchas.md#jsonl-format`
- 时间过滤以内容时间戳为准,不信文件名 → `references/gotchas.md#time-filter`
- 日报合并去重:同一件事两边各出现一次时只记一条 → `references/gotchas.md#dedup`

## 脚本

- `scripts/parse-pi-sessions.cjs` — 扫 `~/.pi/agent/sessions/*/` 日期范围内 jsonl,输出本机活动 JSON
- `scripts/fetch-dingtalk.cjs` — 调 dws 拉钉钉 behavior/calendar/todo/report,输出 JSON(只读)
