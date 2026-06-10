# 创建新 Skill 主流程

## 前置条件
- 明确 skill 的用途和目标用户
- 已读 `rules/skill-rules.md` 和 `references/gotchas.md`

## 流程

### Step 1: 明确需求
1. 向用户确认 skill 名称（仅字母、数字、连字符）
2. 确认 skill 类型：
   - **Technique**（具体方法 + 步骤）
   - **Pattern**（思维模型）
   - **Reference**（API 文档 / 工具文档）
3. 确认触发场景：用户会在什么情况下需要这个 skill？会说什么话？
4. 确认目标 runtime：Claude Code / Cursor / Codex / Gemini / 全部

**⚠️ 失败分支**：
- 用户说不清用途 → 给 3 个同类 skill 示例帮用户明确范围；追问 2 次仍模糊 → 提议暂停，让用户想清楚再继续
- 名称含特殊字符 → 自动转为连字符，告知用户
- 类型不确定 → 默认 Technique（最常见），在 Step 10 让用户确认

### Step 2: 设计 Description
→ 执行 `workflows/design-description.md`

**⚠️ 失败分支**：
- Description 超过 500 字符 → 精简触发短语，删除工作流总结性描述
- Description 总结了工作流而非触发条件 → 重写，只保留 "Use when..." + 触发短语

### Step 3: 决定目录结构
→ 执行 `workflows/build-structure.md`

**⚠️ 失败分支**：
- 用户无法判断选哪种结构 → 默认类型 B（标准文件夹），在 Step 10 让用户确认

### Step 4: 🔴 CHECKPOINT — 结构确认
**暂停，向用户展示以下内容并确认**：
1. 确定的名称、类型、触发场景
2. 设计好的 description 全文
3. 选定的目录结构类型及原因
4. 目标 runtime 列表

用户确认后才继续。用户说"改" → 回到对应 Step 修改。

### Step 5: 生成文件

#### 5a. 小型 Skill（单文件）
如果 skill 功能简单（< 200 行可覆盖），创建单文件结构：
```
skills/{name}/
└── SKILL.md
```

#### 5b. 标准文件夹 Skill
创建目录结构：
```
skills/{name}/
├── SKILL.md
├── rules/
├── workflows/
└── references/
```
按 Step 5c-8 依次填充每个文件的内容。

#### 5c. 写 SKILL.md 正文
按以下结构写正文（≤ 100 行）：
```
## Overview — 1-2 句核心原理
## When to Use — 使用场景 + 不使用场景
## Always Read — 每次必读文件列表
## Common Tasks — 任务路由表（≤10 条 + Other 兜底）
## Known Gotchas — 先留空（放 <!-- PENDING_GOTCHAS --> 占位标记）
```

**⚠️ 失败分支**：
- 正文超过 100 行 → 将详细内容拆分到 rules/ 或 workflows/ 文件，SKILL.md 只保留路由
- 缺少 "Other / 未列出" 兜底条目 → 必须补上

**⏱️ 时序说明**：Known Gotchas 段落此时先放 `<!-- PENDING_GOTCHAS -->` 占位标记。gotchas.md 在 Step 8 才写，写完后 Step 8 的反模式扫描会强制回填此处。

### Step 6: 写 rules/ 文件
写入约束规则：
- 每条规则用祈使句
- 解释"为什么"而不只说"做什么"
- 单文件 ≤ 300 行

**⚠️ 反模式扫描**：
扫描已写的 rules 文件，检查是否出现 "建议/可以考虑/根据情况/灵活把握" 等软措辞。
出现 ≥ 3 处 → 重写为祈使句 + 具体参数。

### Step 7: 写 workflows/ 文件
为每种任务类型写一个 workflow：
- 有序步骤 + 每步的输入/输出
- 失败分支："如果 X 失败 → Y"
- 单文件 ≤ 200 行

**⚠️ 失败分支**：
- Workflow 只有正向流程 → 必须补充至少 1 个失败分支
- 步骤超过 15 步 → 考虑拆分为子 workflow

### Step 8: 写 references/ 文件
- `gotchas.md` — 已知踩坑（最高价值内容）
- 其他参考资料按需创建
- 单文件 ≤ 500 行

**⚠️ 反模式扫描**：
检查 gotchas.md 是否同时出现在 SKILL.md 的 Known Gotchas 中。
任何高代价坑点只存在 gotchas.md 中而未在 SKILL.md 摘要出现 → 必须补上（参考 `references/gotchas.md#storage-without-activation`）。

### Step 9: 生成薄壳（如需跨工具）
为每个目标 runtime 生成入口文件。薄壳 ≤ 60 行，包含：
1. Quick Routing 表
2. Auto-Triggers（Task Closure Protocol）
3. Red Flags — STOP（借口表内联）

**⚠️ 失败分支**：
- 目标包含 Gemini 但无 GEMINI.md → **必须生成**，否则 Gemini 完全失明
- 目标包含 Cursor 但 description 与主 SKILL.md 不一致 → **必须对齐**

### Step 10: 验证
→ 执行 `workflows/validate-skill.md`

**⚠️ 失败分支**：
- 验证发现 ❌ 项 → 记录具体 ❌ 项，回到对应 Step 修正后重新验证
- 占位符 `FILL:` 残留 → 每个 `FILL:` 都是必填项，未填写 = 未完成

### Step 11: 🔴 CHECKPOINT — 交付用户
展示以下内容，等用户确认：
1. 完整目录结构（`find` 输出）
2. SKILL.md 全文
3. description 触发测试结果（5 个模拟输入，≥ 4 匹配）
4. 验证清单结果（7 类检查全部 ✅）
5. 任何遗留的 `FILL:` 标记提醒

用户说"好" → 完成。用户说"改" → 回到对应 Step 修改后重新验证。
