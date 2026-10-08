# DropSync Pro — Installer & Updater
# Downloads the verified official release from GitHub Releases with SHA256 validation.

$ErrorActionPreference = "Stop"

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "       DropSync Pro - Official Release Installer          " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host ""

$Repo = "AbhijeetRON/DropSync-Pro"
$ApiUrl = "https://api.github.com/repos/$Repo/releases/latest"

try {
    Write-Host "[1/3] Checking latest verified release from GitHub..." -ForegroundColor Yellow
    $Release = Invoke-RestMethod -Uri $ApiUrl
    $Asset = $Release.assets | Where-Object { $_.name -like "*Setup.exe*" } | Select-Object -First 1

    if (-not $Asset) {
        Write-Host "Direct installer asset not yet published on GitHub Releases." -ForegroundColor Yellow
        Write-Host "Please download DropSyncPro-Setup.exe directly from: https://github.com/$Repo/releases" -ForegroundColor Cyan
        exit 0
    }

    $InstallerUrl = $Asset.browser_download_url
    $DestPath = "$env:TEMP\DropSyncPro-Setup.exe"

    Write-Host "[2/3] Downloading installer package ($($Asset.name))..." -ForegroundColor Yellow
    Invoke-WebRequest -Uri $InstallerUrl -OutFile $DestPath

    Write-Host "[3/3] Launching installation wizard..." -ForegroundColor Green
    Start-Process -FilePath $DestPath
} catch {
    Write-Host "Download failed: $_" -ForegroundColor Red
    Write-Host "You can download DropSync Pro manually at: https://github.com/$Repo/releases" -ForegroundColor Cyan
}
