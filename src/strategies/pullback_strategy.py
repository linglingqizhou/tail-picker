# -*- coding: utf-8 -*-
"""
强势股回调策略
选股条件：
1. 前期（5 日内）涨幅超过 20%
2. 近期回调 5%-10%
3. 当前站上 5 日线
4. 量能萎缩后放大
"""

import pandas as pd
import numpy as np
from typing import Dict, List
from datetime import datetime, timedelta

from src.strategies.base import BaseStrategy


class PullbackStrategy(BaseStrategy):
    """强势股回调策略"""

    NAME = "强势股回调"
    DESCRIPTION = "前期强势上涨 + 近期回调 + 站上均线的反弹机会"

    DEFAULT_CONFIG = {
        # 前期涨幅条件
        'prev_gain_days': 5,         # 前期天数
        'min_prev_gain': 20.0,       # 最小额涨幅%

        # 回调条件
        'min_pullback': 5.0,         # 最小回调%
        'max_pullback': 15.0,        # 最大回调%

        # 均线条件
        'above_ma5': True,           # 站上 5 日线
        'ma5_trend_up': True,        # 5 日线向上

        # 量能条件
        'volume_shrink_ratio': 0.8,  # 缩量比例（相对于前期）
        'volume_expand_ratio': 1.2,  # 今日量能放大比例

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

        print(f"[{datetime.now().strftime('%H:%M:%S')}] 强势股回调策略：分析 {len(symbols)} 只股票...")

        for i, symbol in enumerate(symbols):
            try:
                # 获取历史 K 线
                hist = self.get_stock_history(symbol, days=30)
                if hist is None or len(hist) < 10:
                    continue

                # 计算各项指标
                stock_data = df[df['代码'] == symbol].iloc[0]
                pullback_info = self._calculate_pullback_metrics(hist, stock_data)

                if pullback_info and self._check_pullback_conditions(pullback_info):
                    pullback_info['代码'] = symbol
                    pullback_info['名称'] = stock_data.get('名称', '')
                    pullback_info['最新价'] = stock_data.get('最新价', 0)
                    pullback_info['current_price'] = stock_data.get('最新价', 0)
                    result_list.append(pullback_info)

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

    def _calculate_pullback_metrics(self, hist: pd.DataFrame, current_data: pd.Series) -> Dict:
        """
        计算回调相关指标

        Args:
            hist: 历史 K 线数据
            current_data: 当前行情数据

        Returns:
            dict: 回调指标
        """
        if len(hist) < 10:
            return None

        close = hist['收盘'].values

        # 当前价格
        current_price = close[-1]

        # 5 日线
        ma5 = close[-5:].mean()

        # 前期高点（5 日内最高）
        prev_days = self.config.get('prev_gain_days', 5)
        high_idx = len(close) - prev_days - 1 if len(close) > prev_days + 1 else 0
        prev_high = close[high_idx] if high_idx >= 0 else close[0]

        # 前期低点（N 日前）
        prev_low = close[high_idx - 5] if high_idx >= 5 else close[0]

        # 计算前期涨幅
        if prev_low > 0:
            prev_gain = ((prev_high - prev_low) / prev_low) * 100
        else:
            prev_gain = 0

        # 计算回调幅度
        if prev_high > 0:
            pullback = ((prev_high - current_price) / prev_high) * 100
        else:
            pullback = 0

        # 计算是否站上 5 日线
        above_ma5 = current_price > ma5

        # 计算 5 日线趋势
        ma5_today = close[-5:].mean()
        ma5_yesterday = close[-6:-1].mean() if len(close) >= 6 else ma5_today
        ma5_trend_up = ma5_today > ma5_yesterday

        # 量能分析
        volume = hist['成交量'].values
        today_vol = volume[-1]
        prev_avg_vol = volume[-prev_days-5:-5].mean() if len(volume) > prev_days + 5 else volume[:-1].mean()
        yesterday_vol = volume[-2] if len(volume) >= 2 else today_vol

        # 缩量后放量
        volume_shrink = yesterday_vol < prev_avg_vol * self.config.get('volume_shrink_ratio', 0.8) if len(volume) >= 2 else False
        volume_expand = today_vol > yesterday_vol * self.config.get('volume_expand_ratio', 1.2) if len(volume) >= 2 else False

        # 获取当前涨幅
        current_gain = current_data.get('涨跌幅', 0) if '涨跌幅' in current_data.index else 0

        return {
            'prev_gain': prev_gain,           # 前期涨幅
            'pullback': pullback,             # 回调幅度
            'above_ma5': above_ma5,           # 站上 5 日线
            'ma5_trend_up': ma5_trend_up,     # 5 日线向上
            'volume_shrink': volume_shrink,   # 前期缩量
            'volume_expand': volume_expand,   # 今日放量
            'current_gain': current_gain,     # 当前涨幅
            'ma5': ma5,                       # 5 日线价格
            'prev_high': prev_high,           # 前期高点
        }

    def _check_pullback_conditions(self, metrics: Dict) -> bool:
        """
        检查是否满足回调策略条件

        Args:
            metrics: 回调指标字典

        Returns:
            bool: 是否满足条件
        """
        # 1. 前期涨幅超过 20%
        min_prev_gain = self.config.get('min_prev_gain', 20.0)
        if metrics['prev_gain'] < min_prev_gain:
            return False

        # 2. 近期回调 5%-15%
        min_pullback = self.config.get('min_pullback', 5.0)
        max_pullback = self.config.get('max_pullback', 15.0)
        if not (min_pullback <= metrics['pullback'] <= max_pullback):
            return False

        # 3. 站上 5 日线
        if self.config.get('above_ma5', True) and not metrics['above_ma5']:
            return False

        # 4. 5 日线向上
        if self.config.get('ma5_trend_up', True) and not metrics['ma5_trend_up']:
            return False

        # 5. 量能条件（至少满足其一）
        if not (metrics['volume_expand'] or metrics['current_gain'] > 3):
            return False

        return True

    def calculate_score(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        综合评分系统
        满分 100 分

        评分项:
        - 前期强势度：25 分（前期涨幅）
        - 回调深度：25 分（黄金回调位）
        - 均线支撑：20 分
        - 量能配合：20 分
        - 当前动能：10 分
        """
        result = df.copy()
        result['score'] = 0.0

        # 1. 前期强势度（前期涨幅越大分越高）
        prev_gain_scores = []
        for _, row in result.iterrows():
            prev_gain = row.get('prev_gain', 0)
            # 20%-50% 最佳
            if 20 <= prev_gain <= 50:
                score = 25
            elif prev_gain > 50:
                score = 20  # 涨幅过大可能回调风险高
            else:
                score = max(0, prev_gain)  # 不足 20% 按比例
            prev_gain_scores.append(score)
        result['prev_gain_score'] = prev_gain_scores
        result['score'] += result['prev_gain_score']

        # 2. 回调深度（5%-10% 最佳）
        pullback_scores = []
        for _, row in result.iterrows():
            pullback = row.get('pullback', 0)
            if 5 <= pullback <= 10:
                score = 25
            elif 10 < pullback <= 15:
                score = 20
            elif pullback < 5:
                score = 15
            else:
                score = 10
            pullback_scores.append(score)
        result['pullback_score'] = pullback_scores
        result['score'] += result['pullback_score']

        # 3. 均线支撑
        ma_scores = []
        for _, row in result.iterrows():
            score = 0
            if row.get('above_ma5', False):
                score += 10
            if row.get('ma5_trend_up', False):
                score += 10
            ma_scores.append(score)
        result['ma_score'] = ma_scores
        result['score'] += result['ma_score']

        # 4. 量能配合
        volume_scores = []
        for _, row in result.iterrows():
            score = 0
            if row.get('volume_shrink', False):
                score += 10
            if row.get('volume_expand', False):
                score += 10
            volume_scores.append(score)
        result['volume_score'] = volume_scores
        result['score'] += result['volume_score']

        # 5. 当前动能
        result['momentum_score'] = result['current_gain'].apply(lambda x: min(10, max(0, x)))
        result['score'] += result['momentum_score']

        return result

    def get_required_columns(self) -> List[str]:
        """获取所需列名"""
        return ['代码', '名称', '最新价', '涨跌幅', '成交量']
