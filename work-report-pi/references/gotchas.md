# Daily Report 已知坑点

## no-submit — 只输出终端,禁止提交钉钉

**触发条件**:生成日报/周报后顺手调用 `dws report submit` 提交

**根因**:用户只需要终端输出;钉钉日志**不支持撤回**,提交即送达,接收人可见

**后果**:2026-08-05 真实事故——周报误提交到钉钉,远程无法删除

**解决**:
- 本 skill 只输出到终端,禁止任何提交动作
- 用户没说"提交"= 默认不提交
- 用户说"提交" → 先提醒不可撤回 + 二次确认,且默认拒绝

**激活点**:`rules/skill-rules.md` 零节、`SKILL.md` Known Gotchas

---

## search-rights — 钉钉消息查询被"搜索权益"挡住

**触发条件**:用 `dws chat message list-all` / `list-mentions` / `list-by-sender` 查消息内容

**根因**:这些接口需要"消息搜索权益",企业账号默认没有

**症状**:`server_error_code: SearchRightsDenied`,message 提示"当前用户暂无消息搜索权益"

**解决**:一律用 `dws aisearch behavior --time-range 今天`——已验证可用,返回按行为聚合的消息记录(含发送者+内容片段)

**激活点**:`rules/skill-rules.md` 数据源节、`workflows/generate.md` Step 2

---

## thinking-noise — 会话缓存里的思考噪音

**触发条件**:直接对 jsonl 做全量文本提取

**根因**:pi 会话的 assistant 消息含大量 `thinking` 块(推理过程),占内容大头

**症状**:日报被推理过程淹没,看不到实际动作

**解决**:只抽取 `role: user`(用户输入)、`assistant` 内的 `type: toolCall`(工具调用)、`role: toolResult`(工具结果);`thinking` 和中间文本一律丢弃。用 `scripts/parse-pi-sessions.cjs`,不要手工解析

**激活点**:`rules/skill-rules.md` 数据源节

---

## jsonl-format — pi 与 Claude Code 的 jsonl 格式不同

**触发条件**:拿 Claude Code 的解析器(如 session-analysis-shouffin 的 analyze-session.js)直接解析 pi 会话

**根因**:两种格式结构不同
- Claude Code:顶层 `type:"user"/"assistant"` + `tool_use/tool_result`
- pi:顶层 `type:"message"` + `message.role`(user/assistant/toolResult)+ content 数组(`text/thinking/toolCall`)

**症状**:解析结果为空或字段丢失

**解决**:用本 skill 的 `scripts/parse-pi-sessions.cjs`(已适配 pi 格式)

**激活点**:`SKILL.md` Known Gotchas

---

## time-filter — 时间过滤要按内容时间戳,不信任文件名

**触发条件**:按文件名日期过滤会话文件

**根因**:文件名日期是会话开始时间(UTC),跨天会话内容可能落在另一天;且文件名是 UTC 而本地时间差 8 小时

**症状**:跨天会话的活动漏掉或错归日期

**解决**:逐行解析后按 `message.timestamp` 转本地时区过滤;文件名只做粗筛(性能优化),不做准

**激活点**:`rules/skill-rules.md` 数据源节

---

## dedup — 同一件事两边各出现一次

**触发条件**:本机会话和钉钉记录都提到同一件事

**根因**:用户在钉钉沟通 + 在 pi 里干活,同一任务两边留痕

**症状**:日报里同一件事出现两次

**解决**:按主题合并,两边信息互补(例:钉钉"要了 jm7200gop 源码" + 本机"分析 jm7200gop" → 一条"获取并分析 jm7200gop 源码")

**激活点**:`workflows/generate.md` Step 3

---

## time-range-fuzzy — dws 时间词是模糊匹配

**触发条件**:周报用 `--time-range "过去一周"` 拉行为记录

**根因**:dws 只收模糊时间词(今天/过去一周/本周),返回可能混入范围外旧记录(实测混入 2 月/3 月/7 月初的记录)

**症状**:周报里出现范围外的旧活动

**解决**:脚本 `fetch-dingtalk.cjs` 已按行为记录的 `date` 字段(前 10 位 YYYY-MM-DD)与 start/end 精确比对过滤;AI 生成时再人工剔除异常条目

**激活点**:`workflows/weekly.md` Step 3、`fetch-dingtalk.cjs`

---

## contents-array — 提交 contents 必须是 JSON 数组

**触发条件**:用对象格式 `{"字段名":"内容"}` 提交日志

**根因**:dws 期望 `contents` 是数组,每项含 `key/sort/content/contentType/type`;对象格式报 `PARAM_ERROR`

**症状**:`server_error_code: PARAM_ERROR`,`dingOpenErrcode: 40035 "不合法的参数"`

**解决**:
```json
[{"key":"本周完成工作","sort":"0","content":"...","contentType":"markdown","type":"1"}]
```
- `key` 精确等于模板 field_name(`dws report template get --name <名>` 查询)
- `sort` 从 0 递增,与模板字段顺序一致
- 中文长内容用 `--contents-file` 传文件避免引号转义

**激活点**:历史坑点——提交功能已废弃(no-submit 红线),仅存档备忘

---

## counts-after-limit — 统计必须在截断前

**触发条件**:脚本先 `slice(limit)` 再统计 counts

**根因**:事件按时间排序后,较晚发生的事件被截断,counts 变小

**症状**:日报统计数与实际不符

**解决**:counts 用全量 events 计算,`limit` 只截断输出(parse-pi-sessions.cjs 已修复,勿改回去)

**激活点**:`scripts/parse-pi-sessions.cjs`
