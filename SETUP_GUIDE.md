# OI-7500 Pipeline - Quick Setup Guide

## 🚀 First Time Setup

Before you can start monitoring, you need to configure the system for your hardware setup.

### Step 1: Run Configuration Wizard

**Option A - Double-click:**
```
CONFIGURE_SYSTEM.bat
```

**Option B - Command line:**
```powershell
python configure_system.py
```

The wizard will ask you for:

#### **Modbus Configuration:**
- Monitor model (OI-7032, OI-7530, OI-7010, etc.)
- COM port (e.g., COM10)
- Baud rate (typically 19200)
- Slave ID (32 for OI-7032, 30 for OI-7530, 10 for OI-7010)
- MQTT broker settings

#### **Radio Configuration (for each receiver):**
- How many radio receivers you have
- COM port for each radio
- Baud rate (typically 115200)
- Network ID
- Role: Primary or Secondary
  - **Primary**: Full logging + MQTT publishing
  - **Secondary**: Monitoring only

### Step 2: Start Monitoring

**Option A - Double-click:**
```
START_MONITORING.bat
```

**Option B - Command line:**
```powershell
.\START_MONITORING.ps1
```

The script will:
1. Check if configuration exists
2. Offer to run wizard if not configured
3. Display current configuration
4. Start all monitoring processes
5. Run for 24 hours

---

## 📋 Configuration Files Created

After running the wizard, you'll have:

- `config.yaml` - Modbus and MQTT settings
- `radio_config_comX.json` - One per radio receiver

**Example config.yaml:**
```yaml
modbus:
  port: COM10
  baudrate: 19200
  slave_id: 32
mqtt:
  broker: localhost
  port: 1883
```

**Example radio_config_com7.json:**
```json
{
  "port": "COM7",
  "baudrate": 115200,
  "network_id": 15,
  "role": "primary"
}
```

---

## 🔧 Reconfiguring

To change settings:

1. Run `CONFIGURE_SYSTEM.bat` again
2. Or manually edit `config.yaml` and radio config files
3. Or delete configs and they'll be recreated on next start

---

## ✅ Testing Connection

Test Modbus connection before starting full monitoring:

```powershell
python test_modbus_connection.py
```

This will verify:
- COM port is accessible
- Device responds on configured slave ID
- Register reads work correctly

---

## 🎯 Typical Setups

### **Single OI-7032 with 3 Radios**
```
Modbus: COM10, 19200 baud, Slave ID 32
Radio 1: COM7, 115200 baud, Network 15, Primary
Radio 2: COM11, 115200 baud, Network 20, Primary  
Radio 3: COM12, 115200 baud, Network 25, Primary
```

### **Multiple Monitors (requires multiple runs)**
```
Run 1: OI-7032 on COM10, Slave 32
Run 2: OI-7530 on COM8, Slave 30
Run 3: OI-7010 on COM9, Slave 10
```

---

## 📊 While Monitoring

Check status:
```powershell
Get-Process python*
```

View recent logs:
```powershell
Get-ChildItem logs | Sort-Object LastWriteTime -Descending | Select-Object -First 5
```

Stop monitoring:
```powershell
Get-Process python* | Stop-Process
```

---

## 🔍 Troubleshooting

**No Modbus data captured:**
1. Verify device is powered on
2. Check COM port in Device Manager
3. Run `python test_modbus_connection.py`
4. Try different slave ID (32, 30, 10, or 1)

**Radio not receiving:**
1. Check COM port and baud rate
2. Verify radio is powered on
3. Check network ID matches transmitters

**"Configuration not found":**
- Run `CONFIGURE_SYSTEM.bat` first

---

## 🎬 Next Steps

1. ✅ Configure system → `CONFIGURE_SYSTEM.bat`
2. ✅ Test Modbus → `python test_modbus_connection.py`  
3. ✅ Start monitoring → `START_MONITORING.bat`
4. ✅ Let it run for 24 hours
5. ✅ Review logs and data in `logs/` and `protocol_logs/`
