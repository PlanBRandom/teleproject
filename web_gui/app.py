"""
OI Monitor Control Center - Web GUI
Unified interface for testing, configuration, and monitoring
"""

from flask import Flask, render_template, jsonify, request, Response
from flask_socketio import SocketIO, emit
import sys
import os
import json
import threading
import time
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from pipeline.modbus_client import ModbusClient, ModbusConfig, ConnectionType
from pipeline.radio_receiver import RadioReceiver
from pipeline.device_control import DeviceControl
from pipeline.registers import GAS_TYPES, SENSOR_TYPES, FAULT_CODES
import serial
import serial.tools.list_ports

app = Flask(__name__)
app.config['SECRET_KEY'] = 'oi-monitor-secret'
socketio = SocketIO(app, cors_allowed_origins="*")

# Global state
modbus_client = None
radio_receiver = None
device_control = None
monitoring_active = False
monitoring_thread = None

def enter_radio_command_mode(radio, timeout=20.0):
    """Enter AT command mode using 0xCC binary protocol.
    
    Args:
        radio: RadioReceiver instance
        timeout: Maximum time to wait for response (unused, kept for compatibility)
        
    Returns:
        True if successfully entered command mode, False otherwise
        
    Uses the documented 0xCC binary protocol which works regardless of
    RF Packet Size, Pin 15 status, or Auto Config settings.
    """
    try:
        # Pause the receiver thread if running
        was_running = False
        if hasattr(radio, 'running') and radio.running:
            was_running = True
            radio.running = False
            time.sleep(0.2)  # Let thread finish current read
        
        # Clear any pending data
        if radio.serial.in_waiting > 0:
            radio.serial.read(radio.serial.in_waiting)
        
        # Wait for Interface Timeout (600µs) to ensure buffer is empty
        time.sleep(0.001)
        
        # Send: AT+++\r using binary protocol
        # Command: 41 54 2B 2B 2B 0D ("AT+++\r")
        # Expected Response: CC 43 4F 4D (0xCC + "COM")
        command = bytes([0x41, 0x54, 0x2B, 0x2B, 0x2B, 0x0D])
        print(f"Sending binary command mode entry: {command.hex()}")
        
        # Send entire command at once (no gaps > 600µs)
        radio.serial.write(command)
        radio.serial.flush()
        
        # Wait for Interface Timeout again
        time.sleep(0.001)
        
        # Read response: CC 43 4F 4D
        response = b''
        response_timeout = 2.0
        start = time.time()
        
        while len(response) < 4 and (time.time() - start) < response_timeout:
            if radio.serial.in_waiting > 0:
                response += radio.serial.read(radio.serial.in_waiting)
            time.sleep(0.01)
        
        if len(response) >= 4 and response[:4] == bytes([0xCC, 0x43, 0x4F, 0x4D]):
            print(f"✓ Entered command mode (received: {response[:4].hex()})")
            return True  # SUCCESS - stay in command mode, don't restart receiver
        else:
            print(f"✗ Failed to enter command mode")
            print(f"  Expected: CC 43 4F 4D")
            print(f"  Received: {response.hex() if response else '(no response)'}")
            if was_running:
                radio.running = True
            return False
        
    except Exception as e:
        print(f"Error entering command mode: {e}")
        if was_running:
            radio.running = True
        return False

def exit_radio_command_mode(radio):
    """Exit AT command mode using 0xCC binary protocol and restart receiver."""
    try:
        # Send: CC ATO\r using binary protocol
        # Command: CC 41 54 4F 0D (0xCC + "ATO\r")
        # Expected Response: CC 44 41 54 (0xCC + "DAT")
        command = bytes([0xCC, 0x41, 0x54, 0x4F, 0x0D])
        print(f"Sending binary command mode exit: {command.hex()}")
        
        radio.serial.write(command)
        radio.serial.flush()
        
        # Read response
        response = b''
        timeout = 1.0
        start = time.time()
        
        while len(response) < 4 and (time.time() - start) < timeout:
            if radio.serial.in_waiting > 0:
                response += radio.serial.read(radio.serial.in_waiting)
            time.sleep(0.01)
        
        # Always restart the receiver thread
        if hasattr(radio, 'running'):
            radio.running = True
        
        if len(response) >= 4 and response[:4] == bytes([0xCC, 0x44, 0x41, 0x54]):
            print(f"✓ Exited command mode (received: {response[:4].hex()})")
            return True
        else:
            print(f"⚠ Exit response: {response.hex() if response else '(no response)'}")
            # Assume we're out anyway since we restarted receiver
            return True
        
    except Exception as e:
        print(f"Error exiting command mode: {e}")
        if hasattr(radio, 'running'):
            radio.running = True
        return False

def read_radio_eeprom(radio, start_addr, length):
    """Read EEPROM data using 0xCC binary protocol.
    
    Must be in command mode first.
    Command: CC C0 <Start> <Length>
    Response: CC <Start> <Length> <Data...>
    """
    try:
        command = bytes([0xCC, 0xC0, start_addr, length])
        print(f"Reading EEPROM 0x{start_addr:02X} [{length} bytes]: {command.hex()}")
        
        radio.serial.write(command)
        radio.serial.flush()
        
        expected = 3 + length
        response = b''
        timeout = 2.0
        start = time.time()
        
        while len(response) < expected and (time.time() - start) < timeout:
            if radio.serial.in_waiting > 0:
                response += radio.serial.read(radio.serial.in_waiting)
            time.sleep(0.01)
        
        if len(response) >= 3 and response[0] == 0xCC:
            ret_start = response[1]
            ret_length = response[2]
            data = response[3:3+ret_length]
            
            if ret_start == start_addr and ret_length == length:
                print(f"✓ Read EEPROM: {data.hex()}")
                return data
            else:
                print(f"✗ EEPROM read mismatch")
                return None
        else:
            print(f"✗ EEPROM read failed: {response.hex()}")
            return None
            
    except Exception as e:
        print(f"Error reading EEPROM: {e}")
        return None

def write_radio_eeprom(radio, start_addr, data):
    """Write EEPROM data using 0xCC binary protocol.
    
    Must be in command mode first.
    Command: CC C1 <Start> <Length> <Data...>
    Response: <Start> <Length> <LastByte>
    """
    try:
        if isinstance(data, int):
            data = [data]
        elif isinstance(data, bytes):
            data = list(data)
        
        length = len(data)
        command = bytes([0xCC, 0xC1, start_addr, length] + data)
        print(f"Writing EEPROM 0x{start_addr:02X}: {command.hex()}")
        
        radio.serial.write(command)
        radio.serial.flush()
        
        response = b''
        timeout = 2.0
        start = time.time()
        
        while len(response) < 3 and (time.time() - start) < timeout:
            if radio.serial.in_waiting > 0:
                response += radio.serial.read(radio.serial.in_waiting)
            time.sleep(0.01)
        
        if len(response) >= 3:
            ret_start = response[0]
            ret_length = response[1]
            last_byte = response[2]
            
            if ret_start == start_addr and ret_length == length and last_byte == data[-1]:
                print(f"✓ Wrote EEPROM successfully")
                return True
            else:
                print(f"✗ EEPROM write verification failed")
                return False
        else:
            print(f"✗ EEPROM write failed: {response.hex()}")
            return False
            
    except Exception as e:
        print(f"Error writing EEPROM: {e}")
        return False

def get_radio_status(radio):
    """Get radio firmware and link status using 0xCC binary protocol.
    
    Must be in command mode first.
    Command: CC 00 00
    Response: CC <Firmware> <Status>
    """
    try:
        command = bytes([0xCC, 0x00, 0x00])
        print(f"Getting radio status: {command.hex()}")
        
        radio.serial.write(command)
        radio.serial.flush()
        
        response = b''
        timeout = 1.0
        start = time.time()
        
        while len(response) < 3 and (time.time() - start) < timeout:
            if radio.serial.in_waiting > 0:
                response += radio.serial.read(radio.serial.in_waiting)
            time.sleep(0.01)
        
        if len(response) >= 3 and response[0] == 0xCC:
            firmware = response[1]
            status = response[2]
            
            status_str = {
                0x01: "Client not in Range",
                0x02: "Server",
                0x03: "Client in Range"
            }.get(status, f"Unknown (0x{status:02X})")
            
            print(f"✓ Status: FW=0x{firmware:02X}, Status={status_str}")
            return {'firmware': firmware, 'status': status, 'status_str': status_str}
        else:
            print(f"✗ Status request failed: {response.hex()}")
            return None
            
    except Exception as e:
        print(f"Error getting status: {e}")
        return None

def detect_api_mode(radio):
    """Check if radio is in API mode by looking for CC frame delimiter.
    Returns True if API mode detected, False if transparent mode.
    """
    try:
        # Check if any data in buffer has CC prefix
        if radio.serial.in_waiting > 0:
            data = radio.serial.read(radio.serial.in_waiting)
            if b'\xCC' in data:
                return True
        
        # Send a test to see if we get CC framed response
        radio.serial.write(b'\r')
        time.sleep(0.2)
        if radio.serial.in_waiting > 0:
            data = radio.serial.read(radio.serial.in_waiting)
            if data.startswith(b'\xCC'):
                return True
        
        return False
    except:
        return False

def enter_command_mode_api(radio, timeout=5.0):
    """Enter command mode when radio is in API mode.
    In API mode, all data must be wrapped with CC frame delimiter.
    """
    try:
        # Clear buffer
        if radio.serial.in_waiting > 0:
            radio.serial.read(radio.serial.in_waiting)
        
        # Guard time
        time.sleep(1.2)
        
        # Send +++ wrapped in API frame: CC + +++
        radio.serial.write(b'\xCC\x2B\x2B\x2B')  # CC + "+++"
        
        # Guard time
        time.sleep(1.2)
        
        # Wait for OK response (might be CC framed: CC 4F 4B 0D)
        start_time = time.time()
        response = b''
        while time.time() - start_time < timeout:
            if radio.serial.in_waiting > 0:
                response += radio.serial.read(radio.serial.in_waiting)
                # Look for OK (might be: CC 4F 4B or just 4F 4B)
                if b'OK' in response or b'\x4F\x4B' in response:
                    return True
            time.sleep(0.1)
        
        return False
    except:
        return False

def setup_radio_listeners():
    """Setup event listeners for radio receiver to forward sensor data to web GUI"""
    global radio_receiver
    
    if not radio_receiver:
        return
    
    def on_sensor_message(msg):
        """Forward sensor messages to web GUI via SocketIO"""
        try:
            # Format sensor data for display
            gas_name = msg.gas_type_name if hasattr(msg, 'gas_type_name') else 'Unknown'
            sensor_name = msg.sensor_type_name if hasattr(msg, 'sensor_type_name') else 'Unknown'
            fault_name = msg.fault_name if hasattr(msg, 'fault_name') else 'None'
            
            # Build status string
            status_parts = []
            if msg.battery_voltage:
                status_parts.append(f"Battery: {msg.battery_voltage:.1f}V")
            if fault_name != 'None':
                status_parts.append(f"FAULT: {fault_name}")
            
            status = ', '.join(status_parts) if status_parts else 'OK'
            
            # Log to activity log
            log_msg = f"Sensor @{msg.transmitter_address}: {gas_name} = {msg.reading:.1f} PPM, {status}"
            socketio.emit('log', {
                'message': log_msg,
                'level': 'success' if fault_name == 'None' else 'warning'
            })
            
            # Emit sensor data event
            socketio.emit('sensor_data', {
                'sensor_id': msg.transmitter_address,  # For backwards compatibility
                'address': msg.transmitter_address,
                'channel': msg.channel,
                'reading': msg.reading,
                'gas_type': gas_name,
                'sensor_type': sensor_name,
                'battery': msg.battery_voltage,
                'fault': fault_name,
                'timestamp': time.time()
            })
            
            print(f"[SENSOR DATA] @{msg.transmitter_address}: {gas_name} = {msg.reading:.1f} PPM")
            
        except Exception as e:
            print(f"Error processing sensor message: {e}")
            import traceback
            traceback.print_exc()
    
    # Register callback using the proper RadioReceiver API
    radio_receiver.register_callback(on_sensor_message)
    print("Radio listeners registered")

@app.route('/')
def index():
    """Main dashboard"""
    return render_template('index.html')

@app.route('/api/ports')
def get_ports():
    """Get available COM ports"""
    ports = []
    for port in serial.tools.list_ports.comports():
        ports.append({
            'port': port.device,
            'description': port.description,
            'hwid': port.hwid
        })
    return jsonify(ports)

@app.route('/api/modbus/connect', methods=['POST'])
def modbus_connect():
    """Connect to Modbus device"""
    global modbus_client, device_control
    
    try:
        data = request.json
        port = data.get('port')
        slave_id = int(data.get('slave_id', 1))
        baudrate = int(data.get('baudrate', 9600))
        model = data.get('model', 'Device')
        
        # Close existing connection first
        if modbus_client:
            try:
                modbus_client.close()
                time.sleep(0.5)  # Wait for port to release
            except:
                pass
            modbus_client = None
            device_control = None
        
        config = ModbusConfig(
            connection_type=ConnectionType.RTU,
            port=port,
            slave_id=slave_id,
            baudrate=baudrate,
            timeout=1  # Shorter timeout for web UI
        )
        
        modbus_client = ModbusClient(config)
        device_control = DeviceControl(modbus_client)
        
        # Test connection
        serial_num = modbus_client.read_uint32(0x01)
        
        return jsonify({
            'success': True,
            'message': f'Connected to {model} on {port} at {baudrate} baud (Slave {slave_id}, Serial: {serial_num})',
            'serial_number': serial_num,
            'model': model
        })
    except Exception as e:
        # Clean up on error
        if modbus_client:
            try:
                modbus_client.close()
            except:
                pass
            modbus_client = None
            device_control = None
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/modbus/disconnect', methods=['POST'])
def modbus_disconnect():
    """Disconnect from Modbus"""
    global modbus_client, device_control
    
    try:
        if modbus_client:
            try:
                modbus_client.close()
            except:
                pass  # Ignore close errors
            modbus_client = None
            device_control = None
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/modbus/read_channels')
def read_channels():
    """Read all active channels"""
    if not modbus_client:
        return jsonify({'success': False, 'error': 'Not connected'}), 400
    
    try:
        channels = []
        for ch in range(1, 33):
            addr = 0x20 + (ch - 1) * 2
            value = modbus_client.read_float32(addr)
            
            if value != 0.0:  # Only return active channels
                # Get gas type
                gas_type_addr = 0x100 + (ch - 1) * 2
                gas_code = modbus_client.read_uint16(gas_type_addr)
                gas_name = GAS_TYPES.get(gas_code, f"Unknown ({gas_code})")
                
                channels.append({
                    'channel': ch,
                    'value': round(value, 2),
                    'gas_type': gas_name,
                    'gas_code': gas_code
                })
        
        return jsonify({'success': True, 'channels': channels})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/modbus/device_info')
def get_device_info():
    """Get device information"""
    if not modbus_client:
        return jsonify({'success': False, 'error': 'Not connected'}), 400
    
    try:
        info = {
            'serial_number': modbus_client.read_uint32(0x01),
            'model_number': modbus_client.read_uint32(0x03),
            'firmware_version': modbus_client.read_uint16(0x05),
            'network_channel': modbus_client.read_uint16(0x09),
            'system_id': modbus_client.read_uint16(0x0A),
            'uptime_hours': modbus_client.read_uint32(0x0E)
        }
        return jsonify({'success': True, 'info': info})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/device/channel/<int:channel>/toggle', methods=['POST'])
def toggle_channel(channel):
    """Turn channel on/off"""
    if not device_control:
        return jsonify({'success': False, 'error': 'Not connected'}), 400
    
    try:
        data = request.json
        enable = data.get('enable', True)
        
        if enable:
            device_control.turn_channel_on(channel)
        else:
            device_control.turn_channel_off(channel)
        
        return jsonify({'success': True, 'channel': channel, 'enabled': enable})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/device/channel/<int:channel>/setpoint', methods=['POST'])
def set_channel_setpoint(channel):
    """Set relay setpoint for channel"""
    if not device_control:
        return jsonify({'success': False, 'error': 'Not connected'}), 400
    
    try:
        data = request.json
        setpoint = float(data.get('setpoint'))
        
        device_control.set_relay_setpoint(channel, setpoint)
        
        return jsonify({'success': True, 'channel': channel, 'setpoint': setpoint})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/device/reset', methods=['POST'])
def reset_device():
    """Reset device"""
    if not device_control:
        return jsonify({'success': False, 'error': 'Not connected'}), 400
    
    try:
        device_control.reset_device()
        return jsonify({'success': True, 'message': 'Device reset initiated'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/radio/connect', methods=['POST'])
def radio_connect():
    """Connect to radio module"""
    global radio_receiver
    
    try:
        data = request.json
        port = data.get('port')
        baudrate = int(data.get('baudrate', 9600))
        
        # Close existing connection first
        if radio_receiver:
            try:
                radio_receiver.stop()
                if radio_receiver.serial and radio_receiver.serial.is_open:
                    radio_receiver.serial.close()
                time.sleep(0.5)  # Wait for port to release
            except:
                pass
            radio_receiver = None
        
        # Create and connect radio receiver  
        # Use RM024 API mode to receive sensor data with 0xCC frames
        radio_receiver = RadioReceiver(port, baudrate, api_mode=True, api_type='rm024')
        
        # Connect to serial port
        if not radio_receiver.connect():
            raise Exception("Failed to connect to radio module")
        
        # Setup event listeners BEFORE starting receiver
        setup_radio_listeners()
        
        # Start receiving (starts background thread)
        radio_receiver.start()
        
        return jsonify({'success': True, 'message': f'Radio connected on {port} at {baudrate} baud'})
    except Exception as e:
        # Clean up on error
        if radio_receiver:
            try:
                radio_receiver.stop()
                if radio_receiver.serial and radio_receiver.serial.is_open:
                    radio_receiver.serial.close()
            except:
                pass
            radio_receiver = None
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/radio/disconnect', methods=['POST'])
def radio_disconnect():
    """Disconnect radio"""
    global radio_receiver
    
    try:
        if radio_receiver:
            radio_receiver.stop()
            if radio_receiver.serial and radio_receiver.serial.is_open:
                radio_receiver.serial.close()
            radio_receiver = None
        return jsonify({'success': True})
    except Exception as e:
        radio_receiver = None
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/radio/check_mode')
def check_radio_mode():
    """Check if radio is in API mode or transparent mode"""
    if not radio_receiver:
        return jsonify({'success': False, 'error': 'Not connected'}), 400
    
    try:
        is_api = detect_api_mode(radio_receiver)
        return jsonify({
            'success': True,
            'mode': 'API' if is_api else 'Transparent',
            'api_mode': is_api,
            'note': 'API mode uses CC frame delimiter. Transparent mode sends raw data.'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/radio/switch_transparent', methods=['POST'])
def switch_to_transparent():
    """Switch radio from API mode to transparent mode"""
    if not radio_receiver:
        return jsonify({'success': False, 'error': 'Not connected'}), 400
    
    try:
        # Try to enter command mode (handles API mode automatically)
        if not enter_radio_command_mode(radio_receiver):
            return jsonify({'success': False, 'error': 'Failed to enter command mode'}), 400
        
        # Set transparent mode
        radio_receiver.serial.write(b'ATAP00\r')
        time.sleep(0.3)
        resp = radio_receiver.serial.read(100).decode('utf-8', errors='ignore')
        
        # Save to EEPROM
        radio_receiver.serial.write(b'ATWR\r')
        time.sleep(0.5)
        
        # Reset radio to apply
        radio_receiver.serial.write(b'ATFR\r')
        time.sleep(0.3)
        
        # Exit command mode
        exit_radio_command_mode(radio_receiver)
        
        # Wait for radio to reboot
        time.sleep(2.0)
        
        return jsonify({
            'success': True,
            'message': 'Radio switched to transparent mode and rebooted. Reconnect to continue.'
        })
    except Exception as e:
        exit_radio_command_mode(radio_receiver)
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/radio/status')
def radio_status():
    """Get radio status"""
    if not radio_receiver:
        return jsonify({'success': False, 'error': 'Not connected'}), 400
    
    try:
        rssi = radio_receiver.get_rssi()
        mac = radio_receiver.get_mac_address()
        
        return jsonify({
            'success': True,
            'rssi': rssi,
            'mac': mac,
            'packets_received': radio_receiver.packet_count if hasattr(radio_receiver, 'packet_count') else 0
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/radio/configure', methods=['POST'])
def radio_configure():
    """Configure radio with AT commands"""
    if not radio_receiver:
        return jsonify({'success': False, 'error': 'Not connected'}), 400
    
    try:
        data = request.json
        channel = int(data.get('channel', 25))
        is_primary = data.get('is_primary', False)
        system_id = int(data.get('system_id', 37))
        
        # Enter command mode with proper timing
        if not enter_radio_command_mode(radio_receiver):
            return jsonify({'success': False, 'error': 'Failed to enter command mode'}), 400
        
        commands = []
        
        # Set RF channel
        cmd = f"ATCH{channel:02d}\r"
        radio_receiver.serial.write(cmd.encode())
        time.sleep(0.2)
        resp = radio_receiver.serial.read(100).decode('utf-8', errors='ignore')
        commands.append({'cmd': cmd.strip(), 'response': resp.strip()})
        
        # Set primary/secondary
        mode_val = '01' if is_primary else '00'
        cmd = f"ATSP{mode_val}\r"
        radio_receiver.serial.write(cmd.encode())
        time.sleep(0.2)
        resp = radio_receiver.serial.read(100).decode('utf-8', errors='ignore')
        commands.append({'cmd': cmd.strip(), 'response': resp.strip()})
        
        # Set System ID
        cmd = f"ATSY{system_id:02d}\r"
        radio_receiver.serial.write(cmd.encode())
        time.sleep(0.2)
        resp = radio_receiver.serial.read(100).decode('utf-8', errors='ignore')
        commands.append({'cmd': cmd.strip(), 'response': resp.strip()})
        
        # Save to EEPROM
        cmd = "ATWR\r"
        radio_receiver.serial.write(cmd.encode())
        time.sleep(0.5)
        resp = radio_receiver.serial.read(100).decode('utf-8', errors='ignore')
        commands.append({'cmd': cmd.strip(), 'response': resp.strip()})
        
        # Exit command mode
        exit_radio_command_mode(radio_receiver)
        
        return jsonify({
            'success': True,
            'message': 'Radio configured successfully',
            'commands': commands
        })
    except Exception as e:
        exit_radio_command_mode(radio_receiver)
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/radio/send_test', methods=['POST'])
def radio_send_test():
    """Send test packet spoofing a sensor with full packet customization"""
    if not radio_receiver:
        return jsonify({'success': False, 'error': 'Not connected'}), 400
    
    try:
        data = request.json
        sensor_address = data.get('sensor_address')  # Optional override
        channel = int(data.get('channel', 1))
        reading = float(data.get('reading', 25.5))
        gas_type = int(data.get('gas_type', 0))  # H2S
        sensor_type = int(data.get('sensor_type', 0))  # EC
        battery = int(data.get('battery', 85))
        fault_code = int(data.get('fault_code', 0))  # No fault
        unit_type = data.get('unit_type', '6900')
        
        # Send test packet with all parameters
        radio_receiver.send_test_packet(
            channel=channel,
            reading=reading,
            gas_type=gas_type,
            sensor_type=sensor_type,
            battery_pct=battery,
            fault_code=fault_code,
            unit_type=unit_type,
            sensor_address=sensor_address
        )
        
        addr_info = f"@{sensor_address}" if sensor_address else f"@{channel}"
        fault_name = {
            0: "No Fault", 1: "Board Timeout", 2: "Bad Reading", 
            3: "High Current", 4: "ADC Error", 5: "Null Error",
            7: "Checksum Error", 8: "Duplicate Address (F8)", 
            9: "Radio Timeout", 10: "Not Connected"
        }.get(fault_code, f"Fault {fault_code}")
        
        gas_names = {
            0: "H2S", 1: "SO2", 2: "O2", 3: "CO", 4: "CL2",
            5: "CO2", 6: "LEL", 7: "VOC", 8: "Tank", 9: "HCl", 10: "NH3"
        }
        gas_name = gas_names.get(gas_type, f"Gas {gas_type}")
        
        return jsonify({
            'success': True,
            'message': f'Test packet sent {addr_info}: CH{channel} = {reading} PPM {gas_name}, Battery: {battery}%, {fault_name}, Unit: OI-{unit_type}'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/radio/f8_address_change', methods=['POST'])
def radio_f8_address_change():
    """Send F8 diagnostic command to change sensor address"""
    if not radio_receiver:
        return jsonify({'success': False, 'error': 'Not connected'}), 400
    
    try:
        data = request.json
        current_address = int(data.get('current_address'))
        new_address = int(data.get('new_address'))
        
        if not 1 <= current_address <= 255 or not 1 <= new_address <= 255:
            return jsonify({'success': False, 'error': 'Addresses must be 1-255'}), 400
        
        if current_address == new_address:
            return jsonify({'success': False, 'error': 'Addresses must be different'}), 400
        
        # Send F8 diagnostic command
        success = radio_receiver.send_address_change_command(current_address, new_address)
        
        if success:
            return jsonify({
                'success': True,
                'message': f'F8 command sent: Sensor {current_address} → {new_address}. Sensor must be in Diagnostic Mode (Mode 5) to accept.'
            })
        else:
            return jsonify({'success': False, 'error': 'Failed to send F8 command'}), 400
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/radio/profile')
def get_radio_profile():
    """Read radio EEPROM profile via binary protocol (0xCC commands)"""
    if not radio_receiver:
        return jsonify({'success': False, 'error': 'Not connected'}), 400
    
    try:
        # Temporarily stop the receiver thread to avoid conflicts
        was_running = radio_receiver.running
        if was_running:
            radio_receiver.stop()
            time.sleep(0.5)  # Give receiver time to fully stop
        
        # Try direct binary protocol reads (should work in transparent mode)
        # Clear any buffered data first
        radio_receiver.serial.reset_input_buffer()
        time.sleep(0.2)
        
        # Use binary protocol to read EEPROM registers
        def read_eeprom_register(address, retries=3):
            """Read single EEPROM register using binary protocol with retries"""
            for attempt in range(retries):
                # Command: CC C2 <address_high> <address_low> <checksum>
                cmd = bytearray([0xCC, 0xC2, (address >> 8) & 0xFF, address & 0xFF])
                checksum = sum(cmd[1:]) & 0xFF
                cmd.append(checksum)
                
                # Clear buffer before sending
                radio_receiver.serial.reset_input_buffer()
                time.sleep(0.05)
                
                # Send command
                radio_receiver.serial.write(cmd)
                time.sleep(0.3)  # Wait for response
                
                # Read all available data
                available = radio_receiver.serial.in_waiting
                if available > 0:
                    response = radio_receiver.serial.read(available)
                    print(f"EEPROM read addr=0x{address:04X} attempt {attempt+1}: sent={cmd.hex()} received={response.hex()} ({len(response)} bytes)")
                    
                    # Search for CC C2 response in buffer (might have sensor data mixed in)
                    for i in range(len(response) - 5):
                        if response[i] == 0xCC and response[i+1] == 0xC2:
                            # Found potential response, verify checksum
                            addr_h = response[i+2]
                            addr_l = response[i+3]
                            value = response[i+4]
                            recv_checksum = response[i+5] if i+5 < len(response) else 0
                            expected_checksum = (0xC2 + addr_h + addr_l + value) & 0xFF
                            
                            if recv_checksum == expected_checksum:
                                print(f"  ✓ Found valid response at offset {i}: value=0x{value:02X}")
                                return value
                else:
                    print(f"EEPROM read addr=0x{address:04X} attempt {attempt+1}: sent={cmd.hex()} received NOTHING")
                
                time.sleep(0.1)  # Wait before retry
            
            return None
        
        profile = {}
        
        # Read EEPROM registers (from BINARY_PROTOCOL_GUIDE.md)
        channel = read_eeprom_register(0x0000)  # Network Channel
        system_id_h = read_eeprom_register(0x0001)  # System ID high
        system_id_l = read_eeprom_register(0x0002)  # System ID low
        mode = read_eeprom_register(0x0003)  # Radio Mode
        api_ctrl = read_eeprom_register(0x0004)  # API Control (0xC1)
        baud = read_eeprom_register(0x0005)  # Baud Rate
        rf_power = read_eeprom_register(0x0006)  # RF Power
        
        # Format profile data
        if channel is not None:
            profile['channel'] = str(channel)
        
        if system_id_h is not None and system_id_l is not None:
            system_id = (system_id_h << 8) | system_id_l
            profile['system_id'] = f"0x{system_id:04X}"
        
        if mode is not None:
            profile['mode'] = 'Secondary (RX Only)' if mode == 0 else 'Primary (TX/RX)'
        
        if api_ctrl is not None:
            api_features = []
            if api_ctrl & 0x01:
                api_features.append('API Receive')
            if api_ctrl & 0x02:
                api_features.append('API Transmit')
            if api_ctrl & 0x04:
                api_features.append('API ACK')
            profile['api_mode'] = ', '.join(api_features) if api_features else 'Transparent'
            profile['api_ctrl_raw'] = f"0x{api_ctrl:02X}"
        
        if baud is not None:
            baud_map = {0: '9600', 1: '19200', 2: '38400', 3: '57600', 4: '115200'}
            profile['baudrate'] = baud_map.get(baud, str(baud))
        
        if rf_power is not None:
            profile['rf_power'] = f"{rf_power} dBm"
        
        # Restart receiver if it was running
        if was_running:
            radio_receiver.start()
        
        return jsonify({'success': True, 'profile': profile})
    except Exception as e:
        # Make sure to restart receiver on error
        if was_running:
            try:
                radio_receiver.start()
            except:
                pass
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/radio/command_mode', methods=['POST'])
def toggle_command_mode():
    """Enter or exit command mode"""
    if not radio_receiver:
        return jsonify({'success': False, 'error': 'Not connected'}), 400
    
    try:
        data = request.get_json()
        enter = data.get('enter', True)
        
        if enter:
            # Enter command mode with AT+++
            cmd = bytearray(b'AT+++\r')
            radio_receiver.serial.reset_input_buffer()
            radio_receiver.serial.write(cmd)
            time.sleep(0.3)
            response = radio_receiver.serial.read(100)
            
            if b'\xcc\x43\x4f\x4d' in response:  # CC COM
                return jsonify({'success': True, 'message': '✓ Entered command mode (data flow stopped)'})
            else:
                return jsonify({'success': False, 'error': f'Failed to enter command mode. Response: {response.hex()}'}), 400
        else:
            # Exit command mode with ATO
            cmd = bytearray([0xCC, 0x41, 0x54, 0x4F, 0x0D])  # CC ATO <cr>
            radio_receiver.serial.write(cmd)
            time.sleep(0.2)
            response = radio_receiver.serial.read(100)
            
            if b'\xcc\x44\x41\x54' in response:  # CC DAT
                return jsonify({'success': True, 'message': '✓ Exited command mode (data flow resumed)'})
            else:
                return jsonify({'success': True, 'message': 'Command sent (sensor data should resume)'})
                
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/radio/enable_api_mode', methods=['POST'])
def enable_api_mode():
    """Enable API Receive mode on the radio using binary protocol"""
    if not radio_receiver:
        return jsonify({'success': False, 'error': 'Not connected'}), 400
    
    try:
        # Write to EEPROM register 0x0004 (API Control) with value 0x01 (API Receive enabled)
        # Command: CC C3 <addr_high> <addr_low> <value> <checksum>
        address = 0x0004
        value = 0x01  # Enable API Receive (bit 0)
        
        cmd = bytearray([0xCC, 0xC3, (address >> 8) & 0xFF, address & 0xFF, value])
        checksum = sum(cmd[1:]) & 0xFF
        cmd.append(checksum)
        
        # Clear buffer
        radio_receiver.serial.reset_input_buffer()
        
        # Send command
        radio_receiver.serial.write(cmd)
        time.sleep(0.2)
        
        # Read response: CC C3 <addr_high> <addr_low> <status> <checksum>
        # Status: 00 = success
        response = radio_receiver.serial.read(6)
        
        if len(response) == 6 and response[0] == 0xCC and response[1] == 0xC3:
            if response[4] == 0x00:
                # Success - now reboot radio to apply changes
                # Send reboot command: CC C0 <checksum>
                reboot_cmd = bytearray([0xCC, 0xC0, 0xC0])
                radio_receiver.serial.write(reboot_cmd)
                
                return jsonify({
                    'success': True,
                    'message': 'API Receive mode enabled. Radio will reboot. Please reconnect.'
                })
            else:
                return jsonify({
                    'success': False,
                    'error': f'Write failed with status: 0x{response[4]:02X}'
                }), 400
        else:
            return jsonify({
                'success': False,
                'error': 'Invalid response from radio'
            }), 400
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/radio/wireless_at', methods=['POST'])
def send_wireless_at():
    """Send AT command wirelessly to remote radio (primary mode only)"""
    if not radio_receiver:
        return jsonify({'success': False, 'error': 'Not connected'}), 400
    
    try:
        data = request.json
        command = data.get('command', '').upper()
        
        if not command.startswith('AT'):
            return jsonify({'success': False, 'error': 'Command must start with AT'}), 400
        
        # Enter local command mode
        if not enter_radio_command_mode(radio_receiver):
            return jsonify({'success': False, 'error': 'Failed to enter command mode'}), 400
        
        # Enter remote command mode (sends AT+++ wirelessly)
        radio_receiver.serial.write(b'ATRC\r')
        time.sleep(0.3)
        resp = radio_receiver.serial.read(100)
        
        if b'OK' not in resp:
            exit_radio_command_mode(radio_receiver)
            return jsonify({'success': False, 'error': 'Failed to enter remote command mode'}), 400
        
        # Send command wirelessly
        cmd_bytes = (command + '\r').encode()
        radio_receiver.serial.write(cmd_bytes)
        time.sleep(0.5)
        
        # Read response
        response = radio_receiver.serial.read(200).decode('utf-8', errors='ignore')
        
        # Exit remote command mode
        radio_receiver.serial.write(b'ATCN\r')
        time.sleep(0.2)
        
        # Exit local command mode
        exit_radio_command_mode(radio_receiver)
        
        return jsonify({
            'success': True,
            'response': response.strip(),
            'message': f'Sent wireless command: {command}'
        })
    except Exception as e:
        # Try to exit command modes
        try:
            radio_receiver.serial.write(b'ATCN\r')
            time.sleep(0.2)
        except:
            pass
        exit_radio_command_mode(radio_receiver)
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/radio/direct_at', methods=['POST'])
def send_direct_at():
    """Send AT command directly to local radio"""
    if not radio_receiver:
        return jsonify({'success': False, 'error': 'Not connected'}), 400
    
    try:
        data = request.json
        command = data.get('command', '').upper()
        
        if not command.startswith('AT'):
            return jsonify({'success': False, 'error': 'Command must start with AT'}), 400
        
        # Enter command mode
        if not enter_radio_command_mode(radio_receiver):
            return jsonify({'success': False, 'error': 'Failed to enter command mode'}), 400
        
        # Send command
        cmd_bytes = (command + '\r').encode()
        radio_receiver.serial.write(cmd_bytes)
        time.sleep(0.5)
        
        # Read response
        response = radio_receiver.serial.read(200).decode('utf-8', errors='ignore')
        
        # Exit command mode
        exit_radio_command_mode(radio_receiver)
        
        return jsonify({
            'success': True,
            'response': response.strip(),
            'message': f'Sent command: {command}'
        })
    except Exception as e:
        exit_radio_command_mode(radio_receiver)
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/radio/remote_at', methods=['POST'])
def send_remote_at():
    """Send AT command wirelessly to remote radio on specific channel"""
    if not radio_receiver:
        return jsonify({'success': False, 'error': 'Not connected'}), 400
    
    try:
        data = request.json
        command = data.get('command', '').upper()
        target_channel = int(data.get('channel', 25))
        
        if not command.startswith('AT'):
            return jsonify({'success': False, 'error': 'Command must start with AT'}), 400
        
        # Enter local command mode
        if not enter_radio_command_mode(radio_receiver):
            return jsonify({'success': False, 'error': 'Failed to enter command mode'}), 400
        
        # Save current channel
        radio_receiver.serial.write(b'ATCH\r')
        time.sleep(0.3)
        resp = radio_receiver.serial.read(100).decode('utf-8', errors='ignore')
        try:
            current_channel = int(resp.replace('OK', '').strip())
        except:
            current_channel = 25
        
        # Switch to target channel
        cmd = f'ATCH{target_channel:02d}\r'
        radio_receiver.serial.write(cmd.encode())
        time.sleep(0.3)
        radio_receiver.serial.read(100)
        
        # Exit and re-enter to apply channel change
        exit_radio_command_mode(radio_receiver)
        if not enter_radio_command_mode(radio_receiver):
            return jsonify({'success': False, 'error': 'Failed to re-enter command mode'}), 400
        
        # Enter remote command mode (ATRC)
        radio_receiver.serial.write(b'ATRC\r')
        time.sleep(0.5)
        resp = radio_receiver.serial.read(100)
        
        if b'OK' not in resp:
            # Restore original channel
            cmd = f'ATCH{current_channel:02d}\r'
            radio_receiver.serial.write(cmd.encode())
            time.sleep(0.3)
            exit_radio_command_mode(radio_receiver)
            return jsonify({'success': False, 'error': f'No radio found on channel {target_channel}'}), 400
        
        # Send command to remote radio
        cmd_bytes = (command + '\r').encode()
        radio_receiver.serial.write(cmd_bytes)
        time.sleep(0.5)
        
        # Read response
        response = radio_receiver.serial.read(200).decode('utf-8', errors='ignore')
        
        # Exit remote command mode
        radio_receiver.serial.write(b'ATCN\r')
        time.sleep(0.3)
        
        # Restore original channel
        cmd = f'ATCH{current_channel:02d}\r'
        radio_receiver.serial.write(cmd.encode())
        time.sleep(0.3)
        
        # Exit command mode
        exit_radio_command_mode(radio_receiver)
        
        return jsonify({
            'success': True,
            'response': response.strip(),
            'message': f'Sent {command} to radio on channel {target_channel}'
        })
    except Exception as e:
        exit_radio_command_mode(radio_receiver)
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/radio/scan', methods=['POST'])
def scan_radio_channels():
    """Scan for radios on different channels"""
    if not radio_receiver:
        return jsonify({'success': False, 'error': 'Not connected'}), 400
    
    try:
        data = request.json
        start_ch = int(data.get('start', 1))
        end_ch = int(data.get('end', 78))
        
        found_radios = []
        current_channel = None
        
        # Enter command mode with proper timing
        if not enter_radio_command_mode(radio_receiver):
            return jsonify({'success': False, 'error': 'Failed to enter command mode'}), 400
        
        # Get current channel to restore later
        radio_receiver.serial.write(b'ATCH\r')
        time.sleep(0.3)
        resp = radio_receiver.serial.read(100).decode('utf-8', errors='ignore')
        try:
            current_channel = int(resp.replace('OK', '').strip())
        except:
            current_channel = 25  # Default
        
        # Scan each channel
        for ch in range(start_ch, end_ch + 1):
            # Set channel
            cmd = f'ATCH{ch:02d}\r'
            radio_receiver.serial.write(cmd.encode())
            time.sleep(0.3)
            radio_receiver.serial.read(100)  # Clear buffer
            
            # Exit and re-enter command mode to apply channel change
            exit_radio_command_mode(radio_receiver)
            if not enter_radio_command_mode(radio_receiver):
                continue  # Skip this channel if can't enter command mode
            
            # Try to communicate with remote radio
            radio_receiver.serial.write(b'ATRC\r')
            time.sleep(0.5)
            resp = radio_receiver.serial.read(100)
            
            if b'OK' in resp:
                # Found a radio! Query its settings
                radio_info = {'channel': ch}
                
                # Query settings
                commands = [
                    ('ATSP\r', 'mode'),
                    ('ATSY\r', 'system_id'),
                    ('ATBD\r', 'baudrate'),
                    ('ATMY\r', 'mac')  # Get MAC address
                ]
                
                for cmd, key in commands:
                    radio_receiver.serial.write(cmd.encode())
                    time.sleep(0.3)
                    response = radio_receiver.serial.read(100).decode('utf-8', errors='ignore')
                    value = response.replace('OK', '').strip()
                    
                    # Parse values
                    if key == 'mode':
                        # Primary/Monitor = 01, but sensors don't have this setting
                        # If baud is 9600, it's a sensor, otherwise monitor
                        radio_info['is_primary'] = (value == '01')
                        radio_info[key] = value
                    elif key == 'baudrate':
                        baud_map = {'0': '9600', '1': '19200', '2': '38400', '3': '57600', '4': '115200'}
                        radio_info[key] = baud_map.get(value, value)
                    else:
                        radio_info[key] = value
                
                # Determine radio type: sensor (9600 baud) or monitor (115200 baud)
                if radio_info.get('baudrate') == '9600':
                    radio_info['type'] = 'sensor'
                    radio_info['is_primary'] = False  # Sensors are never primary
                else:
                    radio_info['type'] = 'monitor'
                    # is_primary already set from ATSP
                
                # Exit remote command mode
                radio_receiver.serial.write(b'ATCN\r')
                time.sleep(0.3)
                
                found_radios.append(radio_info)
            else:
                # No radio on this channel, exit command mode if entered
                try:
                    radio_receiver.serial.write(b'ATCN\r')
                    time.sleep(0.2)
                except:
                    pass
        
        # Restore original channel
        if current_channel:
            cmd = f'ATCH{current_channel:02d}\r'
            radio_receiver.serial.write(cmd.encode())
            time.sleep(0.3)
            radio_receiver.serial.write(b'ATWR\r')  # Save
            time.sleep(0.5)
        
        # Exit command mode
        exit_radio_command_mode(radio_receiver)
        
        return jsonify({
            'success': True,
            'radios': found_radios,
            'scanned': end_ch - start_ch + 1
        })
    except Exception as e:
        # Try to exit command mode
        exit_radio_command_mode(radio_receiver)
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/radio/bulk_configure', methods=['POST'])
def bulk_configure_radios():
    """Bulk reconfigure multiple radios wirelessly"""
    if not radio_receiver:
        return jsonify({'success': False, 'error': 'Not connected'}), 400
    
    try:
        data = request.json
        radios = data.get('radios', [])
        new_channel = int(data.get('new_channel'))
        mode = data.get('mode', '')
        system_id = int(data.get('system_id', 37))
        
        configured_count = 0
        messages = []
        
        # Enter command mode with proper timing
        if not enter_radio_command_mode(radio_receiver):
            return jsonify({'success': False, 'error': 'Failed to enter local command mode'}), 400
        
        # Configure each radio
        for radio in radios:
            old_channel = radio['channel']
            radio_type = radio.get('type', 'monitor')
            
            # Switch to radio's current channel
            cmd = f'ATCH{old_channel:02d}\r'
            radio_receiver.serial.write(cmd.encode())
            time.sleep(0.3)
            radio_receiver.serial.read(100)
            
            # Exit and re-enter to apply channel change
            exit_radio_command_mode(radio_receiver)
            if not enter_radio_command_mode(radio_receiver):
                continue  # Skip this radio if can't enter command mode
            
            # Enter remote command mode
            radio_receiver.serial.write(b'ATRC\r')
            time.sleep(0.5)
            resp = radio_receiver.serial.read(100)
            
            if b'OK' in resp:
                # Send configuration commands
                commands = []
                
                # Set new channel
                cmd = f'ATCH{new_channel:02d}\r'
                radio_receiver.serial.write(cmd.encode())
                time.sleep(0.3)
                commands.append(f'Channel → {new_channel}')
                
                # Set system ID
                cmd = f'ATSY{system_id:02d}\r'
                radio_receiver.serial.write(cmd.encode())
                time.sleep(0.3)
                commands.append(f'SysID → {system_id}')
                
                # Convert mode if requested
                if mode == 'sensor':
                    # Sensor mode: 9600 baud, no primary/secondary setting
                    radio_receiver.serial.write(b'ATBD0\r')  # 9600
                    time.sleep(0.3)
                    commands.append('Mode → Sensor (9600)')
                elif mode == 'monitor-only':
                    # Monitor only (not primary): 115200 baud, secondary
                    radio_receiver.serial.write(b'ATSP00\r')  # Secondary
                    time.sleep(0.3)
                    radio_receiver.serial.write(b'ATBD4\r')  # 115200
                    time.sleep(0.3)
                    commands.append('Mode → Monitor Only (Secondary, 115200)')
                # If mode is empty, keep current configuration
                
                # Save to EEPROM
                radio_receiver.serial.write(b'ATWR\r')
                time.sleep(0.5)
                
                # Exit remote command mode
                radio_receiver.serial.write(b'ATCN\r')
                time.sleep(0.3)
                
                configured_count += 1
                messages.append(f"CH{old_channel} ({radio_type}): {', '.join(commands)}")
            
            # Exit local command mode and re-enter for next radio
            exit_radio_command_mode(radio_receiver)
            if not enter_radio_command_mode(radio_receiver):
                break  # Can't continue if we can't enter command mode
        
        # Exit command mode
        exit_radio_command_mode(radio_receiver)
        
        return jsonify({
            'success': True,
            'configured': configured_count,
            'message': '\n'.join(messages)
        })
    except Exception as e:
        # Try to exit command mode
        exit_radio_command_mode(radio_receiver)
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/radio/finalize', methods=['POST'])
def finalize_network():
    """Set one monitor as primary and gracefully exit network"""
    global radio_receiver
    
    if not radio_receiver:
        return jsonify({'success': False, 'error': 'Not connected'}), 400
    
    try:
        data = request.json
        primary_identifier = data.get('primary_identifier')  # MAC address or channel
        
        if not primary_identifier:
            return jsonify({'success': False, 'error': 'No primary identifier provided'}), 400
        
        # Enter command mode with proper timing
        if not enter_radio_command_mode(radio_receiver):
            return jsonify({'success': False, 'error': 'Failed to enter command mode'}), 400
        
        # Try to parse as channel number
        try:
            target_channel = int(primary_identifier)
        except:
            # It's a MAC address, need to scan to find channel
            return jsonify({'success': False, 'error': 'MAC address lookup not implemented yet. Please use channel number'}), 400
        
        # Switch to target channel
        cmd = f'ATCH{target_channel:02d}\r'
        radio_receiver.serial.write(cmd.encode())
        time.sleep(0.3)
        radio_receiver.serial.read(100)
        
        # Exit and re-enter to apply channel change
        exit_radio_command_mode(radio_receiver)
        if not enter_radio_command_mode(radio_receiver):
            return jsonify({'success': False, 'error': 'Failed to re-enter command mode after channel change'}), 400
        
        # Enter remote command mode to target radio
        radio_receiver.serial.write(b'ATRC\r')
        time.sleep(0.5)
        resp = radio_receiver.serial.read(100)
        
        if b'OK' in resp:
            # Set as primary monitor
            radio_receiver.serial.write(b'ATSP01\r')  # Primary
            time.sleep(0.3)
            radio_receiver.serial.write(b'ATBD4\r')  # 115200
            time.sleep(0.3)
            radio_receiver.serial.write(b'ATWR\r')  # Save
            time.sleep(0.5)
            
            # Exit remote command mode
            radio_receiver.serial.write(b'ATCN\r')
            time.sleep(0.3)
            
            message = f'Radio on channel {target_channel} set as Primary Monitor'
        else:
            message = f'No radio found on channel {target_channel}'
        
        # Exit command mode
        exit_radio_command_mode(radio_receiver)
        
        # Gracefully disconnect
        try:
            radio_receiver.stop()
        except:
            pass
        
        radio_receiver = None
        
        return jsonify({
            'success': True,
            'message': message + ' - Connection closed'
        })
    except Exception as e:
        exit_radio_command_mode(radio_receiver)
        return jsonify({'success': False, 'error': str(e)}), 400

@socketio.on('connect')
def handle_connect():
    """Client connected via WebSocket"""
    print('Client connected')
    emit('status', {'message': 'Connected to OI Monitor Control Center'})

@socketio.on('start_monitoring')
def start_monitoring():
    """Start real-time monitoring"""
    global monitoring_active, monitoring_thread
    
    if monitoring_active:
        emit('error', {'message': 'Monitoring already active'})
        return
    
    monitoring_active = True
    monitoring_thread = threading.Thread(target=monitoring_loop, daemon=True)
    monitoring_thread.start()
    
    emit('status', {'message': 'Monitoring started'})

@socketio.on('stop_monitoring')
def stop_monitoring():
    """Stop real-time monitoring"""
    global monitoring_active
    monitoring_active = False
    emit('status', {'message': 'Monitoring stopped'})

def monitoring_loop():
    """Real-time monitoring loop"""
    global monitoring_active
    
    while monitoring_active:
        try:
            # Read Modbus data
            if modbus_client:
                channels = []
                for ch in range(1, 33):
                    addr = 0x20 + (ch - 1) * 2
                    value = modbus_client.read_float32(addr)
                    if value != 0.0:
                        channels.append({
                            'channel': ch,
                            'value': round(value, 2),
                            'timestamp': datetime.now().isoformat()
                        })
                
                socketio.emit('modbus_data', {'channels': channels})
            
            # Read radio packets
            if radio_receiver:
                # Check for new packets
                socketio.emit('radio_status', {
                    'connected': True,
                    'timestamp': datetime.now().isoformat()
                })
            
            time.sleep(2)  # Update every 2 seconds
            
        except Exception as e:
            socketio.emit('error', {'message': str(e)})
            time.sleep(5)

@app.route('/api/gas_types')
def get_gas_types():
    """Get list of all gas types"""
    gas_list = [{'code': code, 'name': name} for code, name in GAS_TYPES.items()]
    return jsonify({'gas_types': gas_list})

@app.route('/api/sensor_types')
def get_sensor_types():
    """Get list of sensor types"""
    sensor_list = [{'code': code, 'name': name} for code, name in SENSOR_TYPES.items()]
    return jsonify({'sensor_types': sensor_list})

# MQTT Configuration
mqtt_config = {
    'broker': 'a1bcc059f5f74a6d8271e8b567fecc6d.s1.eu.hivemq.cloud',
    'port': 8883,
    'username': 'laird',
    'password': 'LairdRM024',
    'base_topic': 'oi_monitors',
    'use_tls': True
}

@app.route('/api/mqtt/config', methods=['GET'])
def get_mqtt_config():
    """Get MQTT configuration"""
    return jsonify(mqtt_config)

@app.route('/api/mqtt/config', methods=['POST'])
def set_mqtt_config():
    """Set MQTT configuration"""
    global mqtt_config
    try:
        data = request.json
        mqtt_config.update(data)
        return jsonify({'success': True, 'config': mqtt_config})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/mqtt/test', methods=['POST'])
def test_mqtt():
    """Test MQTT connection"""
    try:
        import paho.mqtt.client as mqtt
        import ssl
        
        def on_connect(client, userdata, flags, rc):
            userdata['connected'] = rc == 0
            userdata['rc'] = rc
        
        result = {'connected': False, 'rc': -1}
        client = mqtt.Client(userdata=result)
        
        if mqtt_config.get('username'):
            client.username_pw_set(mqtt_config['username'], mqtt_config['password'])
        
        # Enable TLS/SSL if configured (required for HiveMQ port 8883)
        if mqtt_config.get('use_tls', False) or mqtt_config.get('port') == 8883:
            client.tls_set(cert_reqs=ssl.CERT_REQUIRED, tls_version=ssl.PROTOCOL_TLSv1_2)
        
        client.on_connect = on_connect
        client.connect(mqtt_config['broker'], mqtt_config['port'], 10)
        client.loop_start()
        time.sleep(3)
        client.loop_stop()
        client.disconnect()
        
        if result['connected']:
            return jsonify({'success': True, 'message': 'MQTT connection successful'})
        else:
            error_codes = {
                1: 'Connection refused - incorrect protocol version',
                2: 'Connection refused - invalid client identifier',
                3: 'Connection refused - server unavailable',
                4: 'Connection refused - bad username or password',
                5: 'Connection refused - not authorized'
            }
            error_msg = error_codes.get(result['rc'], f'Connection failed (code {result["rc"]})')
            return jsonify({'success': False, 'error': error_msg}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

if __name__ == '__main__':
    print("=" * 60)
    print("  OI Monitor Control Center - Web GUI")
    print("=" * 60)
    print()
    print("  Starting web server...")
    print("  Open your browser to: http://localhost:5000")
    print()
    print("  Features:")
    print("    ✓ Modbus device connection and control")
    print("    ✓ Real-time channel monitoring")
    print("    ✓ Radio configuration and testing")
    print("    ✓ Device diagnostics and settings")
    print()
    print("  Press Ctrl+C to stop")
    print("=" * 60)
    print()
    
    socketio.run(app, host='0.0.0.0', port=5000, debug=True, allow_unsafe_werkzeug=True)
