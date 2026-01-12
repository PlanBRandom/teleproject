#!/usr/bin/env python3
"""
OI-7500 Network Monitor with Home Assistant Integration
Monitors radio packets from all networks and publishes to MQTT/Home Assistant
"""

import argparse
import json
import logging
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Set
import paho.mqtt.client as mqtt

# Add pipeline to path
sys.path.insert(0, str(Path(__file__).parent))
from pipeline.radio_receiver import RadioReceiver, RadioMessage

# Gas type mapping
GAS_TYPES = {
    0: ("H2S", "Hydrogen Sulfide"),
    1: ("SO2", "Sulfur Dioxide"),
    2: ("O2", "Oxygen"),
    3: ("CO", "Carbon Monoxide"),
    4: ("CL2", "Chlorine"),
    5: ("CO2", "Carbon Dioxide"),
    6: ("LEL", "Lower Explosive Limit"),
    7: ("VOC", "Volatile Organic Compounds"),
    8: ("FEET", "Tank Level"),
    9: ("HCl", "Hydrogen Chloride"),
    10: ("NH3", "Ammonia"),
}

class NetworkMonitor:
    def __init__(self, mqtt_host="localhost", mqtt_port=1883, 
                 mqtt_user=None, mqtt_pass=None):
        self.mqtt_host = mqtt_host
        self.mqtt_port = mqtt_port
        self.mqtt_user = mqtt_user
        self.mqtt_pass = mqtt_pass
        self.mqtt_client = None
        self.mqtt_connected = False
        
        # Track discovered sensors
        self.discovered_sensors: Set[int] = set()
        
        # Radio receivers
        self.radios = {}
        self.packet_counts = {}
        
        # Setup logging
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = log_dir / f"network_monitor_{timestamp}.log"
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s [%(levelname)s] %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"Logging to: {log_file}")
        
    def connect_mqtt(self):
        """Connect to MQTT broker"""
        self.logger.info(f"Connecting to MQTT: {self.mqtt_host}:{self.mqtt_port}")
        
        try:
            # Try new API (paho-mqtt 2.0+)
            from paho.mqtt.client import CallbackAPIVersion
            self.mqtt_client = mqtt.Client(
                CallbackAPIVersion.VERSION2,
                "oi7500_network_monitor"
            )
        except (ImportError, AttributeError):
            # Fall back to old API
            self.mqtt_client = mqtt.Client("oi7500_network_monitor")
        
        if self.mqtt_user and self.mqtt_pass:
            self.mqtt_client.username_pw_set(self.mqtt_user, self.mqtt_pass)
        
        self.mqtt_client.on_connect = self._on_mqtt_connect
        self.mqtt_client.on_disconnect = self._on_mqtt_disconnect
        
        try:
            self.mqtt_client.connect(self.mqtt_host, self.mqtt_port, 60)
            self.mqtt_client.loop_start()
            time.sleep(2)
            return True
        except Exception as e:
            self.logger.error(f"Failed to connect to MQTT: {e}")
            return False
    
    def _on_mqtt_connect(self, client, userdata, flags, reason_code, properties=None):
        rc = reason_code if hasattr(reason_code, 'value') else reason_code
        if rc == 0:
            self.logger.info("Connected to MQTT broker")
            self.mqtt_connected = True
        else:
            self.logger.error(f"MQTT connection failed with code {rc}")
            self.mqtt_connected = False
    
    def _on_mqtt_disconnect(self, client, userdata, disconnect_flags, reason_code, properties=None):
        self.logger.warning(f"Disconnected from MQTT broker (code: {reason_code})")
        self.mqtt_connected = False
    
    def publish_ha_discovery(self, channel: int, gas_type: str, gas_name: str):
        """Publish Home Assistant MQTT discovery config"""
        if not self.mqtt_connected:
            return
        
        device_id = "oi7500_01"
        availability_topic = f"homeassistant/sensor/{device_id}/availability"
        
        # Device info (shared across all sensors)
        device_info = {
            "identifiers": [device_id],
            "name": "OI-7500 Radio Monitor",
            "model": "OI-7530/7010",
            "manufacturer": "Otis Instruments"
        }
        
        # Reading sensor
        reading_config = {
            "name": f"Channel {channel} Reading",
            "unique_id": f"{device_id}_channel_{channel}_reading",
            "state_topic": f"homeassistant/sensor/{device_id}/channel_{channel}_reading/state",
            "value_template": "{{ value_json.value }}",
            "device": device_info,
            "availability_topic": availability_topic,
            "unit_of_measurement": "FLOAT",
            "suggested_display_precision": 2
        }
        
        self.mqtt_client.publish(
            f"homeassistant/sensor/{device_id}/channel_{channel}_reading/config",
            json.dumps(reading_config),
            retain=True
        )
        
        # Battery sensor
        battery_config = {
            "name": f"Channel {channel} Battery",
            "unique_id": f"{device_id}_channel_{channel}_battery",
            "state_topic": f"homeassistant/sensor/{device_id}/channel_{channel}_battery/state",
            "value_template": "{{ value_json.value }}",
            "device": device_info,
            "availability_topic": availability_topic,
            "unit_of_measurement": "V",
            "device_class": "voltage",
            "state_class": "measurement",
            "entity_category": "diagnostic"
        }
        
        self.mqtt_client.publish(
            f"homeassistant/sensor/{device_id}/channel_{channel}_battery/config",
            json.dumps(battery_config),
            retain=True
        )
        
        # RSSI sensor
        rssi_config = {
            "name": f"Channel {channel} Signal",
            "unique_id": f"{device_id}_channel_{channel}_rssi",
            "state_topic": f"homeassistant/sensor/{device_id}/channel_{channel}_rssi/state",
            "value_template": "{{ value_json.value }}",
            "device": device_info,
            "availability_topic": availability_topic,
            "unit_of_measurement": "%",
            "icon": "mdi:signal",
            "entity_category": "diagnostic"
        }
        
        self.mqtt_client.publish(
            f"homeassistant/sensor/{device_id}/channel_{channel}_rssi/config",
            json.dumps(rssi_config),
            retain=True
        )
        
        # Fault sensor
        fault_config = {
            "name": f"Channel {channel} Fault",
            "unique_id": f"{device_id}_channel_{channel}_fault",
            "state_topic": f"homeassistant/sensor/{device_id}/channel_{channel}_fault/state",
            "value_template": "{{ value_json.value }}",
            "device": device_info,
            "availability_topic": availability_topic,
            "unit_of_measurement": "ENUMERATION",
            "entity_category": "diagnostic"
        }
        
        self.mqtt_client.publish(
            f"homeassistant/sensor/{device_id}/channel_{channel}_fault/config",
            json.dumps(fault_config),
            retain=True
        )
        
        self.logger.info(f"Published HA discovery for Ch{channel} {gas_type}")
    
    def publish_sensor_data(self, msg: RadioMessage):
        """Publish sensor data to MQTT"""
        if not self.mqtt_connected:
            return
        
        channel = msg.channel
        device_id = "oi7500_01"
        
        # Auto-discover new sensors
        if channel not in self.discovered_sensors:
            gas_type, gas_name = GAS_TYPES.get(msg.gas_type, ("Unknown", "Unknown Gas"))
            self.publish_ha_discovery(channel, gas_type, gas_name)
            self.discovered_sensors.add(channel)
        
        # Calculate RSSI percentage
        rssi_raw = msg.rssi if msg.rssi else 0
        if rssi_raw > 0:
            rssi_dbm = -(rssi_raw + 45)
            rssi_percent = max(0, min(100, int((40 - (rssi_dbm + 45)) * 2.5)))
        else:
            rssi_percent = 0
        
        # Publish reading
        self.mqtt_client.publish(
            f"homeassistant/sensor/{device_id}/channel_{channel}_reading/state",
            json.dumps({"value": round(msg.reading, 2)}),
            retain=True
        )
        
        # Publish battery
        battery = msg.battery_voltage if msg.battery_voltage else 0
        self.mqtt_client.publish(
            f"homeassistant/sensor/{device_id}/channel_{channel}_battery/state",
            json.dumps({"value": round(battery, 1)}),
            retain=True
        )
        
        # Publish RSSI
        self.mqtt_client.publish(
            f"homeassistant/sensor/{device_id}/channel_{channel}_rssi/state",
            json.dumps({"value": rssi_percent}),
            retain=True
        )
        
        # Publish fault
        fault_code = msg.fault_code if msg.fault_code else 0
        self.mqtt_client.publish(
            f"homeassistant/sensor/{device_id}/channel_{channel}_fault/state",
            json.dumps({"value": fault_code}),
            retain=True
        )
        
        # Update availability (online)
        self.mqtt_client.publish(
            f"homeassistant/sensor/{device_id}/availability",
            "online",
            retain=True
        )
    
    def add_radio(self, port: str, network_id: int, name: str):
        """Add a radio receiver to monitor"""
        try:
            self.logger.info(f"Connecting to {name} on {port}...")
            radio = RadioReceiver(port=port, baudrate=115200, api_type='rm024')
            
            # Connect to serial port
            if not radio.connect():
                self.logger.error(f"Failed to open serial port {port}")
                return False
            
            radio.register_callback(lambda msg: self._handle_packet(msg, network_id, name))
            radio.start()
            self.radios[name] = radio
            self.packet_counts[name] = 0
            self.logger.info(f"Connected to {name}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to connect to {name}: {e}")
            return False
    
    def _handle_packet(self, msg: RadioMessage, network_id: int, name: str):
        """Handle received packet"""
        self.packet_counts[name] += 1
        
        # Add network info to message
        msg.network_id = network_id
        
        gas_type, gas_name = GAS_TYPES.get(msg.gas_type, ("Unknown", "Unknown"))
        
        battery = msg.battery_voltage if msg.battery_voltage else 0
        rssi_raw = msg.rssi if msg.rssi else 0
        
        # Convert RSSI from raw byte to percentage (same as radio_receiver.py)
        # RSSI byte format: -dBm (e.g., 0x1A = 26 = -69 dBm)
        if rssi_raw > 0:
            rssi_dbm = -(rssi_raw + 45)  # Convert to actual dBm
            # Map to percentage: -45dBm=100%, -85dBm=0%
            rssi_percent = max(0, min(100, int((40 - (rssi_dbm + 45)) * 2.5)))
        else:
            rssi_percent = 0
        
        self.logger.info(
            f"[{name:6s}] Ch{msg.channel:03d} | {gas_type:8s} | "
            f"{msg.reading:6.1f} ppm | Bat: {battery:4.1f}V | "
            f"RSSI: {rssi_percent:2d}%"
        )
        
        # Publish to MQTT
        self.publish_sensor_data(msg)
    
    def print_status(self):
        """Print status summary"""
        self.logger.info("=" * 80)
        self.logger.info("STATUS:")
        for name, count in self.packet_counts.items():
            self.logger.info(f"  {name}: {count} packets")
        self.logger.info(f"  Discovered sensors: {len(self.discovered_sensors)}")
        self.logger.info(f"  MQTT: {'Connected' if self.mqtt_connected else 'Disconnected'}")
        self.logger.info("=" * 80)
    
    def run(self):
        """Main monitoring loop"""
        self.logger.info("=" * 80)
        self.logger.info("OI-7500 Network Monitor - Running")
        self.logger.info("Press Ctrl+C to stop")
        self.logger.info("=" * 80)
        
        last_status = time.time()
        
        try:
            while True:
                time.sleep(1)
                
                # Print status every 60 seconds
                if time.time() - last_status >= 60:
                    self.print_status()
                    last_status = time.time()
                    
        except KeyboardInterrupt:
            self.logger.info("\nStopping...")
        finally:
            self.stop()
    
    def stop(self):
        """Stop all radios and disconnect MQTT"""
        self.logger.info("Shutting down...")
        
        for name, radio in self.radios.items():
            try:
                radio.stop()
                self.logger.info(f"Stopped {name}")
            except Exception as e:
                self.logger.error(f"Error stopping {name}: {e}")
        
        if self.mqtt_client:
            self.mqtt_client.loop_stop()
            self.mqtt_client.disconnect()
            self.logger.info("Disconnected from MQTT")
        
        self.print_status()
        self.logger.info("Shutdown complete")


def main():
    parser = argparse.ArgumentParser(
        description='OI-7500 Network Monitor with Home Assistant Integration'
    )
    parser.add_argument('--mqtt-host', default='localhost',
                        help='MQTT broker hostname (default: localhost)')
    parser.add_argument('--mqtt-port', type=int, default=1883,
                        help='MQTT broker port (default: 1883)')
    parser.add_argument('--mqtt-user', help='MQTT username')
    parser.add_argument('--mqtt-pass', help='MQTT password')
    parser.add_argument('--com7', action='store_true',
                        help='Monitor COM7 (Network 15)')
    parser.add_argument('--com11', action='store_true',
                        help='Monitor COM11 (Network 25)')
    parser.add_argument('--com12', action='store_true',
                        help='Monitor COM12 (Network 20)')
    
    args = parser.parse_args()
    
    # Create monitor
    monitor = NetworkMonitor(
        mqtt_host=args.mqtt_host,
        mqtt_port=args.mqtt_port,
        mqtt_user=args.mqtt_user,
        mqtt_pass=args.mqtt_pass
    )
    
    # Connect to MQTT
    if not monitor.connect_mqtt():
        print("Failed to connect to MQTT - continuing without MQTT")
    
    # Add radios based on arguments
    radios_added = False
    if args.com7:
        if monitor.add_radio('COM7', 15, 'Net15'):
            radios_added = True
    
    if args.com11:
        if monitor.add_radio('COM11', 25, 'Net25'):
            radios_added = True
    
    if args.com12:
        if monitor.add_radio('COM12', 20, 'Net20'):
            radios_added = True
    
    # Default to COM7 if nothing specified
    if not radios_added:
        print("No COM ports specified, defaulting to COM7...")
        if not monitor.add_radio('COM7', 15, 'Net15'):
            print("Failed to connect to any radios - exiting")
            return 1
    
    # Run monitoring loop
    monitor.run()
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
