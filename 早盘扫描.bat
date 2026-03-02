@echo off
chcp 65001 >nul
title A 股早盘扫描程序
cd /d D:/cursor/A
echo.
echo ============================================
echo           A 股早盘扫描程序
echo ============================================
echo.
python src/data_collector.py --mode morning
echo.
echo ============================================
echo 扫描完成！
echo 数据已保存到 D:\cursor\stock_data\ 目录
echo ============================================
echo.
pause
