#!/usr/bin/env python3
"""
Radio Debug Tool - Shows raw bytes coming from COM port
"""

import serial
import sys
import time

def main():
    port = sys.argv[1] if len(sys.argv) > 1 else "COM7"
    baudrate = 9600
    
    print(f"Opening {port} at {baudrate} baud...")
    print("Showing raw hex bytes. Press Ctrl+C to stop\n")
    
    try:
        ser = serial.Serial(port, baudrate, timeout=0.1)
        byte_count = 0
        line_buffer = []
        
        while True:
            if ser.in_waiting:
                data = ser.read(ser.in_waiting)
                
                for byte in data:
                    line_buffer.append(f'{byte:02X}')
                    byte_count += 1
                    
                    # Print 24 bytes per line
                    if len(line_buffer) >= 24:
                        print(f"[{byte_count-23:04d}] " + ' '.join(line_buffer))
                        line_buffer = []
            
            time.sleep(0.01)
            
    except KeyboardInterrupt:
        print("\n\nStopped")
        if line_buffer:
            print(f"[{byte_count-len(line_buffer)+1:04d}] " + ' '.join(line_buffer))
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if 'ser' in locals():
            ser.close()

if __name__ == "__main__":
    main()
