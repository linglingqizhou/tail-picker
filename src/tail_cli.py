"""
尾盘选股器 - 命令行交互界面
支持自定义筛选条件、保存配置、交互式选股
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import argparse
from datetime import datetime
from pathlib import Path

from src.tail_picker import TailStockPicker
from src.backtest import BacktestEngine


# 配置文件路径
CONFIG_FILE = Path(__file__).parent.parent / "picker_config.json"


def load_config() -> dict:
    """加载配置文件"""
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def save_config(config: dict):
    """保存配置文件"""
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


def interactive_config():
    """交互式配置"""
    print("\n" + "=" * 60)
    print("         尾盘选股器 - 配置向导")
    print("=" * 60)

    config = load_config()

    print("\n当前配置:")
    for k, v in config.items():
        print(f"  {k}: {v}")

    print("\n修改配置 (直接回车跳过):")

    # 涨幅范围
    val = input(f"  最小涨幅% [{config.get('min_gain', 3.0)}]: ").strip()
    if val:
        config['min_gain'] = float(val)

    val = input(f"  最大涨幅% [{config.get('max_gain', 7.0)}]: ").strip()
    if val:
        config['max_gain'] = float(val)

    # 量比
    val = input(f"  最小额比 [{config.get('min_volume_ratio', 1.5)}]: ").strip()
    if val:
        config['min_volume_ratio'] = float(val)

    # 换手率
    val = input(f"  最小换手率% [{config.get('min_turnover', 5.0)}]: ").strip()
    if val:
        config['min_turnover'] = float(val)

    val = input(f"  最大换手率% [{config.get('max_turnover', 20.0)}]: ").strip()
    if val:
        config['max_turnover'] = float(val)

    # 主力流入
    val = input(f"  最小主力流入 (万) [{config.get('min_main_inflow', 500)}]: ").strip()
    if val:
        config['min_main_inflow'] = float(val)

    # 选股数量
    val = input(f"  选中股票数量 [{config.get('top_n', 20)}]: ").strip()
    if val:
        config['top_n'] = int(val)

    save_config(config)
    print("\n配置已保存!")

    return config


def quick_select():
    """快速选股（使用默认配置）"""
    config = load_config()

    picker = TailStockPicker(config)
    result = picker.select(show_all=True)

    if not result.empty:
        # 保存结果
        output_dir = Path(__file__).parent.parent / "stock_data" / "tail_pick"
        output_dir.mkdir(parents=True, exist_ok=True)

        filename = output_dir / f"pick_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        result.to_csv(filename, index=False, encoding='utf-8-sig')
        print(f"\n结果已保存到：{filename}")

    return result


def show_stock_detail():
    """查看个股详情"""
    symbol = input("\n请输入股票代码：").strip()
    if not symbol:
        return

    picker = TailStockPicker()
    picker.fetch_all_data()

    detail = picker.get_stock_detail(symbol)

    print(f"\n【{detail['name']}({symbol})】详细信息")
    print("-" * 40)
    print(f"  当前价：    {detail['current_price']}")
    print(f"  涨幅：      {detail['gain']:.2f}%")
    print(f"  5 日均线：   {detail['ma5']:.2f}")
    print(f"  10 日均线：  {detail['ma10']:.2f}")
    print(f"  20 日均线：  {detail['ma20']:.2f}")
    print(f"  技术形态：  {detail['recommendation']}")
    print("-" * 40)


def run_backtest():
    """运行回测"""
    print("\n" + "=" * 60)
    print("         历史回测")
    print("=" * 60)

    # 获取回测参数
    start_date = input("  开始日期 (YYYYMMDD) [20250101]: ").strip() or "20250101"
    end_date = input("  结束日期 (YYYYMMDD) [20260224]: ").strip() or "20260224"
    days = input("  持股天数 [1]: ").strip() or "1"

    config = load_config()
    engine = BacktestEngine(config)

    print(f"\n开始回测 {start_date} ~ {end_date}...")
    report = engine.run(start_date, end_date, int(days))

    # 打印回测报告
    print("\n" + "=" * 60)
    print("                    回测报告")
    print("=" * 60)
    for k, v in report.items():
        if isinstance(v, float):
            print(f"  {k}: {v:.2f}%")
        else:
            print(f"  {k}: {v}")
    print("=" * 60)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="尾盘选股器")
    parser.add_argument('--mode', choices=['select', 'config', 'detail', 'backtest'],
                       default='select', help='运行模式')
    parser.add_argument('--save', action='store_true', help='保存结果到 CSV')

    args = parser.parse_args()

    if args.mode == 'config':
        interactive_config()
    elif args.mode == 'select':
        quick_select()
    elif args.mode == 'detail':
        show_stock_detail()
    elif args.mode == 'backtest':
        run_backtest()


if __name__ == "__main__":
    main()
