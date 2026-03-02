# -*- coding: utf-8 -*-
"""
板块热度监控引擎
使用本地缓存数据 + 实时行情计算板块热度
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import json
from pathlib import Path


class ThemeHeatEngine:
    """板块热度评分引擎"""

    # 板块 - 成分股映射 (本地缓存，常见热门板块)
    THEME_COMPONENTS = {
        "人工智能": ["600519", "002594", "601360", "300750", "002230", "600845", "600570", "300059"],
        "芯片半导体": ["603986", "600584", "002371", "603019", "002156", "600460", "300623", "688981"],
        "新能源": ["300750", "002594", "002812", "601012", "600438", "002460", "603799", "300014"],
        "光伏": ["601012", "600438", "002460", "603799", "002056", "002865", "300316", "600732"],
        "锂电": ["300750", "002812", "603799", "002460", "600478", "002340", "300073", "603659"],
        "风电": ["601615", "600478", "002202", "600605", "002487", "603218", "600163", "300129"],
        "核电": ["601985", "600875", "002438", "601611", "600765", "002665", "601226", "300185"],
        "AI 算力": ["601360", "000977", "600498", "000066", "300394", "002897", "300502", "603019"],
        "5G": ["600498", "000066", "002594", "300394", "002897", "603220", "300628", "002796"],
        "机器人": ["002747", "002230", "300024", "002698", "603666", "300170", "600666", "002896"],
        "低空经济": ["000099", "002111", "600038", "600765", "002465", "300397", "603666", "002190"],
        "华为概念": ["002594", "300750", "002456", "002230", "600745", "000725", "600584", "300136"],
        "白酒": ["600519", "000858", "000568", "000799", "600809", "000596", "600779", "000860"],
        "医药": ["600276", "000538", "000661", "600085", "600436", "002317", "300122", "600521"],
        "券商": ["600030", "601688", "600837", "000776", "600028", "601318", "600519", "601398"],
        "银行": ["601398", "601288", "600519", "601988", "601939", "600036", "601166", "600030"],
        "房地产": ["000002", "001979", "600048", "000627", "000961", "000415", "600606", "000069"],
        "汽车": ["002594", "002111", "000625", "601127", "000030", "002415", "600733", "300750"],
        "军工": ["002111", "600765", "600150", "600316", "002013", "002179", "600893", "002297"],
        "煤炭": ["600546", "601088", "600188", "600737", "002128", "601699", "600028", "600348"],
        "石油": ["601857", "600028", "000725", "600546", "002128", "601699", "000625", "600737"],
        "钢铁": ["600519", "000898", "000709", "600019", "000778", "600282", "600307", "002110"],
        "有色": ["000898", "600547", "000426", "600489", "000603", "600331", "600497", "600988"],
        "化工": ["600309", "600028", "600546", "002128", "600988", "000426", "600489", "600331", "600075", "600470", "600152"],
        "消费": ["600519", "000858", "000568", "600809", "000596", "002304", "002291", "600779"],
        "科技": ["601360", "002594", "000066", "600498", "300394", "002897", "603019", "300623"],
        "电力": ["600098", "600795", "600642", "600578", "600131", "600886", "000027", "600011"],
        "建材": ["600585", "600801", "600449", "000401", "000789", "600720", "600668", "600219"],
        "稀土": ["600111", "000897", "600259", "000603", "600392", "600117", "600490", "002645"],
    }

    # 板块权重 (龙头股权重更高)
    THEME_WEIGHTS = {
        "人工智能": {"600519": 1.5, "002594": 1.3, "601360": 1.2},
        "芯片半导体": {"603986": 1.5, "600584": 1.3, "002371": 1.2},
        "新能源": {"300750": 1.5, "002594": 1.3, "002812": 1.2},
        "光伏": {"601012": 1.5, "600438": 1.3, "002460": 1.2},
        "锂电": {"300750": 1.5, "002812": 1.3, "603799": 1.2},
        "AI 算力": {"601360": 1.5, "000977": 1.3, "600498": 1.2},
        "白酒": {"600519": 1.5, "000858": 1.3, "000568": 1.2},
        "券商": {"600030": 1.5, "601688": 1.3, "600837": 1.2},
        "银行": {"601398": 1.5, "601288": 1.3, "600519": 1.2},
        "低空经济": {"000099": 1.5, "002111": 1.3, "600038": 1.2},
    }

    def __init__(self, data_source=None):
        """
        Args:
            data_source: 数据源对象，需要有 get_theme_board() 和 get_market_snapshot() 方法
                        如 EastmoneyThemeCrawler 或 TencentThemeCrawler
        """
        self.data_source = data_source
        self.cache_dir = Path("stock_data/theme_cache")
        self.cache_dir.mkdir(exist_ok=True)

    def get_stock_quotes(self, symbols: List[str]) -> pd.DataFrame:
        """
        获取多只股票的实时行情

        Args:
            symbols: 股票代码列表

        Returns:
            DataFrame: 行情数据
        """
        if not symbols:
            return pd.DataFrame()

        # 尝试从数据源获取
        if self.data_source and hasattr(self.data_source, 'get_market_snapshot'):
            results = []
            for symbol in symbols:
                try:
                    quote = self.data_source.get_market_snapshot(symbol)
                    if quote:
                        results.append(quote)
                except:
                    continue
            if results:
                return pd.DataFrame(results)

        # 如果没有数据源，返回空
        return pd.DataFrame()

    def calculate_theme_heat(self, theme_name: str, component_quotes: pd.DataFrame) -> Dict:
        """
        计算板块热度评分

        评分维度:
        - 板块涨幅 (40 分): 成分股平均涨跌幅
        - 资金流入 (30 分): 主力净流入
        - 涨停家数 (20 分): 涨停股票数量
        - 成交活跃度 (10 分): 成交量/换手率

        Args:
            theme_name: 板块名称
            component_quotes: 成分股行情数据

        Returns:
            dict: 板块热度评分结果
        """
        if component_quotes.empty:
            return {
                '板块名称': theme_name,
                '热度评分': 0,
                '平均涨幅': 0,
                '涨停家数': 0,
                '上涨家数': 0,
                '下跌家数': 0,
            }

        # 1. 计算平均涨跌幅 (40 分)
        avg_change = component_quotes['涨跌幅'].mean() if '涨跌幅' in component_quotes.columns else 0
        change_score = min(40, max(0, 20 + avg_change * 4))  # +5% 得满分

        # 2. 涨停家数 (20 分)
        zt_count = len(component_quotes[component_quotes['涨跌幅'] >= 9.8]) if '涨跌幅' in component_quotes.columns else 0
        zt_score = min(20, zt_count * 4)  # 每只涨停 4 分

        # 3. 上涨家数占比 (10 分)
        if '涨跌幅' in component_quotes.columns:
            up_count = len(component_quotes[component_quotes['涨跌幅'] > 0])
            up_ratio = up_count / len(component_quotes)
            up_score = up_ratio * 10
        else:
            up_score = 5

        # 4. 成交活跃度 (10 分) - 基于成交量
        if '成交量' in component_quotes.columns:
            total_volume = component_quotes['成交量'].sum()
            vol_score = min(10, np.log1p(total_volume) / 5)  # 对数评分
        else:
            vol_score = 5

        # 总分
        total_score = change_score + zt_score + up_score + vol_score

        return {
            '板块名称': theme_name,
            '成分股数量': len(component_quotes),
            '平均涨幅': avg_change,
            '涨停家数': zt_count,
            '上涨家数': up_count if '涨跌幅' in component_quotes.columns else 0,
            '下跌家数': len(component_quotes) - up_count if '涨跌幅' in component_quotes.columns else 0,
            '涨幅评分': change_score,
            '涨停评分': zt_score,
            '上涨评分': up_score,
            '活跃度评分': vol_score,
            '热度评分': total_score,
        }

    def get_all_theme_heat_ranking(self) -> pd.DataFrame:
        """
        获取所有板块热度排行

        Returns:
            DataFrame: 板块热度排行
        """
        results = []

        # 如果数据源有 get_theme_board 方法，直接获取真实板块数据
        if self.data_source and hasattr(self.data_source, 'get_theme_board'):
            try:
                board_df = self.data_source.get_theme_board("concept")
                if not board_df.empty and '板块代码' in board_df.columns and '板块名称' in board_df.columns:
                    # 使用真实板块数据
                    for _, row in board_df.head(50).iterrows():  # 取前 50 个板块
                        theme_name = row['板块名称']
                        theme_code = row['板块代码']
                        print(f"计算 {theme_name} 热度...", end="\r")

                        # 获取成分股
                        components_df = self.data_source.get_theme_components(theme_code)
                        if not components_df.empty and '涨跌幅' in components_df.columns:
                            heat_data = self.calculate_theme_heat(theme_name, components_df)
                            heat_data['板块代码'] = theme_code
                            results.append(heat_data)
            except Exception as e:
                print(f"获取实时板块数据失败：{e}，使用本地缓存")

        # 如果上面的实时获取失败或没有数据，使用本地缓存
        if not results:
            for theme_name, components in self.THEME_COMPONENTS.items():
                print(f"计算 {theme_name} 热度...", end="\r")

                # 获取成分股行情
                quotes = self.get_stock_quotes(components)

                if not quotes.empty:
                    heat_data = self.calculate_theme_heat(theme_name, quotes)
                    results.append(heat_data)

        if not results:
            return pd.DataFrame()

        df = pd.DataFrame(results)
        df = df.sort_values('热度评分', ascending=False)
        return df.reset_index(drop=True)

    def get_hot_themes(self, top_n: int = 10) -> pd.DataFrame:
        """
        获取热门板块 TOP N

        Args:
            top_n: 返回前 N 个板块

        Returns:
            DataFrame: 热门板块排行
        """
        df = self.get_all_theme_heat_ranking()
        if df.empty:
            return pd.DataFrame()
        return df.head(top_n)

    def get_hot_themes_with_components(self, top_n: int = 10) -> tuple:
        """
        获取热门板块 TOP N 及其成分股

        Args:
            top_n: 返回前 N 个板块

        Returns:
            tuple: (板块热度 DataFrame, 成分股 dict)
        """
        df = self.get_all_theme_heat_ranking()
        if df.empty:
            return pd.DataFrame(), {}

        top_themes = df.head(top_n)['板块名称'].tolist()
        components_dict = {}

        # 如果有板块代码，使用实时成分股数据
        if '板块代码' in df.columns and self.data_source and hasattr(self.data_source, 'get_theme_components'):
            for theme_name in top_themes:
                theme_row = df[df['板块名称'] == theme_name].iloc[0]
                if '板块代码' in theme_row:
                    theme_code = theme_row['板块代码']
                    components_df = self.data_source.get_theme_components(theme_code)
                    if not components_df.empty:
                        components_dict[theme_name] = components_df['代码'].tolist()
                    else:
                        # 回退到本地缓存
                        components_dict[theme_name] = self.THEME_COMPONENTS.get(theme_name, [])
                else:
                    components_dict[theme_name] = self.THEME_COMPONENTS.get(theme_name, [])
        else:
            # 使用本地缓存
            for theme in top_themes:
                components_dict[theme] = self.get_theme_holdings(theme)

        return df.head(top_n), components_dict

    def get_theme_holdings(self, theme_name: str) -> List[str]:
        """
        获取板块成分股列表

        Args:
            theme_name: 板块名称

        Returns:
            List[str]: 成分股代码列表
        """
        return self.THEME_COMPONENTS.get(theme_name, [])

    def is_theme_hot(self, theme_name: str, threshold: float = 60) -> bool:
        """
        判断板块是否热门

        Args:
            theme_name: 板块名称
            threshold: 热度阈值

        Returns:
            bool: 是否热门
        """
        quotes = self.get_stock_quotes(self.get_theme_holdings(theme_name))
        if quotes.empty:
            return False

        heat_data = self.calculate_theme_heat(theme_name, quotes)
        return heat_data['热度评分'] >= threshold

    def save_cache(self, data: Dict, filename: str):
        """保存缓存数据"""
        filepath = self.cache_dir / filename
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def load_cache(self, filename: str) -> Optional[Dict]:
        """加载缓存数据"""
        filepath = self.cache_dir / filename
        if filepath.exists():
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None


# 测试
if __name__ == "__main__":
    print("=" * 60)
    print("板块热度监控引擎测试")
    print("=" * 60)

    # 尝试使用数据源
    try:
        from src.data_sources.eastmoney_themes import EastmoneyThemeCrawler
        crawler = EastmoneyThemeCrawler()
        engine = ThemeHeatEngine(data_source=crawler)
    except Exception as e:
        print(f"数据源初始化失败：{e}")
        print("使用空数据源测试基本功能")
        engine = ThemeHeatEngine()

    # 测试获取板块热度
    print("\n【获取热门板块 TOP10】")
    hot_df = engine.get_hot_themes(10)
    if not hot_df.empty:
        print(hot_df[['板块名称', '热度评分', '平均涨幅', '涨停家数']].to_string(index=False))
    else:
        print("无法获取实时数据，请检查网络连接")

    # 测试获取板块成分股
    print("\n【人工智能板块成分股】")
    components = engine.get_theme_holdings("人工智能")
    print(f"共 {len(components)} 只：{components}")
