"""
Modbus Register Map Parser for OI-7530/7010 Gas Monitors
Parses CSV register maps and provides structured access to register definitions.
"""
import csv
import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Union
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


@dataclass
class ModbusRegister:
    """Represents a single modbus register entry"""
    address_hex: str
    address_decimal: int
    description: str
    access: str  # R, W, or R/W
    length_bits: int
    units: Optional[str] = None
    valid_response: Optional[str] = None
    
    @property
    def data_type(self) -> str:
        """Infer data type from length"""
        if self.length_bits == 16:
            return "uint16"
        elif self.length_bits == 32:
            if self.units == "FLOAT" or "Reading" in self.description:
                return "float32"
            return "uint32"
        return "unknown"
    
    @property
    def register_count(self) -> int:
        """Number of 16-bit registers needed"""
        return self.length_bits // 16
    
    @property
    def is_readable(self) -> bool:
        """Can this register be read?"""
        return "R" in self.access
    
    @property
    def is_writable(self) -> bool:
        """Can this register be written?"""
        return "W" in self.access
    
    @property
    def mqtt_friendly_name(self) -> str:
        """Generate MQTT-friendly topic name"""
        # Convert "Channel 1 Reading" -> "channel_1_reading"
        name = self.description.lower()
        name = re.sub(r'[^\w\s]', '', name)
        name = re.sub(r'\s+', '_', name)
        return name
    
    @property
    def ha_device_class(self) -> Optional[str]:
        """Home Assistant device class for sensor"""
        desc_lower = self.description.lower()
        
        if any(x in desc_lower for x in ['temperature', 'temp']):
            return 'temperature'
        elif any(x in desc_lower for x in ['humidity', 'rh']):
            return 'humidity'
        elif any(x in desc_lower for x in ['pressure', 'pa', 'bar']):
            return 'pressure'
        elif any(x in desc_lower for x in ['voltage', 'volt']):
            return 'voltage'
        elif any(x in desc_lower for x in ['current', 'amp']):
            return 'current'
        elif any(x in desc_lower for x in ['power', 'watt']):
            return 'power'
        elif any(x in desc_lower for x in ['concentration', 'ppm', 'ppb', 'lel', '%vol']):
            return 'gas'
        
        return None
    
    @property
    def sensor_category(self) -> str:
        """Categorize sensor for organization"""
        desc_lower = self.description.lower()
        
        if 'radio address' in desc_lower:
            return 'configuration'
        elif 'reading' in desc_lower:
            return 'sensor'
        elif any(x in desc_lower for x in ['alarm', 'fault', 'status']):
            return 'diagnostic'
        elif any(x in desc_lower for x in ['relay', 'output']):
            return 'control'
        else:
            return 'other'


class RegisterMapParser:
    """Parser for OI-7530/7010 CSV register maps"""
    
    def __init__(self, csv_path: Union[str, Path]):
        self.csv_path = Path(csv_path)
        self.registers: Dict[int, ModbusRegister] = {}
        self.register_by_name: Dict[str, ModbusRegister] = {}
        self._parse()
    
    def _parse(self):
        """Parse the CSV register map file"""
        logger.info(f"Parsing register map: {self.csv_path}")
        
        # Try multiple encodings
        encodings = ['utf-8-sig', 'utf-8', 'latin-1', 'cp1252']
        content = None
        
        for enc in encodings:
            try:
                with open(self.csv_path, 'r', encoding=enc) as f:
                    content = f.read()
                    logger.debug(f"Successfully read file with {enc} encoding")
                    break
            except (UnicodeDecodeError, UnicodeError):
                continue
        
        if content is None:
            raise ValueError(f"Could not decode file {self.csv_path} with any known encoding")
        
        # Parse with detected encoding
        with open(self.csv_path, 'r', encoding=enc) as f:
            # Skip title row if present
            content = f.read()
            f.seek(0)
            
            reader = csv.reader(f)
            rows = list(reader)
            
            # Find header row (contains "Register Address")
            header_idx = 0
            for idx, row in enumerate(rows):
                if row and 'Register Address' in str(row[0]):
                    header_idx = idx
                    break
            
            # Skip to data rows
            for row in rows[header_idx + 1:]:
                if not row or len(row) < 5:
                    continue
                
                # Skip section headers
                if not row[0] or row[0].strip() in ['', 'Radio Data', 'Sensor Data', 'System Data']:
                    continue
                
                try:
                    # Parse register data
                    addr_hex = row[0].strip().upper()
                    addr_dec = int(row[1]) if row[1] else int(addr_hex, 16)
                    description = row[2].strip() if len(row) > 2 else ""
                    # Skip empty columns (3 is often empty)
                    access = row[4].strip() if len(row) > 4 and row[4].strip() else "R"
                    length = int(row[5]) if len(row) > 5 and row[5].strip().isdigit() else 16
                    units = row[6].strip() if len(row) > 6 and row[6].strip() else None
                    valid_resp = row[7].strip() if len(row) > 7 and row[7].strip() else None
                    
                    if not description:
                        continue
                    
                    register = ModbusRegister(
                        address_hex=addr_hex,
                        address_decimal=addr_dec,
                        description=description,
                        access=access,
                        length_bits=length,
                        units=units,
                        valid_response=valid_resp
                    )
                    
                    self.registers[addr_dec] = register
                    self.register_by_name[description] = register
                    
                except (ValueError, IndexError) as e:
                    logger.debug(f"Skipping row {row}: {e}")
                    continue
        
        logger.info(f"Parsed {len(self.registers)} registers")
    
    def get_register(self, address: int) -> Optional[ModbusRegister]:
        """Get register by decimal address"""
        return self.registers.get(address)
    
    def get_register_by_name(self, name: str) -> Optional[ModbusRegister]:
        """Get register by description"""
        return self.register_by_name.get(name)
    
    def get_readable_registers(self) -> List[ModbusRegister]:
        """Get all readable registers"""
        return [r for r in self.registers.values() if r.is_readable]
    
    def get_sensor_readings(self) -> List[ModbusRegister]:
        """Get all sensor reading registers (channels)"""
        return [r for r in self.registers.values() 
                if 'reading' in r.description.lower() and r.is_readable]
    
    def get_configuration_registers(self) -> List[ModbusRegister]:
        """Get configuration registers (radio addresses, settings)"""
        return [r for r in self.registers.values() 
                if r.sensor_category == 'configuration']
    
    def get_registers_by_category(self, category: str) -> List[ModbusRegister]:
        """Get registers by category"""
        return [r for r in self.registers.values() 
                if r.sensor_category == category]
    
    def get_address_ranges(self) -> List[tuple]:
        """Get contiguous address ranges for efficient bulk reads"""
        if not self.registers:
            return []
        
        sorted_addrs = sorted(self.registers.keys())
        ranges = []
        start = sorted_addrs[0]
        prev = start
        
        for addr in sorted_addrs[1:]:
            reg = self.registers[addr]
            # If gap is too large or data types are too different, start new range
            if addr - prev > 10:  # Max 10 register gap
                end = prev + (self.registers[prev].register_count - 1)
                ranges.append((start, end))
                start = addr
            prev = addr
        
        # Add final range
        end = prev + (self.registers[prev].register_count - 1)
        ranges.append((start, end))
        
        return ranges
    
    def export_to_dict(self) -> List[dict]:
        """Export all registers as list of dictionaries"""
        return [
            {
                'address': reg.address_decimal,
                'address_hex': reg.address_hex,
                'description': reg.description,
                'access': reg.access,
                'data_type': reg.data_type,
                'units': reg.units,
                'category': reg.sensor_category,
                'mqtt_topic': reg.mqtt_friendly_name,
            }
            for reg in sorted(self.registers.values(), key=lambda x: x.address_decimal)
        ]


if __name__ == "__main__":
    # Test the parser
    logging.basicConfig(level=logging.INFO)
    
    parser = RegisterMapParser("register_maps/7500-RegMap.csv")
    
    print(f"\nTotal registers: {len(parser.registers)}")
    print(f"\nSensor readings: {len(parser.get_sensor_readings())}")
    
    print("\n=== First 10 Sensor Readings ===")
    for reg in parser.get_sensor_readings()[:10]:
        print(f"  {reg.address_hex:>4s} (0x{reg.address_decimal:04x}) - {reg.description:40s} [{reg.data_type}] -> {reg.mqtt_friendly_name}")
    
    print("\n=== Address Ranges for Bulk Reads ===")
    for start, end in parser.get_address_ranges()[:5]:
        print(f"  0x{start:04x} - 0x{end:04x} ({end - start + 1} registers)")
