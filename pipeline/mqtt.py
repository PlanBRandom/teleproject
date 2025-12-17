"""
MQTT Publisher with Home Assistant Discovery support.
Publishes modbus register data to MQTT topics with automatic sensor discovery.
"""
import json
import logging
import time
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, asdict
from datetime import datetime

try:
    import paho.mqtt.client as mqtt
except ImportError:
    mqtt = None

from pipeline.register import ModbusRegister

logger = logging.getLogger(__name__)


@dataclass
class MQTTConfig:
    """MQTT broker configuration"""
    broker: str = "localhost"
    port: int = 1883
    username: Optional[str] = None
    password: Optional[str] = None
    client_id: str = "oi7530_modbus_bridge"
    keepalive: int = 60
    
    # Topic configuration
    base_topic: str = "homeassistant"
    device_name: str = "OI-7530"
    device_id: str = "oi7530_01"
    
    # Home Assistant discovery
    discovery_enabled: bool = True
    discovery_prefix: str = "homeassistant"
    
    # QoS and retain
    qos: int = 0
    retain: bool = True


class MQTTPublisher:
    """MQTT publisher with Home Assistant autodiscovery"""
    
    def __init__(self, config: MQTTConfig):
        if mqtt is None:
            raise ImportError("paho-mqtt not installed. Run: pip install paho-mqtt")
        
        self.config = config
        self.client = mqtt.Client(client_id=config.client_id)
        
        # Set callbacks
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_publish = self._on_publish
        
        # Authentication
        if config.username:
            self.client.username_pw_set(config.username, config.password)
        
        self.connected = False
        self.published_discoveries = set()
    
    def connect(self):
        """Connect to MQTT broker"""
        try:
            logger.info(f"Connecting to MQTT broker at {self.config.broker}:{self.config.port}")
            self.client.connect(self.config.broker, self.config.port, self.config.keepalive)
            self.client.loop_start()
            
            # Wait for connection
            timeout = 10
            start = time.time()
            while not self.connected and (time.time() - start) < timeout:
                time.sleep(0.1)
            
            if not self.connected:
                raise ConnectionError("MQTT connection timeout")
            
            logger.info("MQTT connection established")
            
        except Exception as e:
            logger.error(f"Failed to connect to MQTT broker: {e}")
            raise
    
    def disconnect(self):
        """Disconnect from MQTT broker"""
        self.client.loop_stop()
        self.client.disconnect()
        logger.info("MQTT disconnected")
    
    def _on_connect(self, client, userdata, flags, rc):
        """Callback for MQTT connection"""
        if rc == 0:
            self.connected = True
            logger.info("MQTT connected successfully")
        else:
            logger.error(f"MQTT connection failed with code {rc}")
    
    def _on_disconnect(self, client, userdata, rc):
        """Callback for MQTT disconnection"""
        self.connected = False
        if rc != 0:
            logger.warning(f"MQTT unexpected disconnection (code {rc})")
    
    def _on_publish(self, client, userdata, mid):
        """Callback for successful publish"""
        logger.debug(f"Message {mid} published")
    
    def publish(self, topic: str, payload: Any, qos: Optional[int] = None, retain: Optional[bool] = None):
        """
        Publish message to MQTT topic
        
        Args:
            topic: MQTT topic
            payload: Message payload (will be JSON-encoded if dict)
            qos: Quality of Service (0, 1, or 2)
            retain: Retain message flag
        """
        if not self.connected:
            raise ConnectionError("Not connected to MQTT broker")
        
        if qos is None:
            qos = self.config.qos
        if retain is None:
            retain = self.config.retain
        
        # Convert dict to JSON
        if isinstance(payload, dict):
            payload = json.dumps(payload)
        
        result = self.client.publish(topic, payload, qos=qos, retain=retain)
        
        if result.rc != mqtt.MQTT_ERR_SUCCESS:
            logger.warning(f"Publish failed: {result.rc}")
        else:
            logger.debug(f"Published to {topic}: {payload}")
    
    def publish_sensor_value(self, register: ModbusRegister, value: Any):
        """
        Publish sensor value to MQTT
        
        Args:
            register: Register definition
            value: Sensor value
        """
        topic = f"{self.config.base_topic}/sensor/{self.config.device_id}/{register.mqtt_friendly_name}/state"
        
        # Create payload with metadata
        payload = {
            "value": value,
            "timestamp": datetime.utcnow().isoformat(),
            "unit": register.units,
            "address": register.address_decimal,
        }
        
        self.publish(topic, payload)
    
    def publish_discovery(self, register: ModbusRegister):
        """
        Publish Home Assistant MQTT discovery config
        
        Args:
            register: Register definition
        """
        if not self.config.discovery_enabled:
            return
        
        # Skip if already published
        discovery_key = f"{register.address_decimal}_{register.description}"
        if discovery_key in self.published_discoveries:
            return
        
        # Determine component type
        component = "sensor"
        if register.sensor_category == "control":
            component = "switch"
        elif "status" in register.description.lower() or "alarm" in register.description.lower():
            component = "binary_sensor"
        
        # Build discovery topic
        object_id = f"{self.config.device_id}_{register.mqtt_friendly_name}"
        discovery_topic = f"{self.config.discovery_prefix}/{component}/{object_id}/config"
        
        # Build device info
        device_info = {
            "identifiers": [self.config.device_id],
            "name": self.config.device_name,
            "model": "OI-7530/7010",
            "manufacturer": "Otis Instruments",
        }
        
        # Build discovery payload
        state_topic = f"{self.config.base_topic}/sensor/{self.config.device_id}/{register.mqtt_friendly_name}/state"
        
        discovery_payload = {
            "name": register.description,
            "unique_id": object_id,
            "state_topic": state_topic,
            "value_template": "{{ value_json.value }}",
            "device": device_info,
            "availability_topic": f"{self.config.base_topic}/sensor/{self.config.device_id}/availability",
        }
        
        # Add optional fields
        if register.units:
            discovery_payload["unit_of_measurement"] = register.units
        
        if register.ha_device_class:
            discovery_payload["device_class"] = register.ha_device_class
        
        # Add suggested display precision for gas sensors
        if register.data_type == "float32":
            discovery_payload["suggested_display_precision"] = 2
        
        # Add entity category
        if register.sensor_category == "diagnostic":
            discovery_payload["entity_category"] = "diagnostic"
        elif register.sensor_category == "configuration":
            discovery_payload["entity_category"] = "config"
        
        # Publish discovery
        self.publish(discovery_topic, discovery_payload, retain=True)
        self.published_discoveries.add(discovery_key)
        
        logger.info(f"Published discovery for: {register.description}")
    
    def publish_availability(self, available: bool):
        """
        Publish device availability status
        
        Args:
            available: True if device is online
        """
        topic = f"{self.config.base_topic}/sensor/{self.config.device_id}/availability"
        payload = "online" if available else "offline"
        self.publish(topic, payload, retain=True)
    
    def publish_device_info(self, info: Dict[str, Any]):
        """
        Publish general device information
        
        Args:
            info: Device information dictionary
        """
        topic = f"{self.config.base_topic}/sensor/{self.config.device_id}/info"
        self.publish(topic, info, retain=True)
    
    def clear_discovery(self):
        """Clear all published discovery messages (helpful for cleanup)"""
        logger.info("Clearing discovery messages...")
        
        for discovery_key in self.published_discoveries:
            # Extract object_id from key
            parts = discovery_key.split('_', 1)
            if len(parts) == 2:
                addr, name = parts
                object_id = f"{self.config.device_id}_{name}"
                
                # Clear for all component types
                for component in ["sensor", "binary_sensor", "switch"]:
                    discovery_topic = f"{self.config.discovery_prefix}/{component}/{object_id}/config"
                    self.publish(discovery_topic, "", retain=True)
        
        self.published_discoveries.clear()
    
    def __enter__(self):
        """Context manager entry"""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.publish_availability(False)
        self.disconnect()


if __name__ == "__main__":
    # Test MQTT publisher
    logging.basicConfig(level=logging.DEBUG)
    
    config = MQTTConfig(
        broker="localhost",
        device_name="OI-7530 Test",
        device_id="oi7530_test"
    )
    
    try:
        with MQTTPublisher(config) as publisher:
            # Mark device as available
            publisher.publish_availability(True)
            
            # Create test register
            from pipeline.register import ModbusRegister
            test_reg = ModbusRegister(
                address_hex="21",
                address_decimal=33,
                description="Channel 1 Reading",
                access="R",
                length_bits=32,
                units="PPM"
            )
            
            # Publish discovery
            publisher.publish_discovery(test_reg)
            
            # Publish test value
            publisher.publish_sensor_value(test_reg, 42.5)
            
            print("Test publish complete. Check MQTT broker.")
            time.sleep(2)
            
    except Exception as e:
        logger.error(f"Test failed: {e}")
