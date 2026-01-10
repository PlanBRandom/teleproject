# OI-7500 Quick Reference Card

## 🚀 Start Here

**Double-click:** `START_CONTROL_CENTER.bat`  
Or run: `python launcher.py`

## 🎯 Main GUI Tabs

### 📡 Monitoring Tab
- Set duration (hours)
- Enable MQTT/Modbus
- Click "▶ Start Monitoring"
- View live console output
- Click "📊 View MQTT Stream" for separate window

### 🔧 Diagnostics Tab
**Radio Configuration:**
- "✓ Verify Radio Config" - Check all 3 radios are SECONDARY
- "🔧 Fix Radio to Secondary" - Force radio to receive-only mode

**Packet Diagnostics:**
- "🔍 Find F8 Duplicates" - Show channels with same address
- "🔍 Track F14 Timeouts" - Show primary monitor timeout history
- "📈 All Faults" - Show all fault occurrences
- Enter channel number → "View Channel History"
- Select network → "Network Diagnostics"

### 💾 Database Tab
- "🔄 Refresh Statistics" - Show packet counts, faults, RSSI
- Set hours → "📤 Export to CSV" - Export for Excel analysis
- "🔄 Refresh" packet list - View recent 100 packets

### ⚙️ System Tab
- "🌐 Open Web GUI" - Launch Flask web interface
- "📝 View Logs" - Open most recent log in Notepad
- "📁 Open Log Folder" - Open protocol_logs folder
- "📊 Generate Channels" - Create Home Assistant YAML configs

## ⚡ Command Line Quick Reference

### Monitoring
```bash
# 1-hour monitoring with MQTT
python monitoring/monitor_multi_network.py 1 --mqtt-broker <broker> --mqtt-port 8883 --mqtt-username <user> --mqtt-password <pass> --mqtt-use-tls

# Simple MQTT viewer
python monitoring/mqtt_monitor.py
```

### Diagnostics
```bash
# Radio configuration
python diagnostics/verify_radio_config.py
python diagnostics/fix_radio_secondary.py COM7

# F8 duplicate addresses
python diagnostics/packet_diagnostics.py --f8

# F14 primary timeouts (last 24 hours)
python diagnostics/packet_diagnostics.py --f14 --hours 24

# All faults
python diagnostics/packet_diagnostics.py --faults --hours 24

# Channel 16 history (last 50 packets)
python diagnostics/packet_diagnostics.py --channel 16 --limit 50

# Network health (Network_25, last hour)
python diagnostics/packet_diagnostics.py --network Network_25 --hours 1

# View raw packet hex
python diagnostics/packet_diagnostics.py --raw --limit 10

# Export to CSV
python diagnostics/packet_diagnostics.py --export packets.csv --hours 24
```

## 🚨 Fault Codes

| Code | Description | Action |
|------|-------------|--------|
| F0 | None | Normal operation ✅ |
| F1 | Top card lost comm | Check sensor connection |
| F3 | IR sensor beyond repair | Replace sensor |
| F4 | ADC/board comm issue | Check connections |
| F5 | Did not Null | Check for gas, replace element |
| F6 | Did not Cal (Autocal) | Calibrate manually |
| **F8** | **Duplicate address** | Use diagnostics → Find duplicates |
| F9 | Radio timeout | Check sensor battery/signal |
| F10 | Wired sensor not comm | Check wiring |
| F11 | IR temp changing | Auto-clears |
| F12 | IR element restarting | Auto-clears |
| F13 | 4-20mA fault | Check sensor fault display |
| **F14** | **Can't see Primary** | Use diagnostics → Track F14 |

## 🔐 Safety Checklist

Before monitoring:
1. ✅ Run "Verify Radio Config" (Diagnostics tab)
2. ✅ All radios should show "SECONDARY (RX ONLY)"
3. ✅ If any show "PRIMARY", fix immediately!
4. ✅ Check config.json has correct MQTT settings

## 📊 Network Configuration

```
Network_15:  COM7  @ 115200 baud → OI-7530 (Modbus 30)
Network_20:  COM12 @ 115200 baud → OI-7010 (Modbus 10)
Network_25:  COM11 @ 115200 baud → OI-7032 (Modbus 32)
```

## 🗂️ File Locations

```
D:\oi-7500-pipeline\
├── START_CONTROL_CENTER.bat   ← Double-click to launch
├── launcher.py                 ← Main GUI
├── config.json                 ← Settings
├── protocol_logs\packets.db    ← Database
└── protocol_logs\*.log         ← Log files
```

## 💡 Common Tasks

**Start monitoring:**  
GUI → Monitoring tab → Start

**Check if radios are safe:**  
GUI → Diagnostics tab → Verify Radio Config

**Find F8 conflicts:**  
GUI → Diagnostics tab → Find F8 Duplicates

**Export data:**  
GUI → Database tab → Export to CSV

**View logs:**  
GUI → System tab → View Logs

## 🐛 Troubleshooting

**GUI won't start:**
- Check Python installed: `python --version`
- Check virtual env exists: `.venv\Scripts\python.exe`
- Reinstall deps: `pip install -r requirements.txt`

**No data from radios:**
- Close other programs using COM ports
- Verify ports in config.json
- Check radios powered on

**MQTT not connecting:**
- Verify broker URL in config.json
- Check firewall allows port 8883/1883
- Confirm username/password

**F8 faults:**
- Run diagnostics → Find F8 Duplicates
- Shows which channels share address
- Change address using OI-7010 commands

**F14 faults:**
- Run diagnostics → Track F14 Timeouts
- Check signal strength (RSSI)
- Verify repeater operational
- Confirm network ID matches

## 📞 Support

**Error logs:** `protocol_logs\` folder  
**Config file:** `config.json`  
**Test suite:** `pytest`  
**Old docs:** `README_OLD.md`

---

**Version:** 1.0 | **Updated:** Jan 2026
