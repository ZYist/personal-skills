# API 文档生成踩坑清单

## 命名：missing-operation-id — 缺少 operationId 导致下游工具崩溃

**触发条件**：生成 OpenAPI spec 时未为每个 operation 分配 `operationId`

**根因**：`operationId` 是可选字段，容易忽略；但代码生成工具（OpenAPI Generator、Kiota 等）依赖它生成函数名

**后果**：下游工具报错或生成不可预测的函数名（如 `get_1`、`get_2`），消费者无法正常使用 SDK

**解决**：
- 每个 operation 必须有 `operationId`
- 格式统一为 `{resource}_{action}`（如 `users_list`、`orders_create`）
- 在验证流程中检查唯一性和非空

---

## 命名：drift-danger — 文档与代码不同步比没有文档更危险

**触发条件**：API 代码变更后未同步更新文档

**根因**：文档更新不纳入开发流程，遗忘或嫌麻烦

**后果**：开发者按文档调用 API 得到意外结果，浪费调试时间；严重时导致生产事故

**解决**：
- 每次涉及 API 的代码变更必须触发文档更新检查
- 在 CI 中加入 OpenAPI spec 对比验证（如 `oasdiff breaking-change`）
- 增量更新 workflow (`workflows/incremental-update.md`) 应作为 API 变更的标准步骤

---

## 命名：skip-validation — 跳过验证就交付

**触发条件**：生成 OpenAPI spec 后直接交付，不跑验证流程

**根因**：觉得"自动生成的应该没问题"

**后果**：交付了语法错误的 YAML，下游工具无法解析，消费者信任度下降

**解决**：
- 每次生成或更新 OpenAPI spec 后必须执行 `workflows/validate-spec.md`
- 验证不通过不交付
- 可在 scripts/ 中提供自动化验证脚本

---

## 命名：schema-cycle — Schema 引用循环

**触发条件**：两个或多个 Schema 通过 `$ref` 互相引用（A → B → A）

**根因**：数据模型设计本身存在递归（如树形结构、双向关联）

**后果**：Swagger UI、Redoc 等渲染工具无限递归或栈溢出

**解决**：
- 在验证流程中检测循环引用
- 树形结构使用自引用而非双向引用（`Node` 引用 `Node[]`）
- 双向关联在文档中只保留单向，另一侧用 description 说明
- 检测到循环时在引用链最深处截断

---

## 命名：inline-schema-bloat — 内联 Schema 导致 spec 膨胀

**触发条件**：所有 Schema 都内联在 `paths` 中，不使用 `$ref`

**根因**：生成时图省事，直接内联写

**后果**：spec 文件体积膨胀 3-10 倍，同一模型多处定义不一致，修改时漏改

**解决**：
- 复杂类型（超过 2 个属性的对象）必须提取到 `components/schemas/`
- 使用 `$ref: '#/components/schemas/ModelName'` 引用
- 简单类型（单个属性、原始类型）可内联

---

## 命名：missing-examples — 没有示例的文档没有灵魂

**触发条件**：生成了参数列表和 Schema，但没有请求/响应示例

**根因**：觉得 Schema 已经足够描述，示例是"锦上添花"

**后果**：消费者必须反复试错才能构造正确请求，开发体验差

**解决**：
- 每个端点至少 1 个成功响应示例
- 每个端点至少 1 个错误响应示例
- Schema 中每个属性有 `example` 字段
- 示例数据使用合理值，不用 "string"/"123" 等占位值

---

## 命名：framework-guess-wrong — 框架识别错误

**触发条件**：扫描项目时错误判断了 Web 框架类型

**根因**：项目可能同时引入多个框架依赖，或使用了自定义封装

**后果**：路由文件定位错误，提取出不存在的端点或遗漏端点

**解决**：
- 优先从 `package.json`/`requirements.txt`/`go.mod`/`pom.xml` 判断框架
- 从 import 语句验证而非依赖列表
- 不确定时先向用户确认框架类型
- 常见框架路由文件位置：
  - Express: `routes/` 或 `app.js`
  - FastAPI: 同文件 `@app`/`@router` 装饰器
  - Spring: `@Controller`/`@RestController` 注解类
  - Gin: `router.go` 或 `routes/`

---

## 命名：auth-missing-in-doc — 文档未说明认证方式

**触发条件**：API 有认证但文档中未记录

**根因**：认证逻辑在中间件层，端点函数上看不出来

**后果**：消费者不知道需要认证，请求全部返回 401，浪费时间排查

**解决**：
- 识别认证中间件（Express 的 `app.use(auth)`、FastAPI 的 `Depends(get_current_user)` 等）
- 在 Markdown 的 Overview 中记录认证方式
- 在 OpenAPI 的 `components/securitySchemes` 中定义
- 每个 operation 标注 `security`（除非是公开端点）
