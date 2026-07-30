@echo off
setlocal EnableExtensions EnableDelayedExpansion
chcp 65001 >nul 2>&1
title AOMT - Nuitka Build

echo.
echo ================================================
echo        AOMT Switch Operations - Nuitka Build
echo ================================================
echo.

cd /d "%~dp0"
set "PROJECT_DIR=%CD%"
set "PROJECT_PYTHON=%PROJECT_DIR%\.venv\Scripts\python.exe"

rem GCC/SCons used by Nuitka 2.x could not process the Chinese project path.
rem Keep all compiler inputs, the build venv, cache and outputs in an ASCII path.
set "BUILD_ROOT=%LOCALAPPDATA%\AOMT_Nuitka_Build"
set "BUILD_SOURCE=%BUILD_ROOT%\src"
set "BUILD_OUTPUT=%BUILD_ROOT%\output"
set "BUILD_VENV=%BUILD_ROOT%\venv"
set "PYTHON_EXE=%BUILD_VENV%\Scripts\python.exe"
set "NUITKA_CACHE_DIR=%BUILD_ROOT%\cache"

echo [1/6] Checking Python ...
if not exist "%PROJECT_PYTHON%" (
    echo       Project virtual environment not found. Creating .venv ...
    python --version >nul 2>&1
    if errorlevel 1 (
        echo [ERROR] Python not found. Please install Python and add it to PATH.
        pause
        exit /b 1
    )
    python -m venv "%PROJECT_DIR%\.venv"
    if errorlevel 1 (
        echo [ERROR] Failed to create project virtual environment.
        pause
        exit /b 1
    )
)

if not exist "%PYTHON_EXE%" (
    echo       Creating isolated ASCII build environment ...
    "%PROJECT_PYTHON%" -m venv "%BUILD_VENV%"
    if errorlevel 1 (
        echo [ERROR] Failed to create isolated build environment.
        pause
        exit /b 1
    )
)
for /f "tokens=*" %%i in ('""%PYTHON_EXE%" --version"') do echo       %%i
echo       Build Python: %PYTHON_EXE%

echo.
echo [2/6] Installing build dependencies ...
"%PYTHON_EXE%" -m pip install --upgrade pip --quiet
"%PYTHON_EXE%" -m pip install -r "%PROJECT_DIR%\requirements.txt" --quiet
if errorlevel 1 (
    echo [ERROR] Dependency installation failed.
    pause
    exit /b 1
)
"%PYTHON_EXE%" -m pip check
if errorlevel 1 (
    echo [ERROR] Build environment contains broken dependencies.
    pause
    exit /b 1
)

echo.
echo [3/6] Checking Nuitka ...
for /f "tokens=*" %%v in ('""%PYTHON_EXE%" -m nuitka --version 2^>nul"') do (
    echo       Nuitka %%v
    goto :nuitka_version_done
)
echo [ERROR] Nuitka is not available in the build environment.
pause
exit /b 1
:nuitka_version_done

echo.
echo [4/6] Generating app icon ...
"%PYTHON_EXE%" "%PROJECT_DIR%\create_icon.py"
if not exist "%PROJECT_DIR%\app.ico" (
    echo [ERROR] Icon generation failed.
    pause
    exit /b 1
)

echo.
echo [5/6] Staging source in ASCII build directory ...
if exist "%BUILD_SOURCE%" rmdir /s /q "%BUILD_SOURCE%"
if exist "%BUILD_OUTPUT%" rmdir /s /q "%BUILD_OUTPUT%"
mkdir "%BUILD_SOURCE%"
mkdir "%BUILD_OUTPUT%"

xcopy /E /I /Y /Q "%PROJECT_DIR%\config" "%BUILD_SOURCE%\config" >nul
xcopy /E /I /Y /Q "%PROJECT_DIR%\core" "%BUILD_SOURCE%\core" >nul
xcopy /E /I /Y /Q "%PROJECT_DIR%\ui" "%BUILD_SOURCE%\ui" >nul
xcopy /E /I /Y /Q "%PROJECT_DIR%\utils" "%BUILD_SOURCE%\utils" >nul
xcopy /E /I /Y /Q "%PROJECT_DIR%\assets" "%BUILD_SOURCE%\assets" >nul
copy /Y "%PROJECT_DIR%\main.py" "%BUILD_SOURCE%\main.py" >nul
copy /Y "%PROJECT_DIR%\telnetlib_compat.py" "%BUILD_SOURCE%\telnetlib_compat.py" >nul
copy /Y "%PROJECT_DIR%\SSH_command.txt" "%BUILD_SOURCE%\SSH_command.txt" >nul
copy /Y "%PROJECT_DIR%\device_template.xlsx" "%BUILD_SOURCE%\device_template.xlsx" >nul
copy /Y "%PROJECT_DIR%\app.ico" "%BUILD_SOURCE%\app.ico" >nul
copy /Y "%PROJECT_DIR%\THIRD_PARTY_NOTICES.md" "%BUILD_SOURCE%\THIRD_PARTY_NOTICES.md" >nul

if not exist "%BUILD_SOURCE%\main.py" (
    echo [ERROR] Source staging failed.
    pause
    exit /b 1
)

set "ICON_ARGS=--windows-icon-from-ico=app.ico"
set "CONSOLE_MODE=disable"
if /i "%~1"=="debug" set "CONSOLE_MODE=force"
if /i "%DEBUG%"=="1" set "CONSOLE_MODE=force"

set "ONEFILE_ARGS="
set "STAGED_EXE=%BUILD_OUTPUT%\main.dist\H3C_SSH_Tool.exe"
set "FINAL_EXE=%PROJECT_DIR%\dist\main.dist\H3C_SSH_Tool.exe"
set "BUILD_MODE=folder"
if /i "%~1"=="onefile" (
    set "ONEFILE_ARGS=--onefile"
    set "STAGED_EXE=%BUILD_OUTPUT%\H3C_SSH_Tool.exe"
    set "FINAL_EXE=%PROJECT_DIR%\dist\H3C_SSH_Tool.exe"
    set "BUILD_MODE=onefile"
)
if /i "%~2"=="onefile" (
    set "ONEFILE_ARGS=--onefile"
    set "STAGED_EXE=%BUILD_OUTPUT%\H3C_SSH_Tool.exe"
    set "FINAL_EXE=%PROJECT_DIR%\dist\H3C_SSH_Tool.exe"
    set "BUILD_MODE=onefile"
)

echo.
echo [6/6] Building standalone EXE with Nuitka ...
echo       Source       : %BUILD_SOURCE%
echo       Output       : %BUILD_OUTPUT%
echo       Console mode : %CONSOLE_MODE%
echo       Build mode   : %BUILD_MODE%
echo       Please wait, this can take several minutes ...
echo.

cd /d "%BUILD_SOURCE%"
"%PYTHON_EXE%" -m nuitka ^
    --standalone ^
    %ONEFILE_ARGS% ^
    --assume-yes-for-downloads ^
    --mingw64 ^
    --lto=no ^
    --jobs=8 ^
    --enable-plugins=pyqt5 ^
    --include-package=serial ^
    --include-package=pyftpdlib ^
    --include-package=partftpy ^
    --include-package=ntc_templates ^
    --include-package-data=ntc_templates ^
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
    --include-data-dir=config/builtin_templates=config/builtin_templates ^
    --include-data-dir=assets/open_source=assets/open_source ^
    --include-data-dir=assets/icons=assets/icons ^
    --include-data-files=THIRD_PARTY_NOTICES.md=THIRD_PARTY_NOTICES.md ^
    --output-dir="%BUILD_OUTPUT%" ^
    --output-filename=H3C_SSH_Tool.exe ^
    main.py
set "BUILD_EXIT=%ERRORLEVEL%"
cd /d "%PROJECT_DIR%"

if not "%BUILD_EXIT%"=="0" (
    echo.
    echo ================================================
    echo   Build FAILED with exit code %BUILD_EXIT%
    echo ================================================
    echo   Crash reports and compiler files are under:
    echo   %BUILD_SOURCE%
    pause
    exit /b %BUILD_EXIT%
)

if not exist "%STAGED_EXE%" (
    echo [ERROR] Nuitka finished without producing the expected EXE:
    echo         %STAGED_EXE%
    pause
    exit /b 1
)

if exist "%PROJECT_DIR%\dist" rmdir /s /q "%PROJECT_DIR%\dist"
mkdir "%PROJECT_DIR%\dist"
robocopy "%BUILD_OUTPUT%" "%PROJECT_DIR%\dist" /E /R:2 /W:1 /NFL /NDL /NJH /NJS /NP >nul
if errorlevel 8 (
    echo [ERROR] Failed to copy build output back to the project.
    pause
    exit /b 1
)

echo.
echo ================================================
echo   Build SUCCESS!
echo ================================================
for %%f in ("%FINAL_EXE%") do (
    set /a SIZE_MB=%%~zf / 1048576
    echo   Output : %%~ff
    echo   Size   : !SIZE_MB! MB
)
if /i "%BUILD_MODE%"=="folder" (
    echo   Keep the whole dist\main.dist folder together.
) else (
    echo   Onefile builds may trigger antivirus false positives.
)
echo.
set /p OPEN_DIR="Open output folder? (Y/N): "
if /i "!OPEN_DIR!"=="Y" explorer "%PROJECT_DIR%\dist"

echo.
pause
endlocal
