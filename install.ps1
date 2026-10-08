# DropSync Pro One-Line Installer & Manager for Windows
# Run with: irm https://raw.githubusercontent.com/AbhijeetRON/DropSync-Pro/main/install.ps1 | iex

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "       ⚡ DropSync Pro - One-Click Installer ⚡" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host ""

$InstallDir = "$HOME\DropSync-Pro"
$ZipUrl = "https://github.com/AbhijeetRON/DropSync-Pro/archive/refs/heads/main.zip"
$ZipPath = "$env:TEMP\DropSync-Pro.zip"

# Step 1: Check Python
Write-Host "[1/4] Checking Python environment..." -ForegroundColor Yellow
$PythonCmd = "python"
if (Get-Command py -ErrorAction SilentlyContinue) {
    $PythonCmd = "py"
} elseif (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "Python not found. Installing Python via winget..." -ForegroundColor Magenta
    winget install Python.Python.3.12 --accept-source-agreements --accept-package-agreements
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
}
Write-Host "✓ Python runtime verified." -ForegroundColor Green

# Step 2: Download or update repository files
Write-Host "[2/4] Downloading DropSync Pro directly from GitHub..." -ForegroundColor Yellow
if (-not (Test-Path $InstallDir)) {
    New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null
}

Invoke-WebRequest -Uri $ZipUrl -OutFile $ZipPath
Expand-Archive -Path $ZipPath -DestinationPath "$env:TEMP\DropSync-Extract" -Force
Copy-Item -Path "$env:TEMP\DropSync-Extract\DropSync-Pro-main\*" -Destination $InstallDir -Recurse -Force
Remove-Item -Path $ZipPath -Force -ErrorAction SilentlyContinue
Remove-Item -Path "$env:TEMP\DropSync-Extract" -Recurse -Force -ErrorAction SilentlyContinue
Write-Host "✓ Files downloaded to: $InstallDir" -ForegroundColor Green

# Step 3: Install dependencies
Write-Host "[3/4] Installing required dependencies..." -ForegroundColor Yellow
Start-Process -FilePath $PythonCmd -ArgumentList "-m pip install -r `"$InstallDir\requirements.txt`"" -Wait -NoNewWindow
Write-Host "✓ All dependencies installed successfully." -ForegroundColor Green

# Step 4: Create Desktop & Start Menu Shortcuts
Write-Host "[4/4] Creating desktop control panel shortcut..." -ForegroundColor Yellow
$WScriptShell = New-Object -ComObject WScript.Shell
$DesktopShortcut = $WScriptShell.CreateShortcut("$HOME\Desktop\DropSync Pro Controller.lnk")
$DesktopShortcut.TargetPath = "$InstallDir\dropsync.bat"
$DesktopShortcut.WorkingDirectory = $InstallDir
$DesktopShortcut.IconLocation = "shell32.dll,138"
$DesktopShortcut.Save()

Write-Host ""
Write-Host "==========================================================" -ForegroundColor Green
Write-Host "  🎉 Installation Complete! Launching Control Panel...    " -ForegroundColor Green
Write-Host "==========================================================" -ForegroundColor Green
Write-Host ""

Set-Location $InstallDir
Start-Process "$InstallDir\dropsync.bat"
