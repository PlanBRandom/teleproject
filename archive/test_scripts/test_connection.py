"""
CLI tool for testing modbus connection and reading registers
"""
import argparse
import logging
from pipeline.register import RegisterMapParser
from pipeline.modbus_client import ModbusClient, ModbusConfig, ConnectionType

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description='Test Modbus connection to OI-7530/7010')
    
    # Connection args
    parser.add_argument('-t', '--type', choices=['rtu', 'tcp'], default='rtu',
                        help='Connection type')
    parser.add_argument('-p', '--port', default='COM3',
                        help='Serial port (for RTU)')
    parser.add_argument('-H', '--host', default='192.168.1.100',
                        help='Host address (for TCP)')
    parser.add_argument('-b', '--baudrate', type=int, default=9600,
                        help='Baudrate (for RTU)')
    parser.add_argument('-s', '--slave-id', type=int, default=1,
                        help='Modbus slave ID')
    
    # Test options
    parser.add_argument('-r', '--register', type=str,
                        help='Test specific register address (hex or decimal)')
    parser.add_argument('-c', '--count', type=int, default=1,
                        help='Number of registers to read')
    parser.add_argument('--scan', action='store_true',
                        help='Scan all readable registers from map')
    parser.add_argument('--map', default='register_maps/7500-RegMap.csv',
                        help='Register map CSV file')
    
    args = parser.parse_args()
    
    # Create modbus config
    conn_type = ConnectionType.RTU if args.type == 'rtu' else ConnectionType.TCP
    config = ModbusConfig(
        connection_type=conn_type,
        port=args.port,
        host=args.host,
        baudrate=args.baudrate,
        slave_id=args.slave_id
    )
    
    logger.info(f"Connecting to {'RTU' if args.type == 'rtu' else 'TCP'}...")
    
    try:
        client = ModbusClient(config)
        logger.info("✓ Connected successfully")
        
        if args.scan:
            # Scan all registers from map
            logger.info(f"Loading register map: {args.map}")
            reg_parser = RegisterMapParser(args.map)
            readable = reg_parser.get_readable_registers()
            
            logger.info(f"Scanning {len(readable)} registers...")
            print("\n" + "="*80)
            print(f"{'Address':<10} {'Description':<40} {'Value':<20}")
            print("="*80)
            
            success_count = 0
            for reg in readable[:20]:  # Limit to first 20 for quick test
                try:
                    value = client.read_register_value(reg.address_decimal, reg.data_type)
                    print(f"{reg.address_hex:<10} {reg.description:<40} {value:<20}")
                    success_count += 1
                except Exception as e:
                    print(f"{reg.address_hex:<10} {reg.description:<40} ERROR: {e}")
            
            print("="*80)
            logger.info(f"Successfully read {success_count}/{len(readable[:20])} registers")
        
        elif args.register:
            # Test specific register
            try:
                addr = int(args.register, 16) if args.register.startswith('0x') else int(args.register)
            except ValueError:
                logger.error(f"Invalid register address: {args.register}")
                return 1
            
            logger.info(f"Reading register 0x{addr:04x} ({addr})...")
            
            if args.count == 1:
                value = client.read_holding_registers(addr, 1)[0]
                print(f"\nRegister 0x{addr:04x}: {value} (0x{value:04x})")
            elif args.count == 2:
                # Try reading as float32
                value_float = client.read_float32(addr)
                value_uint = client.read_uint32(addr)
                print(f"\nRegister 0x{addr:04x}-0x{addr+1:04x}:")
                print(f"  As float32: {value_float}")
                print(f"  As uint32:  {value_uint}")
            else:
                values = client.read_holding_registers(addr, args.count)
                print(f"\nRegisters 0x{addr:04x}-0x{addr+args.count-1:04x}:")
                for i, val in enumerate(values):
                    print(f"  0x{addr+i:04x}: {val} (0x{val:04x})")
        
        else:
            # Default test - read first sensor channel
            logger.info("Reading Channel 1 sensor value (address 0x21)...")
            value = client.read_float32(0x21)
            print(f"\nChannel 1 Reading: {value} PPM")
        
        client.close()
        logger.info("✓ Test complete")
        return 0
        
    except Exception as e:
        logger.error(f"✗ Test failed: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
