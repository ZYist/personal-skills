---
name: code-review-guard
description: >
  Use when reviewing code before commit or PR, finding bugs, security issues,
  performance problems, or style violations. Activate when user says "code
  review", "check code quality", "review PR", "提交前检查", "代码审查",
  "检查代码", "代码质量", "review diff", or "check before commit".
---

# Code Review Guard

PR 提交前的自动代码质量审查。分析变更、定位风险、给出具体修改建议。

## Always Read

1. `rules/review-rules.md` — 审查维度、严重度分级、输出格式约束
2. `references/gotchas.md` — 常见误判和漏检陷阱

## Common Tasks

| 任务 | 读取 | 执行 |
|------|------|------|
| 审查当前分支变更 | `rules/review-rules.md` + `references/gotchas.md` | → `workflows/review-diff.md` |
| 审查指定文件 | `rules/review-rules.md` | → `workflows/review-files.md` |
| 配置审查严格度 | `rules/review-rules.md` | → `workflows/configure.md` |
| **Other / 未列出** | Always Read 两文件 | 检查 `workflows/` 找最近匹配 |

## Known Gotchas

- 巨型 diff 导致遗漏 → see `references/gotchas.md#huge-diff-overload`
- 误报淹没真实问题 → see `references/gotchas.md#false-positive-flood`
- 只查不改，报告无用 → see `references/gotchas.md#report-without-fix`
