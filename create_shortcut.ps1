# Create desktop shortcut for SYBOT using PowerShell

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ExePath = Join-Path $ScriptDir "dist\SYBOT.exe"
$Desktop = [Environment]::GetFolderPath("Desktop")
$ShortcutPath = Join-Path $Desktop "SYBOT.lnk"

# Check if exe exists
if (-not (Test-Path $ExePath)) {
    Write-Host "Error: SYBOT.exe not found at $ExePath"
    Write-Host "Please build the executable first using: python -m PyInstaller sybot.spec"
    exit 1
}

# Create shortcut using WScript.Shell
$WScriptShell = New-Object -ComObject WScript.Shell
$Shortcut = $WScriptShell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = $ExePath
$Shortcut.WorkingDirectory = $ScriptDir
$Shortcut.Description = "SYBOT AI Assistant"
$Shortcut.Save()

Write-Host "Desktop shortcut created: $ShortcutPath"
Write-Host "Double-click the shortcut to launch SYBOT"
