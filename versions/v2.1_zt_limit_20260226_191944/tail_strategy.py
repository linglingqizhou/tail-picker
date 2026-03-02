# -*- coding: utf-8 -*-
"""
尾盘选股策略
基于传统一夜持股法，综合涨幅、量比、换手率、资金流等多维度选股
"""

import pandas as pd
import numpy as np
from typing import Dict, List
from datetime import datetime

from src.strategies.base import BaseStrategy


class TailStockStrategy(BaseStrategy):
    """尾盘选股策略"""

    NAME = "尾盘选股"
    DESCRIPTION = "基于涨幅、量比、换手率、资金流的综合评分策略"

    DEFAULT_CONFIG = {
        # 涨幅条件 (涨停命中率优化：4%-8.5% 最佳区间)
        'min_gain': 4.0,      # 最小涨幅% (捕捉更强强势股)
        'max_gain': 8.5,      # 最大涨幅% (允许昨日大涨的股票)

        # 量能条件 (量比 2-12 最佳区间)
        'min_volume_ratio': 2.0,  # 量比下限 (要求明显放量)
        'max_volume_ratio': 12.0, # 量比上限 (避免天量股出货)
        'min_turnover': 5.0,      # 最小换手率%
        'max_turnover': 15.0,     # 最大换手率%

        # 资金条件 (要求更强资金推动)
        'min_main_inflow': 800,   # 最小主力净流入 (万元) (500 -> 800)

        # 市值条件
        'max_market_cap': 500,    # 最大流通市值 (亿)

        # 排除条件
        'exclude_st': True,       # 排除 ST
        'min_days_listed': 60,    # 最小上市天数
        'above_ma5': True,        # 必须站上 5 日线

        # 选股数量 (精品化)
        'top_n': 10,              # 返回前 N 只 (15 -> 10)
    }

    def __init__(self, config: Dict = None):
        super().__init__(config)
        self.fund_flow_df = None

    def set_fund_flow_data(self, df: pd.DataFrame):
        """设置资金流数据"""
        self.fund_flow_df = df

    def _normalize_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        统一列名，确保量比、换手率等列存在

        Args:
            df: 原始 DataFrame

        Returns:
            DataFrame: 添加/统一列名后的 DataFrame
        """
        result = df.copy()

        # 量比列统一
        if '量比' not in result.columns:
            if 'volume_ratio' in result.columns:
                result['量比'] = result['volume_ratio']
            else:
                result['量比'] = 0.0  # 默认值

        # 换手率列统一
        if '换手率' not in result.columns:
            if 'turnover_ratio' in result.columns:
                result['换手率'] = result['turnover_ratio']
            elif 'turnover' in result.columns:
                result['换手率'] = result['turnover']
            else:
                result['换手率'] = 0.0  # 默认值

        # 涨跌幅列统一
        if '涨跌幅' not in result.columns:
            if '涨幅' in result.columns:
                result['涨跌幅'] = result['涨幅']
            elif 'change_percent' in result.columns:
                result['涨跌幅'] = result['change_percent']

        # 最新价列统一
        if '最新价' not in result.columns:
            if 'current' in result.columns:
                result['最新价'] = result['current']
            elif 'price' in result.columns:
                result['最新价'] = result['price']

        return result

    def select(self, data: pd.DataFrame) -> pd.DataFrame:
        """执行选股策略"""
        if not self.validate_data(data):
            return pd.DataFrame()

        df = data.copy()

        # 0. 统一列名（确保量比、换手率等列存在）
        df = self._normalize_columns(df)

        # 1. 基础筛选
        df = self._filter_basic(df)

        # 2. 涨幅筛选
        df = self._filter_gain(df)

        # 3. 换手率筛选
        df = self._filter_turnover(df)

        # 4. 量比筛选
        df = self._filter_volume_ratio(df)

        # 5. 合并资金流
        df = self._merge_fund_flow(df)

        # 6. 主力流入筛选
        df = self._filter_main_inflow(df)

        # 7. 计算评分
        df = self.calculate_score(df)

        # 8. 按评分排序
        if not df.empty and 'score' in df.columns:
            df = df.sort_values('score', ascending=False)

        # 9. 返回前 N 只
        top_n = self.config.get('top_n', 20)
        return df.head(top_n)

    def _filter_basic(self, df: pd.DataFrame) -> pd.DataFrame:
        """基础条件筛选"""
        result = df.copy()

        # 排除 ST (使用 regex=True 修复正则表达式问题)
        if self.config.get('exclude_st', True) and '名称' in result.columns:
            result = result[~result['名称'].str.contains('ST', na=False, regex=False)]

        # 排除停牌 (成交量为 0)
        if '成交量' in result.columns:
            result = result[result['成交量'] > 0]

        return result

    def _filter_gain(self, df: pd.DataFrame) -> pd.DataFrame:
        """涨幅筛选"""
        result = df.copy()

        gain_col = self._find_column(result, ['涨跌幅', '涨幅', 'change_percent'])
        if gain_col:
            min_gain = self.config.get('min_gain', 3.0)
            max_gain = self.config.get('max_gain', 7.0)
            result = result[
                (result[gain_col] >= min_gain) &
                (result[gain_col] <= max_gain)
            ]

        return result

    def _filter_turnover(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        换手率筛选
        注意：如果换手率全为 0（数据源问题），则跳过此筛选
        """
        result = df.copy()

        turnover_col = self._find_column(result, ['换手率', 'turnover_ratio'])
        if turnover_col:
            # 检查换手率是否有有效数据
            non_zero = (result[turnover_col] != 0).sum()
            if non_zero < len(result) * 0.1:  # 少于 10% 有数据，跳过
                print(f"  换手率数据缺失 ({non_zero}/{len(result)})，跳过筛选")
                return result

            min_turnover = self.config.get('min_turnover', 5.0)
            max_turnover = self.config.get('max_turnover', 20.0)
            result = result[
                (result[turnover_col] >= min_turnover) &
                (result[turnover_col] <= max_turnover)
            ]

        return result

    def _filter_volume_ratio(self, df: pd.DataFrame) -> pd.DataFrame:
        """量比筛选 (新增上限，避免天量股)"""
        result = df.copy()

        vol_ratio_col = self._find_column(result, ['量比', 'volume_ratio'])
        if vol_ratio_col:
            min_ratio = self.config.get('min_volume_ratio', 1.8)
            max_ratio = self.config.get('max_volume_ratio', 15.0)  # 新增上限
            result = result[
                (result[vol_ratio_col] >= min_ratio) &
                (result[vol_ratio_col] <= max_ratio)
            ]

        return result

    def _merge_fund_flow(self, df: pd.DataFrame) -> pd.DataFrame:
        """合并资金流数据"""
        result = df.copy()

        if self.fund_flow_df is not None and not self.fund_flow_df.empty:
            try:
                merged = pd.merge(
                    result,
                    self.fund_flow_df[['代码', '主力净流入']],
                    on='代码',
                    how='left'
                )
                merged['主力净流入'] = merged['主力净流入'].fillna(0)
                merged['主力净流入 (万)'] = merged['主力净流入'] / 10000
                result = merged
            except Exception as e:
                print(f"合并资金流数据失败：{e}")

        return result

    def _filter_main_inflow(self, df: pd.DataFrame) -> pd.DataFrame:
        """主力净流入筛选"""
        result = df.copy()

        if '主力净流入 (万)' in result.columns:
            # 检查有多少股票有资金流数据
            non_zero = (result['主力净流入 (万)'] != 0).sum()
            total = len(result)

            # 如果大部分股票没有资金流数据，跳过筛选
            if non_zero >= total * 0.5:
                min_inflow = self.config.get('min_main_inflow', 500)
                result = result[result['主力净流入 (万)'] >= min_inflow]

        return result

    def calculate_score(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        综合评分系统 (高胜率优化版)
        满分 60 分

        评分项:
        - 涨幅评分：25 分 (越接近 5.5% 分越高，4%-7% 最佳)
        - 量比评分：15 分 (量比>2 才有分)
        - 换手率评分：20 分 (5%-12% 最佳)
        - 资金流入评分：20 分
        """
        result = df.copy()
        result['score'] = 0.0

        # 1. 涨幅评分 (越接近 5.5% 分越高，4%-7% 范围)
        gain_col = self._find_column(result, ['涨跌幅', '涨幅', 'change_percent'])
        if gain_col:
            # 最佳涨幅 5.5%, 偏离越大分越低
            result['gain_score'] = 25 - abs(result[gain_col] - 5.5) * 5
            result['gain_score'] = result['gain_score'].clip(0, 25)
            result['score'] += result['gain_score']

        # 2. 量比评分 (量比 2-8 最佳，过高惩罚)
        vol_ratio_col = self._find_column(result, ['量比', 'volume_ratio'])
        if vol_ratio_col:
            def calc_vol_score(x):
                if x < 2:
                    return 0
                elif 2 <= x <= 8:
                    # 2-8 倍量比得满分
                    return min(15, (x - 1) * 7.5)
                elif 8 < x <= 15:
                    # 8-15 倍逐渐减分
                    return 15 - (x - 8) * 1.5
                else:
                    # 超过 15 倍严重惩罚 (虽然已被筛选掉，但保留逻辑)
                    return max(0, 7.5 - (x - 15) * 0.5)

            result['vol_score'] = result[vol_ratio_col].apply(calc_vol_score)
            result['score'] += result['vol_score']

        # 3. 换手率评分 (5%-12% 最佳)
        turnover_col = self._find_column(result, ['换手率', 'turnover_ratio'])
        if turnover_col:
            # 最佳换手 8.5%, 偏离减分
            result['turnover_score'] = 20 - abs(result[turnover_col] - 8.5) * 2
            result['turnover_score'] = result['turnover_score'].clip(0, 20)
            result['score'] += result['turnover_score']

        # 4. 资金流入评分 (主力净流入>500 万才有分)
        if '主力净流入 (万)' in result.columns:
            # 500 万 -2000 万 线性评分
            result['inflow_score'] = result['主力净流入 (万)'].apply(
                lambda x: min(20, max(0, (x - 500) / 75)) if x > 500 else 0
            )
            result['inflow_score'] = result['inflow_score'].clip(0, 20)
            result['score'] += result['inflow_score']

        return result

    def _find_column(self, df: pd.DataFrame, options: List[str]) -> str:
        """查找列名"""
        for col in options:
            if col in df.columns:
                return col
        return None

    def get_required_columns(self) -> List[str]:
        """获取所需列名"""
        return ['代码', '名称', '涨跌幅', '量比', '换手率', '最新价']


# 兼容旧代码的别名
TailStockPicker = TailStockStrategy
