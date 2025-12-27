#!/usr/bin/env python3
"""
Radio Diagnostic Tool - Check and fix Laird radio configuration
"""

import serial
import time
import sys


def send_at_command(ser, command, wait_time=0.5):
    """Send AT command and return response"""
    # Clear buffer
    ser.reset_input_buffer()
    
    # Send command with carriage return
    cmd = command + '\r'
    ser.write(cmd.encode())
    time.sleep(wait_time)
    
    # Read response
    response = b''
    while ser.in_waiting > 0:
        response += ser.read(ser.in_waiting)
        time.sleep(0.1)
    
    return response.decode('utf-8', errors='ignore').strip()


def enter_command_mode(ser):
    """Enter AT command mode"""
    print("Entering command mode...")
    time.sleep(1.2)  # Guard time before +++
    ser.write(b'+++')
    time.sleep(1.2)  # Guard time after +++
    
    # Read response
    response = b''
    time.sleep(0.5)
    while ser.in_waiting > 0:
        response += ser.read(ser.in_waiting)
        time.sleep(0.1)
    
    resp_str = response.decode('utf-8', errors='ignore').strip()
    if 'OK' in resp_str:
        print("✓ Entered command mode")
        return True
    else:
        print(f"✗ Failed to enter command mode: {resp_str}")
        return False


def exit_command_mode(ser):
    """Exit AT command mode"""
    print("\nExiting command mode...")
    response = send_at_command(ser, 'ATCN')
    if 'OK' in response:
        print("✓ Exited command mode")
        return True
    return False


def diagnose_radio(port):
    """Diagnose radio configuration"""
    print(f"{'='*70}")
    print(f"  OI Radio Diagnostic Tool")
    print(f"{'='*70}\n")
    
    print(f"Opening {port} at 9600 baud...")
    try:
        ser = serial.Serial(port, 9600, timeout=1)
        print(f"✓ Connected to {port}")
    except Exception as e:
        print(f"✗ Failed to open {port}: {e}")
        return False
    
    # Enter command mode
    if not enter_command_mode(ser):
        print("\n⚠️  Could not enter command mode.")
        print("   This might mean:")
        print("   1. Radio is already in command mode")
        print("   2. Radio is busy receiving/transmitting")
        print("   3. Guard time violated (need 1 second silence)")
        print("\nTrying commands anyway...")
    
    # Get model info
    print("\n" + "-"*70)
    print("RADIO INFORMATION")
    print("-"*70)
    
    response = send_at_command(ser, 'ATI')
    print(f"Model Info:\n{response}")
    
    # Get current settings
    print("\n" + "-"*70)
    print("CURRENT CONFIGURATION")
    print("-"*70)
    
    settings = send_at_command(ser, 'ATS')
    print(settings)
    
    # Parse critical settings
    print("\n" + "-"*70)
    print("OI-CRITICAL SETTINGS CHECK")
    print("-"*70)
    
    # Check individual settings
    checks = {
        'ATBD': ('Baud Rate', '3', '9600 baud'),
        'ATDN': ('Network Channel', '5', 'OI default channel 5'),
        'ATSY': ('System ID', '37', 'OI standard'),
        'ATAP': ('API Mode', '1', 'API mode enabled'),
        'ATCE': ('Server Mode', None, 'Coordinator/Server'),
        'ATSP': ('Sniff Permit', None, 'Listening mode'),
    }
    
    issues = []
    for cmd, (name, expected, description) in checks.items():
        response = send_at_command(ser, cmd, 0.3)
        response = response.replace('OK', '').strip()
        
        status = '✓' if (expected is None or response == expected) else '✗'
        print(f"{status} {name:20} = {response:10} ({description})")
        
        if expected and response != expected:
            issues.append((cmd, name, expected, response))
    
    # Recommend configuration
    if issues:
        print("\n" + "-"*70)
        print("⚠️  CONFIGURATION ISSUES DETECTED")
        print("-"*70)
        
        for cmd, name, expected, current in issues:
            print(f"✗ {name}: Expected {expected}, got {current}")
        
        print("\nWould you like to fix these issues? (y/n): ", end='')
        fix = input().strip().lower()
        
        if fix.startswith('y'):
            print("\nFixing configuration...")
            
            for cmd, name, expected, current in issues:
                fix_cmd = f"{cmd}{expected}"
                print(f"  Setting {name} to {expected}...")
                response = send_at_command(ser, fix_cmd, 0.5)
                if 'OK' in response or 'ok' in response.lower():
                    print(f"    ✓ {name} updated")
                else:
                    print(f"    ✗ Failed: {response}")
            
            # Write to flash
            print("\n  Writing configuration to flash...")
            response = send_at_command(ser, 'ATWR')
            if 'OK' in response:
                print("    ✓ Configuration saved")
            else:
                print(f"    ✗ Save failed: {response}")
    else:
        print("\n✓ All critical settings correct!")
    
    # Configure for OI operation
    print("\n" + "-"*70)
    print("OPERATING MODE CONFIGURATION")
    print("-"*70)
    
    print("\nHow should this radio operate?")
    print("  1. PRIMARY MONITOR - Acts as replacement OI-7500 monitor (receives all sensors)")
    print("  2. SECONDARY MONITOR - Passive listener (does not ACK sensors)")
    print("  3. DIRECT RECEIVER - Standalone listener (no monitor in system)")
    print("\nSelect mode (1-3): ", end='')
    
    mode_choice = input().strip()
    
    if mode_choice == '1':
        print("\nConfiguring as PRIMARY MONITOR...")
        commands = [
            ('ATCE1', 'Enable Server Mode'),
            ('ATSP0', 'Disable Sniff Permit (Primary ACKs only)'),
        ]
    elif mode_choice == '2':
        print("\nConfiguring as SECONDARY MONITOR...")
        commands = [
            ('ATCE0', 'Disable Server Mode'),
            ('ATSP1', 'Enable Sniff Permit (Listen to all)'),
        ]
    else:
        print("\nConfiguring as DIRECT RECEIVER...")
        commands = [
            ('ATCE0', 'Disable Server Mode'),
            ('ATSP1', 'Enable Sniff Permit (Listen to all)'),
        ]
    
    for cmd, description in commands:
        print(f"  {description}...")
        response = send_at_command(ser, cmd, 0.5)
        if 'OK' in response:
            print(f"    ✓ {cmd}")
        else:
            print(f"    ✗ Failed: {response}")
    
    # Save configuration
    print("\n  Saving configuration...")
    response = send_at_command(ser, 'ATWR')
    if 'OK' in response:
        print("    ✓ Configuration saved to flash")
    
    # Exit command mode
    exit_command_mode(ser)
    
    # Final verification
    print("\n" + "="*70)
    print("  DIAGNOSTIC COMPLETE")
    print("="*70)
    print("\nYour radio is now configured and ready to receive OI sensor packets.")
    print("Run 'python test_radio.py' to test reception.")
    
    ser.close()
    return True


if __name__ == "__main__":
    if len(sys.argv) > 1:
        port = sys.argv[1]
    else:
        port = 'COM7'  # Default
    
    try:
        diagnose_radio(port)
    except KeyboardInterrupt:
        print("\n\nDiagnostic cancelled by user")
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
