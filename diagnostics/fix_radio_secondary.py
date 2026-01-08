"""
Fix Radio Configuration - Force radio to SECONDARY (receive-only) mode
Use this if verify_radio_config.py shows a radio in PRIMARY mode
"""

import serial
import time
import sys

def enter_command_mode(ser):
    """Enter AT command mode"""
    ser.reset_input_buffer()
    time.sleep(0.1)
    
    cmd = b'AT+++\r'
    ser.write(cmd)
    time.sleep(0.3)
    
    response = ser.read(100)
    if b'\xCC\x43\x4F\x4D' in response:
        print("  ✓ Entered command mode")
        return True
    else:
        print(f"  ✗ Failed to enter command mode")
        return False

def exit_command_mode(ser):
    """Exit AT command mode"""
    cmd = bytes([0xCC, 0x41, 0x54, 0x4F, 0x0D])
    ser.write(cmd)
    time.sleep(0.2)
    print("  ✓ Exited command mode")

def send_at_command(ser, command):
    """Send AT command and get response"""
    cmd = (command + '\r').encode()
    ser.write(cmd)
    time.sleep(0.3)
    response = ser.read(100).decode('utf-8', errors='ignore')
    return response.replace('OK', '').strip()

def fix_radio_to_secondary(port, baudrate=115200):
    """Configure radio as SECONDARY (receive-only)"""
    print(f"\n{'='*60}")
    print(f"  Fixing Radio on {port}")
    print(f"  Setting to SECONDARY (receive-only) mode")
    print(f"{'='*60}\n")
    
    try:
        ser = serial.Serial(port=port, baudrate=baudrate, timeout=1, rtscts=True)
        print(f"✓ Connected to {port} at {baudrate} baud")
        
        # Enter command mode
        if not enter_command_mode(ser):
            ser.close()
            return False
        
        # Check current mode
        current_mode = send_at_command(ser, 'ATSP')
        print(f"\nCurrent mode: {'PRIMARY' if current_mode == '01' else 'SECONDARY'}")
        
        if current_mode != '00':
            print("\n⚠️  Radio is in PRIMARY mode - fixing now...")
            
            # Set to SECONDARY (00 = receive only)
            print("  Setting ATSP00 (Secondary/Receive-only)")
            send_at_command(ser, 'ATSP00')
            
            # Verify
            new_mode = send_at_command(ser, 'ATSP')
            if new_mode == '00':
                print("  ✓ Mode changed to SECONDARY")
            else:
                print(f"  ✗ Mode change failed: {new_mode}")
                exit_command_mode(ser)
                ser.close()
                return False
            
            # Save to EEPROM
            print("  Saving configuration to EEPROM...")
            send_at_command(ser, 'ATWR')
            time.sleep(0.5)
            print("  ✓ Configuration saved")
            
            # Reset radio to apply
            print("  Resetting radio to apply changes...")
            send_at_command(ser, 'ATFR')
            time.sleep(2.0)
            
            print("\n✓ Radio is now SECONDARY (receive-only)")
            print("  It will NOT transmit or interfere with sensor network")
        else:
            print("\n✓ Radio is already in SECONDARY mode")
            exit_command_mode(ser)
        
        ser.close()
        return True
        
    except serial.SerialException as e:
        print(f"\n✗ Cannot access {port}: {e}")
        print("  Make sure no other programs are using this port")
        return False
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    if len(sys.argv) < 2:
        print("Usage: python fix_radio_secondary.py <COM_PORT> [baudrate]")
        print("\nExample:")
        print("  python fix_radio_secondary.py COM7")
        print("  python fix_radio_secondary.py COM11 115200")
        return 1
    
    port = sys.argv[1]
    baudrate = int(sys.argv[2]) if len(sys.argv) > 2 else 115200
    
    success = fix_radio_to_secondary(port, baudrate)
    
    if success:
        print("\n" + "="*60)
        print("  ✓ SUCCESS - Radio configured as SECONDARY")
        print("="*60)
        print("\nThe radio will now only receive (not transmit)")
        print("It's safe to use for monitoring without interfering")
        return 0
    else:
        print("\n" + "="*60)
        print("  ✗ FAILED - Could not configure radio")
        print("="*60)
        return 1

if __name__ == '__main__':
    sys.exit(main())
