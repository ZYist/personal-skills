# API 文档格式标准与结构约束

## 通用规则

### 语言与风格
- 使用祈使句写文档（"Returns a list of users" 非 "This endpoint returns a list of users"）
- 每个端点必须有 Summary（一句话）和 Description（详细说明，含示例场景）
- 错误码文档化：列出所有可能的 HTTP 状态码及其触发条件
- 参数表格包含：Name、Type、Required、Default、Description

### 文件命名
- Markdown 文档：`api-reference.md` 或按模块拆分为 `api-{module}.md`
- OpenAPI spec：`openapi.yaml`（YAML 优先）或 `openapi.json`
- 版本化文档放在 `docs/api/v{major}/` 目录下

## Markdown 文档结构

```
# API Reference

## Overview
- Base URL
- Authentication method
- Common headers

## Endpoints

### [METHOD] /path/to/endpoint
- **Summary**: 一句话描述
- **Description**: 详细说明
- **Parameters**:
  | Name | Location | Type | Required | Description |
  |------|----------|------|----------|-------------|
  | ...  | query/path/header/body | ... | yes/no | ... |
- **Request Body**: JSON schema 或示例
- **Response**: 各状态码的返回格式 + 示例
- **Errors**: 该端点特有的错误码

## Schemas
- 复用数据模型定义

## Changelog
- API 变更记录
```

### Markdown 规则
- 端点按资源（resource）分组，组内按 HTTP method 排序（GET → POST → PUT → PATCH → DELETE）
- 每个端点至少提供 1 个成功响应示例和 1 个错误响应示例
- 日期时间参数标注格式（ISO 8601）
- 分页参数统一命名：`page` / `per_page` 或 `offset` / `limit`（项目内选一种，全局统一）

## OpenAPI 3.x 规范约束

### 必填字段
每个 Operation 必须包含：
- `operationId`：全局唯一标识符，格式 ` {resource}_{action}`（如 `users_list`、`users_create`）
- `summary`：≤ 120 字符
- `description`：含使用场景说明
- `tags`：按资源分组
- `responses`：至少定义 200（或 201）和默认错误响应

### Schema 规则
- 使用 `$ref` 引用 `components/schemas/` 中的复用模型，避免内联定义
- Schema 属性必须有 `description` 和 `example`
- 使用 `additionalProperties: false` 禁止未知字段（除非设计上需要开放扩展）
- 枚举值用 `enum` + `x-enum-descriptions` 扩展字段
- 日期类型用 `type: string, format: date` 或 `format: date-time`

### 路径与参数
- 路径参数用 `{paramName}` 风格，在 `parameters` 中声明 `in: path`
- 查询参数声明 `in: query`，标注 `required` 和 `schema`
- 请求体使用 `requestBody` + `content` + `application/json` 结构
- 文件上传使用 `multipart/form-data` content type

### 安全定义
- 在顶层 `components/securitySchemes` 定义认证方式
- 在 operation 或 tag 级别引用 `security`
- 不在文档中硬编码 token 或密钥

### Server 定义
- 顶层 `servers` 数组至少包含一个条目
- 使用 `{environment}` 变量区分开发/测试/生产环境

## 格式转换规则

### Markdown → OpenAPI
- 一级标题 → `info.title`
- 端点 HTTP method + path → `paths` 条目
- 参数表格 → `parameters` 数组
- 请求/响应示例 → `examples` 字段

### OpenAPI → Markdown
- `info` → Overview 段
- `paths` → 按资源分组的端点章节
- `components/schemas` → 底部 Schemas 章节
- `security` → Authentication 章节

## 验证规则

### OpenAPI 验证检查项
1. 语法合法（YAML/JSON 可解析）
2. 符合 OpenAPI 3.0.x 或 3.1.x schema
3. 所有 `operationId` 全局唯一
4. 所有 `$ref` 可解析（无悬空引用）
5. 每个操作有成功响应定义
6. 无 Schema 引用循环
7. `servers` 非空

### Markdown 验证检查项
1. 所有端点有 Summary + Description
2. 所有参数表格列完整（Name/Location/Type/Required/Description）
3. 所有端点有响应示例
4. Base URL 和认证方式已文档化
5. 内部锚点链接有效
