# -*- coding: utf-8 -*-
"""
尾盘选股器 - 主程序
整合选股、回测、导出、推送功能
支持多种策略：尾盘选股、强势股回调、突破、龙虎榜
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 设置 UTF-8 编码环境变量（Windows）
os.environ['PYTHONIOENCODING'] = 'utf-8'

import pandas as pd
from datetime import datetime
from pathlib import Path

from src.strategies.tail_strategy import TailStockStrategy
from src.strategies.pullback_strategy import PullbackStrategy
from src.strategies.breakthrough_strategy import BreakthroughStrategy
from src.strategies.lhb_strategy import LHBStrategy
from src.strategies.base import StrategyFactory
from src.backtest import BacktestEngine
from src.export import export_result, DataExporter
from src.notify.serverchan import ServerChanNotifier
from src.data_sources.manager import DataSourceManager

# 尝试加载配置
try:
    from config import (
        TAIL_PICKER_CONFIG,
        PULLBACK_CONFIG,
        BREAKTHROUGH_CONFIG,
        LHB_CONFIG,
        SERVERCHAN_CONFIG,
        DATA_SOURCE_CONFIG,
    )
except ImportError:
    TAIL_PICKER_CONFIG = {}
    PULLBACK_CONFIG = {}
    BREAKTHROUGH_CONFIG = {}
    LHB_CONFIG = {}
    SERVERCHAN_CONFIG = {}
    DATA_SOURCE_CONFIG = {}


# 默认配置
DEFAULT_CONFIG = {
    'top_n': 20,
    'min_gain': 3.0,
    'max_gain': 7.0,
    'min_volume_ratio': 1.5,
    'min_turnover': 5.0,
    'max_turnover': 20.0,
    'min_main_inflow': 500,
    'max_market_cap': 500,
}


def run_tail_pick(config=None, save=True, show_detail=True, push=False):
    """
    运行尾盘选股

    Args:
        config: 配置字典
        save: 是否保存
        show_detail: 是否显示详情
        push: 是否推送消息

    Returns:
        DataFrame: 选股结果
    """
    print("\n" + "=" * 70)
    print("                    尾盘选股器")
    print("         " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("=" * 70)

    # 合并配置
    final_config = {**DEFAULT_CONFIG, **TAIL_PICKER_CONFIG, **(config or {})}

    # 创建选股器
    picker = TailStockStrategy(final_config)

    # 获取数据
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 获取数据...")
    from src.akshare_api import get_all_stocks_realtime, get_individual_fund_flow

    all_data = get_all_stocks_realtime()
    fund_flow = get_individual_fund_flow()

    if all_data is not None and not all_data.empty:
        picker.set_fund_flow_data(fund_flow)
        # 执行选股
        result = picker.select(all_data)
    else:
        print("获取数据失败")
        return pd.DataFrame()

    if result.empty:
        print("\n未找到符合条件的股票")
        return pd.DataFrame()

    print(f"\n选中 {len(result)} 只股票")

    # 保存结果
    if save:
        exporter = DataExporter()

        # CSV
        csv_path = exporter.export_csv(result)
        print(f"CSV 已保存：{csv_path}")

        # 显示推送格式
        print("\n" + exporter.export_for_push(result, top_n=10))

        # 发送推送
        if push:
            send_notification(result)

    return result


def run_strategy(strategy_name: str, config: dict = None, show_detail: bool = True):
    """
    运行指定策略

    Args:
        strategy_name: 策略名称 (tail/pullback/breakthrough/lhb)
        config: 配置字典
        show_detail: 是否显示详情

    Returns:
        DataFrame: 选股结果
    """
    print("\n" + "=" * 70)
    print(f"                    {strategy_name} 策略")
    print("         " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("=" * 70)

    # 获取基础数据
    from src.akshare_api import get_all_stocks_realtime
    all_data = get_all_stocks_realtime()

    if all_data is None or all_data.empty:
        print("获取数据失败")
        return pd.DataFrame()

    # 创建策略实例
    try:
        strategy = StrategyFactory.create(strategy_name, config)
    except ValueError as e:
        print(f"错误：{e}")
        return pd.DataFrame()

    # 执行选股
    result = strategy.select(all_data)

    if result.empty:
        print("\n未找到符合条件的股票")
        return pd.DataFrame()

    print(f"\n选中 {len(result)} 只股票")

    if show_detail:
        from tabulate import tabulate
        cols_to_show = ['代码', '名称', '最新价', '涨跌幅', 'score']
        available_cols = [c for c in cols_to_show if c in result.columns]
        if available_cols:
            print("\n选股结果:")
            print(tabulate(result[available_cols].head(10), headers='keys', tablefmt='grid', showindex=False))

    return result


def run_all_strategies(config: dict = None):
    """
    运行所有策略

    Args:
        config: 配置字典

    Returns:
        dict: 各策略结果
    """
    print("\n" + "=" * 70)
    print("                    运行所有策略")
    print("         " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("=" * 70)

    strategies = {
        'tail': ('尾盘选股', TAIL_PICKER_CONFIG),
        'pullback': ('强势股回调', PULLBACK_CONFIG),
        'breakthrough': ('突破', BREAKTHROUGH_CONFIG),
        'lhb': ('龙虎榜', LHB_CONFIG),
    }

    results = {}
    for key, (name, default_cfg) in strategies.items():
        print(f"\n--- {name} ---")
        cfg = {**(default_cfg or {}), **(config or {})}
        result = run_strategy(key, cfg, show_detail=False)
        results[key] = result
        print(f"  {name}: {len(result)} 只")

    return results


def send_notification(df: pd.DataFrame):
    """发送推送消息"""
    # 从配置加载
    notifier = ServerChanNotifier(SERVERCHAN_CONFIG if SERVERCHAN_CONFIG.get('send_key') else None)

    if notifier.enabled:
        notifier.send(df)
    else:
        print("\nServer 酱未启用，请在 config.py 中设置 send_key")
        print("获取方式：访问 https://sct.ftqq.com/ 注册并获取 send_key")


def run_backtest(start_date=None, end_date=None, hold_days=1):
    """
    运行回测

    Args:
        start_date: 开始日期 YYYYMMDD
        end_date: 结束日期 YYYYMMDD
        hold_days: 持有天数

    Returns:
        dict: 回测报告
    """
    print("\n" + "=" * 70)
    print("                    历史回测")
    print("=" * 70)

    if start_date is None:
        start_date = "20250101"
    if end_date is None:
        end_date = datetime.now().strftime("%Y%m%d")

    engine = BacktestEngine({**DEFAULT_CONFIG, **TAIL_PICKER_CONFIG})
    report = engine.run(start_date, end_date, hold_days)

    # 打印报告
    print("\n" + "=" * 70)
    print("                    回测报告摘要")
    print("=" * 70)
    print(f"  回测区间：{start_date} ~ {end_date}")
    print(f"  持有天数：{hold_days}天")
    print("-" * 70)
    for k, v in report.items():
        if isinstance(v, float):
            print(f"  {k}: {v:.2f}%")
        else:
            print(f"  {k}: {v}")
    print("=" * 70)

    return report


def test_data_sources():
    """测试数据源"""
    print("\n" + "=" * 70)
    print("                    数据源健康检查")
    print("=" * 70)

    manager = DataSourceManager(DATA_SOURCE_CONFIG if DATA_SOURCE_CONFIG else None)
    status = manager.health_check_all()

    print("\n数据源状态:")
    for name, info in status.items():
        status_str = "✓ 可用" if info['available'] else "× 不可用"
        print(f"  {name} (优先级 {info['priority']}): {status_str}")

    return status


def quick_pick():
    """快速选股（一键运行）"""
    return run_tail_pick(save=True, show_detail=True, push=False)


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="尾盘选股器 - 增强版")
    parser.add_argument('--mode', choices=['pick', 'backtest', 'quick', 'clear_cache',
                                           'pullback', 'breakthrough', 'lhb', 'all', 'test_source'],
                       default='quick', help='运行模式')
    parser.add_argument('--start-date', help='回测开始日期 YYYYMMDD')
    parser.add_argument('--end-date', help='回测结束日期 YYYYMMDD')
    parser.add_argument('--hold-days', type=int, default=1, help='回测持有天数')
    parser.add_argument('--push', action='store_true', help='是否推送消息到微信')
    parser.add_argument('--strategy-config', type=str, help='策略配置文件路径 (JSON)')

    args = parser.parse_args()

    # 加载策略配置
    strategy_config = {}
    if args.strategy_config:
        try:
            import json
            with open(args.strategy_config, 'r', encoding='utf-8') as f:
                strategy_config = json.load(f)
        except Exception as e:
            print(f"加载策略配置失败：{e}")

    if args.mode == 'pick':
        run_tail_pick(config=strategy_config, save=True, show_detail=True, push=args.push)
    elif args.mode == 'backtest':
        run_backtest(args.start_date, args.end_date, args.hold_days)
    elif args.mode == 'clear_cache':
        print("清除缓存...")
        from src.tail_picker import TailStockPicker
        picker = TailStockPicker()
        picker.clear_fund_flow_cache()
        print("完成")
    elif args.mode == 'quick':
        quick_pick()
    elif args.mode == 'pullback':
        run_strategy('pullback', config=strategy_config)
    elif args.mode == 'breakthrough':
        run_strategy('breakthrough', config=strategy_config)
    elif args.mode == 'lhb':
        run_strategy('lhb', config=strategy_config)
    elif args.mode == 'all':
        run_all_strategies(config=strategy_config)
    elif args.mode == 'test_source':
        test_data_sources()


if __name__ == "__main__":
    main()
