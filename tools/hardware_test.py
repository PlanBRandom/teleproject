"""
OI Hardware Test Suite
Interactive testing for Modbus monitors and Laird radio modules
"""

import time
import sys
from pipeline.modbus_client import ModbusClient, ModbusConfig, ConnectionType
from pipeline.registers import GAS_TYPES, SENSOR_TYPES, RegisterAddresses
from pipeline.device_control import DeviceControl


def print_header(text):
    """Print formatted header"""
    print("\n" + "="*70)
    print(f"  {text}")
    print("="*70)


def print_subheader(text):
    """Print formatted subheader"""
    print(f"\n--- {text} ---")


def test_modbus_connection(port, slave_id, device_name):
    """Test basic Modbus connection"""
    print_subheader(f"Testing {device_name} (Slave {slave_id})")
    
    try:
        config = ModbusConfig(
            connection_type=ConnectionType.RTU,
            port=port,
            slave_id=slave_id,
            baudrate=9600
        )
        client = ModbusClient(config)
        
        # Try to read a register
        test_addr = RegisterAddresses.READING_BASE  # Channel 1 reading
        value = client.read_float32(test_addr)
        
        print(f"✓ Connection successful")
        print(f"  Channel 1 reading: {value:.2f} PPM")
        
        client.close()
        return True
        
    except Exception as e:
        print(f"✗ Connection failed: {e}")
        return False


def scan_active_channels(port, slave_id, device_name):
    """Scan for active channels"""
    print_subheader(f"Scanning Active Channels - {device_name}")
    
    try:
        config = ModbusConfig(
            connection_type=ConnectionType.RTU,
            port=port,
            slave_id=slave_id
        )
        client = ModbusClient(config)
        control = DeviceControl(client)
        
        active_channels = []
        
        for ch in range(1, 33):
            try:
                # Read sensor type (if 31, channel is disabled)
                sensor_type = client.read_holding_registers(
                    RegisterAddresses.SENSOR_TYPE_BASE + (ch - 1), 1
                )[0]
                
                if sensor_type != 31:  # 31 = None/Disabled
                    reading_addr = RegisterAddresses.READING_BASE + (ch - 1) * 2
                    reading = client.read_float32(reading_addr)
                    
                    gas_type_addr = RegisterAddresses.GAS_TYPE_BASE + (ch - 1)
                    gas_type = client.read_holding_registers(gas_type_addr, 1)[0]
                    
                    active_channels.append({
                        'channel': ch,
                        'reading': reading,
                        'sensor_type': sensor_type,
                        'gas_type': gas_type
                    })
            except:
                pass
        
        if active_channels:
            print(f"\n✓ Found {len(active_channels)} active channels:")
            print(f"\n{'Ch':<4} {'Reading':<12} {'Gas Type':<15} {'Sensor'}")
            print("-" * 50)
            
            for ch_data in active_channels:
                gas_name = GAS_TYPES.get(ch_data['gas_type'], 'Unknown')
                sensor_name = SENSOR_TYPES.get(ch_data['sensor_type'], 'Unknown')
                print(f"{ch_data['channel']:<4} {ch_data['reading']:>8.2f} PPM  "
                      f"{gas_name:<15} {sensor_name}")
        else:
            print("✗ No active channels found")
        
        client.close()
        return active_channels
        
    except Exception as e:
        print(f"✗ Scan failed: {e}")
        return []


def test_device_info(port, slave_id, device_name):
    """Test device information reading"""
    print_subheader(f"Reading Device Info - {device_name}")
    
    try:
        config = ModbusConfig(
            connection_type=ConnectionType.RTU,
            port=port,
            slave_id=slave_id
        )
        client = ModbusClient(config)
        control = DeviceControl(client)
        
        info = control.get_device_info()
        
        if info:
            print(f"✓ Device information:")
            print(f"  Serial Number:     {info.serial_number}")
            print(f"  Network Channel:   {info.network_channel}")
            print(f"  Primary/Secondary: {'Primary' if info.is_primary else 'Secondary'}")
            print(f"  Baud Rate:         {info.baud_rate}")
            print(f"  Radio Timeout:     {info.radio_timeout} sec")
        else:
            print("✗ Could not read device info")
        
        client.close()
        return info is not None
        
    except Exception as e:
        print(f"✗ Failed: {e}")
        return False


def test_diagnostics(port, slave_id, device_name):
    """Test diagnostics reading"""
    print_subheader(f"Reading Diagnostics - {device_name}")
    
    try:
        config = ModbusConfig(
            connection_type=ConnectionType.RTU,
            port=port,
            slave_id=slave_id
        )
        client = ModbusClient(config)
        control = DeviceControl(client)
        
        diag = control.get_diagnostics()
        
        if diag:
            print(f"✓ Diagnostics:")
            print(f"  Uptime:            {diag.uptime_hours:.1f} hours")
            print(f"  Modbus Requests:   {diag.modbus_requests}")
            print(f"  Modbus Errors:     {diag.modbus_errors}")
            
            error_rate = diag.error_rate
            if error_rate > 5:
                print(f"  ⚠️  Error Rate:      {error_rate:.2f}% (HIGH)")
            else:
                print(f"  Error Rate:        {error_rate:.2f}%")
        else:
            print("✗ Could not read diagnostics")
        
        client.close()
        return diag is not None
        
    except Exception as e:
        print(f"✗ Failed: {e}")
        return False


def test_maintenance_timing(port, slave_id, device_name, model):
    """Test maintenance timing (null/cal days)"""
    print_subheader(f"Checking Maintenance Timing - {device_name}")
    
    try:
        config = ModbusConfig(
            connection_type=ConnectionType.RTU,
            port=port,
            slave_id=slave_id
        )
        client = ModbusClient(config)
        control = DeviceControl(client)
        
        # This feature is only on 7010/7032, not 7530
        if '7530' in model.upper():
            print(f"ℹ️  Maintenance timing not available on OI-7530")
            client.close()
            return True
        
        print(f"\n{'Ch':<4} {'Gas Type':<10} {'Days Since Null':<18} {'Days Since Cal'}")
        print("-" * 60)
        
        for ch in [5, 7, 16, 21, 32]:  # Known active channels
            try:
                null_days = control.get_days_since_null(ch)
                cal_days = control.get_days_since_calibration(ch)
                
                gas_type_addr = RegisterAddresses.GAS_TYPE_BASE + (ch - 1)
                gas_type = client.read_holding_registers(gas_type_addr, 1)[0]
                gas_name = GAS_TYPES.get(gas_type, 'Unknown')
                
                if null_days >= 0 and cal_days >= 0:
                    null_status = "⚠️" if null_days > 90 else ""
                    cal_status = "⚠️" if cal_days > 180 else ""
                    
                    print(f"{ch:<4} {gas_name:<10} {null_days:>4} days {null_status:<10} "
                          f"{cal_days:>4} days {cal_status}")
            except:
                pass
        
        client.close()
        return True
        
    except Exception as e:
        print(f"✗ Failed: {e}")
        return False


def test_radio_module():
    """Test Laird radio module if connected"""
    print_header("Laird Radio Module Test")
    
    print("\nEnter COM port for Laird radio (or 'skip' to skip): ", end='')
    port = input().strip()
    
    if port.lower() == 'skip':
        print("Skipping radio test")
        return
    
    # Get network configuration
    print("\nEnter network channel (1-78, default 25): ", end='')
    channel_input = input().strip()
    network_channel = int(channel_input) if channel_input else 25
    
    print("\nIs this a PRIMARY or SECONDARY receiver?")
    print("  PRIMARY - Can transmit and receive (monitor replacement)")
    print("  SECONDARY - Receive only (passive listener)")
    print("Enter mode (primary/secondary, default secondary): ", end='')
    mode_input = input().strip().lower()
    is_primary = mode_input.startswith('p')
    
    try:
        from pipeline.radio_receiver import RadioReceiver
        import time
        
        print(f"\nConnecting to {port}...")
        receiver = RadioReceiver(port, baudrate=115200, api_mode=True)
        
        if not receiver.connect():
            print("✗ Failed to connect to radio")
            return
        
        print("✓ Connected to radio module")
        
        # Get MAC address
        print_subheader("Radio Information")
        mac = receiver.get_mac_address()
        if mac:
            print(f"✓ MAC Address: {mac}")
        else:
            print("✗ Could not read MAC address")
        
        # Get RSSI
        rssi = receiver.get_rssi()
        if rssi:
            print(f"✓ Current RSSI: {rssi} dBm")
            if rssi > -70:
                print("  Signal: Excellent ████████████")
            elif rssi > -85:
                print("  Signal: Good      ████████░░░░")
            elif rssi > -95:
                print("  Signal: Fair      ████░░░░░░░░")
            else:
                print("  Signal: Poor      ██░░░░░░░░░░")
        else:
            print("✗ Could not read RSSI")
        
        # Set channel
        print_subheader("Setting RF Channel")
        mode_str = "primary transmitter" if is_primary else "secondary receiver"
        if receiver.set_rf_channel(network_channel):
            print(f"✓ RF Channel set to {network_channel} ({mode_str})")
        else:
            print("✗ Failed to set RF channel")
        
        # Test transmission (primary mode only)
        if is_primary:
            print_subheader("Test Transmission (Primary Mode)")
            print("Send a test sensor reading? (y/n, default n): ", end='')
            send_test = input().strip().lower().startswith('y')
            
            if send_test:
                print("\nEnter test channel (1-32): ", end='')
                test_channel = int(input().strip() or "1")
                print("Enter test reading value: ", end='')
                test_reading = float(input().strip() or "50.0")
                print("Enter gas type (0-27, default 0=H2S): ", end='')
                test_gas = int(input().strip() or "0")
                
                print(f"\nSending: Ch {test_channel} = {test_reading:.2f} (Gas type {test_gas})...")
                if receiver.send_test_packet(test_channel, test_reading, test_gas):
                    print("✓ Test packet transmitted")
                else:
                    print("✗ Failed to transmit test packet")
                time.sleep(2)
        
        # Listen for packets
        print_subheader("Listening for Sensor Packets")
        print("Listening for 30 seconds... (sensors transmit every 60s)")
        
        packet_count = [0]  # Use list to modify in callback
        
        def on_packet(msg):
            packet_count[0] += 1
            print(f"\n✓ Packet {packet_count[0]} received:")
            print(f"  Channel {msg.channel}: {msg.reading:.2f}")
            if msg.battery_voltage:
                print(f"  Battery: {msg.battery_voltage:.1f}V")
        
        receiver.register_callback(on_packet)
        receiver.start()
        
        time.sleep(30)
        
        receiver.stop()
        receiver.disconnect()
        
        if packet_count[0] > 0:
            print(f"\n✓ Received {packet_count[0]} sensor packets")
        else:
            print(f"\n⚠️  No packets received (sensors may not be transmitting)")
            print(f"   Check: 1) Network channel (should be {network_channel})")
            print("          2) System ID (should be 37)")
            print("          3) Sensors are powered on")
            if not is_primary:
                print("          4) Sniff Permit enabled (secondary mode)")
        
    except ImportError:
        print("✗ Radio receiver module not available")
    except Exception as e:
        print(f"✗ Radio test failed: {e}")


def main():
    """Main test suite"""
    print_header("OI Hardware Test Suite")
    print("Testing Modbus monitors and Laird radio modules\n")
    
    # Get test configuration
    print("Enter COM port for Modbus monitors (e.g., COM10): ", end='')
    port = input().strip()
    
    if not port:
        print("No port specified, exiting")
        return
    
    # Test devices
    devices = [
        {'slave_id': 1, 'name': 'OI-7010', 'model': 'OI-7010'},
        {'slave_id': 2, 'name': 'OI-7530', 'model': 'OI-7530'},
        {'slave_id': 3, 'name': 'OI-7032', 'model': 'OI-7032'},
    ]
    
    results = {}
    
    # Test each device
    for device in devices:
        print_header(f"Testing {device['name']} (Slave {device['slave_id']})")
        
        # Connection test
        conn_ok = test_modbus_connection(port, device['slave_id'], device['name'])
        if not conn_ok:
            print(f"\n⚠️  Skipping further tests for {device['name']}")
            results[device['name']] = 'Failed'
            continue
        
        # Active channels
        channels = scan_active_channels(port, device['slave_id'], device['name'])
        
        # Device info
        test_device_info(port, device['slave_id'], device['name'])
        
        # Diagnostics
        test_diagnostics(port, device['slave_id'], device['name'])
        
        # Maintenance timing
        if channels:
            test_maintenance_timing(port, device['slave_id'], device['name'], device['model'])
        
        results[device['name']] = 'Passed'
        
        time.sleep(0.5)
    
    # Test radio
    test_radio_module()
    
    # Summary
    print_header("Test Summary")
    for device_name, status in results.items():
        status_icon = "✓" if status == 'Passed' else "✗"
        print(f"{status_icon} {device_name:<15} {status}")
    
    print("\nTests complete!")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nTests interrupted by user")
    except Exception as e:
        print(f"\n\nFatal error: {e}")
        import traceback
        traceback.print_exc()
