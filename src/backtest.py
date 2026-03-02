"""
尾盘选股器 - 历史回测引擎
回测选股策略的历史表现，计算胜率、收益率等指标
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List
from pathlib import Path

from src.tail_picker import TailStockPicker
from src.akshare_api import get_stock_history


class BacktestEngine:
    """回测引擎"""

    def __init__(self, picker_config: dict = None):
        self.picker_config = picker_config or {}
        self.results = []

    def get_trading_days(self, start_date: str, end_date: str) -> List[str]:
        """获取交易日列表"""
        # 简单实现：获取所有日期，实际使用时应该过滤周末和节假日
        days = []
        current = datetime.strptime(start_date, "%Y%m%d")
        end = datetime.strptime(end_date, "%Y%m%d")

        while current <= end:
            # 排除周末
            if current.weekday() < 5:
                days.append(current.strftime("%Y%m%d"))
            current += timedelta(days=1)

        return days

    def simulate_next_day_return(self, symbol: str, date: str, hold_days: int = 1) -> float:
        """
        模拟次日/持有 N 日后的收益率

        Args:
            symbol: 股票代码
            date: 买入日期
            hold_days: 持有天数

        Returns:
            float: 收益率%
        """
        try:
            # 获取买入日之后 N 天的数据
            start = datetime.strptime(date, "%Y%m%d")
            end_date = (start + timedelta(days=hold_days + 5)).strftime("%Y%m%d")

            hist = get_stock_history(symbol, start_date=date, end_date=end_date)

            if hist is None or len(hist) < 2:
                return 0.0

            # 买入价（当日收盘）
            buy_price = hist['收盘'].iloc[0]

            # 卖出价（持有 N 日后的收盘）
            sell_idx = min(hold_days, len(hist) - 1)
            sell_price = hist['收盘'].iloc[sell_idx]

            if buy_price <= 0:
                return 0.0

            return ((sell_price - buy_price) / buy_price) * 100

        except Exception as e:
            # print(f"获取 {symbol} 数据失败：{e}")
            return 0.0

    def run(self, start_date: str, end_date: str, hold_days: int = 1) -> Dict:
        """
        运行回测

        Args:
            start_date: 开始日期 YYYYMMDD
            end_date: 结束日期 YYYYMMDD
            hold_days: 持有天数

        Returns:
            dict: 回测报告
        """
        trading_days = self.get_trading_days(start_date, end_date)

        total_trades = 0
        winning_trades = 0
        total_return = 0.0
        max_drawdown = 0.0
        daily_returns = []

        print(f"回测区间：{start_date} ~ {end_date}")
        print(f"交易日数：{len(trading_days)}")
        print(f"持有天数：{hold_days}天")
        print("\n开始回测...")

        picker = TailStockPicker(self.picker_config)
        # 减少选股数量以加快回测速度
        picker.config['top_n'] = 5

        for i, day in enumerate(trading_days):
            print(f"\r[{i+1}/{len(trading_days)}] {day}...", end="")

            # 获取选股结果
            if not picker.fetch_all_data():
                continue

            selected = picker.select()

            if selected.empty:
                continue

            # 对每只选股模拟次日收益
            for _, row in selected.iterrows():
                symbol = row.get('代码', '')
                if not symbol:
                    continue

                ret = self.simulate_next_day_return(str(symbol), day, hold_days)
                daily_returns.append(ret)

                total_trades += 1
                total_return += ret

                if ret > 0:
                    winning_trades += 1

                # 计算最大回撤
                if ret < max_drawdown:
                    max_drawdown = ret

        print("\n回测完成!")

        # 计算回测指标
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
        avg_return = (total_return / total_trades) if total_trades > 0 else 0

        # 计算夏普比率 (简化版)
        if daily_returns:
            returns_series = pd.Series(daily_returns)
            sharpe = (returns_series.mean() / returns_series.std() * np.sqrt(252)) if returns_series.std() > 0 else 0
        else:
            sharpe = 0

        report = {
            '交易次数': total_trades,
            '胜率': win_rate,
            '总收益率': total_return,
            '平均收益': avg_return,
            '最大回撤': max_drawdown,
            '夏普比率': sharpe,
            '盈利交易': winning_trades,
            '亏损交易': total_trades - winning_trades,
        }

        self.results = daily_returns
        return report

    def plot_returns(self):
        """绘制收益曲线（需要 matplotlib）"""
        try:
            import matplotlib.pyplot as plt

            if not self.results:
                print("无回测数据")
                return

            # 累计收益
            cumulative = pd.Series(self.results).cumsum()

            plt.figure(figsize=(12, 6))
            plt.plot(cumulative.values)
            plt.title('累计收益曲线')
            plt.xlabel('交易次数')
            plt.ylabel('累计收益率%')
            plt.grid(True)
            plt.savefig('backtest_returns.png')
            print("收益曲线已保存到：backtest_returns.png")

        except ImportError:
            print("安装 matplotlib 以绘制收益曲线：pip install matplotlib")


if __name__ == "__main__":
    # 测试回测
    print("=" * 60)
    print("         回测引擎测试")
    print("=" * 60)

    engine = BacktestEngine({
        'top_n': 3,  # 只选 3 只，加快测试
        'min_gain': 3.0,
        'max_gain': 7.0,
    })

    # 回测最近一个月（简化测试）
    report = engine.run("20260101", "20260131", hold_days=1)

    print("\n" + "=" * 60)
    print("回测结果摘要")
    print("=" * 60)
    for k, v in report.items():
        if isinstance(v, float):
            print(f"  {k}: {v:.2f}%")
        else:
            print(f"  {k}: {v}")
    print("=" * 60)
