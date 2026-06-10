# 设计 Skill Description

Description 是 Agent 判断"要不要激活"的唯一依据。写不好 = skill 不存在。

## 核心原则

1. **只写触发条件，不总结工作流**
2. **以 "Use when..." 开头**
3. **覆盖用户可能说的各种表达**（模型天然 undertrigger）
4. **第三人称**（被注入到系统提示词中）
5. **≤ 500 字符**

## 设计步骤

### 1. 收集触发短语
列出用户会说的真实话语：
- 直接请求："帮我写一个 skill"
- 间接描述："我需要一个工具来处理 X"
- 同义词："创建/生成/制作/搭建"
- 中英文都要覆盖

### 2. 写触发条件
```
Use when [具体触发条件], [场景], [上下文].
Activate when user says "[短语1]", "[短语2]", "[短语3]".
```

### 3. 检查清单

| 检查项 | 标准 |
|--------|------|
| 是否以 "Use when" 开头 | ✅/❌ |
| 是否包含 ≥ 3 个触发短语 | ✅/❌ |
| 是否包含中文触发短语（如适用） | ✅/❌ |
| 是否包含同义词覆盖 | ✅/❌ |
| 是否描述了问题/症状（非技术实现） | ✅/❌ |
| 是否避免了工作流总结 | ✅/❌ |
| 是否 ≤ 500 字符 | ✅/❌ |
| 是否第三人称 | ✅/❌ |

### 4. 反模式对照

❌ **错误写法**：
```yaml
description: API development helper
```
→ 太抽象，Agent 无法匹配

❌ **错误写法**：
```yaml
description: For creating skills - generates folder structure, writes SKILL.md, creates rules and workflows
```
→ 总结了工作流，Agent 可能不读正文

✅ **正确写法**：
```yaml
description: >
  Use when creating a new skill, generating skill folder structure, or
  designing skill description. Activate when user says "create a skill",
  "写一个skill", "skill template", or "skill scaffold".
```

### 5. 质量验证
- 让 Agent 读 description 后判断："给我 5 个会触发这个 skill 的用户输入"
- 5 个中 ≥ 4 个合理 → 通过
- < 4 个 → 优化 description 后重测
