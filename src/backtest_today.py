# coding: utf-8
"""
尾盘选股回测脚本
用于查看昨日选股在今日的表现
"""
import pandas as pd
import requests
import os

def backtest_yesterday_pick():
    # 查找昨天的选股文件
    pick_dir = 'stock_data/tail_pick'
    files = sorted([f for f in os.listdir(pick_dir) if 'pick_20260226' in f])
    
    if not files:
        print('未找到昨日选股数据')
        return
    
    # 读取昨日数据
    yesterday_file = f'{pick_dir}/{files[-1]}'
    yesterday_df = pd.read_csv(yesterday_file)
    
    print('=' * 60)
    print('昨日尾盘选股今日表现回测')
    print('=' * 60)
    print(f'选股日期：2026-02-26')
    print(f'选股数量：{len(yesterday_df)}只')
    print()
    
    # 获取今日表现
    codes = yesterday_df['代码'].astype(int).astype(str).str.zfill(6).tolist()
    symbols = ','.join(['sh'+c if c.startswith('6') else 'sz'+c for c in codes])
    url = f'http://qt.gtimg.cn/q={symbols}'
    
    try:
        resp = requests.get(url, timeout=10)
        resp.encoding = 'gbk'
        lines = resp.text.strip().split(';')
        
        results = []
        for i, line in enumerate(lines):
            if not line: continue
            parts = line.split('"')
            if len(parts) < 2: continue
            data = parts[1].split(',')
            if len(data) >= 32:
                code = codes[i]
                name = data[0]
                cur = float(data[3])
                pre = float(data[2])
                change = (cur - pre) / pre * 100 if pre else 0
                results.append({'代码': code, '今日涨跌': change})
        
        if results:
            today_df = pd.DataFrame(results)
            
            print('今日表现:')
            for _, r in today_df.iterrows():
                orig = yesterday_df[yesterday_df['代码'].astype(str).str.zfill(6)==r['代码']]
                if not orig.empty:
                    o = orig.iloc[0]
                    status = '涨停' if r['今日涨跌']>=9.8 else ('涨' if r['今日涨跌']>0 else '跌')
                    print(f"{r['代码']} {r['名称']}  昨:{o['涨跌幅']:.2f}% 量比:{o['volume_ratio']:.2f} → 今日:{r['今日涨跌']:+.2f}% [{status}]")
            
            # 统计
            up = len(today_df[today_df['今日涨跌']>0])
            zt = len(today_df[today_df['今日涨跌']>=9.8])
            avg = today_df['今日涨跌'].mean()
            
            print()
            print('=' * 60)
            print('统计结果:')
            print(f'  上涨：{up}只 / 下跌：{len(today_df)-up}只')
            print(f'  胜率：{up/len(today_df)*100:.1f}%')
            print(f'  涨停：{zt}只')
            print(f'  平均涨跌：{avg:+.2f}%')
            print('=' * 60)
            
            # 保存结果
            merged = yesterday_df.copy()
            merged['代码'] = merged['代码'].astype(int).astype(str).str.zfill(6)
            merged = merged.merge(today_df, on='代码')
            merged.to_csv(f'stock_data/tail_pick/performance_20260227.csv', index=False, encoding='utf-8-sig')
            print(f'结果已保存：stock_data/tail_pick/performance_20260227.csv')
            
    except Exception as e:
        print(f'获取数据失败：{e}')

if __name__ == '__main__':
    backtest_yesterday_pick()
