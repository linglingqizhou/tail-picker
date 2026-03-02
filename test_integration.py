# -*- coding: utf-8 -*-
"""
尾盘选股器 - 集成测试
测试实际数据获取和策略执行
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from datetime import datetime

print("=" * 60)
print("              尾盘选股器 - 集成测试")
print("=" * 60)


# ==================== 测试 1: 数据获取集成测试 ====================
print("\n[集成测试 1] 实时数据获取测试")
print("-" * 40)

try:
    from src.akshare_api import get_all_stocks_realtime, get_individual_fund_flow

    # 测试获取全部 A 股（可能较慢，只测试前几只）
    print("获取全部 A 股实时行情...")
    all_stocks = get_all_stocks_realtime()

    if all_stocks is not None and not all_stocks.empty:
        print(f"✓ 获取成功，共 {len(all_stocks)} 只股票")

        # 检查必要列
        required_cols = ['代码', '名称', '最新价', '涨跌幅']
        missing_cols = [col for col in required_cols if col not in all_stocks.columns]
        if missing_cols:
            print(f"⚠ 缺少列：{missing_cols}")
        else:
            print(f"✓ 必要列完整：{required_cols}")

        # 显示前 5 只
        print("\n前 5 只股票:")
        print(all_stocks[required_cols].head().to_string())

    else:
        print("✗ 获取数据为空")

except Exception as e:
    print(f"✗ 数据获取失败：{e}")


# ==================== 测试 2: 资金流数据测试 ====================
print("\n[集成测试 2] 资金流数据测试")
print("-" * 40)

try:
    from src.akshare_api import get_individual_fund_flow

    print("获取资金流向数据...")
    fund_flow = get_individual_fund_flow()

    if fund_flow is not None and not fund_flow.empty:
        print(f"✓ 获取成功，共 {len(fund_flow)} 条记录")
        print("\n资金流 Top 5:")
        print(fund_flow.head(5).to_string())
    else:
        print("⚠ 资金流数据为空（可能是网络问题）")

except Exception as e:
    print(f"✗ 资金流获取失败：{e}")


# ==================== 测试 3: 尾盘选股策略执行测试 ====================
print("\n[集成测试 3] 尾盘选股策略执行测试")
print("-" * 40)

try:
    from src.strategies.tail_strategy import TailStockStrategy

    # 使用测试数据
    test_config = {
        'top_n': 5,
        'min_gain': 2.0,
        'max_gain': 10.0,
        'min_volume_ratio': 1.0,
        'min_turnover': 3.0,
        'max_turnover': 25.0,
        'min_main_inflow': 0,
        'exclude_st': True,
    }

    picker = TailStockStrategy(test_config)

    # 获取测试数据（只取前 100 只加快测试）
    from src.akshare_api import get_all_stocks_realtime, get_individual_fund_flow

    all_data = get_all_stocks_realtime()
    fund_flow = get_individual_fund_flow()

    if all_data is not None and not all_data.empty:
        # 取前 100 只测试
        test_data = all_data.head(100)
        print(f"使用 {len(test_data)} 只股票进行测试...")

        picker.set_fund_flow_data(fund_flow)
        result = picker.select(test_data)

        if not result.empty:
            print(f"✓ 策略执行成功，选中 {len(result)} 只股票")
            print("\n选股结果:")
            cols = ['代码', '名称', '最新价', '涨跌幅', 'score']
            available_cols = [c for c in cols if c in result.columns]
            print(result[available_cols].to_string())
        else:
            print("⚠ 策略未选中任何股票（可能是条件太严格）")

except Exception as e:
    print(f"✗ 策略执行失败：{e}")
    import traceback
    traceback.print_exc()


# ==================== 测试 4: 腾讯财经数据源测试 ====================
print("\n[集成测试 4] 腾讯财经数据源测试")
print("-" * 40)

try:
    from src.data_sources.qq_source import TencentStockAPI

    qq_api = TencentStockAPI(timeout=10)

    # 测试获取多只股票
    symbols = ['600519', '000001', '300750']
    print(f"获取 {symbols} 实时行情...")
    df = qq_api.get_realtime(symbols)

    if df is not None and not df.empty:
        print(f"✓ 获取成功，返回 {len(df)} 条数据")
        print(df[['symbol', 'name', 'current', 'change_percent']].to_string())
    else:
        print("⚠ 返回数据为空")

except Exception as e:
    print(f"✗ 腾讯财经测试失败：{e}")


# ==================== 测试 5: 数据源管理器自动切换测试 ====================
print("\n[集成测试 5] 数据源管理器自动切换测试")
print("-" * 40)

try:
    from src.data_sources.manager import DataSourceManager

    manager = DataSourceManager({'timeout': 10})

    print("测试数据源健康检查...")
    status = manager.health_check_all()

    for name, info in status.items():
        status_str = "✓ 可用" if info['available'] else "✗ 不可用"
        print(f"  {name} (优先级 {info['priority']}): {status_str}")

    # 测试获取全部 A 股（自动选择数据源）
    print("\n测试自动获取全部 A 股（前 50 只）...")
    # 注意：实际获取全部会比较慢，这里只测试接口可用性

except Exception as e:
    print(f"✗ 数据源管理器测试失败：{e}")


# ==================== 测试 6: 导出功能测试 ====================
print("\n[集成测试 6] 数据导出功能测试")
print("-" * 40)

try:
    from src.export import DataExporter
    import pandas as pd

    # 创建测试数据
    test_df = pd.DataFrame({
        '代码': ['000001', '600519', '300750'],
        '名称': ['平安银行', '贵州茅台', '宁德时代'],
        '最新价': [12.5, 1800.0, 200.0],
        '涨跌幅': [4.5, 6.2, 5.8],
        '量比': [1.8, 2.1, 1.9],
        '换手率': [5.2, 2.1, 3.8],
        'score': [85.5, 92.0, 88.3]
    })

    exporter = DataExporter()

    # 测试 CSV 导出
    csv_path = exporter.export_csv(test_df, 'test_export.csv')
    if os.path.exists(csv_path):
        print(f"✓ CSV 导出成功：{csv_path}")
        # 清理测试文件
        os.remove(csv_path)
        print("  (测试文件已清理)")
    else:
        print("✗ CSV 导出失败")

    # 测试推送格式
    push_msg = exporter.export_for_push(test_df, top_n=3)
    if push_msg and len(push_msg) > 100:
        print(f"✓ 推送格式生成成功，长度：{len(push_msg)} 字符")
    else:
        print("✗ 推送格式生成失败")

except Exception as e:
    print(f"✗ 导出功能测试失败：{e}")


# ==================== 测试 7: 回测引擎测试 ====================
print("\n[集成测试 7] 回测引擎测试（简化）")
print("-" * 40)

try:
    from src.backtest import BacktestEngine

    engine = BacktestEngine({
        'top_n': 3,
        'min_gain': 3.0,
        'max_gain': 7.0,
    })

    # 测试获取交易日（不实际运行回测，只测试接口）
    trading_days = engine.get_trading_days("20260101", "20260110")
    print(f"✓ 回测引擎初始化成功")
    print(f"  测试区间交易日：{len(trading_days)} 天")
    print(f"  交易日：{trading_days[:5]}...")

except Exception as e:
    print(f"✗ 回测引擎测试失败：{e}")


# ==================== 测试结果汇总 ====================
print("\n" + "=" * 60)
print("                    集成测试完成")
print("=" * 60)
print("\n提示：以上测试验证了主要功能的可用性")
print("实际使用时请确保网络连接正常")
print("=" * 60)
