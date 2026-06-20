# Skill 开发踩坑清单

## 命名：description-fail — Description 写不好 = Skill 不存在

**触发条件**：写 description 时只写了一句抽象描述

**根因**：模型天然 undertrigger，描述模糊时 Agent 找不到门

**后果**：用户说了正确的话，但 skill 不触发

**解决**：
- description 以 "Use when..." 开头
- 覆盖 ≥ 3 个触发短语（含中英文同义词）
- 描述问题/症状，不描述技术实现
- ≤ 500 字符但信息密度高

**反例**：
```yaml
description: API development helper
```

**正例**：
```yaml
description: >
  Use when creating REST endpoints, writing controller logic,
  or fixing backend bugs. Activate when user says "add API",
  "写接口", "new route", or "fix controller".
```

---

## 命名：monolith-trap — 单文件巨石陷阱

**触发条件**：所有内容塞进一个 SKILL.md，超过 500 行

**根因**：没做目录分离，规则/流程/参考混在一起

**后果**：Agent 读不到关键内容，token 浪费在无关内容上

**解决**：
- SKILL.md ≤ 100 行，只做路由
- 规则 → `rules/`
- 流程 → `workflows/`
- 参考 → `references/`
- 超标时按话题可分离性决定是否拆分

---

## 命名：blind-harness — 缺薄壳导致工具失明

**触发条件**：skill 只写了 CLAUDE.md，没写 GEMINI.md

**根因**：没意识到不同 runtime 读不同入口文件

**后果**：Gemini/Codex/Copilot 完全看不到你的 skill

**解决**：
- 为每个目标 runtime 生成入口文件
- 薄壳 ≤ 60 行，包含三件套（路由表 + Auto-Triggers + Red Flags）
- Cursor 入口的 description 必须与主 SKILL.md 完全一致

**注（skills CLI 生态）**：通过 `npx skills add` 分发时，入口薄壳由 CLI 自动生成，本陷阱主要适用于手动部署到单一 runtime 目录、或需要增强薄壳三件套的场景。

---

## 命名：skip-aar — 跳过 AAR 导致知识永不录入

**触发条件**：任务完成后直接结束，没跑 30 秒 AAR 扫描

**根因**：Agent 自我协商"这次就算了"

**后果**：踩过的坑未来还会再踩

**解决**：
- 任务闭环协议作为任务完成的一部分
- 在薄壳 Red Flags 里内联"就这一次跳过 AAR"
- 借口表必须从真实失败中抄写，不凭空编造

---

## 命名：template-overreach — 预制内容越界

**触发条件**：往 templates/ 里放了具体业务示例

**根因**：混淆了"结构可复用"和"内容可复用"

**后果**：所有下游项目长得一样，开发者抄模板不写自己的

**解决**：
- 铁律 1：结构可预制，内容禁止预制
- 铁律 2："两个真实项目会不同意吗？" 准入测试
- `FILL:` 标记是必填项，不是可选项
- 不往 templates/ 加的东西记入 ANTI-TEMPLATES.md

---

## 命名：route-skip — Agent 跳过路由直接干活

**触发条件**：同一会话第二个任务开始后，Agent 不重走路由

**根因**：Agent "觉得自己已经知道了"

**后果**：必读清单被跳过，规则不被遵守

**解决**：
- 硬性前置：每个新任务重新走路由
- 增加同会话多任务警告
- 或提升到 SKILL.md 作为全局规则

---

## 命名：over-instruction — 过度指令化

**触发条件**：把每一步都写死，包括 Tailwind class 名

**根因**：想控制 Agent 的每一个动作

**后果**：Skill 不可复用，只能用于特定项目

**解决**：
- 提供约束和上下文，不把步骤写死
- "按钮使用项目的设计系统 token" > "使用 bg-blue-500"
- 记录"为什么"而非"做什么"

---

## 命名：scaffold-leak — Agent 实时生成脚手架遗漏段

**触发条件**：让 Agent 每次从头 heredoc 写 SKILL.md

**根因**：Agent 在压力下会忘记写某些段落

**后果**：同一个协议五次生成出五个版本

**解决**：
- 用 `cp -R templates/` + `sed` 替换占位符
- Agent 只做"填空"，不做"生成"
- `grep -rn 'FILL:'` 作为最终检查

---

## 命名：storage-without-activation — 只存储不激活

**触发条件**：高代价陷阱只躺在 references/ 里

**根因**：记录了但没放到 Agent 任务路径上

**后果**：坑记下来了但下次还会踩

**解决**：
- 高代价陷阱同时出现在：
  1. `references/gotchas.md`（详细内容）
  2. SKILL.md 的 Known Gotchas（摘要 + 链接）
  3. 相关 workflow 的检查项
- 判断方法："下次 Agent 走正常路径会自然读到吗？"

---

## 命名：knowledge-rot — references/ 变成会话日志堆

**触发条件**：`references/` 下出现 `2026-xx-xx-session-notes.md` 等日期文件

**根因**：Agent 过度解读"记录"，把整次会话存下来

**后果**：无限膨胀，1 个月后 100+ 同构文件

**解决**：
- references/ 只放规则级引用材料
- 会话日志放 docs/ 或用 git commit + CHANGELOG
- 通过 2/3 门槛过滤（可重复 + 代价高 + 代码不可见）
- 泛化规则：脱离当前项目上下文也能看懂
