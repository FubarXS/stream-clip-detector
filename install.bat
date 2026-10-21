@echo off
cd /d "%~dp0"
echo Installing the Python packages (this can take a few minutes)...
py -m pip install -r requirements.txt
echo.
echo Done. Start the program with spustit.bat
pause
