"""Manually reconstruct and analyze fragmented packets"""
# Packet #1 + #2
p1 = bytes.fromhex('811100')
p2 = bytes.fromhex('11e0882b000f81000000000824060042e087e92377')
full = p1 + p2

print('Reconstructed packet #1+#2 (24 bytes):')
print(f'Hex: {full.hex()}')
print(f'Bytes: {" ".join(f"{b:02x}" for b in full)}')
print()

# Search for Protocol 1 marker
print('Searching for Protocol 1 marker (0x01):')
for offset in range(len(full) - 12):
    if offset + 2 < len(full):
        proto = full[offset + 2]
        if proto == 0x01:
            print(f'  ✓ Found at offset {offset}!')
            print(f'    Address: 0x{full[offset]:02x}{full[offset+1]:02x} = {(full[offset] << 8) | full[offset+1]}')
            print(f'    Protocol: {proto}')

# Also check for common patterns
print('\nByte value frequencies:')
freq = {}
for b in full:
    freq[b] = freq.get(b, 0) + 1
for b in sorted(freq.keys(), key=lambda x: freq[x], reverse=True)[:5]:
    print(f'  0x{b:02x}: {freq[b]} times')
