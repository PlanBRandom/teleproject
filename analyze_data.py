#!/usr/bin/env python3
"""
Data Analysis Tool for OI-7500 Pipeline
Analyzes collected radio and Modbus data to generate reports and insights
"""
import json
import csv
import sys
from pathlib import Path
from datetime import datetime
from collections import defaultdict, Counter
from typing import Dict, List, Any
import re


class DataAnalyzer:
    """Analyze collected monitoring data"""
    
    def __init__(self, base_path: Path = None):
        self.base_path = base_path or Path(__file__).parent
        self.radio_logs = self.base_path / "radio_logs"
        self.protocol_logs = self.base_path / "protocol_logs"
        self.logs = self.base_path / "logs"
        self.exports = self.base_path / "exports"
        self.exports.mkdir(exist_ok=True)
        
    def print_header(self, title: str):
        """Print formatted header"""
        print("\n" + "=" * 80)
        print(f"  {title}")
        print("=" * 80)
    
    def analyze_radio_data(self):
        """Analyze radio packet data"""
        self.print_header("RADIO DATA ANALYSIS")
        
        # Load stats
        stats_file = self.protocol_logs / "stats.json"
        if not stats_file.exists():
            print("❌ No stats.json found")
            return {}
        
        with open(stats_file) as f:
            stats = json.load(f)
        
        radio_stats = stats.get("radio", {})
        
        print(f"\n📡 Radio Traffic Summary:")
        print(f"  Total Packets:  {radio_stats.get('total_packets', 0):,}")
        print(f"  Total Bytes:    {radio_stats.get('total_bytes', 0):,} ({radio_stats.get('total_bytes', 0)/1024:.2f} KB)")
        
        print(f"\n📊 Frame Types:")
        for frame_type, count in radio_stats.get("frame_types", {}).items():
            percentage = (count / radio_stats.get('total_packets', 1)) * 100
            print(f"  {frame_type:25s}: {count:4d} ({percentage:5.2f}%)")
        
        print(f"\n🔢 Protocol Types:")
        for proto_type, count in radio_stats.get("protocol_types", {}).items():
            print(f"  {proto_type:15s}: {count:4d}")
        
        return radio_stats
    
    def analyze_csv_data(self):
        """Analyze CSV log files"""
        self.print_header("CSV DATA ANALYSIS")
        
        csv_files = list(self.radio_logs.glob("*.csv"))
        if not csv_files:
            print("❌ No CSV files found")
            return
        
        print(f"\nFound {len(csv_files)} CSV file(s)")
        
        for csv_file in csv_files:
            print(f"\n📄 {csv_file.name}")
            
            try:
                with open(csv_file, 'r') as f:
                    reader = csv.DictReader(f)
                    rows = list(reader)
                    
                    if not rows:
                        print("  Empty file")
                        continue
                    
                    print(f"  Rows: {len(rows)}")
                    print(f"  Columns: {', '.join(rows[0].keys())}")
                    
                    # Analyze by network if available
                    if 'network_id' in rows[0]:
                        networks = Counter(row['network_id'] for row in rows)
                        print(f"  Networks:")
                        for net_id, count in networks.most_common():
                            print(f"    Network {net_id}: {count} packets")
                    
                    # Analyze by sensor if available
                    if 'sensor_id' in rows[0]:
                        sensors = Counter(row['sensor_id'] for row in rows)
                        print(f"  Sensors: {len(sensors)} unique")
                        for sensor_id, count in sensors.most_common(5):
                            print(f"    Sensor {sensor_id}: {count} readings")
                    
            except Exception as e:
                print(f"  ❌ Error reading file: {e}")
    
    def extract_gas_readings(self):
        """Extract gas sensor readings from logs"""
        self.print_header("GAS SENSOR READINGS EXTRACTION")
        
        csv_files = list(self.radio_logs.glob("*_data.csv"))
        if not csv_files:
            print("❌ No data CSV files found")
            return
        
        all_readings = []
        
        for csv_file in csv_files:
            try:
                with open(csv_file, 'r') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        all_readings.append(row)
            except Exception as e:
                print(f"❌ Error reading {csv_file.name}: {e}")
        
        if not all_readings:
            print("❌ No readings found")
            return
        
        print(f"\n✓ Found {len(all_readings)} gas readings")
        
        # Export to consolidated CSV
        export_file = self.exports / f"gas_readings_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        if all_readings:
            with open(export_file, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=all_readings[0].keys())
                writer.writeheader()
                writer.writerows(all_readings)
            
            print(f"✓ Exported to: {export_file}")
            
            # Show summary
            if 'gas_reading' in all_readings[0]:
                readings = [float(r['gas_reading']) for r in all_readings if r.get('gas_reading')]
                if readings:
                    print(f"\nGas Reading Statistics:")
                    print(f"  Count:   {len(readings)}")
                    print(f"  Min:     {min(readings):.2f}")
                    print(f"  Max:     {max(readings):.2f}")
                    print(f"  Average: {sum(readings)/len(readings):.2f}")
    
    def analyze_network_logs(self):
        """Analyze network-specific logs"""
        self.print_header("NETWORK ANALYSIS")
        
        network_logs = list(self.protocol_logs.glob("Network_*.log"))
        if not network_logs:
            print("❌ No network logs found")
            return
        
        print(f"\nFound {len(network_logs)} network log file(s)")
        
        networks = defaultdict(lambda: {"size": 0, "lines": 0})
        
        for log_file in network_logs:
            # Extract network ID from filename
            match = re.search(r'Network_(\d+)', log_file.name)
            if match:
                net_id = match.group(1)
                networks[net_id]["size"] += log_file.stat().st_size
                
                try:
                    with open(log_file) as f:
                        networks[net_id]["lines"] += sum(1 for _ in f)
                except:
                    pass
        
        print(f"\n📊 Network Statistics:")
        for net_id in sorted(networks.keys()):
            info = networks[net_id]
            print(f"  Network {net_id}:")
            print(f"    Log entries: {info['lines']}")
            print(f"    Data size:   {info['size']/1024:.2f} KB")
    
    def generate_summary_report(self):
        """Generate comprehensive summary report"""
        self.print_header("GENERATING SUMMARY REPORT")
        
        report_file = self.exports / f"monitoring_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        
        with open(report_file, 'w') as f:
            f.write("=" * 80 + "\n")
            f.write("OI-7500 MONITORING RUN - SUMMARY REPORT\n")
            f.write("=" * 80 + "\n\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            # Stats
            stats_file = self.protocol_logs / "stats.json"
            if stats_file.exists():
                with open(stats_file) as sf:
                    stats = json.load(sf)
                
                f.write("RADIO DATA:\n")
                f.write(f"  Total Packets: {stats['radio'].get('total_packets', 0):,}\n")
                f.write(f"  Total Bytes:   {stats['radio'].get('total_bytes', 0):,}\n")
                f.write(f"  Frame Types:   {len(stats['radio'].get('frame_types', {}))}\n")
                f.write(f"  Protocols:     {len(stats['radio'].get('protocol_types', {}))}\n\n")
                
                f.write("MODBUS DATA:\n")
                f.write(f"  Requests:  {stats['modbus'].get('total_requests', 0)}\n")
                f.write(f"  Responses: {stats['modbus'].get('total_responses', 0)}\n\n")
            
            # File counts
            f.write("FILE COUNTS:\n")
            f.write(f"  Radio logs:    {len(list(self.radio_logs.glob('*')))}\n")
            f.write(f"  Protocol logs: {len(list(self.protocol_logs.glob('*')))}\n")
            f.write(f"  General logs:  {len(list(self.logs.glob('*.log')))}\n\n")
            
            f.write("=" * 80 + "\n")
        
        print(f"✓ Report saved to: {report_file}")
        return report_file
    
    def list_available_data(self):
        """List all available data files"""
        self.print_header("AVAILABLE DATA FILES")
        
        print("\n📁 Radio Logs:")
        for f in sorted(self.radio_logs.glob("*"))[:10]:
            print(f"  {f.name} ({f.stat().st_size/1024:.2f} KB)")
        
        print("\n📁 Protocol Logs (showing recent):")
        for f in sorted(self.protocol_logs.glob("*"), key=lambda x: x.stat().st_mtime, reverse=True)[:10]:
            print(f"  {f.name} ({f.stat().st_size/1024:.2f} KB)")
        
        print("\n📁 General Logs (showing recent):")
        for f in sorted(self.logs.glob("*.log"), key=lambda x: x.stat().st_mtime, reverse=True)[:10]:
            print(f"  {f.name} ({f.stat().st_size/1024:.2f} KB)")
    
    def run_full_analysis(self):
        """Run complete analysis"""
        print("\n")
        print("╔═══════════════════════════════════════════════════════════════════════════╗")
        print("║              OI-7500 DATA ANALYSIS TOOL                                   ║")
        print("╚═══════════════════════════════════════════════════════════════════════════╝")
        
        # Run all analyses
        self.analyze_radio_data()
        self.analyze_csv_data()
        self.extract_gas_readings()
        self.analyze_network_logs()
        self.list_available_data()
        report = self.generate_summary_report()
        
        # Final summary
        self.print_header("ANALYSIS COMPLETE")
        print("\n✅ Data analysis finished!")
        print(f"\n📊 Exports saved to: {self.exports}")
        print(f"📄 Summary report: {report.name}")
        print("\n💡 What you can do with this data:")
        print("  • Import gas_readings_*.csv into Excel/Google Sheets")
        print("  • Analyze trends and patterns")
        print("  • Create graphs and visualizations")
        print("  • Share with team or clients")
        print("  • Archive for compliance/records")
        print()


def main():
    """Main entry point"""
    analyzer = DataAnalyzer()
    analyzer.run_full_analysis()


if __name__ == "__main__":
    main()
