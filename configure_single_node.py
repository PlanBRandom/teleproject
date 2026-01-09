#!/usr/bin/env python3
"""
Configure a single Meshtastic node with OI7500 channel
"""
import sys
import meshtastic.serial_interface
import meshtastic.tcp_interface
from pubsub import pub

def configure_node(port, psk="everythingisfine"):
    """Configure a single node with Channel 1 (OI7500)"""
    
    print(f"\n{'='*80}")
    print(f"Configuring Meshtastic Node: {port}")
    print(f"{'='*80}\n")
    
    # Connect to device
    print(f"Connecting to {port}...")
    if ":" in str(port) or "." in str(port):
        # TCP/IP connection
        interface = meshtastic.tcp_interface.TCPInterface(hostname=port)
    else:
        # Serial connection
        interface = meshtastic.serial_interface.SerialInterface(port)
    
    # Get node info
    node_info = interface.getMyNodeInfo()
    print(f"\n[OK] Connected to: {node_info['user']['longName']} ({node_info['user']['shortName']})")
    print(f"  ID: {node_info['user']['id']}")
    print(f"  Hardware: {node_info['user']['hwModel']}")
    if 'deviceMetrics' in node_info:
        print(f"  Battery: {node_info['deviceMetrics'].get('batteryLevel', 'N/A')}%")
    
    # Show current channels
    print(f"\nCurrent channels:")
    channels = interface.localNode.channels
    for i, ch in enumerate(channels):
        if ch.role != 0:  # Skip disabled channels
            ch_name = ch.settings.name if ch.settings.name else "(unnamed)"
            has_psk = "Yes" if ch.settings.psk else "No"
            print(f"  Channel {i}: {ch_name} - PSK: {has_psk}")
    
    # Check if Channel 1 already exists and is configured
    if len(channels) > 1 and channels[1].role != 0:
        ch1_name = channels[1].settings.name
        if ch1_name == "OI7500" and channels[1].settings.psk:
            print(f"\n[OK] Channel 1 (OI7500) already configured!")
            print(f"  Uplink: {channels[1].settings.uplink_enabled}")
            print(f"  Downlink: {channels[1].settings.downlink_enabled}")
            interface.close()
            return True
    
    # Configure Channel 1
    print(f"\nConfiguring Channel 1 (OI7500)...")
    print(f"  PSK: {psk}")
    
    # Get channel 1
    ch1 = interface.localNode.getChannelByChannelIndex(1)
    
    # Set channel settings
    ch1.settings.name = "OI7500"
    ch1.settings.psk = psk.encode('utf-8')
    ch1.settings.uplink_enabled = True
    ch1.settings.downlink_enabled = True
    ch1.role = 1  # SECONDARY
    
    # Write the channel back
    interface.localNode.writeChannel(1)
    
    print(f"[OK] Channel 1 configured!")
    print(f"\nWaiting for device to apply settings...")
    import time
    time.sleep(3)
    
    # Verify configuration
    interface = meshtastic.serial_interface.SerialInterface(port) if "COM" in str(port) else meshtastic.tcp_interface.TCPInterface(hostname=port)
    channels = interface.localNode.channels
    
    print(f"\n{'='*80}")
    print(f"FINAL CONFIGURATION")
    print(f"{'='*80}")
    for i, ch in enumerate(channels):
        if ch.role != 0:
            ch_name = ch.settings.name if ch.settings.name else "(unnamed)"
            has_psk = "[OK]" if ch.settings.psk else "[NO]"
            uplink = "[OK]" if ch.settings.uplink_enabled else "[NO]"
            downlink = "[OK]" if ch.settings.downlink_enabled else "[NO]"
            print(f"  Channel {i}: {ch_name}")
            print(f"    PSK: {has_psk} | Uplink: {uplink} | Downlink: {downlink}")
    
    interface.close()
    
    print(f"\n{'='*80}")
    print(f"[OK] CONFIGURATION COMPLETE!")
    print(f"{'='*80}\n")
    
    return True

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python configure_single_node.py <PORT> [PSK]")
        print("Example: python configure_single_node.py COM19 everythingisfine")
        sys.exit(1)
    
    port = sys.argv[1]
    psk = sys.argv[2] if len(sys.argv) > 2 else "everythingisfine"
    
    try:
        configure_node(port, psk)
    except KeyboardInterrupt:
        print("\n\nConfiguration cancelled by user")
    except Exception as e:
        print(f"\n[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()
