# Docx Skill

读取和创建 Word 文档（`.docx`）的 Claude Code Skill。

## 功能

- **读取**：将 `.docx` 文件提取为 Markdown，支持导出图片和附件
- **创建**：从 Markdown 生成带样式的 Word 文档，支持标题、表格、图片、代码块等

## 前置要求

- Python 3.12+
- [uv](https://github.com/astral-sh/uv)（用于依赖管理）

## 使用

### 读取 Docx

```bash
# Bash
scripts/docx-read <input.docx> [output_dir]

# PowerShell
scripts/docx-read.ps1 <input.docx> [output_dir]
```

输出：
- `<output_dir>/<filename>.md` - Markdown 内容
- `<output_dir>/<filename>/` - 提取的图片和附件

### 创建 Docx

```bash
# Bash
scripts/docx-write <input.md> [output.docx] [--style-config style.json]

# PowerShell
scripts/docx-write.ps1 <input.md> [output.docx] [--style-config style.json]
```

支持内容：标题 1-6、段落、加粗/斜体/删除线、行内代码、引用、列表、分隔线、代码块、表格、图片。

### 样式覆盖

```bash
# CLI 参数覆盖
scripts/docx-write report.md report.docx --body-size 12 --h1-size 22

# JSON 配置文件覆盖
scripts/docx-write report.md report.docx --style-config style.json
```

## 依赖

- python-docx
- markdown-it-py
