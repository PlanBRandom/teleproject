#!/usr/bin/env python3
"""
Multi-Network Repeater Flow Analyzer
Analyzes packet flow through 3-tier repeater network:
  Network 15/20 (direct sensors) → Repeaters → Network 25 (primary)
"""

import re
import struct
import json
from collections import defaultdict
from datetime import datetime

# Gas type mapping
GAS_TYPES = {
    0: "H2S", 1: "SO2", 2: "O2", 3: "CO", 4: "CL2", 5: "CO2", 6: "LEL", 7: "VOC",
    8: "FEET", 9: "HCl", 10: "NH3", 11: "H2", 12: "ClO2", 13: "HCN", 14: "F2", 
    15: "HF", 16: "CH2O", 17: "NO2", 18: "O3", 19: "INCHES", 20: "4-20mA", 
    21: "Not Specified", 22: "°C", 23: "°F", 24: "CH4", 25: "NO", 26: "PH3", 
    27: "HBr", 28: "EtO", 29: "CH3SH", 30: "AsH3", 31: "R410A", 32: "R1234YF", 33: "R32"
}

def decode_0x81_packet(hex_data):
    """Decode RM024 API transmit packet (0x81 frame) - wrapped by repeater."""
    if len(hex_data) < 48 or hex_data[0:2] != '81':
        return None
    
    try:
        data = bytes.fromhex(hex_data)
        if len(data) < 24:
            return None
        
        channel = data[8]
        reading = struct.unpack('>f', data[10:14])[0]
        gas_type = data[14]
        status = data[15]
        radio_addr = int(hex_data[6:10], 16)
        
        return {
            'frame_type': '0x81_wrapped',
            'channel': channel,
            'reading': reading,
            'gas_type': gas_type,
            'gas_name': GAS_TYPES.get(gas_type, f"Unknown({gas_type})"),
            'status': status,
            'radio_addr': radio_addr,
        }
    except:
        return None

def decode_gen2_packet(hex_data):
    """Decode Gen2 protocol packet (direct from sensor)."""
    # Gen2 packets start with protocol byte, followed by data
    # This is a simplified decoder - actual Gen2 is more complex
    try:
        data = bytes.fromhex(hex_data)
        if len(data) < 16:
            return None
        
        # Try to identify Gen2 by looking for protocol markers
        protocol = data[0]
        
        # Protocol 1 (sensor reading) has specific structure
        if protocol == 1 and len(data) >= 16:
            # Extract channel and reading (exact positions depend on Gen2 format)
            # This is a placeholder - real Gen2 decoding is more complex
            return {
                'frame_type': 'gen2_direct',
                'protocol': protocol,
                'raw_length': len(data)
            }
        
        return None
    except:
        return None

def parse_network_log(log_file):
    """Parse a network log file and extract packet information."""
    packets = []
    
    with open(log_file, 'r') as f:
        for line in f:
            # Match timestamp and hex data
            match = re.match(r'\[([^\]]+)\] RX: (\d+) bytes - ([0-9a-f]+)', line)
            if match:
                timestamp_str = match.group(1)
                byte_count = int(match.group(2))
                hex_data = match.group(3)
                
                # Try to decode as 0x81 wrapped packet
                decoded = decode_0x81_packet(hex_data)
                if decoded:
                    decoded['timestamp'] = timestamp_str
                    decoded['raw_hex'] = hex_data
                    decoded['byte_count'] = byte_count
                    packets.append(decoded)
                else:
                    # Not a recognized wrapped packet, might be direct Gen2
                    decoded = decode_gen2_packet(hex_data)
                    if decoded:
                        decoded['timestamp'] = timestamp_str
                        decoded['raw_hex'] = hex_data
                        decoded['byte_count'] = byte_count
                        packets.append(decoded)
    
    return packets

def analyze_network_comparison(log_prefix):
    """Compare packets across all three networks."""
    
    print("="*100)
    print("MULTI-NETWORK REPEATER FLOW ANALYSIS")
    print("="*100)
    print()
    
    # Parse logs from each network
    networks = {
        'Network_15': {'file': f'protocol_logs/Network_15_{log_prefix}.log', 'type': 'Direct Sensors'},
        'Network_20': {'file': f'protocol_logs/Network_20_{log_prefix}.log', 'type': 'Direct Sensors'},
        'Network_25': {'file': f'protocol_logs/Network_25_{log_prefix}.log', 'type': 'Primary via Repeaters'},
    }
    
    network_data = {}
    
    print("Loading network logs...")
    for network, info in networks.items():
        try:
            packets = parse_network_log(info['file'])
            network_data[network] = {
                'packets': packets,
                'type': info['type'],
                'channels': set(),
                'gas_types': defaultdict(int),
            }
            
            # Collect statistics
            for packet in packets:
                if 'channel' in packet:
                    network_data[network]['channels'].add(packet['channel'])
                    network_data[network]['gas_types'][packet['gas_name']] += 1
            
            print(f"  ✓ {network}: {len(packets)} packets")
        except FileNotFoundError:
            print(f"  ✗ {network}: Log file not found")
            network_data[network] = {'packets': [], 'type': info['type'], 'channels': set(), 'gas_types': {}}
    
    print()
    
    # Network summary
    print("="*100)
    print("NETWORK SUMMARY")
    print("="*100)
    
    for network in ['Network_15', 'Network_20', 'Network_25']:
        data = network_data[network]
        print(f"\n{network} ({data['type']}):")
        print(f"  Total packets: {len(data['packets']):,}")
        print(f"  Unique channels: {len(data['channels'])}")
        
        if data['channels']:
            print(f"  Channels detected: {sorted(data['channels'])}")
        
        if data['gas_types']:
            print(f"  Gas types:")
            for gas, count in sorted(data['gas_types'].items(), key=lambda x: x[1], reverse=True)[:10]:
                print(f"    {gas:15s}: {count:4d} packets")
    
    print()
    print("="*100)
    print("REPEATER FORWARDING ANALYSIS")
    print("="*100)
    
    # Compare Network 15 vs Network 25
    net15_channels = network_data['Network_15']['channels']
    net20_channels = network_data['Network_20']['channels']
    net25_channels = network_data['Network_25']['channels']
    
    print(f"\nNetwork 15 channels: {sorted(net15_channels) if net15_channels else 'None'}")
    print(f"Network 20 channels: {sorted(net20_channels) if net20_channels else 'None'}")
    print(f"Network 25 channels: {sorted(net25_channels) if net25_channels else 'None'}")
    print()
    
    # Channels only on Network 15/20 (not forwarded)
    direct_only = (net15_channels | net20_channels) - net25_channels
    if direct_only:
        print(f"⚠️  Channels on 15/20 but NOT forwarded to 25: {sorted(direct_only)}")
        print(f"    (These sensors might not be configured for repeater forwarding)")
    
    # Channels only on Network 25 (forwarded from repeaters)
    forwarded_only = net25_channels - (net15_channels | net20_channels)
    if forwarded_only:
        print(f"✓ Channels on 25 but not seen on 15/20: {sorted(forwarded_only)}")
        print(f"    (These are being forwarded through repeaters)")
    
    # Channels on both (should be the majority)
    both = net25_channels & (net15_channels | net20_channels)
    if both:
        print(f"✓ Channels appearing on both direct and primary: {sorted(both)}")
        print(f"    (Successfully forwarded through repeater network)")
    
    print()
    print("="*100)
    print("CHANNEL ROUTING TABLE")
    print("="*100)
    print(f"\n{'Channel':<10} {'Network 15':<12} {'Network 20':<12} {'Network 25':<12} {'Gas Type':<15} {'Status'}")
    print("-"*100)
    
    all_channels = net15_channels | net20_channels | net25_channels
    
    for ch in sorted(all_channels):
        # Find gas type from any network
        gas_type = "?"
        for network in ['Network_15', 'Network_20', 'Network_25']:
            for packet in network_data[network]['packets']:
                if packet.get('channel') == ch:
                    gas_type = packet.get('gas_name', '?')
                    break
            if gas_type != "?":
                break
        
        on_15 = "✓" if ch in net15_channels else "✗"
        on_20 = "✓" if ch in net20_channels else "✗"
        on_25 = "✓" if ch in net25_channels else "✗"
        
        # Determine status
        if ch in net15_channels or ch in net20_channels:
            if ch in net25_channels:
                status = "Forwarded"
            else:
                status = "NOT FORWARDED"
        else:
            status = "Only on Network 25"
        
        print(f"{ch:<10} {on_15:<12} {on_20:<12} {on_25:<12} {gas_type:<15} {status}")
    
    print()
    print("="*100)
    print("SAMPLE PACKET FLOW (Channel by Channel)")
    print("="*100)
    
    # Show sample packets for each channel across networks
    for ch in sorted(list(all_channels)[:10]):  # Limit to first 10 channels
        print(f"\nChannel {ch}:")
        
        for network in ['Network_15', 'Network_20', 'Network_25']:
            samples = [p for p in network_data[network]['packets'] if p.get('channel') == ch][:2]
            if samples:
                print(f"  {network}:")
                for sample in samples:
                    reading = sample.get('reading', 0)
                    gas = sample.get('gas_name', '?')
                    ts = sample.get('timestamp', '?')[:19]
                    print(f"    [{ts}] {reading:8.2f} ppm {gas}")
    
    print()
    print("="*100)
    print("RADIO ADDRESS ANALYSIS (Network 25)")
    print("="*100)
    
    # Analyze radio addresses on Network 25 (repeater identifiers)
    radio_addrs = defaultdict(lambda: {'count': 0, 'channels': set()})
    
    for packet in network_data['Network_25']['packets']:
        if 'radio_addr' in packet:
            addr = packet['radio_addr']
            radio_addrs[addr]['count'] += 1
            if 'channel' in packet:
                radio_addrs[addr]['channels'].add(packet['channel'])
    
    if radio_addrs:
        print(f"\n{'Radio Address':<15} {'Packets':<10} {'Channels'}")
        print("-"*100)
        for addr, info in sorted(radio_addrs.items(), key=lambda x: x[1]['count'], reverse=True):
            channels_str = str(sorted(info['channels']))
            print(f"0x{addr:04X} ({addr:5d})   {info['count']:6d}    {channels_str}")
        
        print(f"\nNote: Radio addresses identify which repeater radio forwarded the packet.")
        print(f"      Different addresses = different repeater radios on networks 15/20")
    
    print()
    print("="*100)
    print("RECOMMENDATIONS")
    print("="*100)
    print()
    
    if direct_only:
        print("⚠️  Some channels are not being forwarded to the primary (Network 25):")
        print("    - Check repeater configuration for these channels")
        print("    - Verify sensors are on correct radio networks")
        print()
    
    if forwarded_only:
        print("✓ Some channels only appear on Network 25 (expected for forwarded packets):")
        print("    - These sensors are likely on networks not directly monitored")
        print("    - Or were captured at different times")
        print()
    
    print("📊 Next steps:")
    print("    1. Compare packet timing between networks (repeater latency)")
    print("    2. Check for packet loss (count discrepancies)")
    print("    3. Monitor Modbus polling to see which monitors are reading which channels")
    print("    4. Identify the SO2 sensor for oven testing")
    print()
    print("="*100)

def analyze_modbus_log(log_prefix):
    """Analyze Modbus traffic."""
    
    print()
    print("="*100)
    print("MODBUS TRAFFIC ANALYSIS")
    print("="*100)
    
    log_file = f'protocol_logs/modbus_{log_prefix}.log'
    
    slave_traffic = defaultdict(lambda: {'requests': 0, 'responses': 0, 'bytes': 0})
    
    try:
        with open(log_file, 'r') as f:
            for line in f:
                match = re.match(r'\[([^\]]+)\] RX: (\d+) bytes - ([0-9a-f]+)', line)
                if match:
                    byte_count = int(match.group(2))
                    hex_data = match.group(3)
                    
                    if len(hex_data) >= 4:
                        slave_id = int(hex_data[0:2], 16)
                        function = int(hex_data[2:4], 16)
                        
                        slave_traffic[slave_id]['bytes'] += byte_count
                        
                        # Function code > 0x80 is an error response
                        if function >= 0x80:
                            slave_traffic[slave_id]['responses'] += 1
                        elif function in [0x03, 0x04, 0x06, 0x10]:  # Read/write functions
                            slave_traffic[slave_id]['responses'] += 1
        
        print(f"\n{'Slave ID':<10} {'Monitor':<10} {'Responses':<12} {'Total Bytes'}")
        print("-"*100)
        
        slave_names = {
            3: "OI-7032",
            10: "OI-7010", 
            30: "OI-7530"
        }
        
        for slave_id in [3, 10, 30]:
            info = slave_traffic[slave_id]
            name = slave_names.get(slave_id, "Unknown")
            print(f"{slave_id:<10} {name:<10} {info['responses']:6d}       {info['bytes']:8d}")
        
        if not slave_traffic:
            print("  No Modbus traffic detected")
            print("  Possible causes:")
            print("    - No Modbus master polling")
            print("    - Wrong COM port")
            print("    - Baudrate mismatch")
    
    except FileNotFoundError:
        print(f"\n  ✗ Modbus log not found: {log_file}")
    
    print()
    print("="*100)

if __name__ == '__main__':
    import sys
    import glob
    
    # Find the most recent log timestamp
    log_files = glob.glob('protocol_logs/Network_15_*.log')
    
    if not log_files:
        print("ERROR: No network log files found in protocol_logs/")
        print("Run monitor_multi_network.py first to collect data")
        sys.exit(1)
    
    # Extract timestamp from filename
    log_file = log_files[-1]  # Most recent
    timestamp = log_file.split('_')[-1].replace('.log', '')
    
    print(f"Analyzing logs with timestamp: {timestamp}")
    print()
    
    analyze_network_comparison(timestamp)
    analyze_modbus_log(timestamp)
    
    # Load stats if available
    stats_file = f'protocol_logs/stats_{timestamp}.json'
    try:
        with open(stats_file, 'r') as f:
            stats = json.load(f)
        
        print()
        print("="*100)
        print("CAPTURE STATISTICS")
        print("="*100)
        print(f"\nCapture started: {stats.get('start_time', 'Unknown')}")
        print(f"Capture ended:   {stats.get('last_update', 'Unknown')}")
        
        elapsed = stats.get('elapsed_seconds', 0)
        print(f"Duration:        {elapsed:.0f} seconds ({elapsed/60:.1f} minutes)")
        
        print()
        print("="*100)
    except FileNotFoundError:
        pass
