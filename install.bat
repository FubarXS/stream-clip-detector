@echo off
cd /d "%~dp0"
echo Installing the Python packages (this can take a few minutes)...
py -m pip install -r requirements.txt
echo.
echo Creating a desktop shortcut...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0create_shortcut.ps1"
echo.
echo Done. Start the program with the "Stream Clip Detector" icon on your desktop (or with start.bat).
pause
