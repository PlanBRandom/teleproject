#!/usr/bin/env python3
"""
Quick test script to verify Meshtastic device connection
"""

import sys
import time

try:
    import meshtastic
    import meshtastic.serial_interface
except ImportError:
    print("ERROR: meshtastic library not installed")
    print("Run: pip install meshtastic pypubsub")
    sys.exit(1)

def test_meshtastic(port):
    """Test connection to Meshtastic device"""
    print("="*80)
    print("Meshtastic Device Test")
    print("="*80)
    print(f"Connecting to: {port}")
    print("Please wait...")
    print()
    
    try:
        # Detect connection type (IP address vs COM port)
        if '.' in port or ':' in port:
            # TCP/WiFi connection
            import meshtastic.tcp_interface
            interface = meshtastic.tcp_interface.TCPInterface(hostname=port)
            print("✓ TCP/WiFi connection established")
        else:
            # Serial/USB connection
            interface = meshtastic.serial_interface.SerialInterface(port)
            print("✓ Serial connection established")
        
        # Wait for device to respond
        time.sleep(2)
        
        # Get node info
        try:
            node_info = interface.getMyNodeInfo()
            print("\n" + "="*80)
            print("Device Information:")
            print("="*80)
            
            # Print node details
            if 'user' in node_info:
                user = node_info['user']
                print(f"Long Name: {user.get('longName', 'Unknown')}")
                print(f"Short Name: {user.get('shortName', 'Unknown')}")
                print(f"Hardware: {user.get('hwModel', 'Unknown')}")
                print(f"ID: {user.get('id', 'Unknown')}")
            
            print(f"\nFull Info: {node_info}")
            
        except Exception as e:
            print(f"⚠️  Could not get node info: {e}")
            print("Device connected but info not available yet")
        
        # Get node database
        try:
            print("\n" + "="*80)
            print("Checking mesh network...")
            print("="*80)
            
            nodes = interface.nodes
            print(f"Known nodes in mesh: {len(nodes)}")
            
            for node_id, node in nodes.items():
                user = node.get('user', {})
                print(f"  - {user.get('longName', 'Unknown')} ({user.get('shortName', '???')})")
        except:
            pass
        
        # Close connection
        interface.close()
        
        print("\n" + "="*80)
        print("✓ Test SUCCESSFUL - Device is ready!")
        print("="*80)
        print("\nYou can now run:")
        print("  python meshtastic_bridge.py")
        print("  python meshtastic_gateway.py")
        print()
        
        return True
        
    except Exception as e:
        print("\n" + "="*80)
        print("✗ Test FAILED")
        print("="*80)
        print(f"Error: {e}")
        print()
        print("Troubleshooting:")
        print("1. Check device is plugged into correct COM port")
        print("2. Close any other apps using the device (Meshtastic app, etc)")
        print("3. Try unplugging and replugging the device")
        print("4. Verify port with: python -m serial.tools.list_ports")
        print()
        
        return False


if __name__ == "__main__":
    import json
    
    # Try to load config
    try:
        with open('meshtastic_config.json', 'r') as f:
            config = json.load(f)
        port = config['edge_node']['meshtastic_port']
    except:
        port = "COM16"  # Default
    
    # Allow override from command line
    if len(sys.argv) > 1:
        port = sys.argv[1]
    
    success = test_meshtastic(port)
    sys.exit(0 if success else 1)
