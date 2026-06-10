# 验证 OpenAPI Spec 合规性

## 输入
- OpenAPI spec 文件（YAML 或 JSON）

## 输出
- 验证报告：通过项 + 问题列表（按严重性分类）

## 流程

### Step 1: 语法验证
1. 确认文件可解析（YAML/JSON 格式合法）
2. 确认 `openapi` 字段值为 `3.0.x` 或 `3.1.x`
3. 确认顶层必需字段存在：`openapi`、`info`、`paths`

**失败分支**：
- 文件无法解析 → 报告具体语法错误位置和原因，终止后续验证
- `openapi` 版本不是 3.x → 报告版本不兼容，终止后续验证

### Step 2: 结构验证
检查以下结构性问题：
1. `info.title` 和 `info.version` 非空
2. `servers` 数组非空，每个 server 的 `url` 非空
3. `paths` 中的每个 path 以 `/` 开头
4. 每个 operation 至少有一个 response 定义
5. `components/securitySchemes` 中引用的 scheme 都有定义
6. 所有 `$ref` 指向文档内已存在的位置（无悬空引用）

### Step 3: operationId 唯一性
1. 收集所有 operation 的 `operationId`
2. 检查无重复
3. 检查每个 operation 都有 `operationId`（非空）

**失败分支**：
- 缺失 `operationId` → 报告具体哪些 operation 缺失，建议自动生成格式
- 重复 `operationId` → 报告具体重复项，建议重命名方案

### Step 4: Schema 验证
1. 检查 `components/schemas/` 中每个 schema 的属性都有 `type` 或 `$ref`
2. 检查无 Schema 引用循环（A → B → A）
3. 检查 `enum` 类型属性值列表非空
4. 检查 `required` 中列出的属性在 `properties` 中已定义
5. 检查 `example` 值与 `type` 匹配

**循环检测方法**：
- 构建引用图（schema → 其 `$ref` 目标）
- 深度优先遍历检测环

### Step 5: 描述质量检查
1. 所有 operation 有 `summary`（≤ 120 字符）
2. 所有 operation 有 `description`
3. 所有 parameter 有 `description`
4. 所有 schema 属性有 `description`
5. 所有 schema 属性有 `example`

### Step 6: 安全性检查
1. 无硬编码 token/密钥（正则匹配 `Bearer x`、`api-key:` 等模式）
2. `security` 引用的 scheme 在 `components/securitySchemes` 中存在
3. 全局 `security` 或每个 operation 的 `security` 已定义

### Step 7: 生成报告
汇总所有检查结果，按严重性分类：
- **ERROR**：必须修复（语法错误、悬空引用、缺少 operationId）
- **WARNING**：强烈建议修复（缺少 description/example、Schema 循环）
- **INFO**：优化建议（未使用 `additionalProperties: false`、缺少 tags）

输出格式：
```
## OpenAPI Spec 验证报告

### Summary
- ERROR: N 项
- WARNING: N 项
- INFO: N 项

### Details
#### [ERROR] 描述
- Location: paths > /users > get
- Detail: ...
- Fix: ...
```
