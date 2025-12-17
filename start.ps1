# Quick Start Script for OI-7530/7010 Modbus-MQTT Bridge
# This script helps you get started quickly

Write-Host "==================================" -ForegroundColor Cyan
Write-Host "OI-7530/7010 Modbus-MQTT Bridge" -ForegroundColor Cyan
Write-Host "==================================" -ForegroundColor Cyan
Write-Host ""

# Check Python
Write-Host "[1/5] Checking Python..." -ForegroundColor Yellow
try {
    $pythonVersion = python --version 2>&1
    Write-Host "✓ Found: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "✗ Python not found! Please install Python 3.8+" -ForegroundColor Red
    exit 1
}

# Install dependencies
Write-Host ""
Write-Host "[2/5] Installing Python dependencies..." -ForegroundColor Yellow
pip install -r requirements.txt
if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Dependencies installed" -ForegroundColor Green
} else {
    Write-Host "✗ Failed to install dependencies" -ForegroundColor Red
    exit 1
}

# Check for config
Write-Host ""
Write-Host "[3/5] Checking configuration..." -ForegroundColor Yellow
if (Test-Path "config.yaml") {
    Write-Host "✓ Found config.yaml" -ForegroundColor Green
    
    # Ask if user wants to edit
    $edit = Read-Host "Do you want to edit the config now? (y/n)"
    if ($edit -eq "y") {
        notepad config.yaml
    }
} else {
    Write-Host "✗ config.yaml not found!" -ForegroundColor Red
    exit 1
}

# List available COM ports
Write-Host ""
Write-Host "[4/5] Available COM ports:" -ForegroundColor Yellow
$ports = [System.IO.Ports.SerialPort]::getportnames()
if ($ports) {
    foreach ($port in $ports) {
        Write-Host "  - $port" -ForegroundColor Cyan
    }
} else {
    Write-Host "  No COM ports detected" -ForegroundColor Gray
}

# Generate dashboards
Write-Host ""
Write-Host "[5/5] Generating Home Assistant dashboards..." -ForegroundColor Yellow
python generate_channels.py
if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Dashboards generated in configs/lovelace/" -ForegroundColor Green
} else {
    Write-Host "⚠ Dashboard generation failed (non-critical)" -ForegroundColor Yellow
}

# Ready to start
Write-Host ""
Write-Host "==================================" -ForegroundColor Green
Write-Host "Setup Complete!" -ForegroundColor Green
Write-Host "==================================" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "  1. Edit config.yaml with your Modbus and MQTT settings"
Write-Host "  2. Run: python -m pipeline.main"
Write-Host "  3. Import dashboards from configs/lovelace/ into Home Assistant"
Write-Host ""
Write-Host "For ESP32 deployment:" -ForegroundColor Cyan
Write-Host "  1. Install ESPHome: pip install esphome"
Write-Host "  2. Edit config.esphome.yaml and secrets.yaml"
Write-Host "  3. Run: esphome run config.esphome.yaml"
Write-Host ""

# Ask if user wants to start now
$start = Read-Host "Start the bridge now? (y/n)"
if ($start -eq "y") {
    Write-Host ""
    Write-Host "Starting bridge..." -ForegroundColor Cyan
    python -m pipeline.main -v
}
