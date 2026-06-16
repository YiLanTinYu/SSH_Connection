@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul 2>&1
title H3C SSH Tool - Nuitka Build

echo.
echo ================================================
echo    H3C SSH Auto-OPS Tool  -  Nuitka Build
echo ================================================
echo.

cd /d "%~dp0"
set NUITKA_CACHE_DIR=%CD%\.nuitka-cache

echo [1/5] Checking Python ...
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Please install Python and add it to PATH.
    pause
    exit /b 1
)
for /f "tokens=*" %%i in ('python --version') do echo       %%i

echo.
echo [2/5] Installing project dependencies ...
python -m pip install --upgrade pip --quiet
python -m pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo [ERROR] Dependency installation failed.
    pause
    exit /b 1
)

echo.
echo [3/5] Checking Nuitka ...
python -m nuitka --version >nul 2>&1
if errorlevel 1 (
    echo       Installing Nuitka ...
    python -m pip install nuitka --quiet
)
for /f "tokens=*" %%v in ('python -m nuitka --version 2^>nul') do (
    echo       Nuitka %%v
    goto :nuitka_version_done
)
:nuitka_version_done

echo.
echo [4/5] Generating app icon ...
python create_icon.py
if not exist "app.ico" (
    echo [WARN] Icon generation failed, building without custom icon.
)

echo.
echo [5/5] Building standalone EXE with Nuitka ...
echo ------------------------------------------------
echo   Please wait, this can take several minutes ...
echo ------------------------------------------------
echo.

if exist "build" rmdir /s /q build >nul 2>&1
if exist "dist" rmdir /s /q dist >nul 2>&1
mkdir dist >nul 2>&1

set ICON_ARGS=
if exist "app.ico" set ICON_ARGS=--windows-icon-from-ico=app.ico

set CONSOLE_MODE=disable
if /i "%~1"=="debug" set CONSOLE_MODE=force
if /i "%DEBUG%"=="1" set CONSOLE_MODE=force
echo   Console mode: %CONSOLE_MODE%

set ONEFILE_ARGS=
set OUTPUT_EXE=dist\main.dist\H3C_SSH_Tool.exe
set BUILD_MODE=folder
if /i "%~1"=="onefile" (
    set ONEFILE_ARGS=--onefile
    set OUTPUT_EXE=dist\H3C_SSH_Tool.exe
    set BUILD_MODE=onefile
)
if /i "%~2"=="onefile" (
    set ONEFILE_ARGS=--onefile
    set OUTPUT_EXE=dist\H3C_SSH_Tool.exe
    set BUILD_MODE=onefile
)
echo   Build mode  : %BUILD_MODE%

python -m nuitka ^
    --standalone ^
    %ONEFILE_ARGS% ^
    --assume-yes-for-downloads ^
    --mingw64 ^
    --lto=no ^
    --jobs=8 ^
    --enable-plugins=pyqt5 ^
    --windows-console-mode=%CONSOLE_MODE% ^
    --nofollow-import-to=tests ^
    --nofollow-import-to=Kylin ^
    --nofollow-import-to=matplotlib ^
    --nofollow-import-to=pytest ^
    --nofollow-import-to=pandas ^
    %ICON_ARGS% ^
    --include-data-files=app.ico=app.ico ^
    --include-data-files=SSH_command.txt=SSH_command.txt ^
    --include-data-files=device_template.xlsx=device_template.xlsx ^
    --output-dir=dist ^
    --output-filename=H3C_SSH_Tool.exe ^
    main.py

echo.
if exist "%OUTPUT_EXE%" (
    echo ================================================
    echo   Build SUCCESS!
    echo ================================================
    echo.
    for %%f in ("%OUTPUT_EXE%") do (
        set /a SIZE_MB=%%~zf / 1048576
        echo   Output : %%~ff
        echo   Size   : !SIZE_MB! MB
    )
    echo.
    if /i "%BUILD_MODE%"=="folder" (
        echo   Folder build is recommended to reduce antivirus false positives.
        echo   Keep the whole dist\main.dist folder together when copying.
    ) else (
        echo   Onefile build may trigger antivirus false positives on some systems.
    )
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
    echo     1. Install Microsoft Visual Studio Build Tools
    echo     2. Ensure dependencies installed successfully
    echo     3. Run build.bat from the project root
)

echo.
pause
endlocal
