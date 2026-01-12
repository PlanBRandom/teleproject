"""
OI-7032 Channel Management System
Manage channels: disable inactive, enable scan mode, auto-assign rogues
"""
import serial
import struct
import time

class OI7032Manager:
    def __init__(self, port='COM10', baud=9600, slave_id=3):
        self.port = port
        self.baud = baud
        self.slave_id = slave_id
        self.ser = None
        
    def connect(self):
        """Connect to OI-7032"""
        self.ser = serial.Serial(self.port, self.baud, timeout=1)
        time.sleep(0.1)
        
    def disconnect(self):
        """Disconnect from OI-7032"""
        if self.ser:
            self.ser.close()
            
    def calculate_crc(self, data):
        """Calculate Modbus RTU CRC-16"""
        crc = 0xFFFF
        for byte in data:
            crc ^= byte
            for _ in range(8):
                crc = (crc >> 1) ^ 0xA001 if crc & 1 else crc >> 1
        return struct.pack('<H', crc)
    
    def read_registers(self, address, count):
        """Read holding registers"""
        request = bytes([self.slave_id, 0x03]) + struct.pack('>HH', address, count)
        request += self.calculate_crc(request)
        self.ser.write(request)
        time.sleep(0.05)
        response = self.ser.read(100)
        if len(response) < 5:
            return None
        byte_count = response[2]
        register_data = response[3:3+byte_count]
        registers = []
        for i in range(0, len(register_data), 2):
            registers.append(struct.unpack('>H', register_data[i:i+2])[0])
        return registers
    
    def write_register(self, address, value):
        """Write single holding register"""
        request = bytes([self.slave_id, 0x06]) + struct.pack('>HH', address, value)
        request += self.calculate_crc(request)
        self.ser.write(request)
        time.sleep(0.05)
        response = self.ser.read(100)
        return len(response) > 0
    
    def get_channel_info(self, channel):
        """Get channel information"""
        # Modbus addresses (0-based)
        addr_reg = 0x00 + (channel - 1)
        time_reg = 0xC0 + (channel - 1)
        battery_reg = 0x80 + (channel - 1) * 2
        reading_reg = 0x20 + (channel - 1) * 2
        
        # Radio address
        regs = self.read_registers(addr_reg, 1)
        radio_addr = regs[0] if regs else 0
        
        # Time since last message
        regs = self.read_registers(time_reg, 1)
        time_since = regs[0] if regs else 65535
        
        # Battery
        regs = self.read_registers(battery_reg, 2)
        battery = 0.0
        if regs and len(regs) == 2:
            bytes_data = struct.pack('>HH', regs[0], regs[1])
            battery = struct.unpack('>f', bytes_data)[0]
        
        # Reading
        regs = self.read_registers(reading_reg, 2)
        reading = 0.0
        if regs and len(regs) == 2:
            bytes_data = struct.pack('>HH', regs[0], regs[1])
            reading = struct.unpack('>f', bytes_data)[0]
        
        return {
            'channel': channel,
            'radio_addr': radio_addr,
            'time_since': time_since,
            'battery': battery,
            'reading': reading,
            'active': time_since < 600 and radio_addr > 0
        }
    
    def scan_all_channels(self):
        """Scan all 32 channels and categorize them"""
        active = []
        inactive = []
        unused = []
        
        for channel in range(1, 33):
            info = self.get_channel_info(channel)
            if info['radio_addr'] == 0:
                unused.append(channel)
            elif info['active']:
                active.append(info)
            else:
                inactive.append(info)
            time.sleep(0.02)
        
        return {
            'active': active,
            'inactive': inactive,
            'unused': unused
        }
    
    def disable_channel(self, channel):
        """Disable a channel by setting address to 0"""
        addr_reg = 0x00 + (channel - 1)
        success = self.write_register(addr_reg, 0)
        return success
    
    def enable_channel(self, channel, radio_addr):
        """Enable a channel with specified radio address"""
        addr_reg = 0x00 + (channel - 1)
        success = self.write_register(addr_reg, radio_addr)
        return success
    
    def setup_scan_channel(self, channel, scan_addr=255):
        """Setup a channel to scan for rogue radios"""
        # Enable channel with scan address
        success = self.enable_channel(channel, scan_addr)
        if success:
            print(f"✓ Channel {channel} enabled for scanning (address {scan_addr})")
        else:
            print(f"✗ Failed to enable channel {channel}")
        return success
    
    def monitor_scan_channel(self, channel, duration=60):
        """Monitor scan channel for rogue radio transmissions"""
        print(f"\nMonitoring channel {channel} for {duration} seconds...")
        print("Listening for rogue radio transmissions...")
        
        start_time = time.time()
        detected_addresses = set()
        
        while time.time() - start_time < duration:
            info = self.get_channel_info(channel)
            
            # Check if we received a message
            if info['time_since'] < 5:  # Message within last 5 seconds
                if info['radio_addr'] not in detected_addresses:
                    detected_addresses.add(info['radio_addr'])
                    print(f"  → Detected radio address: {info['radio_addr']}")
            
            time.sleep(2)
        
        return list(detected_addresses)
    
    def auto_assign_rogue(self, rogue_addr, unused_channels):
        """Automatically assign a rogue radio to an unused channel"""
        if not unused_channels:
            print("✗ No unused channels available")
            return None
        
        # Use first available unused channel
        channel = unused_channels[0]
        success = self.enable_channel(channel, rogue_addr)
        
        if success:
            print(f"✓ Assigned rogue radio {rogue_addr} to channel {channel}")
            return channel
        else:
            print(f"✗ Failed to assign rogue radio {rogue_addr}")
            return None

def main():
    print('='*80)
    print('OI-7032 CHANNEL MANAGEMENT SYSTEM')
    print('='*80)
    print()
    
    mgr = OI7032Manager()
    mgr.connect()
    
    # Step 1: Scan current channels
    print('STEP 1: Scanning all channels...')
    channels = mgr.scan_all_channels()
    
    print(f"\n✓ Active channels: {len(channels['active'])}")
    for ch in channels['active']:
        print(f"  Channel {ch['channel']:2d}: Address {ch['radio_addr']:3d}, {ch['time_since']:3d}s ago")
    
    print(f"\n⚠ Inactive channels: {len(channels['inactive'])}")
    for ch in channels['inactive']:
        print(f"  Channel {ch['channel']:2d}: Address {ch['radio_addr']:3d}, {ch['time_since']:4d}s ago")
    
    print(f"\n○ Unused channels: {len(channels['unused'])}")
    print(f"  Channels: {channels['unused']}")
    
    # Step 2: Disable inactive channels
    print('\n' + '='*80)
    print('STEP 2: Disabling inactive channels...')
    for ch in channels['inactive']:
        print(f"  Disabling channel {ch['channel']}... ", end='')
        if mgr.disable_channel(ch['channel']):
            print("✓")
        else:
            print("✗")
        time.sleep(0.1)
    
    # Step 3: Setup scan channel
    print('\n' + '='*80)
    print('STEP 3: Setting up rogue radio scan channel...')
    if channels['unused']:
        scan_channel = channels['unused'][0]
        mgr.setup_scan_channel(scan_channel, scan_addr=255)
        
        # Monitor for rogues
        print('\nWould you like to monitor for rogue radios? (requires time)')
        print('Press Ctrl+C to skip monitoring')
        try:
            rogues = mgr.monitor_scan_channel(scan_channel, duration=30)
            
            if rogues:
                print(f"\n✓ Found {len(rogues)} rogue radio(s): {rogues}")
                
                # Auto-assign rogues
                print('\nAuto-assigning rogues to unused channels...')
                remaining_unused = channels['unused'][1:]  # Skip scan channel
                for rogue_addr in rogues:
                    if remaining_unused:
                        assigned_ch = mgr.auto_assign_rogue(rogue_addr, remaining_unused)
                        if assigned_ch:
                            remaining_unused.remove(assigned_ch)
            else:
                print("\n○ No rogue radios detected")
        except KeyboardInterrupt:
            print("\n\n○ Monitoring skipped")
    else:
        print("✗ No unused channels available for scanning")
    
    mgr.disconnect()
    
    print('\n' + '='*80)
    print('CHANNEL MANAGEMENT COMPLETE')
    print('='*80)

if __name__ == '__main__':
    main()
