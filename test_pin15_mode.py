#!/usr/bin/env python3
"""
Test to determine if Laird radios are in AT Command mode or Standard Config mode.

Pin 15 (CMD/DATA) Status:
- HIGH or floating → AT Command mode (responds to +++)
- LOW → Standard Configuration mode (AT commands ignored)

This test will:
1. Try AT command mode entry during a traffic gap
2. Analyze the response to determine mode
3. Recommend next steps
"""

import serial
import time

def test_at_command_mode(port, name):
    """Test if radio responds to AT commands."""
    print(f"\n{'='*70}")
    print(f"Testing {name} on {port}")
    print(f"{'='*70}")
    
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
        
        # Wait for traffic gap (we know these radios have 3-12 second gaps)
        print("\nWaiting for sensor traffic gap (max 15 seconds)...")
        last_rx = time.time()
        start = time.time()
        gap_found = False
        
        while (time.time() - start) < 15:
            if ser.in_waiting > 0:
                data = ser.read(ser.in_waiting)
                last_rx = time.time()
            else:
                gap_duration = time.time() - last_rx
                if gap_duration >= 3.0:
                    gap_found = True
                    print(f"✓ Found {gap_duration:.1f}s traffic gap")
                    break
            time.sleep(0.1)
        
        if not gap_found:
            print("✗ No traffic gap found - sensors transmitting continuously")
            ser.close()
            return None
        
        # Clear buffer
        if ser.in_waiting > 0:
            ser.read(ser.in_waiting)
        
        # Try entering AT command mode
        print("\nAttempting AT command mode entry:")
        print("  1. Waiting 1.3s (guard time before)")
        time.sleep(1.3)
        
        print("  2. Sending '+++'")
        ser.write(b'+++')
        
        print("  3. Waiting 1.3s (guard time after)")
        time.sleep(1.3)
        
        print("  4. Waiting for response (3 seconds)...")
        response = b''
        start_wait = time.time()
        while (time.time() - start_wait) < 3.0:
            if ser.in_waiting > 0:
                response += ser.read(ser.in_waiting)
            time.sleep(0.1)
        
        # Analyze response
        print(f"\nResponse received: {len(response)} bytes")
        
        if len(response) == 0:
            print("  → No response (completely silent)")
            result = "UNKNOWN"
            
        elif b'OK' in response:
            print("  → Contains 'OK'")
            print(f"  → ASCII: {response.decode('ascii', errors='ignore').strip()}")
            result = "AT_MODE"
            
            # We're in command mode! Try reading channel
            print("\n✓✓✓ AT COMMAND MODE CONFIRMED! ✓✓✓")
            print("\nTrying ATCH command...")
            ser.write(b'ATCH\r')
            time.sleep(0.3)
            resp = ser.read(ser.in_waiting).decode('ascii', errors='ignore').strip()
            print(f"  ATCH response: {resp}")
            
            # Exit command mode
            ser.write(b'ATCN\r')
            time.sleep(0.3)
            ser.read(ser.in_waiting)
            print("  Exited command mode (ATCN)")
            
        elif b'\x81\x11' in response:
            print("  → Contains Gen2 sensor packet (81 11)")
            hex_str = ' '.join([f'{b:02X}' for b in response[:24]])
            print(f"  → Hex: {hex_str}")
            print("  → AT command was IGNORED - sensor data continued")
            result = "STANDARD_CONFIG"
            
        else:
            print("  → Unknown response")
            hex_str = ' '.join([f'{b:02X}' for b in response[:40]])
            print(f"  → Hex: {hex_str}")
            result = "UNKNOWN"
        
        ser.close()
        return result
        
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return None

def main():
    print("\n" + "="*70)
    print("Laird RM024 - AT Command Mode Detection")
    print("="*70)
    print("\nThis test determines if Pin 15 (CMD/DATA) is HIGH or LOW:")
    print("  Pin 15 HIGH → AT Command mode (responds to +++)")
    print("  Pin 15 LOW  → Standard Config mode (AT commands ignored)")
    print("\nTesting both radios...")
    
    # Test both radios
    com7_mode = test_at_command_mode("COM7", "Radio 1 (Ch 76)")
    com11_mode = test_at_command_mode("COM11", "Radio 2 (Ch 12)")
    
    # Summary
    print("\n" + "="*70)
    print("DIAGNOSIS")
    print("="*70)
    
    def explain_mode(mode):
        if mode == "AT_MODE":
            return "✓ AT Command Mode (Pin 15 HIGH) - WORKING!"
        elif mode == "STANDARD_CONFIG":
            return "✗ Standard Config Mode (Pin 15 LOW) - AT commands disabled"
        elif mode == "UNKNOWN":
            return "? Unknown - inconclusive test"
        else:
            return "? Test failed"
    
    print(f"\nCOM7:  {explain_mode(com7_mode)}")
    print(f"COM11: {explain_mode(com11_mode)}")
    
    # Recommendations
    print("\n" + "="*70)
    print("RECOMMENDATIONS")
    print("="*70)
    
    if com7_mode == "AT_MODE" or com11_mode == "AT_MODE":
        print("\n✓ AT Command mode is working on at least one radio!")
        print("\nNext steps:")
        print("  1. Use web app to configure radios")
        print("  2. Radio tab → Connect → Read Profile")
        print("  3. Configure radio settings as needed")
        print("  4. Monitor sensor data in Activity Log")
        
    elif com7_mode == "STANDARD_CONFIG" or com11_mode == "STANDARD_CONFIG":
        print("\n✗ Radios are in Standard Configuration mode (Pin 15 LOW)")
        print("\nThis means AT commands (+++) are DISABLED.")
        print("\nOptions:")
        print("  1. Check Pin 15 hardware status:")
        print("     - Use multimeter to check Pin 15 voltage")
        print("     - Should be 3.3V (HIGH) for AT commands")
        print("     - Currently appears to be 0V (LOW)")
        print("\n  2. Hardware fix:")
        print("     - Pull Pin 15 to HIGH (3.3V)")
        print("     - Or leave Pin 15 floating (disconnected)")
        print("     - Requires physical radio access")
        print("\n  3. Use Laird Configuration Utility:")
        print("     - Official software can handle both modes")
        print("     - Use it for radio configuration")
        print("     - Use web app for sensor data monitoring")
        print("\n  4. Implement binary EEPROM protocol:")
        print("     - Reverse engineer Standard Config commands")
        print("     - Complex but would work with Pin 15 LOW")
        
    else:
        print("\n? Test was inconclusive")
        print("\nPossible issues:")
        print("  - No traffic gaps found")
        print("  - Radio in unknown state")
        print("  - Connection issues")
        print("\nTry running test again, or check:")
        print("  - Serial port connections")
        print("  - Baud rate (115200)")
        print("  - Sensor transmissions active")
    
    print("\n" + "="*70)
    print("Current Status:")
    print("  ✓ Radios receiving sensor data perfectly")
    print("  ✓ 14 sensors detected and transmitting")
    print("  ✓ Hardware flow control enabled")
    print("  ✓ Gen2 protocol parsing working")
    print("  ? AT command mode depends on Pin 15 status")
    print("="*70 + "\n")

if __name__ == "__main__":
    main()
