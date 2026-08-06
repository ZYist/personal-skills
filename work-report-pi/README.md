# work-report-pi

> pi 日报/周报生成器 — 汇总本机 pi 会话缓存 + 钉钉记录两个数据源，生成「重点+成果」式日报/周报，**只输出到终端，禁止提交钉钉**。

## 一句话

**你说「写日报」「写周报」「今天干了啥」，它扫描本机 pi 会话缓存 + 钉钉行为/日程/待办，去重合并后按模板输出报告。**

## 调用方式

```
/work-report-pi    ← pi 输入 slash command 或直接描述需求即可触发
```

触发词（说任意一句即可）：
- 中文：「日报」「写日报」「今日工作」「今天干了啥」「生成日报」「写周报」「周报」「总结今天的工作」
- 英文：「daily report」

## 它做什么

| 场景 | 它做的事 |
|------|---------|
| 「帮我写今天的日报」 | 扫本机 pi 会话 + 钉钉记录，输出今日日报（重点+成果式），仅终端展示 |
| 「写个这周的周报」 | 按天聚合本周活动，输出周报（本周完成/总结/下周计划/需协调） |
| 「昨天我都干了什么」 | 传 `--date 昨天` 重新生成指定日期日报 |
| 「只看本机 / 只看钉钉」 | 跳过对应数据源脚本，单源生成 |

## 核心能力

1. **双数据源** — `scripts/parse-pi-sessions.cjs` 扫 `~/.pi/agent/sessions/*/` 的 jsonl；`scripts/fetch-dingtalk.cjs` 通过 dws 拉钉钉 behavior/calendar/todo（只读）
2. **去重合并** — 同一件事在本机与钉钉各出现一次时只记一条
3. **噪音过滤** — 只抽 user/toolCall/toolResult，丢弃 pi 会话的 thinking 噪音
4. **安全约束** — 只输出终端，绝不调用任何 dws 写操作提交钉钉

## 文件结构

```
work-report-pi/
├── SKILL.md                # skill 指令（含 Common Tasks + Known Gotchas）
├── README.md               # 本文件
├── rules/skill-rules.md    # 核心规则（数据源路径、生成约束）
├── references/gotchas.md   # 已知坑点（搜索权益/噪音/格式/去重）
├── workflows/              # 日报/周报生成主流程
│   ├── generate.md
│   └── weekly.md
├── docs/                   # 报告模板（report-template.md / weekly-template.md）
├── scripts/                # 数据拉取脚本（Node.js，零依赖）
│   ├── parse-pi-sessions.cjs
│   └── fetch-dingtalk.cjs
└── test-prompts.json       # 触发词测试用例
```

## 使用示例

```bash
# 生成今日日报（默认）
node scripts/parse-pi-sessions.cjs
node scripts/fetch-dingtalk.cjs

# 指定日期
node scripts/parse-pi-sessions.cjs --date 2026-08-05

# 明细被截断时加大 limit
node scripts/parse-pi-sessions.cjs --limit 5000
```

## 特性

- **依赖**：Node.js（脚本零第三方依赖）、dws MCP（钉钉数据源）
- **只读**：从不写钉钉，只输出终端
- **范围控制**：可只看本机 / 只看钉钉 / 指定日期

## License

MIT
