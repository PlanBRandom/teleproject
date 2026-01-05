#!/usr/bin/env python3
"""
RM024 Firmware Upgrade Utility

Upgrades Laird RM024 radio firmware using the 0xCC binary protocol.
Requires encrypted firmware binary files from Ezurio/Laird.

Usage:
    python firmware_upgrade.py COM7 rm024_fw_v25[00].bin
    python firmware_upgrade.py COM11 rm024_fw_v25[00].bin rm024_fw_v25[01].bin

Requires:
    - Firmware version 1.3+ on radio
    - Encrypted .bin files
    - 115200 baud, hardware flow control
"""

import sys
import os
import time
import serial
from pathlib import Path

# Import LairdRM024 class from test script
sys.path.insert(0, os.path.dirname(__file__))
from test_binary_protocol import LairdRM024


class FirmwareUpgrader:
    """Handles firmware upgrade process for RM024 radios."""
    
    def __init__(self, port, baudrate=115200):
        self.radio = LairdRM024(port, baudrate)
        self.port = port
        
    def upgrade_firmware(self, firmware_file, chunk_size=128):
        """Upgrade radio with firmware binary file.
        
        Args:
            firmware_file: Path to encrypted .bin file
            chunk_size: Bytes to write per operation (1-255, default 128)
        
        Returns:
            True if upgrade successful, False otherwise
        """
        firmware_path = Path(firmware_file)
        
        if not firmware_path.exists():
            print(f"✗ Firmware file not found: {firmware_file}")
            return False
        
        file_size = firmware_path.stat().st_size
        print(f"\n{'='*70}")
        print(f"Upgrading firmware from: {firmware_path.name}")
        print(f"File size: {file_size} bytes")
        print(f"Chunk size: {chunk_size} bytes")
        print(f"{'='*70}\n")
        
        try:
            # Connect to radio
            print("1. Connecting to radio...")
            self.radio.connect()
            time.sleep(0.5)
            
            # Enter command mode
            print("\n2. Entering command mode...")
            if not self.radio.enter_command_mode():
                print("✗ Failed to enter command mode")
                return False
            
            # Erase flash
            print("\n3. Erasing flash memory...")
            print("   ⚠ Radio will disconnect from network")
            if not self.radio.erase_flash():
                print("✗ Failed to erase flash")
                return False
            
            time.sleep(0.5)
            
            # Write firmware binary
            print(f"\n4. Writing firmware binary ({file_size} bytes)...")
            print("   This may take several minutes...")
            
            address = 0x0000
            bytes_written = 0
            verify_errors = 0
            
            with open(firmware_path, 'rb') as f:
                while True:
                    data = f.read(chunk_size)
                    if not data:
                        break
                    
                    # Write chunk
                    if not self.radio.write_flash(address, data):
                        print(f"\n✗ Write failed at address 0x{address:04X}")
                        return False
                    
                    # Verify write (optional but highly recommended)
                    verify_data = self.radio.read_flash(address, len(data))
                    if verify_data != data:
                        verify_errors += 1
                        print(f"\n⚠ Verify mismatch at 0x{address:04X} (error {verify_errors})")
                        
                        if verify_errors > 3:
                            print("✗ Too many verify errors - aborting")
                            return False
                        
                        # Retry write
                        print("   Retrying write...")
                        if not self.radio.write_flash(address, data):
                            print("✗ Retry failed")
                            return False
                        
                        verify_data = self.radio.read_flash(address, len(data))
                        if verify_data != data:
                            print("✗ Verify failed again")
                            return False
                    
                    bytes_written += len(data)
                    address += len(data)
                    
                    # Progress indicator
                    percent = (bytes_written / file_size) * 100
                    progress_bar = '=' * int(percent / 2)
                    print(f"\r   Progress: [{progress_bar:<50}] {percent:.1f}% ({bytes_written}/{file_size} bytes)", end='')
                    
                    # Special delay on first write to 0x800+ (flash erase)
                    if address == chunk_size and address >= 0x800:
                        print("\n   (Erasing upper flash region - 300ms delay)")
                        time.sleep(0.3)
            
            print(f"\n\n   ✓ Wrote {bytes_written} bytes successfully")
            
            # Decrypt firmware
            print("\n5. Decrypting firmware image...")
            if not self.radio.decrypt_image():
                print("✗ Failed to decrypt image")
                return False
            
            # Reset radio
            print("\n6. Resetting radio to activate new firmware...")
            self.radio.soft_reset()
            
            print("   Waiting for radio to restart...")
            time.sleep(3.0)
            
            # Verify upgrade
            print("\n7. Verifying firmware upgrade...")
            
            # Reconnect
            self.radio.disconnect()
            time.sleep(1.0)
            self.radio.connect()
            time.sleep(0.5)
            
            if not self.radio.enter_command_mode():
                print("⚠ Could not re-enter command mode to verify")
                print("   Firmware may still have upgraded successfully")
                return True
            
            if self.radio.verify_firmware_upgrade():
                print("\n✓ Firmware upgrade completed successfully!")
                
                # Show new firmware version
                status = self.radio.status_request()
                if status:
                    fw_version = status['firmware'] / 16
                    print(f"   New firmware version: v{fw_version:.1f}")
                
                self.radio.exit_command_mode()
                return True
            else:
                print("\n⚠ Firmware verification reported errors")
                print("   Some pages may not have been upgraded")
                print("   Check for additional binary files to load")
                self.radio.exit_command_mode()
                return False
            
        except Exception as e:
            print(f"\n✗ Error during upgrade: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        finally:
            self.radio.disconnect()


def main():
    print("\n" + "="*70)
    print("RM024 Firmware Upgrade Utility")
    print("="*70)
    
    if len(sys.argv) < 3:
        print("\nUsage:")
        print("  python firmware_upgrade.py <PORT> <FIRMWARE_FILE> [FIRMWARE_FILE2] ...")
        print("\nExamples:")
        print("  python firmware_upgrade.py COM7 rm024_fw_v25[00].bin")
        print("  python firmware_upgrade.py COM11 rm024_fw_v25[00].bin rm024_fw_v25[01].bin")
        print("\nNote:")
        print("  - Requires firmware v1.3+ already on radio")
        print("  - Uses encrypted .bin files from Ezurio/Laird")
        print("  - Primary image [00] must be loaded first")
        print("  - Load additional [XX] files if verification fails")
        sys.exit(1)
    
    port = sys.argv[1]
    firmware_files = sys.argv[2:]
    
    print(f"\nPort: {port}")
    print(f"Firmware files: {len(firmware_files)}")
    for i, f in enumerate(firmware_files, 1):
        print(f"  {i}. {f}")
    
    print("\n⚠ WARNING: Firmware upgrade process will:")
    print("  - Disconnect radio from network")
    print("  - Erase existing firmware")
    print("  - Take several minutes to complete")
    print("  - Require radio reset")
    
    response = input("\nProceed with upgrade? (yes/no): ")
    if response.lower() not in ['yes', 'y']:
        print("Upgrade cancelled.")
        sys.exit(0)
    
    upgrader = FirmwareUpgrader(port)
    
    success_count = 0
    
    for i, firmware_file in enumerate(firmware_files, 1):
        print(f"\n{'#'*70}")
        print(f"# Upgrading file {i} of {len(firmware_files)}")
        print(f"{'#'*70}")
        
        if upgrader.upgrade_firmware(firmware_file):
            success_count += 1
        else:
            print(f"\n✗ Upgrade failed for: {firmware_file}")
            
            response = input("\nContinue with next file? (yes/no): ")
            if response.lower() not in ['yes', 'y']:
                break
    
    # Summary
    print("\n" + "="*70)
    print("Firmware Upgrade Summary")
    print("="*70)
    print(f"  Files processed: {len(firmware_files)}")
    print(f"  Successful: {success_count}")
    print(f"  Failed: {len(firmware_files) - success_count}")
    
    if success_count == len(firmware_files):
        print("\n🎉 All firmware files upgraded successfully!")
    else:
        print("\n⚠ Some upgrades failed - check errors above")
    
    print("="*70 + "\n")


if __name__ == "__main__":
    main()
