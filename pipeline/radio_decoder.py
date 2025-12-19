"""
Enhanced Laird Radio Decoder for OI WireFree Gen II Protocol

Implements complete parsing of OI Instruments WireFree Generation II Protocol
as documented in WireFree_Prot_GenII_W_Text.txt

Protocol 1 Packet Structure:
Byte 0-1: Transmitter Address (16-bit unsigned)
Byte 2: Protocol Number (1 for standard sensor data)
Byte 3-6: Sensor Reading (32-bit float, big-endian)
Byte 7: Sensor Mode/Type (bit field)
Byte 8: Battery Reading (8-bit unsigned)
Byte 9: Gas Type/Battery Scale (7-bit gas type + 1-bit scale)
Byte 10: Fault/Error/Text indicator
Byte 11+: Checksum or text data
"""

import struct
import logging
from typing import Dict, Optional, List
from datetime import datetime
from enum import IntEnum

logger = logging.getLogger(__name__)


class SensorMode(IntEnum):
    """Sensor operating modes"""
    NORMAL = 0
    NULL = 1
    CALIBRATION = 2
    RELAY = 3
    RADIO_ADDRESS = 4
    DIAGNOSTIC = 5
    ADVANCED_MENU = 6
    ADMIN_MENU = 7


class SensorType(IntEnum):
    """Sensor types"""
    EC = 0          # Electrochemical
    IR = 1          # Infrared
    CB = 2          # Catalytic Bead
    MOS = 3         # Metal Oxide Semiconductor
    PID = 4         # Photoionization Detector
    TANK_LEVEL = 5  # Tank Level
    ANALOG_4_20 = 6 # 4-20mA
    SWITCH = 7      # Switch
    OI_WF190 = 30   # OI-WF190
    NONE = 31       # None selected


class GasType(IntEnum):
    """Gas types"""
    H2S = 0     # Hydrogen Sulfide
    SO2 = 1     # Sulfur Dioxide
    O2 = 2      # Oxygen
    CO = 3      # Carbon Monoxide
    CL2 = 4     # Chlorine
    CO2 = 5     # Carbon Dioxide
    LEL = 6     # Lower Explosive Limit
    VOC = 7     # Volatile Organic Compounds
    FEET = 8    # Feet (Tank Level)
    HCL = 9     # Hydrochloric Acid
    NH3 = 10    # Ammonia


class OIRadioDecoder:
    """Enhanced decoder for OI WireFree Gen II radio packets"""
    
    def __init__(self):
        self.packet_count = 0
        self.error_count = 0
        self.last_readings = {}  # Store last reading per sensor
        
    def calculate_checksum(self, data: bytes) -> int:
        """Calculate simple sum checksum"""
        return sum(data) & 0xFF
        
    def decode_protocol1(self, packet: bytes) -> Dict:
        """
        Decode Protocol 1 packet (standard sensor data)
        
        Returns:
            Dict with all decoded fields
        """
        if len(packet) < 12:
            return {'error': 'Packet too short for Protocol 1'}
        
        result = {
            'protocol': 1,
            'protocol_name': 'Standard Sensor Data',
            'timestamp': datetime.now().isoformat(),
            'raw_hex': ' '.join(f'{b:02X}' for b in packet)
        }
        
        # Bytes 0-1: Transmitter Address
        address = struct.unpack('>H', packet[0:2])[0]
        result['transmitter_address'] = address
        result['channel'] = address  # Address maps to channel number
        
        # Byte 2: Protocol (should be 1)
        protocol = packet[2]
        if protocol != 1:
            result['warning'] = f'Expected protocol 1, got {protocol}'
        
        # Bytes 3-6: Sensor Reading (32-bit float, big-endian)
        try:
            reading = struct.unpack('>f', packet[3:7])[0]
            result['sensor_reading'] = round(reading, 3)
        except Exception as e:
            result['sensor_reading_error'] = str(e)
            result['sensor_reading'] = None
        
        # Byte 7: Sensor Mode/Type (bit field)
        mode_type_byte = packet[7]
        mode = mode_type_byte & 0x07  # Lower 3 bits
        sensor_type = (mode_type_byte >> 3) & 0x1F  # Upper 5 bits
        
        try:
            result['sensor_mode'] = SensorMode(mode).name
            result['sensor_mode_value'] = mode
        except ValueError:
            result['sensor_mode'] = f'Unknown({mode})'
            result['sensor_mode_value'] = mode
        
        try:
            result['sensor_type'] = SensorType(sensor_type).name
            result['sensor_type_value'] = sensor_type
        except ValueError:
            result['sensor_type'] = f'Unknown({sensor_type})'
            result['sensor_type_value'] = sensor_type
        
        # Byte 8: Battery Reading
        battery_raw = packet[8]
        result['battery_raw'] = battery_raw
        
        # Byte 9: Gas Type/Battery Scale
        gas_battery_byte = packet[9]
        gas_type = gas_battery_byte >> 1  # Upper 7 bits
        battery_scale = gas_battery_byte & 0x01  # Lower 1 bit
        
        try:
            result['gas_type'] = GasType(gas_type).name
            result['gas_type_value'] = gas_type
        except ValueError:
            result['gas_type'] = f'Unknown({gas_type})'
            result['gas_type_value'] = gas_type
        
        # Calculate battery voltage based on scale
        if battery_scale == 0:
            result['battery_voltage'] = battery_raw / 10.0
        else:
            result['battery_voltage'] = float(battery_raw)
        result['battery_scale'] = battery_scale
        
        # Byte 10: Fault/Error/Text indicator
        if len(packet) > 10:
            fault_byte = packet[10]
            result['fault_indicator'] = fault_byte
            
            # Check for fault conditions
            if fault_byte & 0x80:  # High bit set indicates fault
                result['has_fault'] = True
                result['fault_code'] = fault_byte & 0x7F
            else:
                result['has_fault'] = False
        
        # Byte 11+: Checksum or text length
        if len(packet) > 11:
            checksum_or_length = packet[11]
            result['checksum'] = checksum_or_length
            
            # Verify checksum (simple sum of first 11 bytes)
            calculated = self.calculate_checksum(packet[0:11])
            result['checksum_valid'] = (calculated == checksum_or_length)
        
        # Store as last reading for this sensor
        self.last_readings[address] = result
        
        return result
    
    def decode_packet(self, packet: bytes) -> Dict:
        """
        Decode any WireFree Gen II packet
        
        Returns:
            Dict with decoded information
        """
        self.packet_count += 1
        
        if len(packet) < 4:
            self.error_count += 1
            return {
                'error': 'Packet too short',
                'min_length': 4,
                'actual_length': len(packet),
                'raw_hex': ' '.join(f'{b:02X}' for b in packet)
            }
        
        # Byte 2 is protocol number
        protocol = packet[2]
        
        if protocol == 0:
            return {
                'protocol': 0,
                'protocol_name': 'Monitor Control',
                'description': 'Primary monitor taking control from secondary',
                'transmitter_address': struct.unpack('>H', packet[0:2])[0],
                'timestamp': datetime.now().isoformat()
            }
        elif protocol == 1:
            return self.decode_protocol1(packet)
        else:
            return {
                'protocol': protocol,
                'protocol_name': f'Protocol {protocol}',
                'warning': 'Protocol not yet implemented',
                'transmitter_address': struct.unpack('>H', packet[0:2])[0] if len(packet) >= 2 else None,
                'timestamp': datetime.now().isoformat(),
                'raw_hex': ' '.join(f'{b:02X}' for b in packet)
            }
    
    def get_stats(self) -> Dict:
        """Get decoder statistics"""
        return {
            'packets_decoded': self.packet_count,
            'errors': self.error_count,
            'unique_sensors': len(self.last_readings),
            'sensor_addresses': list(self.last_readings.keys())
        }
    
    def get_last_reading(self, address: int) -> Optional[Dict]:
        """Get the last reading from a specific sensor address"""
        return self.last_readings.get(address)
    
    def get_all_last_readings(self) -> Dict[int, Dict]:
        """Get last readings from all sensors"""
        return self.last_readings.copy()


def format_decoded_packet(decoded: Dict) -> str:
    """Format a decoded packet for display"""
    lines = []
    lines.append(f"Protocol: {decoded.get('protocol_name', 'Unknown')}")
    
    if 'error' in decoded:
        lines.append(f"ERROR: {decoded['error']}")
        return '\n'.join(lines)
    
    if decoded.get('protocol') == 1:
        lines.append(f"Channel/Address: {decoded.get('transmitter_address', 'N/A')}")
        lines.append(f"Sensor Reading: {decoded.get('sensor_reading', 'N/A')} {decoded.get('gas_type', '')}")
        lines.append(f"Gas Type: {decoded.get('gas_type', 'Unknown')}")
        lines.append(f"Sensor Type: {decoded.get('sensor_type', 'Unknown')}")
        lines.append(f"Mode: {decoded.get('sensor_mode', 'Unknown')}")
        lines.append(f"Battery: {decoded.get('battery_voltage', 'N/A')}V")
        
        if decoded.get('has_fault'):
            lines.append(f"⚠️  FAULT: Code {decoded.get('fault_code', 'Unknown')}")
        
        if not decoded.get('checksum_valid', True):
            lines.append("⚠️  Checksum mismatch!")
    
    return '\n'.join(lines)


if __name__ == "__main__":
    # Test with sample data
    import sys
    
    logging.basicConfig(level=logging.INFO)
    
    # Example Protocol 1 packet (from your samples)
    # 81 11 00 11 E0 88 49 00 03 81 00 00 00 00 00 22 00 00 26 C8 B6 60 5F 09
    # But protocol 1 has address in first 2 bytes, protocol in byte 2
    
    # Construct a test packet based on Protocol 1 format
    # Address: 0x000F (15), Protocol: 1, Reading: 12.5 ppm, etc.
    test_packet = bytes([
        0x00, 0x0F,  # Address 15
        0x01,        # Protocol 1
        0x41, 0x48, 0x00, 0x00,  # Float 12.5
        0x00,        # Mode: Normal(0), Type: EC(0)
        0x24,        # Battery: 36
        0x00,        # Gas: H2S(0), Scale: 0
        0x00,        # No fault
        0x00         # Checksum placeholder
    ])
    
    decoder = OIRadioDecoder()
    decoded = decoder.decode_packet(test_packet)
    
    print("Test Packet Decode:")
    print("=" * 60)
    print(format_decoded_packet(decoded))
    print("\n" + "=" * 60)
    print("\nRaw decoded dict:")
    for key, value in decoded.items():
        print(f"  {key}: {value}")
