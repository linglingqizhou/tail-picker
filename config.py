"""
配置文件
"""

import os

# 项目根目录
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 数据存储目录
DATA_DIR = os.path.join(BASE_DIR, "stock_data")
DAILY_DATA_DIR = os.path.join(DATA_DIR, "daily")
MINUTE_DATA_DIR = os.path.join(DATA_DIR, "minute")
REALTIME_DATA_DIR = os.path.join(DATA_DIR, "realtime")

# 确保目录存在
os.makedirs(DAILY_DATA_DIR, exist_ok=True)
os.makedirs(MINUTE_DATA_DIR, exist_ok=True)
os.makedirs(REALTIME_DATA_DIR, exist_ok=True)

# 关注的股票池（示例）
WATCHLIST = [
    "600519",  # 贵州茅台
    "000001",  # 平安银行
    "000858",  # 五粮液
    "300750",  # 宁德时代
    "601318",  # 中国平安
]

# 采集配置
COLLECTION_CONFIG = {
    "realtime_interval": 5,  # 实时数据采集间隔（秒）
    "daily采集_time": "15:30",  # 日线数据采集时间（收盘后）
    "minute_interval": 60,  # 分钟线采集间隔（秒）
}

# 涨停判断配置
ZT_CONFIG = {
    "main_board_rate": 0.10,   # 主板涨停幅度 10%
    "star_market_rate": 0.20,  # 科创板/创业板 20%
    "north_board_rate": 0.30,  # 北交所 30%
}

# ======================
# 尾盘选股器配置
# ======================

# Server 酱推送配置
SERVERCHAN_CONFIG = {
    'send_key': 'SCT316113Tfoxs7wuFzRGKYxh1o8a2e7ov',  # 你的 send_key
    'enabled': True,  # 是否启用推送
    'top_n': 10,  # 推送前 N 只股票
}

# 尾盘选股策略配置 (涨停命中率优化版 - 2026-02-26)
TAIL_PICKER_CONFIG = {
    'top_n': 10,            # 选股数量 (15 -> 10, 精品化)
    'min_gain': 4.0,        # 最小涨幅 (3.5 -> 4.0, 捕捉更强股)
    'max_gain': 8.5,        # 最大涨幅 (7.5 -> 8.5, 允许更强股)
    'min_volume_ratio': 2.0,  # 最小额比 (1.8 -> 2.0, 要求更明显放量)
    'max_volume_ratio': 12.0, # 最大量比 (15.0 -> 12.0, 避免天量)
    'min_turnover': 5.0,    # 最小换手率
    'max_turnover': 15.0,   # 最大换手率
    'min_main_inflow': 800, # 最小主力净流入 (500 -> 800 万，要求更强资金)
    'max_main_inflow_ratio': 15.0,
    'max_market_cap': 500,
    'above_ma5': True,
    'exclude_st': True,
    'volume_score_weight': 30,  # 量比评分权重 (提高)
    'gain_score_weight': 35,
    'inflow_score_weight': 25,
    'trend_score_weight': 10,
}

# 强势股回调策略配置
PULLBACK_CONFIG = {
    'top_n': 20,
    'prev_gain_days': 5,
    'min_prev_gain': 20.0,
    'min_pullback': 5.0,
    'max_pullback': 15.0,
    'above_ma5': True,
    'ma5_trend_up': True,
    'exclude_st': True,
}

# 突破策略配置
BREAKTHROUGH_CONFIG = {
    'top_n': 20,
    'breakthrough_days': 20,
    'min_daily_gain': 5.0,
    'min_volume_ratio': 2.0,
    'min_consolidation_days': 5,
    'consolidation_range': 0.15,
    'exclude_st': True,
}

# 龙虎榜策略配置
LHB_CONFIG = {
    'top_n': 20,
    'lookback_days': 3,
    'min_institution_net_buy': 0,
    'active_trader_days': 2,
    'min_trader_turnover': 1000,
    'exclude_st': True,
}

# 数据源配置
DATA_SOURCE_CONFIG = {
    'timeout': 10,
    'max_retries': 3,
    'retry_delay': 2,
    'auto_switch': True,
    'health_check': True,
}
