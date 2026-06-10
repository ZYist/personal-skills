# 目录结构决策

## 决策树

```
开始
  │
  ├─ skill 功能简单（< 200 行可覆盖）?
  │   └─ YES → 单文件结构
  │
  ├─ skill 涉及多种任务类型?
  │   └─ YES → 标准文件夹结构
  │
  └─ skill 需要大量参考资料（API 文档等）?
      └─ YES → 文件夹 + references/ 深层
```

## 结构类型

### 类型 A：单文件 Skill
```
skills/{name}/
└── SKILL.md    # 所有内容内联
```
**适用**：功能简单、步骤少、无大量参考资料
**限制**：SKILL.md ≤ 200 行

### 类型 B：标准文件夹 Skill
```
skills/{name}/
├── SKILL.md        # 导航中心（≤ 100 行）
├── rules/          # 约束规则
├── workflows/      # 流程步骤
└── references/     # 背景资料、坑点
```
**适用**：多种任务类型、需要路由

### 类型 C：完整 Skill
```
skills/{name}/
├── SKILL.md
├── rules/
├── workflows/
├── references/
├── scripts/        # 辅助脚本
└── docs/           # 可选：报告、提示词
```
**适用**：需要可执行工具、大量参考资料

## 四类内容判定

遇到内容不知道放哪里？按以下判定：

| 内容 | 放哪里 | 判定标准 |
|------|--------|---------|
| "你必须做 X" | `rules/` | 指令性 |
| "第1步、第2步" | `workflows/` | 流程性 |
| "小心 X / 注意 Y" | `references/gotchas.md` | 警告性 |
| 可执行脚本 | `scripts/` | 工具性 |
| 提示词/报告模板 | `docs/` | 可选辅助 |

## 文件大小管理

### 何时拆分
文件超标时回答三个问题：
1. 话题可分离？
2. 导航困难？
3. 拆后各部分能独立存在？

三个都 Yes → 拆。任何一个 No → 不拆。

### 何时合并
碎片文件过多时：
1. 话题相关？
2. 合并后更好找？
3. 合并后不超标？

三个都 Yes → 合并。

## 薄壳文件（跨工具时）

需要薄壳的信号：
- skill 用于多个 runtime（Claude Code + Cursor + Codex 等）
- 项目有团队协作，不同成员用不同工具
- skill 需要在 CI/CD 中被不同 Agent 使用

薄壳位置参考 `rules/skill-rules.md` 第四节。
