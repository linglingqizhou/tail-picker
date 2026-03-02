"""
测试所有数据接口
"""

import sys
sys.path.insert(0, '.')

from src.akshare_api import *
from src.sina_api import SinaStockAPI
from src.data_collector import DataCollector

def test_all():
    print("=" * 60)
    print("A 股行情数据采集系统 - 测试程序")
    print("=" * 60)

    # 测试 1: AkShare 实时行情
    print("\n【测试 1】AkShare 获取全部 A 股实时行情...")
    df = get_all_stocks_realtime()
    if df is not None and not df.empty:
        print(f"[OK] 获取成功，共 {len(df)} 只股票")
        print("前 10 只股票:")
        cols = [c for c in ['代码', '名称', '最新价', '涨跌幅'] if c in df.columns]
        print(df[cols].head(10).to_string())
    else:
        print("[FAIL] 获取失败")

    # 测试 2: 新浪单只股票行情
    print("\n【测试 2】新浪财经获取贵州茅台 (600519) 实时行情...")
    api = SinaStockAPI()
    data = api.get_realtime('600519')
    if data:
        print(f"[OK] 获取成功")
        print(f"  股票：{data['name']}")
        print(f"  当前价：{data['current']}")
        print(f"  涨跌幅：{data['change_percent']:.2f}%")
        print(f"  时间：{data['date']} {data['time']}")
    else:
        print("[FAIL] 获取失败")

    # 测试 3: 新浪批量行情
    print("\n【测试 3】新浪财经批量获取 5 只股票行情...")
    test_symbols = ['600519', '000001', '000858', '300750', '601318']
    df = api.get_batch_realtime(test_symbols)
    if not df.empty:
        print(f"[OK] 获取成功，共 {len(df)} 只股票")
        print(df[['symbol', 'name', 'current', 'change_percent']].to_string())
    else:
        print("[FAIL] 获取失败")

    # 测试 4: 历史 K 线
    print("\n【测试 4】AkShare 获取贵州茅台历史 K 线...")
    df = get_stock_history('600519', start_date='20250101')
    if df is not None and not df.empty:
        print(f"[OK] 获取成功，共 {len(df)} 条记录")
        print(df.tail(5).to_string())
    else:
        print("[FAIL] 获取失败")

    # 测试 5: 资金流向
    print("\n【测试 5】AkShare 获取资金流向排名...")
    df = get_individual_fund_flow()
    if df is not None and not df.empty:
        print(f"[OK] 获取成功，共 {len(df)} 条记录")
        print("Top 10:")
        print(df.head(10).to_string())
    else:
        print("[FAIL] 获取失败")

    # 测试 6: 龙虎榜
    print("\n【测试 6】AkShare 获取龙虎榜数据...")
    df = get_lhb_today()
    if df is not None and not df.empty:
        print(f"[OK] 获取成功，共 {len(df)} 条记录")
        print(df.head(5).to_string())
    else:
        print("[FAIL] 获取失败或暂无数据")

    print("\n" + "=" * 60)
    print("测试完成!")
    print("=" * 60)


if __name__ == '__main__':
    test_all()
