# Viewing OI-7500 Data Through Meshtastic Mesh

## Overview

Your OI-7500 sensor data is being forwarded through the Meshtastic mesh network on:
- **Channel 1: "OI7500"**
- **Encryption**: PSK = `everythingisfine`
- **Data Format**: Binary encoded (15 bytes per reading)
- **Mesh Range**: 5-10 miles with LoRa

## Quick Setup

### 1. Configure Your Phone's Meshtastic Device

You need to add Channel 1 (OI7500) to your Meshtastic device to receive the telemetry.

#### Using Meshtastic App (Android/iPhone):

1. **Open Meshtastic App**
2. Connect to your device (Bluetooth)
3. Go to **Settings** → **Radio Config** → **Channels**
4. **Add New Channel** (Channel 1):
   - **Name**: `OI7500`
   - **PSK**: `everythingisfine`
   - **Role**: SECONDARY
   - **Enable Uplink**: ✓
   - **Enable Downlink**: ✓
5. **Save** and wait for device to reboot

#### Using Python Script (If device is connected to PC):

```powershell
# Connect your device via USB first
python verify_node.py COM19  # Replace COM19 with your device's port
```

Or configure manually:
```powershell
python configure_single_node.py COM19 everythingisfine
```

### 2. View Telemetry Data

Once Channel 1 is configured, you have several options:

---

## Option 1: Meshtastic App (Easiest)

**Problem**: The Meshtastic app shows binary messages but doesn't automatically decode them.

You'll see messages on Channel 1 that look like:
```
PRIVATE_APP: [15 bytes of binary data]
```

**To view the decoded data**, you need a companion app or decoder.

---

## Option 2: Create a Meshtastic Decoder App

I can create a simple Python script that runs on your phone (with Termux) or on a device connected to a Meshtastic node:

<function_calls>
<invoke name="create_file">
<parameter name="content">#!/usr/bin/env python3
"""
Meshtastic OI-7500 Telemetry Viewer
Listens to mesh network and decodes OI-7500 binary telemetry
"""
import sys
import struct
import meshtastic
import meshtastic.serial_interface
import meshtastic.tcp_interface
from datetime import datetime
from pubsub import pub

# Gas type lookup
GAS_TYPES = {
    0: "LEL", 1: "O2", 2: "CO", 3: "H2S", 4: "SO2", 5: "NO", 6: "NO2",
    7: "NH3", 8: "Cl2", 9: "ClO2", 10: "HCl", 11: "HCN", 12: "PH3",
    13: "CO2", 14: "COCl2", 15: "ETO", 16: "H2", 17: "HF", 18: "O3",
    19: "CH4", 20: "C3H8", 21: "AsH3", 22: "B2H6", 23: "GeH4",
    24: "SiH4", 25: "F2", 26: "VOC"
}

# Fault codes
FAULT_CODES = {
    0: "No Fault", 1: "Low Battery", 2: "Sensor Fault", 3: "Calibration Error",
    4: "Out of Range", 5: "Warm Up", 6: "Inhibit", 7: "Span Fault",
    8: "Zero Fault", 9: "Communication Error", 10: "Hardware Fault"
}

def decode_telemetry(payload):
    """Decode 15-byte OI-7500 telemetry packet"""
    if len(payload) < 15:
        return None
    
    try:
        # Unpack binary data
        channel = payload[0]
        reading_raw = struct.unpack('<h', payload[1:3])[0]  # Signed 16-bit
        gas_type = payload[3]
        battery = payload[4] * 0.1
        fault_code = payload[5]
        timestamp = struct.unpack('<I', payload[6:10])[0]  # Unix timestamp
        sensor_info = payload[10]
        precision = payload[11]
        
        # Calculate actual reading
        actual_reading = reading_raw / (10 ** precision)
        
        return {
            'channel': channel,
            'reading': actual_reading,
            'gas_type': GAS_TYPES.get(gas_type, f"Unknown({gas_type})"),
            'battery': round(battery, 1),
            'fault_code': fault_code,
            'fault': FAULT_CODES.get(fault_code, f"Unknown({fault_code})"),
            'timestamp': datetime.fromtimestamp(timestamp).isoformat() if timestamp > 0 else 'N/A',
            'mesh_time': datetime.now().isoformat()
        }
    except Exception as e:
        print(f"Decode error: {e}")
        return None

def on_receive(packet, interface):
    """Handle incoming mesh packet"""
    try:
        # Check if it's a PRIVATE_APP packet on Channel 1
        if 'decoded' not in packet:
            return
        
        decoded = packet['decoded']
        
        # Only process PRIVATE_APP messages (our telemetry)
        if decoded.get('portnum') != 'PRIVATE_APP':
            return
        
        payload = decoded.get('payload')
        if not payload or len(payload) < 15:
            return
        
        # Decode telemetry
        data = decode_telemetry(payload)
        if not data:
            return
        
        # Get mesh info
        from_id = packet.get('fromId', 'unknown')
        from_node = packet.get('from', 0)
        rssi = packet.get('rxRssi', 'N/A')
        snr = packet.get('rxSnr', 'N/A')
        hop_limit = packet.get('hopLimit', 'N/A')
        
        # Display
        print("\n" + "="*70)
        print(f"📡 MESH TELEMETRY RECEIVED")
        print("="*70)
        print(f"From Node: {from_id} (ID: {from_node})")
        print(f"Signal: RSSI {rssi} dBm, SNR {snr} dB, Hops: {hop_limit}")
        print(f"Received: {data['mesh_time']}")
        print("-"*70)
        print(f"Channel {data['channel']:02d} | {data['gas_type']}")
        print(f"Reading: {data['reading']} | Battery: {data['battery']}V")
        print(f"Status: {data['fault']}")
        print(f"Sensor Time: {data['timestamp']}")
        print("="*70)
        
    except Exception as e:
        print(f"Error processing packet: {e}")

def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  Serial: python mesh_viewer.py COM16")
        print("  TCP/IP: python mesh_viewer.py 192.168.1.100")
        sys.exit(1)
    
    device = sys.argv[1]
    
    print("="*70)
    print("OI-7500 Meshtastic Telemetry Viewer")
    print("="*70)
    print(f"Connecting to: {device}")
    print("Listening on Channel 1 (OI7500)...")
    print("Press Ctrl+C to stop\n")
    
    # Connect to Meshtastic device
    try:
        if ':' in device or '.' in device:
            # TCP connection
            interface = meshtastic.tcp_interface.TCPInterface(hostname=device)
        else:
            # Serial connection
            interface = meshtastic.serial_interface.SerialInterface(device)
        
        node_info = interface.getMyNodeInfo()
        print(f"✓ Connected to: {node_info['user']['longName']}")
        print(f"  ID: {node_info['user']['id']}")
        print(f"  Listening for OI-7500 telemetry...\n")
        
        # Subscribe to incoming packets
        pub.subscribe(on_receive, "meshtastic.receive")
        
        # Keep running
        try:
            while True:
                import time
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n\nStopping...")
            
    except Exception as e:
        print(f"✗ Error: {e}")
        sys.exit(1)
    finally:
        interface.close()
        print("Disconnected")

if __name__ == "__main__":
    main()
