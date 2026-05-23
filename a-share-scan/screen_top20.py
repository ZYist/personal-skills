"""
A股盘面扫描：多源行情拉取 + 打分筛选 Top20
数据源优先级：腾讯 > 新浪 > 东财push2（自动降级）
用法: python screen_top20.py [--sector 关键词] [--top N] [--output result.json]
"""
import requests
import pandas as pd
import numpy as np
import json
import sys
import time
import argparse
import re
from datetime import datetime

# ── Stock list ──────────────────────────────────────────
def fetch_stock_list_sina():
    """从新浪获取A股列表（分页，可获取全部5200+只）"""
    all_stocks = []
    headers = {'User-Agent': 'Mozilla/5.0', 'Referer': 'https://finance.sina.com.cn'}
    for page in range(1, 80):
        try:
            url = 'https://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/Market_Center.getHQNodeData'
            params = {'page': str(page), 'num': '100', 'sort': 'symbol', 'asc': '1',
                      'node': 'hs_a', 'symbol': '', '_s_r_a': 'init'}
            r = requests.get(url, params=params, headers=headers, timeout=15)
            r.encoding = 'gb2312'
            data = json.loads(r.text)
            if not data:
                break
            for s in data:
                code = s.get('symbol', '')
                if not code.startswith('bj'):  # 排除北交所
                    all_stocks.append({'code': code, 'name': s.get('name', '')})
            if len(data) < 100:
                break
            time.sleep(0.2)
        except Exception:
            break
    return all_stocks

# ── Quote fetchers (tried in priority order) ────────────
def fetch_tencent(codes, batch_size=800):
    """腾讯行情API — 数据字段最全，含PE/PB/换手率/市值"""
    headers = {'User-Agent': 'Mozilla/5.0'}
    records = []
    for i in range(0, len(codes), batch_size):
        batch = codes[i:i+batch_size]
        try:
            r = requests.get(f"http://qt.gtimg.cn/q={','.join(batch)}",
                            headers=headers, timeout=30)
            r.encoding = 'gbk'
            for line in r.text.strip().split('\n'):
                m = re.match(r'v_(\w+)="(.*)"', line.strip())
                if not m:
                    continue
                code, raw = m.group(1), m.group(2)
                f = raw.split('~')
                if len(f) < 40:
                    continue
                try:
                    price = float(f[3]) if f[3] else 0
                    prev = float(f[4]) if f[4] else 0
                    records.append({
                        'code': code, 'name': f[1],
                        'latest': price,
                        'pct_chg': round((price-prev)/prev*100, 2) if prev > 0 else 0,
                        'change': round(price-prev, 2),
                        'volume': float(f[6] or 0) * 100,
                        'amount': float(f[37] or 0) * 10000,  # 万元→元
                        'turnover': float(f[38] or 0),
                        'pe': float(f[39] or 0),
                        'vol_ratio': float(f[47] or 0) if len(f) > 47 else 0,
                        'high': float(f[33] or 0),
                        'low': float(f[34] or 0),
                        'open': float(f[5] or 0),
                        'amplitude': float(f[43] or 0),
                        'market_cap': float(f[45] or 0),  # 流通市值(亿)
                        'pb': float(f[46] or 0) if len(f) > 46 else 0,
                    })
                except (ValueError, IndexError):
                    continue
            time.sleep(0.3)
        except Exception as e:
            print(f"  腾讯API批次{i//batch_size+1}失败: {e}", file=sys.stderr)
            continue
    return records

def fetch_sina(codes, batch_size=800):
    """新浪行情API — 备选方案"""
    headers = {'User-Agent': 'Mozilla/5.0', 'Referer': 'https://finance.sina.com.cn'}
    records = []
    for i in range(0, len(codes), batch_size):
        batch = codes[i:i+batch_size]
        try:
            r = requests.get(f"https://hq.sinajs.cn/list={','.join(batch)}",
                            headers=headers, timeout=30)
            r.encoding = 'gb2312'
            for line in r.text.strip().split('\n'):
                m = re.match(r'var hq_str_(\w+)="(.*)"', line.strip())
                if not m:
                    continue
                code, raw = m.group(1), m.group(2)
                f = raw.split(',')
                if len(f) < 10:
                    continue
                try:
                    price = float(f[3]) if f[3] else 0
                    prev = float(f[2]) if f[2] else 0
                    records.append({
                        'code': code, 'name': f[0],
                        'latest': price,
                        'pct_chg': round((price-prev)/prev*100, 2) if prev > 0 else 0,
                        'change': round(price-prev, 2),
                        'volume': float(f[8] or 0),
                        'amount': float(f[9] or 0),
                        'turnover': 0, 'pe': 0, 'vol_ratio': 0,
                        'high': float(f[4] or 0),
                        'low': float(f[5] or 0),
                        'open': float(f[1] or 0),
                        'amplitude': 0, 'market_cap': 0, 'pb': 0,
                    })
                except (ValueError, IndexError):
                    continue
            time.sleep(0.3)
        except Exception as e:
            print(f"  新浪API批次{i//batch_size+1}失败: {e}", file=sys.stderr)
            continue
    return records

# ── Main pipeline ───────────────────────────────────────
def fetch_all_quotes():
    """多源自动降级拉取全市场行情"""
    print("[1] 获取A股股票列表...", file=sys.stderr)
    stocks = fetch_stock_list_sina()
    codes = [s['code'] for s in stocks]
    print(f"  获取到 {len(codes)} 只", file=sys.stderr)

    # Try sources in priority order
    sources = [
        ("腾讯 qt.gtimg.cn", fetch_tencent),
        ("新浪 hq.sinajs.cn", fetch_sina),
    ]
    for name, fetcher in sources:
        print(f"[2] 尝试 {name} 行情...", file=sys.stderr)
        records = fetcher(codes)
        if len(records) > 1000:
            print(f"  成功: {len(records)} 条", file=sys.stderr)
            return pd.DataFrame(records)
        print(f"  数据不足({len(records)}条)，切换下一源...", file=sys.stderr)

    raise RuntimeError("所有数据源均失败")

def filter_and_score(df, sector=None, top_n=30):
    """筛选 + 打分"""
    # Filter
    df = df[~df['name'].str.contains('ST|退', na=False)].copy()
    df = df[df['amount'] >= 1e8].copy()
    df = df[df['latest'].notna() & (df['latest'] > 0)].copy()
    if sector:
        df = df[df['name'].str.contains(sector, na=False)]
    print(f"[3] 筛选后: {len(df)} 只", file=sys.stderr)

    # Score
    def norm(s):
        return (s - s.min()) / (s.max() - s.min() + 1e-10)

    df['score_amt'] = norm(np.log1p(df['amount'])) * 0.30
    df['score_pct'] = norm(df['pct_chg'].abs()) * 0.25
    df.loc[df['pct_chg'] > 0, 'score_pct'] *= 1.3
    df['score_pct'] = df['score_pct'].clip(upper=0.25)
    df['score_vol'] = norm(df['vol_ratio'].fillna(1).clip(0, 15)) * 0.25
    df['score_to'] = norm(df['turnover'].fillna(0)) * 0.20

    df['score'] = df['score_amt'] + df['score_pct'] + df['score_vol'] + df['score_to']
    df['score'] = (df['score'] * 10).round(1)

    top = df.nlargest(top_n, 'score').reset_index(drop=True)
    top['rank'] = range(1, len(top)+1)
    return top

def main():
    parser = argparse.ArgumentParser(description='A股Top30扫描')
    parser.add_argument('--sector', type=str, default=None)
    parser.add_argument('--top', type=int, default=30)
    parser.add_argument('--output', type=str, default=None)
    args = parser.parse_args()

    t0 = time.time()
    df = fetch_all_quotes()
    top = filter_and_score(df, args.sector, args.top)

    # Output
    result = []
    for _, row in top.iterrows():
        result.append({
            'rank': int(row['rank']),
            'code': str(row['code']),
            'name': str(row['name']),
            'price': round(float(row['latest']), 2),
            'change_pct': round(float(row['pct_chg']), 2),
            'amount': round(float(row['amount']), 2),
            'turnover': round(float(row['turnover']), 2),
            'volume_ratio': round(float(row['vol_ratio']), 2),
            'pe': round(float(row.get('pe', 0)), 2),
            'pb': round(float(row.get('pb', 0)), 2),
            'score': float(row['score']),
        })

    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

    print(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"\n[完成] {len(top)}只, 耗时 {time.time()-t0:.0f}秒", file=sys.stderr)

if __name__ == '__main__':
    main()
