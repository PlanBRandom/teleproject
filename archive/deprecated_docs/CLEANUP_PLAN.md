# Repository Cleanup Plan

## Directory Structure (Proposed)

```
oi-7500-pipeline/
├── README.md                          # Main documentation
├── requirements.txt                   # Python dependencies
├── config.yaml                        # Main configuration
│
├── monitor.py                         # MAIN SCRIPT - Network monitor with HA
│
├── pipeline/                          # Core library (KEEP)
│   ├── radio_receiver.py             # Radio decoder (WORKING)
│   ├── mqtt.py                        # MQTT client
│   ├── register.py                    # Modbus registers
│   └── main.py                        # Pipeline entry
│
├── configs/                           # Configuration files
│   └── lovelace/                      # Home Assistant dashboards
│
├── reference/                         # Documentation & references
│   ├── protocol/                      # Protocol specifications
│   │   ├── gen2_wirefree_protocol.md # Official protocol doc
│   │   └── laird_api_frames.md       # Laird frame format
│   ├── hardware/                      # Hardware documentation
│   │   ├── radio_setup.md            # Radio configuration
│   │   └── modbus_registers.md       # OI-6000 register map
│   └── troubleshooting.md            # Common issues
│
├── tools/                             # Utility scripts
│   ├── configure_radio.py            # Radio configuration
│   ├── test_connection.py            # Connection testing
│   └── decode_packet.py              # Manual packet decoder
│
├── archive/                           # Old/test files (TO MOVE)
│   ├── test_scripts/                 # All test_*.py files
│   ├── analysis/                     # All analyze_*.py files
│   ├── experiments/                  # One-off scripts
│   └── old_monitors/                 # Deprecated monitors
│
├── logs/                              # Log files (existing)
└── test/                              # Unit tests (existing)
```

## Files to Keep (Active)

### Core Application
- `network_monitor_with_ha.py` → rename to `monitor.py`
- `pipeline/radio_receiver.py` (WORKING - Protocol 1 decoder)
- `pipeline/mqtt.py`
- `pipeline/register.py`
- `config.yaml`
- `requirements.txt`

### Configuration
- `configs/lovelace/` (all channel YAML files)

## Files to Archive

### Test Scripts (60+ files)
- All `test_*.py` → `archive/test_scripts/`
- All `analyze_*.py` → `archive/analysis/`
- All `capture_*.py` → `archive/experiments/`
- All `scan_*.py` → `archive/experiments/`
- All `simple_monitor*.py` → `archive/old_monitors/`

### Deprecated Monitors
- `weekend_monitor.py` → `archive/old_monitors/`
- `monitor_with_modbus_status.py` → `archive/old_monitors/`
- `multi_network_monitor.py` → `archive/old_monitors/`
- `laird_monitor.py` → `archive/old_monitors/`

### Documentation to Consolidate
- Multiple README files → Single README.md
- Multiple setup guides → Consolidated in reference/

## Files to Delete
- `*.log` files (keep logs/ directory)
- Duplicate config files
- Old markdown files with outdated info

## Actions

1. Create new directory structure
2. Move active files to proper locations
3. Archive old files
4. Create comprehensive README.md
5. Create reference documentation
6. Update imports in active files
