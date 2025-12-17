"""
Control commands and diagnostics for OI-7032/7530/7010 monitors
"""
from dataclasses import dataclass
from typing import Optional
from pipeline.modbus_client import ModbusClient
from pipeline.registers import RegisterAddresses

@dataclass
class DeviceInfo:
    """Device information"""
    modbus_address: int
    baud_rate: int
    date_month: int
    date_day: int
    date_year: int
    serial_number: int
    radio_timeout: int
    network_channel: int
    is_primary: bool
    relay3_as_fault: bool
    relay1_failsafe: bool
    relay2_failsafe: bool
    relay3_failsafe: bool
    fault_terminal_failsafe: bool

@dataclass
class DiagnosticsInfo:
    """Diagnostics and uptime information"""
    serial_rx_good: int
    serial_rx_error: int
    serial_tx_good: int
    serial_tx_error: int
    radio_rx_good: int
    radio_rx_error: int
    radio_tx_good: int
    radio_tx_error: int
    uptime_days: int
    uptime_hours: int
    uptime_minutes: int
    
    @property
    def uptime_string(self) -> str:
        """Format uptime as string"""
        return f"{self.uptime_days}d {self.uptime_hours}h {self.uptime_minutes}m"
    
    @property
    def serial_error_rate(self) -> float:
        """Calculate serial error rate"""
        total = self.serial_rx_good + self.serial_rx_error
        if total == 0:
            return 0.0
        return (self.serial_rx_error / total) * 100
    
    @property
    def radio_error_rate(self) -> float:
        """Calculate radio error rate"""
        total = self.radio_rx_good + self.radio_rx_error
        if total == 0:
            return 0.0
        return (self.radio_rx_error / total) * 100

@dataclass
class RelayStatus:
    """Relay alarm status"""
    relay1_in_alarm: bool
    relay2_in_alarm: bool
    relay3_in_alarm: bool

class DeviceControl:
    """Control commands for OI monitors"""
    
    def __init__(self, client: ModbusClient):
        self.client = client
    
    # ===== Device Control Commands =====
    
    def reset_device(self, device_id: Optional[int] = None) -> bool:
        """
        Reset/reboot the device
        
        Args:
            device_id: Optional slave device ID
            
        Returns:
            True if command was sent successfully
        """
        try:
            self.client.client.write_register(
                RegisterAddresses.RESET,
                1,
                device_id=device_id or self.client.config.slave_id
            )
            return True
        except Exception as e:
            print(f"Reset failed: {e}")
            return False
    
    def factory_reset(self, device_id: Optional[int] = None) -> bool:
        """
        Restore device to factory defaults
        
        Args:
            device_id: Optional slave device ID
            
        Returns:
            True if command was sent successfully
        """
        try:
            self.client.client.write_register(
                RegisterAddresses.RESTORE_FACTORY_DEFAULT,
                1,
                device_id=device_id or self.client.config.slave_id
            )
            return True
        except Exception as e:
            print(f"Factory reset failed: {e}")
            return False
    
    # ===== Startup Menu Settings (R/W) =====
    
    def set_network_channel(self, channel: int, device_id: Optional[int] = None) -> bool:
        """
        Set radio network channel (1-78)
        
        Args:
            channel: Network channel (1-78)
            device_id: Optional slave device ID
            
        Returns:
            True if successful
        """
        if not 1 <= channel <= 78:
            print("Network channel must be between 1 and 78")
            return False
        
        try:
            self.client.client.write_register(
                RegisterAddresses.NETWORK_CHANNEL,
                channel,
                device_id=device_id or self.client.config.slave_id
            )
            return True
        except Exception as e:
            print(f"Failed to set network channel: {e}")
            return False
    
    def set_primary_secondary(self, is_primary: bool, device_id: Optional[int] = None) -> bool:
        """
        Set device as primary or secondary monitor
        
        Args:
            is_primary: True for primary, False for secondary
            device_id: Optional slave device ID
            
        Returns:
            True if successful
        """
        try:
            value = 0 if is_primary else 1
            self.client.client.write_register(
                RegisterAddresses.PRIMARY_SECONDARY,
                value,
                device_id=device_id or self.client.config.slave_id
            )
            return True
        except Exception as e:
            print(f"Failed to set primary/secondary: {e}")
            return False
    
    def set_radio_timeout(self, timeout_minutes: int, device_id: Optional[int] = None) -> bool:
        """
        Set radio timeout in minutes (6-255)
        
        Args:
            timeout_minutes: Timeout in minutes (6-255)
            device_id: Optional slave device ID
            
        Returns:
            True if successful
        """
        if not 6 <= timeout_minutes <= 255:
            print("Radio timeout must be between 6 and 255 minutes")
            return False
        
        try:
            self.client.client.write_register(
                RegisterAddresses.RADIO_TIMEOUT,
                timeout_minutes,
                device_id=device_id or self.client.config.slave_id
            )
            return True
        except Exception as e:
            print(f"Failed to set radio timeout: {e}")
            return False
    
    def set_relay3_as_fault(self, enabled: bool, device_id: Optional[int] = None) -> bool:
        """
        Configure Relay 3 as fault relay
        
        Args:
            enabled: True to enable as fault relay, False for normal relay
            device_id: Optional slave device ID
            
        Returns:
            True if successful
        """
        try:
            value = 1 if enabled else 0
            self.client.client.write_register(
                RegisterAddresses.RELAY3_AS_FAULT,
                value,
                device_id=device_id or self.client.config.slave_id
            )
            return True
        except Exception as e:
            print(f"Failed to set relay 3 as fault: {e}")
            return False
    
    def set_relay_failsafe(self, relay_num: int, enabled: bool, device_id: Optional[int] = None) -> bool:
        """
        Set relay fail-safe mode
        
        Args:
            relay_num: Relay number (1, 2, or 3)
            enabled: True to enable fail-safe, False to disable
            device_id: Optional slave device ID
            
        Returns:
            True if successful
        """
        if relay_num not in [1, 2, 3]:
            print("Relay number must be 1, 2, or 3")
            return False
        
        register_map = {
            1: RegisterAddresses.RELAY1_FAILSAFE,
            2: RegisterAddresses.RELAY2_FAILSAFE,
            3: RegisterAddresses.RELAY3_FAILSAFE
        }
        
        try:
            value = 1 if enabled else 0
            self.client.client.write_register(
                register_map[relay_num],
                value,
                device_id=device_id or self.client.config.slave_id
            )
            return True
        except Exception as e:
            print(f"Failed to set relay {relay_num} fail-safe: {e}")
            return False
    
    # ===== Channel Control =====
    
    def set_channel_mode(self, channel: int, mode: int, device_id: Optional[int] = None) -> bool:
        """
        Set channel operating mode
        
        Args:
            channel: Channel number (1-32)
            mode: Mode code (0=Off, 1=Normal, 2=Inhibit, 3=Maintenance, 4=Calibration, 5=Null)
            device_id: Optional slave device ID
            
        Returns:
            True if successful
        """
        if not 1 <= channel <= 32:
            print("Channel must be between 1 and 32")
            return False
        
        if not 0 <= mode <= 7:
            print("Mode must be between 0 and 7")
            return False
        
        try:
            mode_reg = 0x61 + (channel - 1)
            self.client.client.write_register(
                mode_reg,
                mode,
                device_id=device_id or self.client.config.slave_id
            )
            return True
        except Exception as e:
            print(f"Failed to set channel {channel} mode: {e}")
            return False
    
    def turn_channel_on(self, channel: int, device_id: Optional[int] = None) -> bool:
        """Turn channel on (set to Normal mode)"""
        return self.set_channel_mode(channel, 1, device_id)
    
    def turn_channel_off(self, channel: int, device_id: Optional[int] = None) -> bool:
        """Turn channel off (set to Off mode)"""
        return self.set_channel_mode(channel, 0, device_id)
    
    def set_channel_inhibit(self, channel: int, device_id: Optional[int] = None) -> bool:
        """Set channel to Inhibit mode (sensor active but alarms disabled)"""
        return self.set_channel_mode(channel, 2, device_id)
    
    # ===== Relay Setpoint Control =====
    
    def set_relay_setpoint(self, channel: int, relay_num: int, setpoint: float, 
                          device_id: Optional[int] = None) -> bool:
        """
        Set relay alarm setpoint for a channel
        
        Args:
            channel: Channel number (1-32)
            relay_num: Relay number (1, 2, or 3)
            setpoint: Setpoint value (0-65000)
            device_id: Optional slave device ID
            
        Returns:
            True if successful
        """
        if not 1 <= channel <= 32:
            print("Channel must be between 1 and 32")
            return False
        
        if relay_num not in [1, 2, 3]:
            print("Relay number must be 1, 2, or 3")
            return False
        
        if not 0 <= setpoint <= 65000:
            print("Setpoint must be between 0 and 65000")
            return False
        
        base_registers = {
            1: 0x1A1,  # Relay 1 setpoint base
            2: 0x221,  # Relay 2 setpoint base  
            3: 0x2A1   # Relay 3 setpoint base
        }
        
        try:
            setpoint_reg = base_registers[relay_num] + (channel - 1) * 2
            
            # Convert float to two 16-bit registers (Float32)
            import struct
            bytes_data = struct.pack('>f', setpoint)
            high, low = struct.unpack('>HH', bytes_data)
            
            self.client.client.write_registers(
                setpoint_reg,
                [high, low],
                device_id=device_id or self.client.config.slave_id
            )
            return True
        except Exception as e:
            print(f"Failed to set relay {relay_num} setpoint for channel {channel}: {e}")
            return False
    
    def enable_relay(self, channel: int, relay_num: int, enabled: bool,
                    device_id: Optional[int] = None) -> bool:
        """
        Enable or disable a relay for a channel
        
        Args:
            channel: Channel number (1-32)
            relay_num: Relay number (1, 2, or 3)
            enabled: True to enable, False to disable
            device_id: Optional slave device ID
            
        Returns:
            True if successful
        """
        if not 1 <= channel <= 32:
            print("Channel must be between 1 and 32")
            return False
        
        if relay_num not in [1, 2, 3]:
            print("Relay number must be 1, 2, or 3")
            return False
        
        base_registers = {
            1: 0x161,  # Relay 1 enable base (353-384)
            2: 0x201,  # Relay 2 enable base (513-544)
            3: 0x2A1   # Relay 3 enable base (673-704)
        }
        
        try:
            enable_reg = base_registers[relay_num] + (channel - 1)
            value = 1 if enabled else 0
            
            self.client.client.write_register(
                enable_reg,
                value,
                device_id=device_id or self.client.config.slave_id
            )
            return True
        except Exception as e:
            print(f"Failed to enable/disable relay {relay_num} for channel {channel}: {e}")
            return False
    
    # ===== Information Retrieval =====
    
    def get_seconds_since_message(self, channel: int, device_id: Optional[int] = None) -> int:
        """
        Get seconds since last message from a channel's sensor
        
        Args:
            channel: Channel number (1-32)
            device_id: Optional slave device ID
            
        Returns:
            Seconds since last message (-1 = never, 0 = timeout, positive = time)
        """
        if not 1 <= channel <= 32:
            print("Channel must be between 1 and 32")
            return -1
        
        try:
            msg_reg = 0xC1 + (channel - 1)
            result = self.client.read_holding_registers(
                msg_reg,
                1,
                device_id=device_id or self.client.config.slave_id
            )
            if result and len(result.registers) > 0:
                value = result.registers[0]
                # Handle signed 16-bit value
                if value > 32767:
                    value = value - 65536
                return value
            return -1
        except Exception as e:
            print(f"Failed to read seconds since message for channel {channel}: {e}")
            return -1
    
    def get_days_since_null(self, channel: int, device_id: Optional[int] = None) -> int:
        """
        Get days since last null for a channel
        NOTE: Only available on OI-7010/7032, not on OI-7530
        
        Args:
            channel: Channel number (1-32)
            device_id: Optional slave device ID
            
        Returns:
            Days since last null (0-65535, 65535 may indicate never, -1 on error/unsupported)
        """
        if not 1 <= channel <= 32:
            print("Channel must be between 1 and 32")
            return -1
        
        try:
            null_reg = 0x3E1 + (channel - 1)
            result = self.client.read_holding_registers(
                null_reg,
                1,
                device_id=device_id or self.client.config.slave_id
            )
            if result and len(result.registers) > 0:
                return result.registers[0]
            return -1
        except Exception as e:
            print(f"Failed to read days since null for channel {channel}: {e}")
            return -1
    
    def get_days_since_calibration(self, channel: int, device_id: Optional[int] = None) -> int:
        """
        Get days since last calibration for a channel
        NOTE: Only available on OI-7010/7032, not on OI-7530
        
        Args:
            channel: Channel number (1-32)
            device_id: Optional slave device ID
            
        Returns:
            Days since last calibration (0-65535, 65535 may indicate never, -1 on error/unsupported)
        """
        if not 1 <= channel <= 32:
            print("Channel must be between 1 and 32")
            return -1
        
        try:
            cal_reg = 0x401 + (channel - 1)
            result = self.client.read_holding_registers(
                cal_reg,
                1,
                device_id=device_id or self.client.config.slave_id
            )
            if result and len(result.registers) > 0:
                return result.registers[0]
            return -1
        except Exception as e:
            print(f"Failed to read days since calibration for channel {channel}: {e}")
            return -1
    
    def get_device_info(self, device_id: Optional[int] = None) -> DeviceInfo:
        """Read device configuration and info"""
        did = device_id or self.client.config.slave_id
        
        modbus_address = self.client.read_holding_registers(RegisterAddresses.MODBUS_ADDRESS, 1, device_id=did)[0]
        baud_rate = self.client.read_holding_registers(RegisterAddresses.MODBUS_BAUD_RATE, 1, device_id=did)[0]
        date_month = self.client.read_holding_registers(RegisterAddresses.DATE_MONTH, 1, device_id=did)[0]
        date_day = self.client.read_holding_registers(RegisterAddresses.DATE_DAY, 1, device_id=did)[0]
        date_year = self.client.read_holding_registers(RegisterAddresses.DATE_YEAR, 1, device_id=did)[0]
        serial_number = self.client.read_uint32(RegisterAddresses.SERIAL_NUMBER, device_id=did)
        radio_timeout = self.client.read_holding_registers(RegisterAddresses.RADIO_TIMEOUT, 1, device_id=did)[0]
        network_channel = self.client.read_holding_registers(RegisterAddresses.NETWORK_CHANNEL, 1, device_id=did)[0]
        primary_secondary = self.client.read_holding_registers(RegisterAddresses.PRIMARY_SECONDARY, 1, device_id=did)[0]
        relay3_fault = self.client.read_holding_registers(RegisterAddresses.RELAY3_AS_FAULT, 1, device_id=did)[0]
        relay1_fs = self.client.read_holding_registers(RegisterAddresses.RELAY1_FAILSAFE, 1, device_id=did)[0]
        relay2_fs = self.client.read_holding_registers(RegisterAddresses.RELAY2_FAILSAFE, 1, device_id=did)[0]
        relay3_fs = self.client.read_holding_registers(RegisterAddresses.RELAY3_FAILSAFE, 1, device_id=did)[0]
        fault_term_fs = self.client.read_holding_registers(RegisterAddresses.FAULT_TERMINAL_FAILSAFE, 1, device_id=did)[0]
        
        return DeviceInfo(
            modbus_address=modbus_address,
            baud_rate=baud_rate,
            date_month=date_month,
            date_day=date_day,
            date_year=date_year,
            serial_number=serial_number,
            radio_timeout=radio_timeout,
            network_channel=network_channel,
            is_primary=(primary_secondary == 0),
            relay3_as_fault=(relay3_fault == 1),
            relay1_failsafe=(relay1_fs == 1),
            relay2_failsafe=(relay2_fs == 1),
            relay3_failsafe=(relay3_fs == 1),
            fault_terminal_failsafe=(fault_term_fs == 1)
        )
    
    def get_diagnostics(self, device_id: Optional[int] = None) -> DiagnosticsInfo:
        """Read diagnostics and uptime"""
        did = device_id or self.client.config.slave_id
        
        return DiagnosticsInfo(
            serial_rx_good=self.client.read_holding_registers(RegisterAddresses.SERIAL_RX_GOOD, 1, device_id=did)[0],
            serial_rx_error=self.client.read_holding_registers(RegisterAddresses.SERIAL_RX_ERROR, 1, device_id=did)[0],
            serial_tx_good=self.client.read_holding_registers(RegisterAddresses.SERIAL_TX_GOOD, 1, device_id=did)[0],
            serial_tx_error=self.client.read_holding_registers(RegisterAddresses.SERIAL_TX_ERROR, 1, device_id=did)[0],
            radio_rx_good=self.client.read_holding_registers(RegisterAddresses.RADIO_RX_GOOD, 1, device_id=did)[0],
            radio_rx_error=self.client.read_holding_registers(RegisterAddresses.RADIO_RX_ERROR, 1, device_id=did)[0],
            radio_tx_good=self.client.read_holding_registers(RegisterAddresses.RADIO_TX_GOOD, 1, device_id=did)[0],
            radio_tx_error=self.client.read_holding_registers(RegisterAddresses.RADIO_TX_ERROR, 1, device_id=did)[0],
            uptime_days=self.client.read_holding_registers(RegisterAddresses.UPTIME_DAYS, 1, device_id=did)[0],
            uptime_hours=self.client.read_holding_registers(RegisterAddresses.UPTIME_HOURS, 1, device_id=did)[0],
            uptime_minutes=self.client.read_holding_registers(RegisterAddresses.UPTIME_MINUTES, 1, device_id=did)[0]
        )
    
    def get_relay_status(self, device_id: Optional[int] = None) -> RelayStatus:
        """Read relay alarm status"""
        did = device_id or self.client.config.slave_id
        
        relay1 = self.client.read_holding_registers(RegisterAddresses.RELAY1_IN_ALARM, 1, device_id=did)[0]
        relay2 = self.client.read_holding_registers(RegisterAddresses.RELAY2_IN_ALARM, 1, device_id=did)[0]
        relay3 = self.client.read_holding_registers(RegisterAddresses.RELAY3_IN_ALARM, 1, device_id=did)[0]
        
        return RelayStatus(
            relay1_in_alarm=(relay1 == 1),
            relay2_in_alarm=(relay2 == 1),
            relay3_in_alarm=(relay3 == 1)
        )
