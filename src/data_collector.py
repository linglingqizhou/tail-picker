"""
数据采集主程序
整合 AkShare 和新浪财经 API，提供完整的数据采集功能
"""

import sys
import os
import io

# 将项目根目录添加到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 设置标准输出编码为 UTF-8，避免 Windows 命令行中文乱码
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import pandas as pd
from tabulate import tabulate
from datetime import datetime, timedelta
import time
from typing import List, Optional

from src.akshare_api import (
    get_all_stocks_realtime,
    get_stock_history,
    get_stock_minute,
    get_lhb_today,
    get_individual_fund_flow,
    get_concept_fund_flow,
)
from src.sina_api import SinaStockAPI
import config


class DataCollector:
    """数据采集器"""

    def __init__(self):
        self.sina_api = SinaStockAPI()

    def collect_all_stocks_snapshot(self, save: bool = True) -> pd.DataFrame:
        """
        采集全部 A 股实时快照

        Args:
            save: 是否保存到文件

        Returns:
            DataFrame: 行情数据
        """
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 开始采集全部 A 股快照...")

        # 使用 AkShare 获取全量数据
        df = get_all_stocks_realtime()

        if df is None or df.empty:
            print("采集失败！")
            return pd.DataFrame()

        print(f"采集成功，共 {len(df)} 只股票")

        if save:
            # 保存到 CSV
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = os.path.join(
                config.REALTIME_DATA_DIR,
                f"snapshot_{timestamp}.csv"
            )
            df.to_csv(filename, index=False, encoding="utf-8-sig")
            print(f"已保存到：{filename}")

        return df

    def collect_watchlist(self, symbols: List[str] = None) -> pd.DataFrame:
        """
        采集关注列表股票实时行情

        Args:
            symbols: 股票代码列表，默认使用 config.WATCHLIST

        Returns:
            DataFrame: 行情数据
        """
        if symbols is None:
            symbols = config.WATCHLIST

        print(f"[{datetime.now().strftime('%H:%M:%S')}] 采集关注列表行情...")

        df = self.sina_api.get_batch_realtime(symbols)

        if df.empty:
            print("采集失败！")
            return pd.DataFrame()

        print(f"采集成功，共 {len(df)} 只股票")
        print(df.to_string())

        return df

    def collect_stock_history(
        self,
        symbol: str,
        start_date: str = None,
        save: bool = True
    ) -> pd.DataFrame:
        """
        采集个股历史 K 线数据

        Args:
            symbol: 股票代码
            start_date: 开始日期，默认 2023-01-01
            save: 是否保存

        Returns:
            DataFrame: K 线数据
        """
        if start_date is None:
            start_date = "20230101"

        print(f"[{datetime.now().strftime('%H:%M:%S')}] 采集 {symbol} 历史数据...")

        df = get_stock_history(symbol, start_date=start_date)

        if df is None or df.empty:
            print(f"采集 {symbol} 失败！")
            return pd.DataFrame()

        print(f"采集 {symbol} 成功，共 {len(df)} 条记录")

        if save:
            filename = os.path.join(
                config.DAILY_DATA_DIR,
                f"{symbol}_daily.csv"
            )
            df.to_csv(filename, index=False, encoding="utf-8-sig")
            print(f"已保存到：{filename}")

        return df

    def collect_all_stocks_history(
        self,
        symbols: List[str] = None,
        start_date: str = "20230101",
        delay: float = 1.0
    ) -> dict:
        """
        批量采集多只股票历史数据

        Args:
            symbols: 股票代码列表
            start_date: 开始日期
            delay: 请求间隔（秒），避免被封

        Returns:
            dict: {symbol: DataFrame}
        """
        if symbols is None:
            # 从 AkShare 获取全部股票列表
            all_df = get_all_stocks_realtime()
            if all_df is not None:
                symbols = all_df["代码"].astype(str).tolist()[:100]  # 限制前 100 只测试

        results = {}
        for i, symbol in enumerate(symbols):
            df = self.collect_stock_history(symbol, start_date, save=True)
            if not df.empty:
                results[symbol] = df

            if i < len(symbols) - 1:
                time.sleep(delay)
                print(f"等待 {delay} 秒后继续...")

        return results

    def collect_minute_data(
        self,
        symbol: str,
        period: str = "5",
        save: bool = True
    ) -> pd.DataFrame:
        """
        采集个股分钟 K 线数据

        Args:
            symbol: 股票代码
            period: 分钟周期 1/5/15/30/60
            save: 是否保存

        Returns:
            DataFrame: 分钟 K 线数据
        """
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 采集 {symbol} {period}分钟线...")

        df = get_stock_minute(symbol, period=period)

        if df is None or df.empty:
            print(f"采集失败！")
            return pd.DataFrame()

        print(f"采集成功，共 {len(df)} 条记录")

        if save:
            filename = os.path.join(
                config.MINUTE_DATA_DIR,
                f"{symbol}_{period}m.csv"
            )
            df.to_csv(filename, index=False, encoding="utf-8-sig")
            print(f"已保存到：{filename}")

        return df

    def collect_lhb(self) -> pd.DataFrame:
        """
        采集龙虎榜数据

        Returns:
            DataFrame: 龙虎榜数据
        """
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 采集龙虎榜数据...")

        df = get_lhb_today()

        if df is None or df.empty:
            print("暂无数据或非交易日")
            return pd.DataFrame()

        print(f"采集成功，共 {len(df)} 条记录")

        # 保存
        timestamp = datetime.now().strftime("%Y%m%d")
        filename = os.path.join(config.DATA_DIR, f"lhb_{timestamp}.csv")
        df.to_csv(filename, index=False, encoding="utf-8-sig")
        print(f"已保存到：{filename}")

        return df

    def collect_fund_flow(self) -> pd.DataFrame:
        """
        采集资金流向数据

        Returns:
            DataFrame: 资金流向排名
        """
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 采集资金流向数据...")

        df = get_individual_fund_flow()

        if df is None or df.empty:
            print("采集失败！")
            return pd.DataFrame()

        print(f"采集成功，共 {len(df)} 条记录\n")
        print("今日资金流向 Top 10:")
        print("-" * 110)

        # 选择要显示的列 - 尝试多种可能的列名
        cols_map = {
            ' rank ': [' rank ', '序号'],
            '代码': ['代码'],
            '名称': ['名称'],
            '最新价': ['最新价'],
            '涨跌幅': ['今日涨跌幅', '涨跌幅', '涨幅']
        }

        available_cols = []
        for nice_name, options in cols_map.items():
            for col in options:
                if col in df.columns:
                    available_cols.append(col)
                    break

        if available_cols:
            subset = df[available_cols].head(10)
            # 重命名为好看的中文名
            rename_map = {}
            for nice_name, options in cols_map.items():
                for col in options:
                    if col in subset.columns:
                        rename_map[col] = nice_name
                        break

            subset = subset.rename(columns=rename_map)

            # 格式化数值
            if '涨跌幅' in subset.columns:
                subset['涨跌幅'] = subset['涨跌幅'].apply(lambda x: f"{x:.2f}%")
            if '最新价' in subset.columns:
                subset['最新价'] = subset['最新价'].apply(lambda x: f"{x:.2f}")

            table = tabulate(subset, headers='keys', tablefmt='grid', showindex=False, stralign='center')
            print(table)
        print("-" * 110)

        return df

    def find_limit_up_stocks(self, df: pd.DataFrame = None) -> pd.DataFrame:
        """
        从实时数据中筛选涨停股票

        Args:
            df: 实时行情 DataFrame，默认调用 AkShare 获取

        Returns:
            DataFrame: 涨停股票列表
        """
        if df is None:
            df = get_all_stocks_realtime()

        if df is None or df.empty:
            return pd.DataFrame()

        # 涨停判断（不同板块幅度不同）
        # 科创板/创业板：20%，北交所：30%，主板：10%

        # 尝试不同可能的列名
        pct_col = None
        for col in ["涨跌幅", "涨跌幅%", "pctChange", "change_percent"]:
            if col in df.columns:
                pct_col = col
                break

        if pct_col is None:
            print("未找到涨跌幅列")
            return pd.DataFrame()

        # 筛选涨幅 > 9.5% 的股票
        limit_up_df = df[df[pct_col] >= 9.5].copy()

        # 排除 ST 和新三板
        if "代码" in limit_up_df.columns:
            limit_up_df = limit_up_df[
                ~limit_up_df["代码"].str.startswith(("4", "8"), na=False)
            ]

        return limit_up_df

        return limit_up_df


def run_morning_scan(target_time: str = "09:30"):
    """
    早盘扫描任务
    每天 9:30 自动运行，筛选潜在涨停股

    Args:
        target_time: 目标时间 HH:MM
    """
    print("\n" + "=" * 70)
    print("                    A 股早盘扫描程序")
    print("                    扫描时间：" + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("=" * 70)

    collector = DataCollector()

    # 1. 获取全部 A 股实时行情
    df = collector.collect_all_stocks_snapshot(save=True)

    if df.empty:
        print("获取行情失败，退出")
        return

    # 2. 筛选涨停股票
    print("\n" + "-" * 70)
    print("【涨停股筛选】")
    print("-" * 70)

    limit_up_df = collector.find_limit_up_stocks(df)

    if not limit_up_df.empty:
        # 按涨幅排序
        if '涨跌幅' in limit_up_df.columns:
            limit_up_df = limit_up_df.sort_values('涨跌幅', ascending=False)

        print(f"\n 涨停股票共 {len(limit_up_df)} 只\n")

        # 显示前 20 只
        cols_to_show = [c for c in ['代码', '名称', '涨跌幅', '最新价', '成交量'] if c in limit_up_df.columns]

        if cols_to_show:
            top20 = limit_up_df[cols_to_show].head(20)
            # 格式化数值
            display_df = top20.copy()
            if '涨跌幅' in display_df.columns:
                display_df['涨跌幅'] = display_df['涨跌幅'].apply(lambda x: f"{x:.2f}%")
            if '最新价' in display_df.columns:
                display_df['最新价'] = display_df['最新价'].apply(lambda x: f"{x:.2f}")

            table = tabulate(display_df, headers='keys', tablefmt='grid', showindex=False, stralign='center')
            print(table)

        if len(limit_up_df) > 20:
            print(f"\n   ... 还有 {len(limit_up_df) - 20} 只涨停股，查看完整列表请打开 CSV 文件")
    else:
        print("\n   暂未发现涨停股票")

    # 3. 获取资金流向
    print("\n" + "-" * 70)
    print("【资金流向】")
    print("-" * 70)
    fund_flow = collector.collect_fund_flow()

    # 4. 获取龙虎榜（如有）
    print("\n" + "-" * 70)
    print("【龙虎榜】")
    print("-" * 70)
    collector.collect_lhb()

    print("\n" + "=" * 70)
    print("                    扫描完成!")
    print("                    数据已保存到：D:\\cursor\\stock_data\\")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="A 股数据采集程序")
    parser.add_argument(
        "--mode",
        choices=["snapshot", "watchlist", "history", "minute", "lhb", "fundflow", "morning"],
        default="snapshot",
        help="采集模式"
    )
    parser.add_argument("--symbol", help="股票代码")
    parser.add_argument("--start-date", help="开始日期 YYYYMMDD", default="20230101")

    args = parser.parse_args()

    collector = DataCollector()

    if args.mode == "snapshot":
        collector.collect_all_stocks_snapshot()

    elif args.mode == "watchlist":
        collector.collect_watchlist()

    elif args.mode == "history":
        if not args.symbol:
            print("请指定股票代码 --symbol")
        else:
            collector.collect_stock_history(args.symbol, args.start_date)

    elif args.mode == "minute":
        if not args.symbol:
            print("请指定股票代码 --symbol")
        else:
            collector.collect_minute_data(args.symbol)

    elif args.mode == "lhb":
        collector.collect_lhb()

    elif args.mode == "fundflow":
        collector.collect_fund_flow()

    elif args.mode == "morning":
        run_morning_scan()
