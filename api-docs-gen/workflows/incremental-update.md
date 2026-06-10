# 增量更新已有 API 文档

## 输入
- 已有的 Markdown 文档和/或 OpenAPI spec 文件
- 代码变更内容（git diff 或变更描述）
- 变更影响范围

## 输出
- 更新后的文档文件
- 变更摘要

## 流程

### Step 1: 分析变更影响
1. 获取代码变更范围（git diff、变更文件列表、或用户描述）
2. 识别变更涉及的 API 端点：
   - 新增端点
   - 删除端点
   - 修改端点（参数、响应、行为变化）
   - 新增/修改数据模型
3. 生成影响列表：`{端点/模型} → {变更类型} → {需更新的文档位置}`

**失败分支**：
- 无法确定影响范围 → 列出所有可能相关的端点，标记为 `[UNCERTAIN]`，请用户确认
- 变更不涉及 API → 报告"变更不影响 API 文档"并终止

### Step 2: 读取现有文档
1. 读取现有 Markdown 文档或 OpenAPI spec
2. 定位到需要更新的章节/路径
3. 对比代码当前状态与文档当前内容，确认差异

**失败分支**：
- 现有文档结构不符合标准 → 按标准格式重新组织后再更新
- 文档文件不存在 → 报告情况，建议执行完整生成流程而非增量更新

### Step 3: 更新内容

#### 新增端点
1. 提取新端点的完整元数据
2. 在 Markdown 中添加到对应资源分组
3. 在 OpenAPI 中添加到 `paths` 并更新 `components/schemas`（如有新模型）

#### 删除端点
1. 从 Markdown 中移除对应章节
2. 从 OpenAPI 中移除对应 path
3. 检查是否有 Schema 仅被删除的端点引用 → 若是，一并移除
4. 在 Changelog 中记录删除

#### 修改端点
1. 对比参数变化（新增/删除/类型变更）
2. 对比请求体变化
3. 对比响应变化
4. 更新 Markdown 中的参数表格和示例
5. 更新 OpenAPI 中的对应 operation

#### 数据模型变更
1. 在 Markdown Schemas 章节更新
2. 在 OpenAPI `components/schemas/` 更新
3. 检查所有引用该模型的端点文档是否需要联动更新

### Step 4: 更新版本号
1. 如有破坏性变更（删除端点、必填参数变更、响应格式变更）→ 递增 major 版本
2. 如有新增功能（新增端点、新增可选参数）→ 递增 minor 版本
3. 如仅修复文档错误 → 递增 patch 版本

### Step 5: 验证
- **OpenAPI** → 执行 `workflows/validate-spec.md`
- **Markdown** → 对照 `rules/doc-standards.md` 验证检查项
- **一致性** → 检查 Markdown 和 OpenAPI（如同时存在）描述一致

### Step 6: 生成变更摘要
输出格式：
```
## API 文档变更摘要

### Added
- `[POST] /users` — 新增用户创建端点
- `UserCreateDTO` schema

### Changed
- `[GET] /users` — 新增 `role` 查询参数
- `UserResponse` schema — 新增 `lastLoginAt` 字段

### Removed
- `[DELETE] /users/batch` — 已废弃

### Version
- 1.2.0 → 1.3.0
```
