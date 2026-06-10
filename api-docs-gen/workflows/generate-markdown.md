# 从代码生成 Markdown API 文档

## 输入
- 源代码中的 API 端点定义（controllers/routes/handlers）
- 已有的注解/注释（如 JSDoc、docstrings、XML comments）
- 项目框架信息（Express、FastAPI、Spring、Gin 等）

## 输出
- 结构化的 Markdown API 文档文件

## 流程

### Step 1: 发现 API 端点
1. 扫描项目目录，定位路由/控制器文件
2. 识别框架类型（从依赖文件或 import 语句判断）
3. 提取所有端点的 HTTP method + path 组合
4. 按资源分组排序

**失败分支**：
- 无法定位路由文件 → 检查项目是否有自定义路由注册机制（如插件系统），搜索路由注册函数调用
- 端点数量为 0 → 确认项目是否为 API 项目；如不是，报告"未发现 API 端点"并终止

### Step 2: 提取端点元数据
对每个端点提取：
- Summary（从注释第一行或函数名推断）
- Description（从注释详细说明部分提取）
- Parameters（路径参数、查询参数、请求头）
- Request body schema（从类型定义/DTO/struct 提取）
- Response schema（从返回类型或注解提取）
- 认证要求

**失败分支**：
- 注释缺失 → 从函数签名和参数类型推断，标注 `[AUTO-INFERRED]` 标记
- 类型定义复杂（泛型、嵌套）→ 展开到具体类型，记录简化假设

### Step 3: 组装文档结构
按 `rules/doc-standards.md` 中定义的 Markdown 结构组装：
1. 写 Overview（Base URL、Auth、Common headers）
2. 按资源分组写端点章节
3. 写 Schemas 章节（复用数据模型）
4. 写 Changelog（初始版本标记）

### Step 4: 补充示例
1. 为每个端点生成至少 1 个成功请求/响应示例
2. 为每个端点生成至少 1 个常见错误响应示例
3. 示例数据使用真实类型和合理值（不用 "string"、"123" 占位）

**失败分支**：
- 无法推断示例数据 → 使用类型信息构造最小有效示例，标注 `[PLACEHOLDER]`

### Step 5: 自检
对照 `rules/doc-standards.md` 的 Markdown 验证检查项逐项检查：
- [ ] 所有端点有 Summary + Description
- [ ] 所有参数表格列完整
- [ ] 所有端点有响应示例
- [ ] Base URL 和认证方式已文档化
- [ ] 内部锚点链接有效

不通过项 → 回到对应 Step 修正后重检。
