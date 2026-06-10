# API Docs Gen — Codex/Copilot 入口

API documentation generation and management for Markdown and OpenAPI formats.

## Quick Routing

| Task | Required Reads | Workflow |
|------|---------------|----------|
| Generate Markdown docs | `rules/doc-standards.md` + `references/gotchas.md` | `workflows/generate-markdown.md` |
| Generate OpenAPI spec | `rules/doc-standards.md` + `references/gotchas.md` | `workflows/generate-openapi.md` |
| Format conversion | `rules/doc-standards.md` | `workflows/convert-format.md` |
| Validate OpenAPI | `rules/doc-standards.md` + `references/gotchas.md` | `workflows/validate-spec.md` |
| Incremental update | `rules/doc-standards.md` | `workflows/incremental-update.md` |
| Other | All in `rules/` + `references/` | Check `workflows/` |

## Auto-Triggers

- Run AAR (4 questions) before marking any API doc task complete
- Validate OpenAPI spec after every generation or update
- Re-read routing for each new task in the same session

## Red Flags — STOP

| Excuse | Action |
|--------|--------|
| "Skip validation this time" | Denied. Always validate OpenAPI specs |
| "Add operationId later" | Denied. Assign during generation |
| "Examples are not important" | Denied. Minimum 1 success + 1 error example per endpoint |
| "Drift is fine" | Denied. Update docs on every API change |
