"""
Diagnostic tool for Channel 32 / Radio Channel 16 issue

Channel 32 is configured as a wired 4-20mA sensor but also receives
radio data from radio address 16 on channel 16. This script helps
diagnose and understand the configuration.
"""

import serial
from pymodbus.client import ModbusSerialClient
import struct
import time

# OI-7032 connection settings
COM_PORT = 'COM10'
BAUDRATE = 9600
SLAVE_ID = 3

def read_channel_info(client, channel):
    """Read complete information for a channel"""
    print(f"\n{'='*60}")
    print(f"Channel {channel} Diagnostic")
    print(f"{'='*60}")
    
    try:
        # Radio Address (determines what sensor this channel listens to)
        addr_reg = 0x00 + (channel - 1)
        result = client.read_holding_registers(addr_reg, 1, slave=SLAVE_ID)
        if not result.isError():
            radio_addr = result.registers[0]
            print(f"Radio Address: {radio_addr}")
            if radio_addr == 0:
                print("  → Channel is DISABLED (address 0)")
            elif radio_addr == 255:
                print("  → Channel is in SCAN MODE (catch-all)")
            else:
                print(f"  → Channel listens to radio sensor #{radio_addr}")
        
        # Reading (Float32 - 2 registers)
        reading_reg = 0x20 + (channel - 1) * 2
        result = client.read_holding_registers(reading_reg, 2, slave=SLAVE_ID)
        if not result.isError():
            raw = struct.pack('>HH', result.registers[0], result.registers[1])
            reading = struct.unpack('>f', raw)[0]
            print(f"Current Reading: {reading:.3f} PPM")
        
        # Mode (0=Disabled, 1=Enabled, etc)
        mode_reg = 0x60 + (channel - 1)
        result = client.read_holding_registers(mode_reg, 1, slave=SLAVE_ID)
        if not result.isError():
            mode = result.registers[0]
            mode_names = {0: "Disabled", 1: "Enabled", 2: "Alarm Only", 3: "4-20mA Wired"}
            print(f"Mode: {mode} ({mode_names.get(mode, 'Unknown')})")
        
        # Battery (Float32 - 2 registers)
        battery_reg = 0x80 + (channel - 1) * 2
        result = client.read_holding_registers(battery_reg, 2, slave=SLAVE_ID)
        if not result.isError():
            raw = struct.pack('>HH', result.registers[0], result.registers[1])
            battery = struct.unpack('>f', raw)[0]
            print(f"Battery: {battery:.1f} V")
            if battery > 30:
                print("  → Invalid battery reading (not a radio sensor)")
        
        # Time Since Last Message
        time_reg = 0xC0 + (channel - 1)
        result = client.read_holding_registers(time_reg, 1, slave=SLAVE_ID)
        if not result.isError():
            time_since = result.registers[0]
            if time_since == 65535:
                print(f"Time Since Last Msg: NEVER (no messages received)")
            else:
                print(f"Time Since Last Msg: {time_since} seconds ago")
                if time_since < 600:
                    print("  → Channel is ACTIVE (< 10 min)")
                else:
                    print("  → Channel is INACTIVE (> 10 min)")
        
        # Sensor Type
        sensor_reg = 0xE0 + (channel - 1)
        result = client.read_holding_registers(sensor_reg, 1, slave=SLAVE_ID)
        if not result.isError():
            sensor_type = result.registers[0]
            sensor_names = {
                0: "EC (Electrochemical)",
                1: "IR (Infrared)",
                2: "CB (Catalytic Bead)",
                3: "MOS (Metal Oxide)",
                4: "PID (Photo-Ionization)",
                5: "Tank Level",
                6: "4-20mA",
                7: "Switch",
                8: "Pressure",
                9: "Temperature"
            }
            print(f"Sensor Type: {sensor_type} ({sensor_names.get(sensor_type, 'Unknown')})")
        
        # Gas Type
        gas_reg = 0x100 + (channel - 1)
        result = client.read_holding_registers(gas_reg, 1, slave=SLAVE_ID)
        if not result.isError():
            gas_type = result.registers[0]
            gas_names = {
                0: "H2S", 1: "SO2", 2: "O2", 3: "CO", 4: "CL2",
                5: "CO2", 6: "LEL", 7: "VOC", 8: "HCl", 9: "NH3",
                10: "NO", 11: "NO2", 12: "PH3", 13: "CLO2"
            }
            print(f"Gas Type: {gas_type} ({gas_names.get(gas_type, 'Unknown')})")
        
    except Exception as e:
        print(f"Error reading channel {channel}: {e}")

def main():
    print("\n" + "="*60)
    print("OI-7032 Channel 32 / Radio 16 Diagnostic Tool")
    print("="*60)
    
    print(f"\nConnecting to OI-7032 on {COM_PORT} at {BAUDRATE} baud...")
    
    client = ModbusSerialClient(
        port=COM_PORT,
        baudrate=BAUDRATE,
        bytesize=8,
        parity='N',
        stopbits=1,
        timeout=1
    )
    
    if not client.connect():
        print("ERROR: Failed to connect to OI-7032")
        return
    
    print("Connected!\n")
    
    # Check both Channel 16 and Channel 32
    read_channel_info(client, 16)
    read_channel_info(client, 32)
    
    print("\n" + "="*60)
    print("Analysis")
    print("="*60)
    print("""
If Channel 32 shows:
  - Radio Address: 16
  - Sensor Type: 4-20mA (6)
  - Battery: Invalid/High value
  - Time Since: Active

Then Channel 32 is configured as BOTH:
  1. A wired 4-20mA sensor (sensor type 6)
  2. Listening to radio address 16

This is unusual but possible if:
  - Channel 32 is physically wired to a 4-20mA sensor
  - Radio address 16 is also transmitting
  - Both readings get mixed/displayed incorrectly

Recommendation:
  - If Channel 32 should be wired ONLY, set radio address to 0
  - If radio sensor 16 should be on Channel 16, check Channel 16's config
  - The radio sensor may be transmitting on the wrong address

To fix (if needed):
  1. Set Channel 32 radio address to 0: Write 0 to register 0x001F
  2. Set Channel 16 radio address to 16: Write 16 to register 0x000F
""")
    
    client.close()
    print("\nDisconnected.")

if __name__ == "__main__":
    main()
