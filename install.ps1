# DropSync Pro — Official Release Installer & Checksum Validator
# Downloads DropSyncPro-Setup.exe directly from GitHub Releases and validates SHA256 integrity.

$ErrorActionPreference = "Stop"

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "       DropSync Pro - Official Release Installer          " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host ""

$Repo = "AbhijeetRON/DropSync-Pro"
$ApiUrl = "https://api.github.com/repos/$Repo/releases/latest"

try {
    Write-Host "[1/4] Checking latest release from GitHub..." -ForegroundColor Yellow
    $Release = Invoke-RestMethod -Uri $ApiUrl
    $Asset = $Release.assets | Where-Object { $_.name -like "*Setup.exe*" } | Select-Object -First 1
    $ShaAsset = $Release.assets | Where-Object { $_.name -like "*SHA256SUMS.txt*" } | Select-Object -First 1

    if (-not $Asset) {
        Write-Host "Direct installer asset not yet published on GitHub Releases." -ForegroundColor Yellow
        Write-Host "Please download DropSyncPro-Setup.exe directly from: https://github.com/$Repo/releases" -ForegroundColor Cyan
        exit 0
    }

    $InstallerUrl = $Asset.browser_download_url
    $DestPath = "$env:TEMP\DropSyncPro-Setup.exe"

    Write-Host "[2/4] Downloading installer package ($($Asset.name))..." -ForegroundColor Yellow
    Invoke-WebRequest -Uri $InstallerUrl -OutFile $DestPath

    # SHA256 Integrity Verification
    if ($ShaAsset) {
        Write-Host "[3/4] Verifying SHA256 checksum..." -ForegroundColor Yellow
        $ShaContent = (Invoke-WebRequest -Uri $ShaAsset.browser_download_url).Content
        $ExpectedHash = ($ShaContent -split '\s+')[0].Trim()
        $ActualHash = (Get-FileHash $DestPath -Algorithm SHA256).Hash

        if ($ExpectedHash -and ($ExpectedHash.ToLower() -ne $ActualHash.ToLower())) {
            Write-Host "FATAL: Checksum mismatch! The installer may be corrupted or compromised." -ForegroundColor Red
            Remove-Item $DestPath -Force -ErrorAction SilentlyContinue
            exit 1
        }
        Write-Host "✓ SHA256 Checksum Verified." -ForegroundColor Green
    } else {
        Write-Host "[3/4] Skipping checksum (no SHA256SUMS.txt attached to release)." -ForegroundColor Yellow
    }

    Write-Host "[4/4] Launching installation wizard..." -ForegroundColor Green
    Start-Process -FilePath $DestPath
} catch {
    Write-Host "Installation failed: $_" -ForegroundColor Red
    Write-Host "You can download DropSync Pro manually at: https://github.com/$Repo/releases" -ForegroundColor Cyan
}
