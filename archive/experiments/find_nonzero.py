"""Find packets with non-zero readings"""
import struct
import sys
sys.path.insert(0, '.')

# Import parse function
exec(open('analyze_radio_logs.py').read().split('if __name__')[0])

packets = parse_hex_log('radio_logs/radio_log_COM7_20260105_171202_hex.txt')

print(f'Scanning {len(packets)} packets for non-zero readings...')
print()

found = 0
for ts, data in packets:
    if len(data) >= 12:
        addr = (data[0] << 8) | data[1]
        reading = struct.unpack('>f', data[3:7])[0]
        
        if reading != 0.0 and -10000 < reading < 10000:
            gas = data[9] & 0x7F
            batt_raw = data[8]
            scale = (data[9] >> 7) & 0x01
            batt_v = batt_raw / 10.0 if scale == 0 else float(batt_raw)
            
            print(f'{ts} | Addr {addr:5d} | Reading: {reading:8.2f} | Gas: {gas:2d} | Batt: {batt_v:4.1f}V')
            print(f'  Hex: {data.hex()}')
            found += 1
            
            if found >= 20:
                break

if found == 0:
    print("No non-zero readings found - all sensors transmitting zeros")
    print("\nSample zero-reading packet:")
    if packets:
        ts, data = packets[100]
        print(f'{ts}: {data.hex()}')
