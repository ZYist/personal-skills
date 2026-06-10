---
name: api-docs-gen
description: >
  Use when generating, validating, or maintaining API documentation in Markdown
  or OpenAPI (Swagger) format. Activate when user says "generate API docs",
  "write API documentation", "create OpenAPI spec", "API文档", "生成接口文档",
  "OpenAPI", "Swagger spec", "API reference", "接口文档生成", "document endpoints",
  or "API文档管理". Covers both Markdown-based docs and OpenAPI 3.x YAML/JSON specs.
---

# API Docs Gen — API 文档生成与管理

从代码和注解中生成、验证、维护 Markdown 与 OpenAPI 格式的 API 文档。

## Overview

本 skill 帮助 Agent 从源代码中提取 API 信息，产出结构化的 Markdown 文档和/或 OpenAPI 3.x 规范文件。支持从零生成、增量更新、格式转换、合规验证四种核心工作流。

## When to Use

- 项目有 REST/GraphQL/gRPC API 需要文档化
- 需要从现有代码生成分 API 参考文档
- 已有 Markdown 文档需要转为 OpenAPI 规范（或反之）
- OpenAPI spec 需要验证合规性或发现遗漏
- API 变更后需要增量更新文档

## When NOT to Use

- 纯用户手册或教程写作（无 API 端点涉及）
- 非 API 相关的通用文档生成

## Always Read

1. `rules/doc-standards.md` — 文档格式标准与结构约束
2. `references/gotchas.md` — 已知踩坑清单

## Common Tasks

| 任务 | 读取 | 执行 |
|------|------|------|
| **从代码生成 Markdown 文档** | `rules/doc-standards.md` + `references/gotchas.md` | → `workflows/generate-markdown.md` |
| **从代码生成 OpenAPI spec** | `rules/doc-standards.md` + `references/gotchas.md` | → `workflows/generate-openapi.md` |
| **Markdown ↔ OpenAPI 格式转换** | `rules/doc-standards.md` | → `workflows/convert-format.md` |
| **验证 OpenAPI spec 合规性** | `rules/doc-standards.md` + `references/gotchas.md` | → `workflows/validate-spec.md` |
| **增量更新已有文档** | `rules/doc-standards.md` | → `workflows/incremental-update.md` |
| **Other / 未列出** | Always Read 两文件 | 检查 `workflows/` 找最近匹配 |

## Known Gotchas

- OpenAPI spec 缺 `operationId` → 下游代码生成工具报错或产出不可预测的函数名 → see `references/gotchas.md#missing-operation-id`
- Markdown 文档与代码不同步 → 误导开发者，比没有文档更危险 → see `references/gotchas.md#drift-danger`
- 自动生成后不验证 → 可能产出语法错误的 OpenAPI YAML → see `references/gotchas.md#skip-validation`
- 嵌套 Schema 引用循环 → 渲染工具无限递归或栈溢出 → see `references/gotchas.md#schema-cycle`
