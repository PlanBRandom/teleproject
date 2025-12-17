# OI Gen2 Gas Type Reference

## Gas Type Codes (0-27)

| Code | Gas Name | Full Name | Typical Range |
|------|----------|-----------|---------------|
| 0 | H2S | Hydrogen Sulfide | 0-100 PPM |
| 1 | CO | Carbon Monoxide | 0-500 PPM |
| 2 | O2 | Oxygen | 0-25% |
| 3 | LEL | Lower Explosive Limit | 0-100% |
| 4 | SO2 | Sulfur Dioxide | 0-20 PPM |
| 5 | CL2 | Chlorine | 0-10 PPM |
| 6 | HCN | Hydrogen Cyanide | 0-30 PPM |
| 7 | NH3 | Ammonia | 0-100 PPM |
| 8 | PH3 | Phosphine | 0-1 PPM |
| 9 | NO | Nitric Oxide | 0-250 PPM |
| 10 | NO2 | Nitrogen Dioxide | 0-20 PPM |
| 11 | O3 | Ozone | 0-1 PPM |
| 12 | CLO2 | Chlorine Dioxide | 0-1 PPM |
| 13 | HCL | Hydrogen Chloride | 0-10 PPM |
| 14 | HF | Hydrogen Fluoride | 0-10 PPM |
| 15 | ETO | Ethylene Oxide | 0-100 PPM |
| 16 | VOC | Volatile Organic Compounds | 0-2000 PPM |
| 17 | CO2 | Carbon Dioxide | 0-5% |
| 18 | H2 | Hydrogen | 0-1000 PPM |
| 19 | ASH3 | Arsine | 0-1 PPM |
| 20 | COCl2 | Phosgene | 0-1 PPM |
| 21 | B2H6 | Diborane | 0-1 PPM |
| 22 | C2H4O | Ethylene Oxide (alt) | 0-100 PPM |
| 23 | GeH4 | Germane | 0-1 PPM |
| 24 | SiH4 | Silane | 0-10 PPM |
| 25 | F2 | Fluorine | 0-1 PPM |
| 26 | HBr | Hydrogen Bromide | 0-10 PPM |
| 27 | FEET | Distance (LPIR) | 0-300 FEET |

## Sensor Type Codes (0-3)

| Code | Sensor Type | Description |
|------|-------------|-------------|
| 0 | OI-6000 Sensor | Standard electrochemical sensor |
| 1 | OI-6500 LPIR Sensor | Laser-based point IR sensor |
| 2 | OI-6600 Transmitter | Gas transmitter |
| 3 | Reserved | Reserved for future use |

## Sensor Mode Codes (0-7)

| Code | Mode | Description |
|------|------|-------------|
| 0 | Normal | Normal operation |
| 1 | Calibration | Calibration in progress |
| 2 | Null | Null/zero calibration |
| 3 | Span | Span calibration |
| 4 | Fault | Sensor fault |
| 5 | Warmup | Warmup period |
| 6 | Maintenance | Maintenance required |
| 7 | Disabled | Sensor disabled |

## Fault Codes (0-15)

| Code | Fault | Description |
|------|-------|-------------|
| 0 | No Fault | Normal operation |
| 1 | Low Signal | Sensor signal too low |
| 2 | High Signal | Sensor signal too high |
| 3 | Over Range | Reading exceeds sensor range |
| 4 | Under Range | Reading below sensor range |
| 5 | Comm Fault | Communication error |
| 6 | Cal Due | Calibration overdue |
| 7 | Cal Overdue | Calibration seriously overdue |
| 8 | Null Due | Null calibration due |
| 9 | Null Overdue | Null calibration overdue |
| 10 | Sensor Fault | General sensor fault |
| 11 | Battery Low | Low battery voltage |
| 12 | Battery Critical | Critical battery voltage |
| 13 | Hardware Fault | Hardware malfunction |
| 14 | Config Error | Configuration error |
| 15 | Reserved | Reserved |

## Usage Examples

### Reading Test Packet Data
```python
# Protocol 1 packet received:
{
    'channel': 5,           # Channel 5
    'reading': 45.23,       # Reading value
    'gas_type': 0,          # H2S
    'sensor_type': 0,       # OI-6000 Sensor
    'sensor_mode': 0,       # Normal
    'fault_code': 0,        # No Fault
    'battery_voltage': 3.5, # Battery OK
    'precision': 2          # 2 decimal places
}
```

### Sending Test Packets
```python
from pipeline.radio_receiver import RadioReceiver

receiver = RadioReceiver("COM11", api_mode=True)
receiver.connect()

# Send H2S reading on channel 5
receiver.send_test_packet(
    channel=5,
    reading=50.5,
    gas_type=0,      # H2S
    sensor_type=0,   # OI-6000
    battery_voltage=3.3
)

# Send CO reading on channel 10
receiver.send_test_packet(
    channel=10,
    reading=125.0,
    gas_type=1,      # CO
    sensor_type=0,   # OI-6000
    battery_voltage=3.2
)

# Send O2 reading on channel 15
receiver.send_test_packet(
    channel=15,
    reading=20.9,
    gas_type=2,      # O2
    sensor_type=0,   # OI-6000
    battery_voltage=3.4
)
```

### Common Testing Scenarios

**Test Low H2S Alert (10 PPM)**
```python
receiver.send_test_packet(channel=1, reading=10.0, gas_type=0)
```

**Test High H2S Alarm (30 PPM)**
```python
receiver.send_test_packet(channel=1, reading=30.0, gas_type=0)
```

**Test Low O2 Alert (19.5%)**
```python
receiver.send_test_packet(channel=2, reading=19.5, gas_type=2)
```

**Test LEL Warning (20% LEL)**
```python
receiver.send_test_packet(channel=3, reading=20.0, gas_type=3)
```

**Test Low Battery**
```python
receiver.send_test_packet(channel=1, reading=0.0, gas_type=0, battery_voltage=2.5)
```

## Quick Reference: Common Gases

**Toxic Gases**
- H2S (0): OSHA TWA 10 PPM, STEL 15 PPM
- CO (1): OSHA TWA 50 PPM
- SO2 (4): OSHA TWA 5 PPM
- CL2 (5): OSHA TWA 1 PPM
- NH3 (7): OSHA TWA 50 PPM

**Asphyxiants**
- O2 (2): Safe range 19.5-23.5%
- CO2 (17): OSHA TWA 5000 PPM (0.5%)

**Flammables**
- LEL (3): Alarm typically 10-20% LEL
- H2 (18): LEL = 4% by volume

**Distance Measurement**
- FEET (27): OI-6500 LPIR sensor, 0-300 feet range
