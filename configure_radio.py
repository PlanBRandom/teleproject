#!/usr/bin/env python3
"""
Laird Radio Configuration Utility
Configure Laird LT1110/RM024 radio modules for OI Gen2 wireless protocol
"""

import serial
import time
import sys


def send_at_command(ser, command, wait=0.3):
    """Send AT command and return response"""
    ser.write(command)
    time.sleep(wait)
    response = ser.read(ser.in_waiting or 1024).decode('ascii', errors='ignore')
    return response.strip()


def enter_command_mode(ser):
    """Enter AT command mode"""
    # Must have 1 second of silence before +++
    time.sleep(1.2)
    ser.write(b'+++')
    time.sleep(1.5)  # Wait for OK response
    response = ser.read(ser.in_waiting or 100).decode('ascii', errors='ignore')
    return 'OK' in response


def exit_command_mode(ser):
    """Exit AT command mode"""
    send_at_command(ser, b'ATCN\r')


def configure_radio(port, network_channel, is_primary=False, baud=9600):
    """Configure Laird radio module"""
    
    print(f"\n{'='*60}")
    print(f"  Laird Radio Configuration")
    print(f"{'='*60}")
    print(f"Port:            {port}")
    print(f"Network Channel: {network_channel}")
    print(f"Mode:            {'PRIMARY (transmit/receive)' if is_primary else 'SECONDARY (receive only)'}")
    print(f"Baud Rate:       {baud}")
    print(f"System ID:       37 (OI standard)")
    print(f"API Mode:        Enabled (0x7E frames)")
    print(f"{'='*60}\n")
    
    try:
        # Open serial connection
        ser = serial.Serial(port, baud, timeout=1)
        print(f"✓ Connected to {port}\n")
        time.sleep(0.5)
        
        # Enter command mode
        print("Entering command mode...")
        if not enter_command_mode(ser):
            print("⚠️  No OK response, but continuing...")
        
        # Baud rate mapping
        baud_codes = {1200: 0, 2400: 1, 4800: 2, 9600: 3, 19200: 4, 
                     38400: 5, 57600: 6, 115200: 7}
        baud_code = baud_codes.get(baud, 3)
        
        # Configure radio
        commands = [
            (f'ATDN{network_channel}\r', f'Set Network Channel to {network_channel}'),
            ('ATSY37\r', 'Set System ID to 37 (OI standard)'),
            (f'ATCE{1 if is_primary else 0}\r',
             'Set Server Mode ' + ('ON (primary monitor)' if is_primary else 'OFF (secondary)')),
            (f'ATSP{0 if is_primary else 1}\r', 
             'Set Sniff Permit ' + ('OFF (primary)' if is_primary else 'ON (secondary)')),
            ('ATAP1\r', 'Enable API mode (0x7E frames)'),
            (f'ATBD{baud_code}\r', f'Set baud rate to {baud}'),
            ('ATWR\r', 'Write configuration to EEPROM'),
        ]
        
        print("Configuring radio...\n")
        for cmd, desc in commands:
            print(f"  {desc}...")
            response = send_at_command(ser, cmd.encode('ascii'))
            if 'OK' in response or 'AOK' in response or response == '':
                print(f"    ✓ OK")
            else:
                print(f"    Response: {response}")
        
        # Exit command mode
        print("\nExiting command mode...")
        exit_command_mode(ser)
        time.sleep(0.5)
        
        # Verify configuration
        print("\nVerifying configuration...")
        if enter_command_mode(ser):
            
            queries = [
                ('ATDN?\r', 'Network Channel'),
                ('ATSY?\r', 'System ID'),
                ('ATCE?\r', 'Server Mode'),
                ('ATSP?\r', 'Sniff Permit'),
                ('ATAP?\r', 'API Mode'),
            ]
            
            print()
            for query, label in queries:
                response = send_at_command(ser, query.encode('ascii'))
                # Parse numeric response
                value = ''.join(c for c in response if c.isdigit() or c == '-')
                if value:
                    print(f"  {label:20s} = {value}")
            
            exit_command_mode(ser)
        
        ser.close()
        
        print(f"\n{'='*60}")
        print("✓ Configuration complete!")
        print(f"{'='*60}")
        print("\nRadio is ready to use. Power cycle the module to apply settings.")
        print("\nNext steps:")
        print("  1. Disconnect and reconnect the radio module")
        print("  2. Run: python hardware_test.py")
        print(f"  3. Use channel {network_channel} when prompted")
        
        return True
        
    except serial.SerialException as e:
        print(f"\n✗ Serial error: {e}")
        print("\nTroubleshooting:")
        print("  - Check COM port is correct")
        print("  - Ensure no other program is using the port")
        print("  - Verify radio module is connected")
        return False
    except Exception as e:
        print(f"\n✗ Error: {e}")
        return False


def main():
    """Main configuration wizard"""
    print("\n" + "="*60)
    print("  OI Gen2 Wireless - Laird Radio Configuration Wizard")
    print("="*60)
    
    # Get COM port
    print("\nEnter COM port (e.g., COM11): ", end='')
    port = input().strip()
    if not port:
        print("✗ No port specified")
        return
    
    # Get network channel
    print("\nEnter network channel (1-78).")
    print("  Common: 5 (OI default), 25 (custom)")
    print("Channel: ", end='')
    try:
        channel = int(input().strip() or "25")
        if channel < 1 or channel > 78:
            print("✗ Channel must be 1-78")
            return
    except ValueError:
        print("✗ Invalid channel number")
        return
    
    # Get mode
    print("\nSelect mode:")
    print("  1. SECONDARY - Receive only (passive listener)")
    print("     • Receives all broadcasts on the network")
    print("     • Does not transmit (won't interfere)")
    print("     • Best for monitoring/data collection")
    print()
    print("  2. PRIMARY - Transmit and receive (monitor replacement)")
    print("     • Can send test packets")
    print("     • Acts as network participant")
    print("     • Use only if replacing a monitor")
    print()
    print("Mode (1=secondary, 2=primary, default 1): ", end='')
    mode_input = input().strip()
    is_primary = mode_input == '2'
    
    # Get baud rate
    print("\nBaud rate (default 9600): ", end='')
    baud_input = input().strip()
    baud = int(baud_input) if baud_input else 9600
    
    if baud not in [1200, 2400, 4800, 9600, 19200, 38400, 57600, 115200]:
        print(f"⚠️  Non-standard baud rate {baud}, using 9600")
        baud = 9600
    
    # Confirm
    print("\n" + "-"*60)
    print("Configuration Summary:")
    print(f"  Port:    {port}")
    print(f"  Channel: {channel}")
    print(f"  Mode:    {'PRIMARY' if is_primary else 'SECONDARY'}")
    print(f"  Baud:    {baud}")
    print("-"*60)
    print("\nProceed? (y/n): ", end='')
    if not input().strip().lower().startswith('y'):
        print("Cancelled")
        return
    
    # Configure
    configure_radio(port, channel, is_primary, baud)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nCancelled by user")
    except Exception as e:
        print(f"\n\n✗ Unexpected error: {e}")
        sys.exit(1)
