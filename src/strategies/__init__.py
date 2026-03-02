"""
策略模块
包含多种选股策略：尾盘选股、强势股回调、突破、龙虎榜等
"""

# 先导入基类和工厂
from src.strategies.base import BaseStrategy, StrategyFactory

# 再导入具体策略（避免循环导入）
from src.strategies.tail_strategy import TailStockStrategy
from src.strategies.pullback_strategy import PullbackStrategy
from src.strategies.breakthrough_strategy import BreakthroughStrategy
from src.strategies.lhb_strategy import LHBStrategy

# 注册策略到工厂
StrategyFactory.register('tail', TailStockStrategy)
StrategyFactory.register('pullback', PullbackStrategy)
StrategyFactory.register('breakthrough', BreakthroughStrategy)
StrategyFactory.register('lhb', LHBStrategy)

__all__ = [
    'BaseStrategy',
    'TailStockStrategy',
    'PullbackStrategy',
    'BreakthroughStrategy',
    'LHBStrategy',
    'StrategyFactory',
]
