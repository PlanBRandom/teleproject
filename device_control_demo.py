#!/usr/bin/env python3
"""
Demonstration of all device control capabilities for OI monitors
Shows how to read/write startup menu settings, control channels, and manage relays
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from pipeline.modbus_client import ModbusClient, ModbusConfig
from pipeline.device_control import DeviceControl
from pipeline.registers import get_mode_name, MODE_CODES
import time


def print_section(title: str):
    """Print a formatted section header"""
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print('=' * 60)


def show_current_settings(control: DeviceControl, device_name: str, device_id: int):
    """Display current device settings"""
    print(f"\n{device_name} (Slave {device_id}) - Current Settings:")
    print("-" * 60)
    
    info = control.get_device_info(device_id)
    if info:
        print(f"  Serial Number: {info.serial_number}")
        print(f"  Network Channel: {info.network_channel}")
        print(f"  Mode: {'Primary' if info.is_primary else 'Secondary'}")
        print(f"  Radio Timeout: {info.radio_timeout_minutes} minutes")
        print(f"  Relay 1 Failsafe: {'Enabled' if info.relay1_failsafe else 'Disabled'}")
        print(f"  Relay 2 Failsafe: {'Enabled' if info.relay2_failsafe else 'Disabled'}")
        print(f"  Relay 3 Failsafe: {'Enabled' if info.relay3_failsafe else 'Disabled'}")
        print(f"  Relay 3 as Fault: {'Yes' if info.relay3_as_fault else 'No'}")


def show_channel_status(control: DeviceControl, channels: list, device_id: int):
    """Show status of specific channels"""
    print("\nActive Channels Status:")
    print("-" * 100)
    print(f"{'Ch':<4} {'Mode':<15} {'Msg':<8} {'Null':<8} {'Cal':<8} {'R1':<4} {'R2':<4} {'R3':<4}")
    print("-" * 100)
    
    for ch in channels:
        try:
            # Read mode
            mode_reg = 0x61 + (ch - 1)
            result = control.client.read_holding_registers(mode_reg, 1, device_id=device_id)
            mode = result.registers[0] if result else 0
            mode_name = get_mode_name(mode)
            
            # Read seconds since message
            seconds = control.get_seconds_since_message(ch, device_id)
            if seconds == -1:
                sec_str = "Never"
            elif seconds == 0:
                sec_str = "Timeout!"
            else:
                sec_str = f"{seconds}s"
            
            # Read days since null
            days_null = control.get_days_since_null(ch, device_id)
            null_str = f"{days_null}d" if days_null >= 0 and days_null < 65535 else "Never"
            
            # Read days since calibration
            days_cal = control.get_days_since_calibration(ch, device_id)
            cal_str = f"{days_cal}d" if days_cal >= 0 and days_cal < 65535 else "Never"
            
            # Read relay enables
            try:
                r1_reg = 0x161 + (ch - 1)
                r1_result = control.client.read_holding_registers(r1_reg, 1, device_id=device_id)
                r1_en = "Yes" if (r1_result and r1_result.registers[0]) else "No"
            except:
                r1_en = "?"
            
            try:
                r2_reg = 0x201 + (ch - 1)
                r2_result = control.client.read_holding_registers(r2_reg, 1, device_id=device_id)
                r2_en = "Yes" if (r2_result and r2_result.registers[0]) else "No"
            except:
                r2_en = "?"
            
            try:
                r3_reg = 0x2A1 + (ch - 1)
                r3_result = control.client.read_holding_registers(r3_reg, 1, device_id=device_id)
                r3_en = "Yes" if (r3_result and r3_result.registers[0]) else "No"
            except:
                r3_en = "?"
            
            print(f"{ch:<4} {mode_name:<15} {sec_str:<8} {null_str:<8} {cal_str:<8} {r1_en:<4} {r2_en:<4} {r3_en:<4}")
            
        except Exception as e:
            print(f"{ch:<4} Error: {e}")


def demonstrate_startup_menu_control(control: DeviceControl, device_id: int):
    """Demonstrate startup menu setting control"""
    print_section("Startup Menu Settings Control")
    
    print("\nAvailable Commands:")
    print("  1. Change network channel (1-78)")
    print("  2. Set Primary/Secondary mode")
    print("  3. Set radio timeout (6-255 minutes)")
    print("  4. Configure Relay 3 as fault relay")
    print("  5. Set relay fail-safe modes")
    
    print("\nExample: Set network channel to 2")
    print("  control.set_network_channel(2, device_id)")
    
    print("\nExample: Set as secondary monitor")
    print("  control.set_primary_secondary(is_primary=False, device_id)")
    
    print("\nExample: Set radio timeout to 30 minutes")
    print("  control.set_radio_timeout(30, device_id)")
    
    print("\nExample: Enable Relay 3 as fault relay")
    print("  control.set_relay3_as_fault(enabled=True, device_id)")
    
    print("\nExample: Enable Relay 1 fail-safe mode")
    print("  control.set_relay_failsafe(relay_num=1, enabled=True, device_id)")


def demonstrate_channel_control(control: DeviceControl, device_id: int):
    """Demonstrate channel control"""
    print_section("Channel Control")
    
    print("\nAvailable Commands:")
    print("  1. Turn channel on/off")
    print("  2. Set channel mode (Off, Normal, Inhibit, Maintenance, etc.)")
    print("  3. Enable/disable relay for channel")
    print("  4. Set relay setpoints")
    
    print("\nMode Codes:")
    for code, name in MODE_CODES.items():
        print(f"  {code}: {name}")
    
    print("\nExample: Turn channel 5 on")
    print("  control.turn_channel_on(5, device_id)")
    
    print("\nExample: Turn channel 10 off")
    print("  control.turn_channel_off(10, device_id)")
    
    print("\nExample: Set channel 16 to Inhibit mode")
    print("  control.set_channel_inhibit(16, device_id)")
    
    print("\nExample: Enable Relay 1 for channel 5")
    print("  control.enable_relay(channel=5, relay_num=1, enabled=True, device_id)")
    
    print("\nExample: Set Relay 1 setpoint to 10.0 PPM for channel 5")
    print("  control.set_relay_setpoint(channel=5, relay_num=1, setpoint=10.0, device_id)")


def demonstrate_relay_control(control: DeviceControl, device_id: int):
    """Demonstrate relay control"""
    print_section("Relay Control")
    
    print("\nRelay Status:")
    relay_status = control.get_relay_status(device_id)
    if relay_status:
        print(f"  Relay 1: {'Energized' if relay_status.relay1_on else 'De-energized'} "
              f"(Failsafe: {'On' if relay_status.relay1_failsafe else 'Off'})")
        print(f"  Relay 2: {'Energized' if relay_status.relay2_on else 'De-energized'} "
              f"(Failsafe: {'On' if relay_status.relay2_failsafe else 'Off'})")
        print(f"  Relay 3: {'Energized' if relay_status.relay3_on else 'De-energized'} "
              f"(Failsafe: {'On' if relay_status.relay3_failsafe else 'Off'}, "
              f"Fault Mode: {'Yes' if relay_status.relay3_as_fault else 'No'})")
    
    print("\nAvailable Commands:")
    print("  1. Set relay setpoint for a channel")
    print("  2. Enable/disable relay for a channel")
    print("  3. Set relay fail-safe mode")
    
    print("\nExample: Set Relay 1 alarm at 15 PPM for channel 1")
    print("  control.set_relay_setpoint(channel=1, relay_num=1, setpoint=15.0, device_id)")
    
    print("\nExample: Enable Relay 2 for channel 7")
    print("  control.enable_relay(channel=7, relay_num=2, enabled=True, device_id)")


def interactive_menu(control: DeviceControl, device_id: int, device_name: str):
    """Interactive control menu"""
    
    while True:
        print_section(f"{device_name} Control Menu")
        print("\n1. Show current settings")
        print("2. Show channel status")
        print("3. Change network channel")
        print("4. Set Primary/Secondary")
        print("5. Turn channel on/off")
        print("6. Set channel inhibit mode")
        print("7. Set relay setpoint")
        print("8. Enable/disable relay")
        print("9. View all capabilities")
        print("0. Exit")
        
        choice = input("\nSelect option: ").strip()
        
        if choice == '0':
            break
        elif choice == '1':
            show_current_settings(control, device_name, device_id)
        elif choice == '2':
            channels = [5, 7, 16, 21, 32]  # Your active channels
            show_channel_status(control, channels, device_id)
        elif choice == '3':
            channel = input("Enter network channel (1-78): ").strip()
            try:
                ch = int(channel)
                if control.set_network_channel(ch, device_id):
                    print(f"✓ Network channel set to {ch}")
                else:
                    print("✗ Failed to set network channel")
            except ValueError:
                print("Invalid input")
        elif choice == '4':
            mode = input("Set as (P)rimary or (S)econdary: ").strip().upper()
            if mode in ['P', 'S']:
                is_primary = (mode == 'P')
                if control.set_primary_secondary(is_primary, device_id):
                    print(f"✓ Set as {'Primary' if is_primary else 'Secondary'}")
                else:
                    print("✗ Failed to set mode")
            else:
                print("Invalid input")
        elif choice == '5':
            ch = input("Enter channel number (1-32): ").strip()
            action = input("(O)n or Off: ").strip().upper()
            try:
                channel_num = int(ch)
                if action == 'O':
                    if control.turn_channel_on(channel_num, device_id):
                        print(f"✓ Channel {channel_num} turned on")
                    else:
                        print("✗ Failed")
                else:
                    if control.turn_channel_off(channel_num, device_id):
                        print(f"✓ Channel {channel_num} turned off")
                    else:
                        print("✗ Failed")
            except ValueError:
                print("Invalid input")
        elif choice == '6':
            ch = input("Enter channel number (1-32): ").strip()
            try:
                channel_num = int(ch)
                if control.set_channel_inhibit(channel_num, device_id):
                    print(f"✓ Channel {channel_num} set to Inhibit mode")
                else:
                    print("✗ Failed")
            except ValueError:
                print("Invalid input")
        elif choice == '7':
            ch = input("Enter channel number (1-32): ").strip()
            relay = input("Enter relay number (1-3): ").strip()
            setpoint = input("Enter setpoint value: ").strip()
            try:
                channel_num = int(ch)
                relay_num = int(relay)
                sp = float(setpoint)
                if control.set_relay_setpoint(channel_num, relay_num, sp, device_id):
                    print(f"✓ Relay {relay_num} setpoint set to {sp} for channel {channel_num}")
                else:
                    print("✗ Failed")
            except ValueError:
                print("Invalid input")
        elif choice == '8':
            ch = input("Enter channel number (1-32): ").strip()
            relay = input("Enter relay number (1-3): ").strip()
            enable = input("(E)nable or (D)isable: ").strip().upper()
            try:
                channel_num = int(ch)
                relay_num = int(relay)
                enabled = (enable == 'E')
                if control.enable_relay(channel_num, relay_num, enabled, device_id):
                    print(f"✓ Relay {relay_num} {'enabled' if enabled else 'disabled'} for channel {channel_num}")
                else:
                    print("✗ Failed")
            except ValueError:
                print("Invalid input")
        elif choice == '9':
            demonstrate_startup_menu_control(control, device_id)
            demonstrate_channel_control(control, device_id)
            demonstrate_relay_control(control, device_id)
            input("\nPress Enter to continue...")


def main():
    # Configuration
    config = ModbusConfig(
        port='COM10',
        slave_id=1,
        baudrate=9600
    )
    
    DEVICES = [
        (1, "OI-7010"),
        (2, "OI-7530"),
        (3, "OI-7032")
    ]
    
    print("OI Monitor Device Control Demonstration")
    print("=" * 60)
    
    # Connect to modbus
    client = ModbusClient(config)
    if not client.connect():
        print("Failed to connect to Modbus")
        return
    
    control = DeviceControl(client)
    
    try:
        print("\nSelect device:")
        for idx, (device_id, name) in enumerate(DEVICES, 1):
            print(f"{idx}. {name} (Slave {device_id})")
        
        choice = input("\nDevice number: ").strip()
        try:
            device_idx = int(choice) - 1
            if 0 <= device_idx < len(DEVICES):
                device_id, device_name = DEVICES[device_idx]
                
                # Show current settings
                show_current_settings(control, device_name, device_id)
                
                # Show channel status for common active channels
                channels = [5, 7, 16, 21, 32]
                show_channel_status(control, channels, device_id)
                
                # Show control capabilities
                print("\n" + "=" * 60)
                print("Control Capabilities Available:")
                print("=" * 60)
                demonstrate_startup_menu_control(control, device_id)
                demonstrate_channel_control(control, device_id)
                demonstrate_relay_control(control, device_id)
                
                # Interactive menu
                proceed = input("\nEnter interactive control menu? (y/n): ").strip().lower()
                if proceed == 'y':
                    interactive_menu(control, device_id, device_name)
            else:
                print("Invalid device number")
        except ValueError:
            print("Invalid input")
    
    finally:
        client.disconnect()
        print("\nDisconnected from Modbus")


if __name__ == "__main__":
    main()
