"""
Gas Type and Sensor Type Decoder
Based on OI WireFree Gen II Protocol Documentation

This provides human-readable names for gas types and sensor types found in radio packets.
"""

# Gas Types (from protocol documentation)
GAS_TYPES = {
    0: "H2S (Hydrogen Sulfide)",
    1: "SO2 (Sulfur Dioxide)",
    2: "O2 (Oxygen)",
    3: "CO (Carbon Monoxide)",
    4: "CL2 (Chlorine)",
    5: "CO2 (Carbon Dioxide)",
    6: "LEL (Lower Explosive Limit / Combustible)",
    7: "H2 (Hydrogen)",
    8: "HCN (Hydrogen Cyanide)",
    9: "NO2 (Nitrogen Dioxide)",
    10: "NH3 (Ammonia)",
    11: "PH3 (Phosphine)",
    12: "CH4 (Methane)",
    # Extended gas types (from field observations)
    63: "Unknown Gas Type 63 (possibly custom/calibration)",
    64: "Unknown Gas Type 64 (possibly custom/calibration)",
    65: "Unknown Gas Type 65 (possibly custom/calibration)",
}

# Sensor Types (from protocol documentation)
SENSOR_TYPES = {
    0: "Electrochemical (EC)",
    1: "Infrared (IR)",
    2: "Catalytic Bead (CB)",
    3: "Metal Oxide Semiconductor (MOS)",
    4: "Photoionization Detector (PID)",
    5: "Tank Level",
    6: "4-20mA Analog",
    7: "Switch",
    8: "Pressure",
    9: "Temperature",
    10: "Humidity",
    11: "Flow",
    12: "pH",
    13: "Conductivity",
    14: "ORP (Oxidation-Reduction Potential)",
    15: "Turbidity",
    16: "Dissolved Oxygen",
    17: "Total Suspended Solids",
    18: "Total Dissolved Solids",
    19: "Chlorophyll",
    20: "Blue-Green Algae",
    30: "OI-WF190",
    31: "None Selected",
    # From raw byte values (need bit extraction)
    128: "Raw value 128 (check bit extraction - likely EC with flags)",
    174: "Raw value 174 (check bit extraction)",
    175: "Raw value 175 (check bit extraction)",
    192: "Raw value 192 (check bit extraction - likely CB with flags)",
}

# Fault Codes (from protocol documentation)
FAULT_CODES = {
    0: "No Fault",
    1: "Over Range",
    2: "Under Range",
    3: "Sensor Fault",
    4: "Low Battery",
    5: "Calibration Required",
    # Extended fault codes
    8: "Unknown Fault 8",
    16: "Unknown Fault 16",
    32: "Unknown Fault 32",
}

# Sensor Modes
SENSOR_MODES = {
    0: "Normal Operation",
    1: "Null/Zero",
    2: "Calibration",
    3: "Relay Test",
    4: "Radio Address Mode",
    5: "Diagnostic Mode",
    6: "Advanced Menu",
    7: "Admin Menu",
}

def decode_gas_type(gas_code):
    """Get human-readable gas type name"""
    return GAS_TYPES.get(gas_code, f"Unknown Gas Type {gas_code}")

def decode_sensor_type(sensor_code):
    """Get human-readable sensor type name
    
    Note: Sensor type is extracted from byte 7, bits 3-7 (5 bits).
    If you have the raw byte value, extract it first:
        sensor_type = (byte_7 >> 3) & 0x1F
    """
    return SENSOR_TYPES.get(sensor_code, f"Unknown Sensor Type {sensor_code}")

def decode_fault_code(fault_code):
    """Get human-readable fault description
    
    Note: Fault code is extracted from byte 10, bits 4-7 (4 bits).
    If you have the raw byte value, extract it first:
        fault_code = (byte_10 >> 4) & 0x0F
    """
    return FAULT_CODES.get(fault_code, f"Unknown Fault {fault_code}")

def decode_sensor_mode(mode_code):
    """Get human-readable sensor mode
    
    Note: Sensor mode is extracted from byte 7, bits 0-2 (3 bits).
    If you have the raw byte value, extract it first:
        sensor_mode = byte_7 & 0x07
    """
    return SENSOR_MODES.get(mode_code, f"Unknown Mode {mode_code}")

def print_decoder_reference():
    """Print complete decoder reference"""
    print("=" * 80)
    print("OI WIREFREE GEN II PROTOCOL DECODER REFERENCE")
    print("=" * 80)
    print()
    
    print("GAS TYPES:")
    print("-" * 80)
    for code in sorted(GAS_TYPES.keys()):
        print(f"  {code:3d} (0x{code:02X}): {GAS_TYPES[code]}")
    print()
    
    print("SENSOR TYPES:")
    print("-" * 80)
    for code in sorted(SENSOR_TYPES.keys()):
        print(f"  {code:3d} (0x{code:02X}): {SENSOR_TYPES[code]}")
    print()
    
    print("FAULT CODES:")
    print("-" * 80)
    for code in sorted(FAULT_CODES.keys()):
        print(f"  {code:3d} (0x{code:02X}): {FAULT_CODES[code]}")
    print()
    
    print("SENSOR MODES:")
    print("-" * 80)
    for code in sorted(SENSOR_MODES.keys()):
        print(f"  {code:3d} (0x{code:02X}): {SENSOR_MODES[code]}")
    print()
    
    print("PROTOCOL 1 PACKET STRUCTURE:")
    print("-" * 80)
    print("  Byte 0-1:   Transmitter Address (16-bit big-endian)")
    print("  Byte 2:     Protocol Number (0x01 for Protocol 1)")
    print("  Byte 3-6:   Reading (32-bit float, big-endian)")
    print("  Byte 7:     Sensor Info (bits 0-2: mode, bits 3-7: type)")
    print("  Byte 8:     Battery Reading")
    print("  Byte 9:     Gas Type (bits 0-6) + Battery Scale (bit 7)")
    print("  Byte 10:    Fault Code (bits 4-7) + Precision (bits 1-3) + Has Text (bit 0)")
    print("  Byte 11:    Checksum (if no text) OR Text Length (if has text)")
    print("  Byte 12+:   Optional Text Data + Checksum")
    print()
    
    print("BIT FIELD EXTRACTION:")
    print("-" * 80)
    print("  Sensor Mode   = byte_7 & 0x07")
    print("  Sensor Type   = (byte_7 >> 3) & 0x1F")
    print("  Gas Type      = byte_9 & 0x7F")
    print("  Battery Scale = (byte_9 >> 7) & 0x01")
    print("  Fault Code    = (byte_10 >> 4) & 0x0F")
    print("  Precision     = (byte_10 >> 1) & 0x07")
    print("  Has Text      = byte_10 & 0x01")
    print()
    
    print("BATTERY VOLTAGE CALCULATION:")
    print("-" * 80)
    print("  If battery_scale == 0: voltage = battery_reading / 10.0  (0-25.5V)")
    print("  If battery_scale == 1: voltage = battery_reading * 1.0   (0-255V)")
    print()

if __name__ == "__main__":
    print_decoder_reference()
    
    # Examples
    print()
    print("USAGE EXAMPLES:")
    print("=" * 80)
    print()
    print("# Decode gas type from analysis")
    print(f"Gas type 7: {decode_gas_type(7)}")
    print(f"Gas type 63: {decode_gas_type(63)}")
    print()
    
    print("# Decode sensor type from bit-extracted value")
    print(f"Sensor type 0: {decode_sensor_type(0)}")
    print(f"Sensor type 1: {decode_sensor_type(1)}")
    print()
    
    print("# If you have raw byte value 128, extract first:")
    raw_byte_7 = 128
    sensor_mode = raw_byte_7 & 0x07
    sensor_type = (raw_byte_7 >> 3) & 0x1F
    print(f"Raw byte 7 = {raw_byte_7} (0x{raw_byte_7:02X})")
    print(f"  Sensor mode: {sensor_mode} = {decode_sensor_mode(sensor_mode)}")
    print(f"  Sensor type: {sensor_type} = {decode_sensor_type(sensor_type)}")
