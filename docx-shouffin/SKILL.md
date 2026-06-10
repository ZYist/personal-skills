---
name: docx-shouffin
description: 用于读取和创建 Word 文档（.docx）。读取时提取为 Markdown 并导出附件；创建时从本地 Markdown 生成带样式的 docx，支持标题、正文、表格、图片与常见文本样式配置。
---

# Docx

读取 `.docx` 为 Markdown，并从本地 Markdown 生成 `.docx` 文档。

## 前置要求

本技能依赖 `uv` 管理 Python 依赖。若系统未安装 `uv`，应先安装：

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## 何时使用

- 需要将 `.docx` 读取为 Markdown 供 AI 继续处理
- 需要把 Markdown 报告输出为 `.docx`
- 需要保留图片、表格和常见 Markdown 文本样式
- 需要通过默认样式、CLI 参数或 JSON 配置控制 Word 文档格式

## 功能一：读取 Docx

```bash
# Bash/Linux/macOS
scripts/docx-read <input.docx> [output_dir]

# PowerShell/Windows
scripts/docx-read.ps1 <input.docx> [output_dir]
```

### 参数说明

| 参数 | 必填 | 说明 |
|------|------|------|
| `input.docx` | 是 | Word 文件路径（.docx 格式） |
| `output_dir` | 否 | 输出目录（默认：`docs/extracted`） |

### 读取输出

- `<output_dir>/<filename>.md`
- `<output_dir>/<filename>/` 附件目录

默认输出目录：`docs/extracted`

## 功能二：创建 Docx

```bash
# Bash/Linux/macOS
scripts/docx-write <input.md> [output.docx] [--style-config style.json]

# PowerShell/Windows
scripts/docx-write.ps1 <input.md> [output.docx] [--style-config style.json]
```

### 参数说明

| 参数 | 必填 | 说明 |
|------|------|------|
| `input.md` | 是 | Markdown 源文件路径 |
| `output.docx` | 否 | 输出路径（默认：与输入同目录同名 .docx） |
| `--style-config` | 否 | JSON 样式配置文件路径 |
| `--body-size` | 否 | 正文字号（如 `12`） |
| `--h1-size` | 否 | H1 标题字号（如 `22`） |

### 创建支持范围

- 标题 1-6
- 普通段落
- 加粗、斜体、粗斜体
- 删除线
- 行内代码
- 引用块
- 无序列表、有序列表
- 分隔线
- 代码块
- 表格
- 图片
- 链接
- 软换行、硬换行

### 默认样式

未提供样式要求时，默认使用一套通用中文报告格式：

- 页面：A4
- 正文：`Microsoft YaHei` 11pt，1.5 倍行距
- 标题：H1-H6 逐级递减字号并加粗
- 代码块：等宽字体、浅灰底色
- 表格：首行加粗、浅色表头、细边框
- 图片：按页面宽度限制缩放

### 样式覆盖

简单覆盖优先使用 CLI 参数：

```bash
scripts/docx-write report.md report.docx --body-size 12 --h1-size 22
```

复杂样式使用 JSON 配置文件：

```bash
scripts/docx-write report.md report.docx --style-config .tmp/docx-style.json
```

合并优先级：CLI > JSON > 默认值。

### 样式配置 JSON Schema

```json
{
  "page": { "size": "A4", "margin_cm": 2.54 },
  "body": { "font": "Microsoft YaHei", "size_pt": 11, "line_spacing": 1.5 },
  "h1": { "font": "Microsoft YaHei", "size_pt": 18, "bold": true },
  "h2": { "font": "Microsoft YaHei", "size_pt": 16, "bold": true },
  "h3": { "font": "Microsoft YaHei", "size_pt": 14, "bold": true },
  "code_block": { "font": "Consolas", "size_pt": 10, "bg_color": "#F0F0F0" },
  "table": { "header_bold": true, "header_bg": "#D9E2F3", "border": true }
}

## AI 使用约定

若用户没有直接提供 Markdown，而是要求生成一份 docx 报告：

1. 先在 `docs/` 或 `.tmp/` 生成 Markdown 文件
2. 默认直接使用内置样式
3. 用户明确要求字体、字号、图片或表格格式时，再生成 JSON 配置文件或追加 CLI 参数
4. 最后调用 `scripts/docx-write` 生成 `.docx`

### 检查点

| 时机 | 动作 | 原因 |
|------|------|------|
| 读取 docx 前 | 确认文件路径和输出目录 | 避免覆盖已有文件 |
| 创建 docx 前 | 展示样式配置摘要，等用户确认 | 样式直接影响文档外观 |
| 覆盖已有文件前 | 明确告知将覆盖，请求确认 | 防止数据丢失 |

## 依赖要求

- Python 3.12+
- `python-docx`
- `markdown-it-py`
- `uv`

## 示例

```bash
# 读取 docx
scripts/docx-read report.docx

# 创建 docx
scripts/docx-write report.md report.docx

# 使用样式配置
scripts/docx-write report.md report.docx --style-config .tmp/docx-style.json
```

## 常见问题

### 文件不存在（读取）

```
Error: File not found: /path/to/file.docx
```

检查文件路径是否正确。使用绝对路径或确认相对路径基于当前工作目录。

### 不支持的格式

```
Error: Unsupported file format: .doc
```

只支持 `.docx` 格式，不支持旧版 `.doc`。用户需先用 Word 或 LibreOffice 另存为 `.docx`。

### 依赖未安装

```
Error: python-docx not found
```

首次运行时 `uv` 会自动安装依赖。如果失败，手动执行：
```bash
cd packages/docx && uv sync
```

### 样式配置 JSON 格式错误

```
Error: Invalid JSON in style config
```

检查 JSON 文件语法。常见问题：尾逗号、缺少引号、编码问题（确保 UTF-8）。

### 输出目录不存在（读取）

读取时如果指定的 `output_dir` 不存在，脚本会自动创建。如果权限不足会报错，需检查目录写入权限。

### 图片提取失败

如果 docx 中的图片格式不常见（如 EMF/WMF），可能无法提取。脚本会跳过这些图片并在输出中标注。

## 输出说明

### 读取输出

| 输出 | 路径 | 内容 |
|------|------|------|
| Markdown | `<output_dir>/<filename>.md` | 完整文本内容，图片引用为相对路径 |
| 附件目录 | `<output_dir>/<filename>/` | 提取的图片和其他嵌入文件 |

默认 `output_dir` 为 `docs/extracted`。

### 创建输出

| 场景 | 输出路径 |
|------|----------|
| 指定输出路径 | 用户指定的路径 |
| 未指定 | 与输入 `.md` 同目录，同名 `.docx` |
