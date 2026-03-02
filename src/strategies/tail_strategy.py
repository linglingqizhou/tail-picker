# -*- coding: utf-8 -*-
"""
尾盘选股策略 (增强版)
基于传统一夜持股法，综合涨幅、量比、换手率、资金流、题材热度等多维度选股
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from datetime import datetime

from src.strategies.base import BaseStrategy


class TailStockStrategy(BaseStrategy):
    """尾盘选股策略 (增强版)"""

    NAME = "尾盘选股 (增强版)"
    DESCRIPTION = "基于涨幅、量比、换手率、资金流、题材热度的综合评分策略"

    DEFAULT_CONFIG = {
        # 涨幅条件 (涨停命中率优化：4%-8.5% 最佳区间)
        'min_gain': 4.0,      # 最小涨幅%
        'max_gain': 8.5,      # 最大涨幅%

        # 量能条件 (量比 2-12 最佳区间)
        'min_volume_ratio': 2.0,
        'max_volume_ratio': 12.0,
        'min_turnover': 5.0,      # 最小换手率%
        'max_turnover': 15.0,     # 最大换手率%

        # 资金条件
        'min_main_inflow': 800,   # 最小主力净流入 (万元)

        # 市值条件
        'max_market_cap': 500,    # 最大流通市值 (亿)

        # 排除条件
        'exclude_st': True,       # 排除 ST
        'min_days_listed': 60,    # 最小上市天数
        'above_ma5': True,        # 必须站上 5 日线

        # 选股数量
        'top_n': 10,

        # 题材配置
        'use_theme_score': True,   # 是否启用题材评分
        'theme_weight': 0.3,       # 题材评分权重 (30%)
    }

    # 题材 - 成分股映射 (用于判断股票所属题材)
    THEME_COMPONENTS = {
        "人工智能": ["600519", "002594", "601360", "300750", "002230", "600845", "600570", "300059"],
        "芯片半导体": ["603986", "600584", "002371", "603019", "002156", "600460", "300623", "688981"],
        "新能源": ["300750", "002594", "002812", "601012", "600438", "002460", "603799", "300014"],
        "光伏": ["601012", "600438", "002460", "603799", "002056", "002865", "300316", "600732"],
        "锂电": ["300750", "002812", "603799", "002460", "002340", "300073", "603659", "002756"],
        "AI 算力": ["601360", "000977", "600498", "000066", "300394", "002897", "300502", "603019"],
        "5G": ["600498", "000066", "002594", "300394", "002897", "603220", "300628", "002796"],
        "机器人": ["002747", "002230", "300024", "002698", "603666", "300170", "600666", "002896"],
        "低空经济": ["000099", "002111", "600038", "600765", "002465", "300397", "603666", "002190"],
        "华为概念": ["002594", "300750", "002456", "002230", "600745", "000725", "600584", "300136"],
        "白酒": ["600519", "000858", "000568", "000799", "600809", "000596", "600779", "000860"],
        "券商": ["600030", "601688", "600837", "000776", "600028", "601318", "601398", "601901"],
        "医药": ["600276", "000538", "000661", "600085", "600436", "002317", "300122", "600521"],
        "煤炭": ["600546", "601088", "600188", "600737", "002128", "601699", "600348", "600997"],
        "化工": ["600309", "600028", "600546", "002128", "600988", "000426", "600489", "600331", "600075", "600470", "600152"],
        "电力": ["600098", "600795", "600642", "600578", "600131", "600886", "000027", "600011"],
        "建材": ["600585", "600801", "600449", "000401", "000789", "600720", "600668", "600219"],
        "稀土有色": ["600111", "000897", "600259", "000603", "600392", "600117", "600490", "002645", "600331"],
        "钢铁": ["600519", "000898", "000709", "600019", "000778", "600282", "600307", "002110", "600219"],
    }

    # 热门板块 (动态更新，这里放默认的)
    HOT_THEMES = ["AI 算力", "5G", "芯片半导体", "新能源", "低空经济", "华为概念", "化工", "电力", "稀土有色"]

    def __init__(self, config: Dict = None):
        super().__init__(config)
        self.fund_flow_df = None
        self.theme_heat_cache = {}  # 板块热度缓存
        self.dynamic_components = {}  # 动态成分股映射 (从实时数据获取)

    def set_fund_flow_data(self, df: pd.DataFrame):
        """设置资金流数据"""
        self.fund_flow_df = df

    def set_theme_heat(self, theme_heat_dict: Dict):
        """
        设置板块热度数据

        Args:
            theme_heat_dict: dict, 如 {"AI 算力": 85, "5G": 72, ...}
        """
        self.theme_heat_cache = theme_heat_dict

    def set_dynamic_components(self, components_dict: Dict):
        """
        设置动态成分股数据 (从实时数据获取)

        Args:
            components_dict: dict, 如 {"人工智能": ["600519", "002594", ...], ...}
        """
        self.dynamic_components = components_dict
        # 动态更新热门板块
        self.HOT_THEMES = list(components_dict.keys())

    def get_stock_themes(self, code: str) -> List[str]:
        """
        获取股票所属题材

        Args:
            code: 股票代码

        Returns:
            List[str]: 题材列表
        """
        themes = []

        # 先查动态成分股 (实时数据)
        for theme_name, components in self.dynamic_components.items():
            if code in components:
                themes.append(theme_name)

        # 再查静态成分股 (本地缓存)
        if not themes:
            for theme_name, components in self.THEME_COMPONENTS.items():
                if code in components:
                    themes.append(theme_name)

        return themes

    def calculate_theme_score(self, code: str) -> float:
        """
        计算个股的题材评分 (0-30 分)

        评分逻辑:
        - 有题材：基础分 15 分
        - 属于热门板块：+5 分/每个
        - 板块热度高：额外 +10 分 (根据 theme_heat_cache)
        - 属于多个题材：额外 +5 分 (概念叠加)

        Args:
            code: 股票代码

        Returns:
            float: 题材评分
        """
        if not self.config.get('use_theme_score', True):
            return 0.0

        stock_themes = self.get_stock_themes(code)
        if not stock_themes:
            return 10.0  # 无题材，基础分 10 分

        score = 15.0  # 有题材，基础分 15 分

        # 检查是否属于热门板块
        hot_count = 0
        max_theme_heat = 0

        for theme in stock_themes:
            # 属于热门板块
            if theme in self.HOT_THEMES:
                hot_count += 1
            # 板块热度评分 (从缓存获取)
            theme_heat = self.theme_heat_cache.get(theme, 50)
            max_theme_heat = max(max_theme_heat, theme_heat)

        # 热门板块加分
        if hot_count > 0:
            score += 5 * hot_count  # 每个热门板块 +5 分

        # 板块热度高额外加分
        if max_theme_heat >= 70:
            score += 5  # 热度>=70 加分
        if max_theme_heat >= 85:
            score += 5  # 热度>=85 再加分

        # 概念叠加加分
        if len(stock_themes) >= 2:
            score += 5  # 属于 2 个以上题材加分

        return min(30.0, score)  # 最高 30 分

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
        综合评分系统 (增强版 - 技术面 + 题材面)
        满分 100 分

        评分项:
        - 技术面评分 (70 分)
          - 涨幅评分：25 分
          - 量比评分：15 分
          - 换手率评分：20 分
          - 资金流入评分：10 分
        - 题材面评分 (30 分)
          - 所属热门题材：20 分
          - 概念叠加：10 分
        """
        result = df.copy()
        result['score'] = 0.0

        # === 技术面评分 (70 分) ===

        # 1. 涨幅评分 (25 分)
        gain_col = self._find_column(result, ['涨跌幅', '涨幅', 'change_percent'])
        if gain_col:
            result['gain_score'] = 25 - abs(result[gain_col] - 5.5) * 5
            result['gain_score'] = result['gain_score'].clip(0, 25)
            result['score'] += result['gain_score']

        # 2. 量比评分 (15 分)
        vol_ratio_col = self._find_column(result, ['量比', 'volume_ratio'])
        if vol_ratio_col:
            def calc_vol_score(x):
                if x < 2:
                    return 0
                elif 2 <= x <= 8:
                    return min(15, (x - 1) * 7.5)
                elif 8 < x <= 15:
                    return 15 - (x - 8) * 1.5
                else:
                    return max(0, 7.5 - (x - 15) * 0.5)
            result['vol_score'] = result[vol_ratio_col].apply(calc_vol_score)
            result['score'] += result['vol_score']

        # 3. 换手率评分 (20 分)
        turnover_col = self._find_column(result, ['换手率', 'turnover_ratio'])
        if turnover_col:
            result['turnover_score'] = 20 - abs(result[turnover_col] - 8.5) * 2
            result['turnover_score'] = result['turnover_score'].clip(0, 20)
            result['score'] += result['turnover_score']

        # 4. 资金流入评分 (10 分)
        if '主力净流入 (万)' in result.columns:
            result['inflow_score'] = result['主力净流入 (万)'].apply(
                lambda x: min(10, max(0, (x - 500) / 150)) if x > 500 else 0
            )
            result['inflow_score'] = result['inflow_score'].clip(0, 10)
            result['score'] += result['inflow_score']

        # === 题材面评分 (30 分) ===
        if self.config.get('use_theme_score', True):
            # 计算每只股票的题材评分
            result['theme_score'] = result['代码'].apply(
                lambda x: self.calculate_theme_score(str(x).zfill(6))
            )
            result['score'] += result['theme_score']

            # 显示股票所属题材
            result['所属题材'] = result['代码'].apply(
                lambda x: ', '.join(self.get_stock_themes(str(x).zfill(6))) or '无'
            )

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
