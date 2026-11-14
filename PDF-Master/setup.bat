@echo off
setlocal
cd /d "%~dp0"
title PDF Master - Setup
set "VENV=%LOCALAPPDATA%\PDFMaster\venv"

echo ==== PDF Master setup ====
echo Project folder:     %CD%
echo Environment folder: %VENV%
echo.

if not exist "requirements.txt" (
    echo requirements.txt was not found in this folder.
    echo Extract the whole zip first, then run setup.bat from inside the extracted PDF-Master folder.
    goto fail
)

set "PY="
for %%V in (3.12 3.13 3.11 3.10) do call :trypy %%V
if not defined PY goto nopython
goto havepy

:trypy
if defined PY goto :eof
py -%1 --version >nul 2>nul
if not errorlevel 1 set "PY=py -%1"
goto :eof

:nopython
echo Python 3.10 to 3.13 was not found.
echo Install Python 3.12 64-bit from https://www.python.org/downloads/release/python-31210/
echo then run setup.bat again. Very new versions such as 3.14 or 3.15 are not supported yet.
goto fail

:havepy
echo Using:
%PY% --version
echo.

if exist "%VENV%\Scripts\python.exe" goto install
echo Creating environment...
%PY% -m venv "%VENV%"
if errorlevel 1 goto fail

:install
echo Installing libraries - the first time takes a few minutes...
"%VENV%\Scripts\python.exe" -m pip install --upgrade pip
"%VENV%\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto fail

echo.
echo Checking that every library loads...
"%VENV%\Scripts\python.exe" -c "import PySide6, fitz, pypdf, PIL, img2pdf, reportlab, cryptography; print('All libraries load OK')"
if errorlevel 1 goto fail

echo.
echo Setup finished. Next: run_tests.bat to check the engine, or run.bat to start the app.
pause
exit /b 0

:fail
echo.
echo Setup did not finish. Take a screenshot of this window and send it for help.
pause
exit /b 1
