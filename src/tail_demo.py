"""
尾盘选股器 - 演示模式（使用模拟数据）
用于测试选股器功能，无需联网
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
from datetime import datetime

from src.tail_picker import TailStockPicker
from src.export import DataExporter


def generate_mock_data(num_stocks: int = 500) -> pd.DataFrame:
    """
    生成模拟股票数据

    Args:
        num_stocks: 股票数量

    Returns:
        DataFrame: 模拟数据
    """
    np.random.seed(42)

    # 生成股票代码和名称
    symbols = []
    names = []

    # 沪市主板
    for i in range(200):
        symbols.append(f"60{np.random.randint(1000, 4000):04d}")
        names.append(f"股票 {i}")

    # 深市主板
    for i in range(200):
        symbols.append(f"00{np.random.randint(1000, 3000):04d}")
        names.append(f"股票 {200+i}")

    # 创业板
    for i in range(100):
        symbols.append(f"30{np.random.randint(1000, 2000):04d}")
        names.append(f"股票 {400+i}")

    # 科创板
    for i in range(100):
        symbols.append(f"68{np.random.randint(8000, 9000):04d}")
        names.append(f"股票 {500+i}")

    df = pd.DataFrame({
        '代码': symbols[:num_stocks],
        '名称': names[:num_stocks],
        '最新价': np.random.uniform(5, 500, num_stocks),
        '涨跌幅': np.random.uniform(-5, 10, num_stocks),  # 更多股票涨停
        '量比': np.random.uniform(0.5, 5, num_stocks),
        '换手率': np.random.uniform(1, 30, num_stocks),
        '成交量': np.random.randint(1000, 1000000, num_stocks) * 100,
        '成交额': np.random.uniform(1000000, 1000000000, num_stocks),
    })

    # 人为制造一些符合条件的股票
    # 让前 20 只股票满足条件
    for i in range(min(20, num_stocks)):
        df.loc[i, '涨跌幅'] = np.random.uniform(3.5, 6.5)
        df.loc[i, '量比'] = np.random.uniform(1.8, 3.5)
        df.loc[i, '换手率'] = np.random.uniform(6, 15)
        df.loc[i, '主力净流入 (万)'] = np.random.uniform(800, 3000)

    # 添加主力净流入 - 让部分股票满足条件
    df['主力净流入 (万)'] = np.random.uniform(-500, 2000, num_stocks)
    # 确保前 30 只有正流入
    for i in range(min(30, num_stocks)):
        df.loc[i, '主力净流入 (万)'] = np.random.uniform(600, 3000)

    return df


def run_demo():
    """运行演示模式"""
    print("\n" + "=" * 70)
    print("                    尾盘选股器 - 演示模式")
    print("         " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("=" * 70)
    print("\n[演示模式] 使用模拟数据测试选股功能")

    # 创建选股器
    picker = TailStockPicker({
        'top_n': 20,
        'min_gain': 3.0,
        'max_gain': 7.0,
        'min_volume_ratio': 1.5,
        'min_turnover': 5.0,
        'max_turnover': 20.0,
        'min_main_inflow': 500,
    })

    # 生成模拟数据
    print("\n生成模拟股票数据...")
    mock_data = generate_mock_data(500)
    picker.all_stocks_df = mock_data
    picker.fund_flow_df = None  # 演示模式无资金流数据

    print(f"模拟数据：{len(mock_data)} 只股票")

    # 执行筛选
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 开始筛选...")

    result = picker.filter_basic(mock_data)
    print(f"  基础筛选后：{len(result)} 只")

    result = picker.filter_gain(result)
    print(f"  涨幅筛选后：{len(result)} 只")

    result = picker.filter_turnover(result)
    print(f"  换手率筛选后：{len(result)} 只")

    result = picker.filter_volume_ratio(result)
    print(f"  量比筛选后：{len(result)} 只")

    result = picker.merge_fund_flow(result)
    result = picker.filter_main_inflow(result)
    print(f"  资金流筛选后：{len(result)} 只")

    result = picker.calculate_score(result)

    if not result.empty:
        result = result.sort_values('score', ascending=False)
        result = result.head(picker.config['top_n'])

    # 显示结果
    if not result.empty:
        picker._print_result(result)

        # 导出结果
        exporter = DataExporter()
        csv_path = exporter.export_csv(result)
        print(f"\n结果已保存：{csv_path}")

        # 显示推送消息
        print("\n" + exporter.export_for_push(result, top_n=10))
    else:
        print("\n未找到符合条件的股票")

    return result


if __name__ == "__main__":
    run_demo()
