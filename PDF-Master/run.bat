@echo off
setlocal
cd /d "%~dp0"
title PDF Master
set "VENV=%LOCALAPPDATA%\PDFMaster\venv"

if exist "%VENV%\Scripts\python.exe" goto run
echo Environment not found. Running setup first...
call "%~dp0setup.bat"
if not exist "%VENV%\Scripts\python.exe" exit /b 1

:run
"%VENV%\Scripts\python.exe" main.py
echo.
pause
