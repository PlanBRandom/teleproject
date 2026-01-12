"""
Multi-Network Monitor - Compare Direct vs Repeated Packets
Monitors COM7, COM11, COM12 simultaneously to track:
- Which sensors transmit to which network
- Repeater forwarding delay
- Packet loss in repeater chain
- Primary/Secondary status verification
"""
import json
import logging
import signal
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional
from threading import Thread, Lock
from collections import defaultdict

from pipeline.radio_receiver import RadioReceiver, RadioMessage

# Gas type names
GAS_TYPE_NAMES = {
    0: "None", 1: "SO2", 2: "NO2", 3: "CO", 4: "H2S", 5: "HCN", 6: "NH3", 7: "Cl2",
    8: "LEL", 9: "O2", 10: "PH3", 11: "ClO2", 12: "NO", 13: "HCl", 14: "O3", 15: "HF",
    16: "VOC", 17: "ETO", 18: "AsH3", 19: "CO2", 20: "COCl2", 21: "SiH4", 22: "GeH4",
    23: "B2H6", 24: "F2", 25: "BF3", 26: "N2H4", 27: "C2H4O", 28: "CH3OH", 29: "TDI",
    30: "HMDI", 31: "MDI", 32: "H2", 33: "C3H8", 34: "CH4", 35: "C4H10"
}


class MultiNetworkMonitor:
    """Monitor all three networks and compare forwarding"""
    
    def __init__(self, config_file: str = "config.json", duration_minutes: float = 30):
        self.config = self._load_config(config_file)
        self.running = False
        self.duration_seconds = duration_minutes * 60
        
        # Track packets per network
        self.packets = {
            'COM7': [],   # Network 15 - Direct
            'COM11': [],  # Network 25 - Repeated
            'COM12': []   # Network 20 - Direct
        }
        self.lock = Lock()
        
        # Track forwarding stats
        self.direct_to_repeated = defaultdict(list)  # Track delay per channel
        
        # Setup logging
        self._setup_logging()
        
        logger.info("="*80)
        logger.info(f"Multi-Network Monitor - {duration_minutes} minute test")
        logger.info("="*80)
        logger.info("Monitoring:")
        logger.info("  COM7  (Network 15) - Direct sensor packets")
        logger.info("  COM11 (Network 25) - Repeated packets from both networks")
        logger.info("  COM12 (Network 20) - Direct sensor packets")
        logger.info("="*80)
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _load_config(self, config_file: str) -> Dict:
        """Load configuration"""
        with open(config_file, 'r') as f:
            return json.load(f)
    
    def _setup_logging(self):
        """Setup logging"""
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = log_dir / f"multi_network_{timestamp}.log"
        
        global logger
        logger = logging.getLogger("MultiNetworkMonitor")
        logger.setLevel(logging.INFO)
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter('%(message)s')
        console_handler.setFormatter(console_formatter)
        
        # File handler
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(file_formatter)
        
        logger.addHandler(console_handler)
        logger.addHandler(file_handler)
        
        logger.info(f"Logging to: {log_file}")
    
    def _create_callback(self, port_name: str, network_name: str):
        """Create callback for a specific network"""
        def callback(msg: RadioMessage):
            # Skip Protocol 7 (maintenance)
            if msg.protocol == 7:
                return
            
            timestamp = time.time()
            
            with self.lock:
                packet_info = {
                    'timestamp': timestamp,
                    'channel': msg.channel,
                    'protocol': msg.protocol,
                    'reading': msg.reading,
                    'battery': msg.battery_voltage,
                    'gas_type': msg.gas_type,
                    'rssi': msg.rssi,
                    'fault': msg.fault_code
                }
                self.packets[port_name].append(packet_info)
                
                # Log packet
                gas_name = GAS_TYPE_NAMES.get(msg.gas_type, f"Gas{msg.gas_type}")
                elapsed = timestamp - self.start_time
                
                logger.info(f"[{network_name:6s}] [{elapsed:7.1f}s] Ch{msg.channel:02d} | "
                          f"{gas_name:8s} | {msg.reading:7.1f} | "
                          f"Bat: {msg.battery_voltage:.1f}V | RSSI: {msg.rssi}%")
        
        return callback
    
    def _monitor_network(self, port: str, baudrate: int, network_name: str):
        """Monitor a single network"""
        try:
            receiver = RadioReceiver(port, baudrate=baudrate, api_mode=True, api_type='rm024')
            
            if not receiver.connect():
                logger.error(f"[{network_name}] Failed to connect to {port}")
                return
            
            logger.info(f"[{network_name}] Connected to {port}")
            
            callback = self._create_callback(port, network_name)
            receiver.register_callback(callback)
            receiver.start()
            
            # Keep running until stopped
            while self.running:
                time.sleep(1)
            
            receiver.stop()
            
        except Exception as e:
            logger.error(f"[{network_name}] Error: {e}", exc_info=True)
    
    def _analyze_forwarding(self):
        """Analyze packet forwarding from direct to repeated"""
        logger.info("\n" + "="*80)
        logger.info("FORWARDING ANALYSIS")
        logger.info("="*80)
        
        # Get packets from each network
        com7_packets = self.packets['COM7']
        com11_packets = self.packets['COM11']
        com12_packets = self.packets['COM12']
        
        logger.info(f"\nPacket Counts:")
        logger.info(f"  COM7  (Net 15 Direct):  {len(com7_packets)} packets")
        logger.info(f"  COM11 (Net 25 Repeated): {len(com11_packets)} packets")
        logger.info(f"  COM12 (Net 20 Direct):  {len(com12_packets)} packets")
        
        # Analyze which channels appear on which networks
        channels_com7 = set(p['channel'] for p in com7_packets)
        channels_com11 = set(p['channel'] for p in com11_packets)
        channels_com12 = set(p['channel'] for p in com12_packets)
        
        logger.info(f"\nChannels per Network:")
        logger.info(f"  COM7  (Direct):  {sorted(channels_com7) if channels_com7 else 'NONE'}")
        logger.info(f"  COM11 (Repeated): {sorted(channels_com11) if channels_com11 else 'NONE'}")
        logger.info(f"  COM12 (Direct):  {sorted(channels_com12) if channels_com12 else 'NONE'}")
        
        # Check if COM7/COM12 sensors appear in COM11
        if channels_com7:
            forwarded_from_15 = channels_com7 & channels_com11
            not_forwarded_15 = channels_com7 - channels_com11
            logger.info(f"\nNetwork 15 -> 25 Forwarding:")
            logger.info(f"  Forwarded: {sorted(forwarded_from_15) if forwarded_from_15 else 'NONE'}")
            logger.info(f"  NOT Forwarded: {sorted(not_forwarded_15) if not_forwarded_15 else 'ALL OK'}")
        
        if channels_com12:
            forwarded_from_20 = channels_com12 & channels_com11
            not_forwarded_20 = channels_com12 - channels_com11
            logger.info(f"\nNetwork 20 -> 25 Forwarding:")
            logger.info(f"  Forwarded: {sorted(forwarded_from_20) if forwarded_from_20 else 'NONE'}")
            logger.info(f"  NOT Forwarded: {sorted(not_forwarded_20) if not_forwarded_20 else 'ALL OK'}")
        
        # Analyze delay for forwarded packets
        if com7_packets or com12_packets:
            logger.info(f"\nForwarding Delay Analysis:")
            
            # For each direct packet, find matching repeated packet
            direct_packets = com7_packets + com12_packets
            delays = []
            
            for direct in direct_packets:
                # Find corresponding repeated packet (same channel, close timestamp)
                for repeated in com11_packets:
                    if (repeated['channel'] == direct['channel'] and 
                        repeated['timestamp'] > direct['timestamp'] and
                        repeated['timestamp'] - direct['timestamp'] < 5):  # Within 5 seconds
                        
                        delay = (repeated['timestamp'] - direct['timestamp']) * 1000  # ms
                        delays.append(delay)
                        break
            
            if delays:
                avg_delay = sum(delays) / len(delays)
                min_delay = min(delays)
                max_delay = max(delays)
                logger.info(f"  Packets matched: {len(delays)}")
                logger.info(f"  Average delay: {avg_delay:.1f} ms")
                logger.info(f"  Min delay: {min_delay:.1f} ms")
                logger.info(f"  Max delay: {max_delay:.1f} ms")
            else:
                logger.info(f"  Could not match direct/repeated packets for delay calculation")
        
        # Check for sensors ONLY on COM11 (not seen on COM7/COM12)
        only_repeated = channels_com11 - channels_com7 - channels_com12
        if only_repeated:
            logger.info(f"\nChannels ONLY on COM11 (no direct observation):")
            logger.info(f"  {sorted(only_repeated)}")
            logger.info(f"  This means these sensors are NOT transmitting to Networks 15/20")
            logger.info(f"  OR the COM7/COM12 radios are not receiving properly")
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown"""
        logger.info("\n" + "="*80)
        logger.info("Shutdown signal received")
        logger.info("="*80)
        self.stop()
    
    def start(self):
        """Start monitoring all networks"""
        self.running = True
        self.start_time = time.time()
        
        try:
            # Start monitoring threads
            threads = []
            
            networks = [
                ('Network_15', 'COM7', 'Net15'),
                ('Network_25', 'COM11', 'Net25'),
                ('Network_20', 'COM12', 'Net20')
            ]
            
            for config_key, port, name in networks:
                network_config = self.config['radios'][config_key]
                t = Thread(
                    target=self._monitor_network,
                    args=(network_config['port'], network_config['baudrate'], name),
                    daemon=True
                )
                t.start()
                threads.append(t)
            
            logger.info("\n" + "="*80)
            logger.info("All networks started - monitoring...")
            logger.info("="*80 + "\n")
            
            # Run for specified duration
            end_time = self.start_time + self.duration_seconds
            last_status = self.start_time
            
            while self.running and time.time() < end_time:
                time.sleep(1)
                
                # Status every minute
                if time.time() - last_status >= 60:
                    elapsed = (time.time() - self.start_time) / 60
                    remaining = (end_time - time.time()) / 60
                    
                    with self.lock:
                        logger.info(f"\n[STATUS] {elapsed:.1f} min | "
                                  f"COM7: {len(self.packets['COM7'])} | "
                                  f"COM11: {len(self.packets['COM11'])} | "
                                  f"COM12: {len(self.packets['COM12'])} | "
                                  f"Remaining: {remaining:.1f} min\n")
                    
                    last_status = time.time()
            
            if time.time() >= end_time:
                logger.info("\n" + "="*80)
                logger.info("Duration complete - stopping...")
                logger.info("="*80)
        
        except Exception as e:
            logger.error(f"Error: {e}", exc_info=True)
        
        finally:
            self.stop()
    
    def stop(self):
        """Stop monitoring"""
        if not self.running:
            return
        
        self.running = False
        time.sleep(2)  # Let threads finish
        
        # Analyze results
        self._analyze_forwarding()
        
        logger.info("\n" + "="*80)
        logger.info("Monitor stopped")
        logger.info("="*80)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Multi-network monitoring with forwarding analysis")
    parser.add_argument('--config', default='config.json', help='Configuration file')
    parser.add_argument('--duration', type=float, default=30, help='Duration in minutes')
    args = parser.parse_args()
    
    monitor = MultiNetworkMonitor(args.config, duration_minutes=args.duration)
    monitor.start()
