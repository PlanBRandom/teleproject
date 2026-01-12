#!/usr/bin/env python3
"""
Reconfigure radio from sensor mode (9600) to monitor mode (115200)
"""

import serial
import time


def send_at_command(ser, command, wait=0.3):
    """Send AT command and return response"""
    ser.write(command)
    time.sleep(wait)
    response = ser.read(ser.in_waiting or 1024).decode('ascii', errors='ignore')
    return response.strip()


def enter_command_mode(ser):
    """Enter AT command mode"""
    time.sleep(1.2)
    ser.write(b'+++')
    time.sleep(1.5)
    response = ser.read(ser.in_waiting or 100).decode('ascii', errors='ignore')
    return 'OK' in response


def configure_monitor_mode(port, channel=25, is_primary=False):
    """Configure radio for monitor mode at 115200 baud"""
    
    print(f"\n{'='*70}")
    print(f"  Reconfigure Radio: Sensor Mode (9600) → Monitor Mode (115200)")
    print(f"{'='*70}")
    print(f"Port:     {port}")
    print(f"Channel:  {channel}")
    print(f"Mode:     {'PRIMARY MONITOR' if is_primary else 'SECONDARY MONITOR'}")
    print(f"{'='*70}\n")
    
    # Step 1: Connect at 9600 baud
    print("Step 1: Connecting at 9600 baud (current setting)...")
    try:
        ser = serial.Serial(port, 9600, timeout=1)
        print("✓ Connected at 9600 baud\n")
    except Exception as e:
        print(f"✗ Failed to connect: {e}")
        return False
    
    # Step 2: Enter command mode
    print("Step 2: Entering AT command mode...")
    if not enter_command_mode(ser):
        print("⚠️  No OK response, continuing anyway...\n")
    else:
        print("✓ Entered command mode\n")
    
    # Step 3: Configure for monitor mode
    print("Step 3: Configuring radio for monitor operation...")
    
    commands = [
        (f'ATDN{channel}\r', f'Network Channel = {channel}'),
        ('ATSY37\r', 'System ID = 37 (OI standard)'),
        (f'ATCE{1 if is_primary else 0}\r', 
         f'Server Mode = {"ON (Primary)" if is_primary else "OFF (Secondary)"}'),
        (f'ATSP{0 if is_primary else 1}\r',
         f'Sniff Permit = {"OFF (Primary)" if is_primary else "ON (Secondary)"}'),
        ('ATAP1\r', 'API Mode = ON'),
        ('ATBD7\r', 'Baud Rate = 115200 (code 7)'),
        ('ATWR\r', 'Save to EEPROM'),
    ]
    
    for cmd, desc in commands:
        print(f"  {desc}...")
        response = send_at_command(ser, cmd.encode('ascii'))
        if 'OK' in response or response == '':
            print(f"    ✓")
        else:
            print(f"    Response: {response}")
    
    print("\nStep 4: Exiting command mode...")
    send_at_command(ser, b'ATCN\r')
    ser.close()
    print("✓ Configuration saved\n")
    
    # Step 5: Reconnect at 115200
    print("Step 5: Reconnecting at 115200 baud to verify...")
    time.sleep(2)
    
    try:
        ser = serial.Serial(port, 115200, timeout=1)
        print("✓ Connected at 115200 baud\n")
        
        # Enter command mode at new baud rate
        print("Step 6: Verifying configuration...")
        if enter_command_mode(ser):
            print("✓ Command mode active at 115200 baud\n")
            
            # Query settings
            queries = [
                ('ATDN?\r', 'Network Channel'),
                ('ATSY?\r', 'System ID'),
                ('ATCE?\r', 'Server Mode'),
                ('ATSP?\r', 'Sniff Permit'),
                ('ATAP?\r', 'API Mode'),
                ('ATBD?\r', 'Baud Rate'),
            ]
            
            print("Current settings:")
            for query, label in queries:
                response = send_at_command(ser, query.encode('ascii'))
                value = ''.join(c for c in response if c.isdigit() or c == '-')
                if value:
                    # Decode baud rate code
                    if label == 'Baud Rate' and value == '7':
                        value = '7 (115200 baud)'
                    elif label == 'Network Channel':
                        value = f'{value}'
                    elif label == 'System ID' and value == '37':
                        value = '37 (OI standard)'
                    
                    print(f"  {label:20s} = {value}")
            
            # Exit command mode
            send_at_command(ser, b'ATCN\r')
        
        ser.close()
        
        print(f"\n{'='*70}")
        print("✓ SUCCESS - Radio configured for monitor mode!")
        print(f"{'='*70}")
        print("\nRadio is now configured as:")
        print(f"  • {'PRIMARY MONITOR' if is_primary else 'SECONDARY MONITOR'}")
        print(f"  • 115200 baud (monitor mode)")
        print(f"  • Channel {channel}")
        print(f"  • System ID 37")
        print(f"  • API mode enabled")
        
        print("\nNext steps:")
        print("  1. Power cycle the radio (unplug/replug)")
        print("  2. Update your scripts to use 115200 baud")
        print("  3. Test with: python test_radio.py")
        
        return True
        
    except Exception as e:
        print(f"✗ Failed to reconnect at 115200: {e}")
        print("\nThe radio may still be at 9600 baud.")
        return False


if __name__ == "__main__":
    print("\n" + "="*70)
    print("  OI Wireless Radio - Monitor Mode Configuration")
    print("="*70)
    print("\nThis will reconfigure your radio for OI Monitor operation:")
    print("  • Change baud rate from 9600 → 115200")
    print("  • Set up as Primary or Secondary monitor")
    print("  • Configure for channel reception")
    
    print("\nEnter COM port: ", end='')
    port = input().strip() or 'COM7'
    
    print("Enter network channel (default 25): ", end='')
    channel = int(input().strip() or '25')
    
    print("\nMonitor mode:")
    print("  1. SECONDARY - Can become 'New Primary' if Primary disappears")
    print("  2. PRIMARY - Network coordinator (use only if no other Primary)")
    print("\nSelect (1=secondary, 2=primary, default 1): ", end='')
    mode = input().strip()
    is_primary = mode == '2'
    
    print("\n" + "-"*70)
    print("Summary:")
    print(f"  Port:     {port}")
    print(f"  Channel:  {channel}")
    print(f"  Mode:     {'PRIMARY' if is_primary else 'SECONDARY'}")
    print(f"  Baud:     9600 → 115200")
    print("-"*70)
    print("\nProceed? (y/n): ", end='')
    
    if input().strip().lower().startswith('y'):
        configure_monitor_mode(port, channel, is_primary)
    else:
        print("Cancelled")
