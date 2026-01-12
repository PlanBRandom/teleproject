#!/usr/bin/env python3
"""
Serial port sniffer to capture what Laird utility sends.

INSTRUCTIONS:
1. Close Laird utility if open
2. Run this script - it will monitor COM7
3. Open Laird utility and connect to COM7
4. Send an AT command with "AT Enter/Exit Command Mode" checked
5. Watch what bytes the utility sends!

This will reveal the "virtual CMD/DATA" command sequence.
"""

import serial
import time
import sys

def sniff_port(port, baudrate=115200):
    """Monitor serial port traffic in both directions."""
    print(f"\n{'='*70}")
    print(f"Serial Port Sniffer - {port} @ {baudrate} baud")
    print(f"{'='*70}")
    print("\nInstructions:")
    print("1. This script is now monitoring the port")
    print("2. Open Laird utility in ANOTHER window")
    print("3. Connect Laird utility to the SAME port")
    print("4. Check 'AT Enter/Exit Command Mode' checkbox")
    print("5. Send an AT command (like ATCH to read channel)")
    print("6. Watch the output below to see what Laird sends!")
    print("\nNote: Both programs accessing the port may cause conflicts.")
    print("If that happens, we'll use a different approach.")
    print(f"\nMonitoring {port}... Press Ctrl+C to stop\n")
    
    try:
        ser = serial.Serial(
            port=port,
            baudrate=baudrate,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=0.1,
            rtscts=True
        )
        ser.rts = True
        
        last_time = time.time()
        
        while True:
            if ser.in_waiting > 0:
                data = ser.read(ser.in_waiting)
                now = time.time()
                gap = now - last_time
                
                # Show timestamp and gap
                print(f"\n[{time.strftime('%H:%M:%S')}] Gap: {gap:.3f}s | {len(data)} bytes")
                
                # Hex dump
                hex_str = ' '.join([f'{b:02X}' for b in data])
                print(f"  HEX: {hex_str}")
                
                # ASCII (if printable)
                ascii_str = ''.join([chr(b) if 32 <= b < 127 else '.' for b in data])
                print(f"  ASCII: {ascii_str}")
                
                # Check for patterns
                if b'+++' in data:
                    print("  ** DETECTED: +++ (AT command mode entry)")
                
                if b'ATCN' in data:
                    print("  ** DETECTED: ATCN (exit command mode)")
                
                if b'ATCH' in data:
                    print("  ** DETECTED: ATCH (read channel)")
                
                # Check for special control sequences
                if b'\x1B' in data:  # ESC
                    print("  ** DETECTED: ESC character")
                
                if b'\x00' in data:
                    print("  ** DETECTED: NULL bytes (possible binary command)")
                
                if data.startswith(b'\xCC'):
                    print("  ** DETECTED: CC frame (API mode)")
                
                # Look for potential "virtual CMD/DATA" trigger
                if len(data) >= 3 and data[0] > 0x7F:
                    print(f"  ** POSSIBLE COMMAND: Starts with 0x{data[0]:02X}")
                
                last_time = now
            
            time.sleep(0.01)
            
    except serial.SerialException as e:
        if "PermissionError" in str(e) or "Access is denied" in str(e):
            print("\n" + "="*70)
            print("PORT IN USE")
            print("="*70)
            print("\nThe port is being used by another application.")
            print("This is expected - the Laird utility has the port open.")
            print("\nAlternative approach:")
            print("1. Check Laird utility documentation for command format")
            print("2. Use Wireshark with USBPcap to capture USB traffic")
            print("3. Or look in reference_docs for command protocol specs")
            return False
        else:
            print(f"\nSerial error: {e}")
            return False
            
    except KeyboardInterrupt:
        print("\n\nStopped by user")
        return True

def main():
    print("\n" + "="*70)
    print("Laird Radio Command Sniffer")
    print("="*70)
    print("\nGoal: Capture the 'virtual CMD/DATA' command sequence")
    print("\nThe Laird utility claims to 'create a virtual version of the")
    print("Command/Data Line' which allows AT commands even when Pin 15 is LOW.")
    print("\nLet's see what it actually sends...")
    
    # Try to sniff COM7
    result = sniff_port("COM7")
    
    if not result:
        print("\n" + "="*70)
        print("ALTERNATIVE: Check Documentation")
        print("="*70)
        print("\nSince we can't sniff the port while Laird utility uses it,")
        print("let's check if there's protocol documentation in reference_docs")
        print("\nLook for:")
        print("  - Binary command format")
        print("  - Configuration command protocol")
        print("  - Special mode entry sequences")
        print("  - EEPROM read/write command format")

if __name__ == "__main__":
    main()
