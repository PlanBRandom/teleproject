#!/usr/bin/env python3
"""
OI-7500 Protocol Monitor
Monitors radio (COM7) and Modbus (COM10) for 15 hours
Logs all data for protocol analysis
"""

import serial
import time
import datetime
import threading
import json
import struct
from pathlib import Path
from collections import defaultdict

# Configuration
RADIO_PORT = 'COM7'
RADIO_BAUDRATE = 115200
MODBUS_PORT = 'COM10'
MODBUS_BAUDRATE = 9600
MODBUS_SLAVE_ID = 3
MONITOR_DURATION_HOURS = 15
LOG_DIR = Path('protocol_logs')

# Statistics
stats = {
    'radio': {
        'total_bytes': 0,
        'total_packets': 0,
        'frame_types': defaultdict(int),
        'protocol_types': defaultdict(int),
        'start_time': None,
        'last_packet': None
    },
    'modbus': {
        'total_bytes': 0,
        'total_requests': 0,
        'total_responses': 0,
        'function_codes': defaultdict(int),
        'start_time': None,
        'last_packet': None
    }
}

class ProtocolMonitor:
    def __init__(self):
        self.running = False
        self.radio_thread = None
        self.modbus_thread = None
        self.radio_log = None
        self.modbus_log = None
        self.analysis_log = None
        
        # Create log directory
        LOG_DIR.mkdir(exist_ok=True)
        
        # Open log files
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        self.radio_log = open(LOG_DIR / f'radio_{timestamp}.log', 'w', encoding='utf-8')
        self.modbus_log = open(LOG_DIR / f'modbus_{timestamp}.log', 'w', encoding='utf-8')
        self.analysis_log = open(LOG_DIR / f'analysis_{timestamp}.log', 'w', encoding='utf-8')
        self.hex_dump_log = open(LOG_DIR / f'hexdump_{timestamp}.log', 'w', encoding='utf-8')
        
        print(f"Logs will be saved to: {LOG_DIR.absolute()}")
        
    def log_radio(self, msg):
        """Log radio data with timestamp"""
        timestamp = datetime.datetime.now().isoformat()
        self.radio_log.write(f"[{timestamp}] {msg}\n")
        self.radio_log.flush()
        
    def log_modbus(self, msg):
        """Log Modbus data with timestamp"""
        timestamp = datetime.datetime.now().isoformat()
        self.modbus_log.write(f"[{timestamp}] {msg}\n")
        self.modbus_log.flush()
        
    def log_analysis(self, msg):
        """Log analysis findings"""
        timestamp = datetime.datetime.now().isoformat()
        self.analysis_log.write(f"[{timestamp}] {msg}\n")
        self.analysis_log.flush()
        print(f"[ANALYSIS] {msg}")
        
    def log_hex_dump(self, source, data):
        """Log hex dump of raw data"""
        timestamp = datetime.datetime.now().isoformat()
        hex_str = data.hex()
        ascii_str = ''.join(chr(b) if 32 <= b < 127 else '.' for b in data)
        self.hex_dump_log.write(f"[{timestamp}] {source}: {hex_str}\n")
        self.hex_dump_log.write(f"  ASCII: {ascii_str}\n")
        self.hex_dump_log.flush()
    
    def analyze_radio_packet(self, data):
        """Analyze radio packet structure"""
        if len(data) < 3:
            return
        
        stats['radio']['total_packets'] += 1
        
        # Check for RM024 API framing (0x81)
        if data[0] == 0x81:
            stats['radio']['frame_types']['0x81_length_prefixed'] += 1
            if len(data) >= 3:
                payload_len = data[1]
                self.log_analysis(f"Radio: 0x81 frame, payload_len={payload_len}, total={len(data)} bytes")
                
                # Try to extract Gen2 packet
                if len(data) >= 3 + payload_len:
                    gen2_start = 3
                    gen2_data = data[gen2_start:gen2_start + payload_len]
                    if len(gen2_data) >= 3:
                        protocol = gen2_data[2]
                        stats['radio']['protocol_types'][f'protocol_{protocol}'] += 1
                        self.log_analysis(f"  Gen2 protocol byte: {protocol} (0x{protocol:02x})")
        
        # Check for 0xCC frame
        elif data[0] == 0xCC:
            stats['radio']['frame_types']['0xCC_rm024_api'] += 1
            self.log_analysis(f"Radio: 0xCC frame (RM024 API receive)")
        
        # Check for XBee API (0x7E)
        elif data[0] == 0x7E:
            stats['radio']['frame_types']['0x7E_xbee_api'] += 1
            self.log_analysis(f"Radio: 0x7E frame (XBee API)")
        
        # Raw Gen2 packet
        elif len(data) >= 3:
            protocol = data[2]
            if protocol in [1, 2, 7]:
                stats['radio']['frame_types']['raw_gen2'] += 1
                stats['radio']['protocol_types'][f'protocol_{protocol}'] += 1
                self.log_analysis(f"Radio: Raw Gen2, protocol={protocol}")
    
    def analyze_modbus_packet(self, data):
        """Analyze Modbus packet structure"""
        if len(data) < 4:
            return
        
        slave_id = data[0]
        function_code = data[1]
        
        stats['modbus']['function_codes'][f'fc_{function_code}'] += 1
        
        # Determine if request or response
        if function_code & 0x80:
            stats['modbus']['total_responses'] += 1
            error_code = data[2] if len(data) > 2 else 0
            self.log_analysis(f"Modbus: EXCEPTION - Slave={slave_id}, FC={function_code & 0x7F}, Error={error_code}")
        else:
            if slave_id == MODBUS_SLAVE_ID:
                stats['modbus']['total_requests'] += 1
            else:
                stats['modbus']['total_responses'] += 1
            
            # Parse common function codes
            if function_code == 3:  # Read Holding Registers
                if len(data) >= 6:
                    start_addr = (data[2] << 8) | data[3]
                    num_regs = (data[4] << 8) | data[5]
                    self.log_analysis(f"Modbus: FC03 Read Holdings - Addr={start_addr}, Count={num_regs}")
            elif function_code == 4:  # Read Input Registers
                if len(data) >= 6:
                    start_addr = (data[2] << 8) | data[3]
                    num_regs = (data[4] << 8) | data[5]
                    self.log_analysis(f"Modbus: FC04 Read Inputs - Addr={start_addr}, Count={num_regs}")
            elif function_code == 16:  # Write Multiple Registers
                if len(data) >= 7:
                    start_addr = (data[2] << 8) | data[3]
                    num_regs = (data[4] << 8) | data[5]
                    byte_count = data[6]
                    self.log_analysis(f"Modbus: FC16 Write Multiple - Addr={start_addr}, Count={num_regs}, Bytes={byte_count}")
    
    def monitor_radio(self):
        """Monitor radio port"""
        try:
            ser = serial.Serial(
                port=RADIO_PORT,
                baudrate=RADIO_BAUDRATE,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=1,
                rtscts=True  # Hardware flow control
            )
            
            self.log_radio(f"Connected to {RADIO_PORT} at {RADIO_BAUDRATE} baud (RTS/CTS enabled)")
            stats['radio']['start_time'] = datetime.datetime.now()
            
            buffer = bytearray()
            
            while self.running:
                if ser.in_waiting > 0:
                    data = ser.read(ser.in_waiting)
                    stats['radio']['total_bytes'] += len(data)
                    stats['radio']['last_packet'] = datetime.datetime.now()
                    
                    # Log raw data
                    self.log_radio(f"RX: {len(data)} bytes - {data.hex()}")
                    self.log_hex_dump('RADIO_RX', data)
                    
                    # Add to buffer for analysis
                    buffer.extend(data)
                    
                    # Try to analyze packets
                    if len(buffer) >= 24:  # Minimum RM024 frame size
                        self.analyze_radio_packet(buffer)
                        # Keep last 100 bytes in buffer
                        if len(buffer) > 100:
                            buffer = buffer[-100:]
                
                time.sleep(0.01)
            
            ser.close()
            self.log_radio("Radio monitor stopped")
            
        except Exception as e:
            self.log_radio(f"ERROR: {e}")
            import traceback
            self.log_radio(traceback.format_exc())
    
    def monitor_modbus(self):
        """Monitor Modbus port"""
        try:
            ser = serial.Serial(
                port=MODBUS_PORT,
                baudrate=MODBUS_BAUDRATE,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=1
            )
            
            self.log_modbus(f"Connected to {MODBUS_PORT} at {MODBUS_BAUDRATE} baud")
            stats['modbus']['start_time'] = datetime.datetime.now()
            
            buffer = bytearray()
            last_activity = time.time()
            
            while self.running:
                if ser.in_waiting > 0:
                    data = ser.read(ser.in_waiting)
                    stats['modbus']['total_bytes'] += len(data)
                    stats['modbus']['last_packet'] = datetime.datetime.now()
                    
                    # Log raw data
                    self.log_modbus(f"RX: {len(data)} bytes - {data.hex()}")
                    self.log_hex_dump('MODBUS_RX', data)
                    
                    # Add to buffer
                    buffer.extend(data)
                    last_activity = time.time()
                
                # If no activity for 100ms, consider buffer complete
                if len(buffer) > 0 and (time.time() - last_activity) > 0.1:
                    self.analyze_modbus_packet(buffer)
                    buffer.clear()
                
                time.sleep(0.01)
            
            ser.close()
            self.log_modbus("Modbus monitor stopped")
            
        except Exception as e:
            self.log_modbus(f"ERROR: {e}")
            import traceback
            self.log_modbus(traceback.format_exc())
    
    def print_stats(self):
        """Print statistics"""
        print("\n" + "="*60)
        print("PROTOCOL MONITORING STATISTICS")
        print("="*60)
        
        # Radio stats
        print(f"\nRADIO ({RADIO_PORT} @ {RADIO_BAUDRATE} baud):")
        print(f"  Total bytes: {stats['radio']['total_bytes']:,}")
        print(f"  Total packets: {stats['radio']['total_packets']:,}")
        print(f"  Runtime: {datetime.datetime.now() - stats['radio']['start_time']}")
        if stats['radio']['last_packet']:
            print(f"  Last packet: {stats['radio']['last_packet'].strftime('%H:%M:%S')}")
        
        print("  Frame types:")
        for frame_type, count in sorted(stats['radio']['frame_types'].items()):
            print(f"    {frame_type}: {count}")
        
        print("  Protocol types:")
        for proto, count in sorted(stats['radio']['protocol_types'].items()):
            print(f"    {proto}: {count}")
        
        # Modbus stats
        print(f"\nMODBUS ({MODBUS_PORT} @ {MODBUS_BAUDRATE} baud, Slave ID {MODBUS_SLAVE_ID}):")
        print(f"  Total bytes: {stats['modbus']['total_bytes']:,}")
        print(f"  Requests: {stats['modbus']['total_requests']:,}")
        print(f"  Responses: {stats['modbus']['total_responses']:,}")
        if stats['modbus']['start_time']:
            print(f"  Runtime: {datetime.datetime.now() - stats['modbus']['start_time']}")
        if stats['modbus']['last_packet']:
            print(f"  Last packet: {stats['modbus']['last_packet'].strftime('%H:%M:%S')}")
        
        print("  Function codes:")
        for fc, count in sorted(stats['modbus']['function_codes'].items()):
            print(f"    {fc}: {count}")
        
        print("="*60)
    
    def start(self):
        """Start monitoring"""
        self.running = True
        
        print(f"\nStarting protocol monitor for {MONITOR_DURATION_HOURS} hours...")
        print(f"Radio: {RADIO_PORT} @ {RADIO_BAUDRATE} baud (API mode, RTS/CTS)")
        print(f"Modbus: {MODBUS_PORT} @ {MODBUS_BAUDRATE} baud (Slave ID {MODBUS_SLAVE_ID})")
        print("Press Ctrl+C to stop early\n")
        
        # Start monitoring threads
        self.radio_thread = threading.Thread(target=self.monitor_radio, daemon=True)
        self.modbus_thread = threading.Thread(target=self.monitor_modbus, daemon=True)
        
        self.radio_thread.start()
        self.modbus_thread.start()
        
        start_time = time.time()
        end_time = start_time + (MONITOR_DURATION_HOURS * 3600)
        
        try:
            while time.time() < end_time and self.running:
                time.sleep(60)  # Print stats every minute
                self.print_stats()
                
                # Save stats to JSON
                stats_file = LOG_DIR / 'stats.json'
                with open(stats_file, 'w') as f:
                    json.dump({
                        'radio': {k: dict(v) if isinstance(v, defaultdict) else v 
                                 for k, v in stats['radio'].items() 
                                 if k not in ['start_time', 'last_packet']},
                        'modbus': {k: dict(v) if isinstance(v, defaultdict) else v 
                                  for k, v in stats['modbus'].items() 
                                  if k not in ['start_time', 'last_packet']}
                    }, f, indent=2)
        
        except KeyboardInterrupt:
            print("\n\nStopping early (Ctrl+C pressed)")
        
        self.stop()
    
    def stop(self):
        """Stop monitoring"""
        self.running = False
        
        # Wait for threads to finish
        if self.radio_thread:
            self.radio_thread.join(timeout=5)
        if self.modbus_thread:
            self.modbus_thread.join(timeout=5)
        
        # Close log files
        if self.radio_log:
            self.radio_log.close()
        if self.modbus_log:
            self.modbus_log.close()
        if self.analysis_log:
            self.analysis_log.close()
        if self.hex_dump_log:
            self.hex_dump_log.close()
        
        # Print final stats
        self.print_stats()
        
        print(f"\nLogs saved to: {LOG_DIR.absolute()}")
        print(f"  radio_*.log - Radio data")
        print(f"  modbus_*.log - Modbus data")
        print(f"  analysis_*.log - Protocol analysis")
        print(f"  hexdump_*.log - Raw hex dumps")
        print(f"  stats.json - Statistics")

if __name__ == '__main__':
    monitor = ProtocolMonitor()
    monitor.start()
