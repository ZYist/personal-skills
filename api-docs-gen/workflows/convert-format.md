# Markdown ↔ OpenAPI 格式转换

## 输入
- 源格式文件（Markdown 文档或 OpenAPI spec）
- 目标格式指定

## 输出
- 目标格式的完整文档

## 流程

### Step 1: 解析源文件
根据源格式选择解析策略：
- **Markdown** → 识别标题层级、端点区块（`### [METHOD] /path`）、参数表格、代码块
- **OpenAPI** → 解析 YAML/JSON，提取 paths、components、info

**失败分支**：
- Markdown 结构不符合标准格式 → 识别实际结构，尽可能映射，报告无法映射的部分
- OpenAPI 文件语法错误 → 先修复语法错误（如缩进、引号），再解析

### Step 2: 建立中间表示
将源文件内容转换为统一的内部模型：
```
API Doc {
  info: { title, version, description }
  endpoints: [
    { method, path, summary, description, parameters, requestBody, responses, tags }
  ]
  schemas: { name, properties }
  security: [ { type, scheme } ]
}
```

**失败分支**：
- 源文件信息不完整 → 中间模型中标记缺失字段为 `TODO`，转换后逐一提醒

### Step 3: 生成目标格式

#### Markdown → OpenAPI
1. `info.title` ← 一级标题
2. `servers` ← 从 Overview 中提取 Base URL
3. `paths` ← 端点区块，method + path 作为 key
4. `parameters` ← 参数表格转换
5. `requestBody` ← 请求体代码块转换
6. `responses` ← 响应代码块转换
7. `components/schemas` ← Schemas 章节转换
8. `components/securitySchemes` ← Auth 章节转换
9. 为每个操作生成 `operationId`（格式：`{resource}_{action}`）

#### OpenAPI → Markdown
1. Overview 章节 ← `info` + `servers` + `security`
2. 按资源分组的端点章节 ← `paths`（按 `tags` 分组）
3. 参数表格 ← `parameters` 展开
4. 请求/响应示例 ← `examples` 字段
5. Schemas 章节 ← `components/schemas` 展开
6. Changelog 章节 ← 创建初始条目

### Step 4: 补全缺失信息
目标格式有要求但源格式未提供的信息：
- **转 OpenAPI 时缺失**：`operationId`、`tags`、`servers`、`responses` 的 schema
- **转 Markdown 时缺失**：Base URL、认证说明、参数默认值

策略：从上下文推断；无法推断的用 `[TODO]` 标记，生成后提醒用户补充。

### Step 5: 验证
- **目标为 OpenAPI** → 执行 `workflows/validate-spec.md`
- **目标为 Markdown** → 对照 `rules/doc-standards.md` 的 Markdown 验证检查项

不通过 → 回到对应 Step 修正。
