"""
Device information and control demonstration
Shows how to read device info, diagnostics, and execute control commands
"""
from pipeline.modbus_client import ModbusClient, ModbusConfig, ConnectionType
from pipeline.device_control import DeviceControl

DEVICES = [
    {"name": "OI-7010", "slave_id": 1},
    {"name": "OI-7530", "slave_id": 2},
    {"name": "OI-7032", "slave_id": 3}
]

def display_device_info(name, info):
    """Display device configuration"""
    print(f"\n{name} DEVICE INFORMATION:")
    print(f"{'='*60}")
    print(f"Modbus Address:        {info.modbus_address}")
    print(f"Baud Rate:             {info.baud_rate}")
    print(f"Serial Number:         {info.serial_number}")
    print(f"Date:                  {info.date_month}/{info.date_day}/{info.date_year}")
    print(f"Network Channel:       {info.network_channel}")
    print(f"Radio Timeout:         {info.radio_timeout} minutes")
    print(f"Primary/Secondary:     {'Primary' if info.is_primary else 'Secondary'}")
    print(f"Relay 1 Fail Safe:     {'Yes' if info.relay1_failsafe else 'No'}")
    print(f"Relay 2 Fail Safe:     {'Yes' if info.relay2_failsafe else 'No'}")
    print(f"Relay 3 Fail Safe:     {'Yes' if info.relay3_failsafe else 'No'}")
    print(f"Relay 3 as Fault:      {'Yes' if info.relay3_as_fault else 'No'}")
    print(f"Fault Term Fail Safe:  {'Yes' if info.fault_terminal_failsafe else 'No'}")

def display_diagnostics(name, diag):
    """Display diagnostics information"""
    print(f"\n{name} DIAGNOSTICS:")
    print(f"{'='*60}")
    print(f"Uptime:                {diag.uptime_string}")
    print(f"\nSerial Communication:")
    print(f"  RX Good:             {diag.serial_rx_good}")
    print(f"  RX Errors:           {diag.serial_rx_error}")
    print(f"  TX Good:             {diag.serial_tx_good}")
    print(f"  TX Errors:           {diag.serial_tx_error}")
    print(f"  Error Rate:          {diag.serial_error_rate:.2f}%")
    print(f"\nRadio Communication:")
    print(f"  RX Good:             {diag.radio_rx_good}")
    print(f"  RX Errors:           {diag.radio_rx_error}")
    print(f"  TX Good:             {diag.radio_tx_good}")
    print(f"  TX Errors:           {diag.radio_tx_error}")
    print(f"  Error Rate:          {diag.radio_error_rate:.2f}%")

def display_relay_status(name, relay):
    """Display relay alarm status"""
    print(f"\n{name} RELAY STATUS:")
    print(f"{'='*60}")
    print(f"Relay 1:               {'⚠ IN ALARM' if relay.relay1_in_alarm else '✓ Normal'}")
    print(f"Relay 2:               {'⚠ IN ALARM' if relay.relay2_in_alarm else '✓ Normal'}")
    print(f"Relay 3:               {'⚠ IN ALARM' if relay.relay3_in_alarm else '✓ Normal'}")

def main():
    """Main demonstration"""
    config = ModbusConfig(
        connection_type=ConnectionType.RTU,
        port='COM10',
        slave_id=1
    )
    
    print("Connecting to OI monitors on COM10...")
    client = ModbusClient(config)
    control = DeviceControl(client)
    print("✓ Connected\n")
    
    print("="*80)
    print("DEVICE INFORMATION, DIAGNOSTICS & CONTROL")
    print("="*80)
    
    # Read info from all devices
    for device in DEVICES:
        try:
            print(f"\n\nReading {device['name']} (slave {device['slave_id']})...")
            
            # Device info
            info = control.get_device_info(device_id=device['slave_id'])
            display_device_info(device['name'], info)
            
            # Diagnostics
            diag = control.get_diagnostics(device_id=device['slave_id'])
            display_diagnostics(device['name'], diag)
            
            # Relay status
            relay = control.get_relay_status(device_id=device['slave_id'])
            display_relay_status(device['name'], relay)
            
        except Exception as e:
            print(f"\n⚠ Error reading {device['name']}: {e}")
    
    # Show available control commands
    print(f"\n\n{'='*80}")
    print("AVAILABLE CONTROL COMMANDS:")
    print(f"{'='*80}")
    print("1. control.reset_device(device_id=X)       - Restart/reboot the monitor")
    print("2. control.factory_reset(device_id=X)      - Restore to factory defaults")
    print("\nNote: These commands require confirmation and will restart the device.")
    print("Example usage:")
    print("  control.reset_device(device_id=3)  # Reset OI-7032")
    
    print(f"\n{'='*80}\n")
    
    client.close()

if __name__ == "__main__":
    main()
