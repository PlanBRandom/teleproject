#!/usr/bin/env python3
"""
RM024 Radio Configuration Checker
Verifies all radios are configured as secondaries and can see their primary.
Queries network topology and configuration across all radio networks.
"""

import serial
import time
import re

class RM024ConfigChecker:
    def __init__(self):
        self.radios = {
            'Network_15_Radio': {
                'port': 'COM7',
                'baudrate': 115200,
                'expected_network': 15,
                'expected_role': 'Secondary',
                'description': 'OI-7530 Radio (receives sensors on Net 15)'
            },
            'Network_20_Radio': {
                'port': 'COM12',
                'baudrate': 115200,
                'expected_network': 20,
                'expected_role': 'Secondary',
                'description': 'OI-7010 Radio (receives sensors on Net 20)'
            },
            'Network_25_Radio': {
                'port': 'COM11',
                'baudrate': 115200,
                'expected_network': 25,
                'expected_role': 'Secondary',
                'description': 'OI-7032 Radio (receives from repeaters)'
            }
        }
        
        self.results = {}
    
    def send_at_command(self, ser, command, timeout=2):
        """Send AT command and get response."""
        try:
            # Clear input buffer
            ser.reset_input_buffer()
            
            # Send command
            cmd = f"{command}\r\n".encode()
            ser.write(cmd)
            time.sleep(0.1)
            
            # Read response
            start_time = time.time()
            response = b''
            
            while (time.time() - start_time) < timeout:
                if ser.in_waiting:
                    response += ser.read(ser.in_waiting)
                    time.sleep(0.05)
                else:
                    time.sleep(0.1)
            
            return response.decode('utf-8', errors='ignore').strip()
        except Exception as e:
            return f"ERROR: {e}"
    
    def enter_command_mode(self, ser):
        """Enter AT command mode (usually +++)."""
        try:
            time.sleep(1.1)  # Guard time before +++
            ser.write(b'+++')
            time.sleep(1.1)  # Guard time after +++
            
            # Wait for OK response
            response = b''
            for _ in range(20):
                if ser.in_waiting:
                    response += ser.read(ser.in_waiting)
                    if b'OK' in response or b'ok' in response:
                        return True
                time.sleep(0.1)
            
            return False
        except Exception as e:
            print(f"    Error entering command mode: {e}")
            return False
    
    def exit_command_mode(self, ser):
        """Exit AT command mode."""
        try:
            self.send_at_command(ser, "ATO")
            time.sleep(0.5)
        except:
            pass
    
    def check_radio_config(self, radio_name, config):
        """Check configuration of a single radio."""
        port = config['port']
        baudrate = config['baudrate']
        
        print(f"\n{'='*80}")
        print(f"Checking: {radio_name}")
        print(f"Port: {port} | Baudrate: {baudrate}")
        print(f"Description: {config['description']}")
        print(f"{'='*80}")
        
        result = {
            'port': port,
            'connected': False,
            'command_mode': False,
            'role': None,
            'network_id': None,
            'radio_address': None,
            'primary_visible': None,
            'signal_strength': None,
            'firmware': None,
            'errors': []
        }
        
        try:
            # Open serial port
            print(f"  Connecting to {port}...")
            ser = serial.Serial(
                port=port,
                baudrate=baudrate,
                timeout=1,
                rtscts=True
            )
            result['connected'] = True
            print(f"  ✓ Connected")
            
            # Enter command mode
            print(f"  Entering AT command mode...")
            if self.enter_command_mode(ser):
                result['command_mode'] = True
                print(f"  ✓ In command mode")
                
                # Get firmware version
                print(f"  Querying firmware version...")
                response = self.send_at_command(ser, "ATI")
                if response and 'ERROR' not in response:
                    result['firmware'] = response.replace('\r', ' ').replace('\n', ' ').strip()
                    print(f"    Firmware: {result['firmware']}")
                
                # Get network ID
                print(f"  Querying network ID...")
                response = self.send_at_command(ser, "AT+NET?")
                if response:
                    match = re.search(r'(\d+)', response)
                    if match:
                        result['network_id'] = int(match.group(1))
                        print(f"    Network ID: {result['network_id']}")
                        
                        if result['network_id'] == config['expected_network']:
                            print(f"    ✓ Matches expected network {config['expected_network']}")
                        else:
                            print(f"    ⚠️  MISMATCH! Expected {config['expected_network']}, got {result['network_id']}")
                            result['errors'].append(f"Network mismatch: expected {config['expected_network']}")
                
                # Get radio address
                print(f"  Querying radio address...")
                response = self.send_at_command(ser, "AT+ADDR?")
                if response:
                    match = re.search(r'([0-9A-Fa-f]+)', response)
                    if match:
                        result['radio_address'] = match.group(1)
                        print(f"    Radio Address: 0x{result['radio_address']}")
                
                # Get role (Primary/Secondary)
                print(f"  Querying radio role...")
                response = self.send_at_command(ser, "AT+ROLE?")
                if response:
                    if 'PRIMARY' in response.upper() or 'MASTER' in response.upper():
                        result['role'] = 'Primary'
                    elif 'SECONDARY' in response.upper() or 'SLAVE' in response.upper() or 'CLIENT' in response.upper():
                        result['role'] = 'Secondary'
                    else:
                        # Try to parse numeric role (0=Primary, 1=Secondary in some radios)
                        match = re.search(r'(\d+)', response)
                        if match:
                            role_num = int(match.group(1))
                            result['role'] = 'Secondary' if role_num == 1 else 'Primary' if role_num == 0 else f"Unknown({role_num})"
                        else:
                            result['role'] = response.strip()
                    
                    print(f"    Role: {result['role']}")
                    
                    if result['role'] == config['expected_role']:
                        print(f"    ✓ Matches expected role: {config['expected_role']}")
                    else:
                        print(f"    ⚠️  ROLE MISMATCH! Expected {config['expected_role']}, got {result['role']}")
                        result['errors'].append(f"Role mismatch: expected {config['expected_role']}")
                
                # Check if primary is visible (only if this is a secondary)
                if result['role'] == 'Secondary':
                    print(f"  Checking for primary visibility...")
                    
                    # Try different commands to detect primary
                    for cmd in ["AT+PRIM?", "AT+LINK?", "AT+STAT?"]:
                        response = self.send_at_command(ser, cmd, timeout=3)
                        if response and 'ERROR' not in response.upper() and response.strip():
                            print(f"    Response to {cmd}: {response[:100]}")
                            
                            # Look for indicators of primary connection
                            if any(word in response.upper() for word in ['OK', 'CONNECTED', 'LINK', 'UP', 'FOUND']):
                                result['primary_visible'] = True
                                print(f"    ✓ Primary appears to be visible/connected")
                                break
                            elif any(word in response.upper() for word in ['FAIL', 'DOWN', 'NONE', 'NOT FOUND']):
                                result['primary_visible'] = False
                                print(f"    ⚠️  Primary not visible")
                                result['errors'].append("Primary not visible")
                                break
                    
                    # Try scanning for networks
                    print(f"  Scanning for nearby radios...")
                    response = self.send_at_command(ser, "AT+SCAN", timeout=5)
                    if response and 'ERROR' not in response.upper():
                        print(f"    Scan results: {response[:200]}")
                        # Parse scan results to count visible radios
                        radio_count = len(re.findall(r'[0-9A-Fa-f]{4}', response))
                        if radio_count > 0:
                            print(f"    Found {radio_count} radios in scan")
                
                # Get signal strength (RSSI)
                print(f"  Querying signal strength...")
                for cmd in ["AT+RSSI?", "AT+CSQ?"]:
                    response = self.send_at_command(ser, cmd)
                    if response and 'ERROR' not in response.upper():
                        match = re.search(r'(-?\d+)', response)
                        if match:
                            result['signal_strength'] = match.group(1)
                            print(f"    Signal Strength: {result['signal_strength']} dBm")
                            break
                
                # Exit command mode
                print(f"  Exiting command mode...")
                self.exit_command_mode(ser)
                print(f"  ✓ Back to data mode")
            else:
                print(f"  ✗ Failed to enter command mode")
                print(f"    This radio might be in transparent mode or not support AT commands")
                result['errors'].append("Could not enter AT command mode")
            
            ser.close()
            
        except serial.SerialException as e:
            print(f"  ✗ Serial port error: {e}")
            result['errors'].append(f"Serial error: {e}")
        except Exception as e:
            print(f"  ✗ Unexpected error: {e}")
            result['errors'].append(f"Error: {e}")
        
        return result
    
    def check_all_radios(self):
        """Check configuration of all radios."""
        print("="*80)
        print("RM024 RADIO CONFIGURATION CHECKER")
        print("Verifying all radios are configured as secondaries")
        print("="*80)
        
        for radio_name, config in self.radios.items():
            result = self.check_radio_config(radio_name, config)
            self.results[radio_name] = result
            time.sleep(1)  # Brief pause between radios
        
        # Summary
        self.print_summary()
    
    def print_summary(self):
        """Print summary of all radio configurations."""
        print("\n\n")
        print("="*80)
        print("CONFIGURATION SUMMARY")
        print("="*80)
        
        print(f"\n{'Radio':<20} {'Port':<8} {'Connected':<12} {'Role':<12} {'Network':<10} {'Primary':<12} {'Status'}")
        print("-"*80)
        
        all_ok = True
        
        for radio_name, result in self.results.items():
            config = self.radios[radio_name]
            
            connected = "✓" if result['connected'] else "✗"
            role = result['role'] or "?"
            network = str(result['network_id']) if result['network_id'] else "?"
            
            if result['primary_visible'] is True:
                primary = "✓ Visible"
            elif result['primary_visible'] is False:
                primary = "⚠️  Not visible"
            else:
                primary = "Unknown"
            
            # Determine overall status
            if not result['connected']:
                status = "✗ NOT CONNECTED"
                all_ok = False
            elif result['errors']:
                status = f"⚠️  {len(result['errors'])} issues"
                all_ok = False
            elif result['role'] != config['expected_role']:
                status = "⚠️  WRONG ROLE"
                all_ok = False
            elif result['network_id'] != config['expected_network']:
                status = "⚠️  WRONG NETWORK"
                all_ok = False
            elif result['role'] == 'Secondary' and result['primary_visible'] is False:
                status = "⚠️  NO PRIMARY"
                all_ok = False
            else:
                status = "✓ OK"
            
            print(f"{radio_name:<20} {config['port']:<8} {connected:<12} {role:<12} {network:<10} {primary:<12} {status}")
        
        print()
        print("="*80)
        print("DETAILED FINDINGS")
        print("="*80)
        
        for radio_name, result in self.results.items():
            if result['errors'] or result['role'] != self.radios[radio_name]['expected_role']:
                print(f"\n{radio_name}:")
                
                if result['errors']:
                    print(f"  Issues:")
                    for error in result['errors']:
                        print(f"    • {error}")
                
                if result['role'] and result['role'] != self.radios[radio_name]['expected_role']:
                    print(f"  ⚠️  Role is {result['role']}, expected {self.radios[radio_name]['expected_role']}")
                    print(f"      This radio should be configured as a Secondary!")
                
                if result['network_id'] and result['network_id'] != self.radios[radio_name]['expected_network']:
                    print(f"  ⚠️  Network is {result['network_id']}, expected {self.radios[radio_name]['expected_network']}")
                
                if result['role'] == 'Secondary' and result['primary_visible'] is False:
                    print(f"  ⚠️  Secondary radio cannot see primary on network {result['network_id']}")
                    print(f"      Check that a primary radio is active on this network")
        
        print()
        print("="*80)
        print("NETWORK TOPOLOGY")
        print("="*80)
        
        print("\nExpected Configuration:")
        print("  Network 15: Sensors → Secondary (COM7) → OI-7530")
        print("  Network 20: Sensors → Secondary (COM12) → OI-7010")
        print("  Network 25: Repeaters → Secondary (COM11) → OI-7032")
        print()
        print("Note: Each network needs a PRIMARY radio (on the sensors) and")
        print("      SECONDARY radios (on the monitors) for proper operation.")
        
        if all_ok:
            print()
            print("✓ ALL RADIOS CONFIGURED CORRECTLY!")
        else:
            print()
            print("⚠️  CONFIGURATION ISSUES DETECTED - Review findings above")
        
        print()
        print("="*80)

if __name__ == '__main__':
    checker = RM024ConfigChecker()
    checker.check_all_radios()
