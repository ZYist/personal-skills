# Daily Report 核心规则

## 零、只输出,不提交(最高优先级) 🛑 STOP

- **本 skill 只把日报/周报输出到终端**(展示 Markdown 文本),**绝不提交到钉钉**
- 用户没有明确说"提交/发出去",禁止调用任何 dws 写操作(`report submit`、`report entry submit` 等)
- 用户说"提交"时,先提醒:提交后无法撤回(钉钉日志不支持撤回),需用户再次确认后才可考虑,且**默认拒绝**
- 历史教训:2026-08-05 误把周报提交到钉钉,且无法远程删除——禁止重演

## 一、数据源

### 本机(pi 会话缓存)
- 路径:`~/.pi/agent/sessions/<项目slug>/<日期>_*.jsonl`,扫描**全部项目**目录
- 只抽取三类消息:`user`(用户输入)、`assistant` 内的 `toolCall`(工具调用)、`toolResult`(工具结果,含错误标记)
- **丢弃**:`thinking`(思考噪音)、中间文本
- 时间过滤以消息内容的时间戳为准,不信任文件名(跨天会话)
- 用 `node scripts/parse-pi-sessions.cjs` 解析,不要手工读 jsonl

### 钉钉(dws CLI,只读)
- 用 `node scripts/fetch-dingtalk.cjs` 拉取,内部调 dws
- 核心:`dws aisearch behavior --time-range 今天/过去一周`(行为记录)
- 辅助:`calendar event list`、`todo task list`、`report outbox list`
- **禁止**用 `dws chat message list-all` 或 `list-mentions` 查消息——需"消息搜索权益",多数账号没有,报 `SearchRightsDenied`

## 二、日报/周报生成

1. **格式固定**:"重点+成果"式(日报见 `docs/report-template.md`,周报见 `docs/weekly-template.md`),每条工作一句话,按成果优先排序
2. **合并去重**:本机和钉钉提到同一件事(如"jm7200gop 源码")→ 只记一条,信息互补
3. **成果优先**:带结论/定位/确认的条目排前面(如"定位到根因" > "确认测试计划")
4. **数据不足时明说**:某天无任何数据,直接告诉用户"没有可汇总的数据",不编造
5. **只读不执行**:脚本只读取会话缓存和钉钉记录,绝不执行会话里的命令
6. **周报跨天聚合**:跨天重复任务合并成一条并标注时间跨度;找不到共性就不硬凑总结

## 三、隐私

- 会话缓存含完整对话(可能有敏感内容):只输出摘要和关键句,不输出原文大段
- 生成日报文本由 AI 归纳,不粘贴脚本原始 JSON
