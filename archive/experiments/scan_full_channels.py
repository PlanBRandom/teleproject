"""
Comprehensive channel data packet reader for OI-7032
Reads all available data per channel: value, status, alarms, radio address, etc.
"""
from dataclasses import dataclass
from typing import Optional
from pipeline.modbus_client import ModbusClient, ModbusConfig, ConnectionType
from pipeline.registers import (
    GAS_TYPES, SENSOR_TYPES, MODE_CODES, FAULT_CODES,
    get_gas_name, get_sensor_name, get_mode_name, get_fault_name, get_units_for_gas
)

@dataclass
class ChannelDataPacket:
    """Complete data packet for a single channel"""
    channel_num: int
    radio_address: int
    reading_value: float
    reading_status: str
    fault_code: int
    fault_description: str
    is_wired: Optional[bool] = None  # True=4-20mA wired, False=radio, None=N/A
    
    # Additional fields
    mode: Optional[int] = None
    mode_description: Optional[str] = None
    sensor_type: Optional[int] = None
    sensor_type_name: Optional[str] = None
    gas_type: Optional[int] = None
    gas_type_name: Optional[str] = None
    battery_voltage: Optional[float] = None
    relay1_setpoint: Optional[float] = None
    units: Optional[str] = None
    
    def __str__(self):
        status_icon = "✓" if self.fault_code == 0 else "⚠"
        fault_icon = "  " if self.fault_code == 0 else "🔴"
        conn_type = "Wired" if self.is_wired else "Radio" if self.is_wired is False else "N/A"
        battery_str = f"{self.battery_voltage:.1f}V" if self.battery_voltage else "N/A"
        setpoint_str = f"{self.relay1_setpoint:.1f}" if self.relay1_setpoint else "N/A"
        gas_name = self.gas_type_name or "N/A"
        
        return (f"{status_icon} {fault_icon} Ch{self.channel_num:2d} | "
                f"{conn_type:6s} | {gas_name:8s} | {self.mode_description:12s} | "
                f"Value:{self.reading_value:8.2f} {self.units or 'PPM':6s} | Bat:{battery_str:6s} | "
                f"Setpt:{setpoint_str:6s} | Fault:{self.fault_code} - {self.fault_description}")

FAULT_CODES = FAULT_CODES
MODE_CODES = MODE_CODES

def read_channel_packet(client: ModbusClient, channel_num: int) -> ChannelDataPacket:
    """Read complete data packet for a channel"""
    
    # Calculate register addresses
    radio_addr_reg = channel_num  # 0x01-0x20 (1-32)
    reading_reg = 0x21 + (channel_num - 1) * 2  # 0x21-0x5F (33-95) Float32 readings
    mode_reg = 0x61 + (channel_num - 1)  # 0x61-0x80 (97-128) Mode enumeration
    battery_reg = 0x81 + (channel_num - 1) * 2  # 0x81-0xBF (129-191) Float32 battery voltage
    sensor_type_reg = 0xE1 + (channel_num - 1)  # 0xE1-0x100 (225-256) Sensor type
    gas_type_reg = 0x101 + (channel_num - 1)  # 0x101-0x120 (257-288) Gas type
    fault_reg = 0x121 + (channel_num - 1)  # 0x121-0x140 (289-320) Fault status
    relay1_setpoint_reg = 0x1A1 + (channel_num - 1) * 2  # 0x1A1-0x1DF (417-479) Float32 setpoint
    
    try:
        # Read radio address
        radio_addr = client.read_holding_registers(radio_addr_reg, 1)[0]
        
        # Read sensor value (float32)
        reading_value = client.read_float32(reading_reg)
        
        # Read mode
        mode_code = client.read_holding_registers(mode_reg, 1)[0]
        mode_desc = MODE_CODES.get(mode_code, f"Unknown mode {mode_code}")
        
        # Read battery voltage
        try:
            battery_voltage = client.read_float32(battery_reg)
        except:
            battery_voltage = None
        
        # Read sensor type
        try:
            sensor_type = client.read_holding_registers(sensor_type_reg, 1)[0]
            sensor_type_name = get_sensor_name(sensor_type)
        except:
            sensor_type = None
            sensor_type_name = None
        
        # Read gas type
        try:
            gas_type = client.read_holding_registers(gas_type_reg, 1)[0]
            gas_type_name = get_gas_name(gas_type)
            # Determine appropriate units based on gas type
            units = get_units_for_gas(gas_type)
        except:
            gas_type = None
            gas_type_name = None
            units = "PPM"
        
        # Read relay 1 setpoint
        try:
            relay1_setpoint = client.read_float32(relay1_setpoint_reg)
        except:
            relay1_setpoint = None
        
        # Check if channel 29-32 is wired or radio (0x1A5-0x1A8 / 421-424)
        is_wired = None
        if 29 <= channel_num <= 32:
            wired_reg = 0x1A5 + (channel_num - 29)  # 0x1A5=Ch29, 0x1A6=Ch30, 0x1A7=Ch31, 0x1A8=Ch32
            try:
                wired_mode = client.read_holding_registers(wired_reg, 1)[0]
                is_wired = (wired_mode == 0)  # 0=wired, 1=radio
            except:
                is_wired = None
        
        # Read fault status
        try:
            fault_code = client.read_holding_registers(fault_reg, 1)[0]
            
            # For wired channels, check if reading is 2.5 (fault indicator)
            if is_wired and abs(reading_value - 2.5) < 0.01:
                fault_desc = FAULT_CODES.get(fault_code, f"Unknown fault {fault_code}") + " (4-20mA = 2.5)"
            else:
                fault_desc = FAULT_CODES.get(fault_code, f"Unknown fault code {fault_code}")
        except:
            fault_code = 0
            fault_desc = "Unable to read fault status"
        
        return ChannelDataPacket(
            channel_num=channel_num,
            radio_address=radio_addr,
            reading_value=reading_value,
            reading_status="OK",
            fault_code=fault_code,
            fault_description=fault_desc,
            is_wired=is_wired,
            mode=mode_code,
            mode_description=mode_desc,
            sensor_type=sensor_type,
            sensor_type_name=sensor_type_name,
            gas_type=gas_type,
            gas_type_name=gas_type_name,
            battery_voltage=battery_voltage,
            relay1_setpoint=relay1_setpoint,
            units=units
        )
        
    except Exception as e:
        return ChannelDataPacket(
            channel_num=channel_num,
            radio_address=0,
            reading_value=0.0,
            reading_status=f"ERROR: {e}",
            fault_code=99,
            fault_description=str(e)
        )

def scan_all_channels(client: ModbusClient, channels_to_scan=range(1, 33)):
    """Scan all channels and return list of data packets"""
    packets = []
    for ch in channels_to_scan:
        packet = read_channel_packet(client, ch)
        packets.append(packet)
    
    return packets

def display_packets(packets):
    """Display channel packets in organized format"""
    print("\n" + "=" * 150)
    print("OI-7032 COMPLETE CHANNEL DATA PACKETS")
    print("=" * 150)
    print(f"{'Status':<3} {'Fault':<3} {'Ch':<4} | {'Type':<6} | {'Gas':<8} | {'Mode':<12} | {'Reading Value':<20} | {'Battery':<8} | {'Setpoint':<8} | {'Fault Status'}")
    print("-" * 150)
    
    active_channels = [p for p in packets if p.radio_address > 0 or p.reading_value != 0.0]
    
    for packet in active_channels:
        print(packet)
    
    print("-" * 150)
    print(f"Active Channels: {len(active_channels)} / {len(packets)}")
    
    # Show connection type summary
    wired = [p for p in active_channels if p.is_wired is True]
    radio = [p for p in active_channels if p.is_wired is False]
    if wired or radio:
        print(f"\nConnection Types: {len(radio)} Radio, {len(wired)} Wired (4-20mA)")
    
    # Show fault summary
    faulted = [p for p in active_channels if p.fault_code != 0]
    if faulted:
        print(f"\n⚠ FAULTS DETECTED: {len(faulted)} channel(s)")
        for p in faulted:
            conn = "Wired" if p.is_wired else "Radio" if p.is_wired is False else "Unknown"
            print(f"  Ch {p.channel_num} ({conn}): {p.fault_description}")
    else:
        print(f"\n✓ All active channels operating normally")
    
    print("=" * 150)

def main():
    """Main scan and display"""
    config = ModbusConfig(
        connection_type=ConnectionType.RTU,
        port='COM10',
        slave_id=1
    )
    
    print("Connecting to OI-7032 on COM10...")
    client = ModbusClient(config)
    print("✓ Connected\n")
    
    # Scan all 32 channels
    print("Reading complete data packets for all 32 channels...")
    packets = scan_all_channels(client)
    
    # Display results
    display_packets(packets)
    
    # Export to JSON for easy integration
    import json
    export_data = [
        {
            "channel": p.channel_num,
            "radio_address": p.radio_address,
            "value": p.reading_value,
            "status": p.reading_status,
            "fault_code": p.fault_code,
            "fault_description": p.fault_description,
            "connection_type": "wired" if p.is_wired else "radio" if p.is_wired is False else None,
            "mode": p.mode,
            "mode_description": p.mode_description,
            "gas_type": p.gas_type,
            "gas_type_name": p.gas_type_name,
            "sensor_type": p.sensor_type,
            "sensor_type_name": p.sensor_type_name,
            "battery_voltage": p.battery_voltage,
            "relay1_setpoint": p.relay1_setpoint,
            "units": p.units or "PPM"
        }
        for p in packets if p.radio_address > 0 or p.reading_value != 0.0
    ]
    
    with open('channel_data_export.json', 'w') as f:
        json.dump(export_data, f, indent=2)
    
    print(f"\n✓ Exported to channel_data_export.json\n")
    
    client.close()

if __name__ == "__main__":
    main()
