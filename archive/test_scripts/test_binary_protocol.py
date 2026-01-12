#!/usr/bin/env python3
"""
Laird RM024 Binary Protocol Implementation (0xCC Commands)

This implements the documented binary command protocol that works
regardless of Pin 15 status or RF Packet Size settings.

Critical: All bytes must be sent with NO gaps > 600µs (Interface Timeout)
"""

import serial
import time

class LairdRM024:
    """Binary protocol handler for Laird RM024 radios."""
    
    def __init__(self, port, baudrate=115200, timeout=1.0):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.serial = None
        self.in_command_mode = False
        
    def connect(self):
        """Open serial connection with hardware flow control."""
        self.serial = serial.Serial(
            port=self.port,
            baudrate=self.baudrate,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=self.timeout,
            rtscts=True
        )
        self.serial.rts = True
        print(f"✓ Connected to {self.port} @ {self.baudrate} baud")
        
    def disconnect(self):
        """Close serial connection."""
        if self.in_command_mode:
            self.exit_command_mode()
        if self.serial and self.serial.is_open:
            self.serial.close()
            print(f"✓ Disconnected from {self.port}")
    
    def _send_bytes(self, data):
        """Send bytes with NO gaps (critical for 600µs Interface Timeout)."""
        # Send entire command as one write to avoid byte gaps
        self.serial.write(bytes(data))
        self.serial.flush()
        
    def _read_response(self, expected_bytes, timeout=1.0):
        """Read expected response with timeout."""
        response = b''
        start = time.time()
        
        while len(response) < expected_bytes and (time.time() - start) < timeout:
            if self.serial.in_waiting > 0:
                response += self.serial.read(self.serial.in_waiting)
            time.sleep(0.01)
        
        return response
    
    def enter_command_mode(self):
        """Enter AT command mode using binary protocol.
        
        Command: 41 54 2B 2B 2B 0D  ("AT+++\\r")
        Response: CC 43 4F 4D      (0xCC + "COM")
        """
        if self.in_command_mode:
            print("Already in command mode")
            return True
        
        # Clear any pending data
        if self.serial.in_waiting > 0:
            self.serial.read(self.serial.in_waiting)
        
        # Wait for Interface Timeout (600µs) to ensure buffer is empty
        time.sleep(0.001)
        
        # Send: AT+++\r
        command = bytes([0x41, 0x54, 0x2B, 0x2B, 0x2B, 0x0D])
        self._send_bytes(command)
        
        # Wait for Interface Timeout again
        time.sleep(0.001)
        
        # Read response: CC 43 4F 4D
        response = self._read_response(4, timeout=2.0)
        
        if len(response) >= 4 and response[:4] == bytes([0xCC, 0x43, 0x4F, 0x4D]):
            self.in_command_mode = True
            print("✓ Entered command mode (received: CC 43 4F 4D)")
            return True
        else:
            hex_resp = ' '.join([f'{b:02X}' for b in response])
            print(f"✗ Failed to enter command mode")
            print(f"  Expected: CC 43 4F 4D")
            print(f"  Received: {hex_resp if hex_resp else '(no response)'}")
            return False
    
    def exit_command_mode(self):
        """Exit AT command mode.
        
        Command: CC 41 54 4F 0D  (0xCC + "ATO\\r")
        Response: CC 44 41 54    (0xCC + "DAT")
        """
        if not self.in_command_mode:
            print("Not in command mode")
            return True
        
        # Send: CC ATO\r
        command = bytes([0xCC, 0x41, 0x54, 0x4F, 0x0D])
        self._send_bytes(command)
        
        # Read response: CC 44 41 54
        response = self._read_response(4, timeout=1.0)
        
        if len(response) >= 4 and response[:4] == bytes([0xCC, 0x44, 0x41, 0x54]):
            self.in_command_mode = False
            print("✓ Exited command mode (received: CC 44 41 54)")
            return True
        else:
            hex_resp = ' '.join([f'{b:02X}' for b in response])
            print(f"✗ Failed to exit command mode")
            print(f"  Expected: CC 44 41 54")
            print(f"  Received: {hex_resp if hex_resp else '(no response)'}")
            self.in_command_mode = False  # Assume we're out anyway
            return False
    
    def status_request(self):
        """Get firmware version and link status.
        
        Command: CC 00 00
        Response: CC <Firmware> <Status>
        """
        if not self.in_command_mode:
            print("Must be in command mode")
            return None
        
        command = bytes([0xCC, 0x00, 0x00])
        self._send_bytes(command)
        
        response = self._read_response(3, timeout=1.0)
        
        if len(response) >= 3 and response[0] == 0xCC:
            firmware = response[1]
            status = response[2]
            
            status_str = {
                0x01: "Client not in Range",
                0x02: "Server",
                0x03: "Client in Range"
            }.get(status, f"Unknown (0x{status:02X})")
            
            print(f"✓ Status Request:")
            print(f"  Firmware: 0x{firmware:02X}")
            print(f"  Status: {status_str}")
            
            return {'firmware': firmware, 'status': status, 'status_str': status_str}
        else:
            hex_resp = ' '.join([f'{b:02X}' for b in response])
            print(f"✗ Status request failed: {hex_resp}")
            return None
    
    def read_eeprom(self, start_addr, length):
        """Read EEPROM data.
        
        Command: CC C0 <Start> <Length>
        Response: CC <Start> <Length> <Data...>
        """
        if not self.in_command_mode:
            print("Must be in command mode")
            return None
        
        command = bytes([0xCC, 0xC0, start_addr, length])
        self._send_bytes(command)
        
        expected = 3 + length
        response = self._read_response(expected, timeout=2.0)
        
        if len(response) >= 3 and response[0] == 0xCC:
            ret_start = response[1]
            ret_length = response[2]
            data = response[3:3+ret_length]
            
            if ret_start == start_addr and ret_length == length:
                hex_data = ' '.join([f'{b:02X}' for b in data])
                print(f"✓ Read EEPROM 0x{start_addr:02X} [{length} bytes]: {hex_data}")
                return data
            else:
                print(f"✗ EEPROM read mismatch: start={ret_start:02X}, len={ret_length}")
                return None
        else:
            hex_resp = ' '.join([f'{b:02X}' for b in response])
            print(f"✗ EEPROM read failed: {hex_resp}")
            return None
    
    def write_eeprom(self, start_addr, data):
        """Write EEPROM data.
        
        Command: CC C1 <Start> <Length> <Data...>
        Response: <Start> <Length> <LastByte>
        """
        if not self.in_command_mode:
            print("Must be in command mode")
            return False
        
        if isinstance(data, int):
            data = [data]
        elif isinstance(data, bytes):
            data = list(data)
        
        length = len(data)
        command = bytes([0xCC, 0xC1, start_addr, length] + data)
        self._send_bytes(command)
        
        response = self._read_response(3, timeout=2.0)
        
        if len(response) >= 3:
            ret_start = response[0]
            ret_length = response[1]
            last_byte = response[2]
            
            if ret_start == start_addr and ret_length == length and last_byte == data[-1]:
                hex_data = ' '.join([f'{b:02X}' for b in data])
                print(f"✓ Wrote EEPROM 0x{start_addr:02X} [{length} bytes]: {hex_data}")
                return True
            else:
                print(f"✗ EEPROM write verification failed")
                return False
        else:
            hex_resp = ' '.join([f'{b:02X}' for b in response])
            print(f"✗ EEPROM write failed: {hex_resp}")
            return False
    
    def change_channel(self, channel):
        """Change RF channel (on-the-fly, not persistent).
        
        Command: CC 02 <Channel>
        Response: CC <Channel>
        """
        if not self.in_command_mode:
            print("Must be in command mode")
            return False
        
        if channel < 0 or channel > 0x4D:
            print(f"✗ Invalid channel: {channel} (range 0-77 for 79-hop)")
            return False
        
        command = bytes([0xCC, 0x02, channel])
        self._send_bytes(command)
        
        response = self._read_response(2, timeout=1.0)
        
        if len(response) >= 2 and response[0] == 0xCC and response[1] == channel:
            print(f"✓ Changed channel to {channel}")
            return True
        else:
            hex_resp = ' '.join([f'{b:02X}' for b in response])
            print(f"✗ Channel change failed: {hex_resp}")
            return False
    
    def soft_reset(self):
        """Perform soft reset of radio.
        
        Command: CC FF
        Response: None (radio resets)
        """
        if not self.in_command_mode:
            print("Must be in command mode")
            return False
        
        print("Sending soft reset...")
        command = bytes([0xCC, 0xFF])
        self._send_bytes(command)
        
        self.in_command_mode = False
        time.sleep(1.0)  # Wait for reset
        print("✓ Soft reset sent (radio restarting)")
        return True
    
    # Firmware Upgrade Commands (FW 1.3+)
    
    def erase_flash(self):
        """Erase firmware image from flash memory.
        
        Command: CC C6
        Response: CC C6
        
        Erases memory 0x0000-0x7FF immediately.
        Memory 0x800-0x3BFF erased on first write to that range (300ms delay).
        Radio disconnects from network during upgrade process.
        """
        if not self.in_command_mode:
            print("Must be in command mode")
            return False
        
        print("Erasing flash memory (this will disconnect radio from network)...")
        command = bytes([0xCC, 0xC6])
        self._send_bytes(command)
        
        response = self._read_response(2, timeout=2.0)
        
        if len(response) >= 2 and response[:2] == bytes([0xCC, 0xC6]):
            print("✓ Flash erased successfully")
            return True
        else:
            hex_resp = ' '.join([f'{b:02X}' for b in response])
            print(f"✗ Flash erase failed: {hex_resp}")
            return False
    
    def write_flash(self, start_addr, data):
        """Write encrypted firmware data to flash.
        
        Command: CC C4 <StartAddr_MSB> <StartAddr_LSB> <Len_MSB> <Len_LSB> <Data>
        Response: CC C4 <Result> <StartAddr_MSB> <StartAddr_LSB>
        
        Args:
            start_addr: 16-bit start address (0x0000 - 0x3BFF)
            data: bytes to write (1-255 bytes per write)
        
        Result codes:
            0x00 = No Error
            0x03 = Command Timed Out
            0x04 = Valid image exists (erase first)
            0x06 = Bounds Exceeded
        
        Note: First write to 0x800+ causes 300ms delay while erasing 0x800-0x3BFF.
        """
        if not self.in_command_mode:
            print("Must be in command mode")
            return False
        
        if isinstance(data, bytes):
            data = list(data)
        
        length = len(data)
        if length < 1 or length > 255:
            print(f"✗ Invalid length: {length} (must be 1-255)")
            return False
        
        if start_addr < 0 or start_addr > 0x3BFF:
            print(f"✗ Invalid address: 0x{start_addr:04X} (range 0x0000-0x3BFF)")
            return False
        
        # Split 16-bit address into MSB/LSB
        addr_msb = (start_addr >> 8) & 0xFF
        addr_lsb = start_addr & 0xFF
        len_msb = (length >> 8) & 0xFF
        len_lsb = length & 0xFF
        
        command = bytes([0xCC, 0xC4, addr_msb, addr_lsb, len_msb, len_lsb] + data)
        self._send_bytes(command)
        
        # Extra timeout for potential 300ms erase delay
        response = self._read_response(5, timeout=1.0)
        
        if len(response) >= 5 and response[0] == 0xCC and response[1] == 0xC4:
            result = response[2]
            
            if result == 0x00:
                print(f"✓ Wrote {length} bytes to 0x{start_addr:04X}")
                return True
            else:
                error_msg = {
                    0x03: "Command Timed Out",
                    0x04: "Valid image exists (erase first)",
                    0x06: "Bounds Exceeded"
                }.get(result, f"Unknown error 0x{result:02X}")
                print(f"✗ Write failed: {error_msg}")
                return False
        else:
            hex_resp = ' '.join([f'{b:02X}' for b in response])
            print(f"✗ Write flash failed: {hex_resp}")
            return False
    
    def read_flash(self, start_addr, length):
        """Read encrypted firmware data from flash.
        
        Command: CC C9 <StartAddr_MSB> <StartAddr_LSB> <Len_MSB> <Len_LSB>
        Response: CC C9 <Result> <StartAddr_MSB> <StartAddr_LSB> <Data>
        
        Args:
            start_addr: 16-bit start address (0x0000 - 0x3AFF)
            length: bytes to read (1-700, depending on heap)
        
        Result codes:
            0x00 = No Error
            0x02 = Not Enough Free Memory (try shorter length)
            0x03 = Command Timed Out
            0x04 = Image Already Decrypted
            0x06 = Bounds Exceeded
        
        Note: Returns encrypted data. Cannot read after decrypt.
        """
        if not self.in_command_mode:
            print("Must be in command mode")
            return None
        
        if start_addr < 0 or start_addr > 0x3AFF:
            print(f"✗ Invalid address: 0x{start_addr:04X} (range 0x0000-0x3AFF)")
            return None
        
        # Split 16-bit address into MSB/LSB
        addr_msb = (start_addr >> 8) & 0xFF
        addr_lsb = start_addr & 0xFF
        len_msb = (length >> 8) & 0xFF
        len_lsb = length & 0xFF
        
        command = bytes([0xCC, 0xC9, addr_msb, addr_lsb, len_msb, len_lsb])
        self._send_bytes(command)
        
        expected = 5 + length
        response = self._read_response(expected, timeout=2.0)
        
        if len(response) >= 5 and response[0] == 0xCC and response[1] == 0xC9:
            result = response[2]
            
            if result == 0x00:
                data = response[5:5+length]
                print(f"✓ Read {len(data)} bytes from 0x{start_addr:04X}")
                return data
            else:
                error_msg = {
                    0x02: "Not Enough Free Memory (try shorter length)",
                    0x03: "Command Timed Out",
                    0x04: "Image Already Decrypted",
                    0x06: "Bounds Exceeded"
                }.get(result, f"Unknown error 0x{result:02X}")
                print(f"✗ Read failed: {error_msg}")
                return None
        else:
            hex_resp = ' '.join([f'{b:02X}' for b in response])
            print(f"✗ Read flash failed: {hex_resp}")
            return None
    
    def decrypt_image(self):
        """Decrypt downloaded firmware image.
        
        Command: CC C5
        Response: CC C5 <Result>
        
        Result codes:
            0x00 = No Error (image decrypted, will load on next reboot)
            0x01 = File integrity error (erase and retry)
            0x02 = Not enough memory (reset and retry)
            0x04 = Image Already Decrypted
        
        Note: Once decrypted, image cannot be read. Next reboot loads new firmware.
        """
        if not self.in_command_mode:
            print("Must be in command mode")
            return False
        
        print("Decrypting firmware image...")
        command = bytes([0xCC, 0xC5])
        self._send_bytes(command)
        
        response = self._read_response(3, timeout=2.0)
        
        if len(response) >= 3 and response[0] == 0xCC and response[1] == 0xC5:
            result = response[2]
            
            if result == 0x00:
                print("✓ Image decrypted successfully (will load on next reboot)")
                return True
            else:
                error_msg = {
                    0x01: "File integrity error (erase flash and retry)",
                    0x02: "Not enough memory (reset module and retry)",
                    0x04: "Image Already Decrypted"
                }.get(result, f"Unknown error 0x{result:02X}")
                print(f"✗ Decrypt failed: {error_msg}")
                return False
        else:
            hex_resp = ' '.join([f'{b:02X}' for b in response])
            print(f"✗ Decrypt image failed: {hex_resp}")
            return False
    
    def verify_firmware_upgrade(self):
        """Verify all firmware pages were upgraded successfully.
        
        Command: CC 00 02
        Response: CC <FW> <Status> (or error if pages incomplete)
        
        Should be called after firmware upgrade and reset to verify success.
        """
        if not self.in_command_mode:
            print("Must be in command mode")
            return False
        
        print("Verifying firmware upgrade...")
        command = bytes([0xCC, 0x00, 0x02])
        self._send_bytes(command)
        
        response = self._read_response(3, timeout=1.0)
        
        if len(response) >= 3 and response[0] == 0xCC:
            firmware = response[1]
            status = response[2]
            print(f"✓ Firmware upgrade verified: FW=0x{firmware:02X}, Status=0x{status:02X}")
            return True
        else:
            hex_resp = ' '.join([f'{b:02X}' for b in response])
            print(f"✗ Firmware verification failed: {hex_resp}")
            print("  Some pages may not have been upgraded - check and retry")
            return False


def test_radio(port, name):
    """Test binary protocol on a radio."""
    print(f"\n{'='*70}")
    print(f"Testing {name} on {port}")
    print(f"{'='*70}\n")
    
    radio = LairdRM024(port)
    
    try:
        # Connect
        radio.connect()
        time.sleep(0.5)
        
        # Enter command mode
        print("\n--- Entering Command Mode ---")
        if not radio.enter_command_mode():
            print("Failed to enter command mode!")
            return False
        
        # Status request
        print("\n--- Status Request ---")
        status = radio.status_request()
        
        # Read channel from EEPROM
        print("\n--- Reading EEPROM Configuration ---")
        channel_data = radio.read_eeprom(0x40, 1)
        if channel_data:
            print(f"  Current Channel: {channel_data[0]} (0x{channel_data[0]:02X})")
        
        mode_data = radio.read_eeprom(0x41, 1)
        if mode_data:
            mode_str = "Server" if mode_data[0] == 0x01 else "Client"
            print(f"  Mode: {mode_str} (0x{mode_data[0]:02X})")
        
        baud_data = radio.read_eeprom(0x42, 1)
        if baud_data:
            print(f"  Baud Rate: 0x{baud_data[0]:02X}")
        
        sysid_data = radio.read_eeprom(0x76, 1)
        if sysid_data:
            print(f"  System ID: 0x{sysid_data[0]:02X}")
        
        # Read RF Packet Size
        packet_size_data = radio.read_eeprom(0x5A, 1)
        if packet_size_data:
            print(f"  RF Packet Size: {packet_size_data[0]} bytes (0x{packet_size_data[0]:02X})")
        
        # Read Auto Config setting
        control1_data = radio.read_eeprom(0x56, 1)
        if control1_data:
            auto_config = control1_data[0] & 0x01
            print(f"  Auto Config: {'Enabled' if auto_config else 'Disabled'}")
        
        # Exit command mode
        print("\n--- Exiting Command Mode ---")
        radio.exit_command_mode()
        
        print(f"\n✓ {name} test complete!")
        return True
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        radio.disconnect()


def main():
    print("\n" + "="*70)
    print("Laird RM024 Binary Protocol (0xCC) Test")
    print("="*70)
    print("\nThis implements the documented binary command protocol")
    print("that works regardless of RF Packet Size or Pin 15 settings!")
    
    # Test both radios
    com7_ok = test_radio("COM7", "Radio 1 (Ch 76)")
    com11_ok = test_radio("COM11", "Radio 2 (Ch 12)")
    
    # Summary
    print("\n" + "="*70)
    print("Test Summary")
    print("="*70)
    print(f"  COM7:  {'✓ SUCCESS' if com7_ok else '✗ FAILED'}")
    print(f"  COM11: {'✓ SUCCESS' if com11_ok else '✗ FAILED'}")
    
    if com7_ok and com11_ok:
        print("\n🎉 Binary protocol working! Ready to integrate into web app!")
    else:
        print("\n⚠ Some tests failed - check connections and settings")
    
    print("="*70 + "\n")

if __name__ == "__main__":
    main()
