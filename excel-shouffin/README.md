# excel-shouffin

> Excel 文件（.xlsx/.xlsm）读写器 — 读取 Excel 为 Markdown 表格 + JSON，或用 JSON 描述结构生成带样式的 Excel。

## 一句话

**你说「读这个 Excel」或「把数据导出成 Excel」，它调用 openpyxl 完成转换，合并单元格/样式自动处理。**

## 调用方式

```
/excel-shouffin    ← Claude Code 输入 slash command;其他 AI CLI(Gemini/Codex/Cursor/Copilot)直接描述需求即可触发
```

触发词（说任意一句即可）：
- 中文：「Excel」「xlsx」「电子表格」「表格数据」「创建 Excel」「导出 Excel」
- 英文：「read excel」「create spreadsheet」「export xlsx」

## 它做什么

| 场景 | 它做的事 |
|------|---------|
| 「读一下这个 Excel」 | 输出 Markdown 表格（可读）+ JSON（含合并单元格 / 数据类型元数据） |
| 「把这些数据做成 Excel」 | 按 JSON schema 组织 → 写临时 JSON → 生成带样式 .xlsx（标题行 / 表头 / 交替行 / 筛选 / 冻结） |
| 「读取某个 sheet」 | 指定 sheet 名只读那一个，不指定读全部 |

## 核心能力

1. **读取双格式** — Markdown（人读）+ JSON（程序处理，含合并单元格、数据类型）
2. **创建** — JSON 描述结构（sheets / headers / data / column_widths / merge_cells）→ 带样式 .xlsx
3. **样式自动化** — 标题行合并居中、表头蓝底白字、交替行、自适应列宽（中文双倍宽）、表头筛选 + 冻结
4. **类型自动转换** — 数字字符串→数字、浮点字符串→浮点、null→空、布尔→布尔
5. **跨平台脚本** — Bash + PowerShell 双版本

## 文件结构

```
excel-shouffin/
├── SKILL.md                # skill 指令（含检查点 + 反例清单 + 常见问题）
├── README.md               # 本文件
├── scripts/                # Bash + PowerShell 双版本入口脚本
└── packages/excel/         # Python 实现（main.py + writer.py + pyproject.toml + 独立 README）
```

## 使用示例

```bash
# 读取 Excel（全部 sheet）
scripts/excel-reader data.xlsx
# → data.excel_reader.md + data.excel_reader.json

# 读取指定 sheet
scripts/excel-reader data.xlsx "销售数据"

# 从 JSON 创建 Excel
scripts/excel-writer .tmp/data.json report.xlsx
```

JSON 结构示例：

```json
{
  "sheets": [
    {
      "name": "员工信息",
      "title": "2024年度员工信息表",
      "headers": ["姓名", "年龄", "部门"],
      "data": [["张三", 28, "技术部"]],
      "column_widths": [12, 8, 12]
    }
  ]
}
```

## 特性

- **依赖**：Python 3.12+、`uv`、openpyxl
- **只支持 .xlsx / .xlsm**（不支持旧版 .xls，需先另存为 .xlsx）
- **输出位置**：读取产物生成在源文件同目录

## License

MIT
