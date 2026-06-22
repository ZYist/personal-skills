# Excel Skill

读取和创建 Excel 文件（`.xlsx` / `.xlsm`）的 Claude Code Skill。

## 功能

- **读取**：将 Excel 文件提取为 Markdown 表格和 JSON 数据
- **创建**：通过 JSON 描述表格结构，生成带样式的 Excel 文件

## 前置要求

- Python 3.12+
- [uv](https://github.com/astral-sh/uv)（用于依赖管理）

## 使用

### 读取 Excel

```bash
# Bash
scripts/excel-reader <excel_file> [sheet_name]

# PowerShell
scripts/excel-reader.ps1 <excel_file> [sheet_name]
```

输出：
- `<源目录>/<文件名>.excel_reader.md` - Markdown 表格
- `<源目录>/<文件名>.excel_reader.json` - JSON 数据

### 创建 Excel

```bash
# Bash
scripts/excel-writer <input.json> [output.xlsx]

# PowerShell
scripts/excel-writer.ps1 <input.json> [output.xlsx]
```

JSON 格式：

```json
{
  "sheets": [
    {
      "name": "Sheet1",
      "title": "标题",
      "headers": ["列1", "列2"],
      "data": [["值1", "值2"]],
      "column_widths": [15, 20],
      "text_columns": []
    }
  ]
}
```

字段 `text_columns`：可选，1-based 列索引数组，强制按文本处理（保留前导零，如工号 `007`）。

## 依赖

- openpyxl
