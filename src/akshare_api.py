"""
AkShare API 封装模块
提供 A 股实时行情、K 线、龙虎榜、资金流向等数据接口
"""

import akshare as ak
import pandas as pd
from datetime import datetime
from src.sina_api import SinaStockAPI


def get_all_stocks_realtime():
    """
    获取全部 A 股实时行情
    优先使用 AkShare，失败则使用新浪财经 API

    Returns:
        DataFrame: 包含代码、名称、当前价格、涨跌幅、量比、换手率等
    """
    # 尝试 1: AkShare
    try:
        df = ak.stock_zh_a_spot_em()
        if df is not None and not df.empty:
            # 检查是否有量比和换手率列，没有则从腾讯财经补充
            if 'volume_ratio' not in df.columns or 'turnover_ratio' not in df.columns:
                df = _add_volume_and_turnover(df)
            return df
    except Exception as e:
        print(f"AkShare 获取失败，尝试新浪财经 API...")

    # 尝试 2: 新浪财经 API（需要列名映射）
    try:
        api = SinaStockAPI()
        df = api.get_all_a_shares()
        if df is not None and not df.empty:
            # 列名映射（英文->中文）
            column_map = {
                'symbol': '代码',
                'name': '名称',
                'current': '最新价',
                'change_percent': '涨跌幅',
                'change': '涨跌额',
                'volume': '成交量',
                'amount': '成交额',
                'open': '开盘',
                'close': '昨收',
                'high': '最高',
                'low': '最低',
            }
            # 只映射存在的列
            existing_cols = {k: v for k, v in column_map.items() if k in df.columns}
            if existing_cols:
                df = df.rename(columns=existing_cols)
            # 添加代码列（去掉市场前缀）
            if '代码' in df.columns:
                df['代码'] = df['代码'].str.replace('sh', '').replace('sz', '').replace('bj', '')

            # 从腾讯财经补充量比和换手率
            df = _add_volume_and_turnover(df)

        return df
    except Exception as e:
        print(f"获取实时行情失败：{e}")
        return None


def _add_volume_and_turnover(df: pd.DataFrame) -> pd.DataFrame:
    """
    从腾讯财经 API 获取量比和换手率数据并添加到 DataFrame

    Args:
        df: 包含代码列的 DataFrame

    Returns:
        DataFrame: 添加了量比和换手率的 DataFrame
    """
    try:
        # 只获取有代码的股票
        if '代码' not in df.columns:
            return df

        codes = df['代码'].dropna().unique().tolist()
        if not codes:
            return df

        # 从腾讯财经获取量比数据
        from src.data_sources.qq_source import TencentStockAPI
        qq_api = TencentStockAPI()

        # 分批获取（腾讯一次最多 50 只）
        all_qq_data = []
        batch_size = 50

        print(f"从腾讯财经补充量比数据（共{len(codes)}只股票）...")
        for i in range(0, min(len(codes), 500), batch_size):  # 限制最多 500 只，避免过慢
            batch = codes[i:i + batch_size]
            try:
                batch_df = qq_api.get_realtime(batch)
                if not batch_df.empty:
                    all_qq_data.append(batch_df)
            except Exception:
                continue

        if all_qq_data:
            qq_df = pd.concat(all_qq_data, ignore_index=True)

            # 只保留需要的列
            if not qq_df.empty:
                # 处理代码列（去掉市场前缀）
                qq_df['code_clean'] = qq_df['symbol'].str.replace('sh', '').str.replace('sz', '').str.replace('bj', '')

                # 合并量比数据
                result = pd.merge(
                    df,
                    qq_df[['code_clean', 'volume_ratio']],
                    left_on='代码',
                    right_on='code_clean',
                    how='left'
                )
                result = result.drop(columns=['code_clean'])

                # 确保列名统一
                if 'volume_ratio' in result.columns and '量比' not in result.columns:
                    result['量比'] = result['volume_ratio']

                # 计算换手率 = 成交量 / 流通股本 * 100
                # 腾讯的 volume 是股，需要知道流通股本才能计算换手率
                # 这里暂时用 0 填充，因为无法直接获取
                if 'turnover_ratio' not in result.columns and '换手率' not in result.columns:
                    result['换手率'] = 0.0

                return result

    except Exception as e:
        print(f"补充量比数据失败：{e}")

    # 失败时返回原数据，添加默认值
    if '量比' not in df.columns:
        df['量比'] = 0.0
    if '换手率' not in df.columns:
        df['换手率'] = 0.0

    return df


def get_stock_history(symbol: str, start_date: str = "20230101", end_date: str = None, period: str = "daily"):
    """
    获取个股历史 K 线数据

    Args:
        symbol: 股票代码，如 "000001" 或 "sh600519"
        start_date: 开始日期，格式 "YYYYMMDD"
        end_date: 结束日期，格式 "YYYYMMDD"，默认今天
        period: 周期 "daily"/"weekly"/"monthly"

    Returns:
        DataFrame: 包含日期、开盘、收盘、最高、最低、成交量等
    """
    try:
        # 处理股票代码格式
        if symbol.startswith("sh") or symbol.startswith("sz"):
            code = symbol[2:]
        else:
            code = symbol

        if end_date is None:
            end_date = datetime.now().strftime("%Y%m%d")

        df = ak.stock_zh_a_hist(
            symbol=code,
            period=period,
            start_date=start_date,
            end_date=end_date,
            adjust="qfq"  # 前复权
        )
        return df
    except Exception as e:
        print(f"获取历史数据失败 (symbol={symbol}): {e}")
        return None


def get_stock_minute(symbol: str, period: str = "5"):
    """
    获取个股分钟 K 线数据

    Args:
        symbol: 股票代码
        period: 分钟周期 "1"/"5"/"15"/"30"/"60"

    Returns:
        DataFrame: 分钟 K 线数据
    """
    try:
        if symbol.startswith("sh") or symbol.startswith("sz"):
            code = symbol[2:]
        else:
            code = symbol

        df = ak.stock_zh_a_hist_min_em(
            symbol=code,
            period=period
        )
        return df
    except Exception as e:
        print(f"获取分钟数据失败 (symbol={symbol}): {e}")
        return None


def get_lhb_detail(date: str = None):
    """
    获取龙虎榜数据

    Args:
        date: 日期，格式 "YYYY-MM-DD"，默认今天

    Returns:
        DataFrame: 龙虎榜明细数据
    """
    try:
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")

        df = ak.stock_lhb_detail_em(trade_date=date)
        return df
    except Exception as e:
        print(f"获取龙虎榜数据失败：{e}")
        return None


def get_lhb_today():
    """
    获取当日龙虎榜数据

    Returns:
        DataFrame: 龙虎榜数据
    """
    try:
        # 使用机构席位数据作为替代
        df = ak.stock_lhb_jgstatistic_em()
        return df
    except Exception as e:
        print(f"获取龙虎榜数据失败：{e}")
        return None


def get_individual_fund_flow(symbol: str = None):
    """
    获取个股资金流向数据

    Args:
        symbol: 股票代码，不传则获取全部

    Returns:
        DataFrame: 资金流向数据

    Note:
        AkShare 的 stock_individual_fund_flow 函数参数名为 stock 而非 symbol
        且需要指定 market 参数 (sh/sz/bj)
    """
    import time

    max_retries = 3
    for i in range(max_retries):
        try:
            if symbol:
                # 处理股票代码格式，判断市场
                if symbol.startswith("sh") or symbol.startswith("sz") or symbol.startswith("bj"):
                    market = symbol[:2]
                    code = symbol[2:]
                else:
                    # 根据代码前缀判断市场
                    if symbol.startswith("6"):
                        market = "sh"
                    elif symbol.startswith("0") or symbol.startswith("3"):
                        market = "sz"
                    elif symbol.startswith("4") or symbol.startswith("8"):
                        market = "bj"
                    else:
                        market = "sh"  # 默认
                    code = symbol

                # 修正参数名：symbol -> stock，并添加 market 参数
                df = ak.stock_individual_fund_flow(stock=code, market=market)
            else:
                # 获取个股资金流排名（备用接口）
                try:
                    df = ak.stock_fund_flow_individual(indicator="今日")
                except Exception:
                    # 如果备用接口失败，尝试原接口
                    df = ak.stock_individual_fund_flow_rank(indicator="今日")

            if df is not None and not df.empty:
                return df

        except Exception as e:
            error_msg = str(e)
            # 如果是代理问题，快速失败
            if "Proxy" in error_msg or "proxy" in error_msg:
                if i == 0:
                    print("  警告：检测到代理问题，跳过资金流向数据获取")
                break

            # 网络错误时重试
            if "Connection" in error_msg or "连接" in error_msg or "timeout" in error_msg.lower():
                if i < max_retries - 1:
                    print(f"  网络连接不稳定，{i+2}/{max_retries} 次重试...")
                    time.sleep(2)
                else:
                    print(f"  获取资金流向失败（网络问题）：{e}")
            elif i < max_retries - 1:
                time.sleep(1)
            else:
                print(f"  获取资金流向失败：{e}")

    return None


def get_concept_fund_flow():
    """
    获取概念板块资金流向

    Returns:
        DataFrame: 概念板块资金流排名

    Note:
        部分 AkShare 版本函数名已变更，尝试多个备选接口
    """
    # 尝试多个备选接口
    functions_to_try = [
        # 备选 1: 行业资金流
        lambda: ak.stock_fund_flow_industry(indicator="今日"),
        # 备选 2: 概念资金流（旧版）
        lambda: ak.stock_board_concept_fund_flow_em(),
    ]

    for func in functions_to_try:
        try:
            df = func()
            if df is not None and not df.empty:
                return df
        except Exception as e:
            continue

    print("获取概念/行业资金流向失败：所有接口均不可用")
    return None


def get_stock_info(symbol: str):
    """
    获取股票基本信息

    Args:
        symbol: 股票代码

    Returns:
        dict: 股票基本信息
    """
    try:
        df = ak.stock_individual_info_em(symbol=symbol)
        return df
    except Exception as e:
        print(f"获取股票信息失败 (symbol={symbol}): {e}")
        return None


if __name__ == "__main__":
    # 测试代码
    print("=" * 50)
    print("测试 AkShare API 封装")
    print("=" * 50)

    # 测试 1：获取全部 A 股实时行情
    print("\n[测试 1] 获取全部 A 股实时行情...")
    df = get_all_stocks_realtime()
    if df is not None:
        print(f"获取成功，共 {len(df)} 只股票")
        print(df.head(10).to_string())

    # 测试 2：获取个股历史数据
    print("\n[测试 2] 获取贵州茅台历史数据...")
    df = get_stock_history("600519", start_date="20250101")
    if df is not None:
        print(f"获取成功，共 {len(df)} 条记录")
        print(df.tail().to_string())

    # 测试 3：获取资金流向排名
    print("\n[测试 3] 获取今日资金流向排名...")
    df = get_individual_fund_flow()
    if df is not None:
        print(f"获取成功，共 {len(df)} 条记录")
        print(df.head(10).to_string())
