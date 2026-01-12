#!/usr/bin/env python3
"""
Radio Probe Tool - Identify radio type and configuration
"""

import serial
import time


def try_baud_rate(port, baud):
    """Try to connect at specific baud rate and look for data"""
    print(f"\nTrying {baud} baud...")
    try:
        ser = serial.Serial(port, baud, timeout=0.5)
        
        # Try AT command first
        time.sleep(1.2)
        ser.write(b'+++')
        time.sleep(1.2)
        
        response = b''
        if ser.in_waiting > 0:
            response = ser.read(ser.in_waiting)
            print(f"  Response to +++: {response}")
        
        # Try ATI command
        ser.write(b'ATI\r')
        time.sleep(0.5)
        if ser.in_waiting > 0:
            response = ser.read(ser.in_waiting)
            print(f"  Response to ATI: {response.decode('utf-8', errors='ignore')}")
            ser.close()
            return True
        
        # Listen for any data
        print(f"  Listening for 5 seconds...")
        data_bytes = []
        start = time.time()
        while time.time() - start < 5:
            if ser.in_waiting > 0:
                byte = ser.read(1)
                data_bytes.append(byte[0])
                if len(data_bytes) >= 20:
                    break
            time.sleep(0.01)
        
        if data_bytes:
            hex_str = ' '.join(f'{b:02X}' for b in data_bytes[:20])
            print(f"  Raw data: {hex_str}")
            
            # Check for 0x7E (XBee/Laird API frame)
            if 0x7E in data_bytes:
                print(f"  ✓ Detected API mode frames (0x7E)")
                ser.close()
                return True
            
            # Check for OI Gen2 protocol patterns
            if any(b < 32 and b not in [0x7E, 0x0D, 0x0A] for b in data_bytes[:5]):
                print(f"  ✓ Detected binary data (possibly Gen2 protocol)")
                ser.close()
                return True
        else:
            print(f"  No data received")
        
        ser.close()
        return False
        
    except Exception as e:
        print(f"  Error: {e}")
        return False


def probe_radio(port):
    """Probe radio to determine configuration"""
    print(f"{'='*70}")
    print(f"  Radio Probe Tool - {port}")
    print(f"{'='*70}")
    
    common_bauds = [9600, 19200, 38400, 57600, 115200]
    
    print("\nScanning common baud rates...")
    for baud in common_bauds:
        if try_baud_rate(port, baud):
            print(f"\n✓ Found working configuration at {baud} baud")
            break
    else:
        print(f"\n✗ No response at any common baud rate")
        print("\nPossible issues:")
        print("  1. Wrong COM port")
        print("  2. Radio not powered")
        print("  3. TX/RX lines swapped")
        print("  4. Non-standard baud rate")
        print("  5. Radio module not working")


if __name__ == "__main__":
    import sys
    port = sys.argv[1] if len(sys.argv) > 1 else 'COM7'
    
    try:
        probe_radio(port)
    except KeyboardInterrupt:
        print("\n\nProbe cancelled")
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
