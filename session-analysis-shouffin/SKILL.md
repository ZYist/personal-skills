---
name: session-analysis-shouffin
description: "Analyzes a local Claude Code session transcript (.jsonl) and writes a readable Markdown report — a chronological conversation replay plus full tool-call detail. Use when the user wants to review what happened in a session (what was said and which tools were called), summarize a past session, or audit tool usage. Zero-config: analyzes the current project's most recent session by default. 触发词：分析上次会话、看看上个 session 干了什么、整理这段对话、审计工具调用、analyze last session、what happened in that conversation."
---

# Session 分析器

把晦涩的 `~/.claude/projects/<slug>/*.jsonl` 会话记录，转成一份清晰、可审查的 **Markdown 报告** —— 还原说了什么、调用了哪些工具，无需离开 Claude Code、无需任何 GUI。

## 何时使用

- "看看我上一个会话发生了什么。"
- "那次对话我调用了哪些工具？"
- "给这次会话生成一份可读的总结/报告。"
- 审查或审计过去某次会话的工具调用。

## 如何调用

### 快速开始 —— `/session-analysis-shouffin`

在对话框输入 `/session-analysis-shouffin`，分析**当前项目最近一次会话**，报告保存到 `./session-analysis/`。无需任何参数 —— skill 自动完成全部定位：

1. 从当前工作目录推导会话目录，编码成 `~/.claude/projects/<slug>` 形式（每个非 `[A-Za-z0-9]` 字符 → `-`，例如 `D:\workspace\调用分析skill` → `D--workspace-----skill`）。
2. 选取该目录下按 mtime 最新的 `.jsonl`。
3. 解析并生成报告。

### 手动调用（行为相同）

```
node analyze-session.js
```

### 分析其他会话

若要分析非最近一次的会话，model 应从 `~/.claude/projects/` 读取目标 `.jsonl`，并根据对话上下文判断是否需要进一步处理，而不是传路径参数。

## 🔴 CHECKPOINT —— 解析前确认目标会话

零参数路径（最新 `.jsonl`）无需询问直接运行；但当目标有歧义或由用户指定时，**先 STOP 并确认**（症状与修复见下方「故障模式」表）。

## 输出

- 一份 Markdown 报告，写到 **`./session-analysis/<YYYY-MM-DD>_<short-id>.md`**（相对 cwd），包含：
  - **Conversation** —— 按时间顺序回放，结构化为大纲导航（Obsidian / MD 面板）。每个用户输入开一个 **H3 轮次**，标题是该提问的预览；轮次内的所有内容 —— assistant 回复、工具结果、系统注入 —— 降为 **H4**，使大纲按用户轮次导航。来源图标：👤 **User** = 真实键盘输入（`promptSource: "typed"`）；💻 **Command** = 用户发起的 slash 命令（`/darwin-skill`、`/gsd-*`、`/model` —— 同样作为 H3 轮次，因为属于用户动作）；⚙️ **System** = 注入内容（`<local-command-caveat>`、命令回显、task 通知）；🔧 **Tool Result** = 工具输出；🤖 **Assistant** = 文本 / tool_use / thinking。每个新用户轮次用 `---` 分隔。用户输入用代码引用；assistant 文本保留其 markdown，但开头的 `#` 会被转义，不会劫持大纲；代码围栏自动加长，确保任何结果里的 ``` 不会破坏结构。
  - **Tool Call Summary** —— 按工具统计总数 / 成功 / 失败。
  - **Tool Call Detail** —— 每个 `tool_use` 的完整 input 和 result（输出截断 ~50 行，输入 ~200 行，带 `+N more lines` 标记）。失败的调用标 **✗**。
- 一行 stdout 摘要：`Wrote <path> — N messages, M tool calls (S ok, F errors).`（自动定位时，会先打印选中的会话。）

## 环境要求与保证

- **Node.js**（v18+；开发于 v24）。**零依赖** —— 仅 Node stdlib，任何装了 Node 的机器都能跑。
- **仅本地：** 只读 `~/.claude/projects/`。无网络、无遥测。
- **仅展示：** 永不执行或重跑记录里的任何内容。

## 故障模式

当脚本非零退出或报告看起来不对时，对照下表症状，按列依次处理 —— 先一线修复，仍失败再用兜底。触发条件对应脚本的真实错误路径。

| 症状 / 触发 | 一线修复 | 仍失败时 |
|---|---|---|
| `No transcript directory found for this project`（cwd 的 `~/.claude/projects/<slug>` 不存在） | 核对 cwd —— slug 由 cwd 推导（见上）；从正确的项目目录运行通常即可解决 | 该项目在此机器上从未有过会话；向用户要一个已存在的 `.jsonl` 绝对路径：`node analyze-session.js <path>` |
| `No .jsonl sessions found`（目录存在但为空） | 该项目的会话已被清理；用 `ls ~/.claude/projects/<slug>/` 确认 | 换一个项目的会话，或向用户要 `.jsonl` 路径 |
| 自动选中的会话不是用户想要的 | 零参数按 mtime 选最新 —— 先与用户确认目标 | 按惯例**不传路径参数**：列出目录里的候选 `.jsonl`，让用户选，再传该绝对路径 |
| 工具调用计数为 0 / 报告稀疏 | 会话可能主要是纯对话 —— 这是正常的 | 换一个 `.jsonl`；若解析疑似有损，见报告末尾 `## Fidelity Check` 脚注 |
| stdout 显示 `Fidelity: ⚠ N check(s) failed` | 计数自检不一致 —— 见报告 `## Fidelity Check` 脚注里的失败项 | 通常是解析边界情况（如重复 `tool_use_id`）；正文仍可读 —— 重跑同一 `.jsonl` 获取精确计数 |
| `node` 缺失或版本 < v18 | 安装 Node v18+ 后重跑 | 若无法安装 Node，按脚本逻辑手工解析，但失去截断、统计和保真自检 |

## 反例（不要做）

这些脚本已处理 —— 手工做只会降低质量或中断运行：

- **不要**重造解析器。不要手写 `jq` / Node 逐行 `JSON.parse`、内容数组扁平化、或 `tool_use`↔`tool_result` 配对。`analyze-session.js` 已编码 slug 查找、id 配对、截断、统计和保真自检 —— 调用一次胜过任何临时脚本。
- **不要**给脚本传目录路径。它接受 `.jsonl` **文件**路径（或零参数自动定位）；传目录会让 `parseSession` 失败。
- **不要**在用户交互调用 `/session-analysis-shouffin` 时传路径参数。惯例是零参数自动定位，或 model 读取选中的 `.jsonl` 并**仅在确认目标后**传其绝对路径。
- **不要**修改、移动或删除源 `.jsonl` —— 工具是只读 / 仅展示的。
- **不要**执行或重跑记录里的任何命令 —— 它是记录，不是待重放的脚本。
- **不要**忽略 `## Fidelity Check` 脚注。它只在计数自检失败时出现，提示报告的计数可能有误。

## 备注

- 解析器、渲染器和 CLI 都在单文件 `analyze-session.js` 中，与本 `SKILL.md` 同目录。
- Thinking 块渲染在默认折叠的 Obsidian callout（`> [!note]-`）里，保持对话回放整洁。用 callout 而非 `<details>` HTML，这样游离的闭合标签永远不会吞掉后续内容（如 Tool Call Summary 表格）。
