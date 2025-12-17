#!/usr/bin/env python3
"""
Check maintenance timing for all active channels
Shows days since last null and calibration
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from pipeline.modbus_client import ModbusClient, ModbusConfig, ConnectionType
from pipeline.device_control import DeviceControl


def main():
    config = ModbusConfig(
        connection_type=ConnectionType.RTU,
        port='COM10',
        slave_id=1,
        baudrate=9600
    )
    
    DEVICES = [
        (1, "OI-7010"),
        (2, "OI-7530"),
        (3, "OI-7032")
    ]
    
    ACTIVE_CHANNELS = [5, 7, 16, 21, 32]
    
    client = ModbusClient(config)
    control = DeviceControl(client)
    
    try:
        for device_id, device_name in DEVICES:
            print(f"\n{'=' * 80}")
            print(f"{device_name} (Slave {device_id}) - Maintenance Timing")
            print('=' * 80)
            print(f"\n{'Ch':<4} {'Last Msg':<12} {'Days Since Null':<18} {'Days Since Cal':<18}")
            print('-' * 80)
            
            for channel in ACTIVE_CHANNELS:
                try:
                    # Get timing data
                    seconds = control.get_seconds_since_message(channel, device_id)
                    days_null = control.get_days_since_null(channel, device_id)
                    days_cal = control.get_days_since_calibration(channel, device_id)
                    
                    # Format seconds
                    if seconds == -1:
                        sec_str = "Never"
                    elif seconds == 0:
                        sec_str = "TIMEOUT!"
                    elif seconds < 60:
                        sec_str = f"{seconds}s"
                    elif seconds < 3600:
                        sec_str = f"{seconds//60}m {seconds%60}s"
                    else:
                        sec_str = f"{seconds//3600}h {(seconds%3600)//60}m"
                    
                    # Format days (handle unsupported on 7530)
                    if days_null == -1:
                        null_str = "N/A"
                    elif days_null < 65535:
                        null_str = f"{days_null} days"
                    else:
                        null_str = "Never"
                    
                    if days_cal == -1:
                        cal_str = "N/A"
                    elif days_cal < 65535:
                        cal_str = f"{days_cal} days"
                    else:
                        cal_str = "Never"
                    
                    # Color coding for warnings
                    warning = ""
                    if days_null > 90:
                        warning = " ⚠️ NULL OVERDUE"
                    elif days_cal > 180:
                        warning = " ⚠️ CAL OVERDUE"
                    
                    print(f"{channel:<4} {sec_str:<12} {null_str:<18} {cal_str:<18}{warning}")
                    
                except Exception as e:
                    print(f"{channel:<4} Error: {e}")
        
        print(f"\n{'=' * 80}")
        print("Maintenance timing check complete")
    
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
