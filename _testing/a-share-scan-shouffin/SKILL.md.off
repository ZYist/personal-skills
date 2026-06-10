---
name: a-share-scan-shouffin
description: "A股全市场盘面扫描：实时行情筛选Top30 + 逐只quick-scan + 自动深度分析 + HTML合并 + Cloudflare Tunnel公网分享。输出日期文件夹含全部报告。触发词：扫描/盘面/行情/A股/股票/扫盘/选股/看盘/ market scan"
argument-hint: "[可选：板块/概念关键词，如 半导体 / 光伏 / AI]"
allowed-tools:
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - Bash
  - PowerShell
  - Agent
  - AskUserQuestion
  - Skill
  - ToolSearch
  - Monitor
---

# A股盘面扫描任务

用户输入: $ARGUMENTS

## 角色

你是一位**量化扫描分析师**。你的任务是用最快速度完成全市场筛选，然后对 Top 30 做速判，自动对最有价值的股票执行深度分析，最终产出一个日期文件夹，包含所有报告和公网访问链接。

## 输出目录结构

所有产出放在 `{工作目录}/{YYYY-MM-DD_HHmm}/` 文件夹中：

```
2026-05-23_1430/
├── a-share-scan-2026-05-23.md      # 速判报告
├── a-share-deep-2026-05-23.md      # 深度分析报告
├── consolidated-reports.html        # 交互式仪表盘（主入口，点击进入各股报告）
├── index.html                       # 自动重定向到 consolidated-reports.html
├── tunnel_links.txt                 # Cloudflare Tunnel 公网链接（第一条就是主页面）
├── tunnel_links.json                # 链接JSON格式
└── reports/                         # 原始HTML报告目录
    ├── 300136.SZ_20260523/
    │   ├── full-report.html
    │   └── full-report-standalone.html
    ├── 002463.SZ_20260523/
    │   ├── full-report.html
    │   └── full-report-standalone.html
    └── ...
```

## 前置条件 · 上下文空间检查

**本 skill 是重度 Agent 流水线**：10 步流程中会 spawn 6 个速判 Agent + 4-8 个深度分析 Agent + Cloudflare Tunnel，累计产生大量输出。经验值：完整流程约需 **70%+ 的剩余上下文空间**。

**在进入第 1 步之前，必须先做上下文空间检查**：

```
估算当前上下文使用率（检查系统提示中的 usage 百分比或 hook 告警信息）。

┌─────────────────────────┬──────────────────────────────────────────────────┐
│ 上下文剩余              │ 行动                                             │
├─────────────────────────┼──────────────────────────────────────────────────┤
│ < 30% 剩余（使用 >70%） │ 🛑 强制终止。告知用户：                          │
│                         │   "上下文已严重不足（剩余 < 30%），无法完成全流   │
│                         │   程。请新开会话后重试 /a-share-scan。           │
│                         │   新会话中 skill 会以全新上下文启动，保证         │
│                         │   Cloudflare Tunnel 公网链接一定能生成。"        │
│                         │   不执行任何步骤，等待用户新开会话。              │
├─────────────────────────┼──────────────────────────────────────────────────┤
│ 30%-50% 剩余            │ ⚠ 警告但继续。告知用户：                         │
│                         │   "上下文偏紧（剩余 ~X%）。建议新开会话以确保     │
│                         │   完整流程不中断。若继续，可能在深度分析阶段      │
│                         │   耗尽上下文，导致 Tunnel 链接无法生成。"         │
│                         │   若用户选择继续：优先保障 数据拉取 → 速判 →      │
│                         │   深度分析 → Tunnel，必要时自动跳过 HTML 仪表盘。 │
├─────────────────────────┼──────────────────────────────────────────────────┤
│ > 50% 剩余              │ ✅ 正常执行全流程（10 步）。                      │
└─────────────────────────┴──────────────────────────────────────────────────┘
```

**为什么必须在全新会话中运行**：

1. `/a-share-scan` 的最终产物是 **Cloudflare Tunnel 公网链接**，这是用户拿到手的可分享成果
2. 上下文耗尽时，即使前面的分析都做完了，Tunnel 启动步骤也可能被截断——导致**整个流程白跑**
3. 新会话 = 干净上下文 = Tunnel 链接 100% 能生成。代价仅是多一次 `/a-share-scan` 调用

**设计意图**：这个检查不是限制用户，而是保护用户的时间。在旧会话中跑 15 分钟分析后因上下文不足而截断，比新开会话多花 5 秒要糟糕得多。

---

## 执行流程（10 步，必须按顺序）

---

### 第 0 步 · 交易日检测 + 幂等性检查（新增）

**在执行任何数据拉取之前，先做两件事：**

**0a. 交易日检测**

```python
from datetime import datetime
import requests

now = datetime.now()
is_weekday = now.weekday() < 5  # 周一到周五

# 快速检测：拉一只大盘股看量比是否>0（非交易日量比为0或-1）
try:
    resp = requests.get('http://qt.gtimg.cn/q=sh600519', timeout=5)
    resp.encoding = 'gbk'
    # 量比字段通常在返回字符串中，非交易日通常为0
    is_trading = '量比' not in resp.text or '"0.00"' not in resp.text[:500]
except Exception:
    is_trading = is_weekday  # fallback：用工作日判断
```

若非交易日，**必须先告知用户**：

```
⚠️ 今天（{日期}）是非交易日。以下数据来自上一交易日收盘快照。
⚠ 注意：速判和深度分析使用 LLM Agent + WebSearch，每次运行结果可能不同（Agent 非确定性）。
   如需可复现结果，建议仅在交易日运行，或使用已有的同日输出文件夹。
```

然后**继续执行**（不终止）——非交易日也可以跑扫描，只是用户需要知道数据是旧的且 Agent 结果可能漂移。

**0b. 同日输出检测（幂等性）**

检查工作目录下是否已有今天的输出文件夹：

```powershell
$today_pattern = (Get-Date).ToString('yyyy-MM-dd') + "_*"
$existing = Get-ChildItem "D:\模拟炒股" -Directory -Name -Filter $today_pattern 2>$null
```

若已存在：

```
📁 检测到今天已有输出文件夹: {existing_folders}
  这些文件夹包含今天（或同一交易日）的扫描结果。

是否继续创建新的输出文件夹？
  - 是：创建新的 {date}_{HHmm} 文件夹，重新跑全流程
  - 否：直接查看已有结果（终止扫描，引导用户打开已有文件夹）
```

**交互模式**：始终在此处暂停询问。这是防止重复劳动的关键检查点。

**注意**：即使是非交易日，如果用户确认创建新文件夹，Agent 分析结果也会与上次不同（LLM 非确定性）。这是预期行为，不是 bug。如需完全可复现，应直接查看已有结果。

---

### 第 1 步 · 创建输出目录

```python
from datetime import datetime
import os

now = datetime.now()
date_str = now.strftime('%Y-%m-%d')
time_str = now.strftime('%H%M')
output_dir = f"D:\\模拟炒股\\{date_str}_{time_str}"
os.makedirs(output_dir, exist_ok=True)
os.makedirs(f"{output_dir}/reports", exist_ok=True)
print(f"输出目录: {output_dir}")
```

---

### 第 2-4 步（合并）· 一行命令完成数据拉取 + 筛选 + 打分

**直接运行 `screen_top20.py`**，已内置：
- 多源自动降级：腾讯 qt.gtimg.cn → 新浪 hq.sinajs.cn（东财 push2 因代理问题不再作为首选）
- 自动获取新浪股票列表（排除北交所）
- 筛选：剔除ST/退市/成交额<1亿/停牌/新股首日
- 打分：成交额(30%)+涨跌幅(25%,上涨1.3x)+量比(25%,截断15)+换手率(20%)

```powershell
python "{skill_dir}/screen_top20.py" --top 30 --output "{output_dir}/top30.json"
```

如果用户指定了板块/关键词（$ARGUMENTS），加 `--sector "$ARGUMENTS"`。

**⚠️ 不要再手写内联 Python 拉取数据**。内联 python -c 在 PowerShell 下有中文引号转义问题，且每次都要重新写逻辑。直接运行脚本即可。

**⚠️ 东财 push2.eastmoney.com 在网络代理下经常被拦截（本次耗时 15 分钟才确认不可用）。腾讯 qt.gtimg.cn 已证实可用且数据字段更全（含PE/PB/市值）。**

**异常处理**：
- 若脚本崩溃（非零退出码）：重试一次。若仍失败，提示用户"数据拉取失败，可能非交易时间或网络异常"，终止流程。
- 若 Top 30 不足 30 只（市场股票少或板块筛选过严）：有多少算多少，继续执行。若结果为空（0 只）：提示用户"筛选结果为空，请检查板块关键词或筛条件"，终止流程。

---

### 第 5 步 · 逐只 quick-scan（动态并行分组）

将 Top 30 按每 5 只一组分成 `ceil(N/5)` 组（默认 6 组），每组 spawn 一个 Agent 并行执行。Agent 数量随 `--top N` 自动缩放，确保无论 N 多大，quick-scan 耗时始终控制在 ~5 分钟。

每个 Agent 的 prompt 模板：

```
你是A股快速分析师。对以下{N}只股票各做一次"速判"。

维度：财报基本面、K线形态、估值水平、杀猪盘风险。
数据源：优先使用 WebSearch 搜索每只股票的最新财报和研报。不要用 requests 调东财API（push2 大概率被代理拦截）。不要用 akshare。

股票列表：
{从Top30中摘取本组5只的代码/名称/价格/涨跌幅/成交额/换手率/量比}

对每只股票获取：
- 最近季度营收/净利润
- PE/PB估值
- 近期K线均线位置
- 杀猪盘特征检测

请10位投资大佬投票（巴菲特/段永平/林奇/欧奈尔/木头姐/马克斯/米内尔维尼/章盟主/赵老哥/陈小群）。

每只股票输出：
- 一句话定调
- 综合评分(1-10)
- 10位大佬投票（买/观/回各几票）
- 杀猪盘安全等级（安全/警惕/危险）
- 关键风险1-2条

今天是 {当前日期}，是交易日。
```

**等待全部 Agent 完成后再继续。**

全部 Agent 完成后，汇总速判结果，展示摘要给用户：

```
[速判完成] Top30 速判汇总：
  ✅ 评分 ≥ 7.0: N 只
  ⚠ 评分 5.0-6.9: N 只
  ❌ 评分 < 5.0: N 只
  🔴 杀猪盘危险: N 只

是否继续写入速判报告并进入深度分析筛选？
```

**异常处理**：
- 若某些 Agent 超时/失败：用已完成的结果继续。若全部 Agent 失败，降级为"仅输出 Top 30 排名表"（跳过速判和深度分析，直接跳到第 9 步展示 Top 30 列表）。
- 若某只股票 Agent 未返回分析：在速判报告中标注"数据不足，跳过"。

**交互模式**：若 $ARGUMENTS 含 "交互" 关键词，⏸ 暂停等用户确认后再继续第 6 步。否则自动继续。

---

### 第 6 步 · 写入速判报告 md 文件

将全部结果写入 `{output_dir}/a-share-scan-{日期}.md`，格式如下：

```markdown
# A股盘面扫描速判报告 | {日期}

## 筛选参数
- 数据源：东方财富实时行情API
- 原始股票池：{N}只
- 筛选条件：剔除ST/退市/北交所/成交额<1亿/停牌
- 打分维度：成交额(30%)+涨跌幅(25%)+量比(25%)+换手率(20%)

## 综合排名表

| 排名 | 代码 | 名称 | 涨跌幅 | 成交额 | 换手率 | 量比 | 综合评分 | 杀猪盘风险 | 一句话结论 |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---|
| 1 | ... | ... | ... | ... | ... | ... | ... | ... | ... |

## 10大佬投票详情

（每只股票的大佬投票明细表）

## 个股速判详情

### 1. {代码} {名称}
- **一句话定调**：...
- **综合评分**：X.X/10
- **大佬投票**：买入X票 / 观望X票 / 回避X票
- **杀猪盘等级**：安全/警惕/危险
- **关键风险**：1. ... 2. ...
```

---

### 第 7 步 · 自动筛选 + 深度分析（并行执行）

**智能筛选规则**（不是全部 30 只都深度分析，而是选出最值得的）：

从 Top 30 中筛选需要深度分析的股票，标准：
1. **速判评分 ≥ 7.0** 且 **杀猪盘 ≠ 危险** → 强烈建议深度分析
2. **速判评分 ≥ 5.0** 且 **杀猪盘 = 安全** 且 **大佬看多率 ≥ 60%** → 建议深度分析
3. 其余 → 跳过深度分析（速判已足够）

通常筛选出 **4-8 只**进入深度分析。将筛选结果告知用户并等待确认：

```
[筛选结果] Top30 中有 N 只符合深度分析标准：
  ✅ 300136 信维通信 (评分9.0, 杀猪盘安全) → 深度分析
  ✅ 002463 沪电股份 (评分8.0, 杀猪盘安全) → 深度分析
  ✅ 603005 晶方科技 (评分7.0, 杀猪盘警惕) → 深度分析
  ⏭ 其余跳过深度分析（速判已足够）

是否对以上 N 只执行深度分析？深度分析所有股票将并行执行，总计约 4-5 分钟。
```

**异常处理**：
- 若筛选结果为 0 只（评分为空或无符合条件的股票）：跳过深度分析，直接进入第 8 步（仅合并速判报告，不生成深度报告）。
- 若某只股票深度分析中途失败（路径 A 脚本崩溃或路径 B Agent 超时）：跳过该股票，标注"深度分析失败"，继续其他股票。

**交互模式**：若 $ARGUMENTS 含 "交互" 关键词，⏸ 暂停等用户确认后再执行深度分析。否则自动继续。

**深度分析执行方式**：

先检测 `stock-deep-analyzer` 是否可用：

```powershell
$deep_available = Test-Path "{plugin_root}/skills/deep-analysis/scripts/run_real_test.py"
```

**路径 A：stock-deep-analyzer 可用（完整深度分析）**

对筛选出的股票，**并行执行**（每只股票独立运行，不互相阻塞）：

```powershell
# 对每只股票同时启动（并行）：
Set-Location "{plugin_root}/skills/deep-analysis/scripts"

# Stage 1: 数据采集（每只股票独立目录，可并行）
$env:UZI_LITE = '0'; python -c "from run_real_test import stage1; stage1('{股票名}')"

# 所有股票的 stage1 完成后，批量 spawn agent 分析：
# 每只股票 4 个 agent（基本面/技术面/估值面/风险面），所有股票的所有 agent 同时并行
# 各 agent 独立输出到各自股票的 bull_bear_*.json

# Stage 2: 生成报告（每只股票独立，可并行）
$env:UZI_SKIP_REVIEW = '1'; python -c "from run_real_test import stage2; stage2('{代码}')"
```

**⚠️ 重要**：每只股票的 stage1 → agents → stage2 内部仍需按顺序，但**不同股票之间全部并行**，不等待其他股票完成。深度分析总耗时 = 单只最慢股票的耗时（约 4-5 分钟），而非 N × 4 分钟。

---

**路径 B：stock-deep-analyzer 不可用（轻量级 Agent 深度分析）**

若 `$deep_available` 为 false，改用 Agent 做中等深度分析（比速判更深，比完整 analyze-stock 轻量）。

**所有符合条件的股票同时并行执行**，不等待其他股票完成。每只股票 spawn 4 个 Agent 并行分析，prompt 模板：

```
你是A股深度分析师。对 {股票代码} {股票名称} 做一次中等深度分析。

当前行情：价格 {price}，涨跌幅 {pct}%，成交额 {amount}，PE {pe}，PB {pb}。

请从以下角度深入分析（每个 Agent 负责一个角度）：
- Agent 1 基本面：近3年营收/利润趋势，ROE/毛利率变化，商誉/质押风险
- Agent 2 技术面：K线形态（周线+日线），均线排列，MACD/RSI/布林带位置，关键支撑/压力位
- Agent 3 估值面：PE/PB 历史分位，DCF 粗略估算，行业对比
- Agent 4 风险面：杀猪盘特征（换手率突变/对倒/市值异常），解禁/减持/ST风险

数据源：优先使用 WebSearch 搜索最新财报和研报。

输出格式（每只股票）：
- **综合评分**: X.X/10
- **一句话定调**: ...
- **看多理由 Top 3**: 1. ... 2. ... 3. ...
- **看空理由 Top 3**: 1. ... 2. ... 3. ...
- **杀猪盘等级**: 安全/警惕/危险（附检测依据）
- **关键风险**: ...
```

等待全部 Agent 完成，自行合并结果。

---

**两种路径都完成后**，提取关键结论：
- 综合评分 + 定调
- 评委投票分布（路径 A: 51 人 / 路径 B: 4 Agent）
- DCF 内在价值 vs 当前价（路径 B 可标注"粗略估算"）
- Top 3 看多/看空理由
- Great Divide 金句（路径 B 可跳过）
- 杀猪盘等级

全部深度分析完成后，将结果写入 `{output_dir}/a-share-deep-{日期}.md`：

```markdown
# A股深度分析报告 | {日期}

> 本报告由 /a-share-scan 自动生成。深度分析方式：{路径A: stock-deep-analyzer / 路径B: Agent 中等深度分析}。

## 总览

| 排名 | 代码 | 名称 | 深度评分 | 评委看多率 | DCF估值 | 杀猪盘 | 一句话结论 |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---|

## 逐只详情

### 1. {代码} {名称}
（每只股票的完整深度分析结论）

---
```

---

### 第 8 步 · 合并 HTML 报告 + 启动 Cloudflare Tunnel

**⚠ 启动 Cloudflare Tunnel 会占用本地端口 8899 并在公网暴露报告内容。**

在启动前确认：

```
[准备就绪] 深度分析报告已生成，即将：
  1. 合并 HTML 报告 → 交互式仪表盘
  2. 启动 Cloudflare Tunnel → 公网可访问（临时链接）

是否继续？
```

**交互模式**：若 $ARGUMENTS 含 "交互" 关键词，⏸ 暂停等用户确认后再继续。否则自动继续。

**8a. 复制报告到输出目录**

将 stock-deep-analyzer 生成的 reports 目录复制到 `{output_dir}/reports/`：

```powershell
# plugin_root 下的 reports 目录 → 输出目录
Copy-Item -Recurse -Force "{plugin_root}/skills/deep-analysis/scripts/reports/*" "{output_dir}/reports/"
```

**8b. 生成交互式仪表盘**

运行 `consolidate_reports.py` 生成**单页 SPA**（一个 HTML 文件，无跳转，无 iframe）。

该脚本的工作方式：
- **提取结构化数据**：从每份 standalone HTML 报告中提取核心结论、战况面板、作战计划、评委论据
- **统一暗色主题**：所有内容使用同一套 CSS，详情内联展开，视觉效果一致
- **无 iframe / 无跳转**：点击卡片后详情面板直接在当前页面展开，数据驱动渲染
- **体积极小**：5 只股票约 48KB（vs 旧版 4.3MB），加载瞬间完成

页面功能：
- **首页**：股票卡片网格，展示每只股票的评分/定调/一句话金句/安全等级
- **点击卡片**：内联展开详情面板，包含：
  - 股票头部（名称、代码、价格、涨跌、市值/PE/PB）
  - 评分卡片 + 安全体检
  - 核心结论（one-shot conclusion）
  - 战况面板（趋势/价位/量能/筹码/风险/催化）
  - 作战计划（Entry/Position/Stop/Target）
  - 评委交锋（看多/看空双标签页切换）
- **返回按钮**：收起详情，回到网格总览
- **筛选器**：可按高分(≥70)/安全/看多筛选

```powershell
python "{skill_dir}/consolidate_reports.py" `
  --input-dir "{output_dir}/reports" `
  --output "{output_dir}/consolidated-reports.html" `
  --title "A股深度分析 | {日期}"
```

其中 `{skill_dir}` 是本 skill 所在目录（`C:\Users\Shouffin\.claude\skills\a-share-scan\`）。

**8c. 启动 Cloudflare Tunnel**

```powershell
python "{skill_dir}/serve_reports.py" `
  --dir "{output_dir}" `
  --port 8899
```

脚本行为（改进版，不再死循环阻塞）：
1. 生成 `index.html` 重定向到 `consolidated-reports.html`
2. 用**独立子进程**启动 HTTP 服务器（pid 写入 stdout）
3. 启动 `cloudflared tunnel --url http://localhost:8899 --no-autoupdate`
4. 等待 cloudflared 输出 `https://xxx.trycloudflare.com` URL（最多 30 秒）
5. 链接**自动保存**到 `{output_dir}/tunnel_links.json` + `tunnel_links.txt`
6. **脚本退出** —— HTTP 服务器和 cloudflared 作为独立子进程继续运行

**⚠️ 注意**：
- 脚本退出后，两个子进程（HTTP 服务器 + cloudflared）持续在后台运行
- 关闭终端窗口会自动终止子进程；也可以用 `taskkill` 手动终止
- 如果 `cloudflared` 未安装，脚本会提示：`winget install cloudflare.cloudflared`
- Cloudflare Tunnel 链接是**临时的**，cloudflared 进程结束后即失效

**异常处理**：
- 若 `consolidate_reports.py` 输入目录为空（无 HTML 报告）：跳过仪表盘生成，提示用户"无深度分析报告可合并，仅提供 Markdown 报告"。
- 若 Cloudflare Tunnel 启动失败（cloudflared 未安装/超时/网络问题）：跳过公网分享，提示用户"本地文件在 {output_dir}，可手动查看"。不阻塞整个流程。

---

### 第 9 步 · 读取链接并展示

脚本退出后，直接读取 `{output_dir}/tunnel_links.json` 获取公网链接，然后展示最终汇总：

```
📁 输出目录: D:\模拟炒股\2026-05-23_1430\

📄 报告文件:
  • 速判报告: a-share-scan-2026-05-23.md
  • 深度报告: a-share-deep-2026-05-23.md
  • 交互式仪表盘: consolidated-reports.html（主入口）

🌐 公网访问链接 (Cloudflare Tunnel):
  >>> 主页面: https://xxx.trycloudflare.com/consolidated-reports.html
      （点击卡片进入各股详细报告，已修复乱码问题）

📊 深度分析覆盖: N/30 只
⏱️ 总耗时: XX 分钟
```

---

## 快速模式

如果用户说"快速扫描"或"仅速判"：
- 只执行第 1-6 步（跳过深度分析）
- 不合并 HTML，不启动 Cloudflare Tunnel
- 输出速判报告到日期文件夹

如果用户说"仅扫描不分析"：
- 只执行第 1-4 步（跳过 quick-scan 和深度分析）
- 输出 Top 30 排名表

## 交互模式

默认**全自动执行**（9 步一气呵成，不中断）。

如果需要人在回路确认，在 $ARGUMENTS 中加 "交互" 关键词，例如：

```
扫描今天的A股 交互
扫描半导体板块 交互
```

交互模式会在 4 个关键节点暂停等待确认：
1. **第 0 步（始终）**：同日输出检测 → 确认是否复用已有结果（防止重复劳动）
2. 速判完成后 → 确认是否继续写报告
3. 深度分析名单筛选后 → 确认是否执行深度分析
4. Cloudflare Tunnel 启动前 → 确认是否公网暴露

第 0 步的幂等性检查是**唯一不依赖"交互"关键词的检查点**——任何时候检测到同日已有输出，都会暂停询问。

## 注意事项

- **【最高优先级】数据拉取直接用 `screen_top20.py`，不要手写内联 Python**：
  - PowerShell 下 `python -c "..."` 中的 f-string 中文引号会导致 `SyntaxError: unterminated string literal`
  - 东财 push2.eastmoney.com 在本机代理(127.0.0.1:7890)下经常被拦截，腾讯 qt.gtimg.cn 已证实可靠
  - 上次执行浪费 15 分钟在"换 API → 换代理设置 → 换子域名 → 换协议"的死循环中
- **【Agent 数据源】速判 Agent 用 WebSearch，不要让它用 requests 调东财 API**（一样会被代理拦截）
- Windows 环境强制用 PowerShell 7（pwsh），不要用 Bash（中文乱码 + `$env:VAR=x` 语法不兼容）
- 今天日期用 Python `datetime.now()` 获取
- 工作目录默认为 `D:\模拟炒股`，如用户指定则用用户指定的
- plugin_root = `C:/Users/Shouffin/.claude/plugins/cache/uzi-skill/stock-deep-analyzer/3.4.3`
- skill_dir = `C:/Users/Shouffin/.claude/skills/a-share-scan/`
- Cloudflare Tunnel 链接是临时的，关闭进程后失效
- Windows 下 PowerShell 的续行符是 `` ` ``（反引号），不是 `\`
- 如果用户只想要速判不要深度分析，在 $ARGUMENTS 中加 "仅速判" 关键词
- `consolidate_reports.py` 的 Python f-string 模板中，JS 字符串内的 `\'` 会被 Python 消费为 `'`，需写 `\\'` 才能输出 `\'`
