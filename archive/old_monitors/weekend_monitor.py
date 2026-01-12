"""
Weekend Monitoring - OI-7530 Network 25 (Repeated Packets)
Long-running monitor for COM11 with full logging
"""
import json
import logging
import signal
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

from pipeline.radio_receiver import RadioReceiver, RadioMessage
from pipeline.mqtt import MQTTPublisher, MQTTConfig

# Gas type names for display
GAS_TYPE_NAMES = {
    0: "None", 1: "SO2", 2: "NO2", 3: "CO", 4: "H2S", 5: "HCN", 6: "NH3", 7: "Cl2",
    8: "LEL", 9: "O2", 10: "PH3", 11: "ClO2", 12: "NO", 13: "HCl", 14: "O3", 15: "HF",
    16: "VOC", 17: "ETO", 18: "AsH3", 19: "CO2", 20: "COCl2", 21: "SiH4", 22: "GeH4",
    23: "B2H6", 24: "F2", 25: "BF3", 26: "N2H4", 27: "C2H4O", 28: "CH3OH", 29: "TDI",
    30: "HMDI", 31: "MDI", 32: "H2", 33: "C3H8", 34: "CH4", 35: "C4H10"
}


class WeekendMonitor:
    """Long-running radio monitor for weekend logging"""
    
    def __init__(self, config_file: str = "config.json"):
        self.config = self._load_config(config_file)
        self.running = False
        self.packet_count = 0
        self.start_time = None
        
        # Setup logging to both file and console
        self._setup_logging()
        
        # Get Network 25 (COM11) configuration - the only working network
        network_config = self.config['radios']['Network_25']
        self.port = network_config['port']
        self.baudrate = network_config['baudrate']
        
        logger.info("="*80)
        logger.info("Weekend Monitor - OI-7530 - Network 25 (Repeated Packets)")
        logger.info("="*80)
        logger.info(f"Radio: {self.port} @ {self.baudrate} baud")
        logger.info(f"Network: Network_25 (COM11 - Repeated packets from Networks 15 & 20)")
        logger.info(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("="*80)
        
        # Initialize radio receiver
        self.receiver = RadioReceiver(
            self.port,
            baudrate=self.baudrate,
            api_mode=True,
            api_type='rm024'
        )
        
        # Connect to radio
        if not self.receiver.connect():
            logger.error(f"[ERROR] Failed to connect to radio on {self.port}")
            raise RuntimeError(f"Could not connect to radio on {self.port}")
        
        logger.info(f"[OK] Radio connected on {self.port}")
        self.receiver.register_callback(self.on_radio_message)
        
        # Initialize MQTT publisher
        self.mqtt_client = None
        self.published_discovery = set()  # Track which channels have discovery published
        if 'mqtt' in self.config:
            try:
                mqtt_config = MQTTConfig(
                    broker=self.config['mqtt']['broker'],
                    port=self.config['mqtt']['port'],
                    username=self.config['mqtt'].get('username'),
                    password=self.config['mqtt'].get('password'),
                    use_tls=self.config['mqtt'].get('use_tls', False)
                )
                self.mqtt_client = MQTTPublisher(mqtt_config)
                self.mqtt_client.connect()
                logger.info("[OK] MQTT connected")
            except Exception as e:
                logger.warning(f"[WARN] MQTT connection failed: {e}")
                logger.info("[INFO] Continuing without MQTT - logging only")
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _load_config(self, config_file: str) -> Dict:
        """Load configuration from JSON file"""
        with open(config_file, 'r') as f:
            return json.load(f)
    
    def _setup_logging(self):
        """Setup logging to both file and console"""
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = log_dir / f"weekend_monitor_{timestamp}.log"
        
        # Create logger
        global logger
        logger = logging.getLogger("WeekendMonitor")
        logger.setLevel(logging.INFO)
        
        # Console handler - INFO and above
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter('%(message)s')
        console_handler.setFormatter(console_formatter)
        
        # File handler - DEBUG and above with timestamps
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(file_formatter)
        
        logger.addHandler(console_handler)
        logger.addHandler(file_handler)
        
        logger.info(f"Logging to: {log_file}")
    
    def _publish_homeassistant_discovery(self, channel: int, gas_name: str):
        """Publish Home Assistant MQTT discovery config for a channel"""
        if not self.mqtt_client or channel in self.published_discovery:
            return
        
        try:
            device_info = {
                "identifiers": [f"oi7530_ch{channel:02d}"],
                "name": f"OI-7530 Channel {channel:02d}",
                "manufacturer": "Otis Instruments",
                "model": "OI-7530 Gas Monitor"
            }
            
            # Sensor reading discovery
            reading_config = {
                "name": f"Channel {channel:02d} {gas_name}",
                "unique_id": f"oi7530_ch{channel:02d}_reading",
                "state_topic": f"oi7530/channel{channel:02d}",
                "value_template": "{{ value_json.reading }}",
                "unit_of_measurement": "ppm",
                "device_class": "gas" if gas_name not in ["None", "O2", "LEL"] else None,
                "state_class": "measurement",
                "device": device_info
            }
            
            # Battery discovery
            battery_config = {
                "name": f"Channel {channel:02d} Battery",
                "unique_id": f"oi7530_ch{channel:02d}_battery",
                "state_topic": f"oi7530/channel{channel:02d}",
                "value_template": "{{ value_json.battery }}",
                "unit_of_measurement": "V",
                "device_class": "voltage",
                "state_class": "measurement",
                "device": device_info
            }
            
            # RSSI discovery
            rssi_config = {
                "name": f"Channel {channel:02d} Signal",
                "unique_id": f"oi7530_ch{channel:02d}_rssi",
                "state_topic": f"oi7530/channel{channel:02d}",
                "value_template": "{{ value_json.rssi }}",
                "unit_of_measurement": "%",
                "device_class": "signal_strength",
                "state_class": "measurement",
                "device": device_info
            }
            
            # Fault discovery
            fault_config = {
                "name": f"Channel {channel:02d} Fault",
                "unique_id": f"oi7530_ch{channel:02d}_fault",
                "state_topic": f"oi7530/channel{channel:02d}",
                "value_template": "{{ value_json.fault }}",
                "device": device_info
            }
            
            # Publish discovery configs
            base_topic = f"homeassistant/sensor/oi7530_ch{channel:02d}"
            self.mqtt_client.mqtt_client.publish(f"{base_topic}_reading/config", json.dumps(reading_config), retain=True)
            self.mqtt_client.mqtt_client.publish(f"{base_topic}_battery/config", json.dumps(battery_config), retain=True)
            self.mqtt_client.mqtt_client.publish(f"{base_topic}_rssi/config", json.dumps(rssi_config), retain=True)
            self.mqtt_client.mqtt_client.publish(f"{base_topic}_fault/config", json.dumps(fault_config), retain=True)
            
            self.published_discovery.add(channel)
            logger.debug(f"Published Home Assistant discovery for Channel {channel:02d}")
            
        except Exception as e:
            logger.debug(f"Home Assistant discovery publish error: {e}")
    
    def on_radio_message(self, msg: RadioMessage):
        """Callback for received radio messages"""
        self.packet_count += 1
        
        # Get gas type name
        gas_name = GAS_TYPE_NAMES.get(msg.gas_type, f"Gas{msg.gas_type}")
        
        # Format fault status
        if msg.fault_code == 0:
            fault_str = "None"
        else:
            fault_names = {
                1: "Sensor Board Timeout",
                2: "Bad Reading",
                3: "Sensor Fault",
                4: "Duplicate Otis Address",
                5: "Low Battery",
                6: "Calibration Required"
            }
            fault_str = fault_names.get(msg.fault_code, f"Fault {msg.fault_code}")
        
        # Log packet details
        elapsed = time.time() - self.start_time if self.start_time else 0
        logger.info(f"[{elapsed:7.1f}s] Ch{msg.channel:02d} | {gas_name:8s} | "
                   f"{msg.reading:7.1f} | Battery: {msg.battery_voltage:.1f}V | "
                   f"RSSI: {msg.rssi}% | Fault: {fault_str}")
        
        # Publish to MQTT if connected
        if self.mqtt_client:
            try:
                # Publish Home Assistant discovery (once per channel)
                self._publish_homeassistant_discovery(msg.channel, gas_name)
                
                # Publish sensor data
                topic = f"oi7530/channel{msg.channel:02d}"
                payload = {
                    "channel": msg.channel,
                    "gas_type": gas_name,
                    "reading": round(msg.reading, 2),
                    "battery": round(msg.battery_voltage, 2),
                    "rssi": msg.rssi,
                    "fault": fault_str,
                    "fault_code": msg.fault_code,
                    "timestamp": datetime.now().isoformat()
                }
                self.mqtt_client.publish(topic, payload)
            except Exception as e:
                logger.debug(f"MQTT publish error: {e}")
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info("\n" + "="*80)
        logger.info("Shutdown signal received - stopping monitor...")
        logger.info("="*80)
        self.stop()
    
    def start(self):
        """Start monitoring"""
        self.running = True
        self.start_time = time.time()
        
        try:
            # Start radio receiver
            self.receiver.start()
            logger.info("[OK] Radio receiver started")
            logger.info("\nListening for sensor packets (Press Ctrl+C to stop)...")
            logger.info("-"*80)
            
            # Keep running until stopped
            while self.running:
                time.sleep(1)
                
                # Log status every 5 minutes
                if int(time.time() - self.start_time) % 300 == 0:
                    elapsed_hours = (time.time() - self.start_time) / 3600
                    rate = self.packet_count / elapsed_hours if elapsed_hours > 0 else 0
                    logger.info(f"\n[STATUS] Runtime: {elapsed_hours:.1f}h | "
                              f"Packets: {self.packet_count} | "
                              f"Rate: {rate:.1f}/hr\n")
        
        except Exception as e:
            logger.error(f"Error during monitoring: {e}", exc_info=True)
        
        finally:
            self.stop()
    
    def stop(self):
        """Stop monitoring"""
        if not self.running:
            return
        
        self.running = False
        
        # Stop radio receiver
        if self.receiver:
            self.receiver.stop()
            logger.info("[OK] Radio receiver stopped")
        
        # Disconnect MQTT
        if self.mqtt_client:
            try:
                self.mqtt_client.disconnect()
                logger.info("[OK] MQTT disconnected")
            except:
                pass
        
        # Final statistics
        if self.start_time:
            elapsed = time.time() - self.start_time
            elapsed_hours = elapsed / 3600
            rate = self.packet_count / elapsed_hours if elapsed_hours > 0 else 0
            
            logger.info("\n" + "="*80)
            logger.info("Weekend Monitor - Final Statistics")
            logger.info("="*80)
            logger.info(f"Total runtime: {elapsed_hours:.2f} hours ({elapsed/60:.1f} minutes)")
            logger.info(f"Total packets: {self.packet_count}")
            logger.info(f"Average rate: {rate:.1f} packets/hour")
            logger.info(f"End time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            logger.info("="*80)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Weekend radio monitoring for OI-7530")
    parser.add_argument('--config', default='config.json', help='Configuration file')
    args = parser.parse_args()
    
    monitor = WeekendMonitor(args.config)
    monitor.start()
