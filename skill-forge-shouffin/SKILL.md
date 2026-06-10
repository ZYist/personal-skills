---
name: skill-forge-shouffin
description: "Skill 脚手架生成器：快速创建新的 Agent Skill，自动生成文件夹结构、SKILL.md、描述设计及跨工具兼容配置。触发词：创建skill、生成skill、写一个skill、skill生成器、skill工厂、create skill、skill scaffold"
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

## Known Gotchas

- Description 写不好 = skill 不存在（Agent 找不到门）→ `references/gotchas.md#description-fail`
- 单文件 > 500 行且内容混在一起 → Agent 读不到关键内容 → `references/gotchas.md#monolith-trap`
- 薄壳缺 GEMINI.md → Gemini 完全失明 → `references/gotchas.md#blind-harness`
- "就这一次跳过 AAR" → 知识永远不会录入 → `references/gotchas.md#skip-aar`
- 预制内容进 templates → 所有下游项目长得一样 → `references/gotchas.md#template-overreach`

## 模板

无预置模板。按 `workflows/create-skill.md` Step 5b 手动创建目录结构后逐步填充。
`FILL:` 标记 = 必填项，不是可选项。
