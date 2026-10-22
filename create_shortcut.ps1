# Creates a "Stream Clip Detector" shortcut with the program icon on the desktop (called by install.bat).
$dir = Split-Path -Parent $MyInvocation.MyCommand.Path
$pyw = (Get-Command pyw -ErrorAction SilentlyContinue).Source
if (-not $pyw) { $pyw = (Get-Command pythonw -ErrorAction SilentlyContinue).Source }
if (-not $pyw) { Write-Host "Python was not found - no shortcut created. Use start.bat to start the program."; exit 0 }
$desktop = [Environment]::GetFolderPath('Desktop')
$link = (New-Object -ComObject WScript.Shell).CreateShortcut((Join-Path $desktop 'Stream Clip Detector.lnk'))
$link.TargetPath = $pyw
$link.Arguments = '"' + (Join-Path $dir 'clip_gui.py') + '"'
$link.WorkingDirectory = $dir
$link.IconLocation = (Join-Path $dir 'icons\app.ico')
$link.Description = 'Stream Clip Detector'
$link.Save()
Write-Host "Shortcut created on the desktop."
