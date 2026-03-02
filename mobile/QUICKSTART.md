# 尾盘选股器 - 手机 APP 版

## 项目结构

```
mobile/
├── app.py              # Kivy 应用主程序
├── mobile.kv           # Kivy UI 布局文件
├── buildozer.spec      # Android 打包配置文件
├── build_android.sh    # Linux/WSL 打包脚本
└── README.md           # 详细说明文档
```

## 快速开始（三种方式）

### 方式一：GitHub Actions 自动打包（最简单）

1. 将代码推送到 GitHub
2. Actions 会自动打包生成 APK
3. 在 Releases 页面下载 APK

**推送标签触发打包：**
```bash
git tag v3.1.0
git push origin v3.1.0
```

### 方式二：WSL2 本地打包

```bash
# 在 WSL2 中运行
cd /mnt/d/Projects/A/mobile

# 安装依赖
sudo apt-get update
sudo apt-get install -y openjdk-11-jdk
pip3 install buildozer cython==0.29.33

# 打包
bash build_android.sh
```

### 方式三：Google Colab 云端打包

访问 https://colab.research.google.com/ 运行以下代码：

```python
!pip install buildozer cython==0.29.33
!apt-get install -y openjdk-11-jdk

# 上传你的代码后
!cd mobile && buildozer -v android debug

# 下载 bin/目录中的 APK
```

## APP 功能

- **一键选股**：点击按钮执行尾盘选股策略
- **板块热度**：实时计算板块热度评分
- **题材追踪**：显示股票所属题材概念
- **结果保存**：自动保存选股结果到手机

## 安装要求

- Android 5.0 (API 21) 或更高版本
- 至少 100MB 可用存储空间
- 网络连接（用于获取股票数据）

## 使用说明

1. 安装 APK 到手机
2. 打开 APP，点击"开始选股"
3. 等待数据获取完成（约 30-60 秒）
4. 点击"查看结果"查看选股列表
5. 结果自动保存到 `/sdcard/Android/data/com.tailpicker/files/stock_data/`

## 注意事项

1. **网络问题**：部分股票 API 可能需要直连，建议关闭代理
2. **数据准确性**：选股结果仅供参考，不构成投资建议
3. **使用时效**：建议在交易日 14:30-15:00 使用（尾盘时段）

## 打包问题排查

### 问题：Java 版本不兼容

```bash
# 检查 Java 版本
java -version

# 安装 OpenJDK 11
sudo apt-get install -y openjdk-11-jdk
```

### 问题：SDK 许可证未接受

```bash
# 在 buildozer.spec 中添加
android.accept_sdk_license = True
```

### 问题：缺少依赖模块

确保 `buildozer.spec` 中的 `requirements` 包含所有需要的模块：

```
requirements = python3,kivy==2.1.0,akshare,pandas,requests,tabulate,numpy,lxml,beautifulsoup4
```

### 问题：APK 太大

- 正常大小：20-30MB（包含 Python 运行时）
- 可使用 APK 压缩工具减小体积

## 更新日志

### v3.1.0 (2026-03-02)
- ✅ 新增板块热度分析
- ✅ 新增题材热点追踪
- ✅ 优化选股评分系统
- ✅ 修复数据源连接问题

### v3.0.0
- ✅ 初始版本发布

## 技术支持

如遇问题，请查看：
1. APP 内错误提示
2. Android Logcat 日志
3. 项目 README 文档
