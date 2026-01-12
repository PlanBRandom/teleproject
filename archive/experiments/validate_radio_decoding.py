"""
Validation tool to compare Modbus register data with radio packet decoding.
This helps identify errors in radio packet interpretation by comparing against ground truth.
"""

import serial
import struct
import time
import sys
from datetime import datetime
from typing import Dict, Optional, Tuple
import threading
import queue

# Gas type mapping we're currently using (may be wrong)
GAS_TYPES = {
    0: "H2S",
    1: "SO2", 
    2: "O2",
    3: "CO",
    4: "Combustibles",
    5: "CO2",
    6: "NH3",
    7: "NO2",
    8: "Cl2",
    9: "HCN",
    10: "PH3",
    11: "NO",
    12: "HCl",
    13: "ClO2",
    14: "AsH3",
    15: "B2H6",
    16: "Br2",
    17: "C2H4O",
    18: "GeH4",
    19: "SiH4",
    20: "F2"
}

# Modbus register structure for a channel (6 registers starting at (channel-1)*6)
# Register 0-1: Reading value (32-bit float)
# Register 2: Gas type code
# Register 3: Status
# Register 4-5: Additional data

class ModbusReader:
    """Read ground truth data from Modbus devices"""
    
    def __init__(self, port: str = 'COM10', baudrate: int = 9600):
        self.port = port
        self.baudrate = baudrate
        self.ser = None
        
    def connect(self):
        """Connect to Modbus serial port"""
        self.ser = serial.Serial(
            port=self.port,
            baudrate=self.baudrate,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=1.0
        )
        print(f"✓ Connected to Modbus on {self.port} @ {self.baudrate} baud")
        
    def disconnect(self):
        """Disconnect from Modbus"""
        if self.ser and self.ser.is_open:
            self.ser.close()
            print(f"✓ Disconnected from Modbus")
    
    def calculate_crc(self, data: bytes) -> int:
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
    
    def read_channel_registers(self, slave_id: int, channel: int) -> Optional[Dict]:
        """Read all registers for a specific channel"""
        # Calculate starting register address
        base_address = (channel - 1) * 6
        
        # Build Modbus request: Function 0x03, read 6 registers
        request = struct.pack('>BBHHxx', slave_id, 0x03, base_address, 6)
        crc = self.calculate_crc(request[:-2])
        request = request[:-2] + struct.pack('<H', crc)
        
        # Send request
        self.ser.write(request)
        time.sleep(0.05)  # Wait for response
        
        # Read response
        response = self.ser.read(100)
        if len(response) < 5:
            return None
            
        # Validate response
        if response[0] != slave_id or response[1] != 0x03:
            return None
            
        byte_count = response[2]
        if byte_count != 12:  # 6 registers * 2 bytes
            return None
            
        # Extract register values
        registers = struct.unpack('>6H', response[3:15])
        
        # Parse channel data
        reading_raw = (registers[0] << 16) | registers[1]
        reading = struct.unpack('>f', struct.pack('>I', reading_raw))[0]
        gas_type_code = registers[2]
        status = registers[3]
        
        return {
            'slave_id': slave_id,
            'channel': channel,
            'reading': reading,
            'gas_type_code': gas_type_code,
            'gas_type': GAS_TYPES.get(gas_type_code, f"Unknown({gas_type_code})"),
            'status': status,
            'raw_registers': registers
        }


class RadioCapture:
    """Capture and decode radio packets from a specific network"""
    
    def __init__(self, port: str, baudrate: int = 115200):
        self.port = port
        self.baudrate = baudrate
        self.ser = None
        self.packet_queue = queue.Queue()
        self.running = False
        self.thread = None
        
    def connect(self):
        """Connect to radio serial port"""
        self.ser = serial.Serial(
            port=self.port,
            baudrate=self.baudrate,
            timeout=0.1
        )
        print(f"✓ Connected to radio on {self.port}")
        
    def disconnect(self):
        """Disconnect from radio"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=2.0)
        if self.ser and self.ser.is_open:
            self.ser.close()
        print(f"✓ Disconnected from radio")
    
    def start_capture(self):
        """Start capturing packets in background thread"""
        self.running = True
        self.thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.thread.start()
        print("✓ Started radio packet capture")
    
    def _capture_loop(self):
        """Background thread to capture packets"""
        buffer = bytearray()
        
        while self.running:
            try:
                data = self.ser.read(256)
                if data:
                    buffer.extend(data)
                    
                    # Look for RM024 frame start (0x7E)
                    while len(buffer) >= 4:
                        if buffer[0] == 0x7E:
                            # Get frame length
                            frame_length = (buffer[1] << 8) | buffer[2]
                            total_length = frame_length + 4  # +1 start, +2 length, +1 checksum
                            
                            if len(buffer) >= total_length:
                                frame = bytes(buffer[:total_length])
                                buffer = buffer[total_length:]
                                
                                # Decode frame
                                decoded = self._decode_frame(frame)
                                if decoded:
                                    self.packet_queue.put(decoded)
                            else:
                                break  # Wait for more data
                        else:
                            buffer = buffer[1:]  # Skip byte and look for next start
                            
            except Exception as e:
                print(f"Capture error: {e}")
                time.sleep(0.1)
    
    def _decode_frame(self, frame: bytes) -> Optional[Dict]:
        """Decode RM024 frame"""
        if len(frame) < 4:
            return None
            
        frame_length = (frame[1] << 8) | frame[2]
        if len(frame) != frame_length + 4:
            return None
            
        payload = frame[3:-1]  # Remove start, length, checksum
        
        if len(payload) < 2:
            return None
            
        frame_type = payload[0]
        
        # Only decode 0x81 frames (sensor data)
        if frame_type == 0x81 and len(payload) >= 16:
            channel = payload[8]
            
            # Extract reading value (bytes 10-13)
            reading_bytes = payload[10:14]
            reading = struct.unpack('>f', reading_bytes)[0]
            
            # Extract gas type code (byte 14 - this is what we're validating)
            gas_type_code = payload[14]
            gas_type = GAS_TYPES.get(gas_type_code, f"Unknown({gas_type_code})")
            
            # Status byte
            status = payload[15] if len(payload) > 15 else 0
            
            # Dump all payload bytes for analysis
            payload_hex = ' '.join(f'{b:02X}' for b in payload)
            
            return {
                'frame_type': frame_type,
                'channel': channel,
                'reading': reading,
                'gas_type_code': gas_type_code,
                'gas_type': gas_type,
                'status': status,
                'payload_hex': payload_hex,
                'full_frame': frame.hex()
            }
        
        return None
    
    def get_packet_for_channel(self, channel: int, timeout: float = 10.0) -> Optional[Dict]:
        """Wait for and return a packet for specific channel"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                packet = self.packet_queue.get(timeout=0.5)
                if packet['channel'] == channel:
                    return packet
            except queue.Empty:
                continue
                
        return None


def compare_channel(modbus: ModbusReader, radio: RadioCapture, slave_id: int, channel: int):
    """Compare Modbus ground truth with radio decoding for a channel"""
    
    print(f"\n{'='*80}")
    print(f"VALIDATING CHANNEL {channel} (Slave {slave_id})")
    print(f"{'='*80}\n")
    
    # Read Modbus ground truth
    print(f"Reading Modbus registers...")
    modbus_data = modbus.read_channel_registers(slave_id, channel)
    
    if not modbus_data:
        print(f"❌ Failed to read Modbus data for channel {channel}")
        return
    
    print(f"✓ Modbus Ground Truth:")
    print(f"  Channel: {modbus_data['channel']}")
    print(f"  Reading: {modbus_data['reading']:.2f}")
    print(f"  Gas Type Code: 0x{modbus_data['gas_type_code']:02X} ({modbus_data['gas_type_code']})")
    print(f"  Gas Type: {modbus_data['gas_type']}")
    print(f"  Status: 0x{modbus_data['status']:04X}")
    print(f"  Raw Registers: {[f'0x{r:04X}' for r in modbus_data['raw_registers']]}")
    
    # Wait for radio packet
    print(f"\nWaiting for radio packet (up to 10 seconds)...")
    radio_data = radio.get_packet_for_channel(channel, timeout=10.0)
    
    if not radio_data:
        print(f"❌ No radio packet received for channel {channel}")
        return
    
    print(f"✓ Radio Packet Received:")
    print(f"  Channel: {radio_data['channel']}")
    print(f"  Reading: {radio_data['reading']:.2f}")
    print(f"  Gas Type Code: 0x{radio_data['gas_type_code']:02X} ({radio_data['gas_type_code']})")
    print(f"  Gas Type: {radio_data['gas_type']}")
    print(f"  Status: 0x{radio_data['status']:02X}")
    print(f"\n  Full Payload (hex): {radio_data['payload_hex']}")
    
    # Compare results
    print(f"\n{'='*80}")
    print(f"COMPARISON RESULTS")
    print(f"{'='*80}\n")
    
    channel_match = modbus_data['channel'] == radio_data['channel']
    reading_match = abs(modbus_data['reading'] - radio_data['reading']) < 0.1
    gas_type_match = modbus_data['gas_type_code'] == radio_data['gas_type_code']
    
    print(f"  Channel Match: {'✓ YES' if channel_match else '❌ NO'}")
    print(f"    Modbus: {modbus_data['channel']}")
    print(f"    Radio:  {radio_data['channel']}")
    
    print(f"\n  Reading Match: {'✓ YES' if reading_match else '❌ NO'}")
    print(f"    Modbus: {modbus_data['reading']:.2f}")
    print(f"    Radio:  {radio_data['reading']:.2f}")
    
    print(f"\n  Gas Type Match: {'✓ YES' if gas_type_match else '❌ NO'}")
    print(f"    Modbus: 0x{modbus_data['gas_type_code']:02X} = {modbus_data['gas_type']}")
    print(f"    Radio:  0x{radio_data['gas_type_code']:02X} = {radio_data['gas_type']}")
    
    if not gas_type_match:
        print(f"\n  ⚠️  GAS TYPE MISMATCH DETECTED!")
        print(f"  This means byte 14 in the radio packet is NOT the gas type,")
        print(f"  or the encoding is different than our GAS_TYPES mapping.")
        print(f"\n  Analyzing payload to find correct gas type location...")
        
        # Search for the correct gas type code in the payload
        payload_bytes = bytes.fromhex(radio_data['payload_hex'].replace(' ', ''))
        target_code = modbus_data['gas_type_code']
        
        print(f"\n  Looking for 0x{target_code:02X} ({modbus_data['gas_type']}) in payload:")
        for i, byte in enumerate(payload_bytes):
            marker = " ← FOUND!" if byte == target_code else ""
            print(f"    Byte {i:2d}: 0x{byte:02X}{marker}")


def main():
    """Main validation program"""
    if len(sys.argv) < 4:
        print("Usage: python validate_radio_decoding.py <radio_port> <slave_id> <channel>")
        print("\nExample:")
        print("  python validate_radio_decoding.py COM11 32 16")
        print("\nThis will validate Channel 16 from slave 32 on radio network COM11")
        sys.exit(1)
    
    radio_port = sys.argv[1]
    slave_id = int(sys.argv[2])
    channel = int(sys.argv[3])
    
    print(f"\n{'='*80}")
    print(f"RADIO DECODING VALIDATION TOOL")
    print(f"{'='*80}")
    print(f"\nConfiguration:")
    print(f"  Radio Port: {radio_port}")
    print(f"  Modbus Port: COM10 @ 9600 baud")
    print(f"  Slave ID: {slave_id}")
    print(f"  Channel: {channel}")
    print(f"\n{'='*80}\n")
    
    modbus = ModbusReader(port='COM10', baudrate=9600)
    radio = RadioCapture(port=radio_port, baudrate=115200)
    
    try:
        # Connect to both interfaces
        modbus.connect()
        radio.connect()
        radio.start_capture()
        
        time.sleep(1)  # Let radio capture start
        
        # Compare the channel
        compare_channel(modbus, radio, slave_id, channel)
        
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("\n\nCleaning up...")
        radio.disconnect()
        modbus.disconnect()
        print("✓ Done")


if __name__ == '__main__':
    main()
