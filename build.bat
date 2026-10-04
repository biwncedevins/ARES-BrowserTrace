@echo off
REM BrowserTrace - one-step build to a standalone Windows .exe (dist\BrowserTrace.exe)
setlocal
cd /d "%~dp0"

echo [1/4] Installing dependencies...
python -m pip install -r requirements.txt -r requirements-build.txt
if errorlevel 1 goto :err

echo [2/4] Generating application icon...
python scripts\make_icon.py
if errorlevel 1 goto :err

echo [3/4] Running self-test...
python tests\selftest.py
if errorlevel 1 goto :err

echo [4/4] Building executable with PyInstaller...
python -m PyInstaller --noconfirm --clean BrowserTrace.spec
if errorlevel 1 goto :err

echo.
echo Build complete: dist\BrowserTrace.exe
exit /b 0

:err
echo.
echo Build failed. See messages above.
exit /b 1