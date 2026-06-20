---
name: skill-forge-shouffin
description: "Skill 脚手架生成器。Use when 用户要创建一个新的 Agent Skill（设计 description、决定目录结构、生成文件、跨工具薄壳、验证交付），或单独设计 skill 的 description / 验证已有 skill。遵循三要素（Prompt/Context/Harness）+ 严格目录分离 + 跨工具兼容（CLAUDE.md/GEMINI.md/AGENTS.md）。触发词：创建skill、生成skill、写一个skill、skill生成器、skill工厂、create skill、skill scaffold、design description、validate skill"
---

# Skill Forge — Skill 生成器

生成符合最佳实践的 Agent Skill。遵循三要素（Prompt / Context / Harness）、文件夹化、严格目录分离、跨工具兼容原则。

## Always Read

1. `rules/skill-rules.md` — 核心规则：三要素、目录分离、录入标准、任务闭环
2. `references/gotchas.md` — 最高价值内容：已知踩坑清单

## Common Tasks

| 任务 | 读取 | 执行 |
|------|------|------|
| **创建新 skill** | `rules/skill-rules.md` + `references/gotchas.md` | → `workflows/create-skill.md` |
| **设计 description** | `rules/skill-rules.md` | → `workflows/design-description.md` |
| **决定目录结构** | `rules/skill-rules.md` | → `workflows/build-structure.md` |
| **验证已有 skill** | `references/gotchas.md` | → `workflows/validate-skill.md` |
| **Other / 未列出** | Always Read 两文件 | 检查 `workflows/` 找最近匹配 |

## Known Gotchas（反例与黑名单）

| # | 不要做什么 | 为什么 | 正确做法 |
|---|-----------|--------|---------|
| 1 | ❌ Description 写不好 | skill 不存在（Agent 找不到门） | 按 `workflows/design-description.md` 写 | → `references/gotchas.md#description-fail` |
| 2 | ❌ 单文件 > 500 行且内容混在一起 | Agent 读不到关键内容 | 严格目录分离 → `references/gotchas.md#monolith-trap` |
| 3 | ❌ 手动部署缺薄壳 | 非 skills CLI 分发时 Gemini 失明 | skills CLI 自动生成；手动部署则补全 → `references/gotchas.md#blind-harness` |
| 4 | ❌ "就这一次跳过 AAR" | 知识永远不会录入 | 每次必做 AAR → `references/gotchas.md#skip-aar` |
| 5 | ❌ 预制内容进 templates | 所有下游项目长得一样 | templates 只放骨架 → `references/gotchas.md#template-overreach` |

## 模板

无预置模板。按 `workflows/create-skill.md` Step 5b 手动创建目录结构后逐步填充。
`FILL:` 标记 = 必填项，不是可选项。
