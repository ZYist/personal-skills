"""
交互式股票深度分析仪表盘（单页 SPA，无 iframe，无跳转）。

从多份 stock-deep-analyzer HTML 报告提取结构化数据，生成一个自包含的 HTML 文件：
  首页 → 股票卡片网格（评分/信号/价格/一句话）
  点击 → 内联展开详情面板（统一暗色主题）

用法: python consolidate_reports.py --input-dir <报告目录> --output <输出HTML>
"""
import argparse
import os
import re
import glob
import json
from datetime import datetime

PLUGIN_ROOT = "C:/Users/Shouffin/.claude/plugins/cache/uzi-skill/stock-deep-analyzer/3.4.3"


# ═══════════════════════════════════════════════════════════════
# 数据提取
# ═══════════════════════════════════════════════════════════════

def parse_one_liner(filepath):
    """解析 one-liner.txt，提取摘要"""
    info = {}
    if not os.path.exists(filepath):
        return info
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = [l.strip() for l in f.readlines() if l.strip()]

    for line in lines:
        m = re.search(r'体检结果[：:]\s*(\d+\.?\d*)\s*分', line)
        if m:
            info['score'] = float(m.group(1))
        for kw in ['强烈看多', '可以蹲一蹲', '谨慎', '回避', '中性']:
            if kw in line:
                info['tone'] = kw
                break
        m = re.search(r'(\d+)\s*位大佬里\s*(\d+)\s*人喊买', line)
        if m:
            info['total_voters'] = int(m.group(1))
            info['bullish_voters'] = int(m.group(2))
        if '——' in line or ('派' in line and '说' in line):
            if '体检结果' not in line and '杀猪盘' not in line:
                info['punchline'] = line.replace('💬 ', '').strip()

    return info


def extract_html_sections(html):
    """从完整 standalone HTML 中提取关键数据区块。返回 dict。"""
    data = {}

    # ── 股票名 / 代码 / 行业 ──
    m = re.search(r'<h1 class="stock-name">(.+?)</h1>', html)
    if m:
        data['name'] = m.group(1).strip()

    m = re.search(r'<div class="stock-code">(.+?)</div>', html)
    if m:
        code_parts = m.group(1).strip().split('·')
        data['ticker'] = code_parts[0].strip()
        data['sector'] = code_parts[1].strip() if len(code_parts) > 1 else ''

    # ── 价格 / 涨跌 ──
    m = re.search(r'<div class="price">(.+?)</div>', html)
    data['price'] = m.group(1).strip() if m else '—'

    m = re.search(r'<div class="change\s+(up|down)">(.+?)</div>', html)
    if m:
        data['change_dir'] = m.group(1)
        data['change_pct'] = m.group(2).strip()
    else:
        data['change_dir'] = ''
        data['change_pct'] = '—'

    # ── 市值 / PE / PB ──
    chips = re.findall(r'<div class="chip"><strong>(MCAP|PE|PB)</strong>(.+?)</div>', html)
    for key, val in chips:
        data[key.lower()] = val.strip()

    # ── 评分 ──
    m = re.search(r'<div class="score-giant">(\d+\.?\d*)</div>', html)
    if m:
        data['html_score'] = float(m.group(1))
    m = re.search(r'<div class="score-verdict">(.+?)</div>', html)
    if m:
        data['score_verdict'] = m.group(1).strip()

    # ── 安全等级 ──
    m = re.search(r'<div class="bento safety-card\s+(\w+)">', html)
    if m:
        data['safety_class'] = m.group(1)  # green / yellow / orange / red
    m = re.search(r'<strong>杀猪盘体检\s*·\s*(.+?)</strong>', html)
    if m:
        data['safety_label'] = m.group(1).strip()
    m = re.search(r'<span>数据正常[，,].+?</span>', html)
    if m:
        data['safety_detail'] = m.group(0).replace('<span>', '').replace('</span>', '').strip()

    # ── 核心结论 ──
    m = re.search(r'<div class="core-conclusion">.*?<div class="text">(.+?)</div>', html, re.DOTALL)
    if m:
        data['conclusion'] = m.group(1).strip()

    # ── Dashboard data-cell ──
    cells = re.findall(
        r'<div class="data-cell[^"]*">\s*<div class="icon">(.+?)</div>\s*<div class="key">(.+?)</div>\s*<div class="value">(.+?)</div>',
        html, re.DOTALL
    )
    for icon, key, value in cells:
        key_lower = key.strip().lower()
        # 第一个词作为键名
        label = key_lower.split()[0] if key_lower.split() else key_lower
        data[f'cell_{label}'] = value.strip()

    data['cells_raw'] = [(icon.strip(), key.strip(), value.strip()) for icon, key, value in cells]

    # ── Battle Plan ──
    plan_fields = re.findall(
        r'<div class="plan-field"><span class="k">(.+?)</span><span class="v">(.+?)</span></div>',
        html
    )
    data['battle_plan'] = [(k.strip(), v.strip()) for k, v in plan_fields]

    # ── Chat 消息（只看 bullish 和 bearish，skip 类忽略）──
    chat_msgs = re.findall(
        r'<div class="chat-msg\s+(bullish|bearish)".*?id="msg-(\w+?)">\s*'
        r'<img[^>]*>\s*'
        r'<div class="msg-body">\s*'
        r'<div class="msg-meta">\s*'
        r'<span class="msg-name">(.+?)</span>\s*'
        r'<span class="msg-group-tag">(.+?)</span>.*?'
        r'<span class="msg-score-badge">(.+?)</span>.*?'
        r'<div class="msg-reasoning">(.+?)</div>'
        r'(?:<div class="msg-comment">(.+?)</div>)?\s*'
        r'<div class="msg-verdict">(.+?)</div>',
        html, re.DOTALL
    )
    bull_args = []
    bear_args = []
    for stance, msg_id, name, group, score_str, reasoning, comment, verdict in chat_msgs:
        try:
            score = int(re.search(r'(\d+)', score_str).group(1))
        except (ValueError, AttributeError):
            score = 0
        arg = {
            'name': name.strip(),
            'group': group.strip(),
            'score': score,
            'reasoning': re.sub(r'\s+', ' ', reasoning.strip())[:200],
            'comment': (comment or '').strip().replace('💬 ', '') if comment else '',
            'verdict': verdict.strip(),
        }
        if stance == 'bullish':
            bull_args.append(arg)
        else:
            bear_args.append(arg)

    # 按分数降序
    bull_args.sort(key=lambda x: x['score'], reverse=True)
    bear_args.sort(key=lambda x: x['score'], reverse=True)
    data['bull_args'] = bull_args[:12]
    data['bear_args'] = bear_args[:12]

    return data


def scan_reports(input_dir):
    """扫描报告目录，收集所有报告的结构化数据"""
    reports = []

    html_files = sorted(glob.glob(os.path.join(input_dir, '**', '*standalone*.html'), recursive=True))
    if not html_files:
        html_files = sorted(glob.glob(os.path.join(input_dir, '**', '*.html'), recursive=True))
    html_files = [f for f in html_files if 'consolidated' not in os.path.basename(f)]

    # 同时检查 plugin_root
    plugin_reports = os.path.join(PLUGIN_ROOT, 'skills', 'deep-analysis', 'scripts', 'reports')
    if os.path.isdir(plugin_reports) and os.path.abspath(plugin_reports) != os.path.abspath(input_dir):
        extra = sorted(glob.glob(os.path.join(plugin_reports, '**', '*standalone*.html'), recursive=True))
        existing = {os.path.basename(os.path.dirname(f)) for f in html_files}
        for f in extra:
            if os.path.basename(os.path.dirname(f)) not in existing:
                html_files.append(f)

    for fpath in html_files:
        report_dir = os.path.dirname(fpath)
        stock_code = os.path.basename(report_dir)
        code_parts = stock_code.split('_')
        ticker = code_parts[0] if code_parts else stock_code
        date_str = code_parts[1] if len(code_parts) > 1 else ''

        # one-liner
        olt = parse_one_liner(os.path.join(report_dir, 'one-liner.txt'))

        # HTML 数据
        with open(fpath, 'r', encoding='utf-8', errors='replace') as f:
            html = f.read()
        html_data = extract_html_sections(html)

        # 合并
        rid = f'report-{len(reports)}'
        name = html_data.get('name') or olt.get('name') or ticker
        score = olt.get('score') or html_data.get('html_score') or 0
        tone = olt.get('tone', '')
        safety = 'safe'
        safety_label = html_data.get('safety_label', '')
        if '警惕' in safety_label:
            safety = 'caution'
        elif '危险' in safety_label:
            safety = 'danger'

        reports.append({
            'id': rid,
            'ticker': ticker,
            'name': name,
            'date': date_str,
            'score': score,
            'tone': tone,
            'safety': safety,
            'safety_label': safety_label,
            'punchline': olt.get('punchline', ''),
            'bullish_voters': olt.get('bullish_voters', 0),
            'total_voters': olt.get('total_voters', 0),
            'price': html_data.get('price', '—'),
            'change_pct': html_data.get('change_pct', '—'),
            'change_dir': html_data.get('change_dir', ''),
            'mcap': html_data.get('mcap', ''),
            'pe': html_data.get('pe', ''),
            'pb': html_data.get('pb', ''),
            'sector': html_data.get('sector', ''),
            'verdict': html_data.get('score_verdict', ''),
            'safety_detail': html_data.get('safety_detail', ''),
            'conclusion': html_data.get('conclusion', ''),
            'cells_raw': html_data.get('cells_raw', []),
            'battle_plan': html_data.get('battle_plan', []),
            'bull_args': html_data.get('bull_args', []),
            'bear_args': html_data.get('bear_args', []),
        })

    reports.sort(key=lambda r: r['score'], reverse=True)
    return reports


# ═══════════════════════════════════════════════════════════════
# HTML 生成
# ═══════════════════════════════════════════════════════════════

def _esc(s):
    """安全转义 HTML 文本内容"""
    return (s or '').replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')


def build_interactive_html(reports, title, date_str):
    """构建单页 SPA HTML（无 iframe，全部内联）"""

    cards_json = json.dumps([{
        'id': r['id'], 'ticker': r['ticker'], 'name': r['name'],
        'score': r['score'], 'tone': r['tone'], 'safety': r['safety'],
        'punchline': r['punchline'], 'bullish_voters': r['bullish_voters'],
        'total_voters': r['total_voters'],
    } for r in reports], ensure_ascii=False)

    details_json = json.dumps({r['id']: {
        'ticker': r['ticker'], 'name': r['name'], 'sector': r['sector'],
        'price': r['price'], 'change_pct': r['change_pct'], 'change_dir': r['change_dir'],
        'mcap': r['mcap'], 'pe': r['pe'], 'pb': r['pb'],
        'score': r['score'], 'verdict': r['verdict'],
        'safety': r['safety'], 'safety_label': r['safety_label'], 'safety_detail': r['safety_detail'],
        'conclusion': r['conclusion'],
        'cells_raw': r['cells_raw'],
        'battle_plan': r['battle_plan'],
        'bull_args': r['bull_args'], 'bear_args': r['bear_args'],
        'bullish_voters': r['bullish_voters'], 'total_voters': r['total_voters'],
        'punchline': r['punchline'],
    } for r in reports}, ensure_ascii=False)

    return f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{_esc(title)}</title>
<style>
:root {{
  --bg: #0a0a1a; --card-bg: #12122a; --card-hover: #1a1a3a;
  --border: #2a2a4a; --accent: #00d4ff; --accent2: #7c4dff;
  --text: #e0e0e0; --text-dim: #888; --text-bright: #fff;
  --green: #00e676; --yellow: #ffab00; --red: #ff5252;
  --green-bg: rgba(0,230,118,0.12); --yellow-bg: rgba(255,171,0,0.12);
  --red-bg: rgba(255,82,82,0.12); --cyan-bg: rgba(0,212,255,0.08);
}}
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
  background: var(--bg); color: var(--text); line-height: 1.6;
}}

/* ── 导航栏 ── */
.nav {{
  position: sticky; top: 0; z-index: 100;
  background: linear-gradient(135deg, #0d0d2b 0%, #1a1040 100%);
  padding: 12px 24px; border-bottom: 1px solid var(--border);
  display: flex; align-items: center; gap: 12px;
}}
.nav h1 {{ font-size: 16px; color: var(--accent); white-space: nowrap; flex: 1; }}
.nav .back-btn {{
  display: none; padding: 6px 14px; background: var(--border); color: var(--text);
  border: none; border-radius: 6px; cursor: pointer; font-size: 13px; white-space: nowrap;
}}
.nav .back-btn:hover {{ background: var(--accent); color: #000; }}
.nav .nav-stats {{ font-size: 13px; color: var(--text-dim); white-space: nowrap; }}

/* ── 网格 ── */
#grid-view {{ max-width: 1400px; margin: 20px auto; padding: 0 20px; }}
.grid-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; flex-wrap: wrap; gap: 10px; }}
.grid-header h2 {{ color: var(--accent); font-size: 20px; }}
.filter-bar {{ display: flex; gap: 6px; flex-wrap: wrap; }}
.filter-btn {{
  padding: 5px 14px; border-radius: 16px; border: 1px solid var(--border);
  background: transparent; color: var(--text-dim); cursor: pointer; font-size: 12px;
  transition: all 0.2s;
}}
.filter-btn:hover, .filter-btn.active {{ background: var(--accent); color: #000; border-color: var(--accent); }}
.cards {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 14px; }}
.card {{
  background: var(--card-bg); border: 1px solid var(--border); border-radius: 12px;
  padding: 18px; cursor: pointer; transition: all 0.25s; position: relative; overflow: hidden;
}}
.card:hover {{
  background: var(--card-hover); border-color: var(--accent);
  transform: translateY(-2px); box-shadow: 0 8px 24px rgba(0,212,255,0.1);
}}
.card-name {{ font-size: 17px; font-weight: 700; color: var(--text-bright); }}
.card-code {{ font-size: 12px; color: var(--text-dim); margin-top: 2px; }}
.card-top {{ display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 10px; }}
.card-score {{ font-size: 28px; font-weight: 800; line-height: 1; }}
.card-score.high {{ color: var(--green); }}
.card-score.mid {{ color: var(--yellow); }}
.card-score.low {{ color: var(--red); }}
.card-tone {{
  display: inline-block; padding: 3px 10px; border-radius: 10px;
  font-size: 11px; font-weight: 600; margin-bottom: 8px;
}}
.card-tone.strong-bull {{ background: var(--green-bg); color: var(--green); }}
.card-tone.bull {{ background: var(--green-bg); color: var(--green); }}
.card-tone.neutral {{ background: var(--yellow-bg); color: var(--yellow); }}
.card-tone.caution {{ background: var(--yellow-bg); color: var(--yellow); }}
.card-tone.bear {{ background: var(--red-bg); color: var(--red); }}
.card-punchline {{
  font-size: 12px; color: var(--text-dim); line-height: 1.5;
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical;
  overflow: hidden; margin-bottom: 10px; min-height: 36px;
}}
.card-footer {{ display: flex; justify-content: space-between; align-items: center; padding-top: 8px; border-top: 1px solid var(--border); }}
.card-votes {{ font-size: 11px; color: var(--text-dim); }}
.card-safety {{ padding: 3px 8px; border-radius: 8px; font-size: 10px; font-weight: 600; }}
.card-safety.safe {{ background: var(--green-bg); color: var(--green); }}
.card-safety.caution {{ background: var(--yellow-bg); color: var(--yellow); }}
.card-safety.danger {{ background: var(--red-bg); color: var(--red); }}
.card-enter {{ font-size: 11px; color: var(--accent); }}

/* ── 详情视图 ── */
#detail-view {{
  display: none; max-width: 1100px; margin: 20px auto; padding: 0 20px 40px;
}}
.detail-hero {{
  display: grid; grid-template-columns: 2fr 1fr 1fr; gap: 14px; margin-bottom: 20px;
}}
.detail-name-card {{
  background: var(--card-bg); border: 1px solid var(--border); border-radius: 14px;
  padding: 20px 24px;
}}
.detail-name-card .stock-name {{ font-size: 24px; font-weight: 800; color: var(--text-bright); }}
.detail-name-card .stock-meta {{ font-size: 13px; color: var(--text-dim); margin: 4px 0 10px; }}
.detail-name-card .price-row {{ display: flex; align-items: baseline; gap: 10px; margin-bottom: 8px; }}
.detail-name-card .price {{ font-size: 28px; font-weight: 700; color: var(--text-bright); }}
.detail-name-card .change {{ font-size: 16px; font-weight: 600; }}
.detail-name-card .change.up {{ color: var(--green); }}
.detail-name-card .change.down {{ color: var(--red); }}
.detail-name-card .metric-chips {{ display: flex; gap: 8px; flex-wrap: wrap; }}
.detail-name-card .m-chip {{
  background: var(--cyan-bg); padding: 3px 10px; border-radius: 8px;
  font-size: 12px; color: var(--accent);
}}
.detail-score-card {{
  background: var(--card-bg); border: 1px solid var(--accent); border-radius: 14px;
  padding: 20px; text-align: center; display: flex; flex-direction: column;
  justify-content: center; box-shadow: 0 0 20px rgba(0,212,255,0.08);
}}
.detail-score-card .score-giant {{ font-size: 52px; font-weight: 900; color: var(--accent); line-height: 1; }}
.detail-score-card .score-label {{ font-size: 11px; color: var(--text-dim); letter-spacing: 2px; margin-bottom: 4px; }}
.detail-score-card .score-verdict {{ font-size: 12px; color: var(--text-dim); margin-top: 6px; }}
.detail-safety-card {{
  background: var(--card-bg); border: 1px solid var(--border); border-radius: 14px;
  padding: 20px; display: flex; flex-direction: column; justify-content: center;
  text-align: center;
}}
.detail-safety-card .safety-icon {{ font-size: 28px; margin-bottom: 6px; }}
.detail-safety-card .safety-label {{ font-size: 14px; font-weight: 700; }}
.detail-safety-card.safe .safety-label {{ color: var(--green); }}
.detail-safety-card.caution .safety-label {{ color: var(--yellow); }}
.detail-safety-card.danger .safety-label {{ color: var(--red); }}
.detail-safety-card .safety-detail {{ font-size: 11px; color: var(--text-dim); margin-top: 4px; }}

/* ── 详情区块 ── */
.detail-section {{
  background: var(--card-bg); border: 1px solid var(--border); border-radius: 12px;
  padding: 20px 24px; margin-bottom: 14px;
}}
.detail-section h3 {{
  font-size: 15px; color: var(--accent); margin-bottom: 12px;
  padding-bottom: 8px; border-bottom: 1px solid var(--border);
  display: flex; align-items: center; gap: 8px;
}}
.detail-section h3 .s-icon {{ font-size: 16px; }}
.conclusion-text {{ font-size: 15px; color: var(--text); line-height: 1.8; }}

/* metrics grid */
.metrics-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: 10px; }}
.metric-cell {{
  background: var(--cyan-bg); border-radius: 8px; padding: 12px 14px;
}}
.metric-cell .m-icon {{ font-size: 14px; }}
.metric-cell .m-key {{ font-size: 10px; color: var(--text-dim); text-transform: uppercase; margin: 4px 0; }}
.metric-cell .m-value {{ font-size: 13px; color: var(--text); line-height: 1.5; }}
.risk-value {{ font-size: 13px; color: var(--yellow); line-height: 1.7; }}

/* battle plan */
.plan-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; }}
.plan-cell {{
  background: var(--cyan-bg); border-radius: 8px; padding: 14px; text-align: center;
}}
.plan-cell .plan-k {{ font-size: 10px; color: var(--text-dim); text-transform: uppercase; margin-bottom: 4px; }}
.plan-cell .plan-v {{ font-size: 16px; font-weight: 700; color: var(--accent); }}

/* 论据区域 */
.arg-tabs {{ display: flex; gap: 0; margin-bottom: 0; }}
.arg-tab {{
  padding: 8px 20px; border: 1px solid var(--border); background: transparent;
  color: var(--text-dim); cursor: pointer; font-size: 13px; border-radius: 8px 8px 0 0;
  border-bottom: none; transition: all 0.2s;
}}
.arg-tab:first-child {{ border-radius: 8px 0 0 0; }}
.arg-tab:last-child {{ border-radius: 0 8px 0 0; }}
.arg-tab.active {{ background: var(--card-bg); color: var(--accent); border-color: var(--accent); }}
.arg-tab .count {{ font-size: 11px; color: var(--text-dim); margin-left: 4px; }}
.arg-tab.active .count {{ color: var(--accent); }}
.arg-list {{
  background: var(--card-bg); border: 1px solid var(--border); border-top: none;
  border-radius: 0 0 12px 12px; max-height: 500px; overflow-y: auto; display: none;
}}
.arg-list.active {{ display: block; }}
.arg-item {{
  padding: 12px 18px; border-bottom: 1px solid var(--border);
  display: flex; gap: 12px; align-items: flex-start;
}}
.arg-item:last-child {{ border-bottom: none; }}
.arg-item .arg-avatar {{
  width: 36px; height: 36px; border-radius: 50%; flex-shrink: 0;
  display: flex; align-items: center; justify-content: center;
  font-size: 14px; font-weight: 700; color: #fff;
}}
.arg-item.bullish .arg-avatar {{ background: var(--green); }}
.arg-item.bearish .arg-avatar {{ background: var(--red); }}
.arg-item .arg-body {{ flex: 1; min-width: 0; }}
.arg-item .arg-name {{ font-size: 13px; font-weight: 600; color: var(--text-bright); }}
.arg-item .arg-group {{ font-size: 10px; color: var(--text-dim); margin-left: 6px; }}
.arg-item .arg-score {{ font-size: 12px; font-weight: 700; margin-left: auto; }}
.arg-item.bullish .arg-score {{ color: var(--green); }}
.arg-item.bearish .arg-score {{ color: var(--red); }}
.arg-item .arg-reasoning {{ font-size: 12px; color: var(--text-dim); margin-top: 4px; line-height: 1.5; }}
.arg-item .arg-verdict {{ font-size: 11px; margin-top: 4px; }}
.arg-item.bullish .arg-verdict {{ color: var(--green); }}
.arg-item.bearish .arg-verdict {{ color: var(--red); }}

/* ── 响应式 ── */
@media (max-width: 768px) {{
  .cards {{ grid-template-columns: 1fr; }}
  .detail-hero {{ grid-template-columns: 1fr; }}
  .plan-grid {{ grid-template-columns: repeat(2, 1fr); }}
  .metrics-grid {{ grid-template-columns: 1fr 1fr; }}
}}
</style>
</head>
<body>

<div class="nav">
  <button class="back-btn" id="backBtn" onclick="showGrid()">← 返回总览</button>
  <h1 id="navTitle">{_esc(title)}</h1>
  <span class="nav-stats" id="navStats"></span>
</div>

<div id="grid-view">
  <div class="grid-header">
    <h2>深度分析总览</h2>
    <div class="filter-bar">
      <button class="filter-btn active" onclick="filterCards('all', this)">全部</button>
      <button class="filter-btn" onclick="filterCards('high', this)">高分 (≥70)</button>
      <button class="filter-btn" onclick="filterCards('safe', this)">安全</button>
      <button class="filter-btn" onclick="filterCards('bullish', this)">看多</button>
    </div>
  </div>
  <div class="cards" id="cardsContainer"></div>
</div>

<div id="detail-view"></div>

<script>
var CARDS = {cards_json};
var DETAILS = {details_json};
var dateStr = '{date_str}';

// ── 工具 ──
function esc(s) {{ return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }}
function getToneInfo(t) {{
  if (!t) return {{ c:'', l:'' }};
  if (t.indexOf('强烈看多')>=0) return {{ c:'strong-bull', l:t }};
  if (t.indexOf('看多')>=0) return {{ c:'bull', l:t }};
  if (t.indexOf('可以蹲')>=0 || t.indexOf('中性')>=0) return {{ c:'neutral', l:t }};
  if (t.indexOf('谨慎')>=0) return {{ c:'caution', l:t }};
  if (t.indexOf('回避')>=0) return {{ c:'bear', l:t }};
  return {{ c:'neutral', l:t||'中性' }};
}}

// ── 卡片渲染 ──
function renderCards(filter) {{
  var ctr = document.getElementById('cardsContainer');
  ctr.innerHTML = '';
  var list = CARDS;
  if (filter === 'high') list = CARDS.filter(function(c){{ return c.score >= 70; }});
  else if (filter === 'safe') list = CARDS.filter(function(c){{ return c.safety === 'safe'; }});
  else if (filter === 'bullish') list = CARDS.filter(function(c){{ return c.tone && (c.tone.indexOf('看多')>=0); }});

  list.forEach(function(card){{
    var sc = card.score >= 70 ? 'high' : card.score >= 50 ? 'mid' : 'low';
    var ti = getToneInfo(card.tone);
    var sfc = card.safety === 'safe' ? 'safe' : card.safety === 'caution' ? 'caution' : 'danger';
    var sfl = card.safety === 'safe' ? '安全' : card.safety === 'caution' ? '警惕' : '危险';
    var vt = card.total_voters > 0 ? card.bullish_voters + '/' + card.total_voters + ' 看多' : '';

    var div = document.createElement('div');
    div.className = 'card';
    div.onclick = (function(id){{ return function(){{ showDetail(id); }}; }})(card.id);
    div.innerHTML =
      '<div class="card-top"><div>' +
      '<div class="card-name">' + esc(card.name) + '</div>' +
      '<div class="card-code">' + esc(card.ticker) + '</div></div>' +
      '<div class="card-score ' + sc + '">' + card.score.toFixed(1) + '</div></div>' +
      (ti.l ? '<div class="card-tone ' + ti.c + '">' + esc(ti.l) + '</div>' : '') +
      '<div class="card-punchline">' + esc(card.punchline || '—') + '</div>' +
      '<div class="card-footer">' +
      '<span class="card-votes">' + esc(vt) + '</span>' +
      '<span class="card-safety ' + sfc + '">' + sfl + '</span>' +
      '<span class="card-enter">查看详情 →</span></div>';
    ctr.appendChild(div);
  }});
  document.getElementById('navStats').textContent = '共 ' + CARDS.length + ' 只 · ' + dateStr;
}}

// ── 筛选 ──
function filterCards(filter, btn) {{
  var bs = document.querySelectorAll('.filter-btn');
  for (var i = 0; i < bs.length; i++) bs[i].classList.remove('active');
  if (btn) btn.classList.add('active');
  renderCards(filter);
}}

// ── 详情渲染 ──
function showDetail(id) {{
  var d = DETAILS[id];
  if (!d) return;

  // 论据列表 HTML
  function argList(items, stance) {{
    if (!items || !items.length) return '<div class="arg-item"><span style="color:var(--text-dim)">暂无数据</span></div>';
    return items.map(function(a){{
      return '<div class="arg-item ' + stance + '">' +
        '<div class="arg-avatar">' + esc(a.name.charAt(0)) + '</div>' +
        '<div class="arg-body">' +
        '<span class="arg-name">' + esc(a.name) + '</span>' +
        '<span class="arg-group">' + esc(a.group) + '</span>' +
        '<span class="arg-score">' + a.score + '分</span>' +
        (a.reasoning ? '<div class="arg-reasoning">' + esc(a.reasoning) + '</div>' : '') +
        (a.comment ? '<div class="arg-reasoning">💬 ' + esc(a.comment) + '</div>' : '') +
        '<div class="arg-verdict">▸ ' + esc(a.verdict) + '</div>' +
        '</div></div>';
    }}).join('');
  }}

  // cells 渲染
  var cellsHtml = '';
  if (d.cells_raw && d.cells_raw.length) {{
    cellsHtml = '<div class="metrics-grid">';
    d.cells_raw.forEach(function(c){{
      cellsHtml += '<div class="metric-cell"><div class="m-icon">' + esc(c[0]) +
        '</div><div class="m-key">' + esc(c[1]) + '</div><div class="m-value">' + esc(c[2]) + '</div></div>';
    }});
    cellsHtml += '</div>';
  }}

  // battle plan
  var planHtml = '';
  if (d.battle_plan && d.battle_plan.length) {{
    planHtml = '<div class="plan-grid">';
    d.battle_plan.forEach(function(p){{
      planHtml += '<div class="plan-cell"><div class="plan-k">' + esc(p[0]) +
        '</div><div class="plan-v">' + esc(p[1]) + '</div></div>';
    }});
    planHtml += '</div>';
  }}

  // safety
  var sfc = d.safety === 'safe' ? 'safe' : d.safety === 'caution' ? 'caution' : 'danger';
  var sfIcon = d.safety === 'safe' ? '🟢' : d.safety === 'caution' ? '🟡' : '🔴';

  // 构建详情 HTML
  var html =
    '<div class="detail-hero">' +
      '<div class="detail-name-card">' +
        '<div class="stock-name">' + esc(d.name) + '</div>' +
        '<div class="stock-meta">' + esc(d.ticker) + (d.sector ? ' · ' + esc(d.sector) : '') + '</div>' +
        '<div class="price-row">' +
          '<span class="price">' + esc(d.price) + '</span>' +
          '<span class="change ' + (d.change_dir||'') + '">' + esc(d.change_pct) + '</span>' +
        '</div>' +
        '<div class="metric-chips">' +
          (d.mcap ? '<span class="m-chip">MCAP ' + esc(d.mcap) + '</span>' : '') +
          (d.pe ? '<span class="m-chip">PE ' + esc(d.pe) + '</span>' : '') +
          (d.pb ? '<span class="m-chip">PB ' + esc(d.pb) + '</span>' : '') +
        '</div>' +
      '</div>' +
      '<div class="detail-score-card">' +
        '<div class="score-label">ALPHA SCORE</div>' +
        '<div class="score-giant">' + Math.round(d.score) + '</div>' +
        '<div class="score-verdict">' + esc(d.verdict || '') + '</div>' +
      '</div>' +
      '<div class="detail-safety-card ' + sfc + '">' +
        '<div class="safety-icon">' + sfIcon + '</div>' +
        '<div class="safety-label">' + esc(d.safety_label || '—') + '</div>' +
        '<div class="safety-detail">' + esc(d.safety_detail || '') + '</div>' +
      '</div>' +
    '</div>';

  // 核心结论
  if (d.conclusion) {{
    html += '<div class="detail-section">' +
      '<h3><span class="s-icon">◆</span> 核心结论</h3>' +
      '<div class="conclusion-text">' + esc(d.conclusion) + '</div></div>';
  }}

  // 战况面板
  if (cellsHtml) {{
    html += '<div class="detail-section">' +
      '<h3><span class="s-icon">📊</span> 战况面板</h3>' + cellsHtml + '</div>';
  }}

  // 作战计划
  if (planHtml) {{
    html += '<div class="detail-section">' +
      '<h3><span class="s-icon">🎯</span> 作战计划</h3>' + planHtml + '</div>';
  }}

  // 评委交锋
  var hasBull = d.bull_args && d.bull_args.length;
  var hasBear = d.bear_args && d.bear_args.length;
  if (hasBull || hasBear) {{
    html += '<div class="detail-section">' +
      '<h3><span class="s-icon">⚔</span> 评委交锋 ' +
      '<span style="font-size:12px;color:var(--text-dim);font-weight:400">' +
      (d.bullish_voters||0) + '/' + (d.total_voters||0) + ' 看多</span></h3>' +
      '<div class="arg-tabs">' +
      '<div class="arg-tab active" onclick="switchArgTab(this,\\'bull-' + id + '\\')">看多理由<span class="count">' + (d.bull_args||[]).length + '</span></div>' +
      '<div class="arg-tab" onclick="switchArgTab(this,\\'bear-' + id + '\\')">看空理由<span class="count">' + (d.bear_args||[]).length + '</span></div>' +
      '</div>' +
      '<div class="arg-list active" id="arg-bull-' + id + '">' + argList(d.bull_args, 'bullish') + '</div>' +
      '<div class="arg-list" id="arg-bear-' + id + '">' + argList(d.bear_args, 'bearish') + '</div>' +
      '</div>';
  }}

  document.getElementById('detail-view').innerHTML = html;
  document.getElementById('grid-view').style.display = 'none';
  document.getElementById('detail-view').style.display = 'block';
  document.getElementById('backBtn').style.display = 'inline-block';
  document.getElementById('navTitle').textContent = d.name + '  ' + d.ticker;
  window.scrollTo(0, 0);
}}

// ── tab 切换 ──
function switchArgTab(tab, listId) {{
  var parent = tab.parentElement;
  var tabs = parent.querySelectorAll('.arg-tab');
  for (var i = 0; i < tabs.length; i++) tabs[i].classList.remove('active');
  tab.classList.add('active');
  var lists = parent.parentElement.querySelectorAll('.arg-list');
  for (var j = 0; j < lists.length; j++) lists[j].classList.remove('active');
  document.getElementById('arg-' + listId).classList.add('active');
}}

// ── 返回总览 ──
function showGrid() {{
  document.getElementById('grid-view').style.display = 'block';
  document.getElementById('detail-view').style.display = 'none';
  document.getElementById('detail-view').innerHTML = '';
  document.getElementById('backBtn').style.display = 'none';
  document.getElementById('navTitle').textContent = '{_esc(title)}';
  window.scrollTo(0, 0);
}}

renderCards('all');
</script>
</body>
</html>'''


def consolidate(input_dir, output_path, title=None):
    date_str = datetime.now().strftime('%Y-%m-%d')
    if title is None:
        title = f"A股深度分析 | {date_str}"

    reports = scan_reports(input_dir)
    if not reports:
        print(f"[警告] 未找到任何 HTML 报告: {input_dir}")
        return

    print(f"[INFO] 找到 {len(reports)} 份报告:")
    for r in reports:
        bull = len(r.get('bull_args', []))
        bear = len(r.get('bear_args', []))
        print(f"  - {r['ticker']} {r['name']} | {r['score']}分 {r['tone']} | 论据:看多{bull}/看空{bear}")

    html = build_interactive_html(reports, title, date_str)

    os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)

    size_kb = os.path.getsize(output_path) / 1024
    print(f"\n[OK] 单页 SPA: {output_path} ({size_kb:.0f} KB, {len(reports)} stocks)")
    return output_path


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='生成交互式股票分析仪表盘（单页SPA）')
    parser.add_argument('--input-dir', required=True, help='HTML报告目录')
    parser.add_argument('--output', required=True, help='输出HTML路径')
    parser.add_argument('--title', default=None, help='报告标题')
    args = parser.parse_args()
    consolidate(args.input_dir, args.output, args.title)
