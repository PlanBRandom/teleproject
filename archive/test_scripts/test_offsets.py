"""
Hypothesize: Maybe the format is a Laird wrapper + Gen2
Try parsing with Gen2 starting at different offsets
"""
import struct

packet_hex = "81110011e0882b000f81000000000824060042e087e92377"
data = bytes.fromhex(packet_hex)

print("Testing Gen2 protocol at different offsets:")
print("="*80)

for offset in range(8):
    print(f"\nOffset {offset}: Gen2 data starts at byte[{offset}]")
    gen2 = data[offset:]
    
    if len(gen2) < 12:
        print("  Too short")
        continue
    
    # Try parsing as Protocol 1
    addr = (gen2[0] << 8) | gen2[1]
    proto = gen2[2]
    
    print(f"  Address: 0x{addr:04x} = {addr}")
    print(f"  Protocol: {proto}")
    
    if len(gen2) >= 11:
        # Reading at [3-6]
        reading_bytes = gen2[3:7]
        reading = struct.unpack('>f', reading_bytes)[0]
        
        # Sensor info at [7]
        mode = gen2[7] & 0x07
        stype = (gen2[7] >> 3) & 0x1F
        
        # Battery at [8]
        batt_raw = gen2[8]
        
        # Gas at [9]
        gas = gen2[9] & 0x7F
        scale = (gen2[9] >> 7) & 0x01
        
        if scale == 0:
            batt_v = batt_raw / 10.0
        else:
            batt_v = float(batt_raw)
        
        # Fault at [10]
        fault = (gen2[10] >> 4) & 0x0F
        
        print(f"  Reading: {reading:.2f}")
        print(f"  Sensor: mode={mode}, type={stype}")
        print(f"  Battery: {batt_v:.1f}V (raw={batt_raw})")
        print(f"  Gas type: {gas}")
        print(f"  Fault: {fault}")
        
        # Check if values are reasonable
        reasonable = True
        if addr > 60000 or addr == 0:
            reasonable = False
        if proto not in [0, 1, 2, 7]:
            reasonable = False
        if batt_v > 30 or batt_v < 0:
            reasonable = False
        if gas > 20:
            reasonable = False
            
        if reasonable:
            print("  ✓ Values seem reasonable!")
