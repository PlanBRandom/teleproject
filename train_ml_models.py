#!/usr/bin/env python3
"""
Train ML models on historical gas sensor data

This script trains and evaluates machine learning models for:
- Anomaly detection
- Sensor degradation prediction
- Calibration scheduling

Usage:
    python train_ml_models.py --days 90 --output models/
    python train_ml_models.py --config config.yaml --export-report
"""

import argparse
import logging
import sys
from pathlib import Path
from datetime import datetime
import json

from pipeline.ml_analytics import MLAnalyticsPipeline, SensorDataCollector

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description='Train ML models for gas sensor analytics')
    parser.add_argument('--days', type=int, default=30,
                       help='Number of days of historical data to analyze (default: 30)')
    parser.add_argument('--storage-path', type=str, default='ml_data',
                       help='Path to ML data storage (default: ml_data)')
    parser.add_argument('--output', type=str, default='ml_reports',
                       help='Output directory for reports and models (default: ml_reports)')
    parser.add_argument('--anomaly-sensitivity', type=float, default=3.0,
                       help='Anomaly detection sensitivity in std deviations (default: 3.0)')
    parser.add_argument('--anomaly-window', type=int, default=100,
                       help='Window size for anomaly baseline (default: 100)')
    parser.add_argument('--export-report', action='store_true',
                       help='Export detailed analysis report to JSON')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose logging')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Create output directory
    output_path = Path(args.output)
    output_path.mkdir(exist_ok=True)
    
    logger.info("="*60)
    logger.info("GAS SENSOR ML ANALYTICS - TRAINING PIPELINE")
    logger.info("="*60)
    logger.info(f"Analysis window: {args.days} days")
    logger.info(f"Data storage: {args.storage_path}")
    logger.info(f"Output path: {args.output}")
    logger.info(f"Anomaly sensitivity: {args.anomaly_sensitivity} σ")
    logger.info("")
    
    # Initialize ML pipeline
    config = {
        'storage_path': args.storage_path,
        'anomaly_window': args.anomaly_window,
        'anomaly_sensitivity': args.anomaly_sensitivity
    }
    
    pipeline = MLAnalyticsPipeline(config=config)
    
    # Check for available data
    logger.info("Loading historical sensor data...")
    df = pipeline.collector.load_historical_data(days=args.days)
    
    if df.empty:
        logger.error("No historical data found!")
        logger.error(f"Please ensure data files exist in '{args.storage_path}/' directory")
        logger.error("Data should be collected using the main pipeline first.")
        sys.exit(1)
    
    logger.info(f"✓ Loaded {len(df)} data points")
    logger.info(f"✓ Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
    logger.info(f"✓ Channels: {sorted(df['channel'].unique())}")
    logger.info("")
    
    # Run comprehensive analysis
    logger.info("Running ML analytics pipeline...")
    logger.info("-" * 60)
    
    analysis_results = pipeline.run_analysis(days=args.days)
    
    if 'error' in analysis_results:
        logger.error(f"Analysis failed: {analysis_results['error']}")
        sys.exit(1)
    
    # Display results
    logger.info("")
    logger.info("="*60)
    logger.info("ANALYSIS RESULTS")
    logger.info("="*60)
    logger.info("")
    
    # Maintenance predictions
    logger.info("SENSOR DEGRADATION & MAINTENANCE PREDICTIONS")
    logger.info("-" * 60)
    
    maintenance = analysis_results.get('maintenance_predictions', {})
    critical_count = 0
    
    for channel, prediction in sorted(maintenance.items()):
        if 'error' in prediction:
            logger.warning(f"Channel {channel}: {prediction['error']}")
            continue
            
        urgency = prediction.get('urgency', 'unknown')
        days_to_cal = prediction.get('days_to_calibration', 'N/A')
        drift_rate = prediction.get('drift_rate_per_day', 0)
        
        # Color code by urgency
        if urgency == 'critical':
            symbol = "🔴"
            critical_count += 1
        elif urgency == 'high':
            symbol = "🟠"
        elif urgency == 'medium':
            symbol = "🟡"
        else:
            symbol = "🟢"
        
        logger.info(f"{symbol} Channel {channel:2d}: {urgency.upper():8s} | "
                   f"Days to cal: {days_to_cal:6.1f} | "
                   f"Drift: {drift_rate:+.4f}/day")
        logger.info(f"   → {prediction.get('recommended_action', 'N/A')}")
    
    logger.info("")
    
    # Response time analysis
    logger.info("SENSOR RESPONSE TIME ANALYSIS")
    logger.info("-" * 60)
    
    response = analysis_results.get('response_analysis', {})
    for channel, metrics in sorted(response.items()):
        if 'error' in metrics:
            logger.warning(f"Channel {channel}: {metrics['error']}")
            continue
            
        avg_time = metrics.get('average_response_time', 'N/A')
        event_count = metrics.get('event_count', 0)
        status = metrics.get('status', 'unknown')
        
        symbol = "✓" if status == 'normal' else "⚠"
        logger.info(f"{symbol} Channel {channel:2d}: Avg response: {avg_time:.1f}s | "
                   f"Events: {event_count} | Status: {status}")
    
    logger.info("")
    
    # Summary statistics
    logger.info("SUMMARY")
    logger.info("-" * 60)
    logger.info(f"Data points analyzed: {analysis_results['data_points']:,}")
    logger.info(f"Channels monitored: {analysis_results['channels_analyzed']}")
    logger.info(f"Critical maintenance needs: {critical_count}")
    logger.info("")
    
    # Export report if requested
    if args.export_report:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = output_path / f"ml_analysis_report_{timestamp}.json"
        pipeline.export_report(analysis_results, str(report_file))
        logger.info(f"✓ Detailed report exported to: {report_file}")
        
        # Also create a human-readable summary
        summary_file = output_path / f"ml_summary_{timestamp}.txt"
        with open(summary_file, 'w') as f:
            f.write("GAS SENSOR ML ANALYSIS SUMMARY\n")
            f.write("=" * 60 + "\n\n")
            f.write(f"Analysis Date: {analysis_results['analysis_date']}\n")
            f.write(f"Data Points: {analysis_results['data_points']:,}\n")
            f.write(f"Date Range: {analysis_results['date_range']['start']} to "
                   f"{analysis_results['date_range']['end']}\n\n")
            
            f.write("CRITICAL MAINTENANCE ALERTS\n")
            f.write("-" * 60 + "\n")
            for channel, pred in sorted(maintenance.items()):
                if pred.get('urgency') in ['critical', 'high']:
                    f.write(f"Channel {channel}: {pred.get('urgency').upper()} - "
                           f"{pred.get('recommended_action')}\n")
        
        logger.info(f"✓ Summary exported to: {summary_file}")
    
    logger.info("")
    logger.info("="*60)
    logger.info("Training complete!")
    logger.info("="*60)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("\nTraining interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.exception(f"Training failed: {e}")
        sys.exit(1)
