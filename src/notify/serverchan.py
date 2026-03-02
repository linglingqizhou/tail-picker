# -*- coding: utf-8 -*-
"""
Server 酱微信推送模块
使用 Server 酱 API 将选股结果推送到微信
官网：https://sct.ftqq.com/
"""

import requests
import json
from typing import Dict, List, Optional
import pandas as pd
from datetime import datetime


class ServerChanNotifier:
    """Server 酱微信推送器"""

    # 默认配置
    DEFAULT_CONFIG = {
        'send_key': '',  # 从 https://sct.ftqq.com/ 获取
        'enabled': True,
        'title_template': '尾盘选股提醒 - {date}',
        'top_n': 10,  # 推送前 N 只股票
    }

    def __init__(self, config: Dict = None):
        """
        初始化推送器

        Args:
            config: 配置字典，需包含 send_key
        """
        self.config = self.DEFAULT_CONFIG.copy()
        if config:
            self.config.update(config)

        self.send_key = self.config.get('send_key', '')
        self.enabled = self.config.get('enabled', True) and bool(self.send_key)

        # API 地址（Server 酱 Turbo 版）
        self.api_url = f'https://sctapi.ftqq.com/{self.send_key}.send'

    def format_message(self, df: pd.DataFrame, top_n: int = None) -> str:
        """
        格式化选股结果为 Markdown 消息

        Args:
            df: 选股结果 DataFrame
            top_n: 显示前 N 只股票

        Returns:
            str: Markdown 格式消息
        """
        if top_n is None:
            top_n = self.config.get('top_n', 10)

        if df is None or df.empty:
            return "## 尾盘选股提醒\n\n今日未找到符合条件的股票。"

        # 取前 N 只
        display_df = df.head(top_n).copy()

        # 构建 Markdown 消息
        lines = []

        # 标题
        date_str = datetime.now().strftime('%Y-%m-%d %H:%M')
        lines.append(f"## 📈 尾盘选股提醒 - {date_str}")
        lines.append("")

        # 汇总信息
        lines.append(f"**共筛选出 {len(df)} 只股票**，以下是评分最高的 {min(top_n, len(df))} 只：")
        lines.append("")

        # 股票列表表格
        lines.append("### 选股结果")
        lines.append("")
        lines.append("| 排名 | 代码 | 名称 | 涨幅 | 量比 | 换手率 | 评分 |")
        lines.append("|:----:|:----:|:----:|:----:|:----:|:------:|:----:|")

        # 尝试获取列名
        code_col = '代码' if '代码' in df.columns else 'symbol'
        name_col = '名称' if '名称' in df.columns else 'name'
        gain_col = '涨跌幅' if '涨跌幅' in df.columns else ('涨幅' if '涨幅' in df.columns else 'change_percent')
        vol_ratio_col = '量比' if '量比' in df.columns else ('volume_ratio' if 'volume_ratio' in df.columns else None)
        turnover_col = '换手率' if '换手率' in df.columns else ('turnover_ratio' if 'turnover_ratio' in df.columns else None)
        score_col = 'score' if 'score' in df.columns else None

        for i, (_, row) in enumerate(display_df.iterrows(), 1):
            rank = i
            code = row.get(code_col, 'N/A')
            name = row.get(name_col, 'N/A')
            gain = row.get(gain_col, 0) if gain_col in df.columns else 0
            vol_ratio = row.get(vol_ratio_col, '-') if vol_ratio_col and vol_ratio_col in df.columns else '-'
            turnover = row.get(turnover_col, '-') if turnover_col and turnover_col in df.columns else '-'
            score = row.get(score_col, 0) if score_col and score_col in df.columns else 0

            # 格式化数值
            gain_str = f"{gain:.2f}%" if isinstance(gain, (int, float)) else str(gain)
            vol_ratio_str = f"{vol_ratio:.2f}" if isinstance(vol_ratio, (int, float)) else str(vol_ratio)
            turnover_str = f"{turnover:.2f}%" if isinstance(turnover, (int, float)) else str(turnover)
            score_str = f"{score:.1f}" if isinstance(score, (int, float)) else str(score)

            lines.append(f"| {rank} | {code} | {name} | {gain_str} | {vol_ratio_str} | {turnover_str} | {score_str} |")

        lines.append("")

        # 风险提示
        lines.append("### ⚠️ 风险提示")
        lines.append("")
        lines.append("> 以上选股结果仅供参考，不构成投资建议。")
        lines.append("> 股市有风险，投资需谨慎！")
        lines.append("")

        # 策略说明
        lines.append("### 📋 选股策略")
        lines.append("")
        lines.append("- **涨幅条件**: 3%-7%（避免追高）")
        lines.append("- **量比条件**: >1.5（放量）")
        lines.append("- **换手率**: 5%-20%（活跃但不过热）")
        lines.append("- **主力净流入**: >500 万（资金流入）")
        lines.append("- **综合评分**: 按多维度打分排序")

        return "\n".join(lines)

    def send(self, df: pd.DataFrame, title: str = None, content: str = None) -> Dict:
        """
        发送推送消息

        Args:
            df: 选股结果 DataFrame
            title: 消息标题（可选）
            content: 消息内容（可选，如不提供则自动格式化）

        Returns:
            dict: API 响应结果
        """
        if not self.enabled:
            return {'error': 'ServerChan 未启用（缺少 send_key）'}

        # 生成内容
        if content is None:
            content = self.format_message(df)

        # 生成标题
        if title is None:
            date_str = datetime.now().strftime('%Y-%m-%d')
            title = f'尾盘选股提醒 - {date_str}'

        # 发送请求
        try:
            payload = {
                'title': title,
                'desp': content,
                'channel': 9,  # 微信渠道
            }

            response = requests.post(self.api_url, json=payload, timeout=10)
            result = response.json()

            if result.get('code') == 0:
                print(f"[推送成功] ServerChan 消息已发送")
                return {'success': True, 'data': result}
            else:
                error_msg = result.get('message', '未知错误')
                print(f"[推送失败] ServerChan API 返回错误：{error_msg}")
                return {'error': error_msg, 'data': result}

        except requests.exceptions.RequestException as e:
            print(f"[推送失败] 网络请求错误：{e}")
            return {'error': str(e)}
        except Exception as e:
            print(f"[推送失败] 未知错误：{e}")
            return {'error': str(e)}

    def send_test(self) -> Dict:
        """
        发送测试消息

        Returns:
            dict: API 响应结果
        """
        print("[测试] 发送测试消息...")

        # 创建测试数据
        test_df = pd.DataFrame({
            '代码': ['000001', '600519', '300750'],
            '名称': ['平安银行', '贵州茅台', '宁德时代'],
            '涨跌幅': [4.5, 6.2, 5.8],
            '量比': [1.8, 2.1, 1.9],
            '换手率': [5.2, 2.1, 3.8],
            'score': [85.5, 92.0, 88.3]
        })

        return self.send(test_df, title='【测试】尾盘选股器消息推送')


# 便捷函数
def send_to_wechat(df: pd.DataFrame, send_key: str = None, config: Dict = None) -> Dict:
    """
    便捷推送函数

    Args:
        df: 选股结果 DataFrame
        send_key: Server 酱 send_key
        config: 完整配置字典

    Returns:
        dict: API 响应结果
    """
    if config:
        notifier = ServerChanNotifier(config)
    elif send_key:
        notifier = ServerChanNotifier({'send_key': send_key})
    else:
        # 尝试从配置文件加载
        try:
            from config import SERVERCHAN_CONFIG
            notifier = ServerChanNotifier(SERVERCHAN_CONFIG)
        except (ImportError, KeyError):
            return {'error': '未配置 Server 酱 send_key'}

    return notifier.send(df)


if __name__ == "__main__":
    # 测试代码
    print("=" * 50)
    print("测试 Server 酱推送模块")
    print("=" * 50)

    # 从配置文件加载（如果有）
    try:
        from config import SERVERCHAN_CONFIG
        print(f"使用配置文件中的 send_key: {SERVERCHAN_CONFIG.get('send_key', '未配置')[:10]}...")
        notifier = ServerChanNotifier(SERVERCHAN_CONFIG)
    except (ImportError, KeyError):
        print("未找到配置文件配置，使用默认配置")
        notifier = ServerChanNotifier({'send_key': '', 'enabled': False})

    if notifier.enabled:
        # 发送测试消息
        result = notifier.send_test()
        print(f"\n推送结果：{result}")
    else:
        print("\nServer 酱未启用，请在配置文件中设置 send_key")
        print("获取方式：访问 https://sct.ftqq.com/ 注册并获取 send_key")
