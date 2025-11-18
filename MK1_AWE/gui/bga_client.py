"""BGA (Binary Gas Analyzer) HTTP command client"""

import requests

try:
    from .config_loader import get_bga_ports
except ImportError:
    from config_loader import get_bga_ports


def set_primary_gas(bga_id, cas, timeout=1):
    """Set primary gas on a BGA device.
    
    Args:
        bga_id: BGA identifier ("BGA01" or "BGA02")
        cas: CAS number of gas (e.g., "1333-74-0" for H2)
        timeout: HTTP timeout in seconds (default 1)
        
    Raises:
        ValueError: If bga_id is invalid
        ConnectionError: If HTTP bridge is unreachable
        IOError: If command fails
    """
    ports = get_bga_ports()
    if bga_id not in ports:
        raise ValueError(f"Invalid BGA ID: {bga_id}. Must be BGA01, BGA02, or BGA03")
    
    port = ports[bga_id]
    url = f"http://localhost:{port}/command"
    command = f"GASP {cas}"
    
    try:
        requests.post(url, data=command, timeout=timeout)
    except requests.exceptions.ConnectionError:
        raise ConnectionError(f"Failed to connect to {bga_id} bridge at port {port}")
    except requests.exceptions.Timeout:
        raise ConnectionError(f"Timeout connecting to {bga_id} bridge at port {port}")


def set_secondary_gas(bga_id, cas, timeout=1):
    """Set secondary gas on a BGA device.
    
    Args:
        bga_id: BGA identifier ("BGA01" or "BGA02")
        cas: CAS number of gas (e.g., "7782-44-7" for O2)
        timeout: HTTP timeout in seconds (default 1)
        
    Raises:
        ValueError: If bga_id is invalid
        ConnectionError: If HTTP bridge is unreachable
        IOError: If command fails
    """
    ports = get_bga_ports()
    if bga_id not in ports:
        raise ValueError(f"Invalid BGA ID: {bga_id}. Must be BGA01, BGA02, or BGA03")
    
    port = ports[bga_id]
    url = f"http://localhost:{port}/command"
    command = f"GASS {cas}"
    
    try:
        requests.post(url, data=command, timeout=timeout)
    except requests.exceptions.ConnectionError:
        raise ConnectionError(f"Failed to connect to {bga_id} bridge at port {port}")
    except requests.exceptions.Timeout:
        raise ConnectionError(f"Timeout connecting to {bga_id} bridge at port {port}")


def is_bridge_available(port, timeout=0.5):
    """Check if a BGA HTTP bridge is available and has valid data.
    
    Args:
        port: HTTP port number (8888 or 8889)
        timeout: HTTP timeout in seconds (default 0.5)
        
    Returns:
        bool: True if bridge has valid data (status 200), False otherwise
    """
    try:
        response = requests.get(f"http://localhost:{port}/metrics", timeout=timeout)
        return response.status_code == 200
    except requests.exceptions.RequestException:
        return False

