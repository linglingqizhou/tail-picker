# -*- coding: utf-8 -*-
"""
东方财富题材板块数据爬虫
获取板块行情、成分股、资金流向等数据
"""

import requests
import pandas as pd
import time
from typing import Dict, List, Optional
from datetime import datetime


class EastmoneyThemeCrawler:
    """东方财富题材数据爬虫"""

    # 东方财富板块行情 API
    THEME_URL = "http://77.push2.eastmoney.com/api/qt/clist/get"

    # 板块成分股 API
    COMPONENTS_URL = "http://push2.eastmoney.com/api/qt/clist/get"

    # 财联社电报 API
    TELEGRAPH_URL = "https://api.cls.cn/v1/roll/get_roll_list"

    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Referer': 'http://quote.eastmoney.com/',
    }

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)

    def get_theme_board(self, board_type: str = "concept", max_retries: int = 3) -> pd.DataFrame:
        """
        获取板块行情数据

        Args:
            board_type: 板块类型
                - "concept": 概念板块
                - "industry": 行业板块
                - "area": 地区板块
                - "hk": 港股板块
            max_retries: 最大重试次数

        Returns:
            DataFrame: 板块行情数据
        """
        # 板块类型映射 (修复格式：m:90 t:2)
        board_map = {
            "concept": "m:90 t:2",      # 概念板块
            "industry": "m:90 t:1",     # 行业板块
            "area": "m:90 t:3",         # 地区板块
        }

        for attempt in range(max_retries):
            pn = 1
            all_data = []

            try:
                while True:
                    params = {
                        'pn': pn,
                        'pz': '50',
                        'po': '1',
                        'np': '1',
                        'ut': 'bd1d9ddb04089700cf9c27f6f7426281',
                        'fltt': '2',
                        'invt': '2',
                        'fid': 'f3',
                        'fs': board_map.get(board_type, "m:90 t:2"),
                        'fields': 'f12,f13,f14,f2,f3,f4,f5,f6,f15,f16,f17,f18,f20,f21,f35,f36,f37,f38',
                        '_': str(int(time.time() * 1000))
                    }

                    resp = self.session.get(self.THEME_URL, params=params, timeout=15)
                    resp.encoding = 'utf-8'
                    data = resp.json()

                    if data.get('data') and data['data'].get('diff'):
                        all_data.extend(data['data']['diff'])

                        # 如果返回数据少于 50 条，说明已经到最后一页
                        if len(data['data']['diff']) < 50:
                            break
                        pn += 1
                    else:
                        break

                if all_data:
                    break  # 成功获取数据，退出重试循环

            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"获取板块数据失败 (第{attempt+1}次重试): {e}")
                    time.sleep(1)  # 等待 1 秒后重试
                else:
                    print(f"获取板块数据失败 (已重试{max_retries}次): {e}")

        if not all_data:
            return pd.DataFrame()

        df = pd.DataFrame(all_data)

        # 重命名列
        column_map = {
            'f12': '板块代码',
            'f13': '交易所',
            'f14': '板块名称',
            'f2': '最新价',
            'f3': '涨跌幅',
            'f4': '涨跌额',
            'f5': '成交量',
            'f6': '成交额',
            'f15': '最高价',
            'f16': '最低价',
            'f17': '开盘价',
            'f18': '昨收价',
            'f20': '总市值',
            'f21': '流通市值',
            'f35': '主力净流入',
            'f36': '主力净流入率',
            'f37': '超大单净流入',
            'f38': '大单净流入',
        }

        # 只保留存在的列
        existing_cols = [col for col in column_map.keys() if col in df.columns]
        df = df.rename(columns=column_map)
        return df[[column_map[c] for c in existing_cols]]

    def get_theme_components(self, theme_code: str) -> pd.DataFrame:
        """
        获取板块成分股

        Args:
            theme_code: 板块代码 (如 BK0588)

        Returns:
            DataFrame: 成分股列表
        """
        params = {
            'pn': '1',
            'pz': '500',  # 最多 500 只
            'po': '1',
            'np': '1',
            'ut': 'bd1d9ddb04089700cf9c27f6f7426281',
            'fltt': '2',
            'invt': '2',
            'fid': 'f3',
            'fs': f'b:{theme_code}',
            'fields': 'f12,f13,f14,f2,f3,f4,f5,f6,f128',
            '_': str(int(time.time() * 1000))
        }

        try:
            resp = self.session.get(self.COMPONENTS_URL, params=params, timeout=10)
            data = resp.json()

            if data.get('data') and data['data'].get('diff'):
                df = pd.DataFrame(data['data']['diff'])

                # 重命名
                df = df.rename(columns={
                    'f12': '代码',
                    'f13': '交易所',
                    'f14': '名称',
                    'f2': '最新价',
                    'f3': '涨跌幅',
                    'f4': '涨跌额',
                    'f5': '成交量',
                    'f6': '成交额',
                    'f128': '换手率',
                })

                return df[['代码', '名称', '最新价', '涨跌幅', '成交量', '成交额', '换手率']]

        except Exception as e:
            print(f"获取成分股失败：{e}")

        return pd.DataFrame()

    def get_telegraph_news(self, limit: int = 50) -> pd.DataFrame:
        """
        获取财联社电报快讯

        Args:
            limit: 获取数量

        Returns:
            DataFrame: 新闻列表
        """
        params = {
            'app': 'cailianpress',
            'category': 'roll',
            'last_time': str(int(time.time())),
            'limit': str(limit),
            'os': 'web',
            'sv': '7.7.7',
        }

        headers = {
            'User-Agent': 'Mozilla/5.0',
            'Referer': 'https://www.cls.cn/',
        }

        try:
            resp = self.session.get(self.TELEGRAPH_URL, params=params, headers=headers, timeout=10)
            data = resp.json()

            if data.get('data') and data['data'].get('roll_data'):
                news_list = data['data']['roll_data']

                result = []
                for news in news_list:
                    result.append({
                        '时间': datetime.fromtimestamp(news['ctime']),
                        '标题': news.get('title', ''),
                        '内容': news.get('brief', ''),
                        '链接': f"https://www.cls.cn/detail/{news['id']}",
                        '题材标签': news.get('tag_list', []),
                    })

                return pd.DataFrame(result)

        except Exception as e:
            print(f"获取财联社新闻失败：{e}")

        return pd.DataFrame()

    def get_hot_themes_ranking(self, top_n: int = 20) -> pd.DataFrame:
        """
        获取热门板块排行（综合评分）

        Args:
            top_n: 返回前 N 个板块

        Returns:
            DataFrame: 热门板块排行
        """
        df = self.get_theme_board("concept")

        if df.empty:
            return pd.DataFrame()

        # 计算热度评分
        # 评分 = 涨跌幅*40% + 主力流入率*30% + 量比*20% + 涨停家数*10%
        df_norm = df.copy()

        # 归一化处理
        for col in ['涨跌幅', '主力净流入率']:
            if col in df_norm.columns:
                min_val = df_norm[col].min()
                max_val = df_norm[col].max()
                if max_val > min_val:
                    df_norm[f'{col}_norm'] = (df_norm[col] - min_val) / (max_val - min_val)
                else:
                    df_norm[f'{col}_norm'] = 0.5

        # 计算综合评分
        df_norm['热度评分'] = (
            df_norm.get('涨跌幅_norm', pd.Series([0]*len(df_norm))) * 40 +
            df_norm.get('主力净流入率_norm', pd.Series([0]*len(df_norm))) * 30 +
            50  # 基础分
        )

        # 排序
        df_norm = df_norm.sort_values('热度评分', ascending=False)

        return df_norm.head(top_n)[['板块代码', '板块名称', '最新价', '涨跌幅', '主力净流入', '主力净流入率', '热度评分']]

    def get_theme_knowledge(self, theme_name: str) -> Dict:
        """
        获取板块百科信息（成分股、龙头股等）

        Args:
            theme_name: 板块名称

        Returns:
            dict: 板块信息
        """
        # 这个需要爬取网页，简化版本先返回空
        return {
            '板块名称': theme_name,
            '龙头股': [],
            '成分股数量': 0,
            '简介': '',
        }


# 测试
if __name__ == "__main__":
    crawler = EastmoneyThemeCrawler()

    print("=" * 60)
    print("东方财富题材板块数据测试")
    print("=" * 60)

    # 测试 1: 获取概念板块行情
    print("\n【测试 1】获取概念板块行情...")
    df = crawler.get_theme_board("concept")
    if not df.empty:
        print(f"获取到 {len(df)} 个概念板块")
        print(df[['板块名称', '最新价', '涨跌幅', '主力净流入']].head(10))

    # 测试 2: 获取热门板块排行
    print("\n【测试 2】获取热门板块 TOP10...")
    hot_df = crawler.get_hot_themes_ranking(10)
    if not hot_df.empty:
        print(hot_df[['板块名称', '涨跌幅', '热度评分']])

    # 测试 3: 获取财联社新闻
    print("\n【测试 3】获取财联社快讯...")
    news_df = crawler.get_telegraph_news(10)
    if not news_df.empty:
        print(news_df[['时间', '标题']].head(5))

    print("\n测试完成!")
