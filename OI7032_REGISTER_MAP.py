"""
OI-7032 REGISTER MAP - CORRECTED WITH BASE-1/PLC ADDRESSING
============================================================

CRITICAL: Address Conversion
-----------------------------
Modbus Poll and PLCs typically use "Base-1" or "PLC addressing" which adds 1
to the actual Modbus RTU register address.

When using Modbus RTU protocol (like our Python code):
  Actual Modbus Address = PLC Address - 1

Example for Channel 6:
  PLC shows:    0xE6 (230) for Sensor Type
  Modbus uses:  0xE5 (229) for Sensor Type
  
  PLC shows:    0x106 (262) for Gas Type
  Modbus uses:  0x105 (261) for Gas Type

CHANNEL 6 COMPLETE REGISTER MAP
--------------------------------

Register Name              | PLC Addr | Modbus Addr | Type      | Value | Meaning
---------------------------|----------|-------------|-----------|-------|---------------------------
Radio Address              | 0x0006   | 0x0005      | UInt16 RW | 7     | Sensor element address
Reading                    | 0x002B   | 0x002A      | Float32 R | 0.000 | Current gas reading
Mode                       | 0x0066   | 0x0065      | Enum16 R  | 0     | Operating mode
Battery                    | 0x008B   | 0x008A      | Float32 R | 23.00 | Battery voltage
Time Since Last Message    | 0x00C6   | 0x00C5      | UInt16 R  | 23    | Seconds since last packet
Sensor Type                | 0x00E6   | 0x00E5      | Enum16 R  | 2     | CB (Catalytic Bead)
Gas Type                   | 0x0106   | 0x0105      | Enum16 R  | 6     | LEL / %LEL

VERIFIED VALUES FOR CHANNEL 6
------------------------------

From Touchscreen Display:
- Radio Address: 6 (display label) / 7 (actual Modbus value)
- Sensor Type: CATBEAD (Catalytic Bead) = enumeration value 2 ✓
- Gas Type: %LEL (Percent Lower Explosive Limit) = enumeration value 6 ✓
- Reading: 0.000 %LEL ✓
- Battery: 23V ✓
- Mode: Normal
- Location: "UPUP"
- RSSI: 95
- Relays: 1-4 all ON, unlatching, alarm on rising
- Relay Setpoints: 10, 15, 20, 25 %LEL

From Modbus Query (corrected addresses):
- Register 0x0005: Radio Address = 7 ✓
- Register 0x002A-0x002B: Reading = 0.000 ✓
- Register 0x008A-0x008B: Battery = 23.00V ✓
- Register 0x00E5: Sensor Type = 2 (CB) ✓
- Register 0x0105: Gas Type = 6 (LEL) ✓

SENSOR TYPE ENUMERATION
-----------------------
Value | Name | Description
------|------|------------
0     | EC   | Electrochemical sensor
1     | IR   | Infrared sensor
2     | CB   | Catalytic Bead sensor ← CHANNEL 6
3     | MOS  | Metal Oxide Semiconductor
4     | PID  | Photo-Ionization Detector
5     | -    | Tank Level sensor
6     | -    | 4-20mA sensor
7     | -    | Switch
8     | -    | Pressure sensor
9     | -    | Temperature sensor
10    | -    | Humidity sensor

GAS TYPE ENUMERATION
--------------------
Value | Name  | Description
------|-------|------------
0     | H2S   | Hydrogen Sulfide
1     | SO2   | Sulfur Dioxide
2     | O2    | Oxygen
3     | CO    | Carbon Monoxide
4     | CL2   | Chlorine
5     | CO2   | Carbon Dioxide
6     | LEL   | Lower Explosive Limit / %LEL ← CHANNEL 6
7     | VOC   | Volatile Organic Compounds
8     | HCl   | Hydrogen Chloride
9     | NH3   | Ammonia
10    | H2    | Hydrogen
11    | ClO2  | Chlorine Dioxide
12    | HCN   | Hydrogen Cyanide
13    | NO2   | Nitrogen Dioxide
14    | PH3   | Phosphine

REGISTER PATTERN FOR ALL CHANNELS (1-32)
-----------------------------------------

To get register address for any channel N (1-32):

PLC/Base-1 Addressing:
- Radio Address:    0x0001 + (N-1) = 0x0001 to 0x0020
- Reading:          0x0021 + (N-1)*2 = 0x0021 to 0x005F (Float32, 2 registers)
- Mode:             0x0061 + (N-1) = 0x0061 to 0x0080
- Battery:          0x0081 + (N-1)*2 = 0x0081 to 0x00BF (Float32, 2 registers)
- Time Since Msg:   0x00C1 + (N-1) = 0x00C1 to 0x00E0
- Sensor Type:      0x00E1 + (N-1) = 0x00E1 to 0x0100
- Gas Type:         0x0101 + (N-1) = 0x0101 to 0x0120

Modbus RTU (0-based) Addressing:
- Radio Address:    0x0000 + (N-1) = 0x0000 to 0x001F
- Reading:          0x0020 + (N-1)*2 = 0x0020 to 0x005E (Float32, 2 registers)
- Mode:             0x0060 + (N-1) = 0x0060 to 0x007F
- Battery:          0x0080 + (N-1)*2 = 0x0080 to 0x00BE (Float32, 2 registers)
- Time Since Msg:   0x00C0 + (N-1) = 0x00C0 to 0x00DF
- Sensor Type:      0x00E0 + (N-1) = 0x00E0 to 0x00FF
- Gas Type:         0x0100 + (N-1) = 0x0100 to 0x011F

CHANNEL 6 SPECIFIC ADDRESSES
-----------------------------

PLC Addressing (Base-1):
- Radio Address:    0x0006 (6)
- Reading:          0x002B (43-44)
- Mode:             0x0066 (102)
- Battery:          0x008B (139-140)
- Time Since Msg:   0x00C6 (198)
- Sensor Type:      0x00E6 (230)
- Gas Type:         0x0106 (262)

Modbus RTU (0-based):
- Radio Address:    0x0005 (5)
- Reading:          0x002A (42-43)
- Mode:             0x0065 (101)
- Battery:          0x008A (138-139)
- Time Since Msg:   0x00C5 (197)
- Sensor Type:      0x00E5 (229)
- Gas Type:         0x0105 (261)

CATALYTIC BEAD SENSOR FOR LEL MEASUREMENT
------------------------------------------

Sensor: CB (Catalytic Bead) - Type 2
Gas: LEL (Lower Explosive Limit) - Type 6
Units: %LEL (Percent of Lower Explosive Limit)

Catalytic Bead sensors detect combustible gases by measuring heat from
catalytic oxidation. They are the industry standard for LEL detection.

Current Configuration (Channel 6):
- Measuring: Combustible gas concentration as %LEL
- Relay alarms at: 10%, 15%, 20%, 25% LEL
- Battery: 23V (good)
- Signal strength (RSSI): 95 (excellent)
- Current reading: 0.000 %LEL (safe)

REMAINING UNMAPPED REGISTERS
-----------------------------

Still need to identify:
1. RSSI (signal strength) - User reports 95 for Channel 6
2. Location name ("UPUP") - ASCII string storage
3. Relay setpoint registers (4 per channel):
   - Relay 1: 10 %LEL
   - Relay 2: 15 %LEL
   - Relay 3: 20 %LEL
   - Relay 4: 25 %LEL
4. Relay configuration:
   - Enable/disable flags
   - Latching/unlatching mode
   - Alarm direction (rising/falling)

These are likely in extended register ranges (0x200+).

---
Validated: January 6, 2026
Source: OI-7032 touchscreen display + Modbus RTU queries
Channel: 6 (Radio Address 7, CATBEAD, %LEL, 23V battery)
"""

if __name__ == "__main__":
    print(__doc__)
