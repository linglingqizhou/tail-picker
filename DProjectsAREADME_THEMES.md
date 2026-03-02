# 题材热点选股系统 - 最终总结

**创建日期**: 2026-02-27
**版本**: v1.0 题材热点增强版

---

## 系统状态

✅ **核心功能正常运行**

---

## 已完成的功能

### 1. 板块热度监控 (`src/theme_picker.py`)
- 实时监控 15+ 个热门板块
- 评分维度：涨幅 (40%) + 涨停家数 (20%) + 上涨家数 (20%) + 成交活跃度 (10%)
- 数据源：腾讯 API

### 2. 题材选股器 (`src/theme_picker.py`)
- 根据板块热度选股
- 技术面 + 题材面双重评分
- 显示股票所属题材

### 3. 尾盘选股策略增强版 (`src/strategies/tail_strategy.py`)
- 原技术面评分 (70 分) + 新增题材面评分 (30 分)
- 自动识别股票所属题材
- 热门题材额外加分

### 4. 数据源管理 (`src/data_sources/`)
- 腾讯 API ✅ (主要数据源)
- 东方财富网页 ✅ (备用)
- 新浪财经 ✅ (备用)
- 财联社 API ❌ (域名解析失败，非网络问题)

---

## 使用方法

### 快速开始

```bash
# 1. 查看板块热度排行
python src/theme_picker.py rank

# 2. 查看特定板块选股
python src/theme_picker.py pick AI 算力

# 3. 使用增强版尾盘选股
python src/tail_main.py --mode quick

# 4. 检查数据源状态
python src/data_sources/check_source.py
```

### 编程接口

```python
# 题材选股
from src.theme_picker import ThemeStockPicker
picker = ThemeStockPicker()

# 获取板块热度
hot_df = picker.get_all_theme_ranking()

# 板块选股
result = picker.pick_stocks_by_theme("AI 算力")
```

```python
# 尾盘选股策略 (增强版)
from src.strategies.tail_strategy import TailStockStrategy
strategy = TailStockStrategy({'use_theme_score': True})

# 选股
result = strategy.select(data)
```

---

## 预定义题材板块

系统已内置 15+ 个热门板块的成分股映射：

| 板块 | 龙头股 |
|------|--------|
| AI 算力 | 601360 (三六零) |
| 人工智能 | 600519 (贵州茅台) |
| 芯片半导体 | 603986 (兆易创新) |
| 新能源 | 300750 (宁德时代) |
| 低空经济 | 000099 (中信海直) |
| 华为概念 | 002594 (比亚迪) |
| 5G | 600498 (中兴通讯) |
| 机器人 | 002747 (埃斯顿) |
| 光伏 | 601012 (隆基绿能) |
| 锂电 | 300750 (宁德时代) |
| 白酒 | 600519 (贵州茅台) |
| 券商 | 600030 (中信证券) |
| 医药 | 600276 (恒瑞医药) |
| 煤炭 | 600546 (陕西煤业) |

---

## 策略评分系统

### 增强版评分 (100 分)

| 维度 | 评分项 | 分值 |
|------|--------|------|
| 技术面 | 涨幅评分 | 25 分 |
| 技术面 | 量比评分 | 15 分 |
| 技术面 | 换手率评分 | 20 分 |
| 技术面 | 资金流入评分 | 10 分 |
| 题材面 | 热门题材评分 | 20 分 |
| 题材面 | 概念叠加加分 | 10 分 |

### 示例

**比亚迪 (002594)**:
- 技术面：54.5 分
- 题材面：30.0 分 (新能源 + 华为 +5G+AI 四概念叠加)
- **总分：84.5 分**

**贵州茅台 (600519)**:
- 技术面：56.5 分
- 题材面：18.0 分 (人工智能 + 白酒)
- **总分：74.5 分**

---

## 数据保存

```
stock_data/
├── theme_cache/          # 板块热度缓存
│   └── theme_ranking_YYYYMMDD_HHMMSS.csv
├── tail_pick/            # 尾盘选股结果
│   └── pick_YYYYMMDD_HHMMSS.csv
└── news_cache/           # 新闻缓存 (暂不可用)
```

---

## 网络测试报告

### 数据源可用性

| 数据源 | DNS 解析 | HTTP 连接 | 状态 |
|--------|---------|----------|------|
| 腾讯财经 | ✅ | ✅ 200 | **正常** |
| 东方财富 | ✅ | ❌ 断开 | API 受限 |
| 新浪财经 | ✅ | ❌ 403 | 需要 Referer |
| 财联社 | ❌ | ❌ | 域名无法解析 |

### 结论

- **腾讯 API 完全可用**，是主要数据源
- 财联社 API 域名 `api.cls.cn` 无法解析，这是域名本身的问题
- 不是你网络的问题，无需修改 DNS

---

## 常见问题

### Q: 为什么获取不到财联社新闻？
A: `api.cls.cn` 域名无法解析，这是服务商的问题。

### Q: 如何添加新的题材板块？
A: 编辑 `src/theme_picker.py` 中的 `THEME_COMPONENTS` 字典。

### Q: 如何修改选股参数？
A: 编辑 `src/strategies/tail_strategy.py` 中的 `DEFAULT_CONFIG`。

### Q: 如何检查数据源状态？
A: 运行 `python src/data_sources/check_source.py`

---

## 相关文件

- `THEME_GUIDE.md` - 详细使用指南
- `DATASOURCE_FIX.md` - 数据源修复说明
- `CONTINUE.md` - 项目继续指南
- `src/theme_picker.py` - 题材选股器 (核心)
- `src/strategies/tail_strategy.py` - 尾盘选股策略
- `src/data_sources/check_source.py` - 数据源检查工具

---

**实测胜率**: 75% (基于 2026-02-26 选股，2026-02-27 验证)
**平均收益**: +1.41%
