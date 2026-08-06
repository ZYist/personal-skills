# 生成日报主流程

## 输入
- 可选 `--date YYYY-MM-DD`(默认今天,本机时区)
- 可选范围:只看本机 / 只看钉钉(默认两者都看)

## 步骤

### Step 1: 拉本机活动数据
```bash
node scripts/parse-pi-sessions.cjs [--date YYYY-MM-DD]
```
- 输出 JSON:`counts`(用户消息数/工具调用数/工具错误数)+ `truncated`(明细是否被截断)+ `events`(按时间排序的 user/tool/toolResult 列表)
- 关注点:
  - `user` 消息 → 用户今天提了什么需求
  - `tool` 调用 → 实际做了什么操作(bash/ssh/edit 等)
  - `tool_errors` > 0 → 今天有失败操作,值得在日报体现
  - **`truncated: true` → 明细被截断,日报会漏报**:用更大 `--limit` 重跑(如 `--limit 5000`)直到 `truncated: false`,再继续

### Step 2: 拉钉钉数据
```bash
node scripts/fetch-dingtalk.cjs [--date YYYY-MM-DD]
```
- 输出 JSON:`behavior`(行为记录:消息/文件/确认)+ `calendar`(日程)+ `todo`(待办)+ `report_outbox`(今日已提交日志)+ `errors`
- 关注点:
  - `behavior` → 与谁的对话、关键内容(发送者+消息片段)
  - `calendar` → 今天开的会
  - `errors` 非空 → 某数据源不可用,继续用其他数据源,并向用户说明

### Step 3: 合并与去重
- 同一件事在本机和钉钉各出现一次 → 合并为一条,两边信息互补(例:本机"分析 jm7200gop 源码" + 钉钉"向杜豪男要 jm7200gop 代码" → 一条:获取并分析 jm7200gop 源码)
- 钉钉 behavior 一条可能含多条消息 → 提取关键句(发送者+内容),不整段粘贴

### Step 4: 生成日报
- 按 `docs/report-template.md` 的"重点+成果"格式
- 每条一行:动宾结构 + 成果/结论(如有)
- 排序:带成果/结论的优先,会议/沟通次之

### Step 5: 预览
🔴 **CHECKPOINT**:生成日报后,先展示给用户确认,不直接结束。
- 用户说"改" → 回到 Step 3/4 调整
- 用户满意 → 完成(本 skill 只输出终端,不提交钉钉)

## 失败分支(if-then 三段式)

| 触发条件 | 一线修复 | 仍失败兜底 |
|---------|---------|-----------|
| `parse-pi-sessions` 输出 `error` | 确认 sessions 目录存在(`~/.pi/agent/sessions/`) | 只用钉钉数据,告知用户无会话记录 |
| `fetch-dingtalk` errors 含行为/日历失败 | 单独重跑该 dws 命令确认错误 | 用剩余可用数据源,告知用户哪项不可用及原因 |
| 两个数据源都无数据 | 核对日期参数(今天/指定日)是否正确 | 明确告知"今天没有可汇总的数据",不编造 |
| dws 命令报 `unknown command` | 先跑 `dws <path> --help` 查证,修正一次 | 停止并报告完整错误,不反复变通 |
| `truncated: true` 且重跑后仍截断 | 继续加大 `--limit`(5000 → 10000) | 以 `counts` 和 `days` 聚合为准生成,标注数据不完整 |
