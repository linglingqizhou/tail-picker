# 尾盘选股器 - Android APP 打包指南

## 方案说明

由于 Buildozer 需要在 Linux 环境下运行，提供以下两种打包方案：

### 方案一：使用 WSL2 (推荐)

在 Windows 上使用 WSL2 (Windows Subsystem for Linux) 运行 Buildozer。

### 方案二：使用 Google Colab 云端打包

在浏览器中使用 Google Colab 免费云端服务打包，无需本地环境。

---

## 方案一：WSL2 打包步骤

### 1. 安装 WSL2

```powershell
# 在 Windows PowerShell (管理员) 运行
wsl --install
```

重启电脑后，完成 Ubuntu 安装。

### 2. 在 WSL2 中安装依赖

```bash
# 更新系统
sudo apt-get update

# 安装 Python 和依赖
sudo apt-get install -y \
    python3 python3-pip \
    python3-venv \
    git curl \
    openjdk-11-jdk \
    autoconf automake \
    build-essential \
    libssl-dev \
    libffi-dev \
    python3-dev \
    python3-kivy

# 安装 pip 依赖
pip3 install buildozer cython
```

### 3. 准备项目

```bash
# 进入项目目录
cd /mnt/d/Projects/A

# 初始化 buildozer
cd mobile
buildozer init

# 打包 Debug 版本
buildozer -v android debug

# 打包 Release 版本
buildozer -v android release
```

### 4. 获取 APK

打包完成后，APK 文件位于：
```
mobile/bin/*.apk
```

---

## 方案二：Google Colab 云端打包（最简单）

### 1. 打开 Colab

访问：https://colab.research.google.com/

### 2. 创建新 Notebook

新建一个 Notebook，粘贴以下代码：

```python
# 1. 安装依赖
!pip install buildozer cython

# 2. 克隆你的代码（或上传到 GitHub 后下载）
!git clone https://github.com/your-username/tail-picker.git
%cd tail-picker/mobile

# 3. 初始化并打包
!buildozer -v android debug
```

### 3. 运行并下载

运行单元格，等待打包完成（约 20-30 分钟），下载生成的 APK。

---

## 方案三：使用现成的 APK 服务

如果以上方案太复杂，可以考虑：

1. **APKPure 上传服务** - 将代码上传到 GitHub，使用 GitHub Actions 自动打包
2. **GitHub Actions CI/CD** - 配置自动打包流程

---

## GitHub Actions 自动打包（推荐）

在项目根目录创建 `.github/workflows/android.yml`:

```yaml
name: Build Android APK

on:
  push:
    tags:
      - 'v*'

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: 3.8

      - name: Install dependencies
        run: |
          pip install buildozer cython
          sudo apt-get install -y openjdk-11-jdk

      - name: Build APK
        run: |
          cd mobile
          buildozer -v android debug

      - name: Upload APK
        uses: actions/upload-artifact@v3
        with:
          name: app-release
          path: mobile/bin/*.apk
```

---

## 安装到手机

1. 将 APK 文件传输到手机
2. 在手机上启用"未知来源"安装权限
3. 点击 APK 文件安装

---

## 使用说明

1. 打开 APP
2. 点击"开始选股"按钮
3. 等待数据获取完成
4. 点击"查看结果"查看选股列表
5. 结果会自动保存到手机存储

---

## 注意事项

1. **网络要求**: 手机需要能访问 A 股数据 API（可能需要关闭代理）
2. **存储空间**: 确保手机有至少 100MB 可用空间
3. **Android 版本**: 需要 Android 5.0 (API 21) 以上
4. **数据保存**: 选股结果保存在 `/sdcard/Android/data/com.tailpicker/files/stock_data/`

---

## 常见问题

### Q: 打包时出现 "No module named 'xxx'"

确保 `buildozer.spec` 的 `requirements` 中包含所有依赖。

### Q: APP 闪退

检查 Logcat 日志：
```bash
adb logcat | grep python
```

### Q: 数据获取失败

1. 检查手机网络连接
2. 尝试关闭代理/VPN
3. 检查 API 是否可用

---

## 联系支持

如有问题，请查看项目 README 或提交 Issue。
