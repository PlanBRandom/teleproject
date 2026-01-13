#!/usr/bin/env pwsh
<#
.SYNOPSIS
    24-Hour monitoring with Modbus, MQTT, and Radio logging
.DESCRIPTION
    Starts all monitoring components and runs for 24 hours
#>

$ErrorActionPreference = "Continue"
$VenvPython = "D:\oi-7500-pipeline\.venv\Scripts\python.exe"
$WorkDir = "D:\oi-7500-pipeline"
$DurationHours = 24

# Color output functions
function Write-Success { param([string]$Message) Write-Host "[OK] $Message" -ForegroundColor Green }
function Write-Info { param([string]$Message) Write-Host "[INFO] $Message" -ForegroundColor Cyan }
function Write-Warn { param([string]$Message) Write-Host "[WARN] $Message" -ForegroundColor Yellow }

# Track running processes
$Global:RunningProcesses = @{}

function Start-Component {
    param(
        [string]$Name,
        [string]$Script,
        [string]$Args = ""
    )
    
    Write-Info "Starting $Name..."
    
    try {
        $argList = if ($Args) { "$Script $Args" } else { $Script }
        
        $proc = Start-Process -FilePath $VenvPython `
                              -ArgumentList $argList `
                              -WorkingDirectory $WorkDir `
                              -PassThru `
                              -WindowStyle Minimized
        
        Start-Sleep -Seconds 3
        
        if ($proc.HasExited) {
            Write-Warn "$Name exited immediately (code: $($proc.ExitCode))"
            return $null
        }
        
        $Global:RunningProcesses[$Name] = $proc
        Write-Success "$Name started (PID: $($proc.Id))"
        return $proc
        
    } catch {
        Write-Warn "Failed to start $Name : $($_.Exception.Message)"
        return $null
    }
}

function Show-Status {
    $line = "=" * 80
    Write-Host ""
    Write-Host $line
    Write-Host "SYSTEM STATUS" -ForegroundColor Cyan
    Write-Host $line
    
    foreach ($name in $Global:RunningProcesses.Keys) {
        $proc = $Global:RunningProcesses[$name]
        if ($proc.HasExited) {
            Write-Host "  X $name - STOPPED" -ForegroundColor Red
        } else {
            $runtime = (Get-Date) - $proc.StartTime
            $uptimeStr = "{0:hh\:mm\:ss}" -f $runtime
            Write-Host "  OK $name - RUNNING (PID: $($proc.Id), uptime: $uptimeStr)" -ForegroundColor Green
        }
    }
    Write-Host $line
    Write-Host ""
}

function Stop-All {
    Write-Info "Stopping all processes..."
    
    foreach ($name in $Global:RunningProcesses.Keys) {
        $proc = $Global:RunningProcesses[$name]
        if (-not $proc.HasExited) {
            Write-Info "Stopping $name..."
            try {
                $proc.Kill()
                $proc.WaitForExit(5000)
            } catch {
                Write-Warn "Could not stop $name"
            }
        }
    }
    Write-Success "All processes stopped"
}

# Register Ctrl+C handler
$null = Register-EngineEvent -SourceIdentifier PowerShell.Exiting -Action {
    Stop-All
}

try {
    $line = "=" * 80
    Write-Host ""
    Write-Host $line
    Write-Host "24-HOUR MONITORING: MODBUS + MQTT + RADIO" -ForegroundColor Cyan
    Write-Host $line
    Write-Host ""
    Write-Info "Duration: $DurationHours hours"
    Write-Info "Using existing Mosquitto on port 1883"
    Write-Host ""
    
    # Kill any existing Python processes
    Write-Info "Cleaning up existing processes..."
    Get-Process python* -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2
    
    # Verify Mosquitto is running
    $mqttTest = Test-NetConnection -ComputerName localhost -Port 1883 -WarningAction SilentlyContinue -InformationLevel Quiet
    if ($mqttTest) {
        Write-Success "Mosquitto is available on port 1883"
    } else {
        Write-Warn "Mosquitto not detected on port 1883 - some features may not work"
    $line = "=" * 80
    Write-Host ""
    Write-Host $line
    Write-Host "STARTING COMPONENTS" -ForegroundColor Cyan
    Write-Host $line
    Write-Host ")
    Write-Host "STARTING COMPONENTS" -ForegroundColor Cyan
    Write-Host ("="*80) + "`n"
    
    # Start Main Pipeline (Modbus)
    Start-Component -Name "MainPipeline_Modbus" -Script "-m pipeline.main"
    Start-Sleep -Seconds 2
    
    # Start Radio Monitors
    Start-Component -Name "Radio_COM7" -Script "simple_monitor.py" -Args "--config simple_config_com7.json"
    Start-Sleep -Seconds 2
    
    Start-Component -Name "Radio_COM11" -Script "simple_monitor.py" -Args "--config simple_config_com11.json"
    Start-Sleep -Seconds 2
    
    Start-Component -Name "Radio_COM12" -Script "simple_monitor.py" -Args "--config simple_config_com12.json"
    Start-Sleep -Seconds 3
    
    Show-Status
    
    Write-Info "Monitoring for $DurationHours hours..."
    Write-Info "Press Ctrl+C to stop early"
    Write-Host ""
    
    $endTime = (Get-Date).AddHours($DurationHours)
    $statusInterval = 300 # 5 minutes
    $lastStatusTime = Get-Date
    
    while ((Get-Date) -lt $endTime) {
        Start-Sleep -Seconds 30
        
        # Periodic status update
        if (((Get-Date) - $lastStatusTime).TotalSeconds -ge $statusInterval) {
            Show-Status
            $remaining = $endTime - (Get-Date)
            Write-Info "Time remaining: $($remaining.ToString('hh\:mm\:ss'))"
            $lastStatusTime = Get-Date
        }Host ""
    Write-Success "Monitoring period complete!"
    Show-Status
    
} catch {
    Write-Warn "Error: $_"
} finally {
    Stop-All
    Write-Host ""
    Write-Host "Shutdown complete" -ForegroundColor Green
    Write-Host ""
} finally {
    Stop-All
    Write-Host "`nShutdown complete`n" -ForegroundColor Green
}
