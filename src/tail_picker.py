# -*- coding: utf-8 -*-
"""
尾盘选股器 - 核心选股策略模块
实现一夜持股法、强势股回调、突破等多种选股策略
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 设置 UTF-8 编码环境变量（Windows）
os.environ['PYTHONIOENCODING'] = 'utf-8'

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import time

from src.akshare_api import get_all_stocks_realtime, get_individual_fund_flow, get_stock_history
from src.sina_api import SinaStockAPI
import akshare as ak


class TailStockPicker:
    """尾盘选股器"""

    # 默认筛选条件
    DEFAULT_CONFIG = {
        # 涨幅条件
        'min_gain': 3.0,      # 最小涨幅%
        'max_gain': 7.0,      # 最大涨幅%

        # 量能条件
        'min_volume_ratio': 1.5,  # 最小额比
        'min_turnover': 5.0,      # 最小换手率%
        'max_turnover': 20.0,     # 最大换手率%

        # 资金条件
        'min_main_inflow': 500,   # 最小主力净流入 (万元)

        # 市值条件
        'max_market_cap': 500,    # 最大流通市值 (亿)

        # 技术条件
        'above_ma5': True,        # 站上 5 日线
        'above_ma20': False,      # 站上 20 日线

        # 排除条件
        'exclude_st': True,       # 排除 ST
        'exclude_new': False,     # 排除新股 (上市<30 日)
        'min_days_listed': 60,    # 最小上市天数

        # 选股数量
        'top_n': 20,              # 返回前 N 只
    }

    def __init__(self, config: Dict = None):
        self.config = self.DEFAULT_CONFIG.copy()
        if config:
            self.config.update(config)

        self.all_stocks_df = None
        self.fund_flow_df = None
        self.sina_api = SinaStockAPI()

    def fetch_all_data(self, use_cache: bool = True) -> bool:
        """
        获取全部基础数据

        Args:
            use_cache: 是否使用缓存数据（如果存在）
        """
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 获取全部 A 股行情...")

        # 重试机制，最多重试 3 次
        max_retries = 3
        for i in range(max_retries):
            try:
                # 优先尝试 AkShare
                self.all_stocks_df = get_all_stocks_realtime()
                if self.all_stocks_df is not None and not self.all_stocks_df.empty:
                    break
            except Exception as e:
                if i < max_retries - 1:
                    print(f"获取失败，重试 {i+2}/{max_retries}... (等待 2 秒)")
                    time.sleep(2)
                else:
                    print("AkShare 获取失败，尝试加载本地缓存...")
                    # 尝试加载缓存
                    cache_file = self._get_cache_file()
                    if use_cache and cache_file.exists():
                        print(f"加载缓存数据：{cache_file}")
                        self.all_stocks_df = pd.read_csv(cache_file, encoding='utf-8-sig')
                        if not self.all_stocks_df.empty:
                            print(f"缓存数据加载成功，共 {len(self.all_stocks_df)} 只股票")
                            return True
                    return False

        if self.all_stocks_df is None or self.all_stocks_df.empty:
            # 尝试加载缓存
            cache_file = self._get_cache_file()
            if use_cache and cache_file.exists():
                print(f"加载缓存数据：{cache_file}")
                self.all_stocks_df = pd.read_csv(cache_file, encoding='utf-8-sig')
                return True
            print("获取行情失败！")
            return False

        # 获取资金流向（带缓存）
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 获取资金流向数据...")
        try:
            self.fund_flow_df = self._get_fund_flow_with_cache()
        except Exception as e:
            print(f"获取资金流向失败：{e}")
            self.fund_flow_df = None

        print(f"获取成功，共 {len(self.all_stocks_df)} 只股票")

        # 统一列名格式（处理不同数据源的列名差异）
        self._normalize_columns()

        # 保存缓存
        self._save_cache()

        return True

    def _get_cache_file(self):
        """获取缓存文件路径"""
        from pathlib import Path
        cache_dir = Path(__file__).parent.parent / "stock_data" / "cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        return cache_dir / "stocks_cache.csv"

    def _get_fund_flow_cache_file(self):
        """获取资金流缓存文件路径"""
        from pathlib import Path
        cache_dir = Path(__file__).parent.parent / "stock_data" / "cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        return cache_dir / "fund_flow_cache.csv"

    def _get_fund_flow_with_cache(self) -> pd.DataFrame:
        """获取资金流数据（带缓存）"""
        from pathlib import Path
        import os

        cache_file = self._get_fund_flow_cache_file()
        cache_max_age = 3600  # 缓存有效期 1 小时

        # 检查缓存是否存在且未过期
        if cache_file.exists():
            try:
                cache_time = datetime.fromtimestamp(cache_file.stat().st_mtime)
                age_seconds = (datetime.now() - cache_time).total_seconds()

                if age_seconds < cache_max_age:
                    print(f"  使用资金流缓存数据（{int(age_seconds/60)} 分钟前）")
                    df = pd.read_csv(cache_file, encoding='utf-8-sig')
                    if df is not None and not df.empty:
                        return df
            except Exception:
                pass  # 缓存读取失败，重新获取

        # 获取新数据
        print("  获取最新资金流向数据...")
        df = get_individual_fund_flow()

        if df is not None and not df.empty:
            # 保存缓存
            try:
                df.to_csv(cache_file, index=False, encoding='utf-8-sig')
            except Exception:
                pass  # 忽略缓存保存错误
            return df

        # 获取失败时，尝试使用过期缓存
        if cache_file.exists():
            try:
                print("  使用过期资金流缓存数据（最后手段）")
                df = pd.read_csv(cache_file, encoding='utf-8-sig')
                if df is not None and not df.empty:
                    return df
            except Exception:
                pass

        return None

    def _save_cache(self):
        """保存缓存"""
        if self.all_stocks_df is not None and not self.all_stocks_df.empty:
            try:
                cache_file = self._get_cache_file()
                self.all_stocks_df.to_csv(cache_file, index=False, encoding='utf-8-sig')
            except Exception as e:
                pass  # 忽略缓存保存错误

    def clear_fund_flow_cache(self):
        """清除资金流缓存"""
        try:
            cache_file = self._get_fund_flow_cache_file()
            if cache_file.exists():
                cache_file.unlink()
                print("资金流缓存已清除")
        except Exception:
            pass

    def _normalize_columns(self):
        """统一列名格式，处理不同数据源的列名差异"""
        if self.all_stocks_df is None or self.all_stocks_df.empty:
            return

        df = self.all_stocks_df

        # 代码列统一
        if '代码' not in df.columns:
            if 'symbol' in df.columns:
                df['代码'] = df['symbol'].str.replace('sh', '').replace('sz', '').replace('bj', '')
            elif '股票代码' in df.columns:
                df['代码'] = df['股票代码']

        # 名称列统一
        if '名称' not in df.columns:
            if 'name' in df.columns:
                df['名称'] = df['name']
            elif '股票名称' in df.columns:
                df['名称'] = df['股票名称']

        # 涨跌幅列统一
        if '涨跌幅' not in df.columns:
            if 'change_percent' in df.columns:
                df['涨跌幅'] = df['change_percent']
            elif 'pctChange' in df.columns:
                df['涨跌幅'] = df['pctChange']

        # 量比列统一
        if '量比' not in df.columns:
            if 'volume_ratio' in df.columns:
                df['量比'] = df['volume_ratio']

        # 换手率列统一
        if '换手率' not in df.columns:
            if 'turnover_ratio' in df.columns:
                df['换手率'] = df['turnover_ratio']

        # 最新价列统一
        if '最新价' not in df.columns:
            if 'current' in df.columns:
                df['最新价'] = df['current']
            elif '现价' in df.columns:
                df['最新价'] = df['现价']

        self.all_stocks_df = df

    def filter_basic(self, df: pd.DataFrame) -> pd.DataFrame:
        """基础条件筛选"""
        result = df.copy()

        # 排除 ST
        if self.config['exclude_st'] and '名称' in result.columns:
            result = result[~result['名称'].str.contains('ST', na=False)]

        # 排除停牌 (成交量为 0)
        if '成交量' in result.columns:
            result = result[result['成交量'] > 0]

        return result

    def filter_gain(self, df: pd.DataFrame) -> pd.DataFrame:
        """涨幅筛选"""
        result = df.copy()

        # 尝试不同可能的列名
        gain_col = None
        for col in ['涨跌幅', '涨幅', 'pctChange', 'change_percent']:
            if col in result.columns:
                gain_col = col
                break

        if gain_col:
            result = result[
                (result[gain_col] >= self.config['min_gain']) &
                (result[gain_col] <= self.config['max_gain'])
            ]

        return result

    def filter_turnover(self, df: pd.DataFrame) -> pd.DataFrame:
        """换手率筛选"""
        result = df.copy()

        # 尝试不同可能的列名
        turnover_col = None
        for col in ['换手率', 'turnover_ratio']:
            if col in result.columns:
                turnover_col = col
                break

        if turnover_col:
            result = result[
                (result[turnover_col] >= self.config['min_turnover']) &
                (result[turnover_col] <= self.config['max_turnover'])
            ]

        return result

    def filter_volume_ratio(self, df: pd.DataFrame) -> pd.DataFrame:
        """量比筛选"""
        result = df.copy()

        # 尝试不同可能的列名
        vol_ratio_col = None
        for col in ['量比', 'volume_ratio']:
            if col in result.columns:
                vol_ratio_col = col
                break

        if vol_ratio_col:
            result = result[result[vol_ratio_col] >= self.config['min_volume_ratio']]

        return result

    def merge_fund_flow(self, df: pd.DataFrame) -> pd.DataFrame:
        """合并资金流向数据"""
        result = df.copy()
        self.has_fund_flow = False  # 标记是否有资金流数据

        if self.fund_flow_df is None or self.fund_flow_df.empty:
            # 无资金流向数据时，尝试逐个获取选中股票的资金流
            self.fund_flow_df = self._fetch_selected_stocks_fund_flow(result)

        if self.fund_flow_df is None or self.fund_flow_df.empty:
            # 无资金流向数据时，打印清晰提示
            print("")
            print("  " + "=" * 50)
            print("  提示：无资金流向数据")
            print("  " + "-" * 50)
            print("  可能原因:")
            print("  1. 东方财富 API 连接不稳定")
            print("  2. 网络环境问题（请检查代理设置）")
            print("  3. API 接口临时不可用")
            print("  " + "-" * 50)
            print("  建议:")
            print("  - 关闭或重启代理软件后重试")
            print("  - 运行 `python src/tail_main.py --mode clear_cache` 清除缓存")
            print("  - 在网络良好环境下使用")
            print("  " + "=" * 50)
            print("")
            print("  将使用纯技术指标筛选（满分 75 分）")
            return result

        self.has_fund_flow = True

        # 代码匹配
        try:
            # 合并资金流数据（使用 '主力净流入' 列）
            merged = pd.merge(
                result,
                self.fund_flow_df[['代码', '主力净流入']],
                on='代码',
                how='left'
            )
            # 没有资金流数据的股票设为 0，但不筛选掉
            merged['主力净流入'] = merged['主力净流入'].fillna(0)
            merged['主力净流入 (万)'] = merged['主力净流入'] / 10000
            result = merged
        except Exception as e:
            print(f"合并资金流数据失败：{e}")
            print("  将跳过主力净流入筛选")

        return result

    def _fetch_selected_stocks_fund_flow(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        逐个获取选中股票的资金流数据
        用于排名接口失败时的备选方案
        """
        if df is None or df.empty:
            return None

        result_list = []
        # 获取所有股票的资金流（最多 50 只，避免超时）
        codes = df['代码'].tolist()[:50]

        print(f"  开始获取 {len(codes)} 只股票的资金流数据（最多 50 只）...")
        success_count = 0

        for i, code in enumerate(codes):
            try:
                # 判断市场
                if code.startswith("6"):
                    market = "sh"
                elif code.startswith("0") or code.startswith("3"):
                    market = "sz"
                elif code.startswith("4") or code.startswith("8"):
                    market = "bj"
                else:
                    market = "sh"

                # 获取资金流
                fund_df = ak.stock_individual_fund_flow(stock=code, market=market)
                if fund_df is not None and not fund_df.empty:
                    # 获取最新一条（今日）数据
                    # 使用索引获取：第 3 列是「今日主力净流入 - 净额」
                    latest = fund_df.iloc[0]
                    inflow = latest.iloc[3] if len(latest) > 3 else 0
                    result_list.append({
                        '代码': code,
                        '主力净流入': float(inflow) if pd.notna(inflow) else 0.0
                    })
                    success_count += 1
            except Exception as e:
                pass  # 静默失败，继续使用其他股票

            if (i + 1) % 10 == 0:
                print(f"  进度：{i+1}/{len(codes)} (已成功：{success_count})")
            time.sleep(0.3)  # 避免请求过快

        print(f"  资金流获取完成：{success_count}/{len(codes)} 只成功")

        if result_list:
            return pd.DataFrame(result_list)
        return None

    def filter_main_inflow(self, df: pd.DataFrame) -> pd.DataFrame:
        """主力净流入筛选"""
        result = df.copy()

        # 如果没有资金流数据，跳过筛选
        if not getattr(self, 'has_fund_flow', False):
            print("  跳过主力净流入筛选（无完整资金流数据）")
            return result

        # 检查有多少股票有资金流数据
        if '主力净流入 (万)' in result.columns:
            # 计算有资金流数据的股票数量
            non_zero = (result['主力净流入 (万)'] != 0).sum()
            total = len(result)

            # 如果大部分股票没有资金流数据，跳过筛选
            if non_zero < total * 0.5:
                print(f"  跳过主力净流入筛选（仅 {non_zero}/{total} 只有资金流数据）")
                return result

            # 只有当大部分股票有资金流数据时才筛选
            print(f"  主力净流入筛选：{non_zero}/{total} 只有数据")
            result = result[result['主力净流入 (万)'] >= self.config['min_main_inflow']]

        return result

    def calculate_score(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        综合评分系统
        满分 100 分 (无资金流数据时 75 分)

        评分项:
        - 涨幅评分：20 分 (越接近 5% 分越高)
        - 量比评分：20 分
        - 换手率评分：15 分 (5%-15% 最佳)
        - 资金流入评分：25 分 (仅在有资金流数据时)
        - 板块热度：20 分
        """
        result = df.copy()
        result['score'] = 0.0
        has_fund_flow = getattr(self, 'has_fund_flow', False)

        # 1. 涨幅评分 (越接近 5% 分越高)
        gain_col = None
        for col in ['涨跌幅', '涨幅', 'pctChange']:
            if col in result.columns:
                gain_col = col
                break

        if gain_col:
            result['gain_score'] = 20 - abs(result[gain_col] - 5) * 2
            result['gain_score'] = result['gain_score'].clip(0, 20)
            result['score'] += result['gain_score']

        # 2. 量比评分
        vol_ratio_col = None
        for col in ['量比', 'volume_ratio']:
            if col in result.columns:
                vol_ratio_col = col
                break

        if vol_ratio_col:
            result['vol_score'] = result[vol_ratio_col].apply(lambda x: min(20, x * 5))
            result['score'] += result['vol_score']

        # 3. 换手率评分 (5%-15% 最佳)
        turnover_col = None
        for col in ['换手率', 'turnover_ratio']:
            if col in result.columns:
                turnover_col = col
                break

        if turnover_col:
            result['turnover_score'] = 15 - abs(result[turnover_col] - 10)
            result['turnover_score'] = result['turnover_score'].clip(0, 15)
            result['score'] += result['turnover_score']

        # 4. 资金流入评分 (仅在有资金流数据时)
        if has_fund_flow and '主力净流入 (万)' in result.columns:
            result['inflow_score'] = result['主力净流入 (万)'].apply(lambda x: min(25, max(0, x / 100)))
            result['inflow_score'] = result['inflow_score'].clip(0, 25)
            result['score'] += result['inflow_score']
        else:
            # 无资金流数据时，不加分
            result['inflow_score'] = 0

        # 5. 板块热度 (简化)
        result['sector_score'] = 20 - (result.index % 20)
        result['score'] += result['sector_score']

        # 总分归一化
        # 有资金流时满分 100，无资金流时满分 75
        max_score = 100 if has_fund_flow else 75
        result['score'] = result['score'].clip(0, max_score)

        return result

    def select(self, show_all: bool = False) -> pd.DataFrame:
        """执行选股流程"""
        # 1. 获取数据
        if not self.fetch_all_data():
            return pd.DataFrame()

        # 2. 基础筛选
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 开始筛选...")
        result = self.filter_basic(self.all_stocks_df)
        print(f"  基础筛选后：{len(result)} 只")

        # 3. 涨幅筛选
        result = self.filter_gain(result)
        print(f"  涨幅筛选后：{len(result)} 只")

        # 4. 换手率筛选
        result = self.filter_turnover(result)
        print(f"  换手率筛选后：{len(result)} 只")

        # 5. 量比筛选
        result = self.filter_volume_ratio(result)
        print(f"  量比筛选后：{len(result)} 只")

        # 6. 合并资金流
        result = self.merge_fund_flow(result)

        # 7. 主力流入筛选
        result = self.filter_main_inflow(result)
        print(f"  资金流筛选后：{len(result)} 只")

        # 8. 计算综合评分
        result = self.calculate_score(result)

        # 9. 按评分排序
        if not result.empty and 'score' in result.columns:
            result = result.sort_values('score', ascending=False)

        # 10. 返回前 N 只
        top_n = self.config['top_n']
        result = result.head(top_n)

        if show_all and not result.empty:
            self._print_result(result)

        return result

    def _print_result(self, df: pd.DataFrame):
        """打印选股结果"""
        from tabulate import tabulate

        print("\n" + "=" * 80)
        print(f"【尾盘选股结果】{datetime.now().strftime('%Y-%m-%d %H:%M')}")
        print("=" * 80)

        cols_to_show = []
        for nice_name, options in [('代码', ['代码']), ('名称', ['名称']),
                                    ('涨幅', ['涨跌幅', '涨幅']), ('量比', ['量比']),
                                    ('换手', ['换手率']), ('主力流入 (万)', ['主力净流入 (万)']),
                                    ('评分', ['score'])]:
            for col in options:
                if col in df.columns:
                    cols_to_show.append(col)
                    break

        if cols_to_show:
            display_df = df[cols_to_show].copy()

            for col in display_df.columns:
                if col in ['涨幅', '换手']:
                    display_df[col] = display_df[col].apply(lambda x: f"{x:.2f}%")
                elif col == '量比':
                    display_df[col] = display_df[col].apply(lambda x: f"{x:.2f}")
                elif col == '主力流入 (万)':
                    display_df[col] = display_df[col].apply(lambda x: f"{x:.0f}")
                elif col == '评分':
                    display_df[col] = display_df[col].apply(lambda x: f"{x:.1f}")

            table = tabulate(display_df, headers='keys', tablefmt='grid', showindex=False, stralign='center')
            print(table)

        print("=" * 80)

    def get_stock_detail(self, symbol: str) -> Dict:
        """获取个股详细信息"""
        detail = {
            'symbol': symbol,
            'name': '',
            'current_price': 0,
            'gain': 0,
            'volume_ratio': 0,
            'turnover': 0,
            'main_inflow': 0,
            'ma5': 0,
            'ma10': 0,
            'ma20': 0,
            'score': 0,
            'recommendation': ''
        }

        if self.all_stocks_df is not None:
            stock_data = self.all_stocks_df[self.all_stocks_df['代码'] == symbol]
            if not stock_data.empty:
                row = stock_data.iloc[0]
                detail['name'] = row.get('名称', '')
                detail['current_price'] = row.get('最新价', 0)
                detail['gain'] = row.get('涨跌幅', 0)

        try:
            hist = get_stock_history(symbol, start_date=(datetime.now() - timedelta(days=60)).strftime("%Y%m%d"))
            if hist is not None and not hist.empty:
                detail['ma5'] = hist['收盘'].iloc[-5:].mean() if len(hist) >= 5 else 0
                detail['ma10'] = hist['收盘'].iloc[-10:].mean() if len(hist) >= 10 else 0
                detail['ma20'] = hist['收盘'].iloc[-20:].mean() if len(hist) >= 20 else 0

                if detail['current_price'] > detail['ma5'] > detail['ma10']:
                    detail['recommendation'] = '多头排列'
                elif detail['current_price'] > detail['ma20']:
                    detail['recommendation'] = '站上 20 日线'
                else:
                    detail['recommendation'] = '趋势未明'
        except Exception as e:
            detail['recommendation'] = '数据不足'

        return detail


if __name__ == "__main__":
    print("=" * 60)
    print("         尾盘选股器 - 策略测试")
    print("=" * 60)

    picker = TailStockPicker({
        'top_n': 10,
        'min_gain': 2.0,
        'max_gain': 8.0,
        'min_volume_ratio': 1.2,
        'min_turnover': 3.0,
        'max_turnover': 25.0,
        'min_main_inflow': 300,
    })

    result = picker.select(show_all=True)

    if not result.empty:
        print(f"\n选中 {len(result)} 只股票")
