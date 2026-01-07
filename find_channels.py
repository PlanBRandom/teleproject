import re
from collections import defaultdict

def find_channels(log_file):
    """Find all channel numbers in the captured packets."""
    channels = defaultdict(int)
    
    with open(log_file, 'r') as f:
        for line in f:
            match = re.search(r'RX: \d+ bytes - (81[0-9a-f]+)', line)
            if match:
                hex_data = match.group(1)
                # Check if we have enough bytes
                if len(hex_data) >= 10:
                    try:
                        # Byte 4 of payload = position 8-9 in hex string (after 81, len, 00)
                        ch = int(hex_data[8:10], 16)
                        channels[ch] += 1
                    except:
                        pass
    
    return dict(sorted(channels.items()))

if __name__ == '__main__':
    log_file = 'protocol_logs/radio_20260106_181937.log'
    channels = find_channels(log_file)
    
    print(f"\nChannel Distribution (all {sum(channels.values())} packets):")
    for ch, count in channels.items():
        print(f"  Channel {ch}: {count} packets")
    print(f"\nTotal unique channels: {len(channels)}")
    print(f"\nChannels present: {list(channels.keys())}")
