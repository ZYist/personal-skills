---
name: excel
description: 用于读取和创建 Excel 文件。读取时支持 .xlsx/.xlsm 提取数据为 Markdown 和 JSON 格式；创建时通过 JSON 描述表格结构生成带样式的 Excel。当用户提到 Excel、xlsx、电子表格、表格数据、创建 Excel、导出 Excel 时触发。
---

# Excel Reader & Writer

读取 Excel 文件并输出 Markdown 和 JSON 两种格式；通过 JSON 描述表格结构生成带样式的 Excel 文件。

## 前置要求

**重要**：本技能依赖 `uv` 进行 Python 依赖管理。如果用户系统没有安装 `uv`，请停止任务执行并告知用户：

> 当前系统未安装 `uv`，无法执行此技能。请先安装 `uv`：
> ```bash
> curl -LsSf https://astral.sh/uv/install.sh | sh
> ```

## 何时使用

- 需要读取 .xlsx 或 .xlsm 文件
- 需要提取 Excel 数据供 AI 分析
- 需要处理包含合并单元格的表格
- 需要读取特定 sheet 或全部 sheets
- 需要根据数据创建带样式的 Excel 文件
- 需要将结构化数据导出为 Excel

---

## 功能一：读取 Excel

### 工作流程

1. 确认 Excel 文件路径（.xlsx 或 .xlsm）
2. 可选：指定 sheet 名称（不指定则读取所有）
3. 调用脚本，生成 `.excel_reader.md` 和 `.excel_reader.json`
4. 展示 Markdown 内容供用户查看

### 快速开始

```bash
# Bash/Linux/macOS
scripts/excel-reader <excel_file> [sheet_name]

# PowerShell/Windows
scripts/excel-reader.ps1 <excel_file> [sheet_name]
```

### 参数说明

| 参数 | 必填 | 说明 |
|------|------|------|
| `excel_file` | 是 | Excel 文件路径（.xlsx 或 .xlsm） |
| `sheet_name` | 否 | 指定读取的 sheet 名称，不指定则读取所有 |

### 输出格式

执行成功后，会在**源文件所在目录**生成两个文件：
```
Success: <文件名>
Markdown: <源文件目录>/<文件名>.excel_reader.md
JSON: <源文件目录>/<文件名>.excel_reader.json
```

**输出文件命名规则**：
- 源文件 `demo.xlsx` → 输出 `demo.excel_reader.md` 和 `demo.excel_reader.json`
- 源文件 `/path/to/data.xlsx` → 输出 `/path/to/data.excel_reader.md` 和 `/path/to/data.excel_reader.json`

**Markdown 文件**：包含格式化的表格，适合直接阅读。

**JSON 文件**：包含完整元数据（合并单元格信息、数据类型等），适合程序处理。

### 读取示例

```bash
# 读取所有 sheets
scripts/excel-reader data.xlsx
# 输出:
# Success: data.xlsx
# Markdown: /current/path/data.excel_reader.md
# JSON: /current/path/data.excel_reader.json

# 读取指定 sheet
scripts/excel-reader data.xlsx "销售数据"

# 查看生成的 Markdown
cat data.excel_reader.md
```

### 功能特性

**合并单元格支持**：自动识别合并单元格，左上角包含实际值，其他标记为 `merged`。

**数据类型识别**：自动识别 string、number、boolean、date、empty、merged 类型。

**多 Sheet 支持**：不指定 sheet_name 时读取所有 sheets，指定时只读取指定 sheet。

---

## 功能二：创建 Excel

通过 JSON 文件描述表格结构，生成带样式的标准 Excel 文件。

### 工作流程

1. 收集数据（用户提供的信息、文件、网页等）
2. 按 JSON 规范组织数据结构（见下方 schema）
3. 保存为临时 JSON 文件（如 `.tmp/data.json`）
4. 调用脚本生成 `.xlsx` 文件
5. 告知用户输出文件路径

### 快速开始

```bash
# Bash/Linux/macOS
scripts/excel-writer <input.json> [output.xlsx]

# PowerShell/Windows
scripts/excel-writer.ps1 <input.json> [output.xlsx]
```

### 参数说明

| 参数 | 必填 | 说明 |
|------|------|------|
| `input.json` | 是 | JSON 文件路径，描述 Excel 结构 |
| `output.xlsx` | 否 | 输出 Excel 文件路径（默认：与输入同目录同名，后缀 .xlsx） |

### JSON 格式规范

```json
{
  "sheets": [
    {
      "name": "员工信息",
      "title": "2024年度员工信息表",
      "headers": ["姓名", "年龄", "部门", "入职日期"],
      "data": [
        ["张三", 28, "技术部", "2022-03-15"],
        ["李四", 32, "市场部", "2020-08-01"],
        ["王五", 25, "技术部", "2023-01-10"]
      ],
      "column_widths": [12, 8, 12, 15],
      "merge_cells": []
    }
  ]
}
```

### 字段说明

| 字段 | 层级 | 必填 | 说明 |
|------|------|------|------|
| `sheets` | 顶层 | 是 | Sheet 配置数组，至少包含一个 sheet |
| `name` | sheet | 否 | Sheet 名称（默认：Sheet1） |
| `title` | sheet | 否 | 标题行文本，会合并居中显示在首行 |
| `headers` | sheet | 否 | 列标题数组，带蓝色背景白色加粗样式 |
| `data` | sheet | 是* | 二维数组，每行一个数据行 |
| `column_widths` | sheet | 否 | 列宽数组；不指定时自动根据内容计算 |
| `merge_cells` | sheet | 否 | 合并单元格范围数组，如 `["A1:D1"]` |

> *`data` 和 `headers` 至少提供一个，否则该 sheet 会被跳过。

### 数据类型自动转换

JSON 中的值会自动转换为 Excel 原生类型：
- 数字字符串 `"25"` → Excel 数字 `25`
- 浮点字符串 `"3.14"` → Excel 数字 `3.14`
- 纯文本 → Excel 文本
- `null` → 空单元格
- 布尔值 → Excel 布尔值

### 默认样式

创建的 Excel 文件自动包含以下样式：

| 元素 | 样式 |
|------|------|
| 标题行 | 加粗、14号字、居中、合并至所有列、行高30 |
| 表头行 | 蓝色背景(#4472C4)、白色加粗字、居中、行高24 |
| 数据行 | 居中对齐、自动换行、细边框 |
| 交替行 | 偶数行浅蓝背景(#D9E2F3) |
| 列宽 | 自适应内容宽度（支持中文字符双倍宽度计算） |
| 筛选 | 表头自动启用筛选器 |
| 冻结 | 表头行冻结（标题行+表头行以下冻结） |

### 创建示例

**最简示例**（无标题无表头）：
```json
{
  "sheets": [
    {
      "data": [
        ["张三", 25, "北京"],
        ["李四", 30, "上海"]
      ]
    }
  ]
}
```

**完整示例**（多 Sheet、标题、表头、列宽）：
```json
{
  "sheets": [
    {
      "name": "销售数据",
      "title": "2024年Q1销售报表",
      "headers": ["产品", "销量", "单价", "销售额"],
      "data": [
        ["产品A", 150, 29.9, 4485],
        ["产品B", 200, 19.9, 3980],
        ["产品C", 80, 49.9, 3992]
      ],
      "column_widths": [15, 10, 10, 12]
    },
    {
      "name": "汇总",
      "headers": ["指标", "数值"],
      "data": [
        ["总销量", 430],
        ["总销售额", 12457]
      ]
    }
  ]
}
```

**使用方式**：
```bash
# 将 JSON 数据写入文件后调用
scripts/excel-writer data.json report.xlsx
# 输出:
# Success: /path/to/report.xlsx

# 不指定输出路径，默认生成同目录同名 .xlsx
scripts/excel-writer data.json
# 输出:
# Success: /path/to/data.xlsx
```

### AI 使用模式

当用户需要将任意数据创建为 Excel 时：

1. **收集数据**：从用户提供的信息、文件、网页等来源获取结构化数据
2. **生成 JSON**：将数据组织为上述 JSON 格式，保存为临时文件（如 `.tmp/data.json`）
3. **调用脚本**：执行 `scripts/excel-writer .tmp/data.json [output.xlsx]`
4. **告知用户**：输出 Excel 文件路径

### 检查点

| 时机 | 动作 | 原因 |
|------|------|------|
| 读取 Excel 前 | 确认文件路径和目标 sheet | 避免读错文件 |
| 创建 Excel 前 | 展示 JSON 结构摘要（sheet 数、行列数），等用户确认 | 确保数据结构正确 |
| 覆盖已有文件前 | 明确告知将覆盖，请求确认 | 防止数据丢失 |

---

## 依赖要求

- Python 3.12+
- openpyxl
- uv（用于依赖管理）

首次运行会自动初始化虚拟环境并安装依赖。

## 常见问题

### 文件不存在（读取）

```
Error: Excel file not found: /path/to/file.xlsx
```

检查文件路径是否正确。使用绝对路径或确认相对路径基于当前工作目录。

### 不支持的格式（读取）

```
Error: Unsupported file format: .xls
```

只支持 `.xlsx` 和 `.xlsm` 格式，不支持旧版 `.xls`。用户需先用 Excel 或 LibreOffice 另存为 `.xlsx`。

### Sheet 不存在（读取）

```
Error: Sheet 'Data' not found. Available sheets: Sheet1, Sheet2
```

使用列出的可用 sheet 名称。

### JSON 格式错误（创建）

```
Error: Invalid JSON format: Expecting value: line 1 column 1
```

检查 JSON 文件语法是否正确。常见问题：尾逗号、缺少引号、编码问题（确保 UTF-8）。

### 缺少 sheets 配置（创建）

```
Error: 'sheets' array is required and must not be empty
```

JSON 必须包含 `sheets` 数组且至少一个 sheet 配置。

### 依赖未安装

```
Error: openpyxl not found
```

首次运行时 `uv` 会自动安装依赖。如果失败，手动执行：
```bash
cd packages/excel && uv sync
```

### 输出目录不存在（创建）

创建 Excel 时，如果输出路径的父目录不存在，脚本会自动创建。如果权限不足会报错，需检查目录写入权限。

### 文件被占用（创建）

```
Error: Permission denied: /path/to/output.xlsx
```

目标文件可能被 Excel 或其他程序打开。关闭后重试。

## 输出说明

### 读取输出

| 输出 | 路径 | 内容 |
|------|------|------|
| Markdown | `<源目录>/<文件名>.excel_reader.md` | 格式化表格，适合直接阅读 |
| JSON | `<源目录>/<文件名>.excel_reader.json` | 完整元数据（合并单元格、数据类型） |

### 创建输出

| 场景 | 输出路径 |
|------|----------|
| 指定输出路径 | 用户指定的路径 |
| 未指定 | 与输入 JSON 同目录，同名 `.xlsx` |
