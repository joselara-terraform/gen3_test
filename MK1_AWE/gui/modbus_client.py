"""Modbus TCP client for MK1_AWE hardware control"""

from pymodbus.client import ModbusTcpClient


def connect(host, port=502, timeout=1):
    """Connect to a Modbus TCP device.
    
    Args:
        host: IP address of Modbus device
        port: Modbus TCP port (default 502)
        timeout: Connection timeout in seconds (default 1)
        
    Returns:
        ModbusTcpClient: Connected client instance
        
    Raises:
        ConnectionError: If connection fails
    """
    client = ModbusTcpClient(host=host, port=port, timeout=timeout)
    
    if not client.connect():
        raise ConnectionError(f"Failed to connect to Modbus device at {host}:{port}")
    
    return client


def write_coil(host, address, value, port=502, timeout=1):
    """Write a single coil (relay) on a Modbus device.
    
    Args:
        host: IP address of Modbus device
        address: Coil address (0-29 for RL01-RL30)
        value: True for ON, False for OFF
        port: Modbus TCP port (default 502)
        timeout: Connection timeout in seconds (default 1)
        
    Raises:
        ConnectionError: If connection fails
        IOError: If write operation fails
    """
    client = connect(host, port, timeout)
    
    try:
        response = client.write_coil(address, value)
        if response.isError():
            raise IOError(f"Failed to write coil {address} on {host}:{port}")
    finally:
        client.close()


def ping(host, port=502, timeout=0.5):
    """Check if a Modbus device is reachable.
    
    Args:
        host: IP address of Modbus device
        port: Modbus TCP port (default 502)
        timeout: Connection timeout in seconds (default 0.5)
        
    Returns:
        bool: True if device is reachable, False otherwise
    """
    client = None
    try:
        client = ModbusTcpClient(host=host, port=port, timeout=timeout)
        return client.connect()
    except Exception:
        return False
    finally:
        if client:
            client.close()

