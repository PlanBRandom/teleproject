#!/usr/bin/env python3
"""
Real-Time Packet Flow Matcher
Correlates packets as they travel through the repeater network:
  Sensor → Network 15/20 → Repeater → Network 25 (Primary)
Measures repeater latency and identifies packet loss.
"""

import re
import struct
from datetime import datetime, timedelta
from collections import defaultdict, deque
import glob

# Gas type mapping
GAS_TYPES = {
    0: "H2S", 1: "SO2", 2: "O2", 3: "CO", 4: "CL2", 5: "CO2", 6: "LEL", 7: "VOC",
    8: "FEET", 9: "HCl", 10: "NH3", 11: "H2", 12: "ClO2", 13: "HCN", 14: "F2", 
    15: "HF", 16: "CH2O", 17: "NO2", 18: "O3", 19: "INCHES", 20: "4-20mA", 
    21: "Not Specified", 22: "°C", 23: "°F", 24: "CH4", 25: "NO", 26: "PH3", 
    27: "HBr", 28: "EtO", 29: "CH3SH", 30: "AsH3", 31: "R410A", 32: "R1234YF", 33: "R32"
}

def parse_timestamp(ts_str):
    """Parse ISO timestamp string to datetime."""
    try:
        return datetime.fromisoformat(ts_str)
    except:
        return None

def decode_packet(hex_data):
    """Decode 0x81 wrapped packet."""
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
            'channel': channel,
            'reading': reading,
            'gas_type': gas_type,
            'gas_name': GAS_TYPES.get(gas_type, f"Unknown({gas_type})"),
            'status': status,
            'radio_addr': radio_addr,
        }
    except:
        return None

def load_network_packets(log_file):
    """Load all packets from a network log with timestamps."""
    packets = []
    
    try:
        with open(log_file, 'r') as f:
            for line in f:
                match = re.match(r'\[([^\]]+)\] RX: \d+ bytes - ([0-9a-f]+)', line)
                if match:
                    timestamp_str = match.group(1)
                    hex_data = match.group(2)
                    
                    decoded = decode_packet(hex_data)
                    if decoded:
                        decoded['timestamp'] = parse_timestamp(timestamp_str)
                        decoded['timestamp_str'] = timestamp_str
                        decoded['raw_hex'] = hex_data
                        packets.append(decoded)
    except FileNotFoundError:
        pass
    
    return packets

def match_packets(direct_packets, forwarded_packets, max_latency_seconds=10):
    """
    Match packets from direct networks (15/20) with forwarded packets on network 25.
    Returns matched pairs and unmatched packets.
    """
    matches = []
    unmatched_direct = []
    unmatched_forwarded = list(forwarded_packets)
    
    for direct in direct_packets:
        if direct['timestamp'] is None:
            continue
        
        # Look for matching packet on Network 25 within time window
        best_match = None
        best_latency = None
        
        for i, forwarded in enumerate(unmatched_forwarded):
            if forwarded['timestamp'] is None:
                continue
            
            # Match criteria: same channel, similar reading, within time window
            if direct['channel'] == forwarded['channel']:
                # Calculate latency (forwarded should be after direct)
                latency = (forwarded['timestamp'] - direct['timestamp']).total_seconds()
                
                # Must be positive latency (forwarded comes after) and within window
                if 0 <= latency <= max_latency_seconds:
                    # Check if readings are similar (within 5% or 0.1 ppm)
                    reading_diff = abs(forwarded['reading'] - direct['reading'])
                    reading_threshold = max(0.1, abs(direct['reading']) * 0.05)
                    
                    if reading_diff <= reading_threshold:
                        if best_match is None or latency < best_latency:
                            best_match = i
                            best_latency = latency
        
        if best_match is not None:
            forwarded = unmatched_forwarded.pop(best_match)
            matches.append({
                'direct': direct,
                'forwarded': forwarded,
                'latency': best_latency
            })
        else:
            unmatched_direct.append(direct)
    
    return matches, unmatched_direct, unmatched_forwarded

def analyze_packet_flow(log_prefix):
    """Analyze packet flow through repeater networks."""
    
    print("="*100)
    print("REAL-TIME PACKET FLOW ANALYSIS")
    print("Tracking packets through: Network 15/20 → Repeater → Network 25")
    print("="*100)
    print()
    
    # Load packets from all networks
    print("Loading network logs...")
    net15_packets = load_network_packets(f'protocol_logs/Network_15_{log_prefix}.log')
    net20_packets = load_network_packets(f'protocol_logs/Network_20_{log_prefix}.log')
    net25_packets = load_network_packets(f'protocol_logs/Network_25_{log_prefix}.log')
    
    print(f"  Network 15: {len(net15_packets)} packets")
    print(f"  Network 20: {len(net20_packets)} packets")
    print(f"  Network 25: {len(net25_packets)} packets")
    print()
    
    if not net25_packets:
        print("⚠️  No packets found on Network 25 (primary)")
        print("   Cannot analyze repeater forwarding without primary network data")
        return
    
    # Match Network 15 packets with Network 25
    print("Matching Network 15 → Network 25...")
    matches_15_25, unmatched_15, unmatched_25_from_15 = match_packets(net15_packets, net25_packets.copy())
    
    # Match Network 20 packets with remaining Network 25 packets
    print("Matching Network 20 → Network 25...")
    matches_20_25, unmatched_20, unmatched_25_from_20 = match_packets(net20_packets, unmatched_25_from_15)
    
    print()
    print("="*100)
    print("PACKET MATCHING RESULTS")
    print("="*100)
    
    total_direct = len(net15_packets) + len(net20_packets)
    total_matched = len(matches_15_25) + len(matches_20_25)
    total_unmatched_direct = len(unmatched_15) + len(unmatched_20)
    total_unmatched_forwarded = len(unmatched_25_from_20)
    
    print(f"\nNetwork 15 → Network 25:")
    print(f"  Matched packets: {len(matches_15_25)}")
    print(f"  Unmatched on Network 15: {len(unmatched_15)} (not forwarded or outside time window)")
    
    print(f"\nNetwork 20 → Network 25:")
    print(f"  Matched packets: {len(matches_20_25)}")
    print(f"  Unmatched on Network 20: {len(unmatched_20)} (not forwarded or outside time window)")
    
    print(f"\nNetwork 25 orphaned packets: {total_unmatched_forwarded}")
    print(f"  (Packets on Network 25 not matched to 15 or 20)")
    
    if total_direct > 0:
        match_rate = (total_matched / total_direct) * 100
        print(f"\nOverall forwarding rate: {total_matched}/{total_direct} ({match_rate:.1f}%)")
    
    # Latency analysis
    if matches_15_25 or matches_20_25:
        print()
        print("="*100)
        print("REPEATER LATENCY ANALYSIS")
        print("="*100)
        
        all_matches = matches_15_25 + matches_20_25
        latencies = [m['latency'] for m in all_matches]
        
        if latencies:
            avg_latency = sum(latencies) / len(latencies)
            min_latency = min(latencies)
            max_latency = max(latencies)
            
            print(f"\nLatency Statistics (Network 15/20 → Network 25):")
            print(f"  Average: {avg_latency:.3f} seconds")
            print(f"  Minimum: {min_latency:.3f} seconds")
            print(f"  Maximum: {max_latency:.3f} seconds")
            print(f"  Sample size: {len(latencies)} matched packets")
            
            # Latency distribution
            latency_bins = defaultdict(int)
            for lat in latencies:
                if lat < 0.1:
                    latency_bins['0-100ms'] += 1
                elif lat < 0.5:
                    latency_bins['100-500ms'] += 1
                elif lat < 1.0:
                    latency_bins['0.5-1s'] += 1
                elif lat < 2.0:
                    latency_bins['1-2s'] += 1
                elif lat < 5.0:
                    latency_bins['2-5s'] += 1
                else:
                    latency_bins['5s+'] += 1
            
            print(f"\nLatency Distribution:")
            for bin_name in ['0-100ms', '100-500ms', '0.5-1s', '1-2s', '2-5s', '5s+']:
                count = latency_bins.get(bin_name, 0)
                pct = (count / len(latencies)) * 100 if latencies else 0
                bar = '█' * int(pct / 2)
                print(f"  {bin_name:10s}: {count:4d} ({pct:5.1f}%) {bar}")
    
    # Channel-by-channel analysis
    print()
    print("="*100)
    print("CHANNEL-BY-CHANNEL FORWARDING")
    print("="*100)
    
    all_matches = matches_15_25 + matches_20_25
    
    # Group by channel
    channel_stats = defaultdict(lambda: {
        'matched': 0,
        'latencies': [],
        'source_network': set(),
        'gas_type': None
    })
    
    for match in all_matches:
        ch = match['direct']['channel']
        channel_stats[ch]['matched'] += 1
        channel_stats[ch]['latencies'].append(match['latency'])
        channel_stats[ch]['gas_type'] = match['direct']['gas_name']
    
    for pkt in matches_15_25:
        channel_stats[pkt['direct']['channel']]['source_network'].add(15)
    
    for pkt in matches_20_25:
        channel_stats[pkt['direct']['channel']]['source_network'].add(20)
    
    # Add unmatched channels
    for pkt in unmatched_15:
        ch = pkt['channel']
        if ch not in channel_stats:
            channel_stats[ch]['gas_type'] = pkt['gas_name']
        channel_stats[ch]['source_network'].add(15)
    
    for pkt in unmatched_20:
        ch = pkt['channel']
        if ch not in channel_stats:
            channel_stats[ch]['gas_type'] = pkt['gas_name']
        channel_stats[ch]['source_network'].add(20)
    
    print(f"\n{'Ch':<4} {'Gas Type':<12} {'Source':<8} {'Matched':<8} {'Avg Latency':<15} {'Status'}")
    print("-"*100)
    
    for ch in sorted(channel_stats.keys()):
        stats = channel_stats[ch]
        gas = stats['gas_type'] or '?'
        source = ','.join(str(n) for n in sorted(stats['source_network']))
        matched = stats['matched']
        
        if stats['latencies']:
            avg_lat = sum(stats['latencies']) / len(stats['latencies'])
            lat_str = f"{avg_lat:.3f}s"
        else:
            lat_str = "N/A"
        
        # Determine status
        if matched == 0:
            status = "⚠️  NOT FORWARDED"
        elif matched > 0:
            status = "✓ Forwarding OK"
        else:
            status = "?"
        
        print(f"{ch:<4} {gas:<12} Net {source:<5} {matched:<8} {lat_str:<15} {status}")
    
    # Sample packet flows
    if all_matches:
        print()
        print("="*100)
        print("SAMPLE PACKET FLOWS (First 10 matched packets)")
        print("="*100)
        
        for i, match in enumerate(all_matches[:10]):
            direct = match['direct']
            forwarded = match['forwarded']
            latency = match['latency']
            
            source_net = '15' if match in matches_15_25 else '20'
            
            print(f"\nPacket {i+1}:")
            print(f"  Channel: {direct['channel']} ({direct['gas_name']})")
            print(f"  Reading: {direct['reading']:.2f} ppm")
            print(f"  Network {source_net} → Network 25 latency: {latency:.3f}s")
            print(f"  Direct timestamp:    {direct['timestamp_str']}")
            print(f"  Forwarded timestamp: {forwarded['timestamp_str']}")
            print(f"  Radio address (repeater): 0x{forwarded['radio_addr']:04X}")
    
    # Unmatched packet analysis
    if unmatched_15 or unmatched_20:
        print()
        print("="*100)
        print("PACKETS NOT FORWARDED (Sample)")
        print("="*100)
        
        all_unmatched = unmatched_15 + unmatched_20
        
        print(f"\nTotal unmatched on Networks 15/20: {len(all_unmatched)}")
        print(f"Possible reasons:")
        print(f"  - Packet sent after Network 25 radio stopped listening")
        print(f"  - Repeater not configured to forward this channel")
        print(f"  - Packet corrupted during forwarding")
        print(f"  - Timing mismatch (forwarded outside 10s window)")
        
        print(f"\nSample unmatched packets (first 10):")
        for i, pkt in enumerate(all_unmatched[:10]):
            source = '15' if pkt in unmatched_15 else '20'
            print(f"  {i+1}. Network {source} | Ch {pkt['channel']} | "
                  f"{pkt['gas_name']:8s} | {pkt['reading']:8.2f} ppm | {pkt['timestamp_str']}")
    
    # Orphaned packets on Network 25
    if unmatched_25_from_20:
        print()
        print("="*100)
        print("ORPHANED PACKETS ON NETWORK 25")
        print("="*100)
        
        print(f"\nTotal orphaned: {len(unmatched_25_from_20)}")
        print(f"These packets appeared on Network 25 but were not matched to Networks 15/20")
        print(f"Possible reasons:")
        print(f"  - Sensor on different network not being monitored")
        print(f"  - Packet sent before Network 15/20 monitoring started")
        print(f"  - Time synchronization issue")
        
        # Group by channel
        orphan_channels = defaultdict(int)
        for pkt in unmatched_25_from_20:
            orphan_channels[pkt['channel']] += 1
        
        print(f"\nOrphaned packets by channel:")
        for ch in sorted(orphan_channels.keys()):
            count = orphan_channels[ch]
            # Get gas type from first orphan packet of this channel
            gas = next((p['gas_name'] for p in unmatched_25_from_20 if p['channel'] == ch), '?')
            print(f"  Channel {ch:2d} ({gas:8s}): {count} packets")
    
    print()
    print("="*100)
    print("SUMMARY")
    print("="*100)
    print()
    
    if total_matched > 0:
        print(f"✓ Successfully matched {total_matched} packets through repeater network")
        if latencies:
            print(f"✓ Average repeater latency: {sum(latencies)/len(latencies):.3f} seconds")
    
    if total_unmatched_direct > 0:
        pct = (total_unmatched_direct / total_direct) * 100 if total_direct > 0 else 0
        print(f"⚠️  {total_unmatched_direct} packets ({pct:.1f}%) from Networks 15/20 not forwarded")
    
    if total_unmatched_forwarded > 0:
        print(f"ℹ️  {total_unmatched_forwarded} packets on Network 25 could not be matched to source")
    
    print()
    print("="*100)

if __name__ == '__main__':
    import sys
    
    # Find most recent log
    log_files = glob.glob('protocol_logs/Network_15_*.log')
    
    if not log_files:
        print("ERROR: No network log files found")
        print("Run monitor_multi_network.py first to collect data")
        sys.exit(1)
    
    log_file = log_files[-1]
    timestamp = log_file.split('_')[-1].replace('.log', '')
    
    print(f"Analyzing logs with timestamp: {timestamp}")
    print()
    
    analyze_packet_flow(timestamp)
