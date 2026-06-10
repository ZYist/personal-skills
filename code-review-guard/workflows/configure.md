# 配置审查严格度

## 前置条件
- 用户请求更改审查严格度，或首次使用需要初始化配置

## 流程

### Step 1: 确定配置方式

严格度可以通过以下方式设置（优先级从高到低）：

1. **命令行参数** — 用户在触发审查时直接指定（如 "用 high 严格度审查"）
2. **配置文件** — 项目根目录的 `.code-review-guard.json`
3. **环境变量** — `CODE_REVIEW_STRICTNESS`
4. **默认值** — `medium`

### Step 2: 创建/更新配置文件

如果用户需要持久化配置：

```json
{
  "strictness": "low|medium|high",
  "exclude_patterns": ["额外的排除模式"],
  "max_file_lines": 500,
  "max_function_lines": 50,
  "max_nesting_depth": 4
}
```

每个字段说明：
- `strictness` — 审查严格度（low/medium/high）
- `exclude_patterns` — 额外的文件排除 glob 模式
- `max_file_lines` — 文件最大行数警告阈值（默认 500）
- `max_function_lines` — 函数最大行数警告阈值（默认 50）
- `max_nesting_depth` — 嵌套深度警告阈值（默认 4）

**⚠️ 失败分支**：
- 值不在合法范围内 → 告知用户合法值列表，使用默认值
- 配置文件已存在 → 合并非冲突字段，冲突字段使用新值

### Step 3: 确认配置

向用户展示最终生效的配置并确认。
