"""
6-Hour Radio Data Logger
Connects to radio and logs all incoming data with timestamps
"""

import serial
import time
from datetime import datetime
import os

# Configuration
PORT = 'COM7'  # Change to COM11 if needed
BAUDRATE = 115200
DURATION_HOURS = 6
LOG_DIR = 'radio_logs'

def main():
    # Create log directory
    os.makedirs(LOG_DIR, exist_ok=True)
    
    # Create timestamped log file
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_file = os.path.join(LOG_DIR, f'radio_log_{PORT}_{timestamp}.txt')
    hex_log_file = os.path.join(LOG_DIR, f'radio_log_{PORT}_{timestamp}_hex.txt')
    
    print(f"==================================================")
    print(f"  6-Hour Radio Data Logger")
    print(f"==================================================")
    print(f"Port: {PORT} @ {BAUDRATE} baud")
    print(f"Duration: {DURATION_HOURS} hours")
    print(f"Log file: {log_file}")
    print(f"Hex log: {hex_log_file}")
    print(f"==================================================")
    print()
    
    try:
        # Open serial port
        ser = serial.Serial(
            port=PORT,
            baudrate=BAUDRATE,
            timeout=1,
            rtscts=True  # Hardware flow control
        )
        
        print(f"✓ Connected to {PORT}")
        print(f"✓ Started logging at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"✓ Will log until {(datetime.now().timestamp() + DURATION_HOURS * 3600)}")
        print()
        
        start_time = time.time()
        end_time = start_time + (DURATION_HOURS * 3600)
        packet_count = 0
        byte_count = 0
        
        with open(log_file, 'w') as f_text, open(hex_log_file, 'w') as f_hex:
            # Write headers
            f_text.write(f"Radio Data Log - {PORT} @ {BAUDRATE} baud\n")
            f_text.write(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f_text.write(f"Duration: {DURATION_HOURS} hours\n")
            f_text.write("=" * 80 + "\n\n")
            
            f_hex.write(f"Radio Hex Data Log - {PORT} @ {BAUDRATE} baud\n")
            f_hex.write(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f_hex.write("=" * 80 + "\n\n")
            
            last_status_time = time.time()
            
            while time.time() < end_time:
                # Check if data available
                if ser.in_waiting > 0:
                    # Read available data
                    data = ser.read(ser.in_waiting)
                    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
                    
                    # Update counters
                    packet_count += 1
                    byte_count += len(data)
                    
                    # Write to text log (ASCII representation)
                    f_text.write(f"[{timestamp}] Packet #{packet_count} ({len(data)} bytes)\n")
                    f_text.write(f"Raw: {data}\n")
                    f_text.write(f"Hex: {data.hex()}\n")
                    
                    # Try to decode as ASCII (for readable parts)
                    try:
                        ascii_repr = ''.join(chr(b) if 32 <= b < 127 else f'\\x{b:02x}' for b in data)
                        f_text.write(f"ASCII: {ascii_repr}\n")
                    except:
                        pass
                    
                    f_text.write("-" * 80 + "\n\n")
                    f_text.flush()
                    
                    # Write to hex log (compact format)
                    f_hex.write(f"[{timestamp}] {data.hex()}\n")
                    f_hex.flush()
                
                # Print status update every 60 seconds
                current_time = time.time()
                if current_time - last_status_time >= 60:
                    elapsed = current_time - start_time
                    remaining = end_time - current_time
                    elapsed_hours = elapsed / 3600
                    remaining_hours = remaining / 3600
                    
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] Status: {packet_count} packets, {byte_count} bytes | "
                          f"Elapsed: {elapsed_hours:.2f}h | Remaining: {remaining_hours:.2f}h")
                    
                    last_status_time = current_time
                
                time.sleep(0.01)  # Small delay to prevent CPU spinning
            
        print()
        print("=" * 50)
        print("Logging Complete!")
        print(f"Total packets: {packet_count}")
        print(f"Total bytes: {byte_count}")
        print(f"Duration: {DURATION_HOURS} hours")
        print(f"Log saved to: {log_file}")
        print(f"Hex log saved to: {hex_log_file}")
        print("=" * 50)
        
    except serial.SerialException as e:
        print(f"✗ Serial port error: {e}")
        return 1
    except KeyboardInterrupt:
        print("\n\n✗ Logging interrupted by user")
        print(f"Partial log saved to: {log_file}")
        return 0
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        if 'ser' in locals() and ser.is_open:
            ser.close()
            print("✓ Serial port closed")

if __name__ == '__main__':
    exit(main())
