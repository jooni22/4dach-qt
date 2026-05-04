@echo off
setlocal

set "ROOT_DIR=%~dp0"
cd /d "%ROOT_DIR%"

where uv >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Command 'uv' was not found in PATH.
    echo Install uv first: https://docs.astral.sh/uv/
    exit /b 1
)

echo [INFO] Syncing dependencies...
call uv sync || exit /b 1

echo [INFO] Ensuring PyInstaller is available...
call uv run python -c "import PyInstaller" >nul 2>nul
if errorlevel 1 (
    call uv add --dev pyinstaller || exit /b 1
)

echo [INFO] Regenerating application icon...
call uv run python scripts\generate_app_icon.py || exit /b 1

echo [INFO] Cleaning previous build output...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

echo [INFO] Building Windows application (onedir)...
call uv run pyinstaller ^
    --noconfirm ^
    --clean ^
    --onedir ^
    --windowed ^
    --name 4dach ^
    --icon assets\app_icon.ico ^
    --add-data "config.json;." ^
    --add-data "form.ui;." ^
    --add-data "assets;assets" ^
    --add-data "core;core" ^
    --add-data "ui;ui" ^
    --collect-all PySide6 ^
    __main__.py || exit /b 1

echo [INFO] Build complete.
echo [INFO] Output directory: dist\4dach
exit /b 0
