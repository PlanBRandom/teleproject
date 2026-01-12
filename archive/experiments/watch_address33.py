"""
Watch Address 33 Sensor - Monitor relay test
Shows address 33 on Network 15 (direct) and Network 25 (repeated) side-by-side
"""
import json
import time
from datetime import datetime
from threading import Thread, Lock
from pipeline.radio_receiver import RadioReceiver, RadioMessage

GAS_TYPE_NAMES = {
    0: "None", 1: "SO2", 2: "NO2", 3: "CO", 4: "H2S", 5: "HCN", 6: "NH3", 7: "Cl2",
    8: "LEL", 9: "O2", 10: "PH3", 11: "ClO2", 12: "NO", 13: "HCl", 14: "O3", 15: "HF",
    16: "VOC", 17: "ETO", 18: "AsH3", 19: "CO2", 20: "COCl2", 21: "SiH4", 22: "GeH4",
    23: "B2H6", 24: "F2", 25: "BF3", 26: "N2H4", 27: "C2H4O", 28: "CH3OH", 29: "TDI",
    30: "HMDI", 31: "MDI", 32: "H2", 33: "C3H8", 34: "CH4", 35: "C4H10"
}

class Address33Monitor:
    def __init__(self):
        self.lock = Lock()
        self.last_seen = {
            'COM7': None,
            'COM11': None,
            'COM12': None
        }
        self.packet_count = {
            'COM7': 0,
            'COM11': 0,
            'COM12': 0
        }
        self.running = False
        self.start_time = None
        
        # Load config
        with open('config.json', 'r') as f:
            self.config = json.load(f)
    
    def create_callback(self, port_name, network_name):
        """Create callback for specific network"""
        def callback(msg: RadioMessage):
            # Only track channel 33 (address 33)
            if msg.channel != 33:
                return
            
            elapsed = time.time() - self.start_time
            gas_name = GAS_TYPE_NAMES.get(msg.gas_type, f"Gas{msg.gas_type}")
            
            with self.lock:
                self.packet_count[port_name] += 1
                self.last_seen[port_name] = {
                    'timestamp': elapsed,
                    'reading': msg.reading,
                    'battery': msg.battery_voltage,
                    'gas': gas_name,
                    'rssi': msg.rssi,
                    'fault': msg.fault_code,
                    'protocol': msg.protocol
                }
                
                # Print update
                print(f"\n{'='*80}")
                print(f"[{datetime.now().strftime('%H:%M:%S')}] ADDRESS 33 UPDATE - {network_name}")
                print(f"{'='*80}")
                print(f"Elapsed:  {elapsed:.1f}s")
                print(f"Reading:  {msg.reading:.1f} ppm")
                print(f"Gas:      {gas_name}")
                print(f"Battery:  {msg.battery_voltage:.1f}V")
                print(f"RSSI:     {msg.rssi}%")
                print(f"Fault:    {msg.fault_code}")
                print(f"Protocol: {msg.protocol}")
                print(f"{'='*80}\n")
                
                # Show status across all networks
                self.print_status()
        
        return callback
    
    def print_status(self):
        """Print current status across all networks"""
        print("Current Status Across Networks:")
        print("-" * 80)
        
        for port in ['COM7', 'COM11', 'COM12']:
            count = self.packet_count[port]
            data = self.last_seen[port]
            
            network_name = {
                'COM7': 'Network 15 (Direct)',
                'COM11': 'Network 25 (Repeated)',
                'COM12': 'Network 20 (Direct)'
            }[port]
            
            if data:
                print(f"{network_name:30s} | Count: {count:3d} | "
                      f"{data['reading']:6.1f} ppm | {data['battery']:5.1f}V | "
                      f"RSSI: {data['rssi']:3d}% | {data['gas']:8s} | "
                      f"Last: {data['timestamp']:6.1f}s ago")
            else:
                print(f"{network_name:30s} | Count: {count:3d} | NO DATA")
        
        print("-" * 80 + "\n")
    
    def monitor_network(self, port, baudrate, port_name, network_name):
        """Monitor a single network"""
        try:
            receiver = RadioReceiver(port, baudrate=baudrate, api_mode=True, api_type='rm024')
            
            if not receiver.connect():
                print(f"[{network_name}] Failed to connect to {port}")
                return
            
            print(f"[{network_name}] Connected to {port}")
            
            callback = self.create_callback(port_name, network_name)
            receiver.register_callback(callback)
            receiver.start()
            
            while self.running:
                time.sleep(1)
            
            receiver.stop()
            
        except Exception as e:
            print(f"[{network_name}] Error: {e}")
    
    def start(self):
        """Start monitoring all networks"""
        self.running = True
        self.start_time = time.time()
        
        print("="*80)
        print("ADDRESS 33 RELAY TEST MONITOR")
        print("="*80)
        print("Watching for address 33 sensor on all networks")
        print("Expecting: 55 ppm H2S reading in relay test mode")
        print("="*80)
        print()
        
        networks = [
            ('Network_15', 'COM7', 'Net15 Direct'),
            ('Network_25', 'COM11', 'Net25 Repeated'),
            ('Network_20', 'COM12', 'Net20 Direct')
        ]
        
        threads = []
        for config_key, port, name in networks:
            network_config = self.config['radios'][config_key]
            t = Thread(
                target=self.monitor_network,
                args=(network_config['port'], network_config['baudrate'], port, name),
                daemon=True
            )
            t.start()
            threads.append(t)
        
        print("All monitors started. Press Ctrl+C to stop.\n")
        
        try:
            # Status update every 10 seconds
            last_status = time.time()
            while True:
                time.sleep(1)
                
                if time.time() - last_status >= 10:
                    with self.lock:
                        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] STATUS UPDATE:")
                        self.print_status()
                    last_status = time.time()
        
        except KeyboardInterrupt:
            print("\n\nStopping...")
            self.running = False
            time.sleep(2)
            
            # Final report
            print("\n" + "="*80)
            print("FINAL REPORT - ADDRESS 33")
            print("="*80)
            with self.lock:
                self.print_status()


if __name__ == "__main__":
    monitor = Address33Monitor()
    monitor.start()
