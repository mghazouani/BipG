# Run LIV Client on device over USB (ADB reverse + flutter run).
# Use this instead of "flutter run" so the reverse is always set.
# Usage: .\run_usb.ps1   or   .\run_usb.ps1 -Device R5CT40398GD

param(
    [string] $Device = "R5CT40398GD"
)

$adb = "$env:LOCALAPPDATA\Android\Sdk\platform-tools\adb.exe"
if (-not (Test-Path $adb)) {
    Write-Error "ADB not found at $adb. Install Android SDK platform-tools."
    exit 1
}

Write-Host "Setting ADB reverse tcp:8000 tcp:8000 on $Device..."
& $adb -s $Device reverse tcp:8000 tcp:8000
if ($LASTEXITCODE -ne 0) {
    Write-Error "ADB reverse failed. Is the device connected? Run: adb devices"
    exit 1
}

Write-Host "Starting Flutter app..."
Set-Location $PSScriptRoot
flutter run -d $Device
