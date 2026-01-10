"""
Verify Radio Configuration - Ensure all monitoring radios are SECONDARY (receive-only)
Checks that radios won't interfere with sensor network

IMPORTANT: Close any other programs (web GUI, monitor scripts) before running this!
The radios must be available for AT command access.

Laird RM024 Configuration:
- ATSP=00: SECONDARY (receive-only) - SAFE ✓
- ATSP=01: PRIMARY (transmit+receive) - UNSAFE ✗

If radios are primary, they will transmit and interfere with the sensor network!
"""

import serial
import time
import sys

# Radio configurations to check
RADIOS = {
    'Network_15': {'port': 'COM7', 'baudrate': 115200},
    'Network_20': {'port': 'COM12', 'baudrate': 115200},
    'Network_25': {'port': 'COM11', 'baudrate': 115200},
}

def enter_command_mode(ser):
    """Enter AT command mode"""
    # Clear buffer
    ser.reset_input_buffer()
    time.sleep(0.5)
    
    # Send +++
    ser.write(b'+++')
    time.sleep(1.2)  # Need to wait 1 second after +++
    
    # Check response
    response = ser.read(100)
    if b'OK' in response or len(response) > 0:
        print("    ✓ Entered command mode")
        return True
    
    print(f"    ✗ No response to +++ command")
    return False

def exit_command_mode(ser):
    """Exit AT command mode"""
    ser.write(b'ATCN\r')
    time.sleep(0.2)
    print("    ✓ Exited command mode")

def send_at_command(ser, command):
    """Send AT command and get response"""
    # Clear buffer first
    ser.reset_input_buffer()
    
    # Send command with CR
    cmd = (command + '\r').encode()
    ser.write(cmd)
    time.sleep(0.5)
    
    # Read response
    response = ser.read(1000).decode('utf-8', errors='ignore').strip()
    
    # Remove echoes and OK
    response = response.replace(command, '').replace('OK', '').strip()
    
    return response

def check_radio_config(name, config):
    """Check if radio is configured as SECONDARY (receive-only)"""
    print(f"\n{'='*60}")
    print(f"Checking {name} on {config['port']}")
    print(f"{'='*60}")
    
    try:
        # Open serial port
        ser = serial.Serial(
            port=config['port'],
            baudrate=config['baudrate'],
            timeout=1,
            rtscts=True
        )
        
        print(f"  Connected to {config['port']} at {config['baudrate']} baud")
        
        # Enter command mode
        if not enter_command_mode(ser):
            ser.close()
            return False
        
        # Query settings
        print("\n  Current Configuration:")
        
        # ATSP - Primary/Secondary mode
        sp = send_at_command(ser, 'ATSP')
        mode_str = "PRIMARY (TX/RX)" if sp == '01' else "SECONDARY (RX ONLY)"
        mode_color = "\033[91m" if sp == '01' else "\033[92m"  # Red if primary, green if secondary
        print(f"    Mode (ATSP):     {mode_color}{mode_str}\033[0m")
        
        # ATCH - RF Channel
        ch = send_at_command(ser, 'ATCH')
        print(f"    Channel (ATCH):  {ch}")
        
        # ATSY - System ID
        sy = send_at_command(ser, 'ATSY')
        print(f"    System ID (ATSY): {sy}")
        
        # ATAP - API Mode
        ap = send_at_command(ser, 'ATAP')
        api_str = {
            '00': 'Transparent',
            '01': 'API Receive',
            '02': 'API Transmit', 
            '03': 'API TX/RX'
        }.get(ap, ap)
        print(f"    API Mode (ATAP): {api_str}")
        
        # ATBD - Baud Rate
        bd = send_at_command(ser, 'ATBD')
        baud_map = {'0': '9600', '1': '19200', '2': '38400', '3': '57600', '4': '115200'}
        baud_str = baud_map.get(bd, bd)
        print(f"    Baud Rate (ATBD): {baud_str}")
        
        # Exit command mode
        exit_command_mode(ser)
        ser.close()
        
        # Check if it's safe (secondary mode)
        if sp == '01':
            print(f"\n  ⚠️  WARNING: Radio is in PRIMARY mode - it WILL TRANSMIT!")
            print(f"  This can interfere with your sensor network!")
            print(f"  Run: python fix_radio_secondary.py {config['port']}")
            return False
        else:
            print(f"\n  ✓ Radio is SAFE - Secondary mode (receive-only)")
            return True
        
    except serial.SerialException as e:
        print(f"  ✗ Cannot access {config['port']}: {e}")
        return None
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return None

def main():
    print("="*60)
    print("  OI-7500 Radio Configuration Verification")
    print("  Checking all monitoring radios are SECONDARY (RX only)")
    print("="*60)
    
    results = {}
    
    for name, config in RADIOS.items():
        result = check_radio_config(name, config)
        results[name] = result
        time.sleep(0.5)  # Small delay between radios
    
    # Summary
    print("\n" + "="*60)
    print("  SUMMARY")
    print("="*60)
    
    all_safe = True
    for name, result in results.items():
        if result is None:
            print(f"  {name:15s} - ⚠️  Could not check (port busy?)")
        elif result:
            print(f"  {name:15s} - ✓ SAFE (Secondary)")
        else:
            print(f"  {name:15s} - ✗ UNSAFE (Primary - will transmit!)")
            all_safe = False
    
    print("="*60)
    
    if all_safe and all(r for r in results.values() if r is not None):
        print("\n✓ All radios are SAFE - configured as secondaries")
        print("  They will only receive, not transmit")
        return 0
    else:
        print("\n⚠️  ACTION REQUIRED:")
        print("  Some radios are configured as PRIMARY (transmit mode)")
        print("  Run: python fix_radio_secondary.py COM<X>")
        return 1

if __name__ == '__main__':
    import sys
    sys.exit(main())
