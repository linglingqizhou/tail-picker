@echo off
echo ========================================
echo 修改 DNS 服务器为 114.114.114.114
echo ========================================
echo.

:: 获取当前网络连接名称
for /f "tokens=*" %%i in ('netsh interface show interface ^| findstr "连接"') do set "conn=%%i"

:: 提取连接名称（去掉状态列）
for /f "tokens=3*" %%a in ("%conn%") do set "interface_name=%%a %%b"

echo 当前网络连接：%interface_name%
echo.

:: 设置 DNS
echo 正在设置主 DNS 为 114.114.114.114...
netsh interface ip set dns name="%interface_name%" source=static addr=114.114.114.114 register=primary

echo 正在设置备用 DNS 为 8.8.8.8...
netsh interface ip add dns name="%interface_name%" addr=8.8.8.8 index=2

echo.
echo 完成！请重新测试网络连接
echo.
echo 如果要恢复自动获取 DNS，运行：
echo netsh interface ip set dns name="%interface_name%" source=dhcp
echo.
pause
