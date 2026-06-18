# docx-shouffin

> Word 文档（.docx）读写器 — 读取 .docx 为 Markdown（含图片/附件导出），或从本地 Markdown 生成带样式的 .docx。

## 一句话

**你说「读这个 Word」或「生成一份 docx 报告」，它调用 python-docx 完成转换，样式可控。**

## 调用方式

```
/docx-shouffin    ← 在 Claude Code 中直接输入
```

触发词（说任意一句即可）：
- 中文：「Word」「docx」「读取 Word」「创建 Word」「导出 Word」「word 文档」
- 英文：「read docx」「create word」「word document」

## 它做什么

| 场景 | 它做的事 |
|------|---------|
| 「读一下这个 .docx」 | 提取为 Markdown + 导出图片/附件到 `docs/extracted/` |
| 「把这份 Markdown 生成 docx」 | 用默认中文报告样式生成，或按 CLI 参数 / JSON 配置自定义字号字体 |
| 「生成一份 docx 报告」 | 先在 `.tmp/` 写 Markdown，样式确认后再转 docx |

## 核心能力

1. **读取** — `.docx` → Markdown，图片/附件按相对路径导出
2. **创建** — Markdown → `.docx`，支持标题 1-6、加粗/斜体/删除线、行内代码、引用、列表、分隔线、代码块、表格、图片、链接
3. **样式三档** — 默认中文报告样式（YaHei / A4 / 1.5 倍行距）→ CLI 参数覆盖（`--body-size` 等）→ JSON 配置文件精控
4. **跨平台脚本** — Bash（`scripts/docx-read`）与 PowerShell（`scripts/docx-read.ps1`）双版本
5. **依赖自举** — `uv` 管理 Python 依赖，首次运行自动初始化虚拟环境

## 文件结构

```
docx-shouffin/
├── SKILL.md                # skill 指令（含检查点 + 反例清单 + 常见问题）
├── README.md               # 本文件
├── scripts/                # Bash + PowerShell 双版本入口脚本
└── packages/docx/          # Python 实现（main.py + pyproject.toml + 独立 README）
```

## 使用示例

```bash
# 读取 docx → Markdown
scripts/docx-read input.docx docs/extracted

# 从 Markdown 创建 docx（默认样式）
scripts/docx-write report.md report.docx

# 自定义字号
scripts/docx-write report.md report.docx --body-size 12 --h1-size 22

# 复杂样式用 JSON 配置
scripts/docx-write report.md report.docx --style-config .tmp/docx-style.json
```

## 特性

- **依赖**：Python 3.12+、`uv`、python-docx、markdown-it-py
- **只读转换**：不修改原始 .docx；读取后改 .md 再重新生成
- **样式优先级**：CLI > JSON 配置 > 默认值
- **只支持 .docx**（不支持旧版 .doc，需先另存为 .docx）

## License

MIT
