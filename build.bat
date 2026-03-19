@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul 2>&1
title H3C SSH Tool - Build

echo.
echo ================================================
echo    H3C SSH Auto-OPS Tool  -  Build EXE
echo ================================================
echo.

cd /d "%~dp0"

:: ── 1. Check Python ─────────────────────────────
echo [1/5] Checking Python ...
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Please install Python and add to PATH.
    pause
    exit /b 1
)
for /f "tokens=*" %%i in ('python --version') do echo       %%i

:: ── 2. Install dependencies ─────────────────────
echo.
echo [2/5] Installing dependencies ...
python -m pip install --upgrade pip --quiet
python -m pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo [WARN] Some packages may have failed, continuing...
)

:: ── 3. Check PyInstaller ────────────────────────
echo.
echo [3/5] Checking PyInstaller ...
python -m pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo       Installing PyInstaller ...
    python -m pip install pyinstaller --quiet
)
for /f "tokens=2" %%v in ('python -m pip show pyinstaller ^| findstr Version') do echo       PyInstaller %%v

:: ── 4. Generate icon ────────────────────────────
echo.
echo [4/5] Generating app icon ...
python create_icon.py
if not exist "app.ico" (
    echo [WARN] Icon generation failed, using default icon.
)

:: ── 5. Build EXE ────────────────────────────────
echo.
echo [5/5] Building EXE ...
echo ------------------------------------------------
echo   Please wait, this may take 1~3 minutes ...
echo ------------------------------------------------
echo.

if exist "build" rmdir /s /q build >nul 2>&1
if exist "dist\H3C_SSH_Tool.exe" del /f /q "dist\H3C_SSH_Tool.exe" >nul 2>&1

python -m PyInstaller build.spec --noconfirm --clean

echo.
if exist "dist\H3C_SSH_Tool.exe" (
    echo ================================================
    echo   Build SUCCESS!
    echo ================================================
    echo.
    for %%f in ("dist\H3C_SSH_Tool.exe") do (
        set /a SIZE_MB=%%~zf / 1048576
        echo   Output : dist\H3C_SSH_Tool.exe
        echo   Size   : !SIZE_MB! MB
    )
    echo.
    echo   This EXE runs standalone without Python.
    echo.
    set /p OPEN_DIR="Open output folder? (Y/N): "
    if /i "!OPEN_DIR!"=="Y" explorer dist
) else (
    echo ================================================
    echo   Build FAILED!
    echo ================================================
    echo.
    echo   Please check the error messages above.
    echo   Common fixes:
    echo     1. Run as Administrator
    echo     2. Check build.spec configuration
    echo     3. Ensure all dependencies are installed
)

echo.
pause
endlocal
