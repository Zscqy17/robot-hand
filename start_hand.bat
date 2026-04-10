@echo off
chcp 65001 >nul
title FTP灵巧手控制面板 - 右手 RS485

echo ========================================
echo   FTP 灵巧手控制面板 - 启动中...
echo   串口: COM4  波特率: 115200
echo ========================================
echo.

cd /d "%~dp0"
python inspire_hand_sdk\example\Vision_driver_485_r.py

if %errorlevel% neq 0 (
    echo.
    echo [错误] 程序异常退出，错误码: %errorlevel%
    pause
)
