#!/usr/bin/env python3
"""
Read and display Channel 1 PSK from a configured Meshtastic node
Use this to get the encryption key for configuring other devices (like iPhone app)
"""
import sys
import base64
import meshtastic.serial_interface
import meshtastic.tcp_interface

def get_psk(port):
    """Read PSK from Channel 1"""
    
    print(f"\n{'='*80}")
    print(f"Reading Channel 1 PSK from: {port}")
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
    print(f"[OK] Connected to: {node_info['user']['longName']} ({node_info['user']['id']})")
    
    # Get channels
    channels = interface.localNode.channels
    
    print(f"\n{'='*80}")
    print("ALL CHANNELS:")
    print(f"{'='*80}")
    
    for i, ch in enumerate(channels):
        if ch.role != 0:  # Skip disabled channels
            ch_name = ch.settings.name if ch.settings.name else "(unnamed)"
            print(f"\nChannel {i}: {ch_name}")
            print(f"  Role: {ch.role}")
            
            if ch.settings.psk:
                # Get the PSK bytes
                psk_bytes = ch.settings.psk
                
                # Convert to base64 (for iPhone app)
                psk_base64 = base64.b64encode(psk_bytes).decode('ascii')
                
                # Convert to hex
                psk_hex = psk_bytes.hex()
                
                print(f"  PSK (base64): {psk_base64}")
                print(f"  PSK (hex):    {psk_hex}")
                print(f"  PSK length:   {len(psk_bytes)} bytes ({len(psk_bytes)*8} bits)")
            else:
                print(f"  PSK: None (default/public channel)")
            
            print(f"  Uplink:   {ch.settings.uplink_enabled}")
            print(f"  Downlink: {ch.settings.downlink_enabled}")
    
    # Special focus on Channel 1
    if len(channels) > 1 and channels[1].role != 0:
        ch1 = channels[1]
        ch1_name = ch1.settings.name if ch1.settings.name else "(unnamed)"
        
        print(f"\n{'='*80}")
        print(f"CHANNEL 1 - {ch1_name}")
        print(f"{'='*80}")
        
        if ch1.settings.psk:
            psk_bytes = ch1.settings.psk
            psk_base64 = base64.b64encode(psk_bytes).decode('ascii')
            psk_hex = psk_bytes.hex()
            
            print(f"\n[IMPORTANT] Use this key to configure other devices:\n")
            print(f"  Base64 (for iPhone app): {psk_base64}")
            print(f"  Hex format:              {psk_hex}")
            print(f"\n[INSTRUCTIONS FOR iPHONE]")
            print(f"  1. Open Meshtastic app")
            print(f"  2. Go to Channels")
            print(f"  3. Add new channel or edit Channel 1")
            print(f"  4. Name: OI7500")
            print(f"  5. Key Size: {len(psk_bytes)*8}-bit")
            print(f"  6. Key: {psk_base64}")
            print(f"  7. Enable Uplink and Downlink")
            print(f"  8. Save")
        else:
            print(f"\n[WARN] Channel 1 has no PSK configured!")
    else:
        print(f"\n[WARN] Channel 1 not found or disabled!")
    
    interface.close()
    
    print(f"\n{'='*80}\n")
    return True

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python get_channel_psk.py <PORT>")
        print("Example: python get_channel_psk.py COM16")
        print("         python get_channel_psk.py 10.20.0.172")
        print("\nThis will read Channel 1 PSK from your configured node")
        print("so you can copy it to your iPhone Meshtastic app")
        sys.exit(1)
    
    port = sys.argv[1]
    
    try:
        get_psk(port)
    except KeyboardInterrupt:
        print("\n\nCancelled by user")
    except Exception as e:
        print(f"\n[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()
