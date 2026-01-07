"""
Complete OI-7032/7530/7010 register definitions with enumerations and control commands
"""

# Gas Type Enumeration (registers 0x101-0x120 / 257-288)
# Complete OI-7032 specification including firmware 4.1.3+ gases
GAS_TYPES = {
    0: "H2S",
    1: "SO2",
    2: "O2",
    3: "CO",
    4: "CL2",
    5: "CO2",
    6: "LEL",
    7: "VOC",
    8: "FEET",
    9: "HCl",
    10: "NH3",
    11: "H2",
    12: "ClO2",
    13: "HCN",
    14: "F2",
    15: "HF",
    16: "CH2O",
    17: "NO2",
    18: "O3",
    19: "INCHES",
    20: "4-20mA",
    21: "Not Specified",
    22: "°C",
    23: "°F",
    24: "CH4",
    25: "NO",
    26: "PH3",
    27: "HBr",
    28: "EtO",          # Firmware 4.1.3+
    29: "CH3SH",        # Firmware 4.1.3+
    30: "AsH3",         # Firmware 4.1.3+
    31: "R410A",        # Firmware 4.1.3+
    32: "R1234YF",      # Firmware 4.1.3+
    33: "R32"           # Firmware 4.1.3+
}

# Sensor Type Enumeration (registers 0xE1-0x100 / 225-256)
# Note: Base-1/PLC addressing shows these as 0xE2-0x101 (add 1)
SENSOR_TYPES = {
    0: "EC (Electrochemical)",
    1: "IR (Infrared)",
    2: "CB (Catalytic Bead)",  # CATBEAD - for LEL/combustible gas
    3: "MOS (Metal Oxide Semiconductor)",
    4: "PID (Photo-Ionization Detector)",
    5: "Tank Level",
    6: "4-20mA",
    7: "Switch",
    8: "Pressure",
    9: "Temperature",
    10: "Humidity",
}

# Mode Enumeration (registers 0x61-0x80 / 97-128)
MODE_CODES = {
    0: "Off",
    1: "Normal",
    2: "Inhibit",
    3: "Maintenance",
    4: "Calibration",
    5: "Null",
    6: "Reserved",
    7: "Reserved"
}

# Fault Enumeration (registers 0x121-0x140 / 289-320)
FAULT_CODES = {
    0: "None",
    1: "Sensor Timeout",
    2: "Sensor reading below null (152 Model Only)",
    3: "Replace sensor element (LPIR Only)",
    4: "ADC not responding",
    5: "Null Failed",
    6: "Cal Failed",
    7: "Future Error",
    8: "Two Sensors Same Address",
    9: "Sensor Radio Timeout",
    10: "No sensor connected (Wired)",
    11: "Rapid temperature change (LPIR Only)",
    12: "Sensor Element Restarting (LPIR Only)",
    13: "Unspecified Error on sensor unit",
    14: "No Primary Monitor at Sensor Head"
}

# Register Addresses
class RegisterAddresses:
    """All register addresses for OI monitors"""
    
    # Channel data (per channel offsets)
    RADIO_ADDRESS_BASE = 0x01  # 1-32: Channel 1-32 radio addresses
    READING_BASE = 0x21  # 33-95: Channel 1-32 readings (Float32, +2 per channel)
    MODE_BASE = 0x61  # 97-128: Channel 1-32 mode
    BATTERY_BASE = 0x81  # 129-191: Channel 1-32 battery voltage (Float32, +2)
    SECONDS_SINCE_MSG_BASE = 0xC1  # 193-224: Channel 1-32 seconds since last message
    SENSOR_TYPE_BASE = 0xE1  # 225-256: Channel 1-32 sensor type
    GAS_TYPE_BASE = 0x101  # 257-288: Channel 1-32 gas type
    FAULT_BASE = 0x121  # 289-320: Channel 1-32 fault status
    DAYS_SINCE_NULL_BASE = 0x3E1  # 993-1024: Channel 1-32 days since last nulled
    DAYS_SINCE_CAL_BASE = 0x401  # 1025-1056: Channel 1-32 days since last calibrated
    
    # Channel configuration
    RELAY1_ENABLE_BASE = 0x161  # 353-384: Channel 1-32 Relay 1 On/Off
    RELAY1_SETPOINT_BASE = 0x1A1  # 417-479: Channel 1-32 Relay 1 Setpoint (Float32, +2)
    WIRED_RADIO_SELECT_BASE = 0x1A5  # 421-424: Channel 29-32 Wired/Radio select
    
    # Device information
    MODBUS_ADDRESS = 0x1771  # 6001: Current modbus address
    MODBUS_BAUD_RATE = 0x1772  # 6002: Current baud rate
    DATE_MONTH = 0x1773  # 6003: Month
    DATE_DAY = 0x1774  # 6004: Day
    DATE_YEAR = 0x1775  # 6005: Year
    SERIAL_NUMBER = 0x1777  # 6007: Serial number (32-bit)
    
    # Startup menu settings
    RESTORE_FACTORY_DEFAULT = 0x177B  # 6011: Factory reset (write 1 to reset)
    RELAY3_AS_FAULT = 0x177C  # 6012: Relay 3 as fault relay
    RELAY1_FAILSAFE = 0x177D  # 6013: Relay 1 fail safe
    RELAY2_FAILSAFE = 0x177E  # 6014: Relay 2 fail safe
    RELAY3_FAILSAFE = 0x177F  # 6015: Relay 3 fail safe
    FAULT_TERMINAL_FAILSAFE = 0x1781  # 6017: Fault terminal fail safe
    RADIO_TIMEOUT = 0x1782  # 6018: Radio timeout in minutes (6-255)
    NETWORK_CHANNEL = 0x1783  # 6019: Network channel (1-78)
    PRIMARY_SECONDARY = 0x1784  # 6020: Primary/Secondary (0=Primary, 1=Secondary)
    
    # Relay alarm states
    RELAY1_IN_ALARM = 0x1785  # 6021: Relay 1 in alarm
    RELAY2_IN_ALARM = 0x1786  # 6022: Relay 2 in alarm
    RELAY3_IN_ALARM = 0x1787  # 6023: Relay 3 in alarm
    
    # Diagnostics and control
    RESET = 0x2704  # 9988: Reset unit (write 1 to reset)
    SERIAL_RX_GOOD = 0x2705  # 9989: Serial receive good count
    SERIAL_RX_ERROR = 0x2706  # 9990: Serial receive error count
    SERIAL_TX_GOOD = 0x2707  # 9991: Serial transmit good count
    SERIAL_TX_ERROR = 0x2708  # 9992: Serial transmit error count
    RADIO_RX_GOOD = 0x2709  # 9993: Radio receive good count
    RADIO_RX_ERROR = 0x270A  # 9994: Radio receive error count
    RADIO_TX_GOOD = 0x270B  # 9995: Radio transmit good count
    RADIO_TX_ERROR = 0x270C  # 9996: Radio transmit error count
    UPTIME_DAYS = 0x270D  # 9997: Uptime days
    UPTIME_HOURS = 0x270E  # 9998: Uptime hours
    UPTIME_MINUTES = 0x270F  # 9999: Uptime minutes

def get_channel_register(base_address: int, channel: int, is_float32: bool = False) -> int:
    """
    Calculate register address for a specific channel
    
    Args:
        base_address: Base register address
        channel: Channel number (1-32)
        is_float32: True if register is Float32 (occupies 2 registers)
        
    Returns:
        Register address for the specified channel
    """
    if is_float32:
        return base_address + (channel - 1) * 2
    else:
        return base_address + (channel - 1)

def get_gas_name(gas_type_code: int) -> str:
    """Get gas name from gas type code"""
    return GAS_TYPES.get(gas_type_code, f"Unknown gas type {gas_type_code}")

def get_sensor_name(sensor_type_code: int) -> str:
    """Get sensor name from sensor type code"""
    return SENSOR_TYPES.get(sensor_type_code, f"Unknown sensor type {sensor_type_code}")

def get_mode_name(mode_code: int) -> str:
    """Get mode name from mode code"""
    return MODE_CODES.get(mode_code, f"Unknown mode {mode_code}")

def get_fault_name(fault_code: int) -> str:
    """Get fault name from fault code"""
    return FAULT_CODES.get(fault_code, f"Unknown fault {fault_code}")

def get_units_for_gas(gas_type_code: int) -> str:
    """Get appropriate units for a gas type"""
    if gas_type_code == 2:  # O2
        return "%"
    elif gas_type_code == 5:  # CO2
        return "%"
    elif gas_type_code == 6:  # LEL
        return "% LEL"
    elif gas_type_code == 8:  # FEET
        return "Feet"
    elif gas_type_code == 19:  # INCHES
        return "Inches"
    elif gas_type_code == 20:  # 4-20mA
        return "mA"
    elif gas_type_code == 22:  # °C
        return "°C"
    else:
        return "PPM"
