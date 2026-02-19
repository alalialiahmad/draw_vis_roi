@echo off
setlocal EnableDelayedExpansion
title ROI Tool - Build for Windows

echo ============================================================
echo   ROI Tool - Windows Executable Builder
echo ============================================================
echo.

:: ── Check Python ────────────────────────────────────────────
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH.
    echo.
    echo Please install Python 3.9 or newer from:
    echo   https://www.python.org/downloads/
    echo.
    echo Make sure to check "Add Python to PATH" during installation.
    echo.
    pause
    exit /b 1
)

for /f "tokens=2 delims= " %%v in ('python --version 2^>^&1') do set PY_VER=%%v
echo [OK] Python %PY_VER% found.
echo.

:: ── Create isolated virtual environment ─────────────────────
echo [1/4] Creating virtual environment...
if exist "build_env" (
    echo       Removing old build_env...
    rmdir /s /q build_env
)

python -m venv build_env
if errorlevel 1 (
    echo [ERROR] Failed to create virtual environment.
    pause
    exit /b 1
)
echo       Done.
echo.

:: ── Install dependencies inside venv ────────────────────────
echo [2/4] Installing dependencies (PyQt5, Pillow, PyInstaller)...
echo       This may take a few minutes on first run...
echo.

build_env\Scripts\python.exe -m pip install --quiet --upgrade pip
build_env\Scripts\pip.exe install --quiet PyQt5>=5.15 Pillow>=10.0 pyinstaller>=6.0

if errorlevel 1 (
    echo [ERROR] Failed to install dependencies.
    echo         Check your internet connection and try again.
    pause
    exit /b 1
)
echo       Done.
echo.

:: ── Clean previous build artifacts ──────────────────────────
echo [3/4] Building standalone executable...
if exist "dist\ROITool.exe" del /f /q "dist\ROITool.exe"
if exist "build" rmdir /s /q build

build_env\Scripts\pyinstaller.exe ^
    --onefile ^
    --windowed ^
    --name ROITool ^
    --exclude-module tkinter ^
    --exclude-module matplotlib ^
    --exclude-module numpy ^
    --exclude-module scipy ^
    --hidden-import PyQt5.sip ^
    --hidden-import PIL.Image ^
    --hidden-import PIL.ImageDraw ^
    --hidden-import PIL.ImageTk ^
    --collect-all PyQt5 ^
    app.py

if errorlevel 1 (
    echo.
    echo [ERROR] Build failed. See output above for details.
    pause
    exit /b 1
)
echo       Done.
echo.

:: ── Verify output ───────────────────────────────────────────
echo [4/4] Verifying output...
if not exist "dist\ROITool.exe" (
    echo [ERROR] dist\ROITool.exe was not created.
    pause
    exit /b 1
)

for %%A in ("dist\ROITool.exe") do set SIZE=%%~zA
set /a SIZE_MB=!SIZE! / 1048576

echo ============================================================
echo   BUILD SUCCESSFUL
echo ============================================================
echo.
echo   Executable: dist\ROITool.exe  (~%SIZE_MB% MB)
echo.
echo   You can now copy dist\ROITool.exe to any Windows PC
echo   and run it without installing Python or any libraries.
echo.
echo ============================================================

:: Open the dist folder in Explorer
explorer dist

pause
