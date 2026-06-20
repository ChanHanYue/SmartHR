@echo off
cd /d "%~dp0"
SETLOCAL EnableDelayedExpansion

:: 1. Initial IP Detection
:init
echo [INFO] Detecting Network IP...
set "IP="
for /f "delims=" %%i in ('python -c "import socket; print([ip for ip in socket.gethostbyname_ex(socket.gethostname())[2] if not ip.startswith(''127.'')][:1][0] if [ip for ip in socket.gethostbyname_ex(socket.gethostname())[2] if not ip.startswith(''127.'')] else '''') "') do set IP=%%i
if "%IP%"=="" (
    for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /c:"IPv4 Address"') do (
        set val=%%a
        set IP=!val: =!
    )
)
if "%IP%"=="" set IP=127.0.0.1

:: 2. Display Menu
:menu
cls
echo ================================================================
echo        SmartHR - AI-Powered HR Management System
echo ================================================================
echo.
echo  NETWORK ACCESS: http://%IP%:5000
echo.
echo  [1] Start Server
echo  [2] Re-detect IP
echo  [3] Exit
echo.
set /p choice="Enter option (1-3): "

if "%choice%"=="1" goto launch
if "%choice%"=="2" goto init
if "%choice%"=="3" exit
goto menu

:launch
echo [INFO] Starting... (To return to menu, close the server window)
:: Use 'start' to launch the server in a SEPARATE process.
:: The main menu script will wait for it to finish.
start /wait cmd /c "call .venv\Scripts\activate.bat && python run.py"

:: After the server window is closed, return to the menu
goto menu
