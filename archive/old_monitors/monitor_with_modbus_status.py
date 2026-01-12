"""
Combined Radio + Modbus Status Monitor
Monitors radio packets on COM11 while tracking primary/secondary status on multiple 7010 monitors
"""
import json
import logging
import signal
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional
from pymodbus.client import ModbusSerialClient
from threading import Thread, Event

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


class CombinedMonitor:
    """Monitor radio packets and Modbus status simultaneously"""
    
    def __init__(self, config_file: str = "config.json", duration_minutes: float = 30):
        self.config = self._load_config(config_file)
        self.running = False
        self.packet_count = 0
        self.start_time = None
        self.duration_seconds = duration_minutes * 60
        self.stop_event = Event()
        
        # Setup logging to both file and console
        self._setup_logging()
        
        # Get Network 25 (COM11) configuration
        network_config = self.config['radios']['Network_25']
        self.port = network_config['port']
        self.baudrate = network_config['baudrate']
        
        logger.info("="*80)
        logger.info(f"Combined Monitor - Radio + Modbus Status - {duration_minutes} minute test")
        logger.info("="*80)
        logger.info(f"Radio: {self.port} @ {self.baudrate} baud")
        logger.info(f"Network: Network_25 (COM11 - Repeated packets)")
        logger.info(f"Modbus: {self.config['modbus']['port']} @ {self.config['modbus']['baudrate']} baud")
        logger.info(f"Duration: {duration_minutes} minutes")
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
        
        # Initialize Modbus client for status monitoring
        self.modbus_client = None
        self.modbus_status = {}  # Track status for each slave
        try:
            self.modbus_client = ModbusSerialClient(
                port=self.config['modbus']['port'],
                baudrate=self.config['modbus']['baudrate'],
                bytesize=8,
                parity='N',
                stopbits=1,
                timeout=1
            )
            if self.modbus_client.connect():
                logger.info(f"[OK] Modbus connected on {self.config['modbus']['port']}")
            else:
                logger.warning("[WARN] Modbus connection failed - status monitoring disabled")
                self.modbus_client = None
        except Exception as e:
            logger.warning(f"[WARN] Modbus setup failed: {e}")
            self.modbus_client = None
        
        # Initialize MQTT publisher
        self.mqtt_client = None
        self.published_discovery = set()
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
        
        # Setup signal handlers
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
        log_file = log_dir / f"combined_monitor_{timestamp}.log"
        
        global logger
        logger = logging.getLogger("CombinedMonitor")
        logger.setLevel(logging.INFO)
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter('%(message)s')
        console_handler.setFormatter(console_formatter)
        
        # File handler
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(file_formatter)
        
        logger.addHandler(console_handler)
        logger.addHandler(file_handler)
        
        logger.info(f"Logging to: {log_file}")
    
    def _read_modbus_status(self, slave_id: int) -> Dict:
        """Read primary/secondary status from Modbus"""
        if not self.modbus_client:
            return {'error': 'Not connected'}
        
        try:
            # Register 6020 (address 1784) = Primary/Secondary status
            # 0 = Primary, 1 = Secondary
            result = self.modbus_client.read_holding_registers(1784, 1, slave=slave_id)
            
            if result.isError():
                return {'error': str(result)}
            
            status_value = result.registers[0]
            status_name = "Primary" if status_value == 0 else "Secondary" if status_value == 1 else f"Unknown({status_value})"
            
            return {
                'slave_id': slave_id,
                'status_value': status_value,
                'status_name': status_name,
                'timestamp': datetime.now().isoformat()
            }
        
        except Exception as e:
            return {'error': str(e)}
    
    def _modbus_monitoring_loop(self):
        """Background thread for Modbus status monitoring"""
        # Get slave IDs from config
        slaves = self.config.get('modbus', {}).get('slaves', {})
        slave_ids = list(slaves.values())
        
        if not slave_ids:
            logger.warning("[WARN] No Modbus slaves configured - using defaults")
            slave_ids = [30, 10, 32]  # Default: Network 15, 20, 25
        
        logger.info(f"[MODBUS] Monitoring slaves: {slave_ids}")
        logger.info("-"*80)
        
        last_status = {}
        
        while not self.stop_event.is_set():
            for slave_id in slave_ids:
                status = self._read_modbus_status(slave_id)
                
                # Check if status changed
                if slave_id not in last_status or last_status[slave_id] != status.get('status_name'):
                    if 'error' not in status:
                        network_name = {30: "Net15", 10: "Net20", 32: "Net25"}.get(slave_id, f"Slave{slave_id}")
                        logger.info(f"[MODBUS] {network_name} (Slave {slave_id}): {status['status_name']} (value={status['status_value']})")
                        last_status[slave_id] = status['status_name']
                        
                        # Highlight changes
                        if slave_id in self.modbus_status and self.modbus_status[slave_id].get('status_name') != status['status_name']:
                            logger.info(f"  *** STATUS CHANGE: {self.modbus_status[slave_id].get('status_name')} -> {status['status_name']} ***")
                    
                    self.modbus_status[slave_id] = status
            
            # Poll every 2 seconds
            time.sleep(2)
    
    def _publish_homeassistant_discovery(self, channel: int, gas_name: str):
        """Publish Home Assistant MQTT discovery config"""
        if not self.mqtt_client or channel in self.published_discovery:
            return
        
        try:
            device_info = {
                "identifiers": [f"oi7530_ch{channel:02d}"],
                "name": f"OI-7530 Channel {channel:02d}",
                "manufacturer": "Otis Instruments",
                "model": "OI-7530 Gas Monitor"
            }
            
            configs = {
                "reading": {
                    "name": f"Channel {channel:02d} {gas_name}",
                    "unique_id": f"oi7530_ch{channel:02d}_reading",
                    "state_topic": f"oi7530/channel{channel:02d}",
                    "value_template": "{{ value_json.reading }}",
                    "unit_of_measurement": "ppm",
                    "device_class": "gas" if gas_name not in ["None", "O2", "LEL"] else None,
                    "state_class": "measurement",
                    "device": device_info
                },
                "battery": {
                    "name": f"Channel {channel:02d} Battery",
                    "unique_id": f"oi7530_ch{channel:02d}_battery",
                    "state_topic": f"oi7530/channel{channel:02d}",
                    "value_template": "{{ value_json.battery }}",
                    "unit_of_measurement": "V",
                    "device_class": "voltage",
                    "state_class": "measurement",
                    "device": device_info
                },
                "rssi": {
                    "name": f"Channel {channel:02d} Signal",
                    "unique_id": f"oi7530_ch{channel:02d}_rssi",
                    "state_topic": f"oi7530/channel{channel:02d}",
                    "value_template": "{{ value_json.rssi }}",
                    "unit_of_measurement": "%",
                    "device_class": "signal_strength",
                    "state_class": "measurement",
                    "device": device_info
                },
                "fault": {
                    "name": f"Channel {channel:02d} Fault",
                    "unique_id": f"oi7530_ch{channel:02d}_fault",
                    "state_topic": f"oi7530/channel{channel:02d}",
                    "value_template": "{{ value_json.fault }}",
                    "device": device_info
                }
            }
            
            base_topic = f"homeassistant/sensor/oi7530_ch{channel:02d}"
            for key, config in configs.items():
                self.mqtt_client.mqtt_client.publish(f"{base_topic}_{key}/config", json.dumps(config), retain=True)
            
            self.published_discovery.add(channel)
            logger.debug(f"Published HA discovery for Ch{channel:02d}")
            
        except Exception as e:
            logger.debug(f"HA discovery error: {e}")
    
    def on_radio_message(self, msg: RadioMessage):
        """Callback for received radio messages"""
        self.packet_count += 1
        
        # Skip Protocol 7 (maintenance) - different format
        if msg.protocol == 7:
            return
        
        gas_name = GAS_TYPE_NAMES.get(msg.gas_type, f"Gas{msg.gas_type}")
        
        # Format fault status
        fault_names = {
            0: "None", 1: "Sensor Board Timeout", 2: "Bad Reading",
            3: "Sensor Fault", 4: "Duplicate Address", 5: "Low Battery",
            6: "Calibration Required"
        }
        fault_str = fault_names.get(msg.fault_code, f"Fault {msg.fault_code}")
        
        # Log packet
        elapsed = time.time() - self.start_time if self.start_time else 0
        logger.info(f"[RADIO] [{elapsed:7.1f}s] Ch{msg.channel:02d} | {gas_name:8s} | "
                   f"{msg.reading:7.1f} | Bat: {msg.battery_voltage:.1f}V | "
                   f"RSSI: {msg.rssi}% | {fault_str}")
        
        # Publish to MQTT
        if self.mqtt_client:
            try:
                self._publish_homeassistant_discovery(msg.channel, gas_name)
                
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
                logger.debug(f"MQTT error: {e}")
    
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
            # Start Modbus monitoring thread
            if self.modbus_client:
                modbus_thread = Thread(target=self._modbus_monitoring_loop, daemon=True)
                modbus_thread.start()
            
            # Start radio receiver
            self.receiver.start()
            logger.info("[OK] Radio receiver started")
            logger.info("\nMonitoring radio packets and Modbus status...")
            logger.info("-"*80)
            
            # Run for specified duration
            end_time = self.start_time + self.duration_seconds
            last_status_log = self.start_time
            
            while self.running and time.time() < end_time:
                time.sleep(1)
                
                # Log status every minute
                if time.time() - last_status_log >= 60:
                    elapsed_hours = (time.time() - self.start_time) / 3600
                    rate = self.packet_count / elapsed_hours if elapsed_hours > 0 else 0
                    remaining = (end_time - time.time()) / 60
                    
                    logger.info(f"\n[STATUS] {elapsed_hours*60:.1f}min elapsed | "
                              f"Packets: {self.packet_count} ({rate:.1f}/hr) | "
                              f"Remaining: {remaining:.1f}min")
                    
                    # Show current Modbus status
                    for slave_id, status in self.modbus_status.items():
                        network_name = {30: "Net15", 10: "Net20", 32: "Net25"}.get(slave_id, f"Slave{slave_id}")
                        logger.info(f"  {network_name}: {status.get('status_name', 'Unknown')}")
                    
                    logger.info("")
                    last_status_log = time.time()
            
            # Time expired
            if time.time() >= end_time:
                logger.info("\n" + "="*80)
                logger.info(f"Duration complete ({self.duration_seconds/60:.1f} minutes) - stopping...")
                logger.info("="*80)
        
        except Exception as e:
            logger.error(f"Error during monitoring: {e}", exc_info=True)
        
        finally:
            self.stop()
    
    def stop(self):
        """Stop monitoring"""
        if not self.running:
            return
        
        self.running = False
        self.stop_event.set()
        
        # Stop radio
        if self.receiver:
            self.receiver.stop()
            logger.info("[OK] Radio receiver stopped")
        
        # Close Modbus
        if self.modbus_client:
            self.modbus_client.close()
            logger.info("[OK] Modbus closed")
        
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
            logger.info("Final Statistics")
            logger.info("="*80)
            logger.info(f"Runtime: {elapsed_hours:.2f}h ({elapsed/60:.1f}min)")
            logger.info(f"Radio packets: {self.packet_count}")
            logger.info(f"Packet rate: {rate:.1f}/hr")
            
            logger.info("\nFinal Modbus Status:")
            for slave_id, status in self.modbus_status.items():
                network_name = {30: "Net15", 10: "Net20", 32: "Net25"}.get(slave_id, f"Slave{slave_id}")
                logger.info(f"  {network_name} (Slave {slave_id}): {status.get('status_name', 'Unknown')}")
            
            logger.info(f"\nEnd time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            logger.info("="*80)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Combined radio and Modbus status monitoring")
    parser.add_argument('--config', default='config.json', help='Configuration file')
    parser.add_argument('--duration', type=float, default=30, help='Duration in minutes')
    args = parser.parse_args()
    
    monitor = CombinedMonitor(args.config, duration_minutes=args.duration)
    monitor.start()
