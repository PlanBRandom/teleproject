"""
Packet Database - Store raw radio packets for diagnosis
Captures all packets with timestamps, RSSI, network info for F8/F14 troubleshooting
"""

import sqlite3
import json
from datetime import datetime
from pathlib import Path

class PacketDatabase:
    """SQLite database for storing raw radio packets"""
    
    def __init__(self, db_path="protocol_logs/packets.db"):
        """Initialize database connection"""
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.cursor = self.conn.cursor()
        
        # Create tables
        self._create_tables()
    
    def _create_tables(self):
        """Create database tables if they don't exist"""
        
        # Raw packets table
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS raw_packets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                network TEXT NOT NULL,
                raw_hex TEXT NOT NULL,
                length INTEGER NOT NULL,
                frame_type TEXT,
                rssi INTEGER,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Decoded packets table (Protocol 1)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS decoded_packets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                network TEXT NOT NULL,
                channel INTEGER NOT NULL,
                transmitter_address INTEGER NOT NULL,
                protocol INTEGER NOT NULL,
                reading REAL NOT NULL,
                gas_type INTEGER NOT NULL,
                gas_name TEXT NOT NULL,
                battery_voltage REAL,
                battery_reading INTEGER,
                battery_scale INTEGER,
                sensor_mode INTEGER,
                sensor_type INTEGER,
                fault_code INTEGER,
                fault_name TEXT,
                precision INTEGER,
                has_text INTEGER,
                rssi INTEGER,
                raw_packet_id INTEGER,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (raw_packet_id) REFERENCES raw_packets(id)
            )
        """)
        
        # Fault events table (for F8 and F14 tracking)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS fault_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                network TEXT NOT NULL,
                channel INTEGER NOT NULL,
                fault_code INTEGER NOT NULL,
                fault_name TEXT NOT NULL,
                transmitter_address INTEGER,
                first_seen DATETIME DEFAULT CURRENT_TIMESTAMP,
                last_seen DATETIME DEFAULT CURRENT_TIMESTAMP,
                occurrence_count INTEGER DEFAULT 1
            )
        """)
        
        # Network statistics table
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS network_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                network TEXT NOT NULL,
                total_packets INTEGER DEFAULT 0,
                unique_channels INTEGER DEFAULT 0,
                unique_addresses INTEGER DEFAULT 0,
                avg_rssi REAL,
                fault_count INTEGER DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create indexes for faster queries
        self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_decoded_channel ON decoded_packets(channel)")
        self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_decoded_fault ON decoded_packets(fault_code)")
        self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_decoded_address ON decoded_packets(transmitter_address)")
        self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_fault_events_code ON fault_events(fault_code)")
        self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON raw_packets(timestamp)")
        
        self.conn.commit()
    
    def log_raw_packet(self, network, raw_data, frame_type=None, rssi=None):
        """Store raw packet bytes"""
        timestamp = datetime.now().isoformat()
        raw_hex = raw_data.hex()
        length = len(raw_data)
        
        self.cursor.execute("""
            INSERT INTO raw_packets (timestamp, network, raw_hex, length, frame_type, rssi)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (timestamp, network, raw_hex, length, frame_type, rssi))
        
        self.conn.commit()
        return self.cursor.lastrowid
    
    def log_decoded_packet(self, network, decoded_data, raw_packet_id=None, rssi=None):
        """Store decoded packet data"""
        timestamp = datetime.now().isoformat()
        
        self.cursor.execute("""
            INSERT INTO decoded_packets (
                timestamp, network, channel, transmitter_address, protocol,
                reading, gas_type, gas_name, battery_voltage, battery_reading,
                battery_scale, sensor_mode, sensor_type, fault_code, fault_name,
                precision, has_text, rssi, raw_packet_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            timestamp, network, 
            decoded_data.get('channel'),
            decoded_data.get('transmitter_address'),
            decoded_data.get('protocol'),
            decoded_data.get('reading'),
            decoded_data.get('gas_type'),
            decoded_data.get('gas_name'),
            decoded_data.get('battery_voltage'),
            decoded_data.get('battery_reading'),
            decoded_data.get('battery_scale'),
            decoded_data.get('sensor_mode'),
            decoded_data.get('sensor_type'),
            decoded_data.get('fault_code'),
            decoded_data.get('fault_name'),
            decoded_data.get('precision'),
            decoded_data.get('has_text'),
            rssi,
            raw_packet_id
        ))
        
        self.conn.commit()
        
        # Track fault events
        if decoded_data.get('fault_code', 0) != 0:
            self._track_fault_event(network, decoded_data)
    
    def _track_fault_event(self, network, decoded_data):
        """Track fault occurrences (especially F8 and F14)"""
        timestamp = datetime.now().isoformat()
        channel = decoded_data.get('channel')
        fault_code = decoded_data.get('fault_code')
        fault_name = decoded_data.get('fault_name')
        address = decoded_data.get('transmitter_address')
        
        # Check if fault already exists for this channel
        self.cursor.execute("""
            SELECT id, occurrence_count FROM fault_events
            WHERE network = ? AND channel = ? AND fault_code = ?
            AND datetime(last_seen) > datetime('now', '-1 hour')
        """, (network, channel, fault_code))
        
        existing = self.cursor.fetchone()
        
        if existing:
            # Update existing fault
            self.cursor.execute("""
                UPDATE fault_events
                SET last_seen = ?, occurrence_count = occurrence_count + 1
                WHERE id = ?
            """, (timestamp, existing[0]))
        else:
            # New fault event
            self.cursor.execute("""
                INSERT INTO fault_events (
                    timestamp, network, channel, fault_code, fault_name, transmitter_address
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (timestamp, network, channel, fault_code, fault_name, address))
        
        self.conn.commit()
    
    def get_fault_history(self, fault_code=None, hours=24):
        """Get fault event history"""
        query = """
            SELECT timestamp, network, channel, fault_code, fault_name,
                   transmitter_address, first_seen, last_seen, occurrence_count
            FROM fault_events
            WHERE datetime(last_seen) > datetime('now', '-{} hours')
        """.format(hours)
        
        if fault_code is not None:
            query += f" AND fault_code = {fault_code}"
        
        query += " ORDER BY last_seen DESC"
        
        self.cursor.execute(query)
        return self.cursor.fetchall()
    
    def get_packets_by_channel(self, channel, limit=100):
        """Get all packets for a specific channel"""
        self.cursor.execute("""
            SELECT timestamp, network, reading, gas_name, battery_voltage,
                   fault_code, fault_name, transmitter_address, rssi
            FROM decoded_packets
            WHERE channel = ?
            ORDER BY timestamp DESC
            LIMIT ?
        """, (channel, limit))
        return self.cursor.fetchall()
    
    def get_duplicate_addresses(self):
        """Find F8 duplicate address conflicts"""
        self.cursor.execute("""
            SELECT transmitter_address, COUNT(DISTINCT channel) as channel_count,
                   GROUP_CONCAT(DISTINCT channel) as channels,
                   MAX(timestamp) as last_seen
            FROM decoded_packets
            WHERE datetime(timestamp) > datetime('now', '-1 hour')
            GROUP BY transmitter_address
            HAVING channel_count > 1
            ORDER BY channel_count DESC
        """)
        return self.cursor.fetchall()
    
    def get_network_diagnostics(self, network, hours=1):
        """Get diagnostic info for a network"""
        self.cursor.execute("""
            SELECT 
                COUNT(*) as total_packets,
                COUNT(DISTINCT channel) as unique_channels,
                COUNT(DISTINCT transmitter_address) as unique_addresses,
                AVG(rssi) as avg_rssi,
                SUM(CASE WHEN fault_code != 0 THEN 1 ELSE 0 END) as fault_count,
                MIN(timestamp) as first_packet,
                MAX(timestamp) as last_packet
            FROM decoded_packets
            WHERE network = ? AND datetime(timestamp) > datetime('now', '-{} hours')
        """.format(hours), (network,))
        return self.cursor.fetchone()
    
    def get_recent_raw_packets(self, network=None, limit=50):
        """Get recent raw packet hex for manual analysis"""
        query = """
            SELECT timestamp, network, raw_hex, length, frame_type, rssi
            FROM raw_packets
        """
        
        params = []
        if network:
            query += " WHERE network = ?"
            params.append(network)
        
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        
        self.cursor.execute(query, params)
        return self.cursor.fetchall()
    
    def export_packets_csv(self, filename, hours=24):
        """Export decoded packets to CSV for analysis"""
        import csv
        
        self.cursor.execute("""
            SELECT timestamp, network, channel, transmitter_address, reading,
                   gas_name, battery_voltage, fault_code, fault_name, rssi
            FROM decoded_packets
            WHERE datetime(timestamp) > datetime('now', '-{} hours')
            ORDER BY timestamp
        """.format(hours))
        
        rows = self.cursor.fetchall()
        
        with open(filename, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['Timestamp', 'Network', 'Channel', 'Address', 'Reading',
                           'Gas Type', 'Battery', 'Fault Code', 'Fault', 'RSSI'])
            writer.writerows(rows)
        
        return len(rows)
    
    def close(self):
        """Close database connection"""
        self.conn.close()
