# 题材热点选股系统 - 使用指南

**创建时间**: 2026-02-27
**版本**: v1.0 (题材热点增强版)

---

## 系统概述

这是一个**技术面 + 题材面**双重驱动的 A 股选股系统，包含以下模块：

```
┌─────────────────────────────────────────────────────────┐
│                    题材热点选股系统                       │
├─────────────────────────────────────────────────────────┤
│  1. 板块热度监控  (theme_picker.py)                     │
│  2. 题材选股器    (theme_picker.py)                     │
│  3. 尾盘选股策略  (strategies/tail_strategy.py)         │
│  4. 新闻快讯推送  (news_monitor.py)                     │
│  5. 数据爬虫模块  (data_sources/)                       │
└─────────────────────────────────────────────────────────┘
```

---

## 模块说明

### 1. 板块热度监控

**文件**: `src/theme_picker.py`

**功能**:
- 实时监控 15+ 个热门板块的热度评分
- 评分维度：板块涨幅 (40%) + 涨停家数 (20%) + 上涨家数 (20%) + 成交活跃度 (10%)

**使用方法**:
```bash
# 查看板块热度排行
python src/theme_picker.py rank

# 查看特定板块的成分股选股
python src/theme_picker.py pick AI 算力
```

**输出示例**:
```
板块热度排行 TOP10:
  板块名称    热度评分    平均涨幅    涨停家数
  5G          52.09       3.00%        1
  煤炭        51.49       2.23%        1
  AI 算力      49.92       1.82%        1
```

---

### 2. 尾盘选股策略 (增强版)

**文件**: `src/strategies/tail_strategy.py`

**评分系统** (满分 100 分):
| 维度 | 评分项 | 分值 |
|------|--------|------|
| 技术面 | 涨幅评分 | 25 分 |
| 技术面 | 量比评分 | 15 分 |
| 技术面 | 换手率评分 | 20 分 |
| 技术面 | 资金流入评分 | 10 分 |
| 题材面 | 热门题材评分 | 20 分 |
| 题材面 | 概念叠加加分 | 10 分 |

**使用方法**:
```python
from src.strategies.tail_strategy import TailStockStrategy

strategy = TailStockStrategy({
    'top_n': 10,
    'use_theme_score': True,  # 启用题材评分
})

# 执行选股
result = strategy.select(data)
```

---

### 3. 新闻快讯推送

**文件**: `src/news_monitor.py`

**功能**:
- 实时监控财联社电报快讯
- 自动识别重要题材新闻
- Server 酱微信推送

**监控的题材关键词**:
- 低空经济、AI 算力、芯片半导体、新能源、5G/6G
- 机器人、华为概念、券商等

**使用方法**:
```python
from src.news_monitor import NewsMonitor, NewsPusher

monitor = NewsMonitor()

# 获取最新新闻
df = monitor.get_latest_news(20)

# 开始实时监控
def on_important_news(news):
    print(f"重要新闻：{news['标题']}")

monitor.start_monitoring(interval=60, callback=on_important_news)
```

---

### 4. 数据源模块

**目录**: `src/data_sources/`

| 文件 | 功能 | 状态 |
|------|------|------|
| eastmoney_themes.py | 东方财富板块数据 | ⚠️ 需网络 |
| tencent_themes.py | 腾讯财经数据 | ✅ 可用 |

---

## 快速开始

### 方法 1: 查看板块热度
```bash
cd D:\Projects\A
python src/theme_picker.py rank
```

### 方法 2: 查看特定板块选股
```bash
python src/theme_picker.py pick 人工智能
```

### 方法 3: 使用增强版尾盘选股
```bash
python src/tail_main.py --mode quick
```

---

## 题材映射表

系统已预定义以下板块的成分股映射：

| 板块 | 成分股数量 | 龙头股 |
|------|-----------|--------|
| 人工智能 | 8 只 | 600519 |
| 芯片半导体 | 8 只 | 603986 |
| 新能源 | 8 只 | 300750 |
| AI 算力 | 8 只 | 601360 |
| 低空经济 | 8 只 | 000099 |
| 5G | 8 只 | 600498 |
| 华为概念 | 8 只 | 002594 |
| 锂电 | 8 只 | 300750 |
| 光伏 | 8 只 | 601012 |
| 机器人 | 8 只 | 002747 |
| 券商 | 8 只 | 600030 |
| 白酒 | 8 只 | 600519 |
| 医药 | 8 只 | 600276 |
| 煤炭 | 8 只 | 600546 |

---

## 数据保存

系统会自动保存以下数据：

```
stock_data/
├── theme_cache/          # 板块热度缓存
│   └── theme_ranking_YYYYMMDD_HHMMSS.csv
├── tail_pick/            # 尾盘选股结果
│   └── pick_YYYYMMDD_HHMMSS.csv
└── news_cache/           # 新闻快讯缓存
    └── news_YYYYMMDD_HHMMSS.csv
```

---

## 注意事项

1. **网络要求**: 需要访问东方财富、腾讯财经等 API
2. **数据更新**: 板块成分股映射需要定期更新
3. **风险提示**: 选股结果仅供参考，不构成投资建议

---

## 常见问题

### Q: 为什么获取不到实时数据？
A: 检查网络连接，部分 API 可能在某些网络环境下无法访问。

### Q: 如何添加新的题材板块？
A: 编辑 `src/theme_picker.py` 中的 `THEME_COMPONENTS` 字典。

### Q: 如何配置 Server 酱推送？
A: 在 `news_monitor.py` 中设置 `serverchan_key` 参数。

---

## 下一步优化方向

1. **数据源优化**: 添加更多稳定的数据源
2. **题材更新**: 定期更新板块成分股映射
3. **回测功能**: 增加题材策略历史回测
4. **GUI 界面**: 开发桌面界面 (可选)

---

**技术支持**: 查看项目 README.md 获取更多信息
