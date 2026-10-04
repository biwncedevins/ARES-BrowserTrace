@echo off
REM BrowserTrace launcher - runs the application from source.
cd /d "%~dp0"
python run.py
if errorlevel 1 pause