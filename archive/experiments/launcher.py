"""
OI-7500 Pipeline Control Center
Main GUI launcher for all monitoring, diagnostic, and utility tools
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import subprocess
import threading
import queue
import json
import os
from pathlib import Path

class OI7500ControlCenter:
    def __init__(self, root):
        self.root = root
        self.root.title("OI-7500 Pipeline Control Center")
        self.root.geometry("1200x800")
        
        # Process tracking
        self.processes = {}
        self.output_queues = {}
        
        # Configuration
        self.config_file = Path("config.json")
        self.load_config()
        
        # Create UI
        self.create_menu()
        self.create_main_layout()
        
        # Update status periodically
        self.update_status()
        
    def load_config(self):
        """Load configuration from file"""
        if self.config_file.exists():
            with open(self.config_file, 'r') as f:
                self.config = json.load(f)
        else:
            # Default configuration
            self.config = {
                'mqtt': {
                    'broker': 'a1bcc059f5f74a6d8271e8b567fecc6d.s1.eu.hivemq.cloud',
                    'port': 8883,
                    'username': 'laird',
                    'password': 'LairdRM024',
                    'use_tls': True
                },
                'monitoring': {
                    'duration_hours': 1.0,
                    'networks': ['Network_15', 'Network_20', 'Network_25'],
                    'model': 'OI-7530'
                },
                'radios': {
                    'Network_15': {'port': 'COM7', 'baudrate': 115200},
                    'Network_20': {'port': 'COM12', 'baudrate': 115200},
                    'Network_25': {'port': 'COM11', 'baudrate': 115200}
                },
                'modbus': {
                    'port': 'COM10',
                    'baudrate': 9600,
                    'slaves': {
                        'Network_15': 30,
                        'Network_20': 10,
                        'Network_25': 32
                    }
                }
            }
            self.save_config()
    
    def save_config(self):
        """Save configuration to file"""
        with open(self.config_file, 'w') as f:
            json.dump(self.config, indent=2, fp=f)
    
    def create_menu(self):
        """Create menu bar"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Settings", command=self.open_settings)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)
        
        # Tools menu
        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Tools", menu=tools_menu)
        tools_menu.add_command(label="Web GUI", command=self.open_web_gui)
        tools_menu.add_command(label="Channel Generator", command=self.open_channel_generator)
        
        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self.show_about)
        help_menu.add_command(label="Documentation", command=self.show_docs)
    
    def create_main_layout(self):
        """Create main application layout"""
        # Create notebook (tabs)
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Create tabs
        self.create_monitoring_tab()
        self.create_diagnostics_tab()
        self.create_database_tab()
        self.create_system_tab()
    
    def create_monitoring_tab(self):
        """Create monitoring control tab"""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="📡 Monitoring")
        
        # Configuration frame
        config_frame = ttk.LabelFrame(frame, text="Configuration", padding=10)
        config_frame.pack(fill='x', padx=10, pady=5)
        
        # Row 0: Model selection
        ttk.Label(config_frame, text="Model:", font=('', 9, 'bold')).grid(row=0, column=0, sticky='w', padx=5, pady=5)
        self.model_var = tk.StringVar(value=self.config['monitoring'].get('model', 'OI-7530'))
        model_combo = ttk.Combobox(config_frame, textvariable=self.model_var, width=15, state='readonly',
                                   values=['OI-7010', 'OI-7530', 'OI-7032'])
        model_combo.grid(row=0, column=1, padx=5, pady=5, sticky='w')
        ttk.Label(config_frame, text="(Selects appropriate Modbus register map)", 
                 foreground='gray').grid(row=0, column=2, sticky='w', padx=10)
        
        # Row 1: COM Port for Radio
        ttk.Label(config_frame, text="Radio COM Port:", font=('', 9, 'bold')).grid(row=1, column=0, sticky='w', padx=5, pady=5)
        # Get primary network config
        primary_net = self.config['radios'].get('Network_25', {'port': 'COM11', 'baudrate': 115200})
        self.radio_port_var = tk.StringVar(value=primary_net['port'])
        port_combo = ttk.Combobox(config_frame, textvariable=self.radio_port_var, width=15, state='readonly',
                                  values=['COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 
                                         'COM8', 'COM9', 'COM10', 'COM11', 'COM12'])
        port_combo.grid(row=1, column=1, padx=5, pady=5, sticky='w')
        ttk.Label(config_frame, text="@ 115200 baud (SECONDARY/RX-only)", 
                 foreground='gray').grid(row=1, column=2, sticky='w', padx=10)
        
        # Row 2: Radio Network Channel
        ttk.Label(config_frame, text="Radio Network Channel:", font=('', 9, 'bold')).grid(row=2, column=0, sticky='w', padx=5, pady=5)
        self.network_channel_var = tk.StringVar(value='Network_25')
        channel_combo = ttk.Combobox(config_frame, textvariable=self.network_channel_var, width=15, state='readonly',
                                     values=['Network_15', 'Network_20', 'Network_25'])
        channel_combo.grid(row=2, column=1, padx=5, pady=5, sticky='w')
        ttk.Label(config_frame, text="(WireFree radio network to monitor)", 
                 foreground='gray').grid(row=2, column=2, sticky='w', padx=10)
        
        # Row 3: Modbus Slave ID (optional)
        ttk.Label(config_frame, text="Modbus Slave ID:", font=('', 9, 'bold')).grid(row=3, column=0, sticky='w', padx=5, pady=5)
        modbus_slaves = self.config.get('modbus', {}).get('slaves', {})
        self.modbus_slave_var = tk.IntVar(value=modbus_slaves.get('Network_25', 32))
        slave_spin = ttk.Spinbox(config_frame, from_=1, to=255, textvariable=self.modbus_slave_var, width=15)
        slave_spin.grid(row=3, column=1, padx=5, pady=5, sticky='w')
        ttk.Label(config_frame, text="(For Modbus polling - optional)", 
                 foreground='gray').grid(row=3, column=2, sticky='w', padx=10)
        
        # Row 4: Modbus COM Port (optional)
        ttk.Label(config_frame, text="Modbus COM Port:", font=('', 9, 'bold')).grid(row=4, column=0, sticky='w', padx=5, pady=5)
        self.modbus_port_var = tk.StringVar(value=self.config.get('modbus', {}).get('port', 'COM10'))
        modbus_port_combo = ttk.Combobox(config_frame, textvariable=self.modbus_port_var, width=15, state='readonly',
                                         values=['COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 
                                                'COM8', 'COM9', 'COM10', 'COM11', 'COM12'])
        modbus_port_combo.grid(row=4, column=1, padx=5, pady=5, sticky='w')
        ttk.Label(config_frame, text="@ 9600 baud (For Modbus polling)", 
                 foreground='gray').grid(row=4, column=2, sticky='w', padx=10)
        
        # Save button
        ttk.Button(config_frame, text="💾 Save Configuration", 
                  command=self.save_network_config, width=25).grid(row=5, column=0, columnspan=3, pady=15)
        
        # Monitoring controls
        control_frame = ttk.LabelFrame(frame, text="Monitoring Control", padding=10)
        control_frame.pack(fill='x', padx=10, pady=5)
        
        # Duration
        ttk.Label(control_frame, text="Duration (hours):").grid(row=0, column=0, sticky='w', padx=5)
        self.duration_var = tk.DoubleVar(value=self.config['monitoring']['duration_hours'])
        duration_spin = ttk.Spinbox(control_frame, from_=0.1, to=24, increment=0.5, 
                                     textvariable=self.duration_var, width=10)
        duration_spin.grid(row=0, column=1, padx=5)
        
        # MQTT enabled
        self.mqtt_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(control_frame, text="Enable MQTT Publishing", 
                       variable=self.mqtt_var).grid(row=0, column=2, padx=20)
        
        # Modbus enabled
        self.modbus_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(control_frame, text="Enable Modbus Polling", 
                       variable=self.modbus_var).grid(row=0, column=3, padx=5)
        
        # Start/Stop buttons
        btn_frame = ttk.Frame(control_frame)
        btn_frame.grid(row=1, column=0, columnspan=4, pady=10)
        
        self.start_btn = ttk.Button(btn_frame, text="▶ Start Monitoring", 
                                     command=self.start_monitoring, width=20)
        self.start_btn.pack(side='left', padx=5)
        
        self.stop_btn = ttk.Button(btn_frame, text="⏹ Stop Monitoring", 
                                    command=self.stop_monitoring, width=20, state='disabled')
        self.stop_btn.pack(side='left', padx=5)
        
        ttk.Button(btn_frame, text="📊 View MQTT Stream", 
                  command=self.view_mqtt_stream, width=20).pack(side='left', padx=5)
        
        # Status frame
        status_frame = ttk.LabelFrame(frame, text="Status", padding=10)
        status_frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        self.monitoring_status = scrolledtext.ScrolledText(status_frame, height=25, 
                                                            wrap=tk.WORD, bg='black', 
                                                            fg='#00ff00', font=('Consolas', 9))
        self.monitoring_status.pack(fill='both', expand=True)
        self.monitoring_status.insert('1.0', "Ready to start monitoring...\n")
    
    def create_diagnostics_tab(self):
        """Create diagnostics tab"""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="🔧 Diagnostics")
        
        # Radio config check
        radio_frame = ttk.LabelFrame(frame, text="Radio Configuration", padding=10)
        radio_frame.pack(fill='x', padx=10, pady=5)
        
        ttk.Label(radio_frame, text="Verify all monitoring radios are SECONDARY (receive-only)").pack(anchor='w')
        btn_frame1 = ttk.Frame(radio_frame)
        btn_frame1.pack(fill='x', pady=5)
        
        ttk.Button(btn_frame1, text="✓ Verify Radio Config", 
                  command=self.verify_radios, width=25).pack(side='left', padx=5)
        ttk.Button(btn_frame1, text="🔧 Fix Radio to Secondary", 
                  command=self.fix_radio, width=25).pack(side='left', padx=5)
        
        # Packet diagnostics
        packet_frame = ttk.LabelFrame(frame, text="Packet Diagnostics", padding=10)
        packet_frame.pack(fill='x', padx=10, pady=5)
        
        ttk.Label(packet_frame, text="Query packet database for troubleshooting").pack(anchor='w')
        
        query_frame = ttk.Frame(packet_frame)
        query_frame.pack(fill='x', pady=5)
        
        ttk.Button(query_frame, text="🔍 Find F8 Duplicates", 
                  command=lambda: self.run_diagnostic('f8'), width=20).pack(side='left', padx=5)
        ttk.Button(query_frame, text="🔍 Track F14 Timeouts", 
                  command=lambda: self.run_diagnostic('f14'), width=20).pack(side='left', padx=5)
        ttk.Button(query_frame, text="📈 All Faults", 
                  command=lambda: self.run_diagnostic('faults'), width=20).pack(side='left', padx=5)
        
        query_frame2 = ttk.Frame(packet_frame)
        query_frame2.pack(fill='x', pady=5)
        
        ttk.Label(query_frame2, text="Channel:").pack(side='left', padx=5)
        self.channel_var = tk.IntVar(value=16)
        ttk.Spinbox(query_frame2, from_=1, to=255, textvariable=self.channel_var, 
                   width=10).pack(side='left', padx=5)
        ttk.Button(query_frame2, text="View Channel History", 
                  command=self.view_channel_history, width=20).pack(side='left', padx=5)
        
        ttk.Label(query_frame2, text="Network:").pack(side='left', padx=(20,5))
        self.network_var = tk.StringVar(value="Network_25")
        ttk.Combobox(query_frame2, textvariable=self.network_var, 
                    values=['Network_15', 'Network_20', 'Network_25'],
                    width=15).pack(side='left', padx=5)
        ttk.Button(query_frame2, text="Network Diagnostics", 
                  command=self.network_diagnostics, width=20).pack(side='left', padx=5)
        
        # Output
        output_frame = ttk.LabelFrame(frame, text="Diagnostic Output", padding=10)
        output_frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        self.diagnostic_output = scrolledtext.ScrolledText(output_frame, height=20, 
                                                           wrap=tk.WORD, font=('Consolas', 9))
        self.diagnostic_output.pack(fill='both', expand=True)
    
    def create_database_tab(self):
        """Create database tab"""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="💾 Database")
        
        # Database stats
        stats_frame = ttk.LabelFrame(frame, text="Database Statistics", padding=10)
        stats_frame.pack(fill='x', padx=10, pady=5)
        
        self.db_stats_text = tk.Text(stats_frame, height=8, wrap=tk.WORD, font=('Consolas', 10))
        self.db_stats_text.pack(fill='x', pady=5)
        
        ttk.Button(stats_frame, text="🔄 Refresh Statistics", 
                  command=self.refresh_db_stats, width=20).pack(pady=5)
        
        # Export options
        export_frame = ttk.LabelFrame(frame, text="Export Data", padding=10)
        export_frame.pack(fill='x', padx=10, pady=5)
        
        ttk.Label(export_frame, text="Export packet data to CSV for analysis").pack(anchor='w')
        
        exp_frame = ttk.Frame(export_frame)
        exp_frame.pack(fill='x', pady=5)
        
        ttk.Label(exp_frame, text="Hours:").pack(side='left', padx=5)
        self.export_hours_var = tk.IntVar(value=24)
        ttk.Spinbox(exp_frame, from_=1, to=168, textvariable=self.export_hours_var, 
                   width=10).pack(side='left', padx=5)
        ttk.Button(exp_frame, text="📤 Export to CSV", 
                  command=self.export_database, width=20).pack(side='left', padx=20)
        
        # Recent packets
        recent_frame = ttk.LabelFrame(frame, text="Recent Packets", padding=10)
        recent_frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        # Create treeview for recent packets
        columns = ('Time', 'Network', 'Channel', 'Gas', 'Reading', 'Battery', 'Fault')
        self.packet_tree = ttk.Treeview(recent_frame, columns=columns, show='headings', height=15)
        
        for col in columns:
            self.packet_tree.heading(col, text=col)
            self.packet_tree.column(col, width=120 if col == 'Time' else 100)
        
        scrollbar = ttk.Scrollbar(recent_frame, orient='vertical', command=self.packet_tree.yview)
        self.packet_tree.configure(yscrollcommand=scrollbar.set)
        
        self.packet_tree.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        ttk.Button(recent_frame, text="🔄 Refresh", 
                  command=self.refresh_packets).pack(pady=5)
    
    def create_system_tab(self):
        """Create system info tab"""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="⚙️ System")
        
        # System info
        info_frame = ttk.LabelFrame(frame, text="System Information", padding=10)
        info_frame.pack(fill='x', padx=10, pady=5)
        
        self.system_info = tk.Text(info_frame, height=10, wrap=tk.WORD, font=('Consolas', 10))
        self.system_info.pack(fill='x', pady=5)
        self.update_system_info()
        
        # Quick actions
        actions_frame = ttk.LabelFrame(frame, text="Quick Actions", padding=10)
        actions_frame.pack(fill='x', padx=10, pady=5)
        
        btn_grid = ttk.Frame(actions_frame)
        btn_grid.pack(fill='x', pady=5)
        
        ttk.Button(btn_grid, text="🌐 Open Web GUI", 
                  command=self.open_web_gui, width=25).grid(row=0, column=0, padx=5, pady=3)
        ttk.Button(btn_grid, text="📝 View Logs", 
                  command=self.view_logs, width=25).grid(row=0, column=1, padx=5, pady=3)
        ttk.Button(btn_grid, text="📁 Open Log Folder", 
                  command=self.open_log_folder, width=25).grid(row=1, column=0, padx=5, pady=3)
        ttk.Button(btn_grid, text="📊 Generate Channels", 
                  command=self.open_channel_generator, width=25).grid(row=1, column=1, padx=5, pady=3)
        
        # Console output
        console_frame = ttk.LabelFrame(frame, text="Console Output", padding=10)
        console_frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        self.console_output = scrolledtext.ScrolledText(console_frame, height=15, 
                                                        wrap=tk.WORD, font=('Consolas', 9))
        self.console_output.pack(fill='both', expand=True)
    
    # Monitoring methods
    def start_monitoring(self):
        """Start the monitoring process"""
        duration = self.duration_var.get()
        
        cmd = [
            'python', 'monitoring/monitor_multi_network.py',
            str(duration)
        ]
        
        if self.mqtt_var.get():
            cfg = self.config['mqtt']
            cmd.extend([
                '--mqtt-broker', cfg['broker'],
                '--mqtt-port', str(cfg['port']),
                '--mqtt-username', cfg['username'],
                '--mqtt-password', cfg['password']
            ])
            if cfg['use_tls']:
                cmd.append('--mqtt-use-tls')
        
        self.log_monitoring("Starting monitoring...\n")
        self.log_monitoring(f"Command: {' '.join(cmd)}\n\n")
        
        # Start process
        try:
            self.processes['monitor'] = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1
            )
            
            # Create thread to read output
            self.output_queues['monitor'] = queue.Queue()
            threading.Thread(target=self.read_output, 
                           args=(self.processes['monitor'], 'monitor'),
                           daemon=True).start()
            
            self.start_btn.config(state='disabled')
            self.stop_btn.config(state='normal')
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to start monitoring: {e}")
    
    def stop_monitoring(self):
        """Stop the monitoring process"""
        if 'monitor' in self.processes:
            self.processes['monitor'].terminate()
            del self.processes['monitor']
            self.log_monitoring("\n[Monitoring stopped]\n")
            
        self.start_btn.config(state='normal')
        self.stop_btn.config(state='disabled')
    
    def view_mqtt_stream(self):
        """Open MQTT monitor in new window"""
        try:
            subprocess.Popen(['python', 'monitoring/mqtt_monitor.py'])
        except Exception as e:
            messagebox.showerror("Error", f"Failed to start MQTT monitor: {e}")
    
    # Diagnostic methods
    def verify_radios(self):
        """Verify radio configuration"""
        self.diagnostic_output.delete('1.0', tk.END)
        self.diagnostic_output.insert('1.0', "Verifying radio configuration...\n\n")
        
        try:
            result = subprocess.run(
                ['python', 'diagnostics/verify_radio_config.py'],
                capture_output=True,
                text=True,
                timeout=30
            )
            self.diagnostic_output.insert(tk.END, result.stdout)
            if result.stderr:
                self.diagnostic_output.insert(tk.END, f"\nErrors:\n{result.stderr}")
        except Exception as e:
            self.diagnostic_output.insert(tk.END, f"\nError: {e}")
    
    def fix_radio(self):
        """Fix radio to secondary mode"""
        port = tk.simpledialog.askstring("Fix Radio", "Enter COM port (e.g., COM7):")
        if not port:
            return
        
        self.diagnostic_output.delete('1.0', tk.END)
        self.diagnostic_output.insert('1.0', f"Fixing radio on {port}...\n\n")
        
        try:
            result = subprocess.run(
                ['python', 'diagnostics/fix_radio_secondary.py', port],
                capture_output=True,
                text=True,
                timeout=30
            )
            self.diagnostic_output.insert(tk.END, result.stdout)
            if result.stderr:
                self.diagnostic_output.insert(tk.END, f"\nErrors:\n{result.stderr}")
        except Exception as e:
            self.diagnostic_output.insert(tk.END, f"\nError: {e}")
    
    def run_diagnostic(self, diagnostic_type):
        """Run packet diagnostic query"""
        self.diagnostic_output.delete('1.0', tk.END)
        self.diagnostic_output.insert('1.0', f"Running {diagnostic_type} diagnostic...\n\n")
        
        cmd = ['python', 'diagnostics/packet_diagnostics.py', f'--{diagnostic_type}']
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            self.diagnostic_output.insert(tk.END, result.stdout)
            if result.stderr:
                self.diagnostic_output.insert(tk.END, f"\nErrors:\n{result.stderr}")
        except Exception as e:
            self.diagnostic_output.insert(tk.END, f"\nError: {e}")
    
    def view_channel_history(self):
        """View history for specific channel"""
        channel = self.channel_var.get()
        self.diagnostic_output.delete('1.0', tk.END)
        self.diagnostic_output.insert('1.0', f"Channel {channel} history...\n\n")
        
        cmd = ['python', 'diagnostics/packet_diagnostics.py', '--channel', str(channel), '--limit', '50']
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            self.diagnostic_output.insert(tk.END, result.stdout)
        except Exception as e:
            self.diagnostic_output.insert(tk.END, f"\nError: {e}")
    
    def network_diagnostics(self):
        """View network diagnostics"""
        network = self.network_var.get()
        self.diagnostic_output.delete('1.0', tk.END)
        self.diagnostic_output.insert('1.0', f"{network} diagnostics...\n\n")
        
        cmd = ['python', 'diagnostics/packet_diagnostics.py', '--network', network, '--hours', '1']
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            self.diagnostic_output.insert(tk.END, result.stdout)
        except Exception as e:
            self.diagnostic_output.insert(tk.END, f"\nError: {e}")
    
    # Database methods
    def refresh_db_stats(self):
        """Refresh database statistics"""
        try:
            from database.packet_database import PacketDatabase
            db = PacketDatabase()
            
            # Get stats
            stats = db.get_network_diagnostics()
            
            self.db_stats_text.delete('1.0', tk.END)
            self.db_stats_text.insert('1.0', "Database Statistics:\n")
            self.db_stats_text.insert(tk.END, "="*60 + "\n\n")
            
            if stats:
                for stat in stats:
                    self.db_stats_text.insert(tk.END, f"Network: {stat['network']}\n")
                    self.db_stats_text.insert(tk.END, f"  Total Packets: {stat['total_packets']}\n")
                    self.db_stats_text.insert(tk.END, f"  Unique Channels: {stat['unique_channels']}\n")
                    self.db_stats_text.insert(tk.END, f"  Faults: {stat['fault_count']}\n")
                    self.db_stats_text.insert(tk.END, f"  Avg RSSI: {stat.get('avg_rssi', 'N/A')}\n\n")
            else:
                self.db_stats_text.insert(tk.END, "No data in database yet.\n")
                
        except Exception as e:
            self.db_stats_text.delete('1.0', tk.END)
            self.db_stats_text.insert('1.0', f"Error: {e}\n")
    
    def refresh_packets(self):
        """Refresh recent packets display"""
        try:
            from database.packet_database import PacketDatabase
            db = PacketDatabase()
            
            # Clear existing items
            for item in self.packet_tree.get_children():
                self.packet_tree.delete(item)
            
            # Get recent packets
            packets = db.get_recent_packets(limit=100)
            
            for packet in packets:
                self.packet_tree.insert('', 'end', values=(
                    packet['timestamp'][:19],
                    packet['network'],
                    packet['channel'],
                    packet.get('gas_name', 'N/A'),
                    f"{packet.get('reading', 0):.2f}",
                    f"{packet.get('battery_voltage', 0):.1f}V",
                    packet.get('fault_name', 'None')
                ))
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to refresh packets: {e}")
    
    def export_database(self):
        """Export database to CSV"""
        hours = self.export_hours_var.get()
        filename = tk.filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        
        if not filename:
            return
        
        try:
            cmd = ['python', 'diagnostics/packet_diagnostics.py', 
                   '--export', filename, '--hours', str(hours)]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                messagebox.showinfo("Success", f"Exported to {filename}")
            else:
                messagebox.showerror("Error", f"Export failed:\n{result.stderr}")
        except Exception as e:
            messagebox.showerror("Error", f"Export failed: {e}")
    
    # System methods
    def save_network_config(self):
        """Save network configuration"""
        try:
            # Update model
            self.config['monitoring']['model'] = self.model_var.get()
            
            # Update primary network (the one being monitored)
            network = self.network_channel_var.get()
            
            # Update radio config for selected network
            self.config['radios'][network] = {
                'port': self.radio_port_var.get(),
                'baudrate': 115200  # Always 115200 for SECONDARY radios
            }
            
            # Update modbus config
            if 'modbus' not in self.config:
                self.config['modbus'] = {'slaves': {}}
            if 'slaves' not in self.config['modbus']:
                self.config['modbus']['slaves'] = {}
            
            self.config['modbus']['port'] = self.modbus_port_var.get()
            self.config['modbus']['baudrate'] = 9600  # Standard Modbus baud rate
            self.config['modbus']['slaves'][network] = self.modbus_slave_var.get()
            
            # Save to file
            self.save_config()
            
            # Update system info display
            self.update_system_info()
            
            messagebox.showinfo("Success", 
                f"Configuration saved!\n\n"
                f"Model: {self.model_var.get()}\n"
                f"Radio: {self.radio_port_var.get()} @ 115200 baud\n"
                f"Network: {network}\n"
                f"Modbus: {self.modbus_port_var.get()} @ 9600 (Slave {self.modbus_slave_var.get()})")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save configuration: {e}")
    
    def update_system_info(self):
        """Update system information display"""
        self.system_info.delete('1.0', tk.END)
        
        # Get current config
        model = self.config['monitoring'].get('model', 'OI-7530')
        
        # Get network being monitored (default to Network_25)
        network = self.config['monitoring'].get('active_network', 'Network_25')
        radio_cfg = self.config['radios'].get(network, {'port': 'COM11', 'baudrate': 115200})
        
        modbus_cfg = self.config.get('modbus', {})
        modbus_port = modbus_cfg.get('port', 'COM10')
        modbus_slave = modbus_cfg.get('slaves', {}).get(network, 32)
        
        info = f"""OI-7500 Pipeline Control Center
{"="*60}

Version: 1.0
Model: {model}
Database: protocol_logs/packets.db

Active Configuration:
  Radio Network: {network}
  Radio Port: {radio_cfg['port']} @ {radio_cfg['baudrate']} baud (SECONDARY/RX)
  
  Modbus Port: {modbus_port} @ 9600 baud
  Modbus Slave ID: {modbus_slave}

MQTT Broker: {self.config['mqtt']['broker']}
Port: {self.config['mqtt']['port']}

Status: Ready
"""
        self.system_info.insert('1.0', info)
    
    def open_web_gui(self):
        """Open web GUI"""
        try:
            subprocess.Popen(['python', 'gui/web_gui/app.py'])
            messagebox.showinfo("Web GUI", "Web GUI starting on http://localhost:5000")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to start web GUI: {e}")
    
    def open_channel_generator(self):
        """Open channel generator"""
        try:
            subprocess.Popen(['python', 'utils/generate_channels.py'])
        except Exception as e:
            messagebox.showerror("Error", f"Failed to start channel generator: {e}")
    
    def view_logs(self):
        """View recent logs"""
        try:
            log_dir = Path("protocol_logs")
            logs = sorted(log_dir.glob("*.log"), key=lambda p: p.stat().st_mtime, reverse=True)
            
            if logs:
                # Open most recent log
                subprocess.Popen(['notepad.exe', str(logs[0])])
            else:
                messagebox.showinfo("Logs", "No log files found")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open logs: {e}")
    
    def open_log_folder(self):
        """Open log folder in explorer"""
        try:
            os.startfile('protocol_logs')
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open folder: {e}")
    
    def open_settings(self):
        """Open settings dialog"""
        # Create settings window
        settings_win = tk.Toplevel(self.root)
        settings_win.title("Settings")
        settings_win.geometry("600x500")
        
        # Create notebook for settings categories
        notebook = ttk.Notebook(settings_win)
        notebook.pack(fill='both', expand=True, padx=10, pady=10)
        
        # MQTT Settings Tab
        mqtt_frame = ttk.Frame(notebook)
        notebook.add(mqtt_frame, text="MQTT")
        
        ttk.Label(mqtt_frame, text="Broker:").grid(row=0, column=0, sticky='w', padx=10, pady=5)
        mqtt_broker_var = tk.StringVar(value=self.config['mqtt']['broker'])
        ttk.Entry(mqtt_frame, textvariable=mqtt_broker_var, width=40).grid(row=0, column=1, padx=10, pady=5)
        
        ttk.Label(mqtt_frame, text="Port:").grid(row=1, column=0, sticky='w', padx=10, pady=5)
        mqtt_port_var = tk.IntVar(value=self.config['mqtt']['port'])
        ttk.Spinbox(mqtt_frame, from_=1, to=65535, textvariable=mqtt_port_var, width=10).grid(row=1, column=1, sticky='w', padx=10, pady=5)
        
        ttk.Label(mqtt_frame, text="Username:").grid(row=2, column=0, sticky='w', padx=10, pady=5)
        mqtt_user_var = tk.StringVar(value=self.config['mqtt']['username'])
        ttk.Entry(mqtt_frame, textvariable=mqtt_user_var, width=40).grid(row=2, column=1, padx=10, pady=5)
        
        ttk.Label(mqtt_frame, text="Password:").grid(row=3, column=0, sticky='w', padx=10, pady=5)
        mqtt_pass_var = tk.StringVar(value=self.config['mqtt']['password'])
        ttk.Entry(mqtt_frame, textvariable=mqtt_pass_var, width=40, show='*').grid(row=3, column=1, padx=10, pady=5)
        
        mqtt_tls_var = tk.BooleanVar(value=self.config['mqtt']['use_tls'])
        ttk.Checkbutton(mqtt_frame, text="Use TLS/SSL", variable=mqtt_tls_var).grid(row=4, column=0, columnspan=2, sticky='w', padx=10, pady=5)
        
        # Modbus Settings Tab
        modbus_frame = ttk.Frame(notebook)
        notebook.add(modbus_frame, text="Modbus")
        
        ttk.Label(modbus_frame, text="Serial Port:").grid(row=0, column=0, sticky='w', padx=10, pady=5)
        modbus_port_var = tk.StringVar(value=self.config.get('modbus', {}).get('port', 'COM10'))
        ttk.Combobox(modbus_frame, textvariable=modbus_port_var, width=15,
                    values=['COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 
                           'COM8', 'COM9', 'COM10', 'COM11', 'COM12']).grid(row=0, column=1, sticky='w', padx=10, pady=5)
        
        ttk.Label(modbus_frame, text="Baud Rate:").grid(row=1, column=0, sticky='w', padx=10, pady=5)
        modbus_baud_var = tk.IntVar(value=self.config.get('modbus', {}).get('baudrate', 9600))
        ttk.Combobox(modbus_frame, textvariable=modbus_baud_var, width=15,
                    values=[9600, 19200, 38400, 57600, 115200]).grid(row=1, column=1, sticky='w', padx=10, pady=5)
        
        # Save/Cancel buttons
        btn_frame = ttk.Frame(settings_win)
        btn_frame.pack(fill='x', padx=10, pady=10)
        
        def save_settings():
            self.config['mqtt']['broker'] = mqtt_broker_var.get()
            self.config['mqtt']['port'] = mqtt_port_var.get()
            self.config['mqtt']['username'] = mqtt_user_var.get()
            self.config['mqtt']['password'] = mqtt_pass_var.get()
            self.config['mqtt']['use_tls'] = mqtt_tls_var.get()
            
            if 'modbus' not in self.config:
                self.config['modbus'] = {}
            self.config['modbus']['port'] = modbus_port_var.get()
            self.config['modbus']['baudrate'] = modbus_baud_var.get()
            
            self.save_config()
            self.update_system_info()
            messagebox.showinfo("Success", "Settings saved successfully!")
            settings_win.destroy()
        
        ttk.Button(btn_frame, text="💾 Save", command=save_settings, width=15).pack(side='right', padx=5)
        ttk.Button(btn_frame, text="✖ Cancel", command=settings_win.destroy, width=15).pack(side='right', padx=5)
    
    def show_about(self):
        """Show about dialog"""
        messagebox.showinfo("About", 
            "OI-7500 Pipeline Control Center\n\n"
            "Version 1.0\n\n"
            "Complete monitoring and diagnostic system for\n"
            "Oldham OI-7500 gas detection with WireFree radios.\n\n"
            "Features:\n"
            "• Multi-network monitoring\n"
            "• MQTT publishing\n"
            "• Packet database\n"
            "• F8/F14 diagnostics\n"
            "• Radio configuration")
    
    def show_docs(self):
        """Show documentation"""
        messagebox.showinfo("Documentation", 
            "Quick Start:\n\n"
            "1. Verify radios are SECONDARY (Diagnostics tab)\n"
            "2. Configure MQTT settings (File → Settings)\n"
            "3. Start monitoring (Monitoring tab)\n"
            "4. View data via MQTT or Database tab\n\n"
            "For F8/F14 troubleshooting, use Diagnostics tab.")
    
    # Helper methods
    def read_output(self, process, name):
        """Read process output in thread"""
        try:
            for line in iter(process.stdout.readline, ''):
                if line:
                    self.output_queues[name].put(line)
        except Exception:
            pass
    
    def log_monitoring(self, text):
        """Log to monitoring status"""
        self.monitoring_status.insert(tk.END, text)
        self.monitoring_status.see(tk.END)
    
    def update_status(self):
        """Update status displays from queues"""
        # Update monitoring output
        if 'monitor' in self.output_queues:
            try:
                while True:
                    line = self.output_queues['monitor'].get_nowait()
                    self.log_monitoring(line)
            except queue.Empty:
                pass
        
        # Schedule next update
        self.root.after(100, self.update_status)

def main():
    root = tk.Tk()
    app = OI7500ControlCenter(root)
    root.mainloop()

if __name__ == '__main__':
    main()
