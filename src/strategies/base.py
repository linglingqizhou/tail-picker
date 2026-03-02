# -*- coding: utf-8 -*-
"""
策略基类模块
定义所有策略的通用接口
"""

import pandas as pd
from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from datetime import datetime


class BaseStrategy(ABC):
    """策略基类"""

    # 策略名称（子类需覆盖）
    NAME = "基础策略"

    # 策略描述（子类需覆盖）
    DESCRIPTION = "基础选股策略"

    # 默认配置（子类可覆盖）
    DEFAULT_CONFIG = {}

    def __init__(self, config: Dict = None):
        """
        初始化策略

        Args:
            config: 策略配置字典
        """
        self.config = self.DEFAULT_CONFIG.copy()
        if config:
            self.config.update(config)

        # 数据缓存
        self.data_cache = {}

    @abstractmethod
    def select(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        执行选股策略

        Args:
            data: 基础数据 DataFrame（包含行情、财务等数据）

        Returns:
            DataFrame: 筛选结果
        """
        pass

    def validate_data(self, data: pd.DataFrame) -> bool:
        """
        验证数据是否满足策略基本要求

        Args:
            data: 基础数据 DataFrame

        Returns:
            bool: 是否满足要求
        """
        if data is None or data.empty:
            return False
        return True

    def get_required_columns(self) -> List[str]:
        """
        获取策略所需的列名

        Returns:
            list: 列名列表
        """
        return []

    def calculate_score(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        计算综合评分（可选）

        Args:
            df: 筛选后的 DataFrame

        Returns:
            DataFrame: 添加评分列
        """
        df = df.copy()
        df['score'] = 0.0
        return df

    def get_stock_history(self, symbol: str, days: int = 60) -> pd.DataFrame:
        """
        获取个股历史数据（供子类使用）

        Args:
            symbol: 股票代码
            days: 获取天数

        Returns:
            DataFrame: 历史 K 线数据
        """
        from src.akshare_api import get_stock_history
        from datetime import timedelta

        start_date = (datetime.now() - timedelta(days=days)).strftime("%Y%m%d")
        return get_stock_history(symbol, start_date=start_date)

    def get_info(self) -> Dict:
        """
        获取策略信息

        Returns:
            dict: 策略信息
        """
        return {
            'name': self.NAME,
            'description': self.DESCRIPTION,
            'config': self.config,
            'required_columns': self.get_required_columns(),
        }


class StrategyFactory:
    """策略工厂类"""

    _strategies = {}

    @classmethod
    def register(cls, name: str, strategy_class):
        """注册策略"""
        cls._strategies[name] = strategy_class

    @classmethod
    def create(cls, name: str, config: Dict = None):
        """创建策略实例"""
        if name not in cls._strategies:
            raise ValueError(f"未知策略：{name}")
        return cls._strategies[name](config)

    @classmethod
    def get_all_strategies(cls) -> List[str]:
        """获取所有已注册的策略"""
        return list(cls._strategies.keys())

    @classmethod
    def run_all(cls, data: pd.DataFrame, configs: Dict = None) -> Dict[str, pd.DataFrame]:
        """运行所有策略"""
        results = {}
        configs = configs or {}

        for name, strategy_class in cls._strategies.items():
            try:
                strategy = strategy_class(configs.get(name, {}))
                results[name] = strategy.select(data)
            except Exception as e:
                print(f"策略 {name} 执行失败：{e}")
                results[name] = pd.DataFrame()

        return results


# 注意：策略注册在 __init__.py 中进行，避免循环导入
