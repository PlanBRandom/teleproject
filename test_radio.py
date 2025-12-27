#!/usr/bin/env python3
"""
Quick Radio Test - Test Laird radio module functionality
"""

from pipeline.radio_receiver import RadioReceiver
import time


def print_header(text):
    print(f"\n{'='*70}")
    print(f"  {text}")
    print(f"{'='*70}\n")


def print_subheader(text):
    print(f"\n--- {text} ---")


def test_radio():
    """Test radio module"""
    print_header("OI Gen2 Wireless Radio Test")
    
    # Get configuration
    print("Enter COM port for Laird radio: ", end='')
    port = input().strip()
    
    print("\nEnter network channel (1-78, default 25): ", end='')
    channel_input = input().strip()
    network_channel = int(channel_input) if channel_input else 25
    
    print("\nIs this a PRIMARY or SECONDARY receiver?")
    print("  PRIMARY - Can transmit and receive (monitor replacement)")
    print("  SECONDARY - Receive only (passive listener)")
    print("Enter mode (primary/secondary, default secondary): ", end='')
    mode_input = input().strip().lower()
    is_primary = mode_input.startswith('p')
    
    print(f"\nConnecting to {port}...")
    receiver = RadioReceiver(port, baudrate=115200, api_mode=True)
    
    if not receiver.connect():
        print("✗ Failed to connect to radio")
        return
    
    print("✓ Connected to radio module")
    
    # Get MAC address
    print_subheader("Radio Information")
    mac = receiver.get_mac_address()
    if mac:
        print(f"✓ MAC Address: {mac}")
    else:
        print("✗ Could not read MAC address")
    
    # Get RSSI
    rssi = receiver.get_rssi()
    if rssi:
        print(f"✓ Current RSSI: {rssi} dBm")
        if rssi > -70:
            print("  Signal: Excellent ████████████")
        elif rssi > -85:
            print("  Signal: Good      ████████░░░░")
        elif rssi > -95:
            print("  Signal: Fair      ████░░░░░░░░")
        else:
            print("  Signal: Poor      ██░░░░░░░░░░")
    else:
        print("✗ Could not read RSSI")
    
    # Set channel
    print_subheader("Setting RF Channel")
    mode_str = "primary transmitter" if is_primary else "secondary receiver"
    if receiver.set_rf_channel(network_channel):
        print(f"✓ RF Channel set to {network_channel} ({mode_str})")
    else:
        print("✗ Failed to set RF channel")
    
    # Test transmission (primary mode only)
    if is_primary:
        print_subheader("Test Transmission (Primary Mode)")
        print("Send a test sensor reading? (y/n, default n): ", end='')
        send_test = input().strip().lower().startswith('y')
        
        if send_test:
            print("\nEnter test channel (1-32): ", end='')
            test_channel = int(input().strip() or "1")
            print("Enter test reading value: ", end='')
            test_reading = float(input().strip() or "50.0")
            print("Enter gas type (0=H2S, 1=CO, 2=O2, 3=LEL, default 0): ", end='')
            test_gas = int(input().strip() or "0")
            
            gas_names = {0: "H2S", 1: "CO", 2: "O2", 3: "LEL"}
            gas_name = gas_names.get(test_gas, f"Gas{test_gas}")
            
            print(f"\nSending: Ch {test_channel} = {test_reading:.2f} PPM ({gas_name})...")
            if receiver.send_test_packet(test_channel, test_reading, test_gas):
                print("✓ Test packet transmitted")
                print("  Any receiver on this network should detect this packet")
            else:
                print("✗ Failed to transmit test packet")
            time.sleep(2)
    
    # Listen for packets
    print_subheader("Listening for Sensor Packets")
    print("How many seconds to listen? (default 30): ", end='')
    listen_time = int(input().strip() or "30")
    print(f"\nListening for {listen_time} seconds...")
    print("(Sensors typically transmit every 60s, or every 5s during gas alerts)\n")
    
    packet_count = [0]
    
    def on_packet(msg):
        packet_count[0] += 1
        print(f"\n✓ Packet {packet_count[0]} received:")
        print(f"  Protocol:  {msg.protocol}")
        print(f"  Channel:   {msg.channel}")
        print(f"  Reading:   {msg.reading:.2f}")
        
        if msg.protocol == 1:
            from pipeline.registers import GAS_TYPE_NAMES, SENSOR_TYPE_NAMES, MODE_NAMES, FAULT_NAMES
            print(f"  Gas Type:  {GAS_TYPE_NAMES.get(msg.gas_type, 'Unknown')}")
            print(f"  Sensor:    {SENSOR_TYPE_NAMES.get(msg.sensor_type, 'Unknown')}")
            print(f"  Mode:      {MODE_NAMES.get(msg.sensor_mode, 'Unknown')}")
            print(f"  Battery:   {msg.battery_voltage:.1f}V")
            print(f"  Fault:     {FAULT_NAMES.get(msg.fault_code, 'Unknown')}")
            if msg.text:
                print(f"  Text:      {msg.text}")
        elif msg.protocol == 2:
            print(f"  Type:      GAS ALERT (quick detect)")
        elif msg.protocol == 7:
            print(f"  Type:      Maintenance")
            print(f"  Null Days: {msg.days_since_null}")
            print(f"  Cal Days:  {msg.days_since_cal}")
    
    receiver.register_callback(on_packet)
    receiver.start()
    
    time.sleep(listen_time)
    
    receiver.stop()
    receiver.disconnect()
    
    print(f"\n{'='*70}")
    if packet_count[0] > 0:
        print(f"✓ Test Complete - Received {packet_count[0]} sensor packets")
    else:
        print(f"⚠️  No packets received")
        print(f"\nTroubleshooting:")
        print(f"  1. Verify network channel (should be {network_channel})")
        print(f"  2. Check System ID is 37 (OI standard)")
        print(f"  3. Ensure sensors are powered on and transmitting")
        if not is_primary:
            print(f"  4. Verify Sniff Permit is enabled (secondary mode)")
        print(f"  5. Check antenna connection")
        print(f"  6. Try listening longer - sensors transmit every 60s")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    try:
        test_radio()
    except KeyboardInterrupt:
        print("\n\nTest cancelled by user")
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
