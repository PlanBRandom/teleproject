"""
Modbus client wrapper for OI-7530/7010 gas monitors.
Supports both RTU (serial) and TCP connections with automatic retry and error handling.
"""
import logging
import struct
import time
from typing import Optional, Union, List, Tuple
from dataclasses import dataclass
from enum import Enum

try:
    from pymodbus.client import ModbusSerialClient, ModbusTcpClient
    from pymodbus.exceptions import ModbusException
    from pymodbus.pdu import ExceptionResponse
except ImportError:
    ModbusSerialClient = None
    ModbusTcpClient = None
    ModbusException = Exception
    ExceptionResponse = None

logger = logging.getLogger(__name__)


class ConnectionType(Enum):
    """Modbus connection type"""
    RTU = "rtu"
    TCP = "tcp"


@dataclass
class ModbusConfig:
    """Modbus connection configuration"""
    connection_type: ConnectionType
    
    # RTU (Serial) settings
    port: Optional[str] = None  # e.g., "COM3", "/dev/ttyUSB0"
    baudrate: int = 9600
    bytesize: int = 8
    parity: str = 'N'
    stopbits: int = 1
    
    # TCP settings
    host: Optional[str] = None
    tcp_port: int = 502
    
    # Common settings
    slave_id: int = 1
    timeout: int = 3
    retries: int = 3
    retry_delay: float = 0.5


class ModbusClient:
    """Unified Modbus client for RTU and TCP connections"""
    
    def __init__(self, config: ModbusConfig):
        self.config = config
        self.client = None
        self._connect()
    
    def _connect(self):
        """Establish modbus connection"""
        if self.config.connection_type == ConnectionType.RTU:
            if not ModbusSerialClient:
                raise ImportError("pymodbus not installed. Run: pip install pymodbus")
            
            logger.info(f"Connecting to Modbus RTU on {self.config.port} @ {self.config.baudrate} baud")
            self.client = ModbusSerialClient(
                port=self.config.port,
                baudrate=self.config.baudrate,
                bytesize=self.config.bytesize,
                parity=self.config.parity,
                stopbits=self.config.stopbits,
                timeout=self.config.timeout,
                retries=self.config.retries
            )
        
        elif self.config.connection_type == ConnectionType.TCP:
            if not ModbusTcpClient:
                raise ImportError("pymodbus not installed. Run: pip install pymodbus")
            
            logger.info(f"Connecting to Modbus TCP at {self.config.host}:{self.config.tcp_port}")
            self.client = ModbusTcpClient(
                host=self.config.host,
                port=self.config.tcp_port,
                timeout=self.config.timeout,
                retries=self.config.retries
            )
        
        else:
            raise ValueError(f"Unknown connection type: {self.config.connection_type}")
        
        # Attempt connection
        if not self.client.connect():
            raise ConnectionError(f"Failed to connect to Modbus device")
        
        logger.info("Modbus connection established")
    
    def reconnect(self) -> bool:
        """Attempt to reconnect to modbus device"""
        try:
            if self.client:
                self.client.close()
            self._connect()
            return True
        except Exception as e:
            logger.error(f"Reconnection failed: {e}")
            return False
    
    def close(self):
        """Close modbus connection"""
        if self.client:
            self.client.close()
            logger.info("Modbus connection closed")
    
    def _retry_operation(self, operation, *args, **kwargs):
        """Execute operation with retry logic"""
        last_exception = None
        
        for attempt in range(self.config.retries):
            try:
                result = operation(*args, **kwargs)
                
                # Check for modbus exceptions
                if isinstance(result, ExceptionResponse):
                    raise ModbusException(f"Modbus exception: {result}")
                
                if hasattr(result, 'isError') and result.isError():
                    raise ModbusException(f"Modbus error response")
                
                return result
                
            except Exception as e:
                last_exception = e
                logger.warning(f"Attempt {attempt + 1}/{self.config.retries} failed: {e}")
                
                if attempt < self.config.retries - 1:
                    time.sleep(self.config.retry_delay)
                    
                    # Try reconnecting on last retry
                    if attempt == self.config.retries - 2:
                        logger.info("Attempting reconnection...")
                        self.reconnect()
        
        raise last_exception
    
    def read_holding_registers(self, address: int, count: int = 1, device_id: Optional[int] = None) -> List[int]:
        """
        Read holding registers (function code 3)
        
        Args:
            address: Starting register address
            count: Number of registers to read
            device_id: Optional slave device ID (defaults to config.slave_id)
            
        Returns:
            List of register values (16-bit unsigned integers)
        """
        result = self.client.read_holding_registers(
            address,
            count=count,
            device_id=device_id or self.config.slave_id
        )
        
        if hasattr(result, 'registers'):
            logger.debug(f"Read {count} registers from address {address}: {result.registers}")
            return result.registers
        
        raise ModbusException("No data in response")
    
    def read_input_registers(self, address: int, count: int = 1) -> List[int]:
        """
        Read input registers (function code 4)
        
        Args:
            address: Starting register address
            count: Number of registers to read
            
        Returns:
            List of register values (16-bit unsigned integers)
        """
        result = self.client.read_input_registers(
            address,
            count=count,
            device_id=self.config.slave_id
        )
        
        if hasattr(result, 'registers'):
            logger.debug(f"Read {count} input registers from address {address}: {result.registers}")
            return result.registers
        
        raise ModbusException("No data in response")
    
    def write_register(self, address: int, value: int) -> bool:
        """
        Write single register (function code 6)
        
        Args:
            address: Register address
            value: Value to write (16-bit unsigned integer)
            
        Returns:
            True if successful
        """
        result = self.client.write_register(
            address,
            value,
            device_id=self.config.slave_id
        )
        
        logger.info(f"Wrote value {value} to register {address}")
        return True
    
    def write_registers(self, address: int, values: List[int]) -> bool:
        """
        Write multiple registers (function code 16)
        
        Args:
            address: Starting register address
            values: List of values to write (16-bit unsigned integers)
            
        Returns:
            True if successful
        """
        result = self.client.write_registers(
            address,
            values,
            device_id=self.config.slave_id
        )
        
        logger.info(f"Wrote {len(values)} values to registers starting at {address}")
        return True
    
    def read_float32(self, address: int, byte_order: str = '>', device_id: Optional[int] = None) -> float:
        """
        Read 32-bit float from two consecutive registers
        
        Args:
            address: Starting register address
            byte_order: '>' for big-endian (default), '<' for little-endian
            device_id: Optional slave device ID (defaults to config.slave_id)
            
        Returns:
            Float value
        """
        registers = self.read_holding_registers(address, count=2, device_id=device_id)
        
        # Combine two 16-bit registers into 32-bit value
        high = registers[0]
        low = registers[1]
        
        # Pack as bytes and unpack as float
        bytes_data = struct.pack(f'{byte_order}HH', high, low)
        value = struct.unpack(f'{byte_order}f', bytes_data)[0]
        
        logger.debug(f"Read float32 from address {address}: {value}")
        return value
    
    def read_uint32(self, address: int, byte_order: str = '>', device_id: Optional[int] = None) -> int:
        """
        Read 32-bit unsigned integer from two consecutive registers
        
        Args:
            address: Starting register address
            byte_order: '>' for big-endian (default), '<' for little-endian
            device_id: Optional slave device ID (defaults to config.slave_id)
            
        Returns:
            Integer value
        """
        registers = self.read_holding_registers(address, count=2, device_id=device_id)
        
        high = registers[0]
        low = registers[1]
        
        if byte_order == '>':
            value = (high << 16) | low
        else:
            value = (low << 16) | high
        
        logger.debug(f"Read uint32 from address {address}: {value}")
        return value
    
    def write_float32(self, address: int, value: float, byte_order: str = '>') -> bool:
        """
        Write 32-bit float to two consecutive registers
        
        Args:
            address: Starting register address
            value: Float value to write
            byte_order: '>' for big-endian (default), '<' for little-endian
            
        Returns:
            True if successful
        """
        # Pack float as bytes and unpack as two 16-bit values
        bytes_data = struct.pack(f'{byte_order}f', value)
        high, low = struct.unpack(f'{byte_order}HH', bytes_data)
        
        return self.write_registers(address, [high, low])
    
    def read_register_value(self, address: int, data_type: str, byte_order: str = '>') -> Union[int, float]:
        """
        Read register value with automatic type handling
        
        Args:
            address: Register address
            data_type: 'uint16', 'uint32', 'float32', etc.
            byte_order: Byte order for multi-register reads
            
        Returns:
            Register value with appropriate type
        """
        if data_type == 'uint16':
            return self.read_holding_registers(address, count=1)[0]
        elif data_type == 'uint32':
            return self.read_uint32(address, byte_order)
        elif data_type == 'float32':
            return self.read_float32(address, byte_order)
        else:
            raise ValueError(f"Unsupported data type: {data_type}")
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()


if __name__ == "__main__":
    # Test the modbus client
    logging.basicConfig(level=logging.DEBUG)
    
    # Example RTU configuration
    config = ModbusConfig(
        connection_type=ConnectionType.RTU,
        port="COM3",  # Change to your port
        baudrate=9600,
        slave_id=1
    )
    
    try:
        with ModbusClient(config) as client:
            # Read first sensor reading (address 0x21 = 33)
            print("\nReading Channel 1 sensor value...")
            value = client.read_float32(33)
            print(f"Channel 1: {value}")
            
    except Exception as e:
        logger.error(f"Test failed: {e}")
