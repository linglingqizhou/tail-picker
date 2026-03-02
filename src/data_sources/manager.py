# -*- coding: utf-8 -*-
"""
数据源管理器
支持多数据源自动切换，优先级：AkShare > 腾讯财经 > 新浪财经
"""

import pandas as pd
from typing import Dict, List, Optional
from datetime import datetime
import time

from src.data_sources.base import BaseDataSource
from src.data_sources.qq_source import TencentStockAPI
from src.sina_api import SinaStockAPI


class DataSourceManager:
    """数据源管理器"""

    # 默认配置
    DEFAULT_CONFIG = {
        'timeout': 10,              # 请求超时时间（秒）
        'max_retries': 3,           # 最大重试次数
        'retry_delay': 2,           # 重试延迟（秒）
        'auto_switch': True,        # 自动切换数据源
        'health_check': True,       # 启用健康检查
    }

    def __init__(self, config: Dict = None):
        """
        初始化数据源管理器

        Args:
            config: 配置字典
        """
        self.config = self.DEFAULT_CONFIG.copy()
        if config:
            self.config.update(config)

        # 初始化数据源（按优先级排序）
        self.data_sources: List[BaseDataSource] = []
        self._current_index = 0
        self._source_status = {}  # 数据源状态

        # 注册数据源
        self._register_sources()

    def _register_sources(self):
        """注册数据源"""
        timeout = self.config.get('timeout', 10)

        # 1. AkShare（优先级最高）
        try:
            from src.akshare_api import get_all_stocks_realtime, get_individual_fund_flow
            # AkShare 使用函数式接口，创建适配器
            ak_source = AkShareAdapter(timeout)
            ak_source.PRIORITY = 1
            self.data_sources.append(ak_source)
            self._source_status['akshare'] = {'available': True, 'last_check': None}
        except Exception as e:
            print(f"注册 AkShare 数据源失败：{e}")

        # 2. 腾讯财经
        try:
            qq_source = TencentStockAPI(timeout)
            self.data_sources.append(qq_source)
            self._source_status['tencent'] = {'available': True, 'last_check': None}
        except Exception as e:
            print(f"注册腾讯财经数据源失败：{e}")

        # 3. 新浪财经
        try:
            sina_source = SinaStockAPI(timeout)
            # 创建适配器
            sina_adapter = SinaAdapter(sina_source)
            sina_adapter.PRIORITY = 3
            self.data_sources.append(sina_adapter)
            self._source_status['sina'] = {'available': True, 'last_check': None}
        except Exception as e:
            print(f"注册新浪财经数据源失败：{e}")

        # 按优先级排序
        self.data_sources.sort(key=lambda x: x.PRIORITY)

        print(f"已注册 {len(self.data_sources)} 个数据源:")
        for ds in self.data_sources:
            print(f"  - {ds.NAME} (优先级：{ds.PRIORITY})")

    def _get_available_source(self) -> Optional[BaseDataSource]:
        """
        获取可用的数据源

        Returns:
            BaseDataSource: 可用的数据源，如果没有则返回 None
        """
        if not self.data_sources:
            return None

        # 按优先级尝试
        for i, source in enumerate(self.data_sources):
            # 检查状态
            if self.config.get('health_check', True):
                status = self._source_status.get(source.NAME, {})
                if not status.get('available', True):
                    # 检查是否可以重新尝试（距离上次失败超过 5 分钟）
                    last_check = status.get('last_check')
                    if last_check:
                        elapsed = (datetime.now() - last_check).total_seconds()
                        if elapsed < 300:  # 5 分钟内不再尝试
                            continue

            # 健康检查
            if source.health_check():
                self._current_index = i
                self._source_status[source.NAME] = {'available': True, 'last_check': datetime.now()}
                return source
            else:
                self._source_status[source.NAME] = {'available': False, 'last_check': datetime.now()}
                print(f"数据源 {source.NAME} 不可用，尝试下一个...")

        return None

    @property
    def current_source(self) -> Optional[BaseDataSource]:
        """获取当前数据源"""
        return self._get_available_source()

    def get_all_a_shares(self, use_backup: bool = True) -> pd.DataFrame:
        """
        获取全部 A 股实时行情

        Args:
            use_backup: 是否使用备份数据源

        Returns:
            DataFrame: 全部 A 股行情数据
        """
        max_retries = self.config.get('max_retries', 3)
        retry_delay = self.config.get('retry_delay', 2)

        sources_to_try = self.data_sources.copy() if use_backup else [self.data_sources[0]] if self.data_sources else []

        for source in sources_to_try:
            print(f"尝试从 {source.NAME} 获取数据...")

            for attempt in range(max_retries):
                try:
                    df = source.get_all_a_shares()
                    if df is not None and not df.empty:
                        print(f"从 {source.NAME} 获取成功，共 {len(df)} 只股票")
                        self._source_status[source.NAME] = {'available': True, 'last_check': datetime.now()}
                        return df
                except Exception as e:
                    if attempt < max_retries - 1:
                        print(f"  尝试 {attempt + 1}/{max_retries} 失败，{retry_delay}秒后重试...")
                        time.sleep(retry_delay)
                    else:
                        print(f"  {source.NAME} 获取失败：{e}")
                        self._source_status[source.NAME] = {'available': False, 'last_check': datetime.now()}

        print("所有数据源均获取失败")
        return pd.DataFrame()

    def get_realtime(self, symbols: List[str]) -> pd.DataFrame:
        """
        获取实时行情

        Args:
            symbols: 股票代码列表

        Returns:
            DataFrame: 实时行情数据
        """
        source = self.current_source
        if not source:
            print("没有可用的数据源")
            return pd.DataFrame()

        try:
            return source.get_realtime(symbols)
        except Exception as e:
            print(f"获取实时行情失败：{e}")
            return pd.DataFrame()

    def get_fund_flow(self, symbol: str = None) -> pd.DataFrame:
        """
        获取资金流向数据

        Args:
            symbol: 股票代码，None 表示获取排名

        Returns:
            DataFrame: 资金流向数据
        """
        # 资金流数据只有 AkShare 支持
        for source in self.data_sources:
            if hasattr(source, 'get_fund_flow'):
                try:
                    df = source.get_fund_flow(symbol)
                    if df is not None and not df.empty:
                        return df
                except Exception as e:
                    continue

        print("所有数据源资金流接口均不可用")
        return pd.DataFrame()

    def get_lhb(self, date: str = None) -> pd.DataFrame:
        """
        获取龙虎榜数据

        Args:
            date: 日期

        Returns:
            DataFrame: 龙虎榜数据
        """
        # 龙虎榜数据只有 AkShare 支持
        for source in self.data_sources:
            if hasattr(source, 'get_lhb'):
                try:
                    df = source.get_lhb(date)
                    if df is not None and not df.empty:
                        return df
                except Exception as e:
                    continue

        print("所有数据源龙虎榜接口均不可用")
        return pd.DataFrame()

    def get_status(self) -> Dict:
        """获取所有数据源状态"""
        status = {}
        for source in self.data_sources:
            name = source.NAME
            status[name] = {
                'priority': source.PRIORITY,
                'available': self._source_status.get(name, {}).get('available', None),
                'last_check': self._source_status.get(name, {}).get('last_check', None),
            }
        return status

    def health_check_all(self) -> Dict:
        """检查所有数据源健康状态"""
        results = {}
        for source in self.data_sources:
            available = source.health_check()
            results[source.NAME] = {
                'available': available,
                'priority': source.PRIORITY,
            }
            self._source_status[source.NAME] = {
                'available': available,
                'last_check': datetime.now(),
            }
        return results


class AkShareAdapter(BaseDataSource):
    """AkShare 数据源自适配"""

    NAME = "AkShare"
    DESCRIPTION = "AkShare 财经数据接口"
    PRIORITY = 1

    def __init__(self, timeout: int = 10):
        super().__init__(timeout)

    def get_realtime(self, symbols: List[str]) -> pd.DataFrame:
        from src.akshare_api import get_all_stocks_realtime
        df = get_all_stocks_realtime()
        if df is None or symbols is None:
            return df

        # 筛选指定股票
        if '代码' in df.columns:
            df = df[df['代码'].isin(symbols)]
        return df

    def get_all_a_shares(self) -> pd.DataFrame:
        from src.akshare_api import get_all_stocks_realtime
        df = get_all_stocks_realtime()
        return df if df is not None else pd.DataFrame()

    def get_fund_flow(self, symbol: str = None) -> pd.DataFrame:
        from src.akshare_api import get_individual_fund_flow
        return get_individual_fund_flow(symbol)

    def get_lhb(self, date: str = None) -> pd.DataFrame:
        from src.akshare_api import get_lhb_today, get_lhb_detail
        if date:
            return get_lhb_detail(date)
        return get_lhb_today()


class SinaAdapter(BaseDataSource):
    """新浪财经数据源自适配"""

    NAME = "新浪财经"
    DESCRIPTION = "新浪财经实时行情接口"
    PRIORITY = 3

    def __init__(self, api: SinaStockAPI):
        super().__init__(api.timeout)
        self.api = api

    def get_realtime(self, symbols: List[str]) -> pd.DataFrame:
        return self.api.get_batch_realtime(symbols)

    def get_all_a_shares(self) -> pd.DataFrame:
        return self.api.get_all_a_shares()


# 便捷函数
def get_data_source_manager() -> DataSourceManager:
    """获取数据源管理器实例"""
    return DataSourceManager()


if __name__ == "__main__":
    # 测试代码
    print("=" * 50)
    print("测试数据源管理器")
    print("=" * 50)

    manager = DataSourceManager()

    # 测试 1：健康检查
    print("\n[测试 1] 数据源健康检查...")
    status = manager.health_check_all()
    for name, info in status.items():
        print(f"  {name}: {'可用' if info['available'] else '不可用'} (优先级：{info['priority']})")

    # 测试 2：获取全部 A 股
    print("\n[测试 2] 获取全部 A 股（自动选择数据源）...")
    df = manager.get_all_a_shares()
    if not df.empty:
        print(f"获取成功，共 {len(df)} 只股票")
        print(df.head().to_string())
    else:
        print("获取失败")

    # 测试 3：获取实时行情
    print("\n[测试 3] 获取多只股票实时行情...")
    test_symbols = ["600519", "000001", "000858"]
    df = manager.get_realtime(test_symbols)
    if not df.empty:
        print(df.to_string())

    # 测试 4：显示状态
    print("\n[测试 4] 数据源状态:")
    status = manager.get_status()
    for name, info in status.items():
        print(f"  {name}: 可用={info['available']}, 优先级={info['priority']}")
