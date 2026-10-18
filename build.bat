@echo off
setlocal
cd /d "%~dp0"
echo === Afterburner Profile Backup: build ===

echo.
echo Step 1 of 5: Looking for Python...
set "PY="
py -3 --version >nul 2>&1
if not errorlevel 1 set "PY=py -3"
if not defined PY (
    python --version >nul 2>&1
    if not errorlevel 1 set "PY=python"
)
if not defined PY (
    echo Python 3.10+ is needed to BUILD ^(not to use^) the app. Get it from python.org.
    goto :fail
)
echo Found Python: %PY%

echo.
echo Step 2 of 5: Setting up the build environment ^(.venv^)...
if not exist ".venv\Scripts\python.exe" (
    %PY% -m venv .venv
    if errorlevel 1 (
        echo Could not create the .venv folder. Make sure Python 3.10+ is installed correctly.
        goto :fail
    )
)
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -r requirements-dev.txt
if errorlevel 1 (
    echo Could not install PyInstaller. Check your internet connection and try again.
    goto :fail
)

echo.
echo Step 3 of 5: Running the tests...
".venv\Scripts\python.exe" -m unittest discover -s tests
if errorlevel 1 (
    echo The tests failed, so the app was NOT built. Fix the problems above and try again.
    goto :fail
)

echo.
echo Step 4 of 5: Building the app with PyInstaller...
".venv\Scripts\python.exe" -m PyInstaller --noconfirm --clean --onefile --windowed --name AfterburnerProfileBackup --paths src --add-data "docs\QUICKSTART.md;docs" ^
    --hidden-import ui_firstrun --hidden-import ui_backup --hidden-import ui_restore ^
    --hidden-import ui_restore_select --hidden-import ui_settings --hidden-import ui_help ^
    --version-file version_info.txt src\main.py
if errorlevel 1 (
    echo PyInstaller failed, so the app was NOT built. See the messages above.
    goto :fail
)
if not exist "dist\AfterburnerProfileBackup.exe" (
    echo The build finished but dist\AfterburnerProfileBackup.exe was not found.
    goto :fail
)

echo.
echo Step 5 of 5: Done!
echo Your app is here: %~dp0dist\AfterburnerProfileBackup.exe
if /i not "%~1"=="nopause" pause
exit /b 0

:fail
echo.
echo BUILD FAILED.
if /i not "%~1"=="nopause" pause
exit /b 1
