#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Robust startup script for OI-7500 + Meshtastic mesh system
.DESCRIPTION
    Starts all components with proper serial port cleanup, error recovery, and health monitoring
#>

param(
    [int]$DurationHours = 15,
    [switch]$SkipMeshtastic,
    [switch]$SkipRadios,
    [switch]$SkipModbus,
    [switch]$SkipMosquitto
)

$ErrorActionPreference = "Continue"
$VenvPython = "D:\oi-7500-pipeline\.venv\Scripts\python.exe"
$MosquittoExe = "C:\Program Files\mosquitto\mosquitto.exe"
$WorkDir = "D:\oi-7500-pipeline"

# Color output functions
function Write-Success { param([string]$Message) Write-Host "[OK] $Message" -ForegroundColor Green }
function Write-Info { param([string]$Message) Write-Host "[INFO] $Message" -ForegroundColor Cyan }
function Write-Warn { param([string]$Message) Write-Host "[WARN] $Message" -ForegroundColor Yellow }
function Write-Err { param([string]$Message) Write-Host "[ERROR] $Message" -ForegroundColor Red }

# Track running processes
$Global:RunningProcesses = @{}

function Stop-ExistingProcesses {
    Write-Info "Checking for existing Python processes on serial ports..."
    
    # Kill any Python processes that might be holding serial ports
    $pythonProcs = Get-Process python* -ErrorAction SilentlyContinue
    if ($pythonProcs) {
        Write-Warn "Found $($pythonProcs.Count) Python processes. Stopping them..."
        $pythonProcs | ForEach-Object {
            try {
                $_.Kill()
                Write-Success "Stopped process $($_.Id)"
            } catch {
                Write-Warn "Could not stop process $($_.Id): $_"
            }
        }
        Start-Sleep -Seconds 3
    }
    
    # Check for Mosquitto processes
    $mosquittoProcs = Get-Process mosquitto -ErrorAction SilentlyContinue
    if ($mosquittoProcs) {
        Write-Warn "Found Mosquitto process(es) running..."
        
        # Try to stop gracefully
        try {
            $mosquittoProcs | Stop-Process -Force -ErrorAction Stop
            Start-Sleep -Seconds 2
            Write-Success "Stopped Mosquitto"
        } catch {
            Write-Err "Cannot stop Mosquitto - it may be running with elevated privileges"
            Write-Err "Please run this command in an ADMINISTRATOR PowerShell:"
            Write-Host "    taskkill /F /IM mosquitto.exe" -ForegroundColor Yellow
            Write-Host ""
            
            # Check if port 1883 is occupied
            $portTest = Test-NetConnection -ComputerName localhost -Port 1883 -WarningAction SilentlyContinue -ErrorAction SilentlyContinue
            if ($portTest.TcpTestSucceeded) {
                Write-Err "Port 1883 is occupied. Cannot start new Mosquitto instance."
                Write-Info "Options:"
                Write-Info "  1. Kill Mosquitto as administrator (recommended)"
                Write-Info "  2. Run this script with -SkipMosquitto flag (mesh bridge won't work)"
                throw "Mosquitto is blocking port 1883"
            }
        }
    }
    
    Write-Success "Cleanup complete"
}

function Start-ProcessWithRetry {
    param(
        [string]$Name,
        [string]$Command,
        [string]$Arguments,
        [int]$RetryCount = 3,
        [int]$DelaySeconds = 5
    )
    
    for ($i = 1; $i -le $RetryCount; $i++) {
        Write-Info "Starting $Name (attempt $i/$RetryCount)..."
        
        try {
            $proc = Start-Process -FilePath $Command `
                                  -ArgumentList $Arguments `
                                  -WorkingDirectory $WorkDir `
                                  -PassThru `
                                  -NoNewWindow `
                                  -RedirectStandardOutput "$WorkDir\logs\$Name-stdout.log" `
                                  -RedirectStandardError "$WorkDir\logs\$Name-stderr.log"
            
            Start-Sleep -Seconds $DelaySeconds
            
            # Check if process is still running
            if ($proc.HasExited) {
                Write-Err "$Name exited immediately (code: $($proc.ExitCode))"
                if ($i -lt $RetryCount) {
                    Write-Warn "Retrying in $DelaySeconds seconds..."
                    Start-Sleep -Seconds $DelaySeconds
                    continue
                } else {
                    return $null
                }
            }
            
            $Global:RunningProcesses[$Name] = $proc
            Write-Success "$Name started (PID: $($proc.Id))"
            return $proc
            
        } catch {
            Write-Err "Failed to start $Name : $($_.Exception.Message)"
            if ($i -lt $RetryCount) {
                Write-Warn "Retrying in $DelaySeconds seconds..."
                Start-Sleep -Seconds $DelaySeconds
            }
        }
    }
    
    return $null
}

function Test-ProcessHealth {
    param([string]$Name)
    
    if ($Global:RunningProcesses.ContainsKey($Name)) {
        $proc = $Global:RunningProcesses[$Name]
        if (-not $proc.HasExited) {
            return $true
        } else {
            Write-Warn "$Name has exited (code: $($proc.ExitCode))"
            return $false
        }
    }
    return $false
}

function Show-SystemStatus {
    $line = "=" * 80
    Write-Host "`n$line"
    Write-Host "SYSTEM STATUS" -ForegroundColor Cyan
    Write-Host $line
    
    foreach ($name in $Global:RunningProcesses.Keys) {
        $proc = $Global:RunningProcesses[$name]
        if ($proc.HasExited) {
            Write-Host "  X $name - STOPPED (exit code: $($proc.ExitCode))" -ForegroundColor Red
        } else {
            $runtime = (Get-Date) - $proc.StartTime
            $uptimeStr = "{0:hh\:mm\:ss}" -f $runtime
            Write-Host "  OK $name - RUNNING (PID: $($proc.Id), uptime: $uptimeStr)" -ForegroundColor Green
        }
    }
    
    Write-Host "$line`n"
}

function Stop-AllProcesses {
    Write-Info "Stopping all processes gracefully..."
    
    foreach ($name in $Global:RunningProcesses.Keys) {
        $proc = $Global:RunningProcesses[$name]
        if (-not $proc.HasExited) {
            Write-Info "Stopping $name (PID: $($proc.Id))..."
            try {
                $proc.Kill()
                $proc.WaitForExit(5000)
                Write-Success "$name stopped"
            } catch {
                Write-Warn "Could not stop $name gracefully: $_"
            }
        }
    }
}

# Main execution
try {
    Write-Host "`n" + ("="*80)
    Write-Host "OI-7500 + Meshtastic Mesh System Startup" -ForegroundColor Cyan
    Write-Host ("="*80)
    Write-Info "Duration: $DurationHours hours"
    Write-Info "Working directory: $WorkDir"
    Write-Host ""
    
    # Create logs directory
    $logsDir = Join-Path $WorkDir "logs"
    if (-not (Test-Path $logsDir)) {
        New-Item -ItemType Directory -Path $logsDir | Out-Null
        Write-Success "Created logs directory"
    }
    
    # Clean up existing processes
    Stop-ExistingProcesses
    
    Write-Host "`n" + ("="*80)
    Write-Host "STARTING COMPONENTS" -ForegroundColor Cyan
    Write-Host ("="*80) + "`n"
    
    # 1. Start Mosquitto MQTT Broker (if not skipped)
    if (-not $SkipMosquitto) {
        Write-Info "Step 1/7: Starting Mosquitto MQTT broker..."
        $mosquittoProc = Start-ProcessWithRetry -Name "Mosquitto" `
                                                -Command $MosquittoExe `
                                                -Arguments "-v -p 1883" `
                                                -DelaySeconds 3
        
        if (-not $mosquittoProc) {
            Write-Err "Failed to start Mosquitto."
            Write-Warn "Radio monitors and mesh bridge require local MQTT broker"
            Write-Info "You can skip Mosquitto with -SkipMosquitto flag"
            exit 1
        }
        
        # Verify Mosquitto is listening
        Start-Sleep -Seconds 2
        $mqttTest = Test-NetConnection -ComputerName localhost -Port 1883 -WarningAction SilentlyContinue
        if ($mqttTest.TcpTestSucceeded) {
            Write-Success "Mosquitto is listening on port 1883"
        } else {
            Write-Err "Mosquitto not responding on port 1883"
        }
    } else {
        Write-Warn "Skipping Mosquitto (-SkipMosquitto)"
        Write-Warn "Radio monitors and mesh bridge will not work without local MQTT"
    }
    
    # 2. Start Meshtastic Gateway (if enabled)
    if (-not $SkipMeshtastic) {
        Write-Info "Step 2/7: Starting Meshtastic Gateway..."
        $gatewayProc = Start-ProcessWithRetry -Name "MeshtasticGateway" `
                                              -Command $VenvPython `
                                              -Arguments "meshtastic_gateway.py" `
                                              -DelaySeconds 5
    } else {
        Write-Warn "Skipping Meshtastic Gateway (-SkipMeshtastic)"
    }
    
    # 3. Start Meshtastic Bridge (if enabled)
    if (-not $SkipMeshtastic) {
        Write-Info "Step 3/7: Starting Meshtastic Bridge..."
        $bridgeProc = Start-ProcessWithRetry -Name "MeshtasticBridge" `
                                             -Command $VenvPython `
                                             -Arguments "meshtastic_bridge.py" `
                                             -DelaySeconds 5
    } else {
        Write-Warn "Skipping Meshtastic Bridge (-SkipMeshtastic)"
    }
    
    # 4. Start Main Pipeline (Modbus)
    if (-not $SkipModbus) {
        Write-Info "Step 4/7: Starting Main Pipeline (Modbus RTU)..."
        $pipelineProc = Start-ProcessWithRetry -Name "MainPipeline" `
                                               -Command $VenvPython `
                                               -Arguments "-m pipeline.main" `
                                               -DelaySeconds 5
    } else {
        Write-Warn "Skipping Main Pipeline (-SkipModbus)"
    }
    
    # 5-7. Start Radio Monitors (if enabled)
    if (-not $SkipRadios) {
        Write-Info "Step 5/7: Starting WireFree Radio Monitor COM7..."
        $radio7Proc = Start-ProcessWithRetry -Name "Radio_COM7" `
                                             -Command $VenvPython `
                                             -Arguments "simple_monitor.py --config simple_config_com7.json" `
                                             -DelaySeconds 3
        
        Write-Info "Step 6/7: Starting WireFree Radio Monitor COM11..."
        $radio11Proc = Start-ProcessWithRetry -Name "Radio_COM11" `
                                              -Command $VenvPython `
                                              -Arguments "simple_monitor.py --config simple_config_com11.json" `
                                              -DelaySeconds 3
        
        Write-Info "Step 7/7: Starting WireFree Radio Monitor COM12..."
        $radio12Proc = Start-ProcessWithRetry -Name "Radio_COM12" `
                                              -Command $VenvPython `
                                              -Arguments "simple_monitor.py --config simple_config_com12.json" `
                                              -DelaySeconds 3
    } else {
        Write-Warn "Skipping Radio Monitors (-SkipRadios)"
    }
    
    # Show initial status
    Start-Sleep -Seconds 5
    Show-SystemStatus
    
    # Monitor health
    Write-Info "Monitoring system health for $DurationHours hours..."
    Write-Info "Press Ctrl+C to stop early"
    Write-Host ""
    
    $endTime = (Get-Date).AddHours($DurationHours)
    $lastStatusTime = Get-Date
    $statusInterval = 300 # Show status every 5 minutes
    
    while ((Get-Date) -lt $endTime) {
        Start-Sleep -Seconds 30
        
        # Check for crashed processes
        $crashed = @()
        foreach ($name in $Global:RunningProcesses.Keys) {
            if (-not (Test-ProcessHealth -Name $name)) {
                $crashed += $name
            }
        }
        
        if ($crashed.Count -gt 0) {
            Write-Warn "Detected crashed processes: $($crashed -join ', ')"
            
            # Attempt restart
            foreach ($name in $crashed) {
                Write-Info "Attempting to restart $name..."
                
                # Restart logic based on process name
                switch ($name) {
                    "Radio_COM7" {
                        Start-ProcessWithRetry -Name $name -Command $VenvPython `
                            -Arguments "simple_monitor.py --config simple_config_com7.json" -DelaySeconds 3
                    }
                    "Radio_COM11" {
                        Start-ProcessWithRetry -Name $name -Command $VenvPython `
                            -Arguments "simple_monitor.py --config simple_config_com11.json" -DelaySeconds 3
                    }
                    "Radio_COM12" {
                        Start-ProcessWithRetry -Name $name -Command $VenvPython `
                            -Arguments "simple_monitor.py --config simple_config_com12.json" -DelaySeconds 3
                    }
                    "MeshtasticBridge" {
                        Start-ProcessWithRetry -Name $name -Command $VenvPython `
                            -Arguments "meshtastic_bridge.py" -DelaySeconds 5
                    }
                    "MeshtasticGateway" {
                        Start-ProcessWithRetry -Name $name -Command $VenvPython `
                            -Arguments "meshtastic_gateway.py" -DelaySeconds 5
                    }
                    "MainPipeline" {
                        Start-ProcessWithRetry -Name $name -Command $VenvPython `
                            -Arguments "-m pipeline.main" -DelaySeconds 5
                    }
                }
            }
        }
        
        # Periodic status update
        if (((Get-Date) - $lastStatusTime).TotalSeconds -ge $statusInterval) {
            Show-SystemStatus
            $remaining = $endTime - (Get-Date)
            Write-Info "Time remaining: $($remaining.ToString('hh\:mm\:ss'))"
            $lastStatusTime = Get-Date
        }
    }
    
    Write-Success "`nMonitoring period complete!"
    Show-SystemStatus
    
} catch {
    Write-Err "Fatal error: $_"
    Write-Err $_.ScriptStackTrace
} finally {
    Write-Info "`nShutting down..."
    Stop-AllProcesses
    
    Write-Host "`n" + ("="*80)
    Write-Host "FINAL SUMMARY" -ForegroundColor Cyan
    Write-Host ("="*80)
    
    # Show log files
    $logFiles = Get-ChildItem -Path $logsDir -Filter "*.log" | Sort-Object LastWriteTime -Descending
    Write-Info "Log files created:"
    foreach ($log in $logFiles) {
        Write-Host "  $($log.Name) - $($log.Length) bytes" -ForegroundColor Gray
    }
    
    Write-Host "`nSystem shutdown complete`n" -ForegroundColor Green
}

