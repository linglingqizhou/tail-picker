# -*- coding: utf-8 -*-
"""
腾讯财经数据源
接口：http://qt.gtimg.cn/
提供实时行情、涨跌幅等数据
作为 AkShare 的备用数据源
"""

import requests
import re
from typing import List, Dict
import pandas as pd
from datetime import datetime

from src.data_sources.base import BaseDataSource


class TencentStockAPI(BaseDataSource):
    """腾讯财经股票行情 API"""

    NAME = "腾讯财经"
    DESCRIPTION = "腾讯财经实时行情接口"
    PRIORITY = 2  # 优先级 2，作为 AkShare 的备份

    # 腾讯财经 API 地址
    BASE_URL = "http://qt.gtimg.cn/"

    def __init__(self, timeout: int = 10):
        super().__init__(timeout)
        self.session = requests.Session()
        self.session.headers.update({
            'Referer': 'http://qt.gtimg.cn/',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

    def _format_symbol(self, symbol: str) -> str:
        """
        格式化股票代码为腾讯格式

        腾讯格式：
        - sh600519 (沪市)
        - sz000001 (深市)
        - bjXXXXX (北交所)
        """
        symbol = str(symbol).strip()

        # 如果已经有市场前缀，转小写
        if symbol[:2].lower() in ['sh', 'sz', 'bj']:
            return symbol.lower()

        # 根据代码前缀判断市场
        if symbol.startswith('6'):
            return f"sh{symbol}"
        elif symbol.startswith('0') or symbol.startswith('3'):
            return f"sz{symbol}"
        elif symbol.startswith('4') or symbol.startswith('8'):
            return f"bj{symbol}"
        else:
            return f"sh{symbol}"

    def get_realtime(self, symbols: List[str]) -> pd.DataFrame:
        """
        批量获取实时行情

        Args:
            symbols: 股票代码列表

        Returns:
            DataFrame: 实时行情数据
        """
        if not symbols:
            return pd.DataFrame()

        # 格式化股票代码
        codes = [self._format_symbol(s) for s in symbols]

        # 腾讯支持批量查询，最多一次 60 只
        batch_size = 50
        all_results = []

        for i in range(0, len(codes), batch_size):
            batch_codes = codes[i:i + batch_size]
            query_str = ",".join(batch_codes)
            url = f"{self.BASE_URL}q={query_str}"

            try:
                response = self.session.get(url, timeout=self.timeout)
                # 腾讯返回 GBK 编码
                text = response.content.decode('gbk')

                for line in text.split("\n"):
                    if not line.strip():
                        continue

                    # 解析格式：v_sh600519="51~贵州茅台~600519~1800.00~..."
                    match = re.search(r'v_(\w+)="([^"]+)"', line)
                    if not match:
                        continue

                    code = match.group(1)
                    data = match.group(2).split("~")

                    if len(data) < 50:
                        continue

                    # 解析数据
                    # 腾讯数据格式：
                    # [0]: 未知
                    # [1]: 名称
                    # [2]: 代码
                    # [3]: 当前价
                    # [4]: 昨收
                    # [5]: 开盘
                    # [6]: 最高
                    # [7]: 最低
                    # [8]: 买一价
                    # [9]: 买一量
                    # [10]: 卖一价
                    # [11]: 卖一量
                    # ...
                    # [36]: 成交量（手）
                    # [37]: 成交额（万元）
                    # [47]: 量比

                    result = {
                        'symbol': code,
                        'name': data[1] if len(data) > 1 else '',
                        'current': float(data[3]) if len(data) > 3 and data[3] else 0,
                        'close': float(data[4]) if len(data) > 4 and data[4] else 0,
                        'open': float(data[5]) if len(data) > 5 and data[5] else 0,
                        'high': float(data[6]) if len(data) > 6 and data[6] else 0,
                        'low': float(data[7]) if len(data) > 7 and data[7] else 0,
                        'bid_price': float(data[8]) if len(data) > 8 and data[8] else 0,
                        'bid_volume': int(float(data[9])) if len(data) > 9 and data[9] else 0,
                        'ask_price': float(data[10]) if len(data) > 10 and data[10] else 0,
                        'ask_volume': int(float(data[11])) if len(data) > 11 and data[11] else 0,
                        'volume': int(float(data[36])) * 100 if len(data) > 36 and data[36] else 0,  # 手转股
                        'amount': float(data[37]) * 10000 if len(data) > 37 and data[37] else 0,  # 万转元
                        'volume_ratio': float(data[47]) if len(data) > 47 and data[47] else 0,
                    }

                    # 计算涨跌幅
                    if result['current'] > 0 and result['close'] > 0:
                        result['change'] = result['current'] - result['close']
                        result['change_percent'] = (result['change'] / result['close']) * 100
                    else:
                        result['change'] = 0
                        result['change_percent'] = 0

                    all_results.append(result)

            except Exception as e:
                print(f"腾讯财经批量获取失败：{e}")
                continue

        return pd.DataFrame(all_results) if all_results else pd.DataFrame()

    def get_all_a_shares(self) -> pd.DataFrame:
        """
        获取全部 A 股实时行情

        腾讯财经没有直接获取全部 A 股的接口，
        这里通过生成代码列表来获取
        """
        # 生成股票代码列表
        all_symbols = []

        # 沪市主板：600000-603999
        for i in range(600000, 604000):
            all_symbols.append(f"{i:06d}")

        # 深市主板：000000-002999
        for i in range(0, 3000):
            all_symbols.append(f"{i:06d}")

        # 中小板：002000-002999 (已合并)
        # 创业板：300000-301999
        for i in range(300000, 302000):
            all_symbols.append(f"{i:06d}")

        # 科创板：688000-688999
        for i in range(688000, 689000):
            all_symbols.append(f"{i:06d}")

        # 北交所：8XXXXX
        for i in range(800000, 801000):
            all_symbols.append(f"{i:06d}")

        print(f"腾讯财经：共 {len(all_symbols)} 个股票代码，批量获取行情...")

        # 分批获取
        all_results = []
        batch_size = 50

        for i in range(0, len(all_symbols), batch_size):
            batch = all_symbols[i:i + batch_size]
            try:
                df = self.get_realtime(batch)
                if not df.empty:
                    all_results.append(df)

                # 过滤掉无效数据（价格为 0 的）
                valid_results = []
                for df in all_results:
                    if not df.empty:
                        valid_df = df[df['current'] > 0]
                        if not valid_df.empty:
                            valid_results.append(valid_df)

                if valid_results:
                    all_results = valid_results

                print(f"\r  进度：{min(i + batch_size, len(all_symbols))}/{len(all_symbols)}", end="")

            except Exception as e:
                continue

        print()

        if all_results:
            return pd.concat(all_results, ignore_index=True)
        return pd.DataFrame()

    def get_market_summary(self) -> Dict:
        """
        获取大盘指数

        Returns:
            dict: 大盘指数数据
        """
        # 大盘指数代码
        indices = {
            '上证指数': 'sh000001',
            '深证成指': 'sz399001',
            '创业板指': 'sz399006',
            '沪深 300': 'sh000300',
        }

        result = {}
        codes = list(indices.values())

        try:
            query_str = ",".join(codes)
            url = f"{self.BASE_URL}q={query_str}"

            response = self.session.get(url, timeout=self.timeout)
            text = response.content.decode('gbk')

            for line in text.split("\n"):
                match = re.search(r'v_(\w+)="([^"]+)"', line)
                if not match:
                    continue

                code = match.group(1)
                data = match.group(2).split("~")

                # 查找对应的指数名称
                name = None
                for k, v in indices.items():
                    if v == code:
                        name = k
                        break

                if name and len(data) > 3:
                    result[name] = {
                        'code': code,
                        'current': float(data[3]) if data[3] else 0,
                        'change_percent': float(data[32]) if len(data) > 32 and data[32] else 0,
                    }

        except Exception as e:
            print(f"获取大盘指数失败：{e}")

        return result


if __name__ == "__main__":
    # 测试代码
    print("=" * 50)
    print("测试腾讯财经 API")
    print("=" * 50)

    api = TencentStockAPI()

    # 测试 1：获取单只股票行情
    print("\n[测试 1] 获取贵州茅台 (600519) 实时行情...")
    df = api.get_realtime(["600519"])
    if not df.empty:
        print(df.to_string())

    # 测试 2：获取多只股票行情
    print("\n[测试 2] 批量获取多只股票行情...")
    test_symbols = ["600519", "000001", "000858", "300750", "601318"]
    df = api.get_realtime(test_symbols)
    if not df.empty:
        print(df.to_string())

    # 测试 3：获取大盘指数
    print("\n[测试 3] 获取大盘指数...")
    indices = api.get_market_summary()
    for name, data in indices.items():
        print(f"  {name}: {data['current']:.2f} ({data['change_percent']:+.2f}%)")
