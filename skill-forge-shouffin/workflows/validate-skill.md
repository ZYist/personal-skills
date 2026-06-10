# 验证 Skill 质量

## 7 大类检查

### 1. 结构检查
- [ ] 所有必需文件存在（SKILL.md 必须存在）
- [ ] 目录结构符合选定类型（A/B/C）
- [ ] 如需跨工具：薄壳文件齐全
- [ ] 如有薄壳：Cursor 入口 `.cursor/skills/<name>/SKILL.md` 存在

### 2. 行数预算
- [ ] SKILL.md ≤ 100 行
- [ ] 薄壳文件 ≤ 60 行
- [ ] rules/*.md 每个文件 ≤ 300 行
- [ ] workflows/*.md 每个文件 ≤ 200 行
- [ ] references/*.md 每个文件 ≤ 500 行

### 3. 占位符残留
```bash
grep -rn '{{' skills/{name}/
grep -rn 'FILL:' skills/{name}/
```
- [ ] 无 `{{...}}` 残留
- [ ] 无 `FILL:` 残留（每个都是必填项）

### 4. Description 质量
- [ ] 以 "Use when..." 开头
- [ ] 包含 ≥ 3 个触发短语（中英文）
- [ ] 包含同义词覆盖
- [ ] 描述触发条件，不总结工作流
- [ ] ≤ 500 字符
- [ ] 第三人称
- [ ] 与 Cursor 入口的 description 完全一致（如有）

### 5. 路由完整性
- [ ] Common Tasks 引用的每个文件路径都存在
- [ ] Always Read 引用的每个文件路径都存在
- [ ] Known Gotchas 的链接指向正确
- [ ] 有 "Other / unlisted task" 兜底条目
- [ ] Common Tasks ≤ 10 条

### 6. 内容质量
- [ ] 祈使句为主（"读取文件" 非 "你应该读取"）
- [ ] 解释了"为什么"
- [ ] 无 AI 腔废话（"说白了/换句话说/首先其次综上"）
- [ ] 无 "建议/可以考虑/根据情况/灵活把握" 软化措辞
- [ ] 规则文件有明确的失败分支

### 7. 跨工具一致性
- [ ] 所有薄壳的路由表内容一致
- [ ] Description 在所有入口文件中一致
- [ ] 无 runtime-specific 措辞锁定（除非 skill 名明确绑定单一 runtime）

## 自动化验证脚本（推荐）

```bash
# 在 skill 目录外执行
echo "=== 结构检查 ==="
test -f skills/{name}/SKILL.md && echo "✅ SKILL.md 存在" || echo "❌ SKILL.md 缺失"

echo "=== 行数检查 ==="
wc -l skills/{name}/SKILL.md

echo "=== 占位符检查 ==="
grep -rn '{{' skills/{name}/ || echo "✅ 无模板占位符残留"
grep -rn 'FILL:' skills/{name}/ || echo "✅ 无 FILL 标记残留"

echo "=== 路由引用检查 ==="
# 从 SKILL.md 提取引用路径，检查文件存在
grep -oP '`[^`]+`' skills/{name}/SKILL.md | tr -d '`' | while read f; do
  test -f "skills/{name}/$f" && echo "✅ $f" || echo "❌ $f 不存在"
done

echo "=== Description 字符数 ==="
# 提取 description 并计算字符数
```

## 触发测试

用以下方式测试 skill 是否能被正确激活：

1. 读 SKILL.md 的 description
2. 模拟 5 个不同用户输入
3. 检查每个输入是否能正确匹配到本 skill
4. ≥ 4/5 匹配 → 通过

### 8. 反模式扫描
- [ ] Description 未总结工作流（只写触发条件）
- [ ] SKILL.md ≤ 100 行（不是百科全书）
- [ ] 无 heredoc 生成痕迹（必须用 cp -R + sed）
- [ ] 高代价坑点在 gotchas.md 和 SKILL.md Known Gotchas 双重出现
- [ ] rules 文件中软措辞（"建议/可以考虑/灵活把握"）出现 < 3 处
- [ ] 薄壳覆盖所有目标 runtime（缺任一 = 该 runtime 失明）
- [ ] 占位符 `FILL:` 全部已替换（每个都是必填项）

## 🔴 CHECKPOINT
验证完成后，将所有结果展示给用户。
任何 ❌ 项必须在修复后才能视为完成。
