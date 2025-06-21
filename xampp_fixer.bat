@echo off
SETLOCAL ENABLEDELAYEDEXPANSION

chcp 65001 >nul

set "SCRIPT_DIR=%~dp0"
set "PYTHON_SCRIPT=%SCRIPT_DIR%Repair Scripts\dist\xampp_repair.exe"

echo Looking for script at: "%PYTHON_SCRIPT%"

:: Check if the script exists
if not exist "%PYTHON_SCRIPT%" (
    echo [X] xampp_repair.py not found at "%PYTHON_SCRIPT%"
    pause
    exit /b 1
)

:: Check if running as administrator
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [...] Requesting administrative privileges...
    powershell -Command "Start-Process '%~dp0%~n0%~x0' -Verb RunAs"
    exit /b
)

:: Actually run the script
echo [✔ ] Running xampp_repair.py as Administrator...
"%PYTHON_SCRIPT%"
echo.
pause
