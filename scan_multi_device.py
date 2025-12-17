"""
Multi-device scanner for OI-7032, OI-7530, and OI-7010
Compares readings across all three monitors for the same wireless sensors
"""
from dataclasses import dataclass
from typing import Optional, Dict, List
from pipeline.modbus_client import ModbusClient, ModbusConfig, ConnectionType

@dataclass
class DeviceReading:
    """Reading from a single device"""
    device_name: str
    slave_id: int
    channel_num: int
    radio_address: int
    reading_value: float
    fault_code: int
    battery_voltage: Optional[float]
    is_wired: Optional[bool]

DEVICES = [
    {"name": "OI-7010", "slave_id": 1, "description": "Monitor on slave address 1"},
    {"name": "OI-7530", "slave_id": 2, "description": "Monitor on slave address 2"},
    {"name": "OI-7032", "slave_id": 3, "description": "Primary monitor with wired Ch32"}
]

FAULT_CODES = {
    0: "None",
    1: "Sensor Timeout",
    2: "Sensor reading below null",
    3: "Replace sensor element",
    4: "ADC not responding",
    5: "Null Failed",
    6: "Cal Failed",
    7: "Future Error",
    8: "Two Sensors Same Address",
    9: "Sensor Radio Timeout",
    10: "No sensor connected (Wired)",
    11: "Rapid temperature change",
    12: "Sensor Element Restarting",
    13: "Unspecified Error",
    14: "No Primary Monitor at Sensor Head"
}

def read_channel_from_device(client: ModbusClient, device_name: str, slave_id: int, channel_num: int) -> DeviceReading:
    """Read a single channel from a specific device"""
    
    # Calculate register addresses
    radio_addr_reg = channel_num
    reading_reg = 0x21 + (channel_num - 1) * 2
    fault_reg = 0x121 + (channel_num - 1)
    battery_reg = 0x81 + (channel_num - 1) * 2
    
    # Check if wired (only relevant for channels 29-32 on OI-7032)
    is_wired = None
    if device_name == "OI-7032" and 29 <= channel_num <= 32:
        wired_reg = 0x1A5 + (channel_num - 29)
        try:
            wired_mode = client.read_holding_registers(wired_reg, 1, device_id=slave_id)[0]
            is_wired = (wired_mode == 0)
        except:
            is_wired = None
    
    try:
        radio_addr = client.read_holding_registers(radio_addr_reg, 1, device_id=slave_id)[0]
        reading_value = client.read_float32(reading_reg, device_id=slave_id)
        
        try:
            fault_code = client.read_holding_registers(fault_reg, 1, device_id=slave_id)[0]
        except:
            fault_code = 0
        
        try:
            battery_voltage = client.read_float32(battery_reg, device_id=slave_id)
        except:
            battery_voltage = None
        
        return DeviceReading(
            device_name=device_name,
            slave_id=slave_id,
            channel_num=channel_num,
            radio_address=radio_addr,
            reading_value=reading_value,
            fault_code=fault_code,
            battery_voltage=battery_voltage,
            is_wired=is_wired
        )
    except Exception as e:
        return DeviceReading(
            device_name=device_name,
            slave_id=slave_id,
            channel_num=channel_num,
            radio_address=0,
            reading_value=0.0,
            fault_code=99,
            battery_voltage=None,
            is_wired=is_wired
        )

def scan_all_devices(client: ModbusClient, channels=range(1, 33)) -> Dict[int, List[DeviceReading]]:
    """Scan all channels across all devices"""
    results = {ch: [] for ch in channels}
    
    for device in DEVICES:
        print(f"  Scanning {device['name']} (slave {device['slave_id']})...")
        for ch in channels:
            reading = read_channel_from_device(client, device['name'], device['slave_id'], ch)
            results[ch].append(reading)
    
    return results

def display_comparison(results: Dict[int, List[DeviceReading]]):
    """Display comparison of readings across all devices"""
    print("\n" + "=" * 150)
    print("MULTI-DEVICE COMPARISON: OI-7010 vs OI-7530 vs OI-7032")
    print("=" * 150)
    print(f"{'Ch':<4} | {'Radio':<6} | {'OI-7010 (Slave 1)':<30} | {'OI-7530 (Slave 2)':<30} | {'OI-7032 (Slave 3)':<30} | {'Status'}")
    print("-" * 150)
    
    # Only show channels with activity on at least one device
    active_channels = []
    for ch, readings in sorted(results.items()):
        if any(r.radio_address > 0 or r.reading_value != 0.0 for r in readings):
            active_channels.append(ch)
    
    for ch in active_channels:
        readings = results[ch]
        
        # Get radio address from first non-zero reading
        radio_addr = next((r.radio_address for r in readings if r.radio_address > 0), 0)
        
        # Format readings for each device
        oi7010 = readings[0]  # slave 1
        oi7530 = readings[1]  # slave 2
        oi7032 = readings[2]  # slave 3
        
        def format_reading(r: DeviceReading) -> str:
            fault_icon = "⚠" if r.fault_code != 0 else " "
            wired_icon = "[W]" if r.is_wired else "   "
            return f"{fault_icon}{wired_icon} {r.reading_value:7.2f} (F:{r.fault_code})"
        
        r1 = format_reading(oi7010)
        r2 = format_reading(oi7530)
        r3 = format_reading(oi7032)
        
        # Check if readings match (within tolerance)
        tolerance = 0.5
        wireless_readings = []
        if not oi7032.is_wired:
            wireless_readings.append(oi7032.reading_value)
        wireless_readings.append(oi7010.reading_value)
        wireless_readings.append(oi7530.reading_value)
        
        # Calculate variance
        if len(wireless_readings) > 1 and any(v != 0 for v in wireless_readings):
            max_val = max(wireless_readings)
            min_val = min(wireless_readings)
            diff = max_val - min_val
            if diff > tolerance:
                status = f"⚠ MISMATCH ({diff:.2f} diff)"
            else:
                status = "✓ Match"
        else:
            status = ""
        
        # Special note for Ch32 (wired on 7032)
        if ch == 32 and oi7032.is_wired:
            status += " (Ch32 wired on 7032 only)"
        
        print(f"{ch:2d}   | {radio_addr:3d}    | {r1:<30} | {r2:<30} | {r3:<30} | {status}")
    
    print("-" * 150)
    print(f"Active Channels: {len(active_channels)}")
    print("=" * 150)
    
    # Summary of faults
    print("\nFAULT SUMMARY:")
    for device in DEVICES:
        device_readings = [results[ch][DEVICES.index(device)] for ch in active_channels]
        faults = [r for r in device_readings if r.fault_code != 0]
        if faults:
            print(f"\n{device['name']} (Slave {device['slave_id']}):")
            for r in faults:
                fault_desc = FAULT_CODES.get(r.fault_code, f"Unknown {r.fault_code}")
                print(f"  Ch{r.channel_num:2d}: {fault_desc}")
        else:
            print(f"\n{device['name']} (Slave {device['slave_id']}): ✓ No faults")

def main():
    """Main comparison scan"""
    config = ModbusConfig(
        connection_type=ConnectionType.RTU,
        port='COM10',
        slave_id=1  # Will be overridden per device
    )
    
    print("Connecting to OI monitors on COM10...")
    client = ModbusClient(config)
    print("✓ Connected\n")
    
    print("Scanning all devices across 32 channels...")
    results = scan_all_devices(client)
    
    # Display comparison
    display_comparison(results)
    
    # Export to JSON
    import json
    export_data = []
    for ch, readings in sorted(results.items()):
        if any(r.radio_address > 0 or r.reading_value != 0.0 for r in readings):
            channel_data = {
                "channel": ch,
                "radio_address": readings[0].radio_address,
                "devices": {
                    "OI-7010": {
                        "value": readings[0].reading_value,
                        "fault": readings[0].fault_code,
                        "battery": readings[0].battery_voltage
                    },
                    "OI-7530": {
                        "value": readings[1].reading_value,
                        "fault": readings[1].fault_code,
                        "battery": readings[1].battery_voltage
                    },
                    "OI-7032": {
                        "value": readings[2].reading_value,
                        "fault": readings[2].fault_code,
                        "battery": readings[2].battery_voltage,
                        "is_wired": readings[2].is_wired
                    }
                }
            }
            export_data.append(channel_data)
    
    with open('multi_device_comparison.json', 'w') as f:
        json.dump(export_data, f, indent=2)
    
    print(f"\n✓ Exported to multi_device_comparison.json\n")
    
    client.close()

if __name__ == "__main__":
    main()
