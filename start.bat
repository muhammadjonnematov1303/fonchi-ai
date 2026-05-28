@echo off
chcp 65001 > nul
echo Bot ishga tushmoqda...
"%~dp0.venv\Scripts\python.exe" "%~dp0main.py"
if errorlevel 1 (
    echo.
    echo XATO yuz berdi. Enter bosing...
    pause > nul
)
