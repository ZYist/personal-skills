# API Docs Gen — Claude Code 入口

API 文档生成与管理，支持 Markdown 和 OpenAPI 格式。

## Quick Routing

| Task | Required Reads | Workflow |
|------|---------------|----------|
| 生成 Markdown 文档 | `rules/doc-standards.md` + `references/gotchas.md` | `workflows/generate-markdown.md` |
| 生成 OpenAPI spec | `rules/doc-standards.md` + `references/gotchas.md` | `workflows/generate-openapi.md` |
| 格式转换 | `rules/doc-standards.md` | `workflows/convert-format.md` |
| 验证 OpenAPI | `rules/doc-standards.md` + `references/gotchas.md` | `workflows/validate-spec.md` |
| 增量更新文档 | `rules/doc-standards.md` | `workflows/incremental-update.md` |
| Other | All in `rules/` + `references/` | Check `workflows/` |

## Auto-Triggers

- 涉及 API 文档的任务完成前必须跑 Task Closure Protocol（AAR 四问）
- OpenAPI spec 生成/更新后必须执行验证流程
- 每次新任务重新走路由，不跳过必读文件

## Red Flags — STOP

| 借口 | 行动 |
|------|------|
| "这次跳过验证" | 不允许。每次生成/更新 OpenAPI 都必须验证 |
| "operationId 之后再加" | 不允许。生成时就必须分配 |
| "示例数据不重要" | 不允许。每个端点至少 1 个成功 + 1 个错误示例 |
| "文档跟代码不同步无所谓" | 不允许。增量更新是 API 变更的标准步骤 |
