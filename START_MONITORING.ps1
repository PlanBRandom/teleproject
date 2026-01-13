# Start 24-Hour Monitoring with Configuration Check
# Ensures system is properly configured before starting

$ErrorActionPreference = "Stop"
$VenvPython = "D:\oi-7500-pipeline\.venv\Scripts\python.exe"
$ConfigFile = "config.yaml"
$ConfigScript = "configure_system.py"

function Write-Info { param([string]$Message) Write-Host "[INFO] $Message" -ForegroundColor Cyan }
function Write-Success { param([string]$Message) Write-Host "[OK] $Message" -ForegroundColor Green }
function Write-Error { param([string]$Message) Write-Host "[ERROR] $Message" -ForegroundColor Red }

Write-Host ""
Write-Host ("=" * 80) -ForegroundColor Cyan
Write-Host "24-HOUR MONITORING SYSTEM - STARTUP" -ForegroundColor Green
Write-Host ("=" * 80) -ForegroundColor Cyan
Write-Host ""

# Check if config exists
if (-not (Test-Path $ConfigFile)) {
    Write-Error "Configuration file not found: $ConfigFile"
    Write-Host ""
    Write-Host "You need to configure the system before starting monitoring." -ForegroundColor Yellow
    Write-Host ""
    $response = Read-Host "Would you like to run the configuration wizard now? (Y/n)"
    
    if ($response -eq "" -or $response -eq "Y" -or $response -eq "y") {
        Write-Info "Starting configuration wizard..."
        Write-Host ""
        & $VenvPython $ConfigScript
        
        if ($LASTEXITCODE -ne 0) {
            Write-Error "Configuration failed or was cancelled"
            exit 1
        }
        
        Write-Host ""
        Write-Success "Configuration complete!"
        Write-Host ""
        $response = Read-Host "Start monitoring now? (Y/n)"
        
        if ($response -ne "" -and $response -ne "Y" -and $response -ne "y") {
            Write-Info "Monitoring not started. Run this script again when ready."
            exit 0
        }
    } else {
        Write-Info "Please run: python configure_system.py"
        exit 1
    }
}

Write-Success "Configuration found: $ConfigFile"
Write-Host ""

# Display current configuration
Write-Info "Configuration file exists"

# Count radio configs
$radioConfigs = Get-ChildItem -Filter "radio_config*.json" -ErrorAction SilentlyContinue
Write-Host ""
Write-Host "Found configuration files:" -ForegroundColor Yellow
Write-Host "  config.yaml (Modbus settings)" -ForegroundColor White
Write-Host "  Radio configs: $($radioConfigs.Count)" -ForegroundColor White
Write-Host ""

$response = Read-Host "Use existing configuration? (Y/n/reconfigure)"

if ($response -eq "reconfigure") {
    Write-Info "Starting configuration wizard..."
    Write-Host ""
    & $VenvPython $ConfigScript
    
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Configuration failed or was cancelled"
        exit 1
    }
    Write-Host ""
} elseif ($response -ne "" -and $response -ne "Y" -and $response -ne "y") {
    Write-Info "Monitoring cancelled. Run: python configure_system.py to reconfigure"
    exit 0
}

Write-Host ""
Write-Host ("=" * 80) -ForegroundColor Cyan
Write-Host "STARTING MONITORING PROCESSES" -ForegroundColor Green
Write-Host ("=" * 80) -ForegroundColor Cyan
Write-Host ""

# Clean up any existing Python processes
Write-Info "Cleaning up existing processes..."
Get-Process python* -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2

# Start Modbus pipeline
Write-Info "Starting Modbus pipeline..."
Start-Process -FilePath $VenvPython `
              -ArgumentList @("-m", "pipeline.main") `
              -WorkingDirectory $PWD `
              -WindowStyle Minimized
Start-Sleep -Seconds 3

# Start radio monitors
$radioCount = 0
foreach ($radioConfig in $radioConfigs) {
    $radioCount++
    Write-Info "Starting radio monitor: $($radioConfig.Name)"
    Start-Process -FilePath $VenvPython `
                  -ArgumentList @("simple_monitor.py", "--config", $radioConfig.Name) `
                  -WorkingDirectory $PWD `
                  -WindowStyle Minimized
    Start-Sleep -Seconds 2
}

Start-Sleep -Seconds 3

# Check processes started
$processes = Get-Process python* -ErrorAction SilentlyContinue
$expectedCount = 1 + $radioCount

Write-Host ""
if ($processes.Count -eq $expectedCount) {
    Write-Success "All $expectedCount processes started successfully!"
} elseif ($processes.Count -gt 0) {
    Write-Host "Started $($processes.Count) of $expectedCount processes" -ForegroundColor Yellow
} else {
    Write-Error "No processes started - check configuration and logs"
    exit 1
}

Write-Host ""
Write-Host ("=" * 80) -ForegroundColor Green
Write-Host "24-HOUR MONITORING ACTIVE" -ForegroundColor Green
Write-Host ("=" * 80) -ForegroundColor Green
Write-Host ""
Write-Host "Started: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" -ForegroundColor White
Write-Host "Will run until: $((Get-Date).AddHours(24).ToString('yyyy-MM-dd HH:mm:ss'))" -ForegroundColor White
Write-Host ""
Write-Host "Running processes:" -ForegroundColor Yellow
$processes | ForEach-Object {
    Write-Host "  PID $($_.Id) - $($_.Path)" -ForegroundColor White
}
Write-Host ""
Write-Host "Data logging to:" -ForegroundColor Yellow
Write-Host "  - MQTT broker (check config.yaml for details)" -ForegroundColor White
Write-Host "  - Logs: ./logs/" -ForegroundColor White
Write-Host "  - Stats: ./protocol_logs/" -ForegroundColor White
Write-Host ""
Write-Host ("=" * 80) -ForegroundColor Green
Write-Host ""
Write-Host "Monitoring is running. Check status anytime with:" -ForegroundColor Cyan
Write-Host "  Get-Process python*" -ForegroundColor White
Write-Host ""
