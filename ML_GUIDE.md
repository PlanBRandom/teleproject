# Machine Learning Analytics Guide

Complete guide to using ML-powered predictive analytics for gas sensor monitoring.

## Overview

The ML analytics system provides:

1. **Sensor Degradation Prediction** - Predict when sensors need calibration
2. **Anomaly Detection** - Identify unusual readings in real-time
3. **Response Time Analysis** - Monitor sensor performance
4. **Maintenance Scheduling** - Optimize calibration intervals

## Quick Start

### 1. Install ML Dependencies

```powershell
pip install -r requirements.txt
```

This installs: numpy, pandas, scikit-learn, scipy

### 2. Collect Training Data

First, run the normal pipeline to collect sensor data:

```powershell
python -m pipeline.main
```

This will automatically start collecting data to the `ml_data/` directory when ML features are enabled.

### 3. Train and Analyze

After collecting data for a few days/weeks:

```powershell
# Run comprehensive analysis
python train_ml_models.py --days 30 --export-report

# View results in ml_reports/ directory
```

### 4. Enable Real-Time ML Monitoring

```powershell
# Start ML-powered live monitoring
python ml_live_monitor.py --config config.yaml
```

## Detailed Features

### Sensor Degradation Prediction

**What it does:**
- Tracks sensor drift over time using linear regression
- Calculates drift rate (change per day)
- Predicts days until calibration needed
- Assigns urgency levels: Critical, High, Medium, Low

**How it works:**
1. Collects historical sensor readings
2. Calculates rolling mean to smooth noise
3. Fits linear model to identify drift trend
4. Extrapolates to predict when 10% drift threshold is reached
5. Provides confidence score (R²)

**Example output:**
```
🔴 Channel 12: CRITICAL  | Days to cal:    3.2 | Drift: +0.0234/day
   → Immediate calibration required
```

**Usage:**
```python
from pipeline.ml_analytics import SensorDegradationPredictor
import pandas as pd

predictor = SensorDegradationPredictor()
df = pd.read_csv('sensor_data.csv')  # Your data

drift_info = predictor.calculate_drift(df, channel=5)
print(f"Drift rate: {drift_info['drift_rate_per_day']:.4f}")
print(f"Days to calibration: {drift_info['days_to_calibration']:.1f}")
print(f"Confidence: {drift_info['confidence']:.2%}")
```

### Anomaly Detection

**What it does:**
- Detects readings that deviate from normal patterns
- Uses statistical methods (Z-score and IQR)
- Learns baselines automatically
- Provides anomaly scores and reasons

**Methods:**
1. **Z-Score**: Flags values > N standard deviations from mean
2. **IQR**: Identifies outliers using interquartile range

**Configuration:**
```yaml
ml:
  anomaly_detection:
    sensitivity: 3.0     # Standard deviations (lower = more sensitive)
    window_size: 100     # Number of readings for baseline
```

**Usage:**
```python
from pipeline.ml_analytics import AnomalyDetector

detector = AnomalyDetector(sensitivity=3.0)

# Update baseline with historical data
detector.update_baseline(channel=1, values=historical_readings)

# Check new reading
result = detector.detect_anomaly(channel=1, value=12.5)
if result['is_anomaly']:
    print(f"Anomaly detected! Score: {result['score']:.2f}")
    print(f"Reason: {result['reason']}")
```

### Response Time Analysis

**What it does:**
- Measures how quickly sensors respond to concentration changes
- Identifies performance degradation
- Tracks event frequency

**Metrics:**
- Average response time
- Min/Max response times
- Event count
- Performance status (normal/degraded)

**Usage:**
```python
from pipeline.ml_analytics import ResponseTimeAnalyzer

analyzer = ResponseTimeAnalyzer()
metrics = analyzer.analyze_response(df, channel=3, event_threshold=1.0)

print(f"Average response time: {metrics['average_response_time']:.1f}s")
print(f"Status: {metrics['status']}")
```

## Data Storage

### Directory Structure

```
ml_data/
├── batch_20251219_140022.json
├── batch_20251219_150033.json
└── batch_20251219_160044.json

ml_reports/
├── ml_analysis_report_20251219_143022.json
└── ml_summary_20251219_143022.txt
```

### Data Format

Each batch file contains JSON records:

```json
[
  {
    "timestamp": "2025-12-19T14:30:22.123456",
    "channel": 5,
    "value": 10.23,
    "metadata": {
      "temperature": 22.5,
      "humidity": 45.2
    }
  },
  ...
]
```

## Complete Examples

### Example 1: Batch Analysis

```python
from pipeline.ml_analytics import MLAnalyticsPipeline

# Initialize
pipeline = MLAnalyticsPipeline(config={
    'storage_path': 'ml_data',
    'anomaly_sensitivity': 3.0
})

# Run comprehensive analysis
analysis = pipeline.run_analysis(days=30)

# Export report
pipeline.export_report(analysis, 'my_report.json')

# Check critical channels
for channel, pred in analysis['maintenance_predictions'].items():
    if pred.get('urgency') == 'critical':
        print(f"⚠️  Channel {channel}: {pred['recommended_action']}")
```

### Example 2: Real-Time Processing

```python
from pipeline.ml_analytics import MLAnalyticsPipeline
from datetime import datetime

pipeline = MLAnalyticsPipeline()

# Process incoming readings
while True:
    channel, value = read_sensor()  # Your sensor reading function
    
    result = pipeline.process_reading(channel, value)
    
    if result['anomaly']['is_anomaly']:
        send_alert(f"Anomaly on channel {channel}: {result['anomaly']['reason']}")
    
    # Save periodically
    if reading_count % 100 == 0:
        pipeline.collector.save_batch()
```

### Example 3: Custom Analysis

```python
from pipeline.ml_analytics import (
    SensorDataCollector,
    AnomalyDetector,
    SensorDegradationPredictor
)
import pandas as pd

# Load your own data
df = pd.read_csv('my_sensor_data.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])

# Run custom analysis
predictor = SensorDegradationPredictor()

for channel in df['channel'].unique():
    drift_info = predictor.calculate_drift(df, channel)
    
    if drift_info.get('drift_rate_per_day', 0) > 0.01:
        print(f"Channel {channel} showing significant drift")
        print(f"  Rate: {drift_info['drift_rate_per_day']:.4f}/day")
        print(f"  Action: {drift_info.get('recommended_action')}")
```

## Configuration

### Complete ML Configuration

Add to `config.yaml`:

```yaml
ml:
  # Enable ML features
  enabled: true
  
  # Data storage
  storage_path: ml_data
  batch_save_interval: 100  # Save every N readings
  
  # Anomaly detection
  anomaly_detection:
    enabled: true
    sensitivity: 3.0        # Std deviations (2.0 = more sensitive, 4.0 = less)
    window_size: 100        # Readings for baseline calculation
  
  # Maintenance prediction
  maintenance_prediction:
    enabled: true
    drift_threshold: 0.10   # 10% drift triggers calibration
    analysis_interval: 24   # Run analysis every N hours
    
  # Response time analysis
  response_analysis:
    enabled: true
    event_threshold: 1.0    # Minimum change to count as event
    
  # Alerts
  alerts:
    anomaly_alerts: true
    critical_maintenance_alerts: true
    webhook_url: null       # Optional: Slack/Teams webhook
```

## Command-Line Tools

### train_ml_models.py

Train models and generate reports:

```powershell
# Basic usage
python train_ml_models.py

# Analyze 90 days of data
python train_ml_models.py --days 90

# Export detailed report
python train_ml_models.py --days 30 --export-report

# Custom sensitivity
python train_ml_models.py --anomaly-sensitivity 2.5

# Specify output directory
python train_ml_models.py --output custom_reports/

# Verbose output
python train_ml_models.py --verbose
```

### ml_live_monitor.py

Real-time ML monitoring:

```powershell
# Basic usage
python ml_live_monitor.py

# Custom config
python ml_live_monitor.py --config my_config.yaml

# Adjust sensitivity
python ml_live_monitor.py --anomaly-sensitivity 2.0

# Custom ML data storage
python ml_live_monitor.py --ml-storage /path/to/ml_data

# Debug mode
python ml_live_monitor.py --verbose
```

## Troubleshooting

### No Historical Data

**Problem:** "No historical data found!"

**Solutions:**
1. Run main pipeline first to collect data
2. Check `ml_data/` directory exists and has batch files
3. Ensure data collection is enabled in config

### Insufficient Data

**Problem:** Analysis returns "Insufficient data" errors

**Solutions:**
1. Collect more data (at least a few days)
2. Reduce `--days` parameter
3. Check that sensors are actively being polled

### Poor Predictions

**Problem:** Drift predictions seem inaccurate

**Solutions:**
1. Collect longer history (weeks instead of days)
2. Ensure sensors are stable during baseline period
3. Check for calibration events in data (may skew predictions)
4. Adjust drift_threshold in config

### Too Many Anomalies

**Problem:** Everything flagged as anomaly

**Solutions:**
1. Increase anomaly_sensitivity (e.g., 3.0 → 4.0)
2. Increase window_size for more stable baseline
3. Ensure baseline period includes normal operation

### Memory Issues

**Problem:** Large data files causing memory errors

**Solutions:**
1. Reduce analysis window (`--days` parameter)
2. Process data in chunks
3. Clean up old batch files periodically

## Best Practices

### Data Collection

1. **Continuous Collection**: Run pipeline 24/7 for best results
2. **Stable Baseline**: Collect at least 1 week of normal data before trusting predictions
3. **Regular Backups**: Backup `ml_data/` directory periodically
4. **Clean Data**: Remove or mark calibration periods in data

### Analysis Frequency

- **Training**: Run weekly or after major events
- **Live Monitoring**: Continuous when enabled
- **Report Generation**: Daily or weekly for documentation

### Sensitivity Tuning

Start conservative and adjust:

```
More False Positives → Increase sensitivity (3.0 → 4.0)
Missing Real Issues  → Decrease sensitivity (3.0 → 2.5)
```

### Production Deployment

1. Test on historical data first
2. Monitor false positive rate
3. Set up proper alerting infrastructure
4. Document baseline performance
5. Plan calibration schedule based on predictions

## Integration Examples

### Home Assistant Automation

```yaml
automation:
  - alias: "ML Anomaly Alert"
    trigger:
      platform: mqtt
      topic: "oi7530/ml/anomaly"
    action:
      - service: notify.mobile_app
        data:
          message: "Gas sensor anomaly detected: {{ trigger.payload_json.channel }}"
          
  - alias: "Calibration Reminder"
    trigger:
      platform: mqtt
      topic: "oi7530/ml/maintenance"
    condition:
      - condition: template
        value_template: "{{ trigger.payload_json.urgency == 'critical' }}"
    action:
      - service: persistent_notification.create
        data:
          title: "Sensor Calibration Needed"
          message: "Channel {{ trigger.payload_json.channel }} needs calibration"
```

### Slack Notifications

```python
import requests

def send_slack_alert(channel, message):
    webhook_url = "https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
    requests.post(webhook_url, json={"text": f"Channel {channel}: {message}"})

# In your monitoring code
if result['anomaly']['is_anomaly']:
    send_slack_alert(channel, result['anomaly']['reason'])
```

### InfluxDB Storage

```python
from influxdb_client import InfluxDBClient, Point

client = InfluxDBClient(url="http://localhost:8086", token="your-token")
write_api = client.write_api()

def store_prediction(channel, prediction):
    point = Point("sensor_drift") \
        .tag("channel", channel) \
        .field("drift_rate", prediction['drift_rate_per_day']) \
        .field("days_to_calibration", prediction['days_to_calibration'])
    write_api.write(bucket="gas_monitoring", record=point)
```

## Advanced Topics

### Custom ML Models

You can extend the system with scikit-learn models:

```python
from sklearn.ensemble import IsolationForest
import numpy as np

class AdvancedAnomalyDetector:
    def __init__(self):
        self.model = IsolationForest(contamination=0.1)
        
    def train(self, data):
        X = np.array(data).reshape(-1, 1)
        self.model.fit(X)
        
    def predict(self, value):
        prediction = self.model.predict([[value]])
        return prediction[0] == -1  # -1 indicates anomaly
```

### Multi-Sensor Correlation

Detect issues across multiple sensors:

```python
def check_correlation_anomaly(readings):
    """Detect if multiple sensors show unusual patterns"""
    anomaly_count = sum(1 for r in readings if r['is_anomaly'])
    
    if anomaly_count >= 3:
        return {
            'correlation_anomaly': True,
            'affected_channels': [r['channel'] for r in readings if r['is_anomaly']],
            'severity': 'high'
        }
    return {'correlation_anomaly': False}
```

## Support

For issues or questions:
- Check logs with `--verbose` flag
- Review `ml_reports/` for analysis details
- Ensure adequate training data (1+ weeks)
- Verify configuration settings

## License

MIT License - See main LICENSE file
