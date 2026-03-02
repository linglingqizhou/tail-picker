#!/bin/bash
# 尾盘选股器 Android APP 快速打包脚本
# 适用于 WSL/Ubuntu 环境

set -e

echo "======================================"
echo "  尾盘选股器 Android APK 打包工具"
echo "======================================"

# 检查是否安装了必要的依赖
check_dependencies() {
    echo "[1/5] 检查依赖..."

    if ! command -v python3 &> /dev/null; then
        echo "错误：未找到 Python3，请先安装"
        exit 1
    fi

    if ! command -v java &> /dev/null; then
        echo "错误：未找到 Java，请先安装 OpenJDK 11"
        echo "sudo apt-get install -y openjdk-11-jdk"
        exit 1
    fi

    if ! pip3 show buildozer &> /dev/null; then
        echo "安装 Buildozer..."
        pip3 install buildozer cython==0.29.33
    fi

    echo "依赖检查完成!"
}

# 准备项目文件
prepare_files() {
    echo "[2/5] 准备项目文件..."

    cd "$(dirname "$0")"

    # 创建符号链接到 src 目录
    if [ ! -L "src" ] && [ -d "../src" ]; then
        ln -s ../src .
        echo "创建 src 符号链接"
    fi

    # 检查 buildozer.spec
    if [ ! -f "buildozer.spec" ]; then
        echo "错误：未找到 buildozer.spec 文件"
        exit 1
    fi

    echo "项目文件准备完成!"
}

# 清理旧文件
clean_old_builds() {
    echo "[3/5] 清理旧的构建文件..."

    rm -rf .buildozer
    rm -rf bin

    echo "清理完成!"
}

# 打包 APK
build_apk() {
    echo "[4/5] 开始打包 APK..."

    # 初始化 buildozer（如果未初始化）
    if [ ! -d ".buildozer" ]; then
        buildozer init
    fi

    # 打包 debug 版本
    buildozer -v android debug

    echo "打包完成!"
}

# 输出结果
show_result() {
    echo "[5/5] APK 文件位置:"

    if ls bin/*.apk 1> /dev/null 2>&1; then
        echo ""
        echo "======================================"
        echo "  打包成功!"
        echo "======================================"
        ls -lh bin/*.apk
        echo ""
        echo "将 APK 传输到手机即可安装"
    else
        echo "打包失败，请检查日志"
        exit 1
    fi
}

# 主流程
main() {
    check_dependencies
    prepare_files
    clean_old_builds
    build_apk
    show_result
}

# 运行
main
