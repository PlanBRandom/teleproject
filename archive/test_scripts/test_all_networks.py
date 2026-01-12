"""
Test all three networks simultaneously to see what each is receiving
"""
import json
import time
from threading import Thread
from pipeline.radio_receiver import RadioReceiver, RadioMessage

results = {
    'COM7': {'name': 'Network 15 (Direct)', 'packets': []},
    'COM11': {'name': 'Network 25 (Repeated)', 'packets': []},
    'COM12': {'name': 'Network 20 (Direct)', 'packets': []}
}

def monitor_port(port, baudrate, duration=60):
    """Monitor a single port"""
    try:
        receiver = RadioReceiver(port, baudrate=baudrate, api_mode=True, api_type='rm024')
        
        def callback(msg: RadioMessage):
            results[port]['packets'].append({
                'channel': msg.channel,
                'protocol': msg.protocol,
                'has_reading': msg.reading is not None,
                'has_battery': msg.battery_voltage is not None,
                'has_gas': msg.gas_type is not None,
                'rssi': msg.rssi
            })
        
        if not receiver.connect():
            print(f"[{port}] Failed to connect")
            return
        
        receiver.register_callback(callback)
        receiver.start()
        print(f"[{port}] Started monitoring {results[port]['name']}")
        
        time.sleep(duration)
        
        receiver.stop()
        print(f"[{port}] Stopped - received {len(results[port]['packets'])} packets")
        
    except Exception as e:
        print(f"[{port}] Error: {e}")

# Load config
with open('config.json', 'r') as f:
    config = json.load(f)

print("="*80)
print("Testing All Networks Simultaneously - 2 Minute Test")
print("="*80)
print()

# Start monitoring threads
threads = []
for network in ['Network_15', 'Network_20', 'Network_25']:
    port = config['radios'][network]['port']
    baudrate = config['radios'][network]['baudrate']
    t = Thread(target=monitor_port, args=(port, baudrate, 120))
    t.start()
    threads.append(t)

# Wait for completion
for t in threads:
    t.join()

# Display results
print()
print("="*80)
print("RESULTS - Packet Analysis")
print("="*80)

for port in ['COM7', 'COM11', 'COM12']:
    info = results[port]
    print(f"\n{port} - {info['name']}")
    print("-"*80)
    print(f"Total Packets: {len(info['packets'])}")
    
    if info['packets']:
        # Check completeness
        complete = sum(1 for p in info['packets'] if p['has_reading'] and p['has_battery'] and p['has_gas'])
        incomplete = len(info['packets']) - complete
        
        print(f"Complete Packets: {complete} ({100*complete/len(info['packets']):.1f}%)")
        print(f"Incomplete Packets: {incomplete} ({100*incomplete/len(info['packets']):.1f}%)")
        
        # Show unique channels
        channels = set(p['channel'] for p in info['packets'])
        print(f"Channels Seen: {sorted(channels)}")
        
        # Show protocols
        protocols = set(p['protocol'] for p in info['packets'])
        print(f"Protocols: {sorted(protocols)}")
        
        # Show sample packet structure
        sample = info['packets'][0]
        print(f"Sample Packet Structure:")
        print(f"  - Has Reading: {sample['has_reading']}")
        print(f"  - Has Battery: {sample['has_battery']}")
        print(f"  - Has Gas Type: {sample['has_gas']}")
        print(f"  - RSSI: {sample['rssi']}%")
    else:
        print("NO PACKETS RECEIVED")

print()
print("="*80)
print("CONCLUSION:")
print("="*80)
print("If COM7/COM12 show incomplete packets, they're receiving truncated frames.")
print("If COM11 shows complete packets, it's working as expected.")
print("If COM7/COM12 show different channels than COM11, they're direct sensors.")
print("="*80)
