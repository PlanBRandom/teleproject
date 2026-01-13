#!/usr/bin/env python3
"""
System Configuration Wizard
Interactive setup for Modbus and Radio monitoring before deployment
"""
import json
import yaml
import sys
import os
from pathlib import Path
from typing import Dict, List, Optional


class ConfigWizard:
    """Interactive configuration wizard"""
    
    def __init__(self):
        self.base_path = Path(__file__).parent
        self.modbus_config = {}
        self.radio_configs = []
        
    def print_header(self, title: str):
        """Print formatted header"""
        print("\n" + "=" * 80)
        print(f"  {title}")
        print("=" * 80 + "\n")
    
    def print_section(self, title: str):
        """Print section header"""
        print(f"\n--- {title} ---")
    
    def get_input(self, prompt: str, default: Optional[str] = None, 
                  validation_func=None) -> str:
        """Get validated user input"""
        while True:
            if default:
                user_input = input(f"{prompt} [{default}]: ").strip()
                if not user_input:
                    user_input = default
            else:
                user_input = input(f"{prompt}: ").strip()
                if not user_input:
                    print("  ⚠ This field is required. Please enter a value.")
                    continue
            
            if validation_func:
                valid, message = validation_func(user_input)
                if not valid:
                    print(f"  ⚠ {message}")
                    continue
            
            return user_input
    
    def get_choice(self, prompt: str, choices: List[str], default: Optional[str] = None) -> str:
        """Get user choice from list"""
        print(f"\n{prompt}")
        for i, choice in enumerate(choices, 1):
            default_marker = " (default)" if choice == default else ""
            print(f"  {i}. {choice}{default_marker}")
        
        while True:
            choice_input = input(f"Enter choice [1-{len(choices)}]: ").strip()
            
            if not choice_input and default:
                return default
            
            try:
                choice_idx = int(choice_input) - 1
                if 0 <= choice_idx < len(choices):
                    return choices[choice_idx]
                else:
                    print(f"  ⚠ Please enter a number between 1 and {len(choices)}")
            except ValueError:
                print(f"  ⚠ Please enter a valid number")
    
    def validate_port(self, value: str) -> tuple:
        """Validate COM port"""
        if sys.platform.startswith('win'):
            if value.upper().startswith('COM'):
                return True, ""
            return False, "Windows COM port should be like COM1, COM10, etc."
        else:
            if value.startswith('/dev/'):
                return True, ""
            return False, "Linux/Mac port should be like /dev/ttyUSB0, /dev/ttyAMA0, etc."
    
    def validate_baudrate(self, value: str) -> tuple:
        """Validate baud rate"""
        try:
            baud = int(value)
            valid_bauds = [1200, 2400, 4800, 9600, 19200, 38400, 57600, 115200]
            if baud in valid_bauds:
                return True, ""
            return False, f"Baud rate should be one of: {', '.join(map(str, valid_bauds))}"
        except ValueError:
            return False, "Baud rate must be a number"
    
    def validate_slave_id(self, value: str) -> tuple:
        """Validate Modbus slave ID"""
        try:
            slave_id = int(value)
            if 1 <= slave_id <= 247:
                return True, ""
            return False, "Slave ID must be between 1 and 247"
        except ValueError:
            return False, "Slave ID must be a number"
    
    def validate_network_id(self, value: str) -> tuple:
        """Validate network ID"""
        try:
            net_id = int(value)
            if 0 <= net_id <= 255:
                return True, ""
            return False, "Network ID must be between 0 and 255"
        except ValueError:
            return False, "Network ID must be a number"
    
    def configure_modbus(self):
        """Configure Modbus connection"""
        self.print_header("MODBUS CONFIGURATION")
        
        print("Configure Modbus RTU connection to OI gas monitor")
        print()
        
        # Monitor model
        models = ["OI-7032", "OI-7530", "OI-7010", "OI-7500", "Other"]
        model = self.get_choice("Select monitor model:", models, default="OI-7032")
        
        # Suggest slave ID based on model
        slave_id_suggestion = {
            "OI-7032": "32",
            "OI-7530": "30",
            "OI-7010": "10",
            "OI-7500": "1",
            "Other": "1"
        }
        
        # COM port
        self.print_section("Serial Port Settings")
        port = self.get_input(
            "Modbus COM port",
            default="COM10",
            validation_func=self.validate_port
        )
        
        # Baud rate
        baudrate = self.get_input(
            "Baud rate",
            default="19200",
            validation_func=self.validate_baudrate
        )
        
        # Slave ID
        slave_id = self.get_input(
            f"Modbus Slave ID (typical for {model})",
            default=slave_id_suggestion.get(model, "1"),
            validation_func=self.validate_slave_id
        )
        
        # MQTT settings
        self.print_section("MQTT Broker Settings")
        print("Configure where to publish Modbus data")
        
        use_cloud = self.get_choice(
            "MQTT broker type:",
            ["Local (localhost:1883)", "HiveMQ Cloud", "Custom"],
            default="Local (localhost:1883)"
        )
        
        if use_cloud == "Local (localhost:1883)":
            mqtt_broker = "localhost"
            mqtt_port = "1883"
            mqtt_username = ""
            mqtt_password = ""
            use_tls = False
        elif use_cloud == "HiveMQ Cloud":
            mqtt_broker = "a1bcc059f5f74a6d8271e8b567fecc6d.s1.eu.hivemq.cloud"
            mqtt_port = "8883"
            mqtt_username = self.get_input("MQTT Username", default="laird")
            mqtt_password = self.get_input("MQTT Password", default="LairdRM024")
            use_tls = True
        else:
            mqtt_broker = self.get_input("MQTT Broker address", default="localhost")
            mqtt_port = self.get_input("MQTT Port", default="1883")
            mqtt_username = self.get_input("MQTT Username (leave empty if none)", default="")
            mqtt_password = self.get_input("MQTT Password (leave empty if none)", default="")
            use_tls = self.get_choice("Use TLS/SSL?", ["Yes", "No"], default="No") == "Yes"
        
        # Device naming
        device_name = self.get_input("Device name", default=f"{model} Gas Monitor")
        device_id = self.get_input("Device ID", default=model.lower().replace("-", "_") + "_01")
        
        # Polling settings
        self.print_section("Polling Configuration")
        poll_interval = self.get_input("Poll interval (seconds)", default="5.0")
        
        # Store configuration
        self.modbus_config = {
            "modbus": {
                "type": "rtu",
                "port": port,
                "baudrate": int(baudrate),
                "bytesize": 8,
                "parity": "N",
                "stopbits": 1,
                "host": "192.168.1.100",
                "tcp_port": 502,
                "slave_id": int(slave_id),
                "timeout": 3,
                "retries": 3
            },
            "mqtt": {
                "broker": mqtt_broker,
                "port": int(mqtt_port),
                "username": mqtt_username if mqtt_username else None,
                "password": mqtt_password if mqtt_password else None,
                "use_tls": use_tls,
                "device_name": device_name,
                "device_id": device_id,
                "base_topic": "homeassistant",
                "client_id": f"{device_id}_modbus_bridge",
                "discovery_enabled": True,
                "discovery_prefix": "homeassistant"
            },
            "poll_interval": float(poll_interval),
            "poll_sensor_readings": True,
            "poll_configuration": False,
            "poll_diagnostics": True,
            "register_map": "register_maps/7500-RegMap.csv",
            "log_level": "INFO",
            "log_file": None
        }
        
        print("\n✓ Modbus configuration complete")
    
    def configure_radios(self):
        """Configure radio monitors"""
        self.print_header("RADIO MONITOR CONFIGURATION")
        
        print("Configure WireFree radio receivers for wireless gas monitor communication")
        print()
        
        # How many radios?
        num_radios_str = self.get_input(
            "How many radio receivers to configure",
            default="3"
        )
        
        try:
            num_radios = int(num_radios_str)
            if num_radios < 0 or num_radios > 10:
                print("  ⚠ Setting to 3 radios (0-10 allowed)")
                num_radios = 3
        except ValueError:
            print("  ⚠ Invalid number, defaulting to 3")
            num_radios = 3
        
        for i in range(num_radios):
            self.print_section(f"Radio Monitor {i + 1}")
            
            # COM port
            default_port = f"COM{7 + i}" if sys.platform.startswith('win') else f"/dev/ttyUSB{i}"
            port = self.get_input(
                f"Radio {i + 1} COM port",
                default=default_port,
                validation_func=self.validate_port
            )
            
            # Baud rate
            baudrate = self.get_input(
                f"Radio {i + 1} Baud rate",
                default="115200",
                validation_func=self.validate_baudrate
            )
            
            # Network ID
            network_id = self.get_input(
                f"Radio {i + 1} Network ID",
                default=str(15 + i * 5),
                validation_func=self.validate_network_id
            )
            
            # Primary or Secondary
            role = self.get_choice(
                f"Radio {i + 1} Role:",
                ["Primary (monitors and logs)", "Secondary (monitors only)"],
                default="Primary (monitors and logs)"
            )
            is_primary = "Primary" in role
            
            # MQTT publishing
            publish_mqtt = self.get_choice(
                f"Publish Radio {i + 1} data to MQTT?",
                ["Yes", "No"],
                default="Yes"
            ) == "Yes"
            
            # Store radio config
            config_name = f"radio_config_com{port.upper().replace('COM', '').replace('/DEV/TTYUSB', '')}.json"
            
            radio_config = {
                "port": port,
                "baudrate": int(baudrate),
                "network_id": int(network_id),
                "role": "primary" if is_primary else "secondary",
                "mqtt": {
                    "enabled": publish_mqtt,
                    "broker": self.modbus_config["mqtt"]["broker"],
                    "port": self.modbus_config["mqtt"]["port"],
                    "topic": f"wirefree/network_{network_id}",
                    "qos": 1
                },
                "logging": {
                    "enabled": True,
                    "log_packets": True,
                    "log_hex": is_primary,
                    "log_stats": is_primary
                },
                "monitor_name": f"WireFree_Net{network_id}_{port.upper().replace('COM', '').replace('/DEV/TTYUSB', '')}"
            }
            
            self.radio_configs.append({
                "filename": config_name,
                "config": radio_config
            })
            
            print(f"✓ Radio {i + 1} configured")
        
        print(f"\n✓ {num_radios} radio monitor(s) configured")
    
    def save_configs(self):
        """Save all configurations to files"""
        self.print_header("SAVING CONFIGURATION")
        
        # Save Modbus config
        config_path = self.base_path / "config.yaml"
        print(f"Saving Modbus config to: {config_path}")
        
        with open(config_path, 'w') as f:
            yaml.dump(self.modbus_config, f, default_flow_style=False, sort_keys=False)
        
        print("✓ Modbus configuration saved")
        
        # Save radio configs
        for radio in self.radio_configs:
            config_path = self.base_path / radio["filename"]
            print(f"Saving radio config to: {config_path}")
            
            with open(config_path, 'w') as f:
                json.dump(radio["config"], f, indent=2)
        
        print(f"✓ {len(self.radio_configs)} radio configuration(s) saved")
    
    def show_summary(self):
        """Display configuration summary"""
        self.print_header("CONFIGURATION SUMMARY")
        
        print("📊 MODBUS SETUP:")
        print(f"  Port:        {self.modbus_config['modbus']['port']}")
        print(f"  Baud Rate:   {self.modbus_config['modbus']['baudrate']}")
        print(f"  Slave ID:    {self.modbus_config['modbus']['slave_id']}")
        print(f"  Device:      {self.modbus_config['mqtt']['device_name']}")
        print(f"  MQTT Broker: {self.modbus_config['mqtt']['broker']}:{self.modbus_config['mqtt']['port']}")
        
        print("\n📡 RADIO SETUP:")
        for i, radio in enumerate(self.radio_configs, 1):
            cfg = radio["config"]
            print(f"  Radio {i}:")
            print(f"    Port:       {cfg['port']}")
            print(f"    Baud Rate:  {cfg['baudrate']}")
            print(f"    Network ID: {cfg['network_id']}")
            print(f"    Role:       {cfg['role'].upper()}")
            print(f"    MQTT:       {'Enabled' if cfg['mqtt']['enabled'] else 'Disabled'}")
        
        print("\n" + "=" * 80)
        print("Configuration complete! You can now start monitoring.")
        print("\nTo start 24-hour monitoring run:")
        print("  .\\run_24hr.ps1")
        print("\nTo test Modbus connection run:")
        print("  python test_modbus_connection.py")
        print("=" * 80 + "\n")
    
    def run(self):
        """Run the configuration wizard"""
        print("\n")
        print("╔═══════════════════════════════════════════════════════════════════════════╗")
        print("║         OI-7500 SYSTEM CONFIGURATION WIZARD                               ║")
        print("╚═══════════════════════════════════════════════════════════════════════════╝")
        print("\nThis wizard will help you configure:")
        print("  • Modbus RTU connection to gas monitor")
        print("  • WireFree radio receivers")
        print("  • MQTT data publishing")
        print("\nPress Ctrl+C at any time to cancel\n")
        
        try:
            # Configure Modbus
            self.configure_modbus()
            
            # Configure Radios
            self.configure_radios()
            
            # Save everything
            self.save_configs()
            
            # Show summary
            self.show_summary()
            
            return True
            
        except KeyboardInterrupt:
            print("\n\n⚠ Configuration cancelled by user")
            return False
        except Exception as e:
            print(f"\n❌ Error during configuration: {e}")
            import traceback
            traceback.print_exc()
            return False


def main():
    """Main entry point"""
    wizard = ConfigWizard()
    success = wizard.run()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
