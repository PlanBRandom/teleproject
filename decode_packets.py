#!/usr/bin/env python3
"""
Decode actual packet structure from RM024 radio
Based on captured data analysis
"""

import struct
from pathlib import Path

# Sample packets from capture
packets = [
    '81110062e0882b000d81000000000824060040c8afc03e75',
    '81110057e0884900048100000000001680009bc8b1755f03',
    '81110048e088490016810000000008270680ccc8b1bc2f7c',
    '81110055e088490017810000000008270680cdc8b1bc2f7e',
    '81110061e0884900148140c0000020270780e3c8b1bc28a3',
    '8111004be0882b00098100000000002112205de088335f34',
    '8111004be0884900108141af33330017821010c8af2b5fa1',
    '8111004be0882b000b8100000000002300002fe088355fda',
]

GAS_TYPES = {
    0: "H2S", 1: "SO2", 2: "O2", 3: "CO", 4: "CL2",
    5: "CO2", 6: "LEL", 7: "VOC", 8: "FEET", 9: "HCl",
    10: "NH3", 11: "H2", 12: "ClO2", 13: "HCN", 14: "F2",
    15: "HF", 16: "CH2O", 17: "NO2", 18: "O3", 19: "INCHES",
    20: "4-20mA", 21: "Not Specified", 22: "°C", 23: "°F",
    24: "CH4", 25: "NO", 26: "PH3", 27: "HBr",
    28: "EtO", 29: "CH3SH", 30: "AsH3",
    31: "R410A", 32: "R1234YF", 33: "R32"
}

print("="*80)
print("PACKET STRUCTURE ANALYSIS")
print("="*80)

for i, hex_str in enumerate(packets, 1):
    data = bytes.fromhex(hex_str)
    
    print(f"\nPacket {i}:")
    print(f"  Raw: {hex_str}")
    print(f"  Length: {len(data)} bytes")
    
    # 0x81 frame structure
    if data[0] == 0x81:
        frame_start = data[0]
        payload_len = data[1]
        zero_byte = data[2]
        payload = data[3:3+payload_len]
        trailer = data[3+payload_len:]
        
        print(f"  Frame: 0x{frame_start:02x}")
        print(f"  Payload length: {payload_len}")
        print(f"  Zero byte: 0x{zero_byte:02x}")
        print(f"  Payload ({len(payload)} bytes): {payload.hex()}")
        print(f"  Trailer ({len(trailer)} bytes): {trailer.hex()}")
        
        # Try to decode payload
        if len(payload) >= 17:
            # Bytes 0-1: Something (address?)
            byte01 = (payload[0] << 8) | payload[1]
            print(f"\n  Payload decode:")
            print(f"    [0-1]: 0x{byte01:04x} ({byte01})")
            print(f"    [2-3]: 0x{payload[2]:02x}{payload[3]:02x}")
            print(f"    [4]: 0x{payload[4]:02x}")
            
            # Try different float interpretations
            # Big-endian float at offset 5
            if len(payload) >= 9:
                try:
                    float_be = struct.unpack('>f', payload[5:9])[0]
                    print(f"    [5-8]: {payload[5:9].hex()} = {float_be:.3f} (big-endian float)")
                except:
                    pass
                
                try:
                    float_le = struct.unpack('<f', payload[5:9])[0]
                    print(f"    [5-8]: {payload[5:9].hex()} = {float_le:.3f} (little-endian float)")
                except:
                    pass
            
            # Rest of bytes
            print(f"    [9]: 0x{payload[9]:02x} (gas type?) = {GAS_TYPES.get(payload[9], 'Unknown')}")
            print(f"    [10]: 0x{payload[10]:02x} (status?)")
            if len(payload) > 11:
                print(f"    [11-12]: 0x{payload[11]:02x}{payload[12]:02x} (flags?)")
            if len(payload) > 13:
                print(f"    [13-16]: {payload[13:17].hex()}")

print("\n" + "="*80)
print("PATTERN OBSERVATIONS:")
print("="*80)
print("\nLooking at byte [4] values:")
for hex_str in packets:
    data = bytes.fromhex(hex_str)
    payload = data[3:3+data[1]]
    if len(payload) >= 5:
        print(f"  {hex_str[:10]}... -> byte[4] = 0x{payload[4]:02x} (channel {payload[4]}?)")

print("\nLooking at byte [9] (potential gas type):")
for hex_str in packets:
    data = bytes.fromhex(hex_str)
    payload = data[3:3+data[1]]
    if len(payload) >= 10:
        gas_type = payload[9]
        print(f"  {hex_str[:10]}... -> byte[9] = 0x{gas_type:02x} = {GAS_TYPES.get(gas_type, 'Unknown')}")
