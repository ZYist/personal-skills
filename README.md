# Shouffin's Personal Skills

Shouffin 的个人 Agent Skill 仓库，兼容 [Agent Skills](https://agentskills.io) 开放标准。

## Skill 列表

| Skill | 说明 |
|-------|------|
| `docx-shouffin` | 读取和创建 Word 文档（.docx），支持 Markdown 互转 |
| `excel-shouffin` | 读取和创建 Excel 文件（.xlsx/.xlsm），支持 Markdown/JSON 格式互转 |
| `skill-forge-shouffin` | Skill 脚手架生成器，快速创建新的 Agent Skill |

## 安装

使用 [`npx skills`](https://github.com/vercel-labs/skills) 一键安装，自动检测本机已安装的 AI CLI（Claude Code、Gemini CLI、GitHub Copilot、Cursor 等）并部署到对应目录：

```bash
# 查看仓库中所有可用的 skill
npx skills add ZYist/personal-skills --list

# 安装单个 skill
npx skills add ZYist/personal-skills <skill-name>

# 安装全部 skill
npx skills add ZYist/personal-skills
```

例如：

```bash
npx skills add ZYist/personal-skills docx-shouffin
```
