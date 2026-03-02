"""
新浪财经 API 封装模块
提供 A 股实时行情接口（免费、无需授权）
"""

import requests
import re
from typing import List, Dict
import pandas as pd


class SinaStockAPI:
    """新浪财经股票行情 API"""

    # 市场代码映射
    MARKET_MAP = {
        "sh": "sh",  # 上交所
        "sz": "sz",  # 深交所
        "bj": "bj",  # 北交所
    }

    def __init__(self, timeout: int = 10):
        self.timeout = timeout
        self.session = requests.Session()
        # 设置请求头，避免 403
        self.session.headers.update({
            'Referer': 'https://finance.sina.com.cn/',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

    def _format_symbol(self, symbol: str) -> str:
        """
        格式化股票代码为新浪格式

        Args:
            symbol: 股票代码，如 "600519" 或 "sh600519"

        Returns:
            str: 格式化后的代码，如 "sh600519"
        """
        symbol = str(symbol).strip().lower()
        if symbol.startswith("sh") or symbol.startswith("sz") or symbol.startswith("bj"):
            return symbol

        # 根据代码前缀判断市场
        if symbol.startswith("6"):
            return f"sh{symbol}"
        elif symbol.startswith("0") or symbol.startswith("3"):
            return f"sz{symbol}"
        elif symbol.startswith("4") or symbol.startswith("8"):
            return f"bj{symbol}"
        else:
            return f"sh{symbol}"

    def get_realtime(self, symbol: str) -> Dict:
        """
        获取单只股票实时行情

        Args:
            symbol: 股票代码

        Returns:
            dict: 行情数据
        """
        code = self._format_symbol(symbol)
        url = f"http://hq.sinajs.cn/list={code}"

        try:
            response = self.session.get(url, timeout=self.timeout)
            # 新浪返回的是 GBK 编码，使用 content 解码更可靠
            text = response.content.decode('gbk')

            # 解析返回数据
            # 格式：var hq_str_sh600519="股票名，开盘，收盘，当前，最高，最低，..."
            match = re.search(r'"(.+)"', text)
            if not match:
                return {}

            data = match.group(1).split(",")
            if len(data) < 32:
                return {}

            result = {
                "symbol": code,
                "name": data[0],
                "open": float(data[1]) if data[1] else 0,
                "close": float(data[2]) if data[2] else 0,  # 昨收
                "current": float(data[3]) if data[3] else 0,  # 当前价
                "high": float(data[4]) if data[4] else 0,
                "low": float(data[5]) if data[5] else 0,
                "volume": float(data[6]) if data[6] else 0,  # 成交量（手）
                "amount": float(data[7]) if data[7] else 0,  # 成交额（元）
                "bid1_volume": float(data[8]) if data[8] else 0,
                "bid1_price": float(data[9]) if data[9] else 0,
                "bid2_volume": float(data[10]) if data[10] else 0,
                "bid2_price": float(data[11]) if data[11] else 0,
                "bid3_volume": float(data[12]) if data[12] else 0,
                "bid3_price": float(data[13]) if data[13] else 0,
                "bid4_volume": float(data[14]) if data[14] else 0,
                "bid4_price": float(data[15]) if data[15] else 0,
                "bid5_volume": float(data[16]) if data[16] else 0,
                "bid5_price": float(data[17]) if data[17] else 0,
                "ask1_price": float(data[18]) if data[18] else 0,
                "ask1_volume": float(data[19]) if data[19] else 0,
                "ask2_price": float(data[20]) if data[20] else 0,
                "ask2_volume": float(data[21]) if data[21] else 0,
                "ask3_price": float(data[22]) if data[22] else 0,
                "ask3_volume": float(data[23]) if data[23] else 0,
                "ask4_price": float(data[24]) if data[24] else 0,
                "ask4_volume": float(data[25]) if data[25] else 0,
                "ask5_price": float(data[26]) if data[26] else 0,
                "ask5_volume": float(data[27]) if data[27] else 0,
                "date": data[30] if len(data) > 30 else "",
                "time": data[31] if len(data) > 31 else "",
            }

            # 计算涨跌幅
            if result["current"] > 0 and result["close"] > 0:
                result["change"] = result["current"] - result["close"]
                result["change_percent"] = (result["change"] / result["close"]) * 100
            else:
                result["change"] = 0
                result["change_percent"] = 0

            return result

        except Exception as e:
            print(f"获取行情失败 (symbol={symbol}): {e}")
            return {}

    def get_batch_realtime(self, symbols: List[str]) -> pd.DataFrame:
        """
        批量获取多只股票实时行情

        Args:
            symbols: 股票代码列表

        Returns:
            DataFrame: 行情数据
        """
        # 格式化股票代码
        codes = [self._format_symbol(s) for s in symbols]

        # 新浪支持批量查询，最多一次 1020 只
        batch_size = 1000
        all_results = []

        for i in range(0, len(codes), batch_size):
            batch_codes = codes[i:i + batch_size]
            code_str = ",".join(batch_codes)
            url = f"http://hq.sinajs.cn/list={code_str}"

            try:
                response = self.session.get(url, timeout=self.timeout * len(batch_codes))
                # 使用 content 解码
                text = response.content.decode('gbk')

                for line in text.split("\n"):
                    if not line.strip():
                        continue
                    match = re.search(r'var hq_str_(\w+)="(.+)"', line)
                    if not match:
                        continue

                    code = match.group(1)
                    data = match.group(2).split(",")

                    if len(data) < 32:
                        continue

                    current = float(data[3]) if data[3] else 0
                    close = float(data[2]) if data[2] else 0

                    result = {
                        "symbol": code,
                        "name": data[0],
                        "current": current,
                        "open": float(data[1]) if data[1] else 0,
                        "close": close,  # 昨收
                        "high": float(data[4]) if data[4] else 0,
                        "low": float(data[5]) if data[5] else 0,
                        "volume": float(data[6]) if data[6] else 0,  # 改为 float
                        "amount": float(data[7]) if data[7] else 0,
                        "change": current - close if current > 0 and close > 0 else 0,
                        "change_percent": ((current - close) / close * 100) if current > 0 and close > 0 else 0,
                        "time": data[31] if len(data) > 31 else "",
                    }
                    all_results.append(result)

            except Exception as e:
                print(f"批量获取行情失败：{e}")
                continue

        return pd.DataFrame(all_results) if all_results else pd.DataFrame()

    def get_all_a_shares(self) -> pd.DataFrame:
        """
        获取全部 A 股实时行情

        Returns:
            DataFrame: 全部 A 股行情数据
        """
        # 内置 A 股代码列表（避免依赖东方财富接口）
        # 主板 + 创业板 + 科创板
        all_symbols = []

        # 生成股票代码列表
        # 沪市主板：600000-603999
        for i in range(600000, 604000):
            all_symbols.append(f"sh{i:06d}")

        # 深市主板：000000-002999
        for i in range(0, 3000):
            all_symbols.append(f"sz{i:06d}")

        # 中小板：002000-002999 (已合并到深市主板)
        # 创业板：300000-301999
        for i in range(300000, 302000):
            all_symbols.append(f"sz{i:06d}")

        # 科创板：688000-688999
        for i in range(688000, 689000):
            all_symbols.append(f"sh{i:06d}")

        print(f"共 {len(all_symbols)} 个股票代码，批量获取行情...")

        # 分批获取
        all_results = []
        batch_size = 100

        for i in range(0, len(all_symbols), batch_size):
            batch = all_symbols[i:i + batch_size]
            try:
                df = self.get_batch_realtime(batch)
                if not df.empty:
                    all_results.append(df)
                print(f"\r  进度：{i + batch_size}/{len(all_symbols)}", end="")
            except Exception as e:
                continue

        print()

        if all_results:
            return pd.concat(all_results, ignore_index=True)
        return pd.DataFrame()


if __name__ == "__main__":
    # 测试代码
    print("=" * 50)
    print("测试新浪财经 API")
    print("=" * 50)

    api = SinaStockAPI()

    # 测试 1：获取单只股票行情
    print("\n[测试 1] 获取贵州茅台 (600519) 实时行情...")
    data = api.get_realtime("600519")
    if data:
        print(f"股票名称：{data['name']}")
        print(f"当前价：{data['current']}")
        print(f"开盘：{data['open']} | 最高：{data['high']} | 最低：{data['low']}")
        print(f"昨收：{data['close']} | 涨跌：{data['change']:.2f} ({data['change_percent']:.2f}%)")
        print(f"成交量：{data['volume']}手 | 成交额：{data['amount']}元")
        print(f"时间：{data['date']} {data['time']}")

    # 测试 2：批量获取行情
    print("\n[测试 2] 批量获取多只股票行情...")
    test_symbols = ["600519", "000001", "000858", "300750", "601318"]
    df = api.get_batch_realtime(test_symbols)
    if not df.empty:
        print(df.to_string())

    # 测试 3：获取全部 A 股
    print("\n[测试 3] 获取全部 A 股实时行情（可能需要几秒）...")
    df = api.get_all_a_shares()
    if not df.empty:
        print(f"获取成功，共 {len(df)} 只股票")
        print(df.head(10).to_string())
