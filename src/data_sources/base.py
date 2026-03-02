# -*- coding: utf-8 -*-
"""
数据源基类模块
定义所有数据源的通用接口
"""

import pandas as pd
from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from datetime import datetime


class BaseDataSource(ABC):
    """数据源基类"""

    # 数据源名称（子类需覆盖）
    NAME = "基础数据源"

    # 数据源描述（子类需覆盖）
    DESCRIPTION = "基础数据源"

    # 优先级（数字越小优先级越高）
    PRIORITY = 99

    def __init__(self, timeout: int = 10):
        """
        初始化数据源

        Args:
            timeout: 请求超时时间（秒）
        """
        self.timeout = timeout
        self.session = None
        self._initialized = False

    @abstractmethod
    def get_realtime(self, symbols: List[str]) -> pd.DataFrame:
        """
        获取实时行情

        Args:
            symbols: 股票代码列表

        Returns:
            DataFrame: 实时行情数据
        """
        pass

    @abstractmethod
    def get_all_a_shares(self) -> pd.DataFrame:
        """
        获取全部 A 股实时行情

        Returns:
            DataFrame: 全部 A 股行情数据
        """
        pass

    def get_history(self, symbol: str, start_date: str, end_date: str = None) -> pd.DataFrame:
        """
        获取历史 K 线数据

        Args:
            symbol: 股票代码
            start_date: 开始日期 YYYYMMDD
            end_date: 结束日期 YYYYMMDD

        Returns:
            DataFrame: 历史 K 线数据
        """
        raise NotImplementedError(f"{self.NAME} 不支持历史数据接口")

    def get_fund_flow(self, symbol: str = None) -> pd.DataFrame:
        """
        获取资金流向数据

        Args:
            symbol: 股票代码，None 表示获取排名

        Returns:
            DataFrame: 资金流向数据
        """
        raise NotImplementedError(f"{self.NAME} 不支持资金流接口")

    def get_lhb(self, date: str = None) -> pd.DataFrame:
        """
        获取龙虎榜数据

        Args:
            date: 日期 YYYY-MM-DD

        Returns:
            DataFrame: 龙虎榜数据
        """
        raise NotImplementedError(f"{self.NAME} 不支持龙虎榜接口")

    def health_check(self) -> bool:
        """
        健康检查

        Returns:
            bool: 是否可用
        """
        try:
            # 尝试获取单只股票行情
            test_symbols = ['000001']
            df = self.get_realtime(test_symbols)
            return df is not None and not df.empty
        except Exception:
            return False

    def get_status(self) -> Dict:
        """获取数据源状态"""
        return {
            'name': self.NAME,
            'description': self.DESCRIPTION,
            'priority': self.PRIORITY,
            'available': self.health_check(),
        }
