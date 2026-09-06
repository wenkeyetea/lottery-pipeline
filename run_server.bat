@echo off
chcp 65001 >nul
cd /d "%~dp0"

REM 优先使用已建好的隔离 Python 环境（已装 flask），否则退回系统 Python
set PY=%USERPROFILE%\.workbuddy\binaries\python\envs\default\Scripts\python.exe
if not exist "%PY%" set PY=%USERPROFILE%\.workbuddy\binaries\python\versions\3.13.12\python.exe
if not exist "%PY%" set PY=python

echo 正在检查/安装依赖(flask)...
"%PY%" -m pip install -q flask 2>nul

echo.
echo ================================================
echo   开奖分析智能体 · 后端启动中...
echo   手机请与电脑连同一 WiFi，打开下方"手机访问"地址
echo ================================================
echo.

"%PY%" server.py
pause
