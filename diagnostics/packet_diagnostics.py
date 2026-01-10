"""
Packet Diagnostics Tool - Query packet database for F8/F14 troubleshooting
"""

import sys
import os
import argparse

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.packet_database import PacketDatabase
from datetime import datetime, timedelta

def print_header(text):
    """Print section header"""
    print("\n" + "=" * 80)
    print(f"  {text}")
    print("=" * 80)

def show_fault_history(db, fault_code=None, hours=24):
    """Show fault event history"""
    if fault_code:
        print_header(f"Fault F{fault_code} History (Last {hours} hours)")
    else:
        print_header(f"All Fault History (Last {hours} hours)")
    
    faults = db.get_fault_history(fault_code, hours)
    
    if not faults:
        print("  No faults detected")
        return
    
    print(f"\n{'Timestamp':<20} {'Network':<12} {'Ch':<4} {'Fault':<6} {'Description':<40} {'Count':<6}")
    print("-" * 100)
    
    for fault in faults:
        timestamp, network, channel, code, name, addr, first, last, count = fault
        timestamp_fmt = datetime.fromisoformat(timestamp).strftime("%Y-%m-%d %H:%M:%S")
        print(f"{timestamp_fmt:<20} {network:<12} {channel:<4} F{code:<5} {name:<40} {count:<6}")

def show_duplicate_addresses(db):
    """Show F8 duplicate address conflicts"""
    print_header("F8 Duplicate Address Detection")
    
    duplicates = db.get_duplicate_addresses()
    
    if not duplicates:
        print("  ✓ No duplicate addresses detected in last hour")
        return
    
    print(f"\n{'Address':<10} {'Channel Count':<15} {'Channels':<30} {'Last Seen':<20}")
    print("-" * 80)
    
    for dup in duplicates:
        addr, count, channels, last_seen = dup
        timestamp_fmt = datetime.fromisoformat(last_seen).strftime("%Y-%m-%d %H:%M:%S")
        print(f"⚠ {addr:<10} {count:<15} {channels:<30} {timestamp_fmt:<20}")
    
    print("\n⚠ ISSUE: Multiple channels using same transmitter address!")
    print("  Solution: Use F8 diagnostic command to change sensor addresses")

def show_channel_history(db, channel, limit=20):
    """Show packet history for a specific channel"""
    print_header(f"Channel {channel} History (Last {limit} packets)")
    
    packets = db.get_packets_by_channel(channel, limit)
    
    if not packets:
        print(f"  No packets found for channel {channel}")
        return
    
    print(f"\n{'Timestamp':<20} {'Network':<12} {'Reading':<12} {'Gas':<8} {'Battery':<10} {'Fault':<40} {'RSSI':<6}")
    print("-" * 120)
    
    for pkt in packets:
        timestamp, network, reading, gas, battery, fault_code, fault_name, addr, rssi = pkt
        timestamp_fmt = datetime.fromisoformat(timestamp).strftime("%Y-%m-%d %H:%M:%S")
        fault_str = f"F{fault_code}: {fault_name}" if fault_code != 0 else "None"
        rssi_str = str(rssi) if rssi else "N/A"
        print(f"{timestamp_fmt:<20} {network:<12} {reading:<12.2f} {gas:<8} {battery:<10.1f} {fault_str:<40} {rssi_str:<6}")

def show_network_diagnostics(db, network, hours=1):
    """Show network diagnostic information"""
    print_header(f"Network '{network}' Diagnostics (Last {hours} hour)")
    
    diag = db.get_network_diagnostics(network, hours)
    
    if not diag or diag[0] == 0:
        print(f"  No packets received on network '{network}'")
        return
    
    total, channels, addresses, avg_rssi, faults, first, last = diag
    
    print(f"\n  Total Packets:      {total}")
    print(f"  Unique Channels:    {channels}")
    print(f"  Unique Addresses:   {addresses}")
    print(f"  Average RSSI:       {avg_rssi:.1f} dBm" if avg_rssi else "  Average RSSI:       N/A")
    print(f"  Fault Count:        {faults} ({faults/total*100:.1f}%)" if total > 0 else "  Fault Count:        0")
    print(f"  First Packet:       {datetime.fromisoformat(first).strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Last Packet:        {datetime.fromisoformat(last).strftime('%Y-%m-%d %H:%M:%S')}")
    
    duration = datetime.fromisoformat(last) - datetime.fromisoformat(first)
    if duration.total_seconds() > 0:
        rate = total / duration.total_seconds()
        print(f"  Packet Rate:        {rate:.2f} packets/sec")

def show_raw_packets(db, network=None, limit=10):
    """Show recent raw packet hex"""
    if network:
        print_header(f"Recent Raw Packets - {network} (Last {limit})")
    else:
        print_header(f"Recent Raw Packets - All Networks (Last {limit})")
    
    packets = db.get_recent_raw_packets(network, limit)
    
    if not packets:
        print("  No raw packets found")
        return
    
    print(f"\n{'Timestamp':<20} {'Network':<12} {'Length':<8} {'Frame':<10} {'RSSI':<6} {'Raw Hex':<60}")
    print("-" * 120)
    
    for pkt in packets:
        timestamp, net, raw_hex, length, frame_type, rssi = pkt
        timestamp_fmt = datetime.fromisoformat(timestamp).strftime("%Y-%m-%d %H:%M:%S")
        frame = frame_type if frame_type else "N/A"
        rssi_str = str(rssi) if rssi else "N/A"
        hex_preview = raw_hex[:60] + "..." if len(raw_hex) > 60 else raw_hex
        print(f"{timestamp_fmt:<20} {net:<12} {length:<8} {frame:<10} {rssi_str:<6} {hex_preview}")

def export_csv(db, filename, hours=24):
    """Export packets to CSV"""
    print_header(f"Exporting Data to CSV (Last {hours} hours)")
    
    count = db.export_packets_csv(filename, hours)
    print(f"\n  ✓ Exported {count} packets to: {filename}")

def main():
    parser = argparse.ArgumentParser(description="OI-7500 Packet Database Diagnostics")
    parser.add_argument('--db', default='protocol_logs/packets.db', help='Database file path')
    
    # Query options
    parser.add_argument('--faults', action='store_true', help='Show all fault history')
    parser.add_argument('--f8', action='store_true', help='Check for F8 duplicate addresses')
    parser.add_argument('--f14', action='store_true', help='Show F14 primary monitor faults')
    parser.add_argument('--channel', type=int, help='Show history for specific channel')
    parser.add_argument('--network', help='Show diagnostics for specific network')
    parser.add_argument('--raw', action='store_true', help='Show recent raw packet hex')
    parser.add_argument('--export', help='Export to CSV file')
    
    # Options
    parser.add_argument('--hours', type=int, default=24, help='Hours of history to query (default: 24)')
    parser.add_argument('--limit', type=int, default=20, help='Limit number of results (default: 20)')
    
    args = parser.parse_args()
    
    # Open database
    try:
        db = PacketDatabase(args.db)
    except Exception as e:
        print(f"✗ Error opening database: {e}")
        return 1
    
    # Execute queries
    try:
        if args.f8:
            show_duplicate_addresses(db)
        
        if args.f14:
            show_fault_history(db, fault_code=14, hours=args.hours)
        
        if args.faults:
            show_fault_history(db, hours=args.hours)
        
        if args.channel:
            show_channel_history(db, args.channel, args.limit)
        
        if args.network:
            show_network_diagnostics(db, args.network, args.hours)
        
        if args.raw:
            show_raw_packets(db, args.network, args.limit)
        
        if args.export:
            export_csv(db, args.export, args.hours)
        
        # If no specific query, show summary
        if not any([args.faults, args.f8, args.f14, args.channel, args.network, args.raw, args.export]):
            print_header("OI-7500 Packet Database Summary")
            print("\nAvailable commands:")
            print("  --faults              Show all fault history")
            print("  --f8                  Check for duplicate address conflicts")
            print("  --f14                 Show F14 primary monitor faults")
            print("  --channel N           Show history for channel N")
            print("  --network NAME        Show diagnostics for network")
            print("  --raw                 Show recent raw packet hex")
            print("  --export file.csv     Export packets to CSV")
            print("\nOptions:")
            print("  --hours N             Hours of history (default: 24)")
            print("  --limit N             Limit results (default: 20)")
            print("\nExamples:")
            print("  python packet_diagnostics.py --f8")
            print("  python packet_diagnostics.py --channel 16 --limit 50")
            print("  python packet_diagnostics.py --network Network_25 --hours 1")
            print("  python packet_diagnostics.py --raw --network Network_25 --limit 5")
    
    finally:
        db.close()
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
