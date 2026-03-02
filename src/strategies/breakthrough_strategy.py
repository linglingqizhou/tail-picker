# -*- coding: utf-8 -*-
"""
突破策略
选股条件：
1. 突破 N 日（20/60）新高
2. 成交量放大 2 倍以上
3. 当日涨幅>5%
4. 平台整理至少 5 日
"""

import pandas as pd
import numpy as np
from typing import Dict, List
from datetime import datetime, timedelta

from src.strategies.base import BaseStrategy


class BreakthroughStrategy(BaseStrategy):
    """突破策略"""

    NAME = "突破"
    DESCRIPTION = "突破平台新高 + 放量 + 强势上涨的突破机会"

    DEFAULT_CONFIG = {
        # 突破条件
        'breakthrough_days': 20,       # 突破 N 日新高（可选 20/60）
        'min_breakthrough_gain': 0.0,  # 最小突破幅度%（超过新高多少）

        # 量能条件
        'min_volume_ratio': 2.0,       # 最小量比（相对于前期平均）

        # 涨幅条件
        'min_daily_gain': 5.0,         # 最小当日涨幅%

        # 平台整理条件
        'min_consolidation_days': 5,   # 最小整理天数
        'consolidation_range': 0.15,   # 整理区间幅度（最高 - 最低）/ 最高

        # 排除条件
        'exclude_st': True,
        'min_days_listed': 60,

        # 选股数量
        'top_n': 20,
    }

    def select(self, data: pd.DataFrame) -> pd.DataFrame:
        """执行选股策略"""
        if not self.validate_data(data):
            return pd.DataFrame()

        df = data.copy()

        # 1. 基础筛选
        df = self._filter_basic(df)
        if df.empty:
            return df

        # 2. 获取历史数据并计算指标
        result_list = []
        symbols = df['代码'].tolist() if '代码' in df.columns else []

        print(f"[{datetime.now().strftime('%H:%M:%S')}] 突破策略：分析 {len(symbols)} 只股票...")

        for i, symbol in enumerate(symbols):
            try:
                # 获取历史 K 线
                hist = self.get_stock_history(symbol, days=90)
                if hist is None or len(hist) < 60:
                    continue

                # 计算各项指标
                stock_data = df[df['代码'] == symbol].iloc[0]
                breakthrough_info = self._calculate_breakthrough_metrics(hist, stock_data)

                if breakthrough_info and self._check_breakthrough_conditions(breakthrough_info):
                    breakthrough_info['代码'] = symbol
                    breakthrough_info['名称'] = stock_data.get('名称', '')
                    breakthrough_info['最新价'] = stock_data.get('最新价', 0)
                    breakthrough_info['current_price'] = stock_data.get('最新价', 0)
                    result_list.append(breakthrough_info)

            except Exception as e:
                continue

            if (i + 1) % 20 == 0:
                print(f"  进度：{i+1}/{len(symbols)}")

        if not result_list:
            return pd.DataFrame()

        result_df = pd.DataFrame(result_list)

        # 3. 计算评分
        result_df = self.calculate_score(result_df)

        # 4. 按评分排序
        result_df = result_df.sort_values('score', ascending=False)

        # 5. 返回前 N 只
        top_n = self.config.get('top_n', 20)
        return result_df.head(top_n)

    def _filter_basic(self, df: pd.DataFrame) -> pd.DataFrame:
        """基础筛选"""
        result = df.copy()

        # 排除 ST
        if self.config.get('exclude_st', True) and '名称' in result.columns:
            result = result[~result['名称'].str.contains('ST', na=False, regex=False)]

        # 排除停牌
        if '成交量' in result.columns:
            result = result[result['成交量'] > 0]

        return result

    def _calculate_breakthrough_metrics(self, hist: pd.DataFrame, current_data: pd.Series) -> Dict:
        """
        计算突破相关指标

        Args:
            hist: 历史 K 线数据
            current_data: 当前行情数据

        Returns:
            dict: 突破指标
        """
        if len(hist) < 60:
            return None

        close = hist['收盘'].values
        high = hist['最高'].values
        low = hist['最低'].values
        volume = hist['成交量'].values

        # 当前价格
        current_price = close[-1]

        # N 日新高
        n_days = self.config.get('breakthrough_days', 20)
        prev_n_high = high[-n_days-1:-1].max() if len(high) > n_days else high[:-1].max()

        # 突破幅度
        if prev_n_high > 0:
            breakthrough_gain = ((current_price - prev_n_high) / prev_n_high) * 100
        else:
            breakthrough_gain = 0

        # 是否创新高
        is_new_high = current_price > prev_n_high

        # 平台整理分析
        consolidation_days = self.config.get('min_consolidation_days', 5)
        if len(close) > consolidation_days + 1:
            # 整理区间（突破前 N 天）
            consolidation_high = high[-consolidation_days-1:-1].max()
            consolidation_low = low[-consolidation_days-1:-1].min()
            consolidation_range = (consolidation_high - consolidation_low) / consolidation_high if consolidation_high > 0 else 0
        else:
            consolidation_range = 0

        # 平台整理判断
        is_consolidation = consolidation_range < self.config.get('consolidation_range', 0.15)

        # 量能分析
        # 前期平均成交量
        prev_avg_vol = volume[-consolidation_days-5:-5].mean() if len(volume) > consolidation_days + 5 else volume[:-1].mean()
        today_vol = volume[-1]

        # 量比
        volume_ratio = today_vol / prev_avg_vol if prev_avg_vol > 0 else 0

        # 是否放量
        is_volume_expand = volume_ratio >= self.config.get('min_volume_ratio', 2.0)

        # 当日涨幅
        current_gain = current_data.get('涨跌幅', 0) if '涨跌幅' in current_data.index else 0

        # 是否满足最小涨幅
        is_strong_gain = current_gain >= self.config.get('min_daily_gain', 5.0)

        return {
            'breakthrough_days': n_days,         # 突破 N 日
            'prev_n_high': prev_n_high,          # N 日前高点
            'breakthrough_gain': breakthrough_gain,  # 突破幅度
            'is_new_high': is_new_high,          # 是否创新高
            'consolidation_range': consolidation_range,  # 整理区间
            'is_consolidation': is_consolidation,  # 是否平台整理
            'volume_ratio': volume_ratio,        # 量比
            'is_volume_expand': is_volume_expand,  # 是否放量
            'current_gain': current_gain,        # 当前涨幅
            'is_strong_gain': is_strong_gain,    # 是否强势上涨
        }

    def _check_breakthrough_conditions(self, metrics: Dict) -> bool:
        """
        检查是否满足突破策略条件

        Args:
            metrics: 突破指标字典

        Returns:
            bool: 是否满足条件
        """
        # 1. 突破 N 日新高
        if not metrics['is_new_high']:
            return False

        # 2. 成交量放大 2 倍以上
        if not metrics['is_volume_expand']:
            return False

        # 3. 当日涨幅>5%
        if not metrics['is_strong_gain']:
            return False

        # 4. 平台整理
        if self.config.get('min_consolidation_days', 5) > 0:
            if not metrics['is_consolidation']:
                return False

        return True

    def calculate_score(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        综合评分系统
        满分 100 分

        评分项:
        - 突破强度：30 分（突破幅度、是否新高）
        - 量能配合：25 分（量比）
        - 平台整理：20 分（整理时间、区间）
        - 涨幅强度：15 分
        - 趋势强度：10 分
        """
        result = df.copy()
        result['score'] = 0.0

        # 1. 突破强度（30 分）
        breakthrough_scores = []
        for _, row in result.iterrows():
            score = 0
            if row.get('is_new_high', False):
                score += 15
            # 突破幅度越大分越高
            breakthrough_gain = row.get('breakthrough_gain', 0)
            score += min(15, breakthrough_gain * 3)  # 每突破 1% 得 3 分
            breakthrough_scores.append(score)
        result['breakthrough_score'] = breakthrough_scores
        result['score'] += result['breakthrough_score']

        # 2. 量能配合（25 分）
        volume_scores = []
        for _, row in result.iterrows():
            volume_ratio = row.get('volume_ratio', 0)
            # 量比 2 倍以上满分
            score = min(25, volume_ratio * 12.5)
            volume_scores.append(score)
        result['volume_score'] = volume_scores
        result['score'] += result['volume_score']

        # 3. 平台整理（20 分）
        consolidation_scores = []
        for _, row in result.iterrows():
            score = 0
            if row.get('is_consolidation', False):
                score += 10
            # 整理区间越小分越高
            cr = row.get('consolidation_range', 0.15)
            score += max(0, 10 - cr * 50)
            consolidation_scores.append(score)
        result['consolidation_score'] = consolidation_scores
        result['score'] += result['consolidation_score']

        # 4. 涨幅强度（15 分）
        gain_scores = []
        for _, row in result.iterrows():
            current_gain = row.get('current_gain', 0)
            # 涨幅越大分越高，上限 15 分
            score = min(15, current_gain * 1.5)
            gain_scores.append(score)
        result['gain_score'] = gain_scores
        result['score'] += result['gain_score']

        # 5. 趋势强度（10 分）
        # 简化：使用突破天数作为趋势强度指标
        result['trend_score'] = 10  # 通过筛选的都是趋势良好的
        result['score'] += result['trend_score']

        return result

    def get_required_columns(self) -> List[str]:
        """获取所需列名"""
        return ['代码', '名称', '最新价', '涨跌幅', '成交量']
