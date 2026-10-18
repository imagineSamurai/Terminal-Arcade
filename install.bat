@echo off
setlocal
cd /d "%~dp0"
if exist "%~dp0arcade.exe" (
    "%~dp0arcade.exe" --install
) else (
    python "%~dp0arcade.py" --install
)
pause
