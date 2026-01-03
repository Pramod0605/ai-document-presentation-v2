@echo off
setlocal enabledelayedexpansion

echo ==========================================
echo Manim Dependency Diagnostic Tool
echo ==========================================
echo.

set FAIL=0

:: Check Manim
echo [1/4] Checking Manim...
where manim >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Manim not found in PATH.
    set FAIL=1
) else (
    for /f "tokens=*" %%i in ('manim --version') do set M_VER=%%i
    echo [OK] Manim version: !M_VER!
)
echo.

:: Check LaTeX
echo [2/4] Checking LaTeX...
where latex >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] LaTeX not found. (Required for MathTex)
    set FAIL=1
) else (
    echo [OK] LaTeX found.
)
echo.

:: Check dvisvgm
echo [3/4] Checking dvisvgm...
where dvisvgm >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] dvisvgm not found. (Required for SVG math rendering)
    set FAIL=1
) else (
    for /f "tokens=*" %%i in ('dvisvgm --version ^| findstr "dvisvgm"') do set D_VER=%%i
    echo [OK] dvisvgm version: !D_VER!
)
echo.

:: Check FFmpeg
echo [4/4] Checking FFmpeg...
where ffmpeg >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] FFmpeg not found.
    set FAIL=1
) else (
    echo [OK] FFmpeg found.
)
echo.

echo ==========================================
if %FAIL% EQU 0 (
    echo [SUCCESS] All Manim dependencies are verified!
) else (
    echo [FAILURE] Some dependencies are missing. Please check the logs above.
)
echo ==========================================
pause
