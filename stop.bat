@echo off
setlocal EnableExtensions
chcp 65001 >nul
title 停止 WenMind AI 服务

echo 正在停止 WenMind AI 前后端服务...

set "FOUND_PROCESS=0"
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8000" ^| findstr LISTENING') do (
    set "FOUND_PROCESS=1"
    echo 停止后端进程 PID=%%a
    taskkill /F /PID %%a >nul 2>nul
)
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":5173" ^| findstr LISTENING') do (
    set "FOUND_PROCESS=1"
    echo 停止前端进程 PID=%%a
    taskkill /F /PID %%a >nul 2>nul
)

if "%FOUND_PROCESS%"=="0" (
    echo 当前没有检测到 8000 或 5173 端口上的服务。
) else (
    echo 停止命令已执行。
)

echo 如需重新启动，请双击 start.bat。
pause