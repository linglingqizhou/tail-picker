# -*- coding: utf-8 -*-
"""
财经新闻快讯推送模块
实时监控重要题材新闻并推送
"""

import requests
import pandas as pd
import time
from typing import Dict, List, Optional, Callable
from datetime import datetime, timedelta
from pathlib import Path
import json
import threading


class NewsMonitor:
    """财经新闻监控器"""

    # 重要题材关键词
    THEME_KEYWORDS = {
        "低空经济": ["低空经济", "飞行汽车", "eVTOL", "通用航空", "无人机物流"],
        "AI 算力": ["AI 算力", "人工智能", "大模型", "GPU", "算力芯片", "HBM"],
        "芯片半导体": ["芯片", "半导体", "光刻机", "先进封装", "HBM", "碳化硅"],
        "新能源": ["新能源", "锂电池", "固态电池", "氢能", "储能"],
        "5G/6G": ["5G", "6G", "通信", "卫星互联网", "星链"],
        "机器人": ["机器人", "人形机器人", "减速器", "伺服电机", "AI 机器人"],
        "华为概念": ["华为", "鸿蒙", "华为手机", "华为汽车", "昇腾"],
        "券商": ["券商", "证券", "牛市", "IPO", "注册制"],
    }

    # 财联社 API
    TELEGRAPH_URL = "https://api.cls.cn/v1/roll/get_roll_list"

    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Referer': 'https://www.cls.cn/',
    }

    def __init__(self, cache_dir: str = "stock_data/news_cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)
        self.last_news_time = 0
        self.news_callback: Optional[Callable] = None

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

        try:
            resp = self.session.get(self.TELEGRAPH_URL, params=params, timeout=10)
            data = resp.json()

            if data.get('data') and data['data'].get('roll_data'):
                news_list = data['data']['roll_data']
                result = []

                for news in news_list:
                    # 提取关键词匹配的题材
                    content = news.get('brief', '') + ' ' + news.get('title', '')
                    matched_themes = self._match_themes(content)

                    result.append({
                        '时间': datetime.fromtimestamp(news['ctime']),
                        '标题': news.get('name', ''),
                        '内容': news.get('brief', ''),
                        '链接': f"https://www.cls.cn/detail/{news['id']}",
                        '题材标签': matched_themes,
                        '重要度': len(matched_themes),  # 匹配到的题材数量
                    })

                return pd.DataFrame(result)

        except Exception as e:
            print(f"获取财联社新闻失败：{e}")

        return pd.DataFrame()

    def _match_themes(self, text: str) -> List[str]:
        """
        匹配新闻内容中的题材关键词

        Args:
            text: 新闻文本

        Returns:
            List[str]: 匹配的题材列表
        """
        matched = []
        for theme, keywords in self.THEME_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text:
                    if theme not in matched:
                        matched.append(theme)
                    break
        return matched

    def get_latest_news(self, limit: int = 20) -> pd.DataFrame:
        """
        获取最新新闻（去重）

        Args:
            limit: 返回数量

        Returns:
            DataFrame: 新闻列表
        """
        df = self.get_telegraph_news(limit * 2)  # 多获取一些用于过滤

        if df.empty:
            return pd.DataFrame()

        # 只保留有题材标签的新闻
        df_with_tags = df[df['重要度'] > 0]

        # 按重要度排序
        df_with_tags = df_with_tags.sort_values('重要度', ascending=False)

        return df_with_tags.head(limit)

    def save_news(self, df: pd.DataFrame, filename: str = None):
        """保存新闻到文件"""
        if df.empty:
            return

        if filename is None:
            filename = f"news_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

        filepath = self.cache_dir / filename
        df.to_csv(filepath, index=False, encoding='utf-8-sig')
        print(f"新闻已保存：{filepath}")

    def load_cached_news(self, date: str = None) -> pd.DataFrame:
        """加载缓存的新闻数据"""
        if date is None:
            date = datetime.now().strftime('%Y%m%d')

        pattern = f"news_{date}*.csv"
        files = list(self.cache_dir.glob(pattern))

        if files:
            latest = max(files, key=lambda p: p.stat().st_mtime)
            return pd.read_csv(latest, encoding='utf-8-sig')

        return pd.DataFrame()

    def start_monitoring(self, interval: int = 60, callback: Callable = None):
        """
        开始监控新闻

        Args:
            interval: 刷新间隔 (秒)
            callback: 发现重要新闻时的回调函数
        """
        self.news_callback = callback
        print(f"开始监控财经新闻，刷新间隔：{interval}秒")

        def monitor_loop():
            last_ids = set()

            while True:
                try:
                    df = self.get_telegraph_news(20)

                    if not df.empty:
                        for _, row in df.iterrows():
                            news_id = row.get('链接', '')
                            if news_id and news_id not in last_ids:
                                last_ids.add(news_id)

                                # 如果有重要题材，触发回调
                                if row['重要度'] >= 2 and self.news_callback:
                                    self.news_callback(row)

                    time.sleep(interval)

                except Exception as e:
                    print(f"监控出错：{e}")
                    time.sleep(interval)

        thread = threading.Thread(target=monitor_loop, daemon=True)
        thread.start()


class NewsPusher:
    """新闻推送器"""

    def __init__(self, serverchan_key: str = None):
        """
        Args:
            serverchan_key: Server 酱 SCKEY，用于微信推送
        """
        self.serverchan_key = serverchan_key
        self.push_history = []

    def push_serverchan(self, title: str, content: str) -> bool:
        """
        使用 Server 酱推送微信消息

        Args:
            title: 标题
            content: 内容

        Returns:
            bool: 是否成功
        """
        if not self.serverchan_key:
            print("未配置 Server 酱 SCKEY")
            return False

        url = f"https://sctapi.ftqq.com/{self.serverchan_key}.send"

        try:
            data = {
                'text': title,
                'desp': content
            }
            resp = requests.post(url, data=data, timeout=10)
            result = resp.json()

            if result.get('code') == 0:
                print(f"推送成功：{title}")
                return True
            else:
                print(f"推送失败：{result.get('message')}")
                return False

        except Exception as e:
            print(f"推送出错：{e}")
            return False

    def push_news(self, news_row: Dict) -> bool:
        """
        推送单条新闻

        Args:
            news_row: 新闻数据

        Returns:
            bool: 是否成功
        """
        title = f"🔥 重要题材提醒 - {', '.join(news_row.get('题材标签', []))}"

        content = f"""
**{news_row.get('标题', '')}**

{news_row.get('内容', '')}

时间：{news_row.get('时间', '')}
链接：{news_row.get('链接', '')}
"""

        return self.push_serverchan(title, content)


# 命令行工具
if __name__ == "__main__":
    print("=" * 60)
    print("财经新闻快讯监控")
    print("=" * 60)

    monitor = NewsMonitor()

    # 获取最新新闻
    print("\n获取最新财经新闻...")
    df = monitor.get_latest_news(20)

    if not df.empty:
        print(f"\n获取到 {len(df)} 条重要新闻:\n")

        for _, row in df.head(10).iterrows():
            tags = ', '.join(row['题材标签']) if row['题材标签'] else '无'
            print(f"[{row['时间']}] {row['标题']}")
            print(f"  题材：{tags}")
            print(f"  链接：{row['链接']}")
            print()

        # 保存
        monitor.save_news(df)
    else:
        print("未获取到新闻，可能是网络问题")

    print("\n可用功能:")
    print("  1. 实时监控新闻 - monitor.start_monitoring(interval=60)")
    print("  2. 设置推送回调 - monitor.news_callback = your_function")
    print("  3. 手动获取新闻 - df = monitor.get_latest_news(20)")
