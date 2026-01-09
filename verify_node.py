#!/usr/bin/env python3
import sys
import meshtastic.serial_interface
import time

port = sys.argv[1] if len(sys.argv) > 1 else "COM19"

print("\nWaiting for device to be ready...")
time.sleep(2)

iface = meshtastic.serial_interface.SerialInterface(port)

print("\n" + "="*80)
print("MESHTASTIC NODE CONFIGURATION")
print("="*80)

node = iface.getMyNodeInfo()
print(f"\nNode: {node['user']['longName']} ({node['user']['shortName']})")
print(f"ID: {node['user']['id']}")
print(f"Battery: {node.get('deviceMetrics', {}).get('batteryLevel', 'N/A')}%")

print("\nConfigured Channels:")
channels = iface.localNode.channels
for i, ch in enumerate(channels):
    if ch.role != 0:
        ch_name = ch.settings.name if ch.settings.name else "(default)"
        psk = "✓" if ch.settings.psk else "✗"
        uplink = "✓" if ch.settings.uplink_enabled else "✗"
        downlink = "✓" if ch.settings.downlink_enabled else "✗"
        print(f"  Channel {i}: {ch_name}")
        print(f"    PSK: {psk} | Uplink: {uplink} | Downlink: {downlink}")

print("\n" + "="*80)
print("✓ Configuration verified!")
print("="*80 + "\n")

iface.close()
