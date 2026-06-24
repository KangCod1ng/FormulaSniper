@echo off
:: FormulaSniper 一键启动脚本
:: 自动激活虚拟环境并启动应用

cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo [错误] 虚拟环境不存在，请先运行: python -m venv .venv
    pause
    exit /b 1
)

echo 正在启动 FormulaSniper...
call ".venv\Scripts\activate.bat"
".venv\Scripts\python.exe" main.py
pause
