# 24-Hour Monitoring: Modbus + MQTT + Radio

$VenvPython = "D:\oi-7500-pipeline\.venv\Scripts\python.exe"
$Global:Processes = @{}

function Start-Monitor {
    param([string]$Name, [string]$Args)
    Write-Host "[INFO] Starting $Name..." -ForegroundColor Cyan
    try {
        # Split arguments into array
        $argArray = $Args -split '\s+' | Where-Object { $_ }
        $proc = Start-Process -FilePath $VenvPython -ArgumentList $argArray -PassThru -WindowStyle Minimized -WorkingDirectory "D:\oi-7500-pipeline"
        Start-Sleep -Seconds 3
        if (-not $proc.HasExited) {
            $Global:Processes[$Name] = $proc
            Write-Host "[OK] $Name started (PID: $($proc.Id))" -ForegroundColor Green
        } else {
            Write-Host "[WARN] $Name failed to start" -ForegroundColor Yellow
        }
    } catch {
        Write-Host "[ERROR] Failed to start $Name`: $_" -ForegroundColor Red
    }
}

function Show-Status {
    Write-Host "`n================================================================================" -ForegroundColor Cyan
    Write-Host "SYSTEM STATUS" -ForegroundColor Cyan
    Write-Host "================================================================================" -ForegroundColor Cyan
    foreach ($name in $Global:Processes.Keys) {
        $proc = $Global:Processes[$name]
        if ($proc.HasExited) {
            Write-Host "  X $name - STOPPED" -ForegroundColor Red
        } else {
            $uptime = (Get-Date) - $proc.StartTime
            Write-Host "  OK $name - RUNNING (PID: $($proc.Id), uptime: $($uptime.ToString('hh\:mm\:ss')))" -ForegroundColor Green
        }
    }
    Write-Host "================================================================================`n" -ForegroundColor Cyan
}

function Stop-All {
    Write-Host "`n[INFO] Stopping all processes..." -ForegroundColor Cyan
    foreach ($proc in $Global:Processes.Values) {
        if (-not $proc.HasExited) {
            $proc.Kill()
            $proc.WaitForExit(5000)
        }
    }
    Write-Host "[OK] All processes stopped`n" -ForegroundColor Green
}

try {
    Write-Host "`n================================================================================" -ForegroundColor Cyan
    Write-Host "24-HOUR MONITORING: MODBUS + MQTT + RADIO" -ForegroundColor Cyan
    Write-Host "================================================================================`n" -ForegroundColor Cyan
    
    Write-Host "[INFO] Cleaning up existing processes..." -ForegroundColor Cyan
    Get-Process python* -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2
    
    Write-Host "`n================================================================================" -ForegroundColor Cyan
    Write-Host "STARTING COMPONENTS" -ForegroundColor Cyan
    Write-Host "================================================================================`n" -ForegroundColor Cyan
    
    Start-Monitor -Name "Modbus" -Args "-m pipeline.main"
    Start-Monitor -Name "Radio_COM7" -Args "simple_monitor.py --config simple_config_com7.json"
    Start-Monitor -Name "Radio_COM11" -Args "simple_monitor.py --config simple_config_com11.json"
    Start-Monitor -Name "Radio_COM12" -Args "simple_monitor.py --config simple_config_com12.json"
    
    Show-Status
    
    Write-Host "[INFO] Monitoring for 24 hours (Press Ctrl+C to stop early)`n" -ForegroundColor Cyan
    
    $endTime = (Get-Date).AddHours(24)
    $nextStatus = Get-Date
    
    while ((Get-Date) -lt $endTime) {
        Start-Sleep -Seconds 30
        if ((Get-Date) -ge $nextStatus) {
            Show-Status
            $remaining = $endTime - (Get-Date)
            Write-Host "[INFO] Time remaining: $($remaining.ToString('hh\:mm\:ss'))`n" -ForegroundColor Cyan
            $nextStatus = (Get-Date).AddMinutes(5)
        }
    }
    
    Write-Host "`n[OK] Monitoring period complete!" -ForegroundColor Green
    Show-Status
    
} catch {
    Write-Host "`n[ERROR] $_" -ForegroundColor Red
} finally {
    Stop-All
}
