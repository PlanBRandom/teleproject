# What To Do With Your Monitoring Data

## 📊 **Data Collected**

Your 24-hour monitoring run captured:
- **16,586 radio packets** (347 KB)
- **5,237 gas sensor readings** 
- **3 networks monitored** (Network 15, 20, 25)
- **7 MB total data**

---

## 🔍 **Quick Analysis**

### Run the Analysis Tool:
```bash
python analyze_data.py
```

This automatically:
- ✅ Analyzes all radio and Modbus data
- ✅ Extracts gas sensor readings
- ✅ Generates summary reports
- ✅ Exports data to CSV files
- ✅ Creates network statistics

---

## 📁 **Exported Files** (in `exports/` folder)

### 1. **`gas_readings_YYYYMMDD_HHMMSS.csv`**
   
**Contains:** All gas sensor readings from the monitoring run
   
**Columns:**
- Timestamp
- Sensor_Address
- Channel
- Reading (gas concentration)
- Battery_V (sensor battery voltage)
- Fault_Code

**What to do with it:**
- 📈 **Import into Excel/Google Sheets** for analysis
- 📊 **Create charts** showing gas levels over time
- 🔔 **Identify alarms** by filtering high readings
- 🔋 **Monitor battery health** by checking Battery_V column
- 📉 **Trend analysis** to spot patterns
- 📧 **Share with clients** as proof of monitoring
- 💾 **Archive for compliance** records

**Excel Quick Tips:**
```
1. Open Excel → Data → From Text/CSV
2. Select gas_readings_*.csv
3. Create pivot table: Sensor_Address vs Reading
4. Insert Line Chart: Timestamp vs Reading
5. Use conditional formatting for alarms (>threshold)
```

### 2. **`monitoring_report_YYYYMMDD_HHMMSS.txt`**

**Contains:** High-level summary of the monitoring run

**What to do with it:**
- 📄 Include in project reports
- 📧 Email to stakeholders
- 💾 Archive with project documentation

---

## 📡 **Radio Log Files** (in `radio_logs/` folder)

### **`radio_log_COM7_YYYYMMDD_HHMMSS.txt`**
- Full text log of all radio traffic
- Useful for debugging and detailed analysis

### **`radio_log_COM7_YYYYMMDD_HHMMSS_data.csv`**
- Structured sensor readings (source for exports)

### **`radio_log_COM7_YYYYMMDD_HHMMSS_hex.txt`**
- Raw hex dumps of packets
- For protocol analysis and troubleshooting

---

## 📊 **Protocol Logs** (in `protocol_logs/` folder)

### **`Network_XX_YYYYMMDD_HHMMSS.log`**
- Network-specific activity logs
- Shows which sensors are on which network

### **`stats.json`**
- Real-time statistics
- Frame types, protocol counts, byte totals

---

## 💡 **Practical Use Cases**

### **1. Compliance & Safety Reports**
```
✓ Export gas_readings.csv
✓ Filter for alarm conditions (Reading > threshold)
✓ Generate report showing all alarms with timestamps
✓ Include in safety documentation
```

### **2. Equipment Health Monitoring**
```
✓ Check Battery_V column in gas_readings.csv
✓ Identify sensors with low battery (<3.0V)
✓ Schedule battery replacements
✓ Track battery life trends
```

### **3. Network Coverage Analysis**
```
✓ Review Network_XX logs
✓ Count packets per network
✓ Identify coverage gaps
✓ Optimize radio placement
```

### **4. Sensor Performance**
```
✓ Filter by Sensor_Address in CSV
✓ Check reading consistency
✓ Identify faulty sensors (erratic readings)
✓ Verify calibration
```

### **5. Historical Trending**
```
✓ Import multiple monitoring runs into database
✓ Create long-term trend charts
✓ Identify seasonal patterns
✓ Predict maintenance needs
```

---

## 🎨 **Visualization Ideas**

### **Excel/Google Sheets Charts:**
1. **Time Series Line Chart**
   - X-axis: Timestamp
   - Y-axis: Gas Reading
   - Multiple lines for different sensors

2. **Heatmap**
   - Rows: Sensor addresses
   - Columns: Time periods
   - Color: Reading level

3. **Battery Status Bar Chart**
   - X-axis: Sensor addresses
   - Y-axis: Battery voltage
   - Color code: Red <3.0V, Yellow 3.0-3.3V, Green >3.3V

4. **Network Activity Pie Chart**
   - Show packet distribution across networks

---

## 🔄 **Automated Processing**

Want to automatically process data? Create custom scripts:

```python
# Example: Find all alarm conditions
import pandas as pd

df = pd.read_csv('exports/gas_readings_*.csv')
alarms = df[df['Reading'] > 25]  # 25 ppm threshold
print(f"Found {len(alarms)} alarm conditions")
alarms.to_csv('alarm_report.csv', index=False)
```

---

## 📧 **Sharing Data**

### **For Clients:**
- Send `gas_readings_*.csv` + summary report
- Include charts/graphs from Excel
- Provide alarm analysis

### **For Team:**
- Share entire `exports/` folder
- Include raw logs if debugging needed
- Add notes about any anomalies

### **For Archives:**
- Compress all logs: `radio_logs/`, `protocol_logs/`, `logs/`
- Include `exports/` folder
- Add monitoring_report.txt
- Label with date and location

---

## 🚀 **Next Steps**

1. **Run analysis tool** to generate exports
   ```bash
   python analyze_data.py
   ```

2. **Open CSV in Excel** for visualization

3. **Create monitoring schedule** - run weekly/monthly

4. **Set up automated reports** - scheduled analysis

5. **Archive old data** - move to backup storage

---

## 📞 **Quick Reference Commands**

| Task | Command |
|------|---------|
| Analyze all data | `python analyze_data.py` |
| View summary | Open `exports/monitoring_report_*.txt` |
| View readings | Open `exports/gas_readings_*.csv` in Excel |
| Check logs | Look in `radio_logs/`, `protocol_logs/`, `logs/` |
| Clean old data | Move old files to archive folder |

---

**Remember:** This data is valuable for safety, compliance, and operations. Keep backups!
