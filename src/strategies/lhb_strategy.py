# -*- coding: utf-8 -*-
"""
龙虎榜策略
选股条件：
1. 近 3 日登上龙虎榜
2. 机构席位净买入
3. 游资席位活跃
"""

import pandas as pd
import numpy as np
from typing import Dict, List
from datetime import datetime, timedelta

from src.strategies.base import BaseStrategy


class LHBStrategy(BaseStrategy):
    """龙虎榜策略"""

    NAME = "龙虎榜"
    DESCRIPTION = "基于龙虎榜数据的机构席位和游资动向选股"

    DEFAULT_CONFIG = {
        # 龙虎榜条件
        'lookback_days': 3,          # 回溯天数
        'min_institution_net_buy': 0,  # 最小机构净买入（万元）

        # 游资条件
        'active_trader_days': 2,     # 游资活跃天数
        'min_trader_turnover': 1000,  # 最小游资成交额（万元）

        # 营业部条件
        'top_seats_count': 5,        # 关注前 N 大营业部

        # 排除条件
        'exclude_st': True,

        # 选股数量
        'top_n': 20,
    }

    def __init__(self, config: Dict = None):
        super().__init__(config)
        self.lhb_cache = {}  # 龙虎榜数据缓存

    def select(self, data: pd.DataFrame) -> pd.DataFrame:
        """执行选股策略"""
        if not self.validate_data(data):
            return pd.DataFrame()

        df = data.copy()

        # 1. 基础筛选
        df = self._filter_basic(df)
        if df.empty:
            return df

        # 2. 获取龙虎榜数据
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 龙虎榜策略：获取龙虎榜数据...")
        lhb_stocks = self._get_lhb_stocks()

        if not lhb_stocks:
            print("  未获取到龙虎榜数据")
            return pd.DataFrame()

        print(f"  近 {self.config.get('lookback_days', 3)} 日龙虎榜股票：{len(lhb_stocks)} 只")

        # 3. 筛选在龙虎榜中的股票
        symbols = df['代码'].tolist() if '代码' in df.columns else []
        result_list = []

        print(f"[{datetime.now().strftime('%H:%M:%S')}] 分析龙虎榜股票...")

        for i, symbol in enumerate(symbols):
            if symbol not in lhb_stocks:
                continue

            try:
                stock_data = df[df['代码'] == symbol].iloc[0]
                lhb_info = lhb_stocks[symbol]

                # 检查是否满足条件
                if self._check_lhb_conditions(lhb_info):
                    info = {
                        '代码': symbol,
                        '名称': stock_data.get('名称', ''),
                        '最新价': stock_data.get('最新价', 0),
                        'current_price': stock_data.get('最新价', 0),
                        '涨跌幅': stock_data.get('涨跌幅', 0),
                    }
                    # 合并龙虎榜信息
                    info.update(lhb_info)
                    result_list.append(info)

            except Exception as e:
                continue

        if not result_list:
            return pd.DataFrame()

        result_df = pd.DataFrame(result_list)

        # 4. 计算评分
        result_df = self.calculate_score(result_df)

        # 5. 按评分排序
        result_df = result_df.sort_values('score', ascending=False)

        # 6. 返回前 N 只
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

    def _get_lhb_stocks(self) -> Dict:
        """
        获取近 N 日龙虎榜股票及其详细信息

        Returns:
            dict: {股票代码：龙虎榜信息}
        """
        from src.akshare_api import get_lhb_today, get_lhb_detail

        result = {}
        lookback_days = self.config.get('lookback_days', 3)

        # 获取今日龙虎榜
        try:
            today_lhb = get_lhb_today()
            if today_lhb is not None and not today_lhb.empty:
                for _, row in today_lhb.iterrows():
                    symbol = str(row.get('代码', ''))
                    if symbol and len(symbol) >= 6:
                        symbol = symbol[-6:]  # 取后 6 位
                        result[symbol] = self._parse_lhb_row(row, date_offset=0)
        except Exception as e:
            print(f"  获取今日龙虎榜失败：{e}")

        # 获取前几日龙虎榜（从缓存或 API）
        for i in range(1, lookback_days):
            try:
                date = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
                # 周末跳过
                if (datetime.now() - timedelta(days=i)).weekday() >= 5:
                    continue

                detail = get_lhb_detail(date)
                if detail is not None and not detail.empty:
                    for _, row in detail.iterrows():
                        symbol = str(row.get('代码', ''))
                        if symbol and len(symbol) >= 6:
                            symbol = symbol[-6:]
                            if symbol not in result:
                                result[symbol] = self._parse_lhb_row(row, date_offset=i)
                            else:
                                # 累加机构净买入
                                result[symbol]['institution_net_buy'] = \
                                    result[symbol].get('institution_net_buy', 0) + \
                                    self._parse_lhb_row(row, date_offset=i).get('institution_net_buy', 0)
            except Exception as e:
                continue

        return result

    def _parse_lhb_row(self, row: pd.Series, date_offset: int = 0) -> Dict:
        """
        解析龙虎榜数据行

        Args:
            row: 龙虎榜数据行
            date_offset: 日期偏移（0=今日）

        Returns:
            dict: 解析后的信息
        """
        info = {
            'lhb_date_offset': date_offset,
            'lhb_reason': row.get('上榜原因', ''),
            'close_change': row.get('收盘价涨跌幅', 0),
            'turnover': row.get('成交额', 0),
            'institution_net_buy': 0,
            'trader_seats': [],
            'is_institution_buy': False,
            'is_trader_active': False,
        }

        # 尝试获取机构席位数据
        try:
            # 不同 API 返回格式不同，尝试多种字段
            inst_buy = row.get('机构净买入', 0) or row.get('机构买入净额', 0) or 0
            inst_sell = row.get('机构净卖出', 0) or row.get('机构卖出净额', 0) or 0
            info['institution_net_buy'] = float(inst_buy) - float(inst_sell) if inst_buy or inst_sell else 0
            info['is_institution_buy'] = info['institution_net_buy'] > 0
        except:
            pass

        # 游资席位（营业部）
        try:
            for i in range(1, 6):
                seat_name = row.get(f'买入第{i}名营业部', '') or row.get(f'买一营业部', '')
                if seat_name:
                    info['trader_seats'].append({
                        'name': seat_name,
                        'amount': row.get(f'买入第{i}名金额', 0) or 0
                    })
            info['is_trader_active'] = len(info['trader_seats']) >= 1
        except:
            pass

        return info

    def _check_lhb_conditions(self, lhb_info: Dict) -> bool:
        """
        检查是否满足龙虎榜策略条件

        Args:
            lhb_info: 龙虎榜信息

        Returns:
            bool: 是否满足条件
        """
        # 1. 机构席位净买入
        min_inst_buy = self.config.get('min_institution_net_buy', 0)
        if lhb_info.get('institution_net_buy', 0) < min_inst_buy:
            # 如果没有机构数据，但有游资活跃也可以
            if not lhb_info.get('is_trader_active', False):
                return False

        # 2. 游资席位活跃（可选条件）
        # 如果配置要求游资活跃，则检查
        if self.config.get('require_trader_active', False):
            if not lhb_info.get('is_trader_active', False):
                return False

        return True

    def calculate_score(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        综合评分系统
        满分 100 分

        评分项:
        - 机构买入：40 分
        - 游资活跃度：25 分
        - 上榜原因：15 分
        - 成交额：10 分
        - 当日表现：10 分
        """
        result = df.copy()
        result['score'] = 0.0

        # 1. 机构买入评分（40 分）
        inst_scores = []
        for _, row in result.iterrows():
            inst_buy = row.get('institution_net_buy', 0)
            # 净买入越大分越高
            if inst_buy > 0:
                score = min(40, 20 + inst_buy / 100)  # 每 100 万加 1 分
            else:
                score = max(0, 20 + inst_buy / 100)
            inst_scores.append(score)
        result['institution_score'] = inst_scores
        result['score'] += result['institution_score']

        # 2. 游资活跃度（25 分）
        trader_scores = []
        for _, row in result.iterrows():
            score = 0
            if row.get('is_trader_active', False):
                score += 15
            # 营业部数量越多分越高
            trader_count = len(row.get('trader_seats', []))
            score += min(10, trader_count * 2)
            trader_scores.append(score)
        result['trader_score'] = trader_scores
        result['score'] += result['trader_score']

        # 3. 上榜原因（15 分）
        reason_scores = []
        for _, row in result.iterrows():
            reason = row.get('lhb_reason', '')
            score = 5  # 基础分
            # 根据上榜原因加分
            if '涨幅' in reason or '涨停' in reason:
                score += 5
            if '换手' in reason or '放量' in reason:
                score += 3
            if '创新高' in reason:
                score += 2
            reason_scores.append(score)
        result['reason_score'] = reason_scores
        result['score'] += result['reason_score']

        # 4. 成交额（10 分）
        turnover_scores = []
        for _, row in result.iterrows():
            turnover = row.get('turnover', 0)
            # 成交额越大分越高
            score = min(10, np.log1p(turnover) / 10 * 10) if turnover > 0 else 5
            turnover_scores.append(score)
        result['turnover_score'] = turnover_scores
        result['score'] += result['turnover_score']

        # 5. 当日表现（10 分）
        result['performance_score'] = result['涨跌幅'].apply(lambda x: min(10, max(0, x + 5)))
        result['score'] += result['performance_score']

        return result

    def get_required_columns(self) -> List[str]:
        """获取所需列名"""
        return ['代码', '名称', '最新价', '涨跌幅']
