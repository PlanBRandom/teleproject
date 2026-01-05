#!/usr/bin/env python3
"""
Test direct AT commands - try sending commands without +++ entry.
Some Laird radios accept commands in transparent mode during data gaps.
"""

import serial
import time

def test_direct_commands(port, name):
    """Try sending AT commands directly without +++ sequence."""
    print(f"\n{'='*60}")
    print(f"Testing {name} on {port} - Direct AT Commands")
    print(f"{'='*60}")
    
    try:
        ser = serial.Serial(
            port=port,
            baudrate=115200,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=1,
            rtscts=True
        )
        ser.rts = True
        print(f"✓ Port opened")
        time.sleep(0.5)
        
        # Clear buffer
        if ser.in_waiting > 0:
            data = ser.read(ser.in_waiting)
            print(f"  Cleared {len(data)} bytes")
        
        # Wait for a gap in sensor traffic (sensors transmit every minute)
        print("\nWaiting for traffic gap (10 seconds)...")
        last_rx = time.time()
        start = time.time()
        gap_found = False
        
        while (time.time() - start) < 10:
            if ser.in_waiting > 0:
                data = ser.read(ser.in_waiting)
                last_rx = time.time()
            else:
                # Check if we've had 2 seconds of silence
                if (time.time() - last_rx) > 2.0:
                    gap_found = True
                    print(f"✓ Found {time.time() - last_rx:.1f}s gap in traffic!")
                    break
            time.sleep(0.1)
        
        if gap_found:
            # Try +++ during the gap with proper timing
            print("\nTrying +++ with 1.3s guard times...")
            time.sleep(1.3)  # Guard time before
            ser.write(b'+++')
            print("  Sent +++")
            time.sleep(1.3)  # Guard time after
            
            response = b''
            start_wait = time.time()
            while (time.time() - start_wait) < 3:
                if ser.in_waiting > 0:
                    response += ser.read(ser.in_waiting)
                if b'OK' in response:
                    break
                time.sleep(0.1)
            
            print(f"Response: {response}")
            
            if b'OK' in response:
                print("✓✓✓ COMMAND MODE ENTERED! ✓✓✓")
                
                # Try reading full profile
                print("\nReading radio profile...")
                
                # Channel
                ser.write(b'ATCH\r')
                time.sleep(0.3)
                resp = ser.read(ser.in_waiting).decode('ascii', errors='ignore').strip()
                print(f"  ATCH (Channel): {resp}")
                
                # System ID  
                ser.write(b'ATSY\r')
                time.sleep(0.3)
                resp = ser.read(ser.in_waiting).decode('ascii', errors='ignore').strip()
                print(f"  ATSY (System ID): {resp}")
                
                # Primary/Secondary
                ser.write(b'ATSP\r')
                time.sleep(0.3)
                resp = ser.read(ser.in_waiting).decode('ascii', errors='ignore').strip()
                mode = "Secondary (RX only)" if resp == "00" else "Primary (TX/RX)"
                print(f"  ATSP (Mode): {resp} = {mode}")
                
                # Baud
                ser.write(b'ATBD\r')
                time.sleep(0.3)
                resp = ser.read(ser.in_waiting).decode('ascii', errors='ignore').strip()
                print(f"  ATBD (Baud): {resp}")
                
                # MAC
                ser.write(b'ATMY\r')
                time.sleep(0.3)
                resp = ser.read(ser.in_waiting).decode('ascii', errors='ignore').strip()
                print(f"  ATMY (MAC): {resp}")
                
                # Firmware
                ser.write(b'ATVR\r')
                time.sleep(0.3)
                resp = ser.read(ser.in_waiting).decode('ascii', errors='ignore').strip()
                print(f"  ATVR (Firmware): {resp}")
                
                # Exit
                print("\nExiting command mode...")
                ser.write(b'ATCN\r')
                time.sleep(0.3)
                resp = ser.read(ser.in_waiting)
                print(f"  ATCN response: {resp.decode('ascii', errors='ignore').strip()}")
                print("✓ Exited command mode")
            else:
                print("✗ No OK response - command mode failed")
                if response:
                    hex_str = ' '.join([f'{b:02X}' for b in response])
                    print(f"  Hex: {hex_str}")
        else:
            print("✗ No traffic gap found (sensors transmitting continuously)")
        
        ser.close()
        return True
        
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

def main():
    print("\nLaird RM024 - Direct Command Mode Test")
    print("Attempting to find gaps in sensor traffic...")
    
    test_direct_commands("COM7", "Radio 1")
    test_direct_commands("COM11", "Radio 2")

if __name__ == "__main__":
    main()
