# -*- coding: utf-8 -*-
"""
腾讯财经数据源 (增强版)
获取板块数据、成分股、行情等
"""

import requests
import pandas as pd
import time
from typing import Dict, List
from datetime import datetime


class TencentThemeCrawler:
    """腾讯财经题材数据爬虫"""

    # 腾讯板块成分股 API
    THEME_COMPONENTS_URL = "http://stock.gtimg.cn/data/index.php"

    # 腾讯实时行情 API
    QUOTE_URL = "http://qt.gtimg.cn/q="

    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Referer': 'http://stockapp.finance.qq.com/',
    }

    # 常用板块代码映射 (板块名称 -> 腾讯板块代码)
    THEME_CODE_MAP = {
        "人工智能": "bk1021",
        "芯片半导体": "bk1037",
        "新能源": "bk1024",
        "光伏": "bk1065",
        "锂电": "bk1066",
        "风电": "bk1067",
        "核电": "bk1068",
        "AI 算力": "bk1104",
        "5G": "bk1046",
        "机器人": "bk1035",
        "低空经济": "bk1142",
        "华为概念": "bk1057",
        "白酒": "bk1050",
        "医药": "bk1042",
        "券商": "bk1002",
        "银行": "bk1001",
        "房地产": "bk1018",
        "汽车": "bk1013",
        "军工": "bk1019",
        "煤炭": "bk1006",
        "石油": "bk1005",
        "钢铁": "bk1008",
        "有色": "bk1009",
        "化工": "bk1012",
        "消费": "bk1030",
        "科技": "bk1020",
        "互联网": "bk1056",
        "传媒": "bk1054",
        "旅游": "bk1048",
        "物流": "bk1047",
        "高铁": "bk1036",
        "高端装备": "bk1090",
        "区块链": "bk1088",
        "物联网": "bk1045",
    }

    # 龙头股映射
    LEADER_STOCKS = {
        "人工智能": "600519",
        "芯片半导体": "603986",
        "新能源": "300750",
        "AI 算力": "601360",
        "低空经济": "000099",
        "华为概念": "002594",
        "白酒": "600519",
        "券商": "600030",
    }

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)
        self._cache = {}
        self._cache_time = {}

    def get_theme_list(self) -> List[Dict]:
        """获取板块列表"""
        return [{'名称': k, '代码': v} for k, v in self.THEME_CODE_MAP.items()]

    def get_theme_board(self) -> pd.DataFrame:
        """
        获取板块行情数据

        Returns:
            DataFrame: 板块行情数据
        """
        all_data = []

        for theme_name, theme_code in self.THEME_CODE_MAP.items():
            try:
                # 获取板块行情
                symbol = f'BK{theme_code[2:]}' if theme_code.startswith('bk') else theme_code
                url = f'http://qt.gtimg.cn/q={symbol}'
                resp = self.session.get(url, timeout=5)
                resp.encoding = 'gbk'

                text = resp.text.strip()
                if '="' in text:
                    parts = text.split('="')
                    if len(parts) >= 2:
                        data = parts[1].strip('"').strip(';').split('~')
                        if len(data) >= 5:
                            code = data[2] if len(data) > 2 else ''
                            cur = float(data[3]) if data[3] else 0
                            pre = float(data[4]) if data[4] else 0
                            change_pct = (cur - pre) / pre * 100 if pre > 0 else 0

                            all_data.append({
                                '板块代码': theme_code,
                                '板块名称': theme_name,
                                '最新价': cur,
                                '涨跌幅': change_pct,
                                '涨跌额': cur - pre,
                            })

                time.sleep(0.2)

            except Exception as e:
                continue

        return pd.DataFrame(all_data) if all_data else pd.DataFrame()

    def get_theme_components(self, theme_code: str) -> pd.DataFrame:
        """
        获取板块成分股

        Args:
            theme_code: 板块代码 (如 bk0588)

        Returns:
            DataFrame: 成分股列表
        """
        params = {
            'appn': 'detail',
            'act': 'data',
            'c': theme_code,
            'p': '1',
            'l': '500',
            '_': str(int(time.time() * 1000))
        }

        try:
            resp = self.session.get(self.THEME_COMPONENTS_URL, params=params, timeout=10)
            resp.encoding = 'gbk'

            text = resp.text.strip()
            if '=' in text:
                data_str = text.split('=', 1)[1].strip('"').strip('"')
                parts = data_str.split(',')
                if len(parts) >= 3:
                    field_count = int(parts[0])
                    data_list = []
                    idx = 3
                    while idx + 10 < len(parts):
                        try:
                            stock_code = parts[idx + 3][:6] if len(parts[idx + 3]) >= 6 else parts[idx + 3]
                            stock_name = parts[idx + 4]
                            cur = float(parts[idx + 5]) if parts[idx + 5] else 0
                            change = float(parts[idx + 6]) if parts[idx + 6] else 0
                            pre = cur - change
                            change_pct = (change / pre * 100) if pre > 0 else 0

                            data_list.append({
                                '代码': stock_code,
                                '名称': stock_name,
                                '最新价': cur,
                                '涨跌幅': change_pct,
                                '涨跌额': change,
                                '成交量': float(parts[idx + 7]) if parts[idx + 7] else 0,
                                '成交额': float(parts[idx + 8]) if parts[idx + 8] else 0,
                            })
                            idx += 11
                        except (ValueError, IndexError):
                            idx += 11
                            continue

                    return pd.DataFrame(data_list)

        except Exception as e:
            print(f"获取成分股失败：{e}")

        return pd.DataFrame()

    def get_quotes(self, symbols: List[str]) -> pd.DataFrame:
        """
        获取多只股票行情

        Args:
            symbols: 股票代码列表 (6 位数字)

        Returns:
            DataFrame: 行情数据
        """
        if not symbols:
            return pd.DataFrame()

        all_quotes = []
        batch_size = 50

        for i in range(0, len(symbols), batch_size):
            batch = symbols[i:i+batch_size]
            symbol_list = ','.join(['sh'+s if s.startswith('6') else 'sz'+s for s in batch])
            url = f'{self.QUOTE_URL}{symbol_list}'

            try:
                resp = self.session.get(url, timeout=10)
                resp.encoding = 'gbk'

                lines = resp.text.strip().split(';')
                for line in lines:
                    if not line:
                        continue
                    parts = line.split('"')
                    if len(parts) < 2:
                        continue
                    data = parts[1].split('~')
                    if len(data) < 5:
                        continue

                    try:
                        code = data[2] if len(data) > 2 else ''
                        name = data[1] if len(data) > 1 else ''
                        cur = float(data[3]) if data[3] else 0
                        pre = float(data[4]) if data[4] else 0
                        change = cur - pre
                        change_pct = (change / pre * 100) if pre > 0 else 0

                        all_quotes.append({
                            '代码': code,
                            '名称': name,
                            '最新价': cur,
                            '涨跌额': change,
                            '涨跌幅': change_pct,
                            '成交量': float(data[6]) if len(data) > 6 and data[6] else 0,
                            '成交额': float(data[7]) if len(data) > 7 and data[7] else 0,
                        })
                    except (ValueError, IndexError):
                        continue

                time.sleep(0.3)

            except Exception as e:
                continue

        return pd.DataFrame(all_quotes) if all_quotes else pd.DataFrame()

    def get_market_snapshot(self, symbol: str) -> Dict:
        """
        获取个股实时行情

        Args:
            symbol: 股票代码 (6 位数字)

        Returns:
            dict: 行情数据
        """
        quotes = self.get_quotes([symbol])
        if not quotes.empty:
            return quotes.iloc[0].to_dict()
        return {}

    def get_all_components_data(self) -> Dict[str, pd.DataFrame]:
        """
        获取所有板块的成分股数据

        Returns:
            Dict: 板块名 -> 成分股 DataFrame
        """
        result = {}
        for theme_name, theme_code in self.THEME_CODE_MAP.items():
            print(f"获取 {theme_name} 成分股...", end="\r")
            df = self.get_theme_components(theme_code)
            if not df.empty:
                result[theme_name] = df
            time.sleep(0.3)

        print(f"完成获取 {len(result)} 个板块成分股")
        return result


# 测试
if __name__ == "__main__":
    print("=" * 60)
    print("腾讯财经数据源测试")
    print("=" * 60)

    crawler = TencentThemeCrawler()

    # 测试 1: 获取板块列表
    print("\n【测试 1】板块列表:")
    theme_list = crawler.get_theme_list()
    for t in theme_list[:10]:
        print(f"  {t['名称']}: {t['代码']}")

    # 测试 2: 获取板块行情
    print("\n【测试 2】获取板块行情...")
    df = crawler.get_theme_board()
    if not df.empty:
        df = df.sort_values('涨跌幅', ascending=False)
        print(f"成功获取 {len(df)} 个板块行情")
        print("\n涨幅榜 TOP10:")
        print(df[['板块名称', '最新价', '涨跌幅']].head(10).to_string(index=False))

    # 测试 3: 获取板块成分股
    print("\n【测试 3】获取 AI 算力成分股...")
    df = crawler.get_theme_components("bk1104")
    if not df.empty:
        print(f"成功获取 {len(df)} 只成分股")
        print(df[['代码', '名称', '最新价', '涨跌幅']].head(10).to_string(index=False))

    # 测试 4: 获取股票行情
    print("\n【测试 4】获取个股行情...")
    quotes = crawler.get_quotes(["600519", "002594", "601360"])
    if not quotes.empty:
        for _, row in quotes.iterrows():
            print(f"  {row['代码']} {row['名称']}: {row['最新价']}元 ({row['涨跌幅']:+.2f}%)")

    print("\n测试完成!")
