#!/usr/bin/env python3
"""
Decode Laird Radio Packets for OI Gas Monitors

Parses raw hex packet data from Laird wireless radio modules.
Packet structure matches the WireFree Generation II protocol.

Usage:
    python decode_radio_packets.py --file test_data/radio_packets_sample.txt
    python decode_radio_packets.py --port COM7 --live
"""

import argparse
import re
from typing import List, Dict, Optional
from datetime import datetime
import struct


class LairdPacketDecoder:
    """Decoder for Laird WireFree Generation II radio packets"""
    
    # Packet type identifiers
    PACKET_TYPES = {
        0x81: "Standard Data",
        0x82: "Extended Data",
        0x83: "Configuration",
        0x84: "Status",
    }
    
    def __init__(self):
        self.stats = {
            'total_packets': 0,
            'valid_packets': 0,
            'invalid_packets': 0,
            'by_channel': {},
            'by_type': {}
        }
    
    def parse_hex_line(self, line: str) -> Optional[bytes]:
        """
        Parse a line of hex data into bytes
        
        Args:
            line: String like "81 11 00 11 E0 88..."
            
        Returns:
            bytes object or None if invalid
        """
        # Remove extra whitespace and get hex bytes
        hex_str = ' '.join(line.split())
        hex_parts = hex_str.split()
        
        try:
            return bytes([int(h, 16) for h in hex_parts])
        except ValueError:
            return None
    
    def decode_packet(self, packet_bytes: bytes) -> Dict:
        """
        Decode a Laird radio packet
        
        Packet structure (typical):
        Byte 0: Start byte (0x81, 0x82, etc.)
        Byte 1: Command/Type
        Byte 2-3: Sequence/Address
        Byte 4-7: Radio ID (4 bytes)
        Byte 8-9: Command specific
        Byte 10+: Data payload
        Last 2-4: Checksum/CRC
        
        Returns:
            Dict with decoded fields
        """
        self.stats['total_packets'] += 1
        
        if len(packet_bytes) < 10:
            self.stats['invalid_packets'] += 1
            return {'error': 'Packet too short', 'raw': packet_bytes.hex()}
        
        result = {
            'timestamp': datetime.now().isoformat(),
            'raw_hex': ' '.join(f'{b:02X}' for b in packet_bytes),
            'length': len(packet_bytes)
        }
        
        # Byte 0: Start byte / packet type
        start_byte = packet_bytes[0]
        result['start_byte'] = f'0x{start_byte:02X}'
        result['packet_type'] = self.PACKET_TYPES.get(start_byte, 'Unknown')
        
        # Byte 1: Command
        result['command'] = f'0x{packet_bytes[1]:02X}'
        
        # Byte 2-3: Sequence or address
        result['sequence'] = (packet_bytes[2] << 8) | packet_bytes[3]
        
        # Byte 4-7: Radio ID (big endian)
        if len(packet_bytes) >= 8:
            radio_id = struct.unpack('>I', packet_bytes[4:8])[0]
            result['radio_id'] = f'0x{radio_id:08X}'
        
        # Byte 8-9: Additional addressing
        if len(packet_bytes) >= 10:
            result['channel_addr'] = f'0x{packet_bytes[8]:02X}'
            result['sub_command'] = f'0x{packet_bytes[9]:02X}'
        
        # Try to extract sensor data
        if start_byte == 0x81 and len(packet_bytes) >= 20:
            # Standard data packet - look for sensor value
            # Bytes 10-17 often contain sensor data
            data_section = packet_bytes[10:18]
            result['data_hex'] = ' '.join(f'{b:02X}' for b in data_section)
            
            # Try to parse as various formats
            try:
                # Attempt to find channel number (often in specific position)
                # This varies by protocol, but byte 9 or nearby bytes often indicate channel
                if len(packet_bytes) >= 15:
                    # Common location for channel number
                    channel_byte = packet_bytes[9]
                    if 0x01 <= channel_byte <= 0x20:  # 1-32
                        result['channel'] = channel_byte
                        self.stats['by_channel'][channel_byte] = \
                            self.stats['by_channel'].get(channel_byte, 0) + 1
                
                # Try to extract numeric value (varies by device)
                # Some devices use bytes 14-17 for float values
                if len(packet_bytes) >= 18:
                    # Try as 32-bit float
                    try:
                        value_bytes = packet_bytes[14:18]
                        value = struct.unpack('>f', value_bytes)[0]
                        if -1000 < value < 1000:  # Sanity check
                            result['sensor_value'] = round(value, 2)
                    except:
                        pass
                    
                    # Try as 16-bit int
                    try:
                        value_int = struct.unpack('>H', packet_bytes[14:16])[0]
                        result['sensor_value_raw'] = value_int
                    except:
                        pass
            except Exception as e:
                result['parse_error'] = str(e)
        
        # Extended packet (0x82)
        elif start_byte == 0x82:
            result['note'] = 'Extended packet - contains additional diagnostic data'
            if len(packet_bytes) >= 15:
                # Byte 10-11 often contain error/status codes
                result['status_code'] = f'0x{packet_bytes[10]:02X}'
        
        self.stats['valid_packets'] += 1
        self.stats['by_type'][result['packet_type']] = \
            self.stats['by_type'].get(result['packet_type'], 0) + 1
        
        return result
    
    def decode_file(self, filepath: str) -> List[Dict]:
        """Decode all packets from a file"""
        results = []
        
        with open(filepath, 'r') as f:
            content = f.read()
        
        # Split into lines and find hex data
        lines = content.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            if not line or not any(c in '0123456789ABCDEFabcdef' for c in line):
                continue
            
            packet_bytes = self.parse_hex_line(line)
            if packet_bytes and len(packet_bytes) >= 10:
                decoded = self.decode_packet(packet_bytes)
                results.append(decoded)
        
        return results
    
    def print_summary(self):
        """Print decoding statistics"""
        print("\n" + "="*70)
        print("PACKET DECODING SUMMARY")
        print("="*70)
        print(f"Total packets processed: {self.stats['total_packets']}")
        print(f"Valid packets: {self.stats['valid_packets']}")
        print(f"Invalid packets: {self.stats['invalid_packets']}")
        print()
        
        print("By Packet Type:")
        for ptype, count in sorted(self.stats['by_type'].items()):
            print(f"  {ptype:20s}: {count:4d}")
        print()
        
        if self.stats['by_channel']:
            print("By Channel:")
            for channel, count in sorted(self.stats['by_channel'].items()):
                print(f"  Channel {channel:2d}: {count:4d} packets")
        print("="*70)


def live_decode(port: str, baudrate: int = 9600):
    """Decode packets from live serial port"""
    import serial
    
    decoder = LairdPacketDecoder()
    
    print(f"Opening {port} at {baudrate} baud...")
    print("Press Ctrl+C to stop\n")
    
    try:
        ser = serial.Serial(port, baudrate, timeout=1)
        
        buffer = bytearray()
        packet_count = 0
        
        while True:
            # Read available data
            if ser.in_waiting:
                data = ser.read(ser.in_waiting)
                buffer.extend(data)
                
                # Look for packet start byte
                while len(buffer) >= 24:  # Minimum packet size
                    # Find start byte (0x81 or 0x82)
                    start_idx = -1
                    for i in range(len(buffer)):
                        if buffer[i] in [0x81, 0x82]:
                            start_idx = i
                            break
                    
                    if start_idx == -1:
                        buffer.clear()
                        break
                    
                    # Remove junk before start
                    if start_idx > 0:
                        buffer = buffer[start_idx:]
                    
                    # Try to extract packet (assume 24 bytes for now)
                    # Real implementation would parse length field
                    packet_size = 24
                    if len(buffer) >= packet_size:
                        packet = bytes(buffer[:packet_size])
                        buffer = buffer[packet_size:]
                        
                        decoded = decoder.decode_packet(packet)
                        packet_count += 1
                        
                        # Print decoded packet
                        print(f"\n--- Packet #{packet_count} ---")
                        print(f"Type: {decoded.get('packet_type', 'Unknown')}")
                        print(f"Radio ID: {decoded.get('radio_id', 'N/A')}")
                        if 'channel' in decoded:
                            print(f"Channel: {decoded['channel']}")
                        if 'sensor_value' in decoded:
                            print(f"Sensor Value: {decoded['sensor_value']}")
                        print(f"Raw: {decoded['raw_hex'][:60]}...")
                        
    except KeyboardInterrupt:
        print("\n\nStopped by user")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if 'ser' in locals():
            ser.close()
        decoder.print_summary()


def main():
    parser = argparse.ArgumentParser(description='Decode Laird radio packets')
    parser.add_argument('--file', '-f', type=str,
                       help='File containing hex packet data')
    parser.add_argument('--port', '-p', type=str,
                       help='Serial port for live capture (e.g., COM7)')
    parser.add_argument('--baudrate', '-b', type=int, default=9600,
                       help='Serial baudrate (default: 9600)')
    parser.add_argument('--live', '-l', action='store_true',
                       help='Live capture mode')
    parser.add_argument('--output', '-o', type=str,
                       help='Output file for decoded JSON')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Verbose output')
    
    args = parser.parse_args()
    
    # Live capture mode
    if args.live and args.port:
        live_decode(args.port, args.baudrate)
        return
    
    # File decode mode
    if args.file:
        decoder = LairdPacketDecoder()
        
        print(f"Decoding packets from: {args.file}")
        print()
        
        results = decoder.decode_file(args.file)
        
        # Print results
        for i, packet in enumerate(results, 1):
            if args.verbose:
                print(f"\n{'='*70}")
                print(f"Packet #{i}")
                print(f"{'='*70}")
                for key, value in packet.items():
                    print(f"{key:20s}: {value}")
            else:
                # Compact output
                ptype = packet.get('packet_type', 'Unknown')
                radio = packet.get('radio_id', 'N/A')
                channel = packet.get('channel', '?')
                value = packet.get('sensor_value', packet.get('sensor_value_raw', 'N/A'))
                
                print(f"#{i:3d} | {ptype:15s} | Radio: {radio} | "
                      f"Ch: {channel:2} | Value: {value}")
        
        # Print summary
        decoder.print_summary()
        
        # Export to JSON if requested
        if args.output:
            import json
            with open(args.output, 'w') as f:
                json.dump(results, f, indent=2)
            print(f"\nDecoded data exported to: {args.output}")
    
    else:
        parser.print_help()
        print("\nExamples:")
        print("  Decode from file:")
        print("    python decode_radio_packets.py --file test_data/radio_packets_sample.txt")
        print("\n  Live capture:")
        print("    python decode_radio_packets.py --port COM7 --live")
        print("\n  Verbose output:")
        print("    python decode_radio_packets.py --file test_data/radio_packets_sample.txt --verbose")


if __name__ == "__main__":
    main()
