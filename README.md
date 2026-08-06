# Shouffin's Personal Skills

Shouffin 的个人 Agent Skill 仓库，兼容 [Agent Skills](https://agentskills.io) 开放标准。

## Skill 列表

| Skill | 说明 | 作者 |
|-------|------|------|
| `docx-shouffin` | 读取和创建 Word 文档（.docx），支持 Markdown 互转 | Shouffin |
| `excel-shouffin` | 读取和创建 Excel 文件（.xlsx/.xlsm），支持 Markdown/JSON 格式互转 | Shouffin |
| `skill-forge-shouffin` | Skill 脚手架生成器，快速创建新的 Agent Skill | Shouffin |
| `session-analysis-shouffin` | 解析本地 Claude Code 会话记录（.jsonl），生成可读 Markdown 报告（对话回放 + 工具调用明细） | Shouffin |
| `work-report-pi` | 生成日报/周报（汇总本机 pi 会话 + 钉钉记录），仅终端输出不提交 | Shouffin |
| `darwin-skill` | Skill 自动优化器，基于 9 维度评估体系持续改进 Agent Skills（v2.0 集成 Microsoft SkillLens + SkillOpt） | [花叔 Huashu](https://github.com/alchaincyf) |

## 安装

使用 [`npx skills`](https://github.com/vercel-labs/skills) 一键安装，自动检测本机已安装的 AI CLI（Claude Code、Gemini CLI、GitHub Copilot、Cursor 等）并部署到对应目录：

```bash
# 查看仓库中所有可用的 skill
npx skills add ZYist/personal-skills --list

# 安装单个 skill
npx skills add ZYist/personal-skills --skill <skill-name>

# 安装全部 skill
npx skills add ZYist/personal-skills
```

例如：

```bash
npx skills add ZYist/personal-skills --skill docx-shouffin
```

## 更新

skill 安装后，后续拉取本仓库的最新版用 `update`（比重跑 `add` 更规范——保留原有 scope/agent 配置，语义也更清晰）：

```bash
# 更新单个 skill
npx skills@latest update <skill-name> -g

# 更新全部已安装的 skill
npx skills@latest update -g
```

> `-g` = 全局（用户级，最常见）；项目级用 `-p`；或 `-y` 让 CLI 自动判断 scope。

例如：

```bash
npx skills@latest update session-analysis-shouffin -g
```

