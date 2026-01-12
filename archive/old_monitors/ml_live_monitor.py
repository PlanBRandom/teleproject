#!/usr/bin/env python3
"""
Real-time ML monitoring for gas sensors

Monitors live sensor data and applies ML models for:
- Real-time anomaly detection
- Predictive alerts
- Performance tracking

Usage:
    python ml_live_monitor.py --config config.yaml
    python ml_live_monitor.py --mqtt-broker localhost --alert-webhook https://hooks.slack.com/...
"""

import argparse
import asyncio
import logging
import signal
import sys
from datetime import datetime
from pathlib import Path
import json

from pipeline.ml_analytics import MLAnalyticsPipeline
from pipeline.modbus_client import ModbusClientFactory
from pipeline.register import RegisterMapParser
import yaml

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MLLiveMonitor:
    """Real-time ML-powered monitoring system"""
    
    def __init__(self, config: dict, ml_config: dict):
        self.config = config
        self.ml_config = ml_config
        self.ml_pipeline = MLAnalyticsPipeline(config=ml_config)
        self.running = False
        self.stats = {
            'readings_processed': 0,
            'anomalies_detected': 0,
            'start_time': None
        }
        
    async def initialize(self):
        """Initialize Modbus client and register map"""
        logger.info("Initializing Modbus connection...")
        
        # Load register map
        register_map_path = self.config.get('register_map', 'register_maps/7500-RegMap.csv')
        self.register_parser = RegisterMapParser(register_map_path)
        self.registers = self.register_parser.parse()
        
        # Create Modbus client
        modbus_config = self.config.get('modbus', {})
        self.modbus_client = ModbusClientFactory.create_client(modbus_config)
        self.modbus_client.connect()
        
        logger.info("✓ Modbus connected")
        
    async def process_sensor_reading(self, channel: int, value: float):
        """Process a single sensor reading through ML pipeline"""
        result = self.ml_pipeline.process_reading(channel, value)
        
        self.stats['readings_processed'] += 1
        
        # Check for anomaly
        if result['anomaly']['is_anomaly']:
            self.stats['anomalies_detected'] += 1
            await self.handle_anomaly(result)
            
        return result
        
    async def handle_anomaly(self, result: dict):
        """Handle detected anomaly"""
        channel = result['channel']
        value = result['value']
        anomaly = result['anomaly']
        
        logger.warning(f"🚨 ANOMALY DETECTED - Channel {channel}")
        logger.warning(f"   Value: {value:.2f}")
        logger.warning(f"   Score: {anomaly['score']:.2f}")
        logger.warning(f"   Reason: {anomaly['reason']}")
        
        # TODO: Send alerts via webhook, MQTT, etc.
        
    async def monitor_loop(self):
        """Main monitoring loop"""
        logger.info("Starting ML monitoring loop...")
        self.running = True
        self.stats['start_time'] = datetime.now()
        
        poll_interval = self.config.get('poll_interval', 5.0)
        batch_size = self.ml_config.get('batch_save_interval', 100)
        
        try:
            while self.running:
                try:
                    # Read sensor channels
                    channels_to_monitor = self.config.get('channels', list(range(1, 33)))
                    
                    for channel in channels_to_monitor:
                        # Read channel value (adjust register address based on your map)
                        # This is a simplified example - adjust to your register layout
                        try:
                            # Example: reading from holding registers
                            # You'll need to adjust based on your actual register map
                            register_addr = 0x20 + (channel - 1) * 2  # Example addressing
                            response = self.modbus_client.client.read_holding_registers(
                                register_addr, 2, unit=self.config['modbus']['slave_id']
                            )
                            
                            if not response.isError():
                                # Convert registers to float (adjust based on your encoding)
                                value = float(response.registers[0])  # Simplified
                                
                                # Process through ML
                                await self.process_sensor_reading(channel, value)
                            
                        except Exception as e:
                            logger.debug(f"Could not read channel {channel}: {e}")
                            continue
                    
                    # Periodically save batch
                    if self.stats['readings_processed'] % batch_size == 0:
                        self.ml_pipeline.collector.save_batch()
                        logger.info(f"Batch saved. Total readings: {self.stats['readings_processed']}")
                    
                    # Display stats periodically
                    if self.stats['readings_processed'] % 100 == 0:
                        self.print_stats()
                    
                    await asyncio.sleep(poll_interval)
                    
                except Exception as e:
                    logger.error(f"Error in monitoring loop: {e}")
                    await asyncio.sleep(poll_interval)
                    
        except asyncio.CancelledError:
            logger.info("Monitor loop cancelled")
            
    def print_stats(self):
        """Print monitoring statistics"""
        runtime = datetime.now() - self.stats['start_time']
        logger.info("")
        logger.info("=" * 60)
        logger.info("MONITORING STATISTICS")
        logger.info("=" * 60)
        logger.info(f"Runtime: {runtime}")
        logger.info(f"Readings processed: {self.stats['readings_processed']:,}")
        logger.info(f"Anomalies detected: {self.stats['anomalies_detected']}")
        anomaly_rate = (self.stats['anomalies_detected'] / self.stats['readings_processed'] * 100) \
                      if self.stats['readings_processed'] > 0 else 0
        logger.info(f"Anomaly rate: {anomaly_rate:.2f}%")
        logger.info("=" * 60)
        logger.info("")
        
    async def shutdown(self):
        """Graceful shutdown"""
        logger.info("Shutting down ML monitor...")
        self.running = False
        
        # Save final batch
        self.ml_pipeline.collector.save_batch()
        
        # Disconnect Modbus
        if hasattr(self, 'modbus_client'):
            self.modbus_client.disconnect()
            
        # Print final stats
        self.print_stats()
        
        logger.info("✓ Shutdown complete")


async def main():
    parser = argparse.ArgumentParser(description='Real-time ML monitoring for gas sensors')
    parser.add_argument('--config', '-c', type=str, default='config.yaml',
                       help='Path to configuration file (default: config.yaml)')
    parser.add_argument('--ml-storage', type=str, default='ml_data',
                       help='Path to ML data storage (default: ml_data)')
    parser.add_argument('--anomaly-sensitivity', type=float, default=3.0,
                       help='Anomaly detection sensitivity (default: 3.0)')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose logging')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Load configuration
    config_path = Path(args.config)
    if not config_path.exists():
        logger.error(f"Configuration file not found: {args.config}")
        sys.exit(1)
    
    with open(config_path) as f:
        config = yaml.safe_load(f)
    
    # ML configuration
    ml_config = {
        'storage_path': args.ml_storage,
        'anomaly_sensitivity': args.anomaly_sensitivity,
        'anomaly_window': 100,
        'batch_save_interval': 100
    }
    
    # Create monitor
    monitor = MLLiveMonitor(config, ml_config)
    
    # Setup signal handlers
    loop = asyncio.get_event_loop()
    
    def signal_handler():
        logger.info("Received shutdown signal")
        asyncio.create_task(monitor.shutdown())
    
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, signal_handler)
    
    try:
        # Initialize
        await monitor.initialize()
        
        # Start monitoring
        await monitor.monitor_loop()
        
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.exception(f"Monitor failed: {e}")
    finally:
        await monitor.shutdown()


if __name__ == "__main__":
    if sys.platform == 'win32':
        # Windows doesn't support add_signal_handler, use simpler approach
        asyncio.run(main())
    else:
        asyncio.run(main())
