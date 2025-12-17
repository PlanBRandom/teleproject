"""
Test script for OI Gen II radio protocol implementation
Validates packet parsing with known test vectors
"""

from pipeline.radio_receiver import RadioReceiver, RadioMessage
import struct


def test_protocol1_basic():
    """Test Protocol 1 parsing with basic sensor data"""
    print("\n=== Test Protocol 1: Basic Sensor Data ===")
    
    # Create test packet: Protocol 1, 12 bytes (no text)
    # Address: 5 (0x0005)
    # Reading: 1.5 PPM (IEEE 754 float32)
    # Mode: Normal (0), Sensor Type: EC (0) = 0x00
    # Battery: 36 (3.6V with scale 0)
    # Gas: H2S (0), Battery Scale: 0 = 0x00
    # Fault: None (0), Precision: 2, HasText: 0 = 0x04
    
    reading_bytes = struct.pack('>f', 1.5)  # 32-bit float big-endian
    packet = bytearray([
        0x00, 0x05,  # Address: 5
        0x01,        # Protocol 1
        *reading_bytes,  # Reading: 1.5
        0x00,        # Mode: Normal (0), Type: EC (0)
        36,          # Battery: 36 (= 3.6V)
        0x00,        # Gas: H2S (0), Scale: 0
        0x04,        # Fault: 0, Precision: 2, HasText: 0
        0x00         # Checksum placeholder
    ])
    
    # Calculate checksum
    packet[11] = sum(packet[:11]) & 0xFF
    
    print(f"Test packet: {' '.join([f'{b:02X}' for b in packet])}")
    
    receiver = RadioReceiver("", api_mode=False)
    msg = receiver._parse_protocol1(packet)
    
    assert msg is not None, "Failed to parse packet"
    assert msg.transmitter_address == 5, f"Wrong address: {msg.transmitter_address}"
    assert abs(msg.reading - 1.5) < 0.01, f"Wrong reading: {msg.reading}"
    assert msg.sensor_mode == 0, f"Wrong mode: {msg.sensor_mode}"
    assert msg.sensor_type == 0, f"Wrong sensor type: {msg.sensor_type}"
    assert msg.battery_voltage == 3.6, f"Wrong battery: {msg.battery_voltage}"
    assert msg.gas_type == 0, f"Wrong gas type: {msg.gas_type}"
    assert msg.fault_code == 0, f"Wrong fault: {msg.fault_code}"
    assert msg.precision == 2, f"Wrong precision: {msg.precision}"
    
    print("✓ Protocol 1 basic parsing successful")
    print(f"  Address: {msg.transmitter_address}, Reading: {msg.reading:.2f}")
    print(f"  Battery: {msg.battery_voltage}V, Gas Type: {msg.gas_type}")


def test_protocol1_with_text():
    """Test Protocol 1 with text message"""
    print("\n=== Test Protocol 1: With Text Message ===")
    
    reading_bytes = struct.pack('>f', 25.3)
    text = "HIGH GAS"
    text_bytes = text.encode('ascii')
    
    packet = bytearray([
        0x00, 0x10,  # Address: 16
        0x01,        # Protocol 1
        *reading_bytes,
        0x00,        # Mode/Type
        42,          # Battery
        0x03,        # Gas: CO (3)
        0x05,        # Fault: 0, Precision: 2, HasText: 1
        len(text_bytes),  # Text length
        *text_bytes,
        0x00         # Final checksum
    ])
    
    # Calculate final checksum
    packet[-1] = sum(packet[:-1]) & 0xFF
    
    print(f"Test packet with text: {len(packet)} bytes")
    
    receiver = RadioReceiver("", api_mode=False)
    msg = receiver._parse_protocol1(packet)
    
    assert msg is not None, "Failed to parse packet with text"
    assert msg.transmitter_address == 16
    assert abs(msg.reading - 25.3) < 0.01
    assert msg.text == text, f"Wrong text: {msg.text}"
    
    print(f"✓ Protocol 1 with text parsing successful")
    print(f"  Text: '{msg.text}'")


def test_protocol2():
    """Test Protocol 2 quick gas detection"""
    print("\n=== Test Protocol 2: Quick Gas Detection ===")
    
    reading_bytes = struct.pack('>f', 10.5)
    packet = bytearray([
        0x00, 0x07,  # Address: 7
        0x02,        # Protocol 2
        *reading_bytes,
        0x00         # Checksum
    ])
    
    packet[7] = sum(packet[:7]) & 0xFF
    
    print(f"Test packet: {' '.join([f'{b:02X}' for b in packet])}")
    
    receiver = RadioReceiver("", api_mode=False)
    msg = receiver._parse_protocol2(packet)
    
    assert msg is not None
    assert msg.transmitter_address == 7
    assert abs(msg.reading - 10.5) < 0.01
    assert msg.protocol == 2
    
    print("✓ Protocol 2 parsing successful")
    print(f"  Quick alert reading: {msg.reading:.2f}")


def test_protocol7():
    """Test Protocol 7 maintenance timing"""
    print("\n=== Test Protocol 7: Maintenance Timing ===")
    
    reading_bytes = struct.pack('>f', 0.0)
    packet = bytearray([
        0x00, 0x15,  # Address: 21
        0x07,        # Protocol 7
        *reading_bytes,
        0x00, 0x0A,  # Days since null: 10
        0x00, 0x1E,  # Days since cal: 30
        0x00,        # Mode: Normal, Type: EC
        0x00         # Checksum
    ])
    
    packet[12] = sum(packet[:12]) & 0xFF
    
    print(f"Test packet: {' '.join([f'{b:02X}' for b in packet])}")
    
    receiver = RadioReceiver("", api_mode=False)
    msg = receiver._parse_protocol7(packet)
    
    assert msg is not None
    assert msg.transmitter_address == 21
    assert msg.days_since_null == 10
    assert msg.days_since_cal == 30
    assert msg.protocol == 7
    
    print("✓ Protocol 7 parsing successful")
    print(f"  Days since null: {msg.days_since_null}, cal: {msg.days_since_cal}")


def test_xbee_frame_extraction():
    """Test XBee API frame with embedded Gen2 packet"""
    print("\n=== Test XBee API Frame Extraction ===")
    
    # Create a Gen2 Protocol 2 packet
    reading_bytes = struct.pack('>f', 5.2)
    gen2_packet = bytearray([
        0x00, 0x05,  # Address: 5
        0x02,        # Protocol 2
        *reading_bytes,
        0x00         # Checksum
    ])
    gen2_packet[7] = sum(gen2_packet[:7]) & 0xFF
    
    # Embed in XBee RX frame (simplified)
    # Frame type 0x90 (Receive Packet)
    xbee_payload = bytearray([
        0x90,        # Frame type: Receive Packet
        0x00,        # Frame ID
        0x00, 0x13, 0xA2, 0x00, 0x12, 0x34, 0x56, 0x78,  # 64-bit source address
        0xFF, 0xFE,  # 16-bit network address
        0x01,        # Receive options
        *gen2_packet # Gen2 packet in RF data
    ])
    
    # Build complete XBee frame
    frame_len = len(xbee_payload)
    xbee_frame = bytearray([
        0x7E,        # Start delimiter
        (frame_len >> 8) & 0xFF,  # Length MSB
        frame_len & 0xFF,          # Length LSB
        *xbee_payload,
        0x00         # Checksum placeholder
    ])
    
    # Calculate XBee checksum
    xbee_frame[-1] = 0xFF - (sum(xbee_payload) & 0xFF)
    
    print(f"XBee frame: {len(xbee_frame)} bytes")
    print(f"Frame data: {' '.join([f'{b:02X}' for b in xbee_frame[:20]])}...")
    
    receiver = RadioReceiver("", api_mode=True)
    receiver.buffer = xbee_frame
    
    # Should extract and parse Gen2 packet
    messages = []
    def capture_msg(msg):
        messages.append(msg)
    
    receiver.register_callback(capture_msg)
    receiver._process_api_frames()
    
    assert len(messages) == 1, f"Expected 1 message, got {len(messages)}"
    msg = messages[0]
    assert msg.transmitter_address == 5
    assert abs(msg.reading - 5.2) < 0.01
    
    print("✓ XBee frame extraction successful")
    print(f"  Extracted Gen2 packet: Ch{msg.channel}, Reading: {msg.reading:.2f}")


def test_checksum_validation():
    """Test checksum validation catches corrupt packets"""
    print("\n=== Test Checksum Validation ===")
    
    reading_bytes = struct.pack('>f', 1.0)
    packet = bytearray([
        0x00, 0x01,
        0x02,
        *reading_bytes,
        0xFF  # Wrong checksum
    ])
    
    receiver = RadioReceiver("", api_mode=False)
    receiver.buffer = packet.copy()
    
    messages = []
    receiver.register_callback(lambda msg: messages.append(msg))
    receiver._process_transparent()
    
    # Should reject packet due to bad checksum
    assert len(messages) == 0, "Should reject packet with bad checksum"
    
    print("✓ Checksum validation working correctly")


def run_all_tests():
    """Run all protocol tests"""
    print("=" * 60)
    print("OI Gen II Radio Protocol Test Suite")
    print("=" * 60)
    
    try:
        test_protocol1_basic()
        test_protocol1_with_text()
        test_protocol2()
        test_protocol7()
        test_xbee_frame_extraction()
        test_checksum_validation()
        
        print("\n" + "=" * 60)
        print("✓ ALL TESTS PASSED")
        print("=" * 60)
        return True
    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}")
        return False
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)
