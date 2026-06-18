# session-analysis-shouffin

> Claude Code 会话记录分析器 — 把 `~/.claude/projects/<slug>/*.jsonl` 转成结构清晰、Obsidian 大纲友好的 Markdown 报告。

## 一句话

**你说「分析一下上次会话」，它把整段对话 + 工具调用整理成一份可读、可导航的报告。**

## 调用方式

```
/session-analysis-shouffin    ← 在 Claude Code 中直接输入（零参数，自动分析当前项目最新会话）
```

触发词（说任意一句即可）：
- 中文：「分析上次会话」「看看上个 session 干了什么」「整理一下这段对话」「审计工具调用」
- 英文：「analyze last session」「what happened in that conversation」「summarize this session」「audit tool usage」

## 它做什么

| 场景 | 它做的事 |
|------|---------|
| 「分析我上一个 session」 | 零参数自动定位当前项目最新 `.jsonl`，生成报告到 `./session-analysis/` |
| 「看看那个 session 用了哪些工具」 | 按 👤/💻/⚙️/🔧/🤖 分层回放 + 工具调用统计表 + 每次调用的完整 input/result |
| 「审计一下工具调用，哪些失败了」 | 失败调用在统计表计入 Failures、明细标 ✗ 并展示报错文本 |

## 核心能力

1. **分层大纲导航** — 每个用户输入（👤 打字 / 💻 命令）开一个 H3 轮次，轮内回复/工具/注入降为 H4，Obsidian 右侧大纲按「用户每次输入」导航
2. **三色来源区分** — 👤 真实键盘输入（`promptSource:"typed"`）/ 💻 slash 命令 / ⚙️ 程序注入（caveat、命令回显、task 通知）— GSD 等工作流「代替用户输入」一眼可辨
3. **Obsidian 防污染** — 内容里的 `##` 自动转义、代码围栏随内容动态加长（`fenceFor`）、thinking 用原生 callout 折叠，标题/表格不会再被吞
4. **ANSI 清零** — PowerShell 彩色输出等 ANSI 转义码全字段剥离，不再变乱码
5. **保真度自检** — 工具计数自带交叉校验，不一致时在报告末尾附 `## Fidelity Check` 脚注

## 文件结构

```
session-analysis-shouffin/
├── SKILL.md                # skill 指令（含失败模式表 + 反例清单）
├── README.md               # 本文件
├── analyze-session.js      # 解析器 + 渲染器 + CLI（单文件，Node stdlib 零依赖）
└── analyze-session.test.js # node:test 套件（21 用例）
```

## 使用示例

```
用户: 分析一下我上一个 session 都干了什么

→ session-analysis-shouffin:
  1. 从 cwd 推导 ~/.claude/projects/<slug>，取最新 .jsonl
  2. 解析对话 + 工具调用，写报告到 ./session-analysis/<日期>_<id>.md
  3. stdout: Wrote <path> — N messages, M tool calls (S ok, F errors).

报告大纲（Obsidian 右侧导航）:
  # Session Analysis
  └ ## Conversation
    └ ### 👤 <用户输入预览>          ← 每个用户输入一个导航节点
       └ #### 🤖 Assistant / 🔧 Tool Result / ⚙️ System
  └ ## Tool Call Summary           ← 工具统计表
  └ ## Tool Call Detail            ← 每次调用完整 input/result
```

## 特性

- **零依赖** — Node.js v18+，纯 stdlib，任何装了 Node 的机器能跑
- **零配置** — 默认分析当前项目最新会话，无需传参
- **本地只读** — 只读 `~/.claude/projects/`，无网络、无遥测、永不执行会话里的命令

## License

MIT
