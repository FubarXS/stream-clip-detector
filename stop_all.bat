@echo off
echo Stopping Stream Clip Detector processes (window, analysis, downloads, ffmpeg)...
powershell -NoProfile -ExecutionPolicy Bypass -Command "Get-CimInstance Win32_Process | Where-Object { $_.Name -match '^pythonw?\.exe$' -and $_.CommandLine -match 'clip_gui|clip_detector|yt_dlp' -and $_.ProcessId -ne $PID } | ForEach-Object { taskkill /F /T /PID $_.ProcessId | Out-Null; 'stopped ' + $_.Name + ' ' + $_.ProcessId }"
echo.
set /p OLL=Also quit Ollama and free the GPU memory it holds? (y/N): 
if /i "%OLL%"=="y" (
  taskkill /F /IM "ollama app.exe" >nul 2>&1
  taskkill /F /IM ollama.exe >nul 2>&1
  echo Ollama stopped. Start it again from the Start menu when you need it.
)
echo Done.
pause
