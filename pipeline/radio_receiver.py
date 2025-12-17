"""
Radio receiver for OI wireless sensors
Implements OI Gen II WireFree Protocol for direct radio module connection

Protocol Reference: WireFree Generation 2 Protocol specification
Based on: radio.c, laird.c, digi.c from OI-6950, and protocol documentation

Supported Radio Modules:
- Laird LT1110 (900 MHz) - Primary OI radio, model 1110LT200UPLG01
- Laird RM024 (2.4 GHz) - Alternative OI radio, model 2510LT100UPLG01
- XBee-PRO XSC - Legacy/compatible option

Supported Protocols:
- XBee/Laird API mode frames (0x7E start delimiter)
- Protocol 1: Full sensor data with battery, gas type, faults
- Protocol 2: Quick gas detection (sends every 5s when gas detected)
- Protocol 7: Maintenance timing (null/cal days)

Radio Configuration:
- Baud Rate: 9600 (OI default)
- Network Channel: 5 (default, configurable 0-15)
- System ID: 37 (fixed for OI networks)
- API Mode: Enabled for Laird modules (frame extraction)
- Transparent Mode: Direct Gen2 packets (bypass monitor)

Note: OI radios can be in API mode (Laird/XBee with 0x7E frames) or
transparent mode (raw Gen2 packets). This implementation handles both.
"""

import serial
import threading
import time
import struct
from typing import Callable, Dict, Optional, List
from dataclasses import dataclass


# Gas types from OI protocol spec
GAS_TYPE_NAMES = {
    0: "H2S", 1: "SO2", 2: "O2", 3: "CO", 4: "CL2",
    5: "CO2", 6: "LEL", 7: "VOC", 8: "Tank Level",
    9: "HCl", 10: "NH3"
}

# Sensor types from OI protocol spec
SENSOR_TYPE_NAMES = {
    0: "EC", 1: "IR", 2: "CB", 3: "MOS", 4: "PID",
    5: "Tank Level", 6: "4-20mA", 7: "Switch",
    30: "OI-WF190", 31: "None"
}

# Sensor modes from OI protocol spec
MODE_NAMES = {
    0: "Normal", 1: "Null", 2: "Calibration", 3: "Relay",
    4: "Radio Address", 5: "Diagnostic", 6: "Advanced Menu",
    7: "Administration Menu"
}

# Fault codes from OI protocol spec
FAULT_NAMES = {
    0: "None", 1: "Sensor Board Timeout", 2: "Bad Reading",
    3: "Current Draw Too High", 4: "ADC Not Responding",
    5: "Error During Null", 6: "Future Error", 7: "Checksum Error",
    8: "Duplicate Otis Address", 9: "Sensor Radio Timeout",
    10: "Wired Sensor Not Connected", 15: "Monitor Error"
}


@dataclass
class RadioMessage:
    """OI Gen II wireless sensor message"""
    protocol: int              # Protocol number (1, 2, or 7)
    transmitter_address: int   # 16-bit sensor address (1-255)
    channel: int               # Channel number (derived from address)
    reading: float             # Sensor reading (float32)
    
    # Protocol 1 fields
    sensor_mode: Optional[int] = None     # Mode (0-7)
    sensor_type: Optional[int] = None     # Type (0-31)
    battery_reading: Optional[int] = None # Raw battery value (0-255)
    battery_voltage: Optional[float] = None  # Calculated voltage
    gas_type: Optional[int] = None        # Gas type (0-10+)
    fault_code: Optional[int] = None      # Fault (0-15)
    precision: Optional[int] = None       # Decimal places (0-7)
    text: Optional[str] = None            # Optional text message
    
    # Protocol 7 fields
    days_since_null: Optional[int] = None  # Days since last null
    days_since_cal: Optional[int] = None   # Days since last calibration
    
    timestamp: float = None                # Receive timestamp
    rssi: Optional[int] = None             # Signal strength (if available)
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()
        # Derive channel from address (1:1 mapping for sensors)
        if self.channel is None:
            self.channel = self.transmitter_address


class RadioReceiver:
    """
    Receiver for OI Gen II wireless sensor radio module
    
    Connects directly to OI radio modules to receive wireless sensor data
    without going through monitor's modbus interface.
    
    Primary Radio Modules:
    - Laird LT1110: 900 MHz, 2-mile range, model 1110LT200UPLG01
    - Laird RM024: 2.4 GHz, 1-mile range, model 2510LT100UPLG01
    - XBee-PRO XSC: Legacy 900 MHz alternative
    
    Supported Protocols:
    - Protocol 1: Full sensor data (12+ bytes)
    - Protocol 2: Quick gas alert (8 bytes)  
    - Protocol 7: Maintenance timing (13 bytes)
    
    Radio Modes:
    - API mode: XBee/Laird frames with 0x7E start delimiter (recommended)
    - Transparent mode: Raw Gen2 packets (direct sensor to receiver)
    
    Laird Binary Commands:
    - 0xCC 0x22: Get RSSI (signal strength)
    - 0xCC 0x10: Get MAC address
    - 0xCC 0xC1 0x40 0x01 <ch>: Set RF channel
    """
    
    def __init__(self, port: str, baudrate: int = 9600, api_mode: bool = True):
        """
        Initialize radio receiver
        
        Args:
            port: Serial port for radio module (e.g., COM4, /dev/ttyUSB1)
            baudrate: Baud rate (default 9600 for OI radios)
            api_mode: True for XBee/Laird API mode (0x7E frames), False for transparent
        """
        self.port = port
        self.baudrate = baudrate
        self.api_mode = api_mode
        self.serial = None
        self.running = False
        self.thread = None
        self.callbacks: List[Callable[[RadioMessage], None]] = []
        self.buffer = bytearray()
        
    def get_rssi(self) -> Optional[int]:
        """Get RSSI from Laird radio using binary command.
        
        Returns:
            RSSI in dBm (e.g., -75), or None if not available
        """
        if not self.serial or not self.serial.is_open:
            return None
        
        try:
            # Send RSSI query: 0xCC 0x22
            self.serial.write(b'\xCC\x22')
            time.sleep(0.1)
            
            if self.serial.in_waiting >= 2:
                header = self.serial.read(1)[0]
                if header == 0xCC:
                    rssi_raw = self.serial.read(1)[0]
                    # Convert to dBm
                    if rssi_raw >= 128:
                        return int(((rssi_raw - 256) / 2) - 71)
                    else:
                        return int((rssi_raw / 2) - 71)
        except Exception as e:
            print(f"Error getting RSSI: {e}")
        
        return None
    
    def get_mac_address(self) -> Optional[str]:
        """Get MAC address from Laird radio using binary command.
        
        Returns:
            MAC address as hex string (e.g., 'A1B2C3'), or None if not available
        """
        if not self.serial or not self.serial.is_open:
            return None
        
        try:
            # Send MAC query: 0xCC 0x10
            self.serial.write(b'\xCC\x10')
            time.sleep(0.1)
            
            if self.serial.in_waiting >= 4:
                header = self.serial.read(1)[0]
                if header == 0xCC:
                    mac_bytes = self.serial.read(3)
                    return mac_bytes.hex().upper()
        except Exception as e:
            print(f"Error getting MAC: {e}")
        
        return None
    
    def set_rf_channel(self, channel: int) -> bool:
        """Set RF channel on Laird radio using binary command.
        
        Args:
            channel: RF channel (1-78 for LT/RM series)
            
        Returns:
            True if command sent successfully
        """
        if not self.serial or not self.serial.is_open:
            return False
        
        if channel < 1 or channel > 78:
            print(f"Invalid channel {channel}, must be 1-78")
            return False
        
        try:
            # Send channel set command: 0xCC 0xC1 0x40 0x01 <channel>
            cmd = bytes([0xCC, 0xC1, 0x40, 0x01, channel])
            self.serial.write(cmd)
            time.sleep(0.1)
            return True
        except Exception as e:
            print(f"Error setting RF channel: {e}")
            return False
    
    def send_test_packet(self, channel: int, reading: float, gas_type: int = 0, 
                        sensor_type: int = 0, battery_voltage: float = 3.3) -> bool:
        """Send a test OI Gen2 Protocol 1 packet (Primary mode only).
        
        Args:
            channel: Channel number (1-32)
            reading: Sensor reading value
            gas_type: Gas type code (0-27, default 0=H2S)
            sensor_type: Sensor type code (0-3, default 0=OI-6000)
            battery_voltage: Battery voltage (default 3.3V)
            
        Returns:
            True if packet sent successfully
        """
        if not self.serial or not self.serial.is_open:
            print("Radio not connected")
            return False
        
        try:
            # Build Protocol 1 packet (12 bytes minimum, no text)
            transmitter_address = channel  # Use channel as transmitter address
            
            # Byte 0-1: Transmitter address (big-endian)
            addr_high = (transmitter_address >> 8) & 0xFF
            addr_low = transmitter_address & 0xFF
            
            # Byte 2: Protocol = 1
            protocol = 1
            
            # Byte 3-6: Reading (IEEE 754 float, big-endian)
            reading_bytes = struct.pack('>f', reading)
            
            # Byte 7: Sensor mode (3 bits) + Sensor type (5 bits)
            sensor_mode = 0  # Normal mode
            byte7 = (sensor_mode & 0x07) | ((sensor_type & 0x1F) << 3)
            
            # Byte 8: Battery reading (scaled)
            if battery_voltage <= 2.55:
                battery_scale = 0
                battery_reading = int(battery_voltage * 10)
            else:
                battery_scale = 1
                battery_reading = int(battery_voltage)
            
            # Byte 9: Gas type (7 bits) + Battery scale (1 bit)
            byte9 = (gas_type & 0x7F) | ((battery_scale & 0x01) << 7)
            
            # Byte 10: Fault (4 bits) + Precision (3 bits) + Has text (1 bit)
            fault_code = 0  # No fault
            precision = 2   # 2 decimal places
            has_text = 0    # No text
            byte10 = ((fault_code & 0x0F) << 4) | ((precision & 0x07) << 1) | (has_text & 0x01)
            
            # Build packet
            packet = bytearray([
                addr_high, addr_low, protocol,
                reading_bytes[0], reading_bytes[1], reading_bytes[2], reading_bytes[3],
                byte7, battery_reading, byte9, byte10
            ])
            
            # Byte 11: Checksum (sum of all previous bytes & 0xFF)
            checksum = sum(packet) & 0xFF
            packet.append(checksum)
            
            # Send via radio (in API mode, wrap in 0x7E frame if needed)
            if self.api_mode:
                # For API mode, send as TX Request (0x10) frame
                # Frame: 0x7E <length MSB> <length LSB> 0x10 0x01 <dest_addr...> 0x00 <data...> <checksum>
                # Simplified: just send raw data, radio firmware will handle framing
                self.serial.write(packet)
            else:
                # Transparent mode - send raw packet
                self.serial.write(packet)
            
            return True
            
        except Exception as e:
            print(f"Error sending test packet: {e}")
            return False
        
    def connect(self) -> bool:
        """Connect to radio module"""
        try:
            self.serial = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=1
            )
            mode_str = "API" if self.api_mode else "Transparent"
            print(f"Connected to OI radio module on {self.port} ({mode_str} mode)")
            return True
        except Exception as e:
            print(f"Failed to connect to radio module: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from radio module"""
        self.stop()
        if self.serial and self.serial.is_open:
            self.serial.close()
    
    def register_callback(self, callback: Callable[[RadioMessage], None]):
        """Register callback for received messages"""
        self.callbacks.append(callback)
    
    def start(self):
        """Start receiving messages"""
        if not self.serial or not self.serial.is_open:
            raise RuntimeError("Radio module not connected")
        
        self.running = True
        self.thread = threading.Thread(target=self._receive_loop, daemon=True)
        self.thread.start()
        print("Radio receiver started")
    
    def stop(self):
        """Stop receiving messages"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=2)
        print("Radio receiver stopped")
    
    def _receive_loop(self):
        """Main receive loop"""
        while self.running:
            try:
                if self.serial.in_waiting > 0:
                    data = self.serial.read(self.serial.in_waiting)
                    self.buffer.extend(data)
                    self._process_buffer()
                else:
                    time.sleep(0.01)
            except Exception as e:
                print(f"Radio receive error: {e}")
                time.sleep(1)
    
    def _process_buffer(self):
        """Process received data buffer - supports both API mode and transparent mode.
        
        API Mode (XBee/Laird/Digi):
        - Frames start with 0x7E delimiter
        - Frame format: [0x7E][LenH][LenL][FrameType][Data...][Checksum]
        - Gen2 packet embedded within frame data
        
        Transparent Mode:
        - Raw Gen2 packets
        - Protocol 1 (12+ bytes), Protocol 2 (8 bytes), Protocol 7 (13 bytes)
        """
        if self.api_mode:
            self._process_api_frames()
        else:
            self._process_transparent()
    
    def _process_api_frames(self):
        """Process XBee API mode frames (0x7E start delimiter)"""
        while len(self.buffer) >= 4:
            # Look for 0x7E start delimiter
            if self.buffer[0] != 0x7E:
                self.buffer.pop(0)
                continue
            
            # Get frame length (bytes 1-2)
            frame_len = (self.buffer[1] << 8) | self.buffer[2]
            total_len = frame_len + 4  # +4 for delimiter, length, and checksum
            
            if len(self.buffer) < total_len:
                break  # Need more data
            
            # Validate frame checksum (last byte)
            frame_data = self.buffer[3:3+frame_len]
            api_checksum = 0xFF - (sum(frame_data) & 0xFF)
            if self.buffer[3+frame_len] != api_checksum:
                print(f"API frame checksum failed")
                self.buffer.pop(0)
                continue
            
            # Extract Gen2 packet from API payload
            # Frame data format: [FrameType][FrameID][...addressing...][RFData]
            # We scan for Gen2 protocol markers in the RF data section
            gen2_packet, pkt_len = self._extract_gen2_from_api(frame_data)
            
            if gen2_packet:
                # Parse the Gen2 packet
                self._parse_gen2_packet(gen2_packet)
            
            # Remove processed frame
            self.buffer = self.buffer[total_len:]
    
    def _extract_gen2_from_api(self, frame_data: bytearray) -> tuple:
        """Extract OI Gen2 packet from XBee API frame payload.
        
        Based on radio_extract_xbee_gen2() from laird.c in OI-6950 source.
        Scans API payload for valid Gen2 protocol packets.
        """
        # Scan through frame data looking for protocol markers
        for start in range(len(frame_data) - 4):
            if start + 2 >= len(frame_data):
                break
            
            protocol = frame_data[start + 2]
            
            if protocol == 1:  # Protocol 1: need 12 bytes minimum
                if start + 12 <= len(frame_data):
                    packet = frame_data[start:start+12]
                    # Check if there's text (bit 0 of byte 10)
                    has_text = (packet[10] & 0x01) == 1
                    if has_text and start + 12 < len(frame_data):
                        text_len = frame_data[start + 11]
                        if start + 12 + text_len + 1 <= len(frame_data):
                            packet = frame_data[start:start+12+text_len+1]
                    
                    # Validate Gen2 checksum
                    checksum_idx = len(packet) - 1
                    calc_sum = sum(packet[:checksum_idx]) & 0xFF
                    if packet[checksum_idx] == calc_sum or packet[checksum_idx] == (0xFF - calc_sum):
                        return (packet, len(packet))
            
            elif protocol == 2:  # Protocol 2: 8 bytes
                if start + 8 <= len(frame_data):
                    packet = frame_data[start:start+8]
                    calc_sum = sum(packet[:7]) & 0xFF
                    if packet[7] == calc_sum or packet[7] == (0xFF - calc_sum):
                        return (packet, 8)
            
            elif protocol == 7:  # Protocol 7: 13 bytes
                if start + 13 <= len(frame_data):
                    packet = frame_data[start:start+13]
                    calc_sum = sum(packet[:12]) & 0xFF
                    if packet[12] == calc_sum or packet[12] == (0xFF - calc_sum):
                        return (packet, 13)
        
        return (None, 0)
    
    def _process_transparent(self):
        """Process raw Gen2 packets (transparent mode)"""
        while len(self.buffer) >= 3:
            # Try to parse Gen2 packet starting at buffer[0]
            self._parse_gen2_packet(self.buffer)
    
    def _parse_gen2_packet(self, data: bytearray):
        """Parse OI Gen2 protocol packet (Protocol 1, 2, or 7)"""
        if len(data) < 3:
            return
        
        protocol = data[2]
        
        if protocol == 1:
            # Protocol 1: Full sensor data
            if len(data) < 11:
                return  # Need more data
            
            has_text = (data[10] & 0x01) == 1
            if has_text:
                if len(data) < 12:
                    return
                text_length = data[11]
                total_length = 12 + text_length + 1
            else:
                total_length = 12
            
            if len(data) < total_length:
                return
            
            # Validate checksum
            checksum_idx = total_length - 1
            calculated_checksum = sum(data[:checksum_idx]) & 0xFF
            if data[checksum_idx] != calculated_checksum:
                if len(self.buffer) > 0 and self.buffer[0] == data[0]:
                    self.buffer.pop(0)
                return
            
            # Parse valid packet
            msg = self._parse_protocol1(data[:total_length])
            if msg:
                for callback in self.callbacks:
                    callback(msg)
            
            # Remove processed packet (transparent mode only)
            if not self.api_mode and len(self.buffer) >= total_length:
                self.buffer = self.buffer[total_length:]
        
        elif protocol == 2:
            # Protocol 2: Quick gas detection
            if len(data) < 8:
                return
            
            calculated_checksum = sum(data[:7]) & 0xFF
            if data[7] != calculated_checksum:
                if len(self.buffer) > 0 and self.buffer[0] == data[0]:
                    self.buffer.pop(0)
                return
            
            msg = self._parse_protocol2(data[:8])
            if msg:
                for callback in self.callbacks:
                    callback(msg)
            
            if not self.api_mode and len(self.buffer) >= 8:
                self.buffer = self.buffer[8:]
        
        elif protocol == 7:
            # Protocol 7: Maintenance timing
            if len(data) < 13:
                return
            
            calculated_checksum = sum(data[:12]) & 0xFF
            if data[12] != calculated_checksum:
                if len(self.buffer) > 0 and self.buffer[0] == data[0]:
                    self.buffer.pop(0)
                return
            
            msg = self._parse_protocol7(data[:13])
            if msg:
                for callback in self.callbacks:
                    callback(msg)
            
            if not self.api_mode and len(self.buffer) >= 13:
                self.buffer = self.buffer[13:]
        else:
            # Unknown protocol
            if len(self.buffer) > 0:
                self.buffer.pop(0)
    
    def _parse_protocol1(self, data: bytearray) -> Optional[RadioMessage]:
        """Parse Protocol 1: Full sensor data"""
        try:
            transmitter_address = (data[0] << 8) | data[1]
            reading_bytes = bytes([data[3], data[4], data[5], data[6]])
            reading = struct.unpack('>f', reading_bytes)[0]
            
            sensor_mode = data[7] & 0x07
            sensor_type = (data[7] >> 3) & 0x1F
            battery_reading = data[8]
            gas_type = data[9] & 0x7F
            battery_scale = (data[9] >> 7) & 0x01
            
            if battery_scale == 0:
                battery_voltage = battery_reading / 10.0
            else:
                battery_voltage = float(battery_reading)
            
            fault_code = (data[10] >> 4) & 0x0F
            precision = (data[10] >> 1) & 0x07
            has_text = data[10] & 0x01
            
            text = None
            if has_text:
                text_length = data[11]
                if text_length > 0:
                    text_bytes = data[12:12+text_length]
                    try:
                        text = text_bytes.decode('ascii')
                    except:
                        text = str(text_bytes)
            
            return RadioMessage(
                protocol=1,
                transmitter_address=transmitter_address,
                channel=transmitter_address,
                reading=reading,
                sensor_mode=sensor_mode,
                sensor_type=sensor_type,
                battery_reading=battery_reading,
                battery_voltage=battery_voltage,
                gas_type=gas_type,
                fault_code=fault_code,
                precision=precision,
                text=text
            )
        except Exception as e:
            print(f"Error parsing Protocol 1: {e}")
            return None
    
    def _parse_protocol2(self, data: bytearray) -> Optional[RadioMessage]:
        """Parse Protocol 2: Quick gas detection"""
        try:
            transmitter_address = (data[0] << 8) | data[1]
            reading_bytes = bytes([data[3], data[4], data[5], data[6]])
            reading = struct.unpack('>f', reading_bytes)[0]
            
            return RadioMessage(
                protocol=2,
                transmitter_address=transmitter_address,
                channel=transmitter_address,
                reading=reading
            )
        except Exception as e:
            print(f"Error parsing Protocol 2: {e}")
            return None
    
    def _parse_protocol7(self, data: bytearray) -> Optional[RadioMessage]:
        """Parse Protocol 7: Maintenance timing"""
        try:
            transmitter_address = (data[0] << 8) | data[1]
            reading_bytes = bytes([data[3], data[4], data[5], data[6]])
            reading = struct.unpack('>f', reading_bytes)[0]
            
            days_since_null = (data[7] << 8) | data[8]
            days_since_cal = (data[9] << 8) | data[10]
            sensor_mode = data[11] & 0x07
            sensor_type = (data[11] >> 3) & 0x1F
            
            return RadioMessage(
                protocol=7,
                transmitter_address=transmitter_address,
                channel=transmitter_address,
                reading=reading,
                days_since_null=days_since_null,
                days_since_cal=days_since_cal,
                sensor_mode=sensor_mode,
                sensor_type=sensor_type
            )
        except Exception as e:
            print(f"Error parsing Protocol 7: {e}")
            return None


class HybridBridge:
    """
    Bridge supporting both Modbus and direct radio connections
    
    Can receive data from:
    - Modbus RTU/TCP from monitors
    - Direct wireless from radio module  
    - Combination of both (hybrid mode)
    
    Hybrid mode provides redundancy and extended range:
    - Radio for direct wireless sensor data
    - Modbus for monitor configuration and backup data path
    """
    
    def __init__(self):
        self.modbus_client = None
        self.radio_receiver = None
        self.radio_data = {}  # Cache radio messages by channel
        self.lock = threading.Lock()
    
    def set_modbus_client(self, client):
        """Set modbus client for monitor communication"""
        self.modbus_client = client
    
    def set_radio_receiver(self, receiver: RadioReceiver):
        """Set radio receiver for direct wireless"""
        self.radio_receiver = receiver
        receiver.register_callback(self._on_radio_message)
    
    def _on_radio_message(self, message: RadioMessage):
        """Handle received radio message"""
        with self.lock:
            self.radio_data[message.channel] = message
            
            # Format output based on protocol
            if message.protocol == 1:
                gas_name = GAS_TYPE_NAMES.get(message.gas_type, f"Gas {message.gas_type}")
                mode_name = MODE_NAMES.get(message.sensor_mode, f"Mode {message.sensor_mode}")
                fault_name = FAULT_NAMES.get(message.fault_code, f"Fault {message.fault_code}")
                
                print(f"Radio Ch{message.channel} (Addr {message.transmitter_address}): "
                      f"{message.reading:.{message.precision}f} {gas_name} | "
                      f"Battery: {message.battery_voltage:.1f}V | "
                      f"Mode: {mode_name} | Fault: {fault_name}")
                
                if message.text:
                    print(f"  Text: {message.text}")
                    
            elif message.protocol == 2:
                print(f"Radio Ch{message.channel} ALERT: {message.reading:.2f} (quick detect)")
                
            elif message.protocol == 7:
                print(f"Radio Ch{message.channel} Maintenance: {message.reading:.2f} | "
                      f"Null: {message.days_since_null} days | "
                      f"Cal: {message.days_since_cal} days")
    
    def get_channel_data(self, channel: int, device_id: int = None) -> Optional[Dict]:
        """
        Get channel data from either radio or modbus
        
        Priority: Radio data (if recent) > Modbus data
        
        Args:
            channel: Channel number
            device_id: Modbus device ID (if using modbus fallback)
            
        Returns:
            Channel data dict or None
        """
        # Check radio data first
        with self.lock:
            if channel in self.radio_data:
                msg = self.radio_data[channel]
                # Check if data is recent (< 90 seconds old)
                # Sensors transmit every 60s normally, 5s when gas detected
                if time.time() - msg.timestamp < 90:
                    data = {
                        'channel': msg.channel,
                        'reading': msg.reading,
                        'source': 'radio',
                        'timestamp': msg.timestamp,
                        'age': time.time() - msg.timestamp
                    }
                    
                    # Add protocol-specific fields
                    if msg.protocol == 1:
                        data.update({
                            'battery_voltage': msg.battery_voltage,
                            'sensor_type': msg.sensor_type,
                            'gas_type': msg.gas_type,
                            'fault_code': msg.fault_code,
                            'sensor_mode': msg.sensor_mode,
                            'precision': msg.precision,
                            'text': msg.text
                        })
                    elif msg.protocol == 7:
                        data.update({
                            'days_since_null': msg.days_since_null,
                            'days_since_cal': msg.days_since_cal,
                            'sensor_mode': msg.sensor_mode
                        })
                    
                    return data
        
        # Fall back to modbus if available and no recent radio data
        if self.modbus_client and device_id is not None:
            try:
                # TODO: Implement modbus fallback using existing ModbusClient
                # This would read the same data from the monitor's modbus interface
                pass
            except Exception as e:
                print(f"Error reading channel {channel} from modbus: {e}")
        
        return None
    
    def start(self):
        """Start both radio and modbus (if configured)"""
        if self.radio_receiver:
            self.radio_receiver.start()
        print("Hybrid bridge started")
    
    def stop(self):
        """Stop both radio and modbus"""
        if self.radio_receiver:
            self.radio_receiver.stop()
        print("Hybrid bridge stopped")


# Example usage for testing
if __name__ == "__main__":
    def on_message(msg: RadioMessage):
        """Example callback for received messages"""
        if msg.protocol == 1:
            print(f"\\n=== Protocol 1: Full Sensor Data ===")
            print(f"Address: {msg.transmitter_address} (Ch{msg.channel})")
            print(f"Reading: {msg.reading:.{msg.precision}f}")
            print(f"Gas: {GAS_TYPE_NAMES.get(msg.gas_type, 'Unknown')}")
            print(f"Sensor: {SENSOR_TYPE_NAMES.get(msg.sensor_type, 'Unknown')}")
            print(f"Mode: {MODE_NAMES.get(msg.sensor_mode, 'Unknown')}")
            print(f"Battery: {msg.battery_voltage:.1f}V")
            print(f"Fault: {FAULT_NAMES.get(msg.fault_code, 'Unknown')}")
            if msg.text:
                print(f"Text: {msg.text}")
        elif msg.protocol == 2:
            print(f"\\n=== Protocol 2: Gas Alert ===")
            print(f"Ch{msg.channel}: {msg.reading:.2f}")
        elif msg.protocol == 7:
            print(f"\\n=== Protocol 7: Maintenance ===")
            print(f"Ch{msg.channel}: {msg.reading:.2f}")
            print(f"Days since null: {msg.days_since_null}")
            print(f"Days since cal: {msg.days_since_cal}")
    
    # Example: Direct radio connection (Secondary mode on channel 25)
    print("OI Gen II Radio Receiver Test")
    print("=" * 50)
    print("Supported: Laird LT1110 (900MHz), RM024 (2.4GHz), XBee-PRO")
    print("Mode: Secondary receiver on Network Channel 25")
    print()
    
    # Adjust COM port and API mode as needed
    # api_mode=True for Laird LT1110/RM024 in API mode (0x7E frames) - RECOMMENDED
    # api_mode=False for transparent mode (raw Gen2 packets)
    receiver = RadioReceiver("COM5", baudrate=9600, api_mode=True)  # Or "/dev/ttyUSB1" on Linux
    
    if receiver.connect():
        # Configure as secondary on network channel 25
        receiver.set_rf_channel(25)
        print("Radio configured: Channel 25, Secondary (Sniff Permit)\n")
        
        receiver.register_callback(on_message)
        receiver.start()
        
        try:
            print("Listening for OI wireless sensors...")
            print("Press Ctrl+C to stop\\n")
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\\n\\nStopping...")
        finally:
            receiver.disconnect()
    else:
        print("Failed to connect to radio module")
