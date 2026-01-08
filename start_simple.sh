#!/bin/bash
# Startup script for Raspberry Pi / ESP32
# OI-7500 Simple Monitor

echo "Starting OI-7500 Simple Monitor..."

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Run the simple monitor
python3 simple_monitor.py

# Keep window open on error
if [ $? -ne 0 ]; then
    echo "Press Enter to exit..."
    read
fi
