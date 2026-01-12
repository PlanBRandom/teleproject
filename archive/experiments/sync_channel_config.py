"""
Synchronize channel configuration from OI-7032 to OI-7010 and OI-7530
Copies radio addresses, mode settings, and other channel configurations
"""
from pipeline.modbus_client import ModbusClient, ModbusConfig, ConnectionType
import time

# Device addresses
SOURCE_DEVICE = {"name": "OI-7032", "slave_id": 3}
TARGET_DEVICES = [
    {"name": "OI-7010", "slave_id": 1},
    {"name": "OI-7530", "slave_id": 2}
]

def read_channel_config(client: ModbusClient, slave_id: int, channel: int):
    """Read all configuration registers for a channel"""
    config = {}
    
    # Radio address (0x01-0x20)
    radio_addr_reg = channel
    try:
        config['radio_address'] = client.read_holding_registers(radio_addr_reg, 1, device_id=slave_id)[0]
    except:
        config['radio_address'] = None
    
    # Mode (0x61-0x80)
    mode_reg = 0x61 + (channel - 1)
    try:
        config['mode'] = client.read_holding_registers(mode_reg, 1, device_id=slave_id)[0]
    except:
        config['mode'] = None
    
    # Relay 1 On/Off (0x161-0x180 / 353-384)
    relay1_enable_reg = 0x161 + (channel - 1)
    try:
        config['relay1_enable'] = client.read_holding_registers(relay1_enable_reg, 1, device_id=slave_id)[0]
    except:
        config['relay1_enable'] = None
    
    # Relay 1 Setpoint (0x1A1-0x1DF / 417-479) - Float32
    relay1_setpoint_reg = 0x1A1 + (channel - 1) * 2
    try:
        config['relay1_setpoint'] = client.read_float32(relay1_setpoint_reg, device_id=slave_id)
    except:
        config['relay1_setpoint'] = None
    
    return config

def write_channel_config(client: ModbusClient, slave_id: int, channel: int, config: dict):
    """Write configuration registers for a channel"""
    results = []
    
    # Radio address
    if config['radio_address'] is not None:
        radio_addr_reg = channel
        try:
            client.client.write_register(radio_addr_reg, config['radio_address'], device_id=slave_id)
            results.append(f"  Radio address: {config['radio_address']}")
        except Exception as e:
            results.append(f"  Radio address: FAILED - {e}")
    
    # Mode
    if config['mode'] is not None:
        mode_reg = 0x61 + (channel - 1)
        try:
            client.client.write_register(mode_reg, config['mode'], device_id=slave_id)
            results.append(f"  Mode: {config['mode']}")
        except Exception as e:
            results.append(f"  Mode: FAILED - {e}")
    
    # Relay 1 Enable
    if config['relay1_enable'] is not None:
        relay1_enable_reg = 0x161 + (channel - 1)
        try:
            client.client.write_register(relay1_enable_reg, config['relay1_enable'], device_id=slave_id)
            results.append(f"  Relay1 enable: {config['relay1_enable']}")
        except Exception as e:
            results.append(f"  Relay1 enable: FAILED - {e}")
    
    # Relay 1 Setpoint (Float32 - need to write two registers)
    if config['relay1_setpoint'] is not None:
        relay1_setpoint_reg = 0x1A1 + (channel - 1) * 2
        try:
            # Convert float to two 16-bit registers
            import struct
            bytes_data = struct.pack('>f', config['relay1_setpoint'])
            high, low = struct.unpack('>HH', bytes_data)
            client.client.write_registers(relay1_setpoint_reg, [high, low], device_id=slave_id)
            results.append(f"  Relay1 setpoint: {config['relay1_setpoint']:.2f}")
        except Exception as e:
            results.append(f"  Relay1 setpoint: FAILED - {e}")
    
    return results

def sync_all_channels(client: ModbusClient, channels=range(1, 33)):
    """Synchronize all channel configurations"""
    
    print(f"\n{'='*80}")
    print(f"CHANNEL CONFIGURATION SYNC: {SOURCE_DEVICE['name']} → Targets")
    print(f"{'='*80}\n")
    
    print(f"Reading configuration from {SOURCE_DEVICE['name']} (slave {SOURCE_DEVICE['slave_id']})...")
    
    # Read all configs from source
    source_configs = {}
    for ch in channels:
        config = read_channel_config(client, SOURCE_DEVICE['slave_id'], ch)
        source_configs[ch] = config
        if config['radio_address'] and config['radio_address'] > 0:
            print(f"  Ch{ch:2d}: Radio={config['radio_address']:3d}, Mode={config['mode']}")
    
    print(f"\n{'='*80}\n")
    
    # Write configs to target devices
    for target in TARGET_DEVICES:
        print(f"Syncing to {target['name']} (slave {target['slave_id']})...")
        
        for ch in channels:
            config = source_configs[ch]
            
            # Only sync channels that have a radio address configured
            if config['radio_address'] and config['radio_address'] > 0:
                print(f"\nChannel {ch:2d}:")
                results = write_channel_config(client, target['slave_id'], ch, config)
                for result in results:
                    print(result)
                time.sleep(0.05)  # Small delay between writes
        
        print(f"\n✓ {target['name']} synchronized\n")
        print(f"{'='*80}\n")

def verify_sync(client: ModbusClient, channels=range(1, 33)):
    """Verify synchronization by reading back configs"""
    print("VERIFICATION: Reading back configurations...\n")
    
    all_devices = [SOURCE_DEVICE] + TARGET_DEVICES
    
    for ch in channels:
        configs = {}
        for device in all_devices:
            config = read_channel_config(client, device['slave_id'], ch)
            configs[device['name']] = config
        
        # Check if all have same radio address
        radio_addrs = [c['radio_address'] for c in configs.values() if c['radio_address'] is not None]
        if radio_addrs and any(r > 0 for r in radio_addrs):
            unique = set(radio_addrs)
            if len(unique) == 1:
                status = "✓"
            else:
                status = "⚠"
            
            print(f"Ch{ch:2d} {status}: ", end="")
            for device in all_devices:
                config = configs[device['name']]
                print(f"{device['name']}(R:{config['radio_address']:3d},M:{config['mode']})  ", end="")
            print()

def main():
    """Main synchronization"""
    config = ModbusConfig(
        connection_type=ConnectionType.RTU,
        port='COM10',
        slave_id=1
    )
    
    print("Connecting to OI monitors on COM10...")
    client = ModbusClient(config)
    print("✓ Connected\n")
    
    # Ask for confirmation
    print("This will copy channel configuration from OI-7032 to OI-7010 and OI-7530.")
    print("This includes radio addresses, modes, relay settings, and setpoints.")
    response = input("\nContinue? (yes/no): ")
    
    if response.lower() not in ['yes', 'y']:
        print("Cancelled.")
        client.close()
        return
    
    # Perform sync
    sync_all_channels(client)
    
    # Verify
    verify_sync(client)
    
    print("\n✓ Synchronization complete!\n")
    print("Run scan_multi_device.py to verify all monitors are receiving the same sensors.\n")
    
    client.close()

if __name__ == "__main__":
    main()
