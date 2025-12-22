"""
Example: Laird Radio RSSI and MAC monitoring
Demonstrates Laird LT1110/RM024 binary protocol commands

This example shows how to:
- Monitor signal strength (RSSI) from Laird radios
- Read MAC addresses for sensor identification
- Set RF channel dynamically
- Receive Gen2 sensor packets with metadata
"""

from pipeline.radio_receiver import RadioReceiver, RadioMessage, GAS_TYPE_NAMES, FAULT_NAMES
import time


def on_message(msg: RadioMessage):
    """Callback for received sensor messages"""
    if msg.protocol == 1:
        gas_name = GAS_TYPE_NAMES.get(msg.gas_type, f"Gas {msg.gas_type}")
        fault_name = FAULT_NAMES.get(msg.fault_code, "None")
        
        print(f"\n{'='*60}")
        print(f"Channel {msg.channel} (Address {msg.transmitter_address})")
        print(f"{'='*60}")
        print(f"Reading:  {msg.reading:.{msg.precision}f} {gas_name}")
        print(f"Battery:  {msg.battery_voltage:.1f}V")
        print(f"Fault:    {fault_name}")
        print(f"Mode:     {msg.sensor_mode}")
        
        if msg.rssi:
            print(f"RSSI:     {msg.rssi} dBm")
        
        if msg.text:
            print(f"Text:     {msg.text}")
            
    elif msg.protocol == 2:
        print(f"\n⚠️  GAS ALERT - Ch{msg.channel}: {msg.reading:.2f}")
        
    elif msg.protocol == 7:
        print(f"\n🔧 Maintenance - Ch{msg.channel}")
        print(f"   Days since null: {msg.days_since_null}")
        print(f"   Days since cal:  {msg.days_since_cal}")


def main():
    print("="*60)
    print("OI Laird Radio Monitor with RSSI/MAC")
    print("="*60)
    
    # Configure for Laird LT1110 or RM024
    # Adjust COM port as needed
    receiver = RadioReceiver("COM7", baudrate=115200, api_mode=True)
    
    if not receiver.connect():
        print("Failed to connect to radio module")
        return
    
    # Get radio information
    print("\nRadio Information:")
    print("-" * 60)
    
    mac = receiver.get_mac_address()
    if mac:
        print(f"MAC Address: {mac}")
    
    rssi = receiver.get_rssi()
    if rssi:
        print(f"Current RSSI: {rssi} dBm")
        if rssi > -70:
            print("  Signal: Excellent")
        elif rssi > -85:
            print("  Signal: Good")
        elif rssi > -95:
            print("  Signal: Fair")
        else:
            print("  Signal: Poor")
    
    # Set RF channel (OI default is 5)
    print(f"\nSetting RF Channel to 25 (OI default)...")
    if receiver.set_rf_channel(25):
        print("✓ Channel set successfully")
    
    # Register callback and start listening
    receiver.register_callback(on_message)
    receiver.start()
    
    print("\n" + "="*60)
    print("Listening for OI wireless sensors...")
    print("Press Ctrl+C to stop")
    print("="*60 + "\n")
    
    # Monitor loop with periodic RSSI checks
    try:
        last_rssi_check = time.time()
        
        while True:
            time.sleep(1)
            
            # Check RSSI every 30 seconds
            if time.time() - last_rssi_check > 30:
                rssi = receiver.get_rssi()
                if rssi:
                    print(f"\n📡 Radio RSSI: {rssi} dBm")
                last_rssi_check = time.time()
                
    except KeyboardInterrupt:
        print("\n\nStopping...")
    finally:
        receiver.disconnect()
        print("Disconnected")


if __name__ == "__main__":
    main()
