@echo off
chcp 65001 >nul
echo ================================================
echo                 数据源健康检查
echo         %date% %time%
echo ================================================
echo.

cd /d "%~dp0"

python src/tail_main.py --mode test_source

echo.
echo 按任意键退出...
pause >nul
