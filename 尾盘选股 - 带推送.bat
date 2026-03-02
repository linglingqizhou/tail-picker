@echo off
chcp 65001 >nul
echo ================================================
echo                 尾盘选股器 - 带推送
echo         %date% %time%
echo ================================================
echo.

cd /d "%~dp0"

python src/tail_main.py --mode pick --push

echo.
echo 按任意键退出...
pause >nul
