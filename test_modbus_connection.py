#!/usr/bin/env python3
"""
Quick Modbus Connection Test
Tests connection to OI-7530/7032 monitors and reads a few registers
"""
import sys
from pymodbus.client import ModbusSerialClient as ModbusClient

def test_modbus_connection():
    """Test Modbus RTU connection"""
    
    print("=" * 80)
    print("MODBUS CONNECTION TEST")
    print("=" * 80)
    print()
    
    # Configuration from config.yaml
    PORT = "COM10"
    BAUDRATE = 19200
    SLAVE_ID = 1
    TIMEOUT = 3
    
    print(f"Configuration:")
    print(f"  Port:     {PORT}")
    print(f"  Baudrate: {BAUDRATE}")
    print(f"  Slave ID: {SLAVE_ID}")
    print(f"  Timeout:  {TIMEOUT}s")
    print()
    
    # Create client
    print("Connecting to Modbus device...")
    try:
        client = ModbusClient(
            port=PORT,
            baudrate=BAUDRATE,
            bytesize=8,
            parity='N',
            stopbits=1,
            timeout=TIMEOUT
        )
        
        if not client.connect():
            print("❌ ERROR: Failed to open serial port")
            print(f"   Check if {PORT} is available and not in use")
            return False
        
        print(f"✓ Serial port {PORT} opened successfully")
        print()
        
        # Test reads
        print("Testing register reads...")
        print("-" * 80)
        
        test_registers = [
            (40001, "Device ID / Model Number"),
            (40002, "Firmware Version"),
            (40003, "Hardware Version"),
            (40101, "Channel 1 Gas Reading"),
            (40201, "Alarm Status Register"),
        ]
        
        success_count = 0
        
        for reg_addr, description in test_registers:
            # Modbus addressing: subtract 40001 for holding registers
            addr = reg_addr - 40001
            
            try:
                result = client.read_holding_registers(addr, count=1, device_id=SLAVE_ID)
                
                if hasattr(result, 'isError') and result.isError():
                    print(f"❌ Register {reg_addr} ({description})")
                    print(f"   Error: {result}")
                elif hasattr(result, 'registers'):
                    value = result.registers[0]
                    print(f"✓ Register {reg_addr} ({description})")
                    print(f"   Value: {value} (0x{value:04X})")
                    success_count += 1
                else:
                    print(f"❌ Register {reg_addr} ({description})")
                    print(f"   Unexpected response: {result}")
                    
            except Exception as e:
                print(f"❌ Register {reg_addr} ({description})")
                print(f"   Error: {e}")
            
            print()
        
        client.close()
        
        print("-" * 80)
        print()
        print("TEST RESULTS:")
        print(f"  Successful reads: {success_count}/{len(test_registers)}")
        print()
        
        if success_count == 0:
            print("❌ CONNECTION TEST FAILED")
            print()
            print("Possible issues:")
            print("  1. Wrong slave ID (current: {})".format(SLAVE_ID))
            print("  2. Device not powered on")
            print("  3. Wrong serial port (current: {})".format(PORT))
            print("  4. Incorrect baud rate (current: {})".format(BAUDRATE))
            print("  5. Bad RS485 wiring or converter")
            print()
            return False
        elif success_count < len(test_registers):
            print("⚠ PARTIAL SUCCESS")
            print("  Some registers could be read, but not all")
            print("  Connection is working but device may have issues")
            print()
            return True
        else:
            print("✓ CONNECTION TEST PASSED")
            print("  All test registers read successfully!")
            print()
            return True
            
    except Exception as e:
        print(f"❌ CRITICAL ERROR: {e}")
        print()
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_modbus_connection()
    sys.exit(0 if success else 1)
