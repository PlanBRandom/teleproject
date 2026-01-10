#!/usr/bin/env python3
"""
Quick serial port tester - checks if COM ports are receiving any data
"""
import serial
import sys
import time
from datetime import datetime

def test_port(port, baud=9600, duration=10):
    """Test a serial port for incoming data"""
    print(f"\n{'='*60}")
    print(f"Testing {port} @ {baud} baud")
    print(f"Duration: {duration} seconds")
    print(f"{'='*60}")
    
    try:
        ser = serial.Serial(port, baud, timeout=1)
        print(f"[OK] Port opened successfully")
        
        start_time = time.time()
        byte_count = 0
        packet_count = 0
        last_activity = start_time
        
        print(f"\nListening for data... (Ctrl+C to stop early)\n")
        
        while time.time() - start_time < duration:
            if ser.in_waiting > 0:
                data = ser.read(ser.in_waiting)
                byte_count += len(data)
                packet_count += 1
                last_activity = time.time()
                
                # Show first 32 bytes as hex
                hex_str = ' '.join(f'{b:02x}' for b in data[:32])
                if len(data) > 32:
                    hex_str += f"... ({len(data)} bytes total)"
                
                timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                print(f"[{timestamp}] Packet #{packet_count}: {hex_str}")
            
            time.sleep(0.1)
        
        elapsed = time.time() - start_time
        inactive_time = time.time() - last_activity
        
        ser.close()
        
        print(f"\n{'='*60}")
        print(f"TEST RESULTS for {port}")
        print(f"{'='*60}")
        print(f"Duration: {elapsed:.1f} seconds")
        print(f"Total packets: {packet_count}")
        print(f"Total bytes: {byte_count}")
        
        if packet_count > 0:
            print(f"Data rate: {byte_count/elapsed:.1f} bytes/sec")
            print(f"Last activity: {inactive_time:.1f} seconds ago")
            print(f"\n[OK] Port is ACTIVE - receiving data!")
        else:
            print(f"\n[WARN] Port is SILENT - no data received")
            print(f"       Check if radio is powered on")
            print(f"       Check if sensors are transmitting")
        
        return packet_count > 0
        
    except serial.SerialException as e:
        print(f"[ERROR] Could not open {port}: {e}")
        return False
    except KeyboardInterrupt:
        print(f"\n\nTest stopped by user")
        ser.close()
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_serial_ports.py COM7 [COM11 COM12 ...]")
        print("       python test_serial_ports.py COM7 --duration 30")
        print("\nExample: python test_serial_ports.py COM7 COM11 COM12")
        sys.exit(1)
    
    ports = []
    duration = 10
    
    for arg in sys.argv[1:]:
        if arg == "--duration":
            continue
        if arg.isdigit():
            duration = int(arg)
            continue
        if arg.startswith("COM") or arg.startswith("/dev/"):
            ports.append(arg)
    
    if not ports:
        print("Error: No COM ports specified")
        sys.exit(1)
    
    print("\n" + "="*60)
    print("Serial Port Activity Tester")
    print("="*60)
    print(f"Testing {len(ports)} port(s): {', '.join(ports)}")
    print(f"Duration per port: {duration} seconds")
    
    results = {}
    
    for port in ports:
        results[port] = test_port(port, duration=duration)
    
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    
    for port, active in results.items():
        status = "[ACTIVE]" if active else "[SILENT]"
        print(f"{status} {port}")
    
    active_count = sum(results.values())
    print(f"\n{active_count} of {len(ports)} ports receiving data")
    
    if active_count == 0:
        print("\n[!] No data detected on any port")
        print("    Troubleshooting:")
        print("    - Check if WireFree radios are powered on")
        print("    - Verify sensors are within range (300-500 ft)")
        print("    - Ensure sensors are configured to transmit")
        print("    - Check radio antenna connections")
