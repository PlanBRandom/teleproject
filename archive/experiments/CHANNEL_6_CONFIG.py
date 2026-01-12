"""
OI-7032 CHANNEL 6 CONFIGURATION
================================

Date: January 6, 2026
Source: Touchscreen display observation + Modbus verification

TOUCHSCREEN DISPLAY (as observed)
----------------------------------
Radio Address Display: 6 (note: Modbus shows 7)
Battery: 23V
Mode: Normal
Reading: 0.000
Sensor Location: "UPUP"
RSSI: 95

Relays Configuration:
- All relays (1-4): ON
- Relay mode: Unlatching
- Alarm mode: On Rising
- Relay 1 setpoint: 10
- Relay 2 setpoint: 15
- Relay 3 setpoint: 20
- Relay 4 setpoint: 25

MODBUS VERIFICATION
-------------------
Channel: 6
Radio Address: 7 ✓ (confirmed via register 0x06)
Battery: 23.00V ✓ (confirmed via registers 0x8B-0x8C)
Mode: Normal ✓ (confirmed via register 0x66)
Reading: 0.000 ✓ (confirmed via registers 0x2B-0x2C)
Gas Type: CO (Carbon Monoxide)
Fault Code: 0 (No fault)

ANALYSIS
--------

Battery Match Confirmation:
  The 23V battery reading uniquely identifies this as Channel 6 (Modbus Address 7).
  This rules out Channel 5 which has Address 6 but only 3.59V battery.

Address Display Discrepancy:
  Touchscreen shows "Radio Address 6"
  Modbus shows Radio Address 7
  
  Possible explanations:
  1. Touchscreen displays "Sensor ID" or "Element Address" (different from radio address)
  2. Off-by-one display indexing (showing channel number instead of address)
  3. User configuration label vs. actual Modbus register value
  
  The battery voltage (23V) definitively confirms this is Channel 6 with Radio Address 7.

RSSI Information:
  RSSI: 95 (excellent signal strength)
  This indicates strong radio reception from the transmitter
  RSSI register location: Not yet identified in Modbus map

Location Name:
  "UPUP" - Custom sensor location identifier
  Location name register: Not yet identified in Modbus map

Relay Setpoints:
  The relay alarm setpoints (10, 15, 20, 25) are configured but not yet
  identified in the Modbus register map. These would be in the 7032's
  configuration registers (likely in the 0x200-0x300 range or higher).

GAS TYPE: CO (CARBON MONOXIDE)
-------------------------------
The Modbus query shows this channel is monitoring Carbon Monoxide (CO).
Current reading: 0.000 ppm (no CO detected)

With relay setpoints at 10, 15, 20, and 25 ppm:
- Relay 1: Triggers at 10 ppm CO
- Relay 2: Triggers at 15 ppm CO  
- Relay 3: Triggers at 20 ppm CO
- Relay 4: Triggers at 25 ppm CO

These are reasonable alarm levels for CO monitoring in industrial settings.

MAPPING SUMMARY
---------------

Channel 6 Configuration:
  ✓ Radio Address: 7 (receives from sensor element #7)
  ✓ Gas Type: CO (Carbon Monoxide)
  ✓ Battery: 23.00V (good condition)
  ✓ Reading: 0.000 ppm (safe)
  ✓ Mode: Normal operation
  ✓ RSSI: 95 (excellent signal)
  ✓ Location: "UPUP"
  ✓ Relay alarms: Configured at 10/15/20/25 ppm, all enabled

RADIO PACKET CORRELATION
-------------------------

When this sensor transmits, the radio packet structure will be:
  [0-1]  Transmitter Address: 0x8111 (33041) - Radio module
  [2]    Protocol: 0x00 (Field Data)
  [8]    Channel Number: 6
  [10-13] Reading: 0.00 (Float32)
  
The OI-7032 receives this packet, looks up Channel 6 configuration,
and reports via Modbus:
  - Radio Address: 7
  - Reading: 0.00
  - Gas: CO
  - Battery: 23.00V

ADDITIONAL REGISTERS TO MAP
----------------------------

Still need to identify Modbus registers for:
1. RSSI (signal strength) - Likely per-channel
2. Location name (string) - ASCII text storage
3. Relay setpoints (4 per channel) - Float32 values
4. Relay enable/disable flags
5. Relay alarm direction (rising/falling)
6. Relay latching/unlatching mode

These are likely in extended register ranges beyond the basic data registers.

---
This documentation combines touchscreen observation with Modbus verification
to create a complete picture of Channel 6 configuration.
"""

if __name__ == "__main__":
    print(__doc__)
