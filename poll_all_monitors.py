#!/usr/bin/env python3
"""
Poll All Monitors via Modbus
Continuously polls all 3 OI monitors (7010, 7530, 7032) to generate Modbus traffic.
This runs alongside the monitor to capture both radio and Modbus data.
"""

import serial
import time
import struct
import logging
from datetime import datetime

# Configuration
MODBUS_PORT = 'COM10'
MODBUS_BAUDRATE = 9600
POLL_INTERVAL = 5  # seconds between polls

# Device configurations
DEVICES = [
    {'name': 'OI-7010', 'slave_id': 10, 'channels': range(1, 33)},
    {'name': 'OI-7530', 'slave_id': 30, 'channels': range(1, 33)},
    {'name': 'OI-7032', 'slave_id': 32, 'channels': range(1, 33)},
]

# Key register addresses (from register map)
REGISTERS = {
    'channel_reading': 0x0000,  # Channel 1 reading at 0x0000, each channel is +6 registers
    'channel_status': 0x0004,   # Channel status (offset +4 from reading)
    'device_status': 0x0190,    # Device status register
}

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def calculate_crc16_modbus(data: bytes) -> int:
    """Calculate Modbus RTU CRC16"""
    crc = 0xFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 0x0001:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1
    return crc

def create_modbus_request(slave_id: int, function_code: int, start_address: int, count: int) -> bytes:
    """Create a Modbus RTU request"""
    request = struct.pack('>BBHH', slave_id, function_code, start_address, count)
    crc = calculate_crc16_modbus(request)
    return request + struct.pack('<H', crc)

def poll_device_status(ser: serial.Serial, slave_id: int, device_name: str):
    """Poll device status register"""
    try:
        # Read device status register (address 0x0190, 1 register)
        request = create_modbus_request(slave_id, 0x03, REGISTERS['device_status'], 1)
        ser.write(request)
        ser.flush()
        
        # Wait for response
        time.sleep(0.05)
        
        if ser.in_waiting > 0:
            response = ser.read(ser.in_waiting)
            logger.debug(f"{device_name} (slave {slave_id}) - Device status: {response.hex()}")
            return True
        else:
            logger.warning(f"{device_name} (slave {slave_id}) - No response for device status")
            return False
            
    except Exception as e:
        logger.error(f"{device_name} (slave {slave_id}) - Error polling device status: {e}")
        return False

def poll_channel(ser: serial.Serial, slave_id: int, channel: int, device_name: str):
    """Poll a specific channel's reading"""
    try:
        # Calculate register address for this channel
        # Each channel has 6 registers, starting at 0x0000 for channel 1
        base_address = (channel - 1) * 6
        
        # Read 6 registers (reading + status + metadata)
        request = create_modbus_request(slave_id, 0x03, base_address, 6)
        ser.write(request)
        ser.flush()
        
        # Wait for response
        time.sleep(0.05)
        
        if ser.in_waiting > 0:
            response = ser.read(ser.in_waiting)
            logger.debug(f"{device_name} Ch{channel:2d} (slave {slave_id}): {response.hex()}")
            return True
        else:
            logger.debug(f"{device_name} Ch{channel:2d} (slave {slave_id}): No response")
            return False
            
    except Exception as e:
        logger.error(f"{device_name} Ch{channel:2d} (slave {slave_id}): Error - {e}")
        return False

def poll_all_devices(ser: serial.Serial):
    """Poll all devices once"""
    start_time = time.time()
    total_requests = 0
    successful_requests = 0
    
    logger.info("="*60)
    logger.info(f"Polling cycle started - {datetime.now().strftime('%H:%M:%S')}")
    
    for device in DEVICES:
        device_name = device['name']
        slave_id = device['slave_id']
        
        logger.info(f"Polling {device_name} (slave {slave_id})...")
        
        # Poll device status first
        total_requests += 1
        if poll_device_status(ser, slave_id, device_name):
            successful_requests += 1
        
        time.sleep(0.1)
        
        # Poll each channel
        for channel in device['channels']:
            total_requests += 1
            if poll_channel(ser, slave_id, channel, device_name):
                successful_requests += 1
            
            time.sleep(0.1)  # Small delay between requests
    
    elapsed = time.time() - start_time
    logger.info(f"Polling cycle complete - {successful_requests}/{total_requests} successful")
    logger.info(f"Cycle time: {elapsed:.1f}s")
    logger.info("="*60)
    
    return successful_requests, total_requests

def main():
    """Main polling loop"""
    logger.info("="*60)
    logger.info("OI MONITORS MODBUS POLLER")
    logger.info("="*60)
    logger.info(f"Port: {MODBUS_PORT}")
    logger.info(f"Baudrate: {MODBUS_BAUDRATE}")
    logger.info(f"Poll interval: {POLL_INTERVAL}s")
    logger.info("")
    logger.info("Devices:")
    for device in DEVICES:
        logger.info(f"  - {device['name']} (slave {device['slave_id']}): {len(device['channels'])} channels")
    logger.info("="*60)
    logger.info("")
    
    try:
        # Open serial port
        ser = serial.Serial(
            port=MODBUS_PORT,
            baudrate=MODBUS_BAUDRATE,
            bytesize=8,
            parity='N',
            stopbits=1,
            timeout=1
        )
        
        logger.info(f"✓ Connected to {MODBUS_PORT}")
        logger.info("")
        logger.info("Press Ctrl+C to stop")
        logger.info("")
        
        cycle_count = 0
        total_success = 0
        total_attempts = 0
        
        while True:
            cycle_count += 1
            logger.info(f"\n{'='*60}")
            logger.info(f"CYCLE {cycle_count}")
            
            success, attempts = poll_all_devices(ser)
            total_success += success
            total_attempts += attempts
            
            success_rate = (total_success / total_attempts * 100) if total_attempts > 0 else 0
            logger.info(f"\nOverall success rate: {success_rate:.1f}% ({total_success}/{total_attempts})")
            
            # Wait before next cycle
            logger.info(f"\nWaiting {POLL_INTERVAL}s before next cycle...")
            time.sleep(POLL_INTERVAL)
    
    except serial.SerialException as e:
        logger.error(f"Serial port error: {e}")
        return 1
    
    except KeyboardInterrupt:
        logger.info("\n\n✓ Stopped by user (Ctrl+C)")
        return 0
    
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return 1
    
    finally:
        if 'ser' in locals() and ser.is_open:
            ser.close()
            logger.info("Serial port closed")

if __name__ == '__main__':
    import sys
    sys.exit(main())
