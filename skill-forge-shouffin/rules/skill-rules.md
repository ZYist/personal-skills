# Skill 核心规则

## 一、三要素（缺一不可）

### Prompt — 定义做什么

**Description（触发描述）**
- 写在 SKILL.md 的 frontmatter `description` 字段
- 是 Agent 判断"要不要激活这个 Skill"的最重要依据
- 必须包含：触发短语 + 激活条件 + 用户可能说的各种表达
- 模型天然倾向于 undertrigger，所以 description 要主动覆盖各种表达方式
- ≤ 500 字符，用 "Use when..." 开头，只写触发条件，不总结工作流

**Body（执行指令）**
- SKILL.md 正文部分，告诉 Agent 具体怎么执行
- 用祈使句（"读取文件"），不用"你应该……"
- 解释"为什么"，不只说"做什么"
- SKILL.md 正文 ≤ 100 行。超出拆分到引用文件

### Context — 决定知道多少

三级渐进式加载：
1. **第 1 级**：SKILL.md frontmatter + 路由表（始终加载）
2. **第 2 级**：当前任务路由到的文件（按需加载）
3. **第 3 级**：references/ 深层资料（仅相关时加载）

信息越多越好，但 Context 窗口有限 → 只把"始终需要"的放顶层，"可能需要"的放引用文件。

### Harness — 验证好不好用

三件事：
1. **准备测试用例** — 用真实用户会说的话，不用完美提示
2. **定好"怎么算对"** — 能自动检查就自动检查，说不清的留给人看
3. **对比有无 Skill 的差异** — 同一问题带/不带 Skill 各跑一次

## 二、严格目录分离

四类内容严格分离：

| 类型 | 目录 | 判定标准 |
|------|------|---------|
| 约束/规则 | `rules/` | "你必须做 X"（指令性） |
| 流程步骤 | `workflows/` | "第1步、第2步、第3步"（流程性） |
| 背景资料 | `references/` | "小心 X"（警告性）、架构、坑点 |
| 脚本/工具 | `scripts/` | 可执行的辅助工具 |

**边缘情况**：既是解释性又容易违反的内容（如"输入验证的坑"），按形式分：
- 指令性 → Rule
- 警告性 → Reference（`references/gotchas.md`）

**文件大小参考值**：

| 文件 | 建议上限 | 超标处理 |
|------|---------|---------|
| SKILL.md | 100 行 | 评估拆分 |
| 薄壳文件 | 60 行 | 精简 |
| rules/*.md | 300 行 | 评估拆分 |
| workflows/*.md | 200 行 | 评估拆分 |
| references/*.md | 500 行 | 评估拆分 |

行数是信号，不是命令。超标触发评估，不自动拆分。同模块内容不拆。

## 三、SKILL.md 导航中心

SKILL.md 是路由表 + 优先级，不是百科全书。结构：

```
frontmatter（name + description）
# Skill 标题 + 一句话说明
## Always Read（每次任务都读，2-3 个文件）
## Common Tasks（按任务类型路由，≤10 条，含 Other 兜底）
## Known Gotchas（最关键坑点摘要 + 链接）
```

路由表规则：
- 每个条目列出精确路径，不能只写 "follow the workflow"
- Common Tasks ≤ 10 条；超出按领域分组
- 必须包含 "Other / unlisted task" 兜底条目

## 四、跨工具兼容（薄壳）

| Harness | 必需入口 |
|---------|---------|
| Claude Code | `CLAUDE.md` |
| Cursor | `.cursor/skills/<name>/SKILL.md` + `.cursor/rules/workflow.mdc` |
| Codex CLI | `AGENTS.md` + `.codex/instructions.md` |
| Gemini CLI | `GEMINI.md` |
| Copilot CLI / OpenCode | `AGENTS.md`（共用） |
| Windsurf | `.windsurf/rules/*.md` |

**薄壳三件套（≤ 60 行）**：
1. Quick Routing 表 — Task | Required reads | Workflow
2. Auto-Triggers — 非平凡任务完成前必须跑 Task Closure Protocol
3. Red Flags — STOP — 借口表内联

缺哪个 harness 入口 = 该 harness 完全失明。

> **skills CLI 生态注**：通过 `npx skills add` 安装时，CLI 自动为每个目标 runtime 生成入口薄壳（GEMINI.md/AGENTS.md/CLAUDE.md 等），skill 仓库源只需维护 SKILL.md。只有手动部署到单一 runtime 目录、或需要超出 CLI 默认入口的增强薄壳（三件套）时，才需手写。

## 五、任务闭环协议（Task Closure Protocol）

任务完成条件（全部满足前不算完成）：
1. 主体工作完成并验证
2. 30 秒 AAR 扫描（4 个问题 — 全部 "否" 则结束）
3. 任一 "是" → 通过录入标准 → 通过则记录

### AAR 四问
- 新模式？ — 用了未记录的模式或约定？
- 新陷阱？ — 遇到不提前知道就会浪费大量时间的问题？
- 缺失规则？ — 因缺少某条规则走了弯路？
- 过时规则？ — 现有规则已不准确或不再适用？

### 录入标准（2/3 门槛）
| 条件 | 问题 |
|------|------|
| 可重复 | 未来任务还会遇到？ |
| 代价高 | 不知道浪费多少时间？几分钟不值得，30 分钟值得 |
| 代码不可见 | 光看代码能推断？能则不录 |

至少 2/3 通过才录入。

### 泛化规则
记录内容必须脱离当前项目上下文也能看懂。改写公式：
```
具体发现 → 抽象为通用 pattern → 说明不遵守的后果
```

### 激活优于存储
高代价陷阱必须同时：
- 存储在正确文件中
- 激活在会触发它的任务路径上（workflow 检查项、SKILL.md Known Gotchas、或 rules 摘要）

判断："下次 Agent 走正常任务路径时，会自然读到这条经验吗？" — 不会 = 只是记下来了，还没生效。

## 六、让 Skill 谦虚

Agent 读了路由表后"觉得自己已经知道了"，跳过必读清单。解决：
1. 硬性前置：每个 bug/需求重新走路由
2. 增加「同会话多任务」警告
3. 或提升到 SKILL.md 作为全局规则

## 七、保持 Skill 聚焦

需要拆分的信号：
- Description 列了 10+ 个来自不同领域的触发短语
- Common Tasks 有 15+ 条覆盖不相关的工作
- Agent 经常为只涉及一个子领域的任务激活整个 Skill

## 八、Anthropic 建议

- 不陈述显而易见的事 — 聚焦项目特有约定和 Agent 默认行为会出错的场景
- 避免过度指令化 — 提供约束和上下文，不把每一步写死
- 利用脚本和代码库 — Agent 调用脚本比从头写可靠
- 测试和迭代 — Skill 也是代码，需要测试
