#!/usr/bin/env python3
"""
Configure Meshtastic devices for OI-7500 telemetry
Creates a private channel for OI-7500 data (separate from public mesh)
"""

import sys
import time

try:
    import meshtastic
    import meshtastic.serial_interface
    import meshtastic.tcp_interface
except ImportError:
    print("ERROR: meshtastic library not installed")
    print("Run: pip install meshtastic pypubsub")
    sys.exit(1)


def configure_device(port_or_ip, device_name):
    """Configure Meshtastic device for OI-7500 bridge"""
    print("="*80)
    print(f"Configuring {device_name}")
    print("="*80)
    print(f"Connecting to: {port_or_ip}")
    
    try:
        # Connect to device
        if '.' in port_or_ip:
            # TCP/WiFi
            interface = meshtastic.tcp_interface.TCPInterface(hostname=port_or_ip)
            print("✓ Connected via TCP/WiFi")
        else:
            # Serial
            interface = meshtastic.serial_interface.SerialInterface(port_or_ip)
            print("✓ Connected via Serial")
        
        time.sleep(2)
        
        print("\nCurrent configuration:")
        try:
            node = interface.getMyNodeInfo()
            print(f"  Node: {node.get('user', {}).get('longName', 'Unknown')}")
            print(f"  Hardware: {node.get('user', {}).get('hwModel', 'Unknown')}")
        except:
            print("  (Could not read node info)")
        
        print("\n" + "="*80)
        print("Setting up OI-7500 Private Channel")
        print("="*80)
        
        # Channel 0 is primary (keep for mesh connectivity)
        # Channel 1 will be our private OI-7500 channel
        
        print("\n[1/5] Setting Channel 1 for OI-7500 data...")
        interface.sendText("!ch set name OI7500", channelIndex=1)
        time.sleep(1)
        
        print("[2/5] Setting PSK (encryption key)...")
        # Use a simple PSK - change this to something secure for production
        interface.sendText("!ch set psk random", channelIndex=1)
        time.sleep(1)
        
        print("[3/5] Enabling channel...")
        interface.sendText("!ch enable", channelIndex=1)
        time.sleep(1)
        
        print("[4/5] Setting modem preset to LONG_FAST...")
        interface.sendText("!set lora.modem_preset LONG_FAST")
        time.sleep(1)
        
        print("[5/5] Saving configuration...")
        interface.sendText("!save")
        time.sleep(2)
        
        print("\n" + "="*80)
        print("✓ Configuration Complete!")
        print("="*80)
        print("\nChannel Setup:")
        print("  Channel 0: Default LongFast (public mesh)")
        print("  Channel 1: OI7500 (private, encrypted)")
        print("\n⚠️  IMPORTANT: You must set the SAME PSK on both devices!")
        print("   Run this script on both devices with the same PSK.")
        
        interface.close()
        return True
        
    except Exception as e:
        print(f"\n✗ Configuration failed: {e}")
        return False


def configure_with_custom_psk():
    """Interactive configuration with custom PSK"""
    print("="*80)
    print("OI-7500 Meshtastic Channel Setup")
    print("="*80)
    print()
    print("This will configure TWO channels:")
    print("  Channel 0: Default (public mesh) - for general mesh connectivity")
    print("  Channel 1: OI7500 (private) - for your telemetry data")
    print()
    
    # Get PSK
    print("Enter a Pre-Shared Key (PSK) for encryption:")
    print("  - Use 'random' to generate random key")
    print("  - Or enter 'base64:...' for specific key")
    print("  - Or enter passphrase (will be hashed)")
    psk = input("PSK [random]: ").strip() or "random"
    
    # Device 1 - Heltec V3
    print("\n" + "="*80)
    print("DEVICE 1: Heltec V3 (COM16)")
    print("="*80)
    input("Press Enter to configure...")
    
    try:
        if '.' in "COM16":
            interface1 = meshtastic.tcp_interface.TCPInterface(hostname="COM16")
        else:
            interface1 = meshtastic.serial_interface.SerialInterface("COM16")
        
        time.sleep(2)
        
        print("Setting up channels...")
        interface1.sendText(f"!ch set name OI7500", channelIndex=1)
        time.sleep(1)
        interface1.sendText(f"!ch set psk {psk}", channelIndex=1)
        time.sleep(1)
        interface1.sendText("!ch enable", channelIndex=1)
        time.sleep(1)
        interface1.sendText("!set lora.modem_preset LONG_FAST")
        time.sleep(1)
        interface1.sendText("!save")
        time.sleep(2)
        
        print("✓ Device 1 configured")
        interface1.close()
        
    except Exception as e:
        print(f"✗ Device 1 failed: {e}")
        return False
    
    # Device 2 - Roof Node
    print("\n" + "="*80)
    print("DEVICE 2: Roof Node (10.20.0.172)")
    print("="*80)
    input("Press Enter to configure...")
    
    try:
        interface2 = meshtastic.tcp_interface.TCPInterface(hostname="10.20.0.172")
        time.sleep(2)
        
        print("Setting up channels...")
        interface2.sendText(f"!ch set name OI7500", channelIndex=1)
        time.sleep(1)
        interface2.sendText(f"!ch set psk {psk}", channelIndex=1)
        time.sleep(1)
        interface2.sendText("!ch enable", channelIndex=1)
        time.sleep(1)
        interface2.sendText("!set lora.modem_preset LONG_FAST")
        time.sleep(1)
        interface2.sendText("!save")
        time.sleep(2)
        
        print("✓ Device 2 configured")
        interface2.close()
        
    except Exception as e:
        print(f"✗ Device 2 failed: {e}")
        return False
    
    print("\n" + "="*80)
    print("✓ BOTH DEVICES CONFIGURED SUCCESSFULLY!")
    print("="*80)
    print("\nBoth devices now have:")
    print("  Channel 0: Default (public mesh)")
    print("  Channel 1: OI7500 (private, same PSK)")
    print("\nYour bridge will use Channel 1 for private telemetry.")
    print("Channel 0 keeps you connected to the public mesh network.")
    print()
    
    return True


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--auto":
        # Auto mode - configure both with random PSK
        print("Auto-configuring both devices with random PSK...")
        configure_with_custom_psk()
    else:
        # Manual mode
        configure_with_custom_psk()
