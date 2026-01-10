"""Test radio_receiver parsing on logged hex data"""
import sys
sys.path.insert(0, 'pipeline')

# Mock serial to avoid import error
class MockSerial:
    pass
sys.modules['serial'] = MockSerial()

from radio_receiver import RadioReceiver

# Create receiver in transparent mode (no API framing)
# Don't actually connect to port
receiver = RadioReceiver.__new__(RadioReceiver)
receiver.api_mode = False
receiver.api_type = None
receiver.buffer = bytearray()
receiver.callbacks = []

# Sample hex packets from the log
test_packets = [
    "81110016e0882b00078100000000002303002ec8ae905f41",
    "81110015e0882b0006810000000010178600b4c8b1795731",
    "81120015e08849000487000000000018fde80008c8b1755fdd",
]

def test_packet(hex_data):
    print(f"\nTesting packet: {hex_data}")
    print(f"Length: {len(hex_data)//2} bytes")
    
    data = bytearray.fromhex(hex_data)
    
    # Show first few bytes
    print(f"First bytes: {' '.join(f'{b:02x}' for b in data[:8])}")
    print(f"  [0-1]: Address? = 0x{data[0]:02x}{data[1]:02x} = {(data[0] << 8) | data[1]}")
    print(f"  [2]: Protocol/Channel? = 0x{data[2]:02x} = {data[2]}")
    
    # Add to receiver buffer
    receiver.buffer = data
    
    # Try to process
    messages = []
    def callback(msg):
        messages.append(msg)
    
    receiver.callbacks = [callback]
    receiver._process_transparent()
    
    if messages:
        print(f"✓ Parsed successfully!")
        for msg in messages:
            print(f"  Protocol: {msg.protocol}")
            print(f"  Address: {msg.transmitter_address}")
            print(f"  Reading: {msg.reading}")
            print(f"  Gas: {msg.gas_type}")
            print(f"  Battery: {msg.battery_voltage}V")
    else:
        print(f"✗ Failed to parse")

for packet in test_packets:
    test_packet(packet)
