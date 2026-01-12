#!/usr/bin/env python3
"""
Live Radio Monitor with ML Analytics

Combines real-time radio packet decoding with machine learning analytics:
- Decodes OI WireFree Gen II packets from Laird radio
- Applies anomaly detection to sensor readings
- Tracks sensor health and battery levels
- Predicts maintenance needs
- Exports data for ML training

Usage:
    python radio_ml_monitor.py --port COM7
    python radio_ml_monitor.py --port COM7 --enable-ml --anomaly-sensitivity 2.5
"""

import argparse
import serial
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict
import json
import time

from pipeline.radio_decoder import OIRadioDecoder, format_decoded_packet
from pipeline.ml_analytics import MLAnalyticsPipeline

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class RadioMLMonitor:
    """Live radio monitor with ML analytics integration"""
    
    def __init__(self, port: str, baudrate: int = 9600, 
                 enable_ml: bool = True, ml_config: dict = None):
        self.port = port
        self.baudrate = baudrate
        self.enable_ml = enable_ml
        
        # Initialize radio decoder
        self.decoder = OIRadioDecoder()
        
        # Initialize ML pipeline if enabled
        self.ml_pipeline = None
        if enable_ml:
            self.ml_pipeline = MLAnalyticsPipeline(config=ml_config or {})
            logger.info("✓ ML analytics enabled")
        
        # Statistics
        self.stats = {
            'packets_received': 0,
            'valid_packets': 0,
            'anomalies_detected': 0,
            'faults_detected': 0,
            'low_battery_warnings': 0,
            'start_time': None
        }
        
        # Alert thresholds
        self.low_battery_threshold = 3.0  # Volts
        self.alert_history = []
        
    def find_packet_start(self, buffer: bytearray) -> int:
        """
        Find start of next packet in buffer
        
        OI WireFree packets typically start with valid address bytes
        followed by protocol number (0-7 typically)
        """
        for i in range(len(buffer) - 2):
            # Check if this looks like a packet start
            # Protocol number should be small (0-10 typically)
            if i + 2 < len(buffer) and buffer[i + 2] <= 10:
                # Check if address is reasonable (1-1000)
                address = (buffer[i] << 8) | buffer[i + 1]
                if 1 <= address <= 1000:
                    return i
        return -1
    
    def extract_packet(self, buffer: bytearray) -> tuple:
        """
        Extract next complete packet from buffer
        
        Returns:
            (packet_bytes, remaining_buffer) or (None, buffer)
        """
        if len(buffer) < 12:
            return None, buffer
        
        start = self.find_packet_start(buffer)
        if start == -1:
            # No valid packet start found, clear old data
            if len(buffer) > 100:
                buffer = buffer[-50:]  # Keep last 50 bytes
            return None, buffer
        
        # Remove data before packet start
        if start > 0:
            buffer = buffer[start:]
        
        # Protocol 1 packets are typically 12 bytes minimum
        # Some have text data after, making them longer
        # For now, assume 12-byte packets for Protocol 1
        packet_size = 12
        
        if len(buffer) >= packet_size:
            packet = bytes(buffer[:packet_size])
            remaining = buffer[packet_size:]
            return packet, remaining
        
        # Not enough data yet
        return None, buffer
    
    def process_decoded_packet(self, decoded: Dict):
        """Process a decoded packet through ML and alerting"""
        self.stats['valid_packets'] += 1
        
        # Check for faults
        if decoded.get('has_fault'):
            self.stats['faults_detected'] += 1
            self.send_alert(
                'FAULT',
                f"Sensor {decoded['transmitter_address']} reporting fault code {decoded['fault_code']}",
                decoded
            )
        
        # Check battery level
        battery = decoded.get('battery_voltage')
        if battery and battery < self.low_battery_threshold:
            self.stats['low_battery_warnings'] += 1
            self.send_alert(
                'LOW_BATTERY',
                f"Sensor {decoded['transmitter_address']} battery low: {battery}V",
                decoded
            )
        
        # Process through ML if enabled
        if self.ml_pipeline and decoded.get('sensor_reading') is not None:
            channel = decoded['transmitter_address']
            value = decoded['sensor_reading']
            
            ml_result = self.ml_pipeline.process_reading(channel, value)
            
            if ml_result['anomaly']['is_anomaly']:
                self.stats['anomalies_detected'] += 1
                self.send_alert(
                    'ANOMALY',
                    f"Anomaly detected on channel {channel}: {ml_result['anomaly']['reason']}",
                    {'decoded': decoded, 'ml_result': ml_result}
                )
    
    def send_alert(self, alert_type: str, message: str, data: dict):
        """Send alert (log, webhook, MQTT, etc.)"""
        alert = {
            'timestamp': datetime.now().isoformat(),
            'type': alert_type,
            'message': message,
            'data': data
        }
        
        # Log alert
        if alert_type == 'FAULT':
            logger.error(f"🚨 {message}")
        elif alert_type == 'LOW_BATTERY':
            logger.warning(f"🔋 {message}")
        elif alert_type == 'ANOMALY':
            logger.warning(f"⚠️  {message}")
        
        # Store alert history
        self.alert_history.append(alert)
        
        # TODO: Send to webhook, MQTT, etc.
    
    def print_status(self):
        """Print monitoring status"""
        runtime = time.time() - self.stats['start_time']
        
        print("\n" + "=" * 70)
        print("RADIO ML MONITOR STATUS")
        print("=" * 70)
        print(f"Runtime: {runtime:.0f}s")
        print(f"Packets received: {self.stats['packets_received']}")
        print(f"Valid packets: {self.stats['valid_packets']}")
        print(f"Anomalies detected: {self.stats['anomalies_detected']}")
        print(f"Faults detected: {self.stats['faults_detected']}")
        print(f"Low battery warnings: {self.stats['low_battery_warnings']}")
        
        # Show active sensors
        last_readings = self.decoder.get_all_last_readings()
        if last_readings:
            print(f"\nActive sensors: {len(last_readings)}")
            for addr, reading in sorted(last_readings.items()):
                value = reading.get('sensor_reading', 'N/A')
                gas = reading.get('gas_type', '?')
                battery = reading.get('battery_voltage', 'N/A')
                print(f"  Ch {addr:3d}: {value:8.2f} {gas:6s} | Battery: {battery}V")
        
        print("=" * 70 + "\n")
    
    def run(self):
        """Main monitoring loop"""
        logger.info(f"Opening {self.port} at {self.baudrate} baud...")
        logger.info("Press Ctrl+C to stop\n")
        
        try:
            ser = serial.Serial(self.port, self.baudrate, timeout=0.1)
            buffer = bytearray()
            self.stats['start_time'] = time.time()
            last_status = time.time()
            
            while True:
                # Read available data
                if ser.in_waiting:
                    data = ser.read(ser.in_waiting)
                    buffer.extend(data)
                    self.stats['packets_received'] += len(data)
                
                # Try to extract packet
                packet, buffer = self.extract_packet(buffer)
                
                if packet:
                    # Decode packet
                    decoded = self.decoder.decode_packet(packet)
                    
                    # Process packet
                    if 'error' not in decoded:
                        self.process_decoded_packet(decoded)
                        
                        # Print packet info
                        print(f"\n--- Packet #{self.stats['valid_packets']} ---")
                        print(format_decoded_packet(decoded))
                    else:
                        logger.debug(f"Decode error: {decoded['error']}")
                
                # Periodic status update
                if time.time() - last_status > 30:
                    self.print_status()
                    last_status = time.time()
                    
                    # Save ML batch if enabled
                    if self.ml_pipeline:
                        self.ml_pipeline.collector.save_batch()
                
                time.sleep(0.01)  # Small delay
                
        except KeyboardInterrupt:
            logger.info("\n\nStopped by user")
        except Exception as e:
            logger.exception(f"Monitor error: {e}")
        finally:
            if 'ser' in locals():
                ser.close()
            
            # Final status
            self.print_status()
            
            # Export alerts if any
            if self.alert_history:
                alert_file = Path('radio_alerts.json')
                with open(alert_file, 'w') as f:
                    json.dump(self.alert_history, f, indent=2)
                logger.info(f"Alerts exported to {alert_file}")
            
            # Decoder stats
            decoder_stats = self.decoder.get_stats()
            logger.info(f"Decoder stats: {decoder_stats}")


def main():
    parser = argparse.ArgumentParser(
        description='Live radio monitor with ML analytics'
    )
    parser.add_argument('--port', '-p', type=str, required=True,
                       help='Serial port (e.g., COM7)')
    parser.add_argument('--baudrate', '-b', type=int, default=9600,
                       help='Serial baudrate (default: 9600)')
    parser.add_argument('--enable-ml', action='store_true', default=True,
                       help='Enable ML analytics (default: True)')
    parser.add_argument('--disable-ml', action='store_true',
                       help='Disable ML analytics')
    parser.add_argument('--anomaly-sensitivity', type=float, default=3.0,
                       help='Anomaly detection sensitivity (default: 3.0)')
    parser.add_argument('--ml-storage', type=str, default='ml_data',
                       help='ML data storage path (default: ml_data)')
    parser.add_argument('--low-battery-threshold', type=float, default=3.0,
                       help='Low battery voltage threshold (default: 3.0V)')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Verbose logging')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # ML configuration
    enable_ml = args.enable_ml and not args.disable_ml
    ml_config = {
        'storage_path': args.ml_storage,
        'anomaly_sensitivity': args.anomaly_sensitivity,
        'anomaly_window': 100
    } if enable_ml else None
    
    # Create and run monitor
    monitor = RadioMLMonitor(
        port=args.port,
        baudrate=args.baudrate,
        enable_ml=enable_ml,
        ml_config=ml_config
    )
    monitor.low_battery_threshold = args.low_battery_threshold
    
    monitor.run()


if __name__ == "__main__":
    main()
