# 从代码生成 OpenAPI 3.x 规范

## 输入
- 源代码中的 API 端点定义
- 已有的注解/注释
- 项目框架信息
- （可选）已有 Markdown 文档作为补充信息源

## 输出
- 完整的 `openapi.yaml`（或 `openapi.json`）文件

## 流程

### Step 1: 初始化 spec 骨架
生成 OpenAPI 文档顶层结构：
```yaml
openapi: 3.0.3
info:
  title: FILL:项目名称 API
  version: 1.0.0
  description: FILL:API概述
servers:
  - url: FILL:base-url
    description: FILL:环境说明
components:
  securitySchemes: {}
  schemas: {}
paths: {}
```

### Step 2: 发现并提取端点
1. 扫描路由/控制器文件，提取所有端点
2. 对每个端点提取：method、path、parameters、requestBody、responses
3. 识别认证中间件，映射到 `securitySchemes`

**失败分支**：
- 框架使用动态路由注册 → 搜索路由注册函数调用，追踪回调函数
- 认证方式不明确 → 标注 `TODO: security scheme` 并在输出中警告

### Step 3: 构建 Paths
对每个端点生成 operation 对象：
1. 分配 `operationId`（格式：`{resource}_{action}`，如 `users_list`）
2. 写 `summary`（≤ 120 字符）和 `description`
3. 声明 `parameters`（区分 path/query/header）
4. 声明 `requestBody`（如有）
5. 声明 `responses`（至少 200/201 + 默认错误）
6. 打 `tags`（按资源分组）

**关键约束**：
- `operationId` 全局唯一 — 重复时追加 `_2`, `_3` 后缀并警告
- 参数和 body schema 优先使用 `$ref` 引用 `components/schemas/`
- 每个属性必须有 `description` 和 `example`

### Step 4: 构建 Components/Schemas
1. 从代码中的 DTO/struct/interface/model 提取数据模型
2. 转换为 OpenAPI Schema Object
3. 为每个属性添加 `type`、`description`、`example`
4. 处理嵌套：内联简单嵌套，`$ref` 引用复杂嵌套
5. 设置 `additionalProperties: false`

**失败分支**：
- 存在循环引用 → 在引用链最深处截断，使用 `description` 说明循环，记录警告
- 类型映射不明确 → 使用最接近的 OpenAPI 原始类型，标注 `[INFERRED]`

### Step 5: 补充 Security
1. 将项目认证方式映射到 OpenAPI Security Scheme：
   - Bearer token → `type: http, scheme: bearer`
   - API Key → `type: apiKey`
   - OAuth2 → `type: oauth2, flows: ...`
2. 在 `components/securitySchemes` 中定义
3. 在需要的 operation 上引用 `security`

### Step 6: 验证
执行 `workflows/validate-spec.md` 的完整验证流程。
验证不通过 → 回到对应 Step 修正后重验。

### Step 7: 输出
- 优先输出 YAML 格式（人类可读性好）
- 如项目约定 JSON，转换后输出
- 确保输出文件无 `FILL:` 占位符残留
