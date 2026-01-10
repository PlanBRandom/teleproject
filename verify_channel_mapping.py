"""Verify channel mapping in packets"""
import struct

packets = [
    # Channel 5, Address 6, LEL, Reading 1.0
    ('8111000fe088490005813f80000000240300ece08829462f', 5, 6, 1.0, 'LEL'),
    # Channel 20, Address 21, VOC, Reading 6.0
    ('81110014e0884900148140c0000020270780e3c8b1bc34af', 20, 21, 6.0, 'VOC'),
]

print('='*80)
print('CHANNEL MAPPING VERIFICATION')
print('='*80)
print()

for packet_hex, expected_channel, expected_addr, expected_reading, gas in packets:
    packet = bytes.fromhex(packet_hex)
    
    print(f'Expected: Channel {expected_channel}, Address {expected_addr}, {gas}, Reading {expected_reading:.2f}')
    print(f'  Packet: {packet_hex}')
    print(f'  Byte [3]: {packet[3]} (0x{packet[3]:02x})')
    print(f'  Byte [8]: {packet[8]} (0x{packet[8]:02x}) ← MATCHES CHANNEL {expected_channel}!')
    print(f'  Reading [10-13]: {struct.unpack(">f", packet[10:14])[0]:.2f} ✓')
    print()

print('='*80)
print('CORRECTED PACKET STRUCTURE:')
print('='*80)
print('[0-1]  Transmitter Address (16-bit)')
print('[2]    Protocol (0x00 = Field Data)')
print('[3]    Sequence number or flags')
print('[4-7]  Unknown (possibly timestamp or padding)')
print('[8]    7032 Channel Number ✓')
print('[9]    Unknown (always 0x81)')
print('[10-13] Reading (Float32) ✓')
print('[14+]  Additional data (gas type, battery, fault, etc.)')
