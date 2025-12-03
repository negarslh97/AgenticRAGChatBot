# Sally CDP Browser Launcher
# This script starts Chrome with CDP enabled

param(
    [int]$Port = 9222,
    [string]$Url = "http://localhost:3000/super-admin"
)

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   Sally CDP Browser Launcher" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Close existing Chrome instances
Write-Host "Closing existing Chrome instances..." -ForegroundColor Yellow
$chromeProcesses = Get-Process -Name chrome -ErrorAction SilentlyContinue
if ($chromeProcesses) {
    $chromeProcesses | Stop-Process -Force
    Write-Host "   Chrome processes terminated" -ForegroundColor Green
} else {
    Write-Host "   No Chrome processes found" -ForegroundColor Gray
}

Start-Sleep -Seconds 2

# Chrome path
$chromePath = "C:\Program Files\Google\Chrome\Application\chrome.exe"
if (-not (Test-Path $chromePath)) {
    $chromePath = "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
}
if (-not (Test-Path $chromePath)) {
    Write-Host "Chrome not found! Please install Chrome or update the path." -ForegroundColor Red
    exit 1
}

# Temp profile
$profilePath = "C:\temp\chrome-debug-profile"

# Start Chrome with CDP
Write-Host "Starting Chrome with CDP on port $Port..." -ForegroundColor Yellow
Start-Process $chromePath -ArgumentList @(
    "--remote-debugging-port=$Port",
    "--remote-allow-origins=*",
    "--user-data-dir=$profilePath",
    $Url
)

Write-Host "   Chrome started" -ForegroundColor Green

Start-Sleep -Seconds 3

# Check CDP
Write-Host "Checking CDP connection..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "http://127.0.0.1:$Port/json/version" -TimeoutSec 5
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "   CDP is ACTIVE!" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "   Browser: $($response.Browser)" -ForegroundColor White
    Write-Host "   CDP URL: http://127.0.0.1:$Port" -ForegroundColor White
    Write-Host ""
    Write-Host "Now you can use Sally Assistant!" -ForegroundColor Cyan
    Write-Host "   Agent will work in the SAME browser window." -ForegroundColor Gray
    Write-Host ""
} catch {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Red
    Write-Host "   CDP not responding!" -ForegroundColor Red
    Write-Host "========================================" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please try running the script again." -ForegroundColor Yellow
    Write-Host ""
}

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   Quick Reference" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "To use with API:" -ForegroundColor White
Write-Host "  cdp_url: http://127.0.0.1:$Port" -ForegroundColor Gray
Write-Host "  use_current_page: true" -ForegroundColor Gray
Write-Host ""
