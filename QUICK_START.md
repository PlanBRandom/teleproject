# Quick Reference Card

**OI-7500 Radio Monitoring System**

## 🚀 Quick Start

```powershell
# Activate environment
.\.venv\Scripts\Activate.ps1

# Run monitor
python monitor.py
```

## 📁 Repository Layout

```
├── monitor.py          ⭐ MAIN PRODUCTION SCRIPT
├── config.yaml         Configuration
├── requirements.txt    Dependencies
│
├── pipeline/           Core library (radio decoder)
├── tools/              Utilities (5 scripts)
├── reference/          Documentation
│   ├── protocol/       Gen II protocol specs
│   └── hardware/       Hardware docs (TBD)
│
├── configs/            HA dashboard configs
├── logs/               Runtime logs
├── test/               Unit tests
└── archive/            Old files (119 archived)
```

## 📊 System Status

| Component | Status | Notes |
|-----------|--------|-------|
| Protocol 1 Decoder | ✅ 100% | Working perfectly |
| HA Integration | ✅ Working | MQTT discovery |
| Active Sensors | ✅ 10 sensors | Network 15 |
| O2 Validation | ✅ 20.9 ppm | Atmospheric |

## 🔧 Hardware Setup

**Radios** (Laird RM024 @ 115200 baud):
- COM7: Network 15 (direct)
- COM11: Network 25 (repeater)
- COM12: Network 20 (direct)

**Sensors** (10 active on Network 15):
- 3x H2S (Ch002, 003, 010, 033)
- 1x CO (Ch005)
- 3x NH3/LEL (Ch012, 022, 023)
- 1x Cl2/VOC (Ch020)
- 1x O2 (Ch255) ← Validated 20.9%

## 📝 Configuration

Edit `config.yaml`:
```yaml
mqtt:
  host: "your-broker.com"
  port: 1883
  username: "user"
  password: "password"
```

## 🏠 Home Assistant

**Auto-discovered entities:**
- `sensor.oi7500_01_channel_N_reading`
- `sensor.oi7500_01_channel_N_battery`
- `sensor.oi7500_01_channel_N_rssi`
- `sensor.oi7500_01_channel_N_fault`

## 🛠️ Utilities (tools/)

```powershell
# Configure radio
python tools/configure_radio.py

# Decode packet manually
python tools/decode_packet.py <hex_string>

# Test hardware connections
python tools/hardware_test.py
```

## 📖 Documentation (reference/)

- **protocol/gen2_protocol.md** - Complete protocol spec
- **protocol/gas_types.md** - Gas codes & safety info

## 🐛 Troubleshooting

**No packets?**
1. Check COM ports available
2. Verify 115200 baud
3. Ensure radios in SECONDARY mode

**MQTT not connecting?**
1. Check config.yaml broker settings
2. Verify port (1883 or 8883)
3. Test with mosquitto_sub

**HA entities missing?**
1. Enable MQTT discovery in HA
2. Check MQTT topic: `homeassistant/sensor/#`
3. Review logs in logs/

## 📚 More Info

- Full README: [README.md](README.md)
- Protocol docs: [reference/protocol/](reference/protocol/)
- Reorganization log: [REORGANIZATION_SUMMARY.md](REORGANIZATION_SUMMARY.md)
- Old code: [archive/](archive/) (if you need reference)

## ✅ Verification

Test imports:
```powershell
python -c "from pipeline.radio_receiver import RadioReceiver; print('✅')"
```

Test monitor loads:
```powershell
python -c "import monitor; print('✅')"
```

## 🎯 Key Files

| File | Purpose | Status |
|------|---------|--------|
| monitor.py | Production monitoring | ✅ Working |
| pipeline/radio_receiver.py | Protocol 1 decoder | ✅ 100% success |
| config.yaml | Configuration | ✅ Active |
| reference/protocol/gen2_protocol.md | Protocol spec | ✅ Complete |

## 📊 Repository Stats

- **Active files**: 6 in root
- **Archived**: 119 files preserved
- **Documentation**: 3 comprehensive guides
- **Tools**: 5 utility scripts
- **Success rate**: 100% packet decoding

---

**Version**: 1.0  
**Last Updated**: 2026-01-12  
**Status**: Production Ready ✅
