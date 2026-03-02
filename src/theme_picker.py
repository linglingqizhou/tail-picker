# -*- coding: utf-8 -*-
"""
题材热点选股器
综合技术面 + 题材面评分选股
"""

import pandas as pd
import numpy as np
import requests
import time
from typing import Dict, List, Optional
from datetime import datetime
from pathlib import Path


class ThemeStockPicker:
    """题材热点选股器"""

    # 板块 - 成分股映射
    THEME_COMPONENTS = {
        "人工智能": ["600519", "002594", "601360", "300750", "002230", "600845", "600570", "300059"],
        "芯片半导体": ["603986", "600584", "002371", "603019", "002156", "600460", "300623", "688981"],
        "新能源": ["300750", "002594", "002812", "601012", "600438", "002460", "603799", "300014"],
        "光伏": ["601012", "600438", "002460", "603799", "002056", "002865", "300316", "600732"],
        "锂电": ["300750", "002812", "603799", "002460", "002340", "300073", "603659", "002756"],
        "风电": ["601615", "600478", "002202", "600605", "002487", "603218", "600163", "300129"],
        "AI 算力": ["601360", "000977", "600498", "000066", "300394", "002897", "300502", "603019"],
        "5G": ["600498", "000066", "002594", "300394", "002897", "603220", "300628", "002796"],
        "机器人": ["002747", "002230", "300024", "002698", "603666", "300170", "600666", "002896"],
        "低空经济": ["000099", "002111", "600038", "600765", "002465", "300397", "603666", "002190"],
        "华为概念": ["002594", "300750", "002456", "002230", "600745", "000725", "600584", "300136"],
        "白酒": ["600519", "000858", "000568", "000799", "600809", "000596", "600779", "000860"],
        "券商": ["600030", "601688", "600837", "000776", "600028", "601318", "601398", "601901"],
        "医药": ["600276", "000538", "000661", "600085", "600436", "002317", "300122", "600521"],
        "煤炭": ["600546", "601088", "600188", "600737", "002128", "601699", "600348", "600997"],
    }

    # 龙头股映射
    LEADER_STOCKS = {
        "人工智能": "600519",  # 贵州茅台 (示例)
        "芯片半导体": "603986",  # 兆易创新
        "新能源": "300750",  # 宁德时代
        "AI 算力": "601360",  # 浪潮信息
        "低空经济": "000099",  # 中信海直
        "华为概念": "002594",  # 比亚迪
    }

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        })
        self.cache_dir = Path("stock_data/theme_cache")
        self.cache_dir.mkdir(exist_ok=True)

    def get_quotes(self, symbols: List[str]) -> pd.DataFrame:
        """
        使用腾讯 API 获取多只股票行情

        Args:
            symbols: 股票代码列表 (6 位数字)

        Returns:
            DataFrame: 行情数据
        """
        if not symbols:
            return pd.DataFrame()

        # 分批获取，每批 50 只
        all_quotes = []
        batch_size = 50

        for i in range(0, len(symbols), batch_size):
            batch = symbols[i:i+batch_size]
            symbol_list = ','.join(['sh'+s if s.startswith('6') else 'sz'+s for s in batch])
            url = f'http://qt.gtimg.cn/q={symbol_list}'

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
                    # 腾讯 API 数据格式：v_sh600519="1~ 贵州茅台~600519~1455.02~1466.21~..."
                    # 使用 ~ 分割
                    data = parts[1].split('~')
                    if len(data) < 5:
                        continue

                    try:
                        code = data[2] if len(data) > 2 else ''
                        name = data[1] if len(data) > 1 else ''
                        cur = float(data[3]) if data[3] else 0
                        pre_close = float(data[4]) if data[4] else 0
                        change = cur - pre_close
                        change_pct = (change / pre_close * 100) if pre_close > 0 else 0

                        # 成交量和成交额在后续位置
                        volume = float(data[6]) if len(data) > 6 and data[6] else 0
                        amount = float(data[7]) if len(data) > 7 and data[7] else 0

                        all_quotes.append({
                            '代码': code,
                            '名称': name,
                            '最新价': cur,
                            '涨跌额': change,
                            '涨跌幅': change_pct,
                            '成交量': volume,
                            '成交额': amount,
                        })
                    except (ValueError, IndexError) as e:
                        continue

                time.sleep(0.3)  # 避免请求过快

            except Exception as e:
                print(f"获取行情失败：{e}")
                continue

        return pd.DataFrame(all_quotes) if all_quotes else pd.DataFrame()

    def calculate_theme_heat(self, theme_name: str, quotes: pd.DataFrame) -> Dict:
        """
        计算板块热度评分

        评分维度:
        - 板块涨幅 (40 分): 成分股平均涨跌幅
        - 涨停家数 (20 分): 涨停股票数量
        - 上涨家数占比 (20 分): 上涨股票比例
        - 成交活跃度 (20 分): 成交额大小

        总分：100 分
        """
        if quotes.empty:
            return {'板块名称': theme_name, '热度评分': 0}

        result = {'板块名称': theme_name}

        # 1. 平均涨跌幅 (40 分)
        avg_change = quotes['涨跌幅'].mean() if '涨跌幅' in quotes.columns else 0
        result['平均涨幅'] = avg_change
        # +5% 以上满分，-5% 以下 0 分
        change_score = min(40, max(0, 20 + avg_change * 4))
        result['涨幅评分'] = change_score

        # 2. 涨停家数 (20 分)
        zt_count = len(quotes[quotes['涨跌幅'] >= 9.8]) if '涨跌幅' in quotes.columns else 0
        result['涨停家数'] = zt_count
        zt_score = min(20, zt_count * 5)  # 每只涨停 5 分，最多 4 只满分
        result['涨停评分'] = zt_score

        # 3. 上涨家数占比 (20 分)
        if '涨跌幅' in quotes.columns:
            up_count = len(quotes[quotes['涨跌幅'] > 0])
            up_ratio = up_count / len(quotes)
            result['上涨家数'] = up_count
            result['下跌家数'] = len(quotes) - up_count
            up_score = up_ratio * 20
            result['上涨评分'] = up_score
        else:
            up_score = 10

        # 4. 成交活跃度 (20 分)
        if '成交额' in quotes.columns:
            total_amount = quotes['成交额'].sum() / 1e8  # 转换为亿
            # 成交额>100 亿满分
            vol_score = min(20, np.log1p(total_amount) * 4)
            result['成交额 (亿)'] = total_amount
            result['活跃度评分'] = vol_score
        else:
            vol_score = 10

        # 总分
        total_score = change_score + zt_score + up_score + vol_score
        result['热度评分'] = total_score

        return result

    def get_all_theme_ranking(self) -> pd.DataFrame:
        """获取所有板块热度排行"""
        results = []

        for theme_name, components in self.THEME_COMPONENTS.items():
            print(f"分析 {theme_name}...", end="\r")

            quotes = self.get_quotes(components)
            if not quotes.empty:
                heat_data = self.calculate_theme_heat(theme_name, quotes)
                results.append(heat_data)

            time.sleep(0.3)

        if not results:
            return pd.DataFrame()

        df = pd.DataFrame(results)
        df = df.sort_values('热度评分', ascending=False)
        return df.reset_index(drop=True)

    def pick_stocks_by_theme(self, theme_name: str, technical_config: Dict = None) -> pd.DataFrame:
        """
        根据题材选股（技术面 + 题材面）

        Args:
            theme_name: 板块名称
            technical_config: 技术面筛选配置

        Returns:
            DataFrame: 选股结果
        """
        components = self.THEME_COMPONENTS.get(theme_name, [])
        if not components:
            return pd.DataFrame()

        # 获取成分股行情
        quotes = self.get_quotes(components)
        if quotes.empty:
            return pd.DataFrame()

        # 技术面筛选
        df = self._technical_filter(quotes, technical_config)

        # 计算综合评分
        df = self._calculate_composite_score(df, theme_name)

        # 排序
        if not df.empty and '综合评分' in df.columns:
            df = df.sort_values('综合评分', ascending=False)

        return df

    def _technical_filter(self, df: pd.DataFrame, config: Dict = None) -> pd.DataFrame:
        """技术面筛选"""
        result = df.copy()

        # 默认配置
        if config is None:
            config = {
                'min_change': 3.0,      # 最小涨幅
                'max_change': 8.5,      # 最大涨幅
                'min_volume': 1e7,      # 最小成交量
                'exclude_st': True,     # 排除 ST
            }

        # 涨幅筛选
        if 'min_change' in config and '涨跌幅' in result.columns:
            result = result[result['涨跌幅'] >= config['min_change']]
        if 'max_change' in config and '涨跌幅' in result.columns:
            result = result[result['涨跌幅'] <= config['max_change']]

        # 排除 ST
        if config.get('exclude_st', True) and '名称' in result.columns:
            result = result[~result['名称'].str.contains('ST', na=False, regex=False)]

        return result

    def _calculate_composite_score(self, df: pd.DataFrame, theme_name: str) -> pd.DataFrame:
        """
        计算综合评分 (100 分制)

        - 技术面评分 (50 分)
        - 题材热度评分 (30 分)
        - 个股地位评分 (20 分)
        """
        result = df.copy()
        result['综合评分'] = 0.0

        # 1. 技术面评分 (50 分)
        # 涨幅评分 (25 分): 越接近 5.5% 分越高
        if '涨跌幅' in result.columns:
            tech_score = 25 - abs(result['涨跌幅'] - 5.5) * 3
            tech_score = tech_score.clip(0, 25)
            result['技术评分'] = tech_score

        # 2. 题材热度评分 (30 分)
        # 计算板块热度
        theme_heat = self.calculate_theme_heat(theme_name, df)
        theme_score = theme_heat.get('热度评分', 0) / 100 * 30
        result['题材评分'] = theme_score

        # 3. 个股地位评分 (20 分)
        # 龙头股额外加分
        leader = self.LEADER_STOCKS.get(theme_name, '')
        if '代码' in result.columns:
            result['地位评分'] = result['代码'].apply(
                lambda x: 20 if x == leader else 10
            )

        # 综合评分
        if '技术评分' in result.columns:
            result['综合评分'] += result['技术评分']
        if '题材评分' in result.columns:
            result['综合评分'] += result['题材评分']
        if '地位评分' in result.columns:
            result['综合评分'] += result['地位评分']

        return result

    def get_hot_themes_daily(self) -> pd.DataFrame:
        """获取每日热门板块"""
        print("正在分析板块热度...")
        df = self.get_all_theme_ranking()

        if not df.empty:
            # 保存结果
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filepath = self.cache_dir / f'theme_ranking_{timestamp}.csv'
            df.to_csv(filepath, index=False, encoding='utf-8-sig')
            print(f"\n结果已保存：{filepath}")

        return df


# 命令行工具
if __name__ == "__main__":
    import sys

    print("=" * 60)
    print("题材热点选股器")
    print("=" * 60)

    picker = ThemeStockPicker()

    if len(sys.argv) > 1:
        # 命令行参数模式
        command = sys.argv[1]

        if command == 'rank':
            # 板块热度排行
            print("\n【板块热度 TOP10】")
            df = picker.get_hot_themes_daily()
            if not df.empty:
                cols = ['板块名称', '热度评分', '平均涨幅', '涨停家数']
                available_cols = [c for c in cols if c in df.columns]
                print(df[available_cols].head(10).to_string(index=False))

        elif command == 'pick' and len(sys.argv) > 2:
            # 题材选股
            theme = sys.argv[2]
            print(f"\n【{theme}选股】")
            df = picker.pick_stocks_by_theme(theme)
            if not df.empty:
                print(df[['代码', '名称', '涨跌幅', '综合评分']].head(10).to_string(index=False))
            else:
                print("未找到符合条件的股票")

    else:
        # 交互模式
        print("\n可用命令:")
        print("  python theme_picker.py rank          - 查看板块热度排行")
        print("  python theme_picker.py pick 板块名    - 查看某板块选股")
        print("\n示例:")
        print("  python theme_picker.py pick 人工智能")

        # 默认显示板块热度
        print("\n【快速预览 - 板块热度 TOP10】")
        df = picker.get_hot_themes_daily()
        if not df.empty:
            cols = ['板块名称', '热度评分', '平均涨幅', '涨停家数']
            available_cols = [c for c in cols if c in df.columns]
            print(df[available_cols].head(10).to_string(index=False))