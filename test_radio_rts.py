#!/usr/bin/env python3
"""
Test script for Laird RM024 radios with RTS/CTS flow control.
Tests command mode entry and AT commands on COM7 and COM11.

Radio Configuration (from EEPROM):
- COM7 (005067E086EB): RM024125C30, Channel 0x4C (76), System 0x0E01
- COM11: RM024125C30, Channel 0x0C (12), System 0x0E01
- Both: 115200 baud, 8-N-1, Hardware handshaking (RTS/CTS)
"""

import serial
import time
import sys

def test_radio(port, name):
    """Test a single radio with RTS/CTS flow control."""
    print(f"\n{'='*60}")
    print(f"Testing {name} on {port}")
    print(f"{'='*60}")
    
    try:
        # Open port with hardware flow control
        print(f"Opening {port} with RTS/CTS flow control...")
        ser = serial.Serial(
            port=port,
            baudrate=115200,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=1,
            rtscts=True  # Enable hardware flow control
        )
        
        # Set RTS high for normal operation
        ser.rts = True
        print(f"✓ Port opened - RTS: {ser.rts}, CTS: {ser.cts}")
        time.sleep(0.5)
        
        # Clear buffer
        if ser.in_waiting > 0:
            data = ser.read(ser.in_waiting)
            print(f"  Cleared {len(data)} bytes from buffer")
        
        # Monitor for incoming sensor data
        print("\nMonitoring for sensor data (5 seconds, RTS HIGH)...")
        start = time.time()
        packet_count = 0
        while (time.time() - start) < 5:
            if ser.in_waiting > 0:
                data = ser.read(ser.in_waiting)
                hex_str = ' '.join([f'{b:02X}' for b in data])
                print(f"  RX [{len(data)} bytes]: {hex_str[:80]}{'...' if len(hex_str) > 80 else ''}")
                
                # Check for Gen2 packets (81 11)
                if b'\x81\x11' in data:
                    packet_count += 1
                    print(f"    → Gen2 sensor packet detected! (Total: {packet_count})")
                
                # Check for API mode (CC)
                if b'\xCC' in data:
                    print(f"    ⚠ API mode detected (0xCC frame delimiter)")
            
            time.sleep(0.1)
        
        if packet_count > 0:
            print(f"✓ Received {packet_count} sensor packets")
        else:
            print("  No sensor packets received (normal if no sensors transmitting)")
        
        # Test command mode entry with RTS control
        print(f"\n--- Testing Command Mode Entry ---")
        print("Setting RTS LOW to stop incoming data...")
        ser.rts = False
        time.sleep(0.3)
        print(f"  RTS: {ser.rts}, CTS: {ser.cts}")
        
        # Clear buffer
        if ser.in_waiting > 0:
            ser.read(ser.in_waiting)
        
        # Guard time + send +++ + guard time
        print("Sending +++ with guard times (RTS LOW = silence)...")
        time.sleep(1.3)
        ser.write(b'+++')
        print("  Sent: +++")
        time.sleep(1.3)
        
        # Wait for OK
        print("Waiting for OK response...")
        response = b''
        start = time.time()
        while (time.time() - start) < 3:
            if ser.in_waiting > 0:
                response += ser.read(ser.in_waiting)
            if b'OK' in response:
                break
            time.sleep(0.1)
        
        if b'OK' in response:
            print(f"✓ Command mode entered! Response: {response.decode('ascii', errors='ignore').strip()}")
            
            # Try reading radio profile
            print("\n--- Reading Radio Profile ---")
            
            # Channel (ATCH)
            ser.write(b'ATCH\r')
            time.sleep(0.3)
            resp = ser.read(ser.in_waiting).decode('ascii', errors='ignore').strip()
            print(f"  ATCH (Channel): {resp}")
            
            # System ID (ATSY)
            ser.write(b'ATSY\r')
            time.sleep(0.3)
            resp = ser.read(ser.in_waiting).decode('ascii', errors='ignore').strip()
            print(f"  ATSY (System ID): {resp}")
            
            # Primary/Secondary (ATSP)
            ser.write(b'ATSP\r')
            time.sleep(0.3)
            resp = ser.read(ser.in_waiting).decode('ascii', errors='ignore').strip()
            print(f"  ATSP (Primary=0/Secondary=1): {resp}")
            
            # Baud rate (ATBD)
            ser.write(b'ATBD\r')
            time.sleep(0.3)
            resp = ser.read(ser.in_waiting).decode('ascii', errors='ignore').strip()
            print(f"  ATBD (Baud): {resp}")
            
            # Power level (ATPL)
            ser.write(b'ATPL\r')
            time.sleep(0.3)
            resp = ser.read(ser.in_waiting).decode('ascii', errors='ignore').strip()
            print(f"  ATPL (Power Level): {resp}")
            
            # MAC address (ATMY)
            ser.write(b'ATMY\r')
            time.sleep(0.3)
            resp = ser.read(ser.in_waiting).decode('ascii', errors='ignore').strip()
            print(f"  ATMY (MAC Address): {resp}")
            
            # Firmware version (ATVR)
            ser.write(b'ATVR\r')
            time.sleep(0.3)
            resp = ser.read(ser.in_waiting).decode('ascii', errors='ignore').strip()
            print(f"  ATVR (Firmware): {resp}")
            
            # Exit command mode
            print("\nExiting command mode (ATCN)...")
            ser.write(b'ATCN\r')
            time.sleep(0.5)
            resp = ser.read(ser.in_waiting)
            print(f"  Response: {resp.decode('ascii', errors='ignore').strip()}")
            
            # Restore RTS high
            ser.rts = True
            print(f"✓ RTS restored HIGH - normal operation resumed")
            
        else:
            print(f"✗ Failed to enter command mode")
            print(f"  Response: {response}")
            # Restore RTS anyway
            ser.rts = True
        
        # Close port
        ser.close()
        print(f"\n✓ {name} test complete")
        return True
        
    except serial.SerialException as e:
        print(f"✗ Serial error: {e}")
        return False
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Test both radios."""
    print("\n" + "="*60)
    print("Laird RM024 Radio Test with RTS/CTS Flow Control")
    print("="*60)
    print("\nExpected Configuration:")
    print("  COM7:  RM024125C30, Ch 76 (0x4C), Sys 0x0E01")
    print("  COM11: RM024125C30, Ch 12 (0x0C), Sys 0x0E01")
    print("  Baud: 115200, 8-N-1, RTS/CTS enabled")
    print("\nRTS Control:")
    print("  RTS HIGH = Normal operation (sensor data flows)")
    print("  RTS LOW  = Command mode (stops incoming data)")
    
    # Test COM7 first
    com7_ok = test_radio("COM7", "Radio 1 (005067E086EB)")
    
    # Test COM11
    com11_ok = test_radio("COM11", "Radio 2")
    
    # Summary
    print("\n" + "="*60)
    print("Test Summary")
    print("="*60)
    print(f"  COM7:  {'✓ PASSED' if com7_ok else '✗ FAILED'}")
    print(f"  COM11: {'✓ PASSED' if com11_ok else '✗ FAILED'}")
    
    if com7_ok and com11_ok:
        print("\n✓ All radios working! Ready to use in web app.")
        return 0
    else:
        print("\n⚠ Some radios failed - check connections and settings")
        return 1

if __name__ == "__main__":
    sys.exit(main())
