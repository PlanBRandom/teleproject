"""
Home Assistant Dashboard Generator
Automatically generates Lovelace dashboard YAML for OI-7530/7010 sensors
"""
import yaml
import logging
from pathlib import Path
from typing import List, Dict, Any
from pipeline.register import RegisterMapParser, ModbusRegister

logger = logging.getLogger(__name__)


class DashboardGenerator:
    """Generate Home Assistant Lovelace dashboards for gas monitor sensors"""
    
    def __init__(self, register_parser: RegisterMapParser, device_id: str = "oi7530_01"):
        self.register_parser = register_parser
        self.device_id = device_id
    
    def generate_sensor_card(self, registers: List[ModbusRegister]) -> Dict[str, Any]:
        """Generate sensor card showing multiple gas readings"""
        entities = []
        
        for reg in registers:
            entity_id = f"sensor.{self.device_id}_{reg.mqtt_friendly_name}"
            entities.append({"entity": entity_id})
        
        return {
            "type": "entities",
            "title": "Gas Sensor Readings",
            "entities": entities,
            "state_color": True
        }
    
    def generate_gauge_cards(self, registers: List[ModbusRegister], max_value: float = 100) -> List[Dict[str, Any]]:
        """Generate gauge cards for visual monitoring"""
        cards = []
        
        for reg in registers[:8]:  # Limit to first 8 for space
            entity_id = f"sensor.{self.device_id}_{reg.mqtt_friendly_name}"
            
            card = {
                "type": "gauge",
                "entity": entity_id,
                "name": reg.description,
                "min": 0,
                "max": max_value,
                "severity": {
                    "green": 0,
                    "yellow": max_value * 0.5,
                    "red": max_value * 0.8
                }
            }
            
            if reg.units:
                card["unit"] = reg.units
            
            cards.append(card)
        
        return cards
    
    def generate_history_graph(self, registers: List[ModbusRegister]) -> Dict[str, Any]:
        """Generate history graph card"""
        entities = []
        
        for reg in registers[:4]:  # Limit to 4 for readability
            entity_id = f"sensor.{self.device_id}_{reg.mqtt_friendly_name}"
            entities.append(entity_id)
        
        return {
            "type": "history-graph",
            "title": "Gas Levels History",
            "entities": entities,
            "hours_to_show": 24
        }
    
    def generate_statistics_card(self, registers: List[ModbusRegister]) -> Dict[str, Any]:
        """Generate statistics card for sensor data"""
        stat_entities = []
        
        for reg in registers[:6]:
            entity_id = f"sensor.{self.device_id}_{reg.mqtt_friendly_name}"
            stat_entities.append({
                "entity": entity_id,
                "name": reg.description
            })
        
        return {
            "type": "statistic",
            "entities": stat_entities,
            "period": "hour",
            "stat_type": "mean"
        }
    
    def generate_complete_dashboard(self) -> Dict[str, Any]:
        """Generate complete dashboard configuration"""
        sensor_readings = self.register_parser.get_sensor_readings()
        
        # Build view
        view = {
            "title": "OI-7530 Gas Monitor",
            "path": "oi7530_monitor",
            "icon": "mdi:gas-cylinder",
            "badges": [],
            "cards": []
        }
        
        # Add sensor list card
        view["cards"].append(self.generate_sensor_card(sensor_readings))
        
        # Add horizontal stack of gauges
        gauge_cards = self.generate_gauge_cards(sensor_readings)
        if gauge_cards:
            view["cards"].append({
                "type": "horizontal-stack",
                "cards": gauge_cards[:4]
            })
            if len(gauge_cards) > 4:
                view["cards"].append({
                    "type": "horizontal-stack",
                    "cards": gauge_cards[4:8]
                })
        
        # Add history graph
        view["cards"].append(self.generate_history_graph(sensor_readings))
        
        # Add device info card
        view["cards"].append({
            "type": "entities",
            "title": "Device Status",
            "entities": [
                {"entity": f"binary_sensor.{self.device_id}_status"},
                {"entity": f"sensor.{self.device_id}_wifi_signal"},
            ]
        })
        
        return {
            "views": [view]
        }
    
    def generate_channel_cards(self, channels: List[int]) -> List[Dict[str, Any]]:
        """Generate individual channel monitoring cards"""
        cards = []
        
        for channel_num in channels:
            # Find the register for this channel
            reg_name = f"Channel {channel_num} Reading"
            register = self.register_parser.get_register_by_name(reg_name)
            
            if not register:
                continue
            
            entity_id = f"sensor.{self.device_id}_{register.mqtt_friendly_name}"
            
            # Create a vertical stack with gauge and mini-graph
            card = {
                "type": "vertical-stack",
                "cards": [
                    {
                        "type": "gauge",
                        "entity": entity_id,
                        "name": f"Channel {channel_num}",
                        "min": 0,
                        "max": 100,
                        "severity": {
                            "green": 0,
                            "yellow": 50,
                            "red": 80
                        }
                    },
                    {
                        "type": "mini-graph-card",
                        "entities": [entity_id],
                        "hours_to_show": 12,
                        "points_per_hour": 4,
                        "line_width": 2
                    }
                ]
            }
            
            cards.append(card)
        
        return cards
    
    def save_dashboard(self, output_path: str = "configs/lovelace/dashboard.yaml"):
        """Generate and save complete dashboard"""
        dashboard = self.generate_complete_dashboard()
        
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w') as f:
            yaml.dump(dashboard, f, default_flow_style=False, sort_keys=False)
        
        logger.info(f"Dashboard saved to: {output_file}")
        return output_file
    
    def save_channel_dashboard(self, channels: List[int], output_path: str = "configs/lovelace/channels.yaml"):
        """Generate and save detailed channel dashboard"""
        cards = self.generate_channel_cards(channels)
        
        # Arrange in grid (4 columns)
        grid_cards = []
        for i in range(0, len(cards), 4):
            grid_cards.append({
                "type": "horizontal-stack",
                "cards": cards[i:i+4]
            })
        
        dashboard = {
            "views": [{
                "title": "Gas Channels",
                "path": "gas_channels",
                "icon": "mdi:gauge",
                "cards": grid_cards
            }]
        }
        
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w') as f:
            yaml.dump(dashboard, f, default_flow_style=False, sort_keys=False)
        
        logger.info(f"Channel dashboard saved to: {output_file}")
        return output_file


def generate_all_dashboards():
    """Generate all dashboard configurations"""
    logging.basicConfig(level=logging.INFO)
    
    # Load register map
    parser = RegisterMapParser("register_maps/7500-RegMap.csv")
    
    # Create generator
    generator = DashboardGenerator(parser, device_id="oi7530_01")
    
    # Generate main dashboard
    generator.save_dashboard("configs/lovelace/dashboard.yaml")
    
    # Generate detailed channel dashboard (first 16 channels)
    generator.save_channel_dashboard(list(range(1, 17)), "configs/lovelace/channels.yaml")
    
    print("\n✅ Dashboard generation complete!")
    print("   - Main dashboard: configs/lovelace/dashboard.yaml")
    print("   - Channel dashboard: configs/lovelace/channels.yaml")
    print("\nImport these files in Home Assistant:")
    print("   Configuration -> Dashboards -> Add Dashboard -> Import from YAML")


if __name__ == "__main__":
    generate_all_dashboards()
