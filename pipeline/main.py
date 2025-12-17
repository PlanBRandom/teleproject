"""
OI-7530/7010 Modbus to MQTT Bridge
Main application for polling gas monitor registers and publishing to MQTT/Home Assistant
"""
import logging
import time
import signal
import sys
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, field

from pipeline.register import RegisterMapParser, ModbusRegister
from pipeline.modbus_client import ModbusClient, ModbusConfig, ConnectionType
from pipeline.mqtt import MQTTPublisher, MQTTConfig

logger = logging.getLogger(__name__)


@dataclass
class AppConfig:
    """Application configuration"""
    # Modbus settings
    modbus: Dict[str, Any] = field(default_factory=dict)
    
    # MQTT settings
    mqtt: Dict[str, Any] = field(default_factory=dict)
    
    # Polling settings
    poll_interval: float = 5.0  # seconds
    
    # Register map file
    register_map: str = "register_maps/7500-RegMap.csv"
    
    # Which registers to poll
    poll_sensor_readings: bool = True
    poll_configuration: bool = False
    poll_diagnostics: bool = True
    
    # Logging
    log_level: str = "INFO"
    log_file: Optional[str] = None


class ModbusMQTTBridge:
    """Main bridge application"""
    
    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self.running = False
        
        # Setup logging
        self._setup_logging()
        
        # Load register map
        logger.info(f"Loading register map: {self.config.register_map}")
        self.register_parser = RegisterMapParser(self.config.register_map)
        
        # Initialize modbus client
        self.modbus_config = self._create_modbus_config()
        self.modbus_client = None
        
        # Initialize MQTT publisher
        self.mqtt_config = self._create_mqtt_config()
        self.mqtt_publisher = None
        
        # Determine which registers to poll
        self.poll_registers = self._select_poll_registers()
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _load_config(self) -> AppConfig:
        """Load configuration from YAML file"""
        if not self.config_path.exists():
            logger.warning(f"Config file not found: {self.config_path}, using defaults")
            return AppConfig()
        
        with open(self.config_path, 'r') as f:
            config_dict = yaml.safe_load(f)
        
        return AppConfig(**config_dict)
    
    def _setup_logging(self):
        """Configure logging"""
        log_level = getattr(logging, self.config.log_level.upper(), logging.INFO)
        
        handlers = [logging.StreamHandler(sys.stdout)]
        
        if self.config.log_file:
            handlers.append(logging.FileHandler(self.config.log_file))
        
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=handlers
        )
    
    def _create_modbus_config(self) -> ModbusConfig:
        """Create ModbusConfig from app config"""
        modbus_cfg = self.config.modbus
        
        # Determine connection type
        conn_type = modbus_cfg.get('type', 'rtu').lower()
        connection_type = ConnectionType.RTU if conn_type == 'rtu' else ConnectionType.TCP
        
        return ModbusConfig(
            connection_type=connection_type,
            port=modbus_cfg.get('port', 'COM3'),
            baudrate=modbus_cfg.get('baudrate', 9600),
            bytesize=modbus_cfg.get('bytesize', 8),
            parity=modbus_cfg.get('parity', 'N'),
            stopbits=modbus_cfg.get('stopbits', 1),
            host=modbus_cfg.get('host', '192.168.1.100'),
            tcp_port=modbus_cfg.get('tcp_port', 502),
            slave_id=modbus_cfg.get('slave_id', 1),
            timeout=modbus_cfg.get('timeout', 3),
            retries=modbus_cfg.get('retries', 3),
        )
    
    def _create_mqtt_config(self) -> MQTTConfig:
        """Create MQTTConfig from app config"""
        mqtt_cfg = self.config.mqtt
        
        return MQTTConfig(
            broker=mqtt_cfg.get('broker', 'localhost'),
            port=mqtt_cfg.get('port', 1883),
            username=mqtt_cfg.get('username'),
            password=mqtt_cfg.get('password'),
            client_id=mqtt_cfg.get('client_id', 'oi7530_modbus_bridge'),
            base_topic=mqtt_cfg.get('base_topic', 'homeassistant'),
            device_name=mqtt_cfg.get('device_name', 'OI-7530'),
            device_id=mqtt_cfg.get('device_id', 'oi7530_01'),
            discovery_enabled=mqtt_cfg.get('discovery_enabled', True),
        )
    
    def _select_poll_registers(self):
        """Select which registers to poll based on config"""
        poll_registers = []
        
        if self.config.poll_sensor_readings:
            poll_registers.extend(self.register_parser.get_sensor_readings())
        
        if self.config.poll_configuration:
            poll_registers.extend(self.register_parser.get_configuration_registers())
        
        if self.config.poll_diagnostics:
            diagnostics = self.register_parser.get_registers_by_category('diagnostic')
            poll_registers.extend(diagnostics)
        
        # Remove duplicates
        seen = set()
        unique_registers = []
        for reg in poll_registers:
            if reg.address_decimal not in seen:
                seen.add(reg.address_decimal)
                unique_registers.append(reg)
        
        logger.info(f"Selected {len(unique_registers)} registers to poll")
        return unique_registers
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}, shutting down...")
        self.stop()
    
    def start(self):
        """Start the bridge"""
        logger.info("Starting OI-7530/7010 Modbus-MQTT Bridge")
        
        try:
            # Connect to modbus
            logger.info("Initializing Modbus connection...")
            self.modbus_client = ModbusClient(self.modbus_config)
            
            # Connect to MQTT
            logger.info("Initializing MQTT connection...")
            self.mqtt_publisher = MQTTPublisher(self.mqtt_config)
            self.mqtt_publisher.connect()
            
            # Publish availability
            self.mqtt_publisher.publish_availability(True)
            
            # Publish discovery messages for all registers
            if self.mqtt_config.discovery_enabled:
                logger.info("Publishing Home Assistant discovery messages...")
                for register in self.poll_registers:
                    self.mqtt_publisher.publish_discovery(register)
            
            # Start polling loop
            self.running = True
            self._poll_loop()
            
        except KeyboardInterrupt:
            logger.info("Interrupted by user")
        except Exception as e:
            logger.error(f"Fatal error: {e}", exc_info=True)
        finally:
            self.stop()
    
    def _poll_loop(self):
        """Main polling loop"""
        logger.info(f"Starting poll loop (interval: {self.config.poll_interval}s)")
        
        error_count = 0
        max_errors = 10
        
        while self.running:
            cycle_start = time.time()
            
            try:
                # Poll all registers
                for register in self.poll_registers:
                    if not self.running:
                        break
                    
                    try:
                        # Read register value
                        value = self.modbus_client.read_register_value(
                            register.address_decimal,
                            register.data_type
                        )
                        
                        # Publish to MQTT
                        self.mqtt_publisher.publish_sensor_value(register, value)
                        
                        logger.debug(f"{register.description}: {value} {register.units or ''}")
                        
                    except Exception as e:
                        logger.error(f"Error reading {register.description} at address {register.address_decimal}: {e}")
                        error_count += 1
                        
                        if error_count >= max_errors:
                            logger.critical(f"Too many errors ({error_count}), attempting reconnection...")
                            self._reconnect()
                            error_count = 0
                
                # Reset error count on successful cycle
                if error_count > 0:
                    error_count = max(0, error_count - 1)
                
                # Sleep for remainder of poll interval
                elapsed = time.time() - cycle_start
                sleep_time = max(0, self.config.poll_interval - elapsed)
                
                if sleep_time > 0:
                    time.sleep(sleep_time)
                else:
                    logger.warning(f"Poll cycle took {elapsed:.2f}s (longer than {self.config.poll_interval}s interval)")
                
            except Exception as e:
                logger.error(f"Error in poll loop: {e}", exc_info=True)
                time.sleep(5)
    
    def _reconnect(self):
        """Attempt to reconnect modbus and MQTT"""
        try:
            logger.info("Reconnecting modbus...")
            if self.modbus_client:
                self.modbus_client.reconnect()
            
            logger.info("Reconnecting MQTT...")
            if self.mqtt_publisher and not self.mqtt_publisher.connected:
                self.mqtt_publisher.connect()
                self.mqtt_publisher.publish_availability(True)
        
        except Exception as e:
            logger.error(f"Reconnection failed: {e}")
    
    def stop(self):
        """Stop the bridge"""
        logger.info("Stopping bridge...")
        self.running = False
        
        if self.mqtt_publisher:
            try:
                self.mqtt_publisher.publish_availability(False)
                self.mqtt_publisher.disconnect()
            except Exception as e:
                logger.error(f"Error disconnecting MQTT: {e}")
        
        if self.modbus_client:
            try:
                self.modbus_client.close()
            except Exception as e:
                logger.error(f"Error closing modbus: {e}")
        
        logger.info("Bridge stopped")


def main():
    """Entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='OI-7530/7010 Modbus to MQTT Bridge')
    parser.add_argument('-c', '--config', default='config.yaml', help='Configuration file path')
    parser.add_argument('-v', '--verbose', action='store_true', help='Enable verbose logging')
    
    args = parser.parse_args()
    
    # Override log level if verbose
    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    
    # Create and start bridge
    bridge = ModbusMQTTBridge(config_path=args.config)
    bridge.start()


if __name__ == "__main__":
    main()
