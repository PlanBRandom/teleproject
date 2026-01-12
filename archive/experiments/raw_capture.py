"""
Raw Serial Capture - Capture exact bytes from all three ports
to understand the true Laird API frame structure
"""
import serial
import time
from datetime import datetime
from threading import Thread, Lock
from collections import defaultdict

class RawCapture:
    def __init__(self):
        self.captures = {
            'COM7': [],
            'COM11': [],
            'COM12': []
        }
        self.lock = Lock()
        self.running = False
    
    def capture_port(self, port, duration=30):
        """Capture raw bytes from a single port"""
        try:
            ser = serial.Serial(port, 115200, timeout=1)
            print(f"[{port}] Connected")
            
            start_time = time.time()
            frame_count = 0
            
            while self.running and (time.time() - start_time) < duration:
                if ser.in_waiting > 0:
                    # Read all available bytes
                    data = ser.read(ser.in_waiting)
                    timestamp = time.time() - start_time
                    
                    # Look for 0x81 frame starts
                    for i in range(len(data)):
                        if data[i] == 0x81:
                            # Try to capture complete frame
                            if i + 2 < len(data):
                                payload_len = data[i + 1]
                                frame_len = 3 + payload_len
                                
                                if i + frame_len <= len(data):
                                    frame = data[i:i+frame_len]
                                    frame_count += 1
                                    
                                    with self.lock:
                                        self.captures[port].append({
                                            'timestamp': timestamp,
                                            'frame': frame,
                                            'hex': frame.hex()
                                        })
                                    
                                    print(f"[{port}] [{timestamp:7.1f}s] Frame {frame_count}: "
                                          f"Len={payload_len:02d} | {frame[:min(30, len(frame))].hex()}")
            
            ser.close()
            print(f"[{port}] Captured {frame_count} frames")
            
        except Exception as e:
            print(f"[{port}] Error: {e}")
    
    def analyze(self):
        """Analyze captured frames to determine structure"""
        print("\n" + "="*80)
        print("FRAME STRUCTURE ANALYSIS")
        print("="*80)
        
        for port in ['COM7', 'COM11', 'COM12']:
            frames = self.captures[port]
            if not frames:
                print(f"\n{port}: NO FRAMES CAPTURED")
                continue
            
            print(f"\n{port}: {len(frames)} frames")
            print("-" * 80)
            
            # Group by payload length
            by_length = defaultdict(list)
            for frame_data in frames:
                frame = frame_data['frame']
                if len(frame) >= 2:
                    payload_len = frame[1]
                    by_length[payload_len].append(frame)
            
            for payload_len in sorted(by_length.keys()):
                frame_list = by_length[payload_len]
                print(f"\nPayload Length {payload_len}: {len(frame_list)} frames")
                
                # Show first 3 examples
                for i, frame in enumerate(frame_list[:3]):
                    print(f"  Example {i+1}: {frame.hex()}")
                    
                    # Parse structure
                    if len(frame) >= 3 + payload_len:
                        print(f"    [0x81][{frame[1]:02x}][{frame[2]:02x}]", end="")
                        
                        # Show payload bytes with positions
                        payload = frame[3:3+payload_len]
                        for j, byte in enumerate(payload):
                            if j % 10 == 0:
                                print(f"\n    [{j:2d}]:", end="")
                            print(f" {byte:02x}", end="")
                        print()
            
            # Look for patterns
            print(f"\nPattern Analysis for {port}:")
            if frames:
                # Check if byte positions have consistent meaning
                payload_lengths = list(by_length.keys())
                print(f"  Payload lengths seen: {payload_lengths}")
                
                if len(payload_lengths) == 1:
                    print(f"  -> All frames same length: {payload_lengths[0]} bytes")
                else:
                    print(f"  -> Multiple lengths: {min(payload_lengths)}-{max(payload_lengths)} bytes")
    
    def start(self, duration=30):
        """Start capturing all three ports"""
        self.running = True
        
        ports = [
            ('COM7', 115200),
            ('COM11', 115200),
            ('COM12', 115200)
        ]
        
        threads = []
        for port, baud in ports:
            t = Thread(target=self.capture_port, args=(port, duration), daemon=True)
            t.start()
            threads.append(t)
        
        # Wait for all threads
        for t in threads:
            t.join()
        
        self.running = False
        
        # Analyze results
        self.analyze()


if __name__ == "__main__":
    print("="*80)
    print("Raw Packet Capture - 30 second test")
    print("="*80)
    print("Capturing exact bytes from COM7, COM11, COM12")
    print("This will reveal the true Laird API frame structure")
    print("="*80)
    
    capture = RawCapture()
    capture.start(duration=30)
    
    print("\n" + "="*80)
    print("Capture complete")
    print("="*80)
