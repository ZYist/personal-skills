# skill-forge-shouffin

> Agent Skill 生成器 — 基于「[如何写一个好的 skill](https://linux.do/t/topic/1923706)」最佳实践，遵循三要素（Prompt / Context / Harness）、文件夹化、严格目录分离、跨工具兼容原则。

## 一句话

**你说「写一个 skill」，它帮你从头到尾生成一个符合规范的 Agent Skill。**

## 调用方式

```
/skill-forge-shouffin    ← Claude Code 输入 slash command;其他 AI CLI(Gemini/Codex/Cursor/Copilot)直接描述需求即可触发
```

触发词（说任意一句即可）：
- 中文：「创建 skill」「写一个 skill」「生成 skill」「做一个 skill」「skill 生成器」「skill 工厂」「skill 脚手架」
- 英文：「create a skill」「generate skill」「make a skill」「build skill」「skill scaffold」「skill template」

## 它做什么

| 场景 | 它做的事 |
|------|---------|
| 用户说「帮我创建一个 XX skill」 | 引导走完整的 11 步创建流程：明确需求 → 设计 description → 决定目录结构 → 生成文件 → 验证 → 交付 |
| 用户说「帮我设计 description」 | 只走 description 设计子流程 |
| 用户说「验证一下这个 skill」 | 跑 8 类验证检查（含反模式扫描） |

## 核心能力

1. **三要素方法论** — Prompt（触发条件 + 执行指令）、Context（三级渐进式加载）、Harness（验证三步）
2. **文件夹化** — SKILL.md 做 100 行以内路由中心，四类内容严格分离（rules / workflows / references / scripts）
3. **跨工具兼容** — 生成薄壳（CLAUDE.md / GEMINI.md / AGENTS.md），让 skill 在 50+ runtime 通用
4. **反模式扫描** — 生成过程中逐项检查 10 条「绝对不要做」清单
5. **验证闭环** — 交付前跑完整验证：结构、行数、占位符、description 质量、路由完整性、反模式

## 文件结构

```
skill-forge-shouffin/
├── SKILL.md                          # 导航中心（42行）
├── README.md                         # 本文件
├── rules/
│   └── skill-rules.md                # 核心规则：三要素、目录分离、录入标准
├── workflows/
│   ├── create-skill.md               # 主创建流程（11步，含失败分支 + 2个🔴CHECKPOINT）
│   ├── design-description.md         # Description 设计指南
│   ├── build-structure.md            # 目录结构决策树
│   └── validate-skill.md             # 8 类验证检查清单
└── references/
    └── gotchas.md                    # 10 个已知踩坑（最高价值内容）
```

## 使用示例

```
用户: 帮我创建一个用于代码审查的 skill，能在提交 PR 前自动检查代码质量

→ skill-forge-shouffin 走 create-skill workflow:
  Step 1: 确认名称(code-review)、类型(Technique)、触发场景、目标 runtime
  Step 2: 设计 description（Use when... + 中英文触发词）
  Step 3: 决定目录结构（标准文件夹型 B）
  Step 4: 🔴 CHECKPOINT — 展示确认
  Step 5-8: 生成 SKILL.md + rules + workflows + gotchas
  Step 9: 生成薄壳（如需跨工具）
  Step 10: 跑 8 类验证
  Step 11: 🔴 CHECKPOINT — 交付
```

## 设计来源

基于 [linux.do 社区帖子「如何写一个好的 skill」](https://linux.do/t/topic/1923706) 的 16 条最佳实践精华，经 Darwin Skill 2.0 评估优化（9 维 rubric，76.1 → 83.1 分），full_test 实测验证无乐观偏差。

## License

MIT
