"""
Live monitoring display for OI-7032 gas sensors
Shows real-time readings for configured channels
"""
import time
import sys
from datetime import datetime
from pipeline.modbus_client import ModbusClient, ModbusConfig, ConnectionType

# Channel configuration
CHANNELS = {
    5: {"name": "Channel 5", "unit": "PPM", "type": "Gas"},
    16: {"name": "O2 Sensor (Wireless Laird RM024)", "unit": "% O2", "type": "Oxygen"},
    21: {"name": "Channel 21", "unit": "PPM", "type": "Gas"},
    32: {"name": "O2 Sensor (4-20mA Wired)", "unit": "% O2", "type": "Oxygen - Alpha Sense O2-A2"},
}

def clear_screen():
    """Clear console screen"""
    print("\033[2J\033[H", end="")

def get_channel_address(channel_num):
    """Calculate modbus address for channel reading"""
    return 0x21 + (channel_num - 1) * 2

def read_all_channels(client):
    """Read all configured channels"""
    readings = {}
    for ch_num, ch_info in CHANNELS.items():
        try:
            addr = get_channel_address(ch_num)
            value = client.read_float32(addr)
            readings[ch_num] = {"value": value, "status": "OK", "info": ch_info}
        except Exception as e:
            readings[ch_num] = {"value": None, "status": f"ERROR: {e}", "info": ch_info}
    return readings

def display_readings(readings, cycle_count):
    """Display formatted readings"""
    clear_screen()
    
    print("=" * 80)
    print(f"  OI-7032 Gas Monitor - Live Telemetry Data")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Poll Cycle: {cycle_count}")
    print("=" * 80)
    print()
    
    # Group by sensor type
    o2_sensors = {}
    other_sensors = {}
    
    for ch_num, data in sorted(readings.items()):
        if "Oxygen" in data["info"]["type"] or "O2" in data["info"]["unit"]:
            o2_sensors[ch_num] = data
        else:
            other_sensors[ch_num] = data
    
    # Display O2 sensors (with comparison)
    if o2_sensors:
        print("  OXYGEN SENSORS")
        print("  " + "-" * 76)
        for ch_num, data in o2_sensors.items():
            status_icon = "✓" if data["status"] == "OK" else "✗"
            value_str = f"{data['value']:7.2f}" if data['value'] is not None else "  ERROR"
            
            print(f"  {status_icon} Ch {ch_num:2d}: {data['info']['name']:42s} {value_str} {data['info']['unit']}")
        
        # Show wireless vs wired comparison
        if 16 in o2_sensors and 32 in o2_sensors:
            if o2_sensors[16]['value'] is not None and o2_sensors[32]['value'] is not None:
                diff = abs(o2_sensors[16]['value'] - o2_sensors[32]['value'])
                print(f"\n  → Wireless/Wired Difference: {diff:.3f} % O2")
                if diff > 0.5:
                    print(f"    ⚠ WARNING: Readings differ by more than 0.5%")
        print()
    
    # Display other gas sensors
    if other_sensors:
        print("  GAS SENSORS")
        print("  " + "-" * 76)
        for ch_num, data in other_sensors.items():
            status_icon = "✓" if data["status"] == "OK" else "✗"
            value_str = f"{data['value']:7.2f}" if data['value'] is not None else "  ERROR"
            
            print(f"  {status_icon} Ch {ch_num:2d}: {data['info']['name']:42s} {value_str} {data['info']['unit']}")
        print()
    
    print("=" * 80)
    print("  Press Ctrl+C to stop monitoring")
    print("=" * 80)

def main():
    """Main monitoring loop"""
    print("Starting OI-7032 monitor...")
    print("Connecting to COM10...")
    
    config = ModbusConfig(
        connection_type=ConnectionType.RTU,
        port='COM10',
        baudrate=9600,
        slave_id=1,
        timeout=3
    )
    
    try:
        client = ModbusClient(config)
        print("✓ Connected to OI-7032\n")
        time.sleep(1)
        
        cycle_count = 0
        
        while True:
            cycle_count += 1
            
            # Read all channels
            readings = read_all_channels(client)
            
            # Display
            display_readings(readings, cycle_count)
            
            # Wait 5 seconds before next poll
            time.sleep(5)
            
    except KeyboardInterrupt:
        print("\n\nMonitoring stopped by user")
    except Exception as e:
        print(f"\n\nError: {e}")
    finally:
        if 'client' in locals():
            client.close()
            print("Disconnected from OI-7032")

if __name__ == "__main__":
    main()
