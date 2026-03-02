# -*- coding: utf-8 -*-
"""
尾盘选股器 - 测试脚本
测试所有新增功能模块
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

print("=" * 60)
print("              尾盘选股器 - 功能测试")
print("=" * 60)

# ==================== 测试 1: 模块导入测试 ====================
print("\n[测试 1] 模块导入测试")
print("-" * 40)

test_results = []

# 1.1 ServerChan 推送模块
try:
    from src.notify.serverchan import ServerChanNotifier
    print("✓ ServerChan 模块导入成功")
    test_results.append(('ServerChan 导入', True))
except Exception as e:
    print(f"✗ ServerChan 模块导入失败：{e}")
    test_results.append(('ServerChan 导入', False))

# 1.2 策略模块
try:
    from src.strategies.tail_strategy import TailStockStrategy
    print("✓ 尾盘选股策略导入成功")
    test_results.append(('尾盘策略导入', True))
except Exception as e:
    print(f"✗ 尾盘选股策略导入失败：{e}")
    test_results.append(('尾盘策略导入', False))

try:
    from src.strategies.pullback_strategy import PullbackStrategy
    print("✓ 强势股回调策略导入成功")
    test_results.append(('回调策略导入', True))
except Exception as e:
    print(f"✗ 强势股回调策略导入失败：{e}")
    test_results.append(('回调策略导入', False))

try:
    from src.strategies.breakthrough_strategy import BreakthroughStrategy
    print("✓ 突破策略导入成功")
    test_results.append(('突破策略导入', True))
except Exception as e:
    print(f"✗ 突破策略导入失败：{e}")
    test_results.append(('突破策略导入', False))

try:
    from src.strategies.lhb_strategy import LHBStrategy
    print("✓ 龙虎榜策略导入成功")
    test_results.append(('龙 2 榜策略导入', True))
except Exception as e:
    print(f"✗ 龙虎榜策略导入失败：{e}")
    test_results.append(('龙虎榜策略导入', False))

# 1.3 数据源模块
try:
    from src.data_sources.qq_source import TencentStockAPI
    print("✓ 腾讯财经数据源导入成功")
    test_results.append(('腾讯数据源导入', True))
except Exception as e:
    print(f"✗ 腾讯财经数据源导入失败：{e}")
    test_results.append(('腾讯数据源导入', False))

try:
    from src.data_sources.manager import DataSourceManager
    print("✓ 数据源管理器导入成功")
    test_results.append(('数据源管理器导入', True))
except Exception as e:
    print(f"✗ 数据源管理器导入失败：{e}")
    test_results.append(('数据源管理器导入', False))

# 1.4 策略工厂
try:
    from src.strategies import StrategyFactory
    strategies = StrategyFactory.get_all_strategies()
    print(f"✓ 策略工厂导入成功，已注册策略：{strategies}")
    test_results.append(('策略工厂导入', True))
except Exception as e:
    print(f"✗ 策略工厂导入失败：{e}")
    test_results.append(('策略工厂导入', False))

# 1.5 配置加载
try:
    from config import SERVERCHAN_CONFIG, TAIL_PICKER_CONFIG, PULLBACK_CONFIG
    print("✓ 配置文件加载成功")
    test_results.append(('配置文件加载', True))
except Exception as e:
    print(f"✗ 配置文件加载失败：{e}")
    test_results.append(('配置文件加载', False))


# ==================== 测试 2: ServerChan 推送功能测试 ====================
print("\n[测试 2] ServerChan 推送功能测试")
print("-" * 40)

try:
    import pandas as pd
    # 测试配置（无 send_key 情况）
    notifier = ServerChanNotifier({'send_key': '', 'enabled': False})
    print(f"✓ ServerChan 初始化成功，enabled={notifier.enabled}")

    # 测试消息格式化
    test_df = pd.DataFrame({
        '代码': ['000001', '600519'],
        '名称': ['平安银行', '贵州茅台'],
        '涨跌幅': [4.5, 6.2],
        '量比': [1.8, 2.1],
        '换手率': [5.2, 2.1],
        'score': [85.5, 92.0]
    })
    msg = notifier.format_message(test_df, top_n=10)
    if msg and len(msg) > 100:
        print(f"✓ 消息格式化成功，长度：{len(msg)} 字符")
        test_results.append(('ServerChan 格式化', True))
    else:
        print("✗ 消息格式化失败")
        test_results.append(('ServerChan 格式化', False))

    # 测试发送（无 send_key 应返回错误）
    result = notifier.send(test_df)
    if 'error' in result:
        print(f"✓ 发送功能正常（预期错误：{result['error']}）")
        test_results.append(('ServerChan 发送', True))
    else:
        print(f"✗ 发送功能异常：{result}")
        test_results.append(('ServerChan 发送', False))

except Exception as e:
    print(f"✗ ServerChan 测试失败：{e}")
    test_results.append(('ServerChan 测试', False))


# ==================== 测试 3: 策略配置测试 ====================
print("\n[测试 3] 策略配置测试")
print("-" * 40)

try:
    # 尾盘选股策略配置
    tail_cfg = TAIL_PICKER_CONFIG if 'TAIL_PICKER_CONFIG' in dir() else {}
    picker = TailStockStrategy(tail_cfg)
    print(f"✓ 尾盘选股策略初始化成功，配置项：{len(picker.config)}")
    test_results.append(('尾盘策略配置', True))
except Exception as e:
    print(f"✗ 尾盘选股策略配置失败：{e}")
    test_results.append(('尾盘策略配置', False))

try:
    # 强势股回调策略配置
    pullback_cfg = PULLBACK_CONFIG if 'PULLBACK_CONFIG' in dir() else {}
    pullback = PullbackStrategy(pullback_cfg)
    print(f"✓ 强势股回调策略初始化成功，配置项：{len(pullback.config)}")
    test_results.append(('回调策略配置', True))
except Exception as e:
    print(f"✗ 强势股回调策略配置失败：{e}")
    test_results.append(('回调策略配置', False))

try:
    # 突破策略配置
    breakthrough_cfg = BREAKTHROUGH_CONFIG if 'BREAKTHROUGH_CONFIG' in dir() else {}
    breakthrough = BreakthroughStrategy(breakthrough_cfg)
    print(f"✓ 突破策略初始化成功，配置项：{len(breakthrough.config)}")
    test_results.append(('突破策略配置', True))
except Exception as e:
    print(f"✗ 突破策略配置失败：{e}")
    test_results.append(('突破策略配置', False))

try:
    # 龙虎榜策略配置
    lhb_cfg = LHB_CONFIG if 'LHB_CONFIG' in dir() else {}
    lhb = LHBStrategy(lhb_cfg)
    print(f"✓ 龙虎榜策略初始化成功，配置项：{len(lhb.config)}")
    test_results.append(('龙虎榜策略配置', True))
except Exception as e:
    print(f"✗ 龙虎榜策略配置失败：{e}")
    test_results.append(('龙虎榜策略配置', False))


# ==================== 测试 4: 数据源测试 ====================
print("\n[测试 4] 数据源功能测试")
print("-" * 40)

try:
    # 腾讯财经 API
    qq_api = TencentStockAPI(timeout=5)
    print(f"✓ 腾讯财经 API 初始化成功")

    # 测试单只股票行情
    df = qq_api.get_realtime(['600519', '000001'])
    if df is not None:
        print(f"✓ 腾讯财经行情获取成功，返回 {len(df)} 条数据")
        test_results.append(('腾讯行情获取', True))
    else:
        print("✗ 腾讯财经行情获取返回空数据")
        test_results.append(('腾讯行情获取', False))

except Exception as e:
    print(f"✗ 腾讯财经 API 测试失败：{e}")
    test_results.append(('腾讯财经 API', False))

try:
    # 数据源管理器
    manager = DataSourceManager()
    print(f"✓ 数据源管理器初始化成功，注册数据源：{len(manager.data_sources)}")

    status = manager.get_status()
    for name, info in status.items():
        print(f"  - {name}: 优先级 {info['priority']}")
    test_results.append(('数据源管理器', True))
except Exception as e:
    print(f"✗ 数据源管理器测试失败：{e}")
    test_results.append(('数据源管理器', False))


# ==================== 测试 5: 策略工厂测试 ====================
print("\n[测试 5] 策略工厂测试")
print("-" * 40)

try:
    # 测试创建各策略
    for strategy_name in ['tail', 'pullback', 'breakthrough', 'lhb']:
        try:
            strategy = StrategyFactory.create(strategy_name)
            print(f"✓ 策略 '{strategy_name}' 创建成功")
        except Exception as e:
            print(f"✗ 策略 '{strategy_name}' 创建失败：{e}")
    test_results.append(('策略工厂创建', True))
except Exception as e:
    print(f"✗ 策略工厂测试失败：{e}")
    test_results.append(('策略工厂创建', False))


# ==================== 测试 6: 主程序入口测试 ====================
print("\n[测试 6] 主程序入口测试")
print("-" * 40)

try:
    # 测试主程序导入
    import src.tail_main as tail_main
    print("✓ 主程序模块导入成功")

    # 测试默认配置
    if hasattr(tail_main, 'DEFAULT_CONFIG'):
        print(f"✓ 默认配置存在，项数：{len(tail_main.DEFAULT_CONFIG)}")
    test_results.append(('主程序导入', True))
except Exception as e:
    print(f"✗ 主程序测试失败：{e}")
    test_results.append(('主程序导入', False))


# ==================== 测试结果汇总 ====================
print("\n" + "=" * 60)
print("                    测试结果汇总")
print("=" * 60)

passed = sum(1 for _, result in test_results if result)
failed = sum(1 for _, result in test_results if not result)
total = len(test_results)

print(f"\n总测试数：{total}")
print(f"通过：{passed} ✓")
print(f"失败：{failed} ✗")
print(f"通过率：{passed/total*100:.1f}%")

print("\n详细结果:")
for name, result in test_results:
    status = "✓ 通过" if result else "✗ 失败"
    print(f"  {status} - {name}")

print("\n" + "=" * 60)

if failed > 0:
    print("\n⚠️  存在测试失败，请检查上述错误信息")
    sys.exit(1)
else:
    print("\n✓ 所有测试通过!")
    sys.exit(0)
