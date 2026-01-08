#!/usr/bin/env python3
"""
Start Multi-Network Monitor with Modbus Polling
Launches both the Modbus bridge (to generate Modbus traffic) and the monitor simultaneously.
"""

import subprocess
import sys
import time
import signal
import os
from pathlib import Path

# Duration for test
MONITOR_DURATION_HOURS = 12  # Default to 12 hours

# Process handles
modbus_bridge_process = None
monitor_process = None

def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully"""
    print("\n\n🛑 Stopping all processes...")
    
    if monitor_process:
        print("  Stopping monitor...")
        monitor_process.terminate()
        try:
            monitor_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            monitor_process.kill()
    
    if modbus_bridge_process:
        print("  Stopping Modbus bridge...")
        modbus_bridge_process.terminate()
        try:
            modbus_bridge_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            modbus_bridge_process.kill()
    
    print("✓ All processes stopped")
    sys.exit(0)

def main():
    global modbus_bridge_process, monitor_process
    
    # Register signal handler
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    print("="*80)
    print("MULTI-NETWORK MONITOR WITH MODBUS POLLING")
    print("="*80)
    print()
    print("This will start:")
    print("  1. Modbus poller - continuously polls all 3 monitors")
    print("     • OI-7010 (slave 10) - 32 channels")
    print("     • OI-7530 (slave 30) - 32 channels") 
    print("     • OI-7032 (slave 32) - 32 channels")
    print("  2. Multi-network monitor - captures radio + Modbus traffic")
    print()
    print(f"Duration: {MONITOR_DURATION_HOURS} hours")
    print()
    print("Press Ctrl+C to stop both processes early")
    print("="*80)
    print()
    
    # Get Python executable
    python_exe = sys.executable
    
    # Start Modbus bridge (runs continuously)
    print("🔌 Starting Modbus poller...")
    try:
        modbus_bridge_process = subprocess.Popen(
            [python_exe, "poll_all_monitors.py"],
            cwd=os.path.dirname(os.path.abspath(__file__)),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=1,
            universal_newlines=True
        )
        print("  ✓ Modbus poller started (PID: {})".format(modbus_bridge_process.pid))
        
        # Give it time to connect
        time.sleep(3)
        
        # Check if it's still running
        if modbus_bridge_process.poll() is not None:
            # Process died
            stdout, stderr = modbus_bridge_process.communicate()
            print("  ❌ Modbus poller failed to start!")
            print("\nOUTPUT:")
            print(stdout)
            return 1
        
    except Exception as e:
        print(f"  ❌ Failed to start Modbus poller: {e}")
        return 1
    
    # Start monitor (runs for specified duration)
    print("\n📡 Starting multi-network monitor...")
    try:
        monitor_cmd = [
            python_exe,
            "start_12hr_monitor.py"
        ]
        
        # Override duration if needed
        if MONITOR_DURATION_HOURS != 12:
            # Would need to modify start_12hr_monitor.py to accept duration arg
            pass
        
        monitor_process = subprocess.Popen(
            monitor_cmd,
            cwd=os.path.dirname(os.path.abspath(__file__))
        )
        print(f"  ✓ Monitor started (PID: {monitor_process.pid})")
        
    except Exception as e:
        print(f"  ❌ Failed to start monitor: {e}")
        if modbus_bridge_process:
            modbus_bridge_process.terminate()
        return 1
    
    print()
    print("="*80)
    print("✓ Both processes running!")
    print("="*80)
    print()
    print("Modbus poller is querying all 3 monitors every 5 seconds")
    print("Monitor is capturing all radio traffic and Modbus requests/responses")
    print()
    print("Wait for monitor to complete or press Ctrl+C to stop early...")
    print()
    
    # Wait for monitor to complete
    try:
        monitor_process.wait()
        print("\n✓ Monitor completed successfully")
        
    except KeyboardInterrupt:
        print("\n\n🛑 Interrupted by user")
    
    finally:
        # Clean up
        if modbus_bridge_process and modbus_bridge_process.poll() is None:
            print("Stopping Modbus poller...")
            modbus_bridge_process.terminate()
            try:
                modbus_bridge_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                modbus_bridge_process.kill()
            print("  ✓ Modbus poller stopped")
    
    print("\n✓ All processes completed")
    return 0

if __name__ == '__main__':
    sys.exit(main())
