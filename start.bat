@echo off
setlocal EnableExtensions
chcp 65001 >nul
title WenMind AI 一键启动
cd /d "%~dp0"

set "BACKEND_DIR=%~dp0backend"
set "FRONTEND_DIR=%~dp0frontend"
set "BACKEND_PY=%BACKEND_DIR%\.venv\Scripts\python.exe"
set "BACKEND_URL=http://127.0.0.1:8000/api/v1/health"
set "FRONTEND_URL=http://127.0.0.1:5173/login"

echo ============================================================
echo   WenMind AI 文思智评 - 前后端一键启动
echo ============================================================
echo.

where node >nul 2>nul
if errorlevel 1 (
    echo [错误] 未检测到 Node.js，请先安装 Node.js 20 或更高版本。
    pause
    exit /b 1
)

where npm >nul 2>nul
if errorlevel 1 (
    echo [错误] 未检测到 npm，请检查 Node.js 安装。
    pause
    exit /b 1
)

if not exist "%BACKEND_PY%" (
    echo [初始化] 未检测到后端虚拟环境，正在创建...
    where python >nul 2>nul
    if errorlevel 1 (
        echo [错误] 未检测到 Python，请先安装 Python 3.11 或更高版本。
        pause
        exit /b 1
    )
    python -m venv "%BACKEND_DIR%\.venv"
    if errorlevel 1 goto :init_failed
    echo [初始化] 正在安装后端依赖，请耐心等待...
    "%BACKEND_PY%" -m pip install -r "%BACKEND_DIR%\requirements.txt"
    if errorlevel 1 goto :init_failed
)

if not exist "%BACKEND_DIR%\.env" (
    copy /y "%BACKEND_DIR%\.env.example" "%BACKEND_DIR%\.env" >nul
    echo [初始化] 已根据 .env.example 创建后端 .env。
)

if not exist "%FRONTEND_DIR%\node_modules" (
    echo [初始化] 正在安装前端依赖，请耐心等待...
    pushd "%FRONTEND_DIR%"
    call npm install --no-audit --no-fund
    if errorlevel 1 (
        popd
        goto :init_failed
    )
    popd
)

netstat -ano | findstr ":8000" | findstr LISTENING >nul
if errorlevel 1 (
    echo [启动] 正在启动后端服务：http://127.0.0.1:8000
    start "WenMind Backend" /D "%BACKEND_DIR%" cmd /k ".venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000"
) else (
    echo [跳过] 8000 端口已有服务监听，不重复启动后端。
)

netstat -ano | findstr ":5173" | findstr LISTENING >nul
if errorlevel 1 (
    echo [启动] 正在启动前端服务：http://127.0.0.1:5173
    start "WenMind Frontend" /D "%FRONTEND_DIR%" cmd /k "npm run dev -- --host 127.0.0.1 --port 5173"
) else (
    echo [跳过] 5173 端口已有服务监听，不重复启动前端。
)

echo.
echo [检查] 正在等待后端服务就绪...
set /a BACKEND_RETRIES=0
:wait_backend
curl -s --noproxy "*" "%BACKEND_URL%" >nul 2>nul
if not errorlevel 1 goto :backend_ready
set /a BACKEND_RETRIES+=1
if %BACKEND_RETRIES% GEQ 60 (
    echo [错误] 后端启动超时，请查看 WenMind Backend 窗口中的错误日志。
    pause
    exit /b 1
)
ping 127.0.0.1 -n 2 >nul
goto :wait_backend

:backend_ready
echo [成功] 后端健康检查通过。
echo [检查] 正在等待前端服务就绪...
set /a FRONTEND_RETRIES=0
:wait_frontend
curl -s --noproxy "*" "%FRONTEND_URL%" >nul 2>nul
if not errorlevel 1 goto :frontend_ready
set /a FRONTEND_RETRIES+=1
if %FRONTEND_RETRIES% GEQ 60 (
    echo [错误] 前端启动超时，请查看 WenMind Frontend 窗口中的错误日志。
    pause
    exit /b 1
)
ping 127.0.0.1 -n 2 >nul
goto :wait_frontend

:frontend_ready
echo [成功] 前端页面可以访问。
echo.
echo ============================================================
echo   启动完成，即将打开演示角色登录页。
echo   前端：http://127.0.0.1:5173/login
echo   后端：http://127.0.0.1:8000/api/v1/health
echo   接口文档：http://127.0.0.1:8000/docs
echo.
echo   请保持 WenMind Backend 和 WenMind Frontend 窗口开启。
echo   需要停止服务时，双击 stop.bat。
echo ============================================================
start "" "%FRONTEND_URL%"

exit /b 0

:init_failed
echo.
echo [错误] 初始化失败，请检查上方报错信息后重试。
pause
exit /b 1