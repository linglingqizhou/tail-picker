# A 股行情数据采集系统 & 尾盘选股器

一个基于 AkShare 和新浪财经 API 的 A 股数据采集工具，支持实时行情、历史 K 线、资金流向、龙虎榜数据，以及多种选股策略。

---

## 快速开始

**一键运行**：
```bash
python src/tail_main.py --mode quick
```

**带微信推送**：
```bash
python src/tail_main.py --mode pick --push
```

### 早盘扫描（原有功能）

```bash
python src/data_collector.py --mode morning
```

---

## 功能特性

### 尾盘选股器（增强版）

| 功能 | 说明 |
|------|------|
| **多种策略** | 尾盘选股、强势股回调、突破、龙虎榜 |
| **微信推送** | Server 酱实时推送选股结果 |
| **多数据源** | AkShare > 腾讯财经 > 新浪财经 自动切换 |
| **综合评分** | 多维度打分，智能排序 |
| **历史回测** | 验证策略有效性 |
| **数据导出** | CSV/Excel/JSON 格式 |

### 数据采集（原有功能）

| 功能 | 说明 |
|------|------|
| 实时行情 | 获取全部 5810 只 A 股实时数据 |
| 涨停股筛选 | 自动筛选涨幅>9.5% 的股票 |
| 资金流向 | 获取主力资金净流入排名 |
| 龙虎榜 | 获取机构席位交易数据 |
| 历史 K 线 | 获取日线/周线/月线数据 |
| 分钟 K 线 | 获取 1/5/15/30/60 分钟 K 线 |

---

## 尾盘选股器 - 策略说明

### 1. 尾盘选股策略（一夜持股法）

**核心逻辑**：选择尾盘强势、有资金推动的股票，次日冲高获利。

**筛选条件**：
- 涨幅 3%-7%（避免追高）
- 量比 >1.5（放量）
- 换手率 5%-20%（活跃但不过热）
- 主力净流入 >500 万
- 综合评分排序

### 2. 强势股回调策略

**核心逻辑**：前期强势股回调到支撑位后的反弹机会。

**筛选条件**：
- 5 日内涨幅超过 20%
- 近期回调 5%-15%
- 当前站上 5 日线
- 量能萎缩后放大

### 3. 突破策略

**核心逻辑**：突破平台新高的股票往往有较强上涨动能。

**筛选条件**：
- 突破 20 日/60 日新高
- 成交量放大 2 倍以上
- 当日涨幅>5%
- 平台整理至少 5 日

### 4. 龙虎榜策略

**核心逻辑**：跟随机构席位和知名游资的动向。

**筛选条件**：
- 近 3 日登上龙虎榜
- 机构席位净买入
- 游资席位活跃

---

## 使用方法

### 安装依赖

```bash
pip install -r requirements.txt
```

### 运行策略

```bash
# 快速选股（一键运行）
python src/tail_main.py --mode quick

# 尾盘选股策略
python src/tail_main.py --mode pick

# 强势股回调策略
python src/tail_main.py --mode pullback

# 突破策略
python src/tail_main.py --mode breakthrough

# 龙虎榜策略
python src/tail_main.py --mode lhb

# 运行所有策略
python src/tail_main.py --mode all

# 历史回测
python src/tail_main.py --mode backtest --start-date 20250101 --end-date 20251231

# 测试数据源
python src/tail_main.py --mode test_source

# 清除缓存
python src/tail_main.py --mode clear_cache
```

### 微信推送配置

1. 访问 https://sct.ftqq.com/ 注册账号
2. 获取 send_key
3. 编辑 `config.py`，填入 send_key:

```python
SERVERCHAN_CONFIG = {
    'send_key': 'SCTxxxxxxxxxxxxxxxxxxxx',  # 你的 send_key
    'enabled': True,
    'top_n': 10,
}
```

4. 运行带推送的选股：

```bash
python src/tail_main.py --mode pick --push
```

---

## 配置说明

编辑 `config.py` 自定义策略参数：

```python
# 尾盘选股策略配置
TAIL_PICKER_CONFIG = {
    'top_n': 20,           # 返回前 N 只
    'min_gain': 3.0,       # 最小涨幅%
    'max_gain': 7.0,       # 最大涨幅%
    'min_volume_ratio': 1.5,  # 最小额比
    'min_turnover': 5.0,      # 最小换手率%
    'max_turnover': 20.0,     # 最大换手率%
    'min_main_inflow': 500,   # 最小主力净流入 (万元)
    'exclude_st': True,       # 排除 ST
}

# 强势股回调策略配置
PULLBACK_CONFIG = {
    'top_n': 20,
    'prev_gain_days': 5,      # 前期天数
    'min_prev_gain': 20.0,    # 最小额涨幅%
    'min_pullback': 5.0,      # 最小回调%
    'max_pullback': 15.0,     # 最大回调%
}

# 突破策略配置
BREAKTHROUGH_CONFIG = {
    'top_n': 20,
    'breakthrough_days': 20,  # 突破 N 日新高
    'min_daily_gain': 5.0,    # 最小当日涨幅%
    'min_volume_ratio': 2.0,  # 最小量比
}

# 龙虎榜策略配置
LHB_CONFIG = {
    'top_n': 20,
    'lookback_days': 3,       # 回溯天数
    'min_institution_net_buy': 0,
}
```

---

## 项目结构

```
D:/cursor/A/
├── src/
│   ├── strategies/          # 策略模块
│   │   ├── __init__.py
│   │   ├── base.py          # 策略基类
│   │   ├── tail_strategy.py # 尾盘选股策略
│   │   ├── pullback_strategy.py  # 强势股回调
│   │   ├── breakthrough_strategy.py  # 突破策略
│   │   └── lhb_strategy.py  # 龙虎榜策略
│   ├── notify/              # 推送模块
│   │   ├── __init__.py
│   │   └── serverchan.py    # Server 酱推送
│   ├── data_sources/        # 数据源模块
│   │   ├── __init__.py
│   │   ├── base.py          # 数据源基类
│   │   ├── qq_source.py     # 腾讯财经
│   │   └── manager.py       # 数据源管理器
│   ├── akshare_api.py       # AkShare 接口
│   ├── sina_api.py          # 新浪财经接口
│   ├── tail_main.py         # 尾盘选股器主程序
│   ├── tail_picker.py       # 尾盘选股器（旧版）
│   ├── data_collector.py    # 数据采集程序
│   ├── export.py            # 数据导出
│   └── backtest.py          # 回测引擎
├── config.py                # 配置文件
├── requirements.txt         # 依赖包
├── README.md                # 主说明文档
└── 尾盘选股器 - 快速开始.md  # 快速开始指南
```

---

## 依赖

```txt
akshare>=1.17.0
pandas>=2.0.0
requests>=2.28.0
tabulate>=0.9.0
xlsxwriter>=3.0.0
numpy>=1.24.0
```

---

## 输出示例

### 选股结果表格

```
+--------+--------+--------+--------+---------+--------+
|  代码  |  名称  | 最新价 | 涨跌幅 |  量比  | 评分 |
+========+========+========+========+========+========+
| 000001 | 平安银行 |  12.50 |  5.2% |  2.1  |  85.5 |
| 600519 | 贵州茅台 | 1800.0 |  6.8% |  1.8  |  92.0 |
+--------+--------+--------+--------+--------+--------+
```

### 微信推送消息

```
==================================================
[尾盘选股] 2026-02-24 14:30
==================================================

1. 平安银行 (000001)
   涨幅：5.20%  评分：85.5

2. 贵州茅台 (600519)
   涨幅：6.80%  评分：92.0

==================================================
⚠️ 风险提示：选股仅供参考，不构成投资建议
==================================================
```

---

## 数据保存位置

- 尾盘选股结果：`stock_data/tail_pick/pick_YYYYMMDD_HHMMSS.csv`
- 实时快照：`stock_data/realtime/snapshot_YYYYMMDD_HHMMSS.csv`
- 龙虎榜：`stock_data/lhb_YYYYMMDD.csv`

---

## 常见问题

### Q: Server 酱推送失败？
A: 检查 send_key 是否正确配置，确认 `enabled=True`。

### Q: 数据获取失败？
A: 运行 `python src/tail_main.py --mode test_source` 检查数据源状态。

### Q: 选股结果为空？
A: 可能是市场条件不符合策略要求，可适当放宽筛选条件。

---

## 免责声明

本工具仅供学习和个人研究使用，不构成投资建议。

**股市有风险，投资需谨慎！**

---

版本：3.1 (命令行版)
最后更新：2026-03-03
