"""
Machine Learning Analytics for Gas Sensor Data

Provides predictive analytics including:
- Sensor degradation prediction
- Anomaly detection
- Calibration interval optimization
- Response time analysis
"""

import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import json

logger = logging.getLogger(__name__)


class SensorDataCollector:
    """Collects and preprocesses sensor data for ML analysis"""
    
    def __init__(self, storage_path: str = "ml_data"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(exist_ok=True)
        self.current_data = []
        
    def add_reading(self, channel: int, value: float, timestamp: datetime, 
                   metadata: Optional[Dict] = None):
        """Add a sensor reading to the dataset"""
        record = {
            'timestamp': timestamp.isoformat(),
            'channel': channel,
            'value': value,
            'metadata': metadata or {}
        }
        self.current_data.append(record)
        
    def save_batch(self, batch_name: Optional[str] = None):
        """Save current batch to disk"""
        if not self.current_data:
            return
            
        if batch_name is None:
            batch_name = datetime.now().strftime("%Y%m%d_%H%M%S")
            
        filepath = self.storage_path / f"batch_{batch_name}.json"
        with open(filepath, 'w') as f:
            json.dump(self.current_data, f)
            
        logger.info(f"Saved {len(self.current_data)} records to {filepath}")
        self.current_data = []
        
    def load_historical_data(self, days: int = 30) -> pd.DataFrame:
        """Load historical data from storage"""
        all_data = []
        
        for filepath in self.storage_path.glob("batch_*.json"):
            with open(filepath, 'r') as f:
                batch_data = json.load(f)
                all_data.extend(batch_data)
                
        if not all_data:
            return pd.DataFrame()
            
        df = pd.DataFrame(all_data)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        # Filter by date range
        cutoff = datetime.now() - timedelta(days=days)
        df = df[df['timestamp'] >= cutoff]
        
        return df


class AnomalyDetector:
    """Detects anomalies in sensor readings using statistical methods"""
    
    def __init__(self, window_size: int = 100, sensitivity: float = 3.0):
        self.window_size = window_size
        self.sensitivity = sensitivity  # Standard deviations
        self.baselines = {}  # Channel baseline statistics
        
    def update_baseline(self, channel: int, values: List[float]):
        """Update baseline statistics for a channel"""
        if len(values) < self.window_size:
            return
            
        recent_values = values[-self.window_size:]
        self.baselines[channel] = {
            'mean': np.mean(recent_values),
            'std': np.std(recent_values),
            'median': np.median(recent_values),
            'q1': np.percentile(recent_values, 25),
            'q3': np.percentile(recent_values, 75)
        }
        
    def detect_anomaly(self, channel: int, value: float) -> Dict:
        """
        Detect if a reading is anomalous
        
        Returns:
            Dict with 'is_anomaly', 'score', 'reason'
        """
        if channel not in self.baselines:
            return {'is_anomaly': False, 'score': 0.0, 'reason': 'No baseline'}
            
        baseline = self.baselines[channel]
        
        # Z-score method
        if baseline['std'] > 0:
            z_score = abs(value - baseline['mean']) / baseline['std']
            is_anomaly = z_score > self.sensitivity
            
            if is_anomaly:
                return {
                    'is_anomaly': True,
                    'score': z_score,
                    'reason': f'Z-score {z_score:.2f} exceeds threshold {self.sensitivity}'
                }
        
        # IQR method (additional check)
        iqr = baseline['q3'] - baseline['q1']
        lower_bound = baseline['q1'] - 1.5 * iqr
        upper_bound = baseline['q3'] + 1.5 * iqr
        
        if value < lower_bound or value > upper_bound:
            return {
                'is_anomaly': True,
                'score': abs(value - baseline['median']) / (iqr + 1e-6),
                'reason': f'IQR outlier: value {value:.2f} outside [{lower_bound:.2f}, {upper_bound:.2f}]'
            }
            
        return {'is_anomaly': False, 'score': 0.0, 'reason': 'Normal'}


class SensorDegradationPredictor:
    """Predicts sensor degradation and maintenance needs"""
    
    def __init__(self):
        self.drift_history = {}  # Channel drift rates over time
        
    def calculate_drift(self, df: pd.DataFrame, channel: int) -> Dict:
        """
        Calculate sensor drift metrics
        
        Returns:
            Dict with drift_rate, confidence, days_to_threshold
        """
        channel_data = df[df['channel'] == channel].copy()
        
        if len(channel_data) < 10:
            return {'error': 'Insufficient data'}
            
        # Sort by timestamp
        channel_data = channel_data.sort_values('timestamp')
        channel_data['days'] = (channel_data['timestamp'] - channel_data['timestamp'].min()).dt.total_seconds() / 86400
        
        # Calculate rolling mean to identify drift
        channel_data['rolling_mean'] = channel_data['value'].rolling(window=20, min_periods=5).mean()
        
        # Simple linear regression for drift
        if len(channel_data) >= 20:
            x = channel_data['days'].values
            y = channel_data['rolling_mean'].dropna().values
            x = x[-len(y):]
            
            # Calculate slope (drift rate per day)
            coeffs = np.polyfit(x, y, 1)
            drift_rate = coeffs[0]
            
            # Calculate R² for confidence
            y_pred = np.polyval(coeffs, x)
            ss_res = np.sum((y - y_pred) ** 2)
            ss_tot = np.sum((y - np.mean(y)) ** 2)
            r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
            
            # Estimate days until calibration needed (assuming 10% drift threshold)
            current_value = y[-1]
            threshold_value = current_value * 1.1  # 10% drift
            
            if abs(drift_rate) > 1e-6:
                days_to_threshold = abs((threshold_value - current_value) / drift_rate)
            else:
                days_to_threshold = float('inf')
                
            return {
                'drift_rate_per_day': float(drift_rate),
                'confidence': float(r_squared),
                'current_value': float(current_value),
                'days_to_calibration': float(min(days_to_threshold, 365)),
                'status': 'drifting' if abs(drift_rate) > 0.01 else 'stable'
            }
            
        return {'error': 'Insufficient processed data'}
        
    def predict_maintenance(self, df: pd.DataFrame) -> Dict[int, Dict]:
        """
        Predict maintenance needs for all channels
        
        Returns:
            Dict mapping channel to maintenance prediction
        """
        predictions = {}
        
        for channel in df['channel'].unique():
            drift_info = self.calculate_drift(df, channel)
            
            if 'error' not in drift_info:
                # Categorize urgency
                days = drift_info['days_to_calibration']
                if days < 7:
                    urgency = 'critical'
                elif days < 30:
                    urgency = 'high'
                elif days < 90:
                    urgency = 'medium'
                else:
                    urgency = 'low'
                    
                predictions[channel] = {
                    **drift_info,
                    'urgency': urgency,
                    'recommended_action': self._get_recommendation(urgency, drift_info)
                }
            else:
                predictions[channel] = drift_info
                
        return predictions
        
    def _get_recommendation(self, urgency: str, drift_info: Dict) -> str:
        """Generate maintenance recommendation"""
        if urgency == 'critical':
            return "Immediate calibration required"
        elif urgency == 'high':
            return "Schedule calibration within 1 week"
        elif urgency == 'medium':
            return "Plan calibration within 1 month"
        else:
            return "Monitor - no immediate action needed"


class ResponseTimeAnalyzer:
    """Analyzes sensor response time characteristics"""
    
    def __init__(self):
        self.response_times = {}
        
    def analyze_response(self, df: pd.DataFrame, channel: int, 
                        event_threshold: float = 1.0) -> Dict:
        """
        Analyze sensor response time to concentration changes
        
        Args:
            df: DataFrame with sensor data
            channel: Channel number to analyze
            event_threshold: Minimum change to consider an event
            
        Returns:
            Dict with response time metrics
        """
        channel_data = df[df['channel'] == channel].copy()
        channel_data = channel_data.sort_values('timestamp')
        
        if len(channel_data) < 10:
            return {'error': 'Insufficient data'}
            
        # Calculate rate of change
        channel_data['value_diff'] = channel_data['value'].diff()
        channel_data['time_diff'] = channel_data['timestamp'].diff().dt.total_seconds()
        
        # Identify rapid change events
        events = channel_data[abs(channel_data['value_diff']) > event_threshold]
        
        if len(events) == 0:
            return {
                'average_response_time': None,
                'event_count': 0,
                'status': 'No significant events detected'
            }
            
        # Calculate response characteristics
        response_times = events['time_diff'].dropna()
        
        return {
            'average_response_time': float(response_times.mean()),
            'min_response_time': float(response_times.min()),
            'max_response_time': float(response_times.max()),
            'event_count': len(events),
            'status': 'normal' if response_times.mean() < 60 else 'degraded'
        }


class MLAnalyticsPipeline:
    """Complete ML analytics pipeline for gas monitoring"""
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.collector = SensorDataCollector(
            storage_path=self.config.get('storage_path', 'ml_data')
        )
        self.anomaly_detector = AnomalyDetector(
            window_size=self.config.get('anomaly_window', 100),
            sensitivity=self.config.get('anomaly_sensitivity', 3.0)
        )
        self.degradation_predictor = SensorDegradationPredictor()
        self.response_analyzer = ResponseTimeAnalyzer()
        
    def process_reading(self, channel: int, value: float, 
                       timestamp: Optional[datetime] = None) -> Dict:
        """
        Process a single sensor reading through ML pipeline
        
        Returns:
            Dict with analysis results
        """
        if timestamp is None:
            timestamp = datetime.now()
            
        # Store reading
        self.collector.add_reading(channel, value, timestamp)
        
        # Check for anomaly
        anomaly_result = self.anomaly_detector.detect_anomaly(channel, value)
        
        return {
            'timestamp': timestamp.isoformat(),
            'channel': channel,
            'value': value,
            'anomaly': anomaly_result
        }
        
    def run_analysis(self, days: int = 30) -> Dict:
        """
        Run complete analysis on historical data
        
        Returns:
            Dict with comprehensive analytics
        """
        logger.info(f"Running ML analysis on {days} days of data")
        
        # Load historical data
        df = self.collector.load_historical_data(days=days)
        
        if df.empty:
            return {'error': 'No historical data available'}
            
        # Update anomaly baselines
        for channel in df['channel'].unique():
            channel_values = df[df['channel'] == channel]['value'].tolist()
            self.anomaly_detector.update_baseline(channel, channel_values)
            
        # Predict maintenance needs
        maintenance_predictions = self.degradation_predictor.predict_maintenance(df)
        
        # Analyze response times
        response_analysis = {}
        for channel in df['channel'].unique():
            response_analysis[channel] = self.response_analyzer.analyze_response(df, channel)
            
        # Generate summary
        summary = {
            'analysis_date': datetime.now().isoformat(),
            'data_points': len(df),
            'channels_analyzed': len(df['channel'].unique()),
            'date_range': {
                'start': df['timestamp'].min().isoformat(),
                'end': df['timestamp'].max().isoformat()
            },
            'maintenance_predictions': maintenance_predictions,
            'response_analysis': response_analysis,
            'anomaly_baselines': {
                str(k): v for k, v in self.anomaly_detector.baselines.items()
            }
        }
        
        return summary
        
    def export_report(self, analysis_results: Dict, output_path: str = "ml_report.json"):
        """Export analysis results to file"""
        output_file = Path(output_path)
        with open(output_file, 'w') as f:
            json.dump(analysis_results, f, indent=2)
        logger.info(f"Analysis report exported to {output_file}")


if __name__ == "__main__":
    # Example usage
    logging.basicConfig(level=logging.INFO)
    
    # Initialize pipeline
    pipeline = MLAnalyticsPipeline()
    
    # Simulate some data collection
    print("Simulating sensor data collection...")
    for i in range(100):
        # Simulate readings for 3 channels
        for channel in [1, 2, 3]:
            value = 10.0 + np.random.normal(0, 0.5) + (i * 0.01)  # Slight drift
            result = pipeline.process_reading(channel, value)
            if result['anomaly']['is_anomaly']:
                print(f"⚠️  Anomaly detected: {result}")
                
    # Save batch
    pipeline.collector.save_batch()
    
    # Run analysis
    print("\nRunning comprehensive analysis...")
    analysis = pipeline.run_analysis(days=30)
    print(json.dumps(analysis, indent=2))
