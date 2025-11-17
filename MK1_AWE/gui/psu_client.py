"""PSU control client with dual backend support (Gen2/MK1)"""

import struct
import os
import csv
from concurrent.futures import ThreadPoolExecutor, as_completed
from pymodbus.client import ModbusTcpClient

try:
    from .config_loader import get_psu_config, load_config, get_psu_ips
except ImportError:
    from config_loader import get_psu_config, load_config, get_psu_ips


def set_current(amps, voltage=None):
    """Set output current (mode-aware).
    
    Args:
        amps: Current in amperes
        voltage: Voltage in volts (Gen3/MK1 only, optional)
        
    Raises:
        ValueError: If current out of range
        ConnectionError: If device unreachable
    """
    psu_config = get_psu_config()
    mode = psu_config['mode']
    
    if mode == 'gen3':
        # Gen3: Use HTTP-based PSU client
        try:
            from .psu_rtu_client import set_voltage_current
        except ImportError:
            from psu_rtu_client import set_voltage_current
        
        # Default voltage if not provided
        if voltage is None:
            voltage = 300.0  # Default voltage for gen3
        
        set_voltage_current(voltage, amps)
    elif mode == 'gen2':
        _set_current_gen2(amps)
    elif mode == 'mk1':
        _set_current_mk1(amps, voltage)
    else:
        raise ValueError(f"Unknown PSU mode: {mode}")


def stop():
    """Stop PSU output (set to safe state: 0A/0V).
    
    Raises:
        ConnectionError: If device unreachable
    """
    psu_config = get_psu_config()
    mode = psu_config['mode']
    
    if mode == 'gen3':
        # Gen3: Use safe_shutdown
        try:
            from .psu_rtu_client import safe_shutdown
        except ImportError:
            from psu_rtu_client import safe_shutdown
        safe_shutdown()
    elif mode == 'gen2':
        set_current(0.0)
    elif mode == 'mk1':
        # MK1: Disable outputs, then set 0V/0A
        _enable_output_mk1(False)
        _set_voltage_mk1(0.0)
        _set_current_mk1(0.0, voltage=0.0)
    else:
        set_current(0.0)


def get_max_current():
    """Get maximum allowed current from config.
    
    Returns:
        float: Maximum current in amperes
    """
    psu_config = get_psu_config()
    mode = psu_config['mode']
    return psu_config[mode]['current_max']


def get_ramp_config():
    """Get ramp configuration from config.
    
    Returns:
        tuple: (steps, step_duration) for discrete ramp
    """
    psu_config = get_psu_config()
    mode = psu_config['mode']
    steps = psu_config[mode].get('ramp_steps', 15)
    step_duration = psu_config[mode].get('ramp_step_duration', 2)
    return steps, step_duration


def load_profile(profile_path=None):
    """Load and validate current profile from CSV.
    
    Args:
        profile_path: Optional path to profile CSV. If None, uses path from config.
        
    Returns:
        list: List of (time_seconds, current_amps) tuples
        
    Raises:
        FileNotFoundError: If profile file doesn't exist
        ValueError: If profile format invalid or validation fails
    """
    # Get profile path from config if not provided
    if profile_path is None:
        psu_config = get_psu_config()
        mode = psu_config['mode']
        profile_path = psu_config[mode].get('profile_path')
        if not profile_path:
            raise ValueError(f"No profile_path configured for mode '{mode}'")
    
    # Resolve path relative to MK1_AWE directory
    if not os.path.isabs(profile_path):
        # Get MK1_AWE directory (parent of gui/)
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        profile_path = os.path.join(base_dir, profile_path)
    
    # Check file exists
    if not os.path.exists(profile_path):
        raise FileNotFoundError(f"Profile file not found: {profile_path}")
    
    # Read CSV
    profile_data = []
    try:
        with open(profile_path, 'r') as f:
            reader = csv.reader(f)
            for row_num, row in enumerate(reader, 1):
                if len(row) != 2:
                    raise ValueError(f"Row {row_num} has {len(row)} columns, expected 2")
                try:
                    time_sec = float(row[0])
                    current_amp = float(row[1])
                    profile_data.append((time_sec, current_amp))
                except ValueError:
                    raise ValueError(f"Row {row_num} contains non-numeric values: {row}")
    except Exception as e:
        if isinstance(e, ValueError):
            raise
        raise ValueError(f"Failed to read profile CSV: {e}")
    
    if not profile_data:
        raise ValueError("Profile is empty")
    
    # Validate times are non-negative and monotonically increasing
    prev_time = -1
    for i, (time_sec, current_amp) in enumerate(profile_data, 1):
        if time_sec < 0:
            raise ValueError(f"Row {i}: Negative time value {time_sec}")
        if time_sec <= prev_time:
            raise ValueError(f"Row {i}: Time {time_sec}s not greater than previous {prev_time}s")
        prev_time = time_sec
    
    # Validate currents are in range
    max_current = get_max_current()
    for i, (time_sec, current_amp) in enumerate(profile_data, 1):
        if current_amp < 0:
            raise ValueError(f"Row {i}: Negative current {current_amp}A")
        if current_amp > max_current:
            raise ValueError(f"Row {i}: Current {current_amp}A exceeds max {max_current}A")
    
    return profile_data


def _set_current_gen2(amps):
    """Gen2 implementation: Set current via LabJack DAC1 (0-5V output)."""
    psu_config = get_psu_config()
    gen2_config = psu_config['gen2']
    
    # Validate range
    current_min = gen2_config['current_min']
    current_max = gen2_config['current_max']
    if not (current_min <= amps <= current_max):
        raise ValueError(f"Current {amps}A out of range ({current_min}-{current_max}A)")
    
    # Convert current to voltage (linear mapping: 0-200A → 0-5V)
    voltage_min = gen2_config['voltage_min']
    voltage_max = gen2_config['voltage_max']
    voltage = (amps / current_max) * voltage_max
    
    # Clamp to voltage range
    voltage = max(voltage_min, min(voltage_max, voltage))
    
    # Get LabJack connection info
    config = load_config()
    device_ref = gen2_config['device']
    lbjk_device = config['devices'][device_ref]
    host = lbjk_device['ip']
    port = lbjk_device['port']
    register = gen2_config['dac_register']
    
    # Connect and write float as 2 registers (FLOAT32_BE)
    client = None
    try:
        client = ModbusTcpClient(host=host, port=port, timeout=1)
        if not client.connect():
            raise ConnectionError(f"Failed to connect to LabJack at {host}:{port}")
        
        # Pack float to bytes, then to 2x 16-bit registers (big-endian)
        bytes_data = struct.pack('>f', voltage)
        regs = [
            struct.unpack('>H', bytes_data[0:2])[0],
            struct.unpack('>H', bytes_data[2:4])[0]
        ]
        
        # Write registers
        response = client.write_registers(register, regs)
        if response.isError():
            raise IOError(f"Failed to write to LabJack register {register}")
        
        print(f"Gen2: Set current to {amps}A ({gen2_config['dac_channel']} output: {voltage:.2f}V)")
        
    finally:
        if client:
            client.close()


def _set_voltage_mk1(volts):
    """MK1: Set voltage on all PSUs."""
    psu_config = get_psu_config()
    mk1_config = psu_config['mk1']
    
    # Apply minimum threshold: <100V → 0V
    if volts > 0 and volts < mk1_config['voltage_min']:
        volts = 0.0
    
    # Validate range
    if volts < 0 or volts > mk1_config['voltage_max']:
        raise ValueError(f"Voltage {volts}V out of range (0-{mk1_config['voltage_max']}V)")
    
    # Get register info
    reg_addr = mk1_config['psu_registers']['write']['set_voltage']['address']
    reg_value = int(volts / 0.1)  # Convert to register value
    
    # Write to all PSUs in parallel
    psu_ips = get_psu_ips()
    successes = 0
    failures = 0
    
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(_write_psu_register, ip, reg_addr, reg_value): ip for ip in psu_ips}
        
        for future in as_completed(futures):
            ip = futures[future]
            try:
                if future.result():
                    successes += 1
                else:
                    failures += 1
            except Exception:
                failures += 1
    
    if successes == 0:
        raise ConnectionError("Failed to set voltage on any PSU")
    
    print(f"MK1: Set voltage to {volts}V ({successes}/{len(psu_ips)} PSUs)")


def _set_current_mk1(amps, voltage=None):
    """MK1: Set current on all PSUs."""
    psu_config = get_psu_config()
    mk1_config = psu_config['mk1']
    
    # Apply minimum threshold: <1A → 0A
    if amps > 0 and amps < mk1_config['current_min']:
        amps = 0.0
    
    # Validate range
    if amps < 0 or amps > mk1_config['current_max']:
        raise ValueError(f"Current {amps}A out of range (0-{mk1_config['current_max']}A)")
    
    # Set voltage if provided
    if voltage is not None:
        _set_voltage_mk1(voltage)
    
    # Get register info
    reg_addr = mk1_config['psu_registers']['write']['set_current']['address']
    reg_value = int(amps / 0.1)  # Convert to register value
    
    # Write to all PSUs in parallel
    psu_ips = get_psu_ips()
    successes = 0
    failures = 0
    
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(_write_psu_register, ip, reg_addr, reg_value): ip for ip in psu_ips}
        
        for future in as_completed(futures):
            ip = futures[future]
            try:
                if future.result():
                    successes += 1
                else:
                    failures += 1
            except Exception:
                failures += 1
    
    if successes == 0:
        raise ConnectionError("Failed to set current on any PSU")
    
    print(f"MK1: Set current to {amps}A ({successes}/{len(psu_ips)} PSUs)")


def _enable_output_mk1(enabled):
    """MK1: Enable or disable output on all PSUs."""
    psu_config = get_psu_config()
    mk1_config = psu_config['mk1']
    
    # Get register info
    reg_addr = mk1_config['psu_registers']['write']['enable_output']['address']
    reg_value = 1 if enabled else 0
    
    # Write to all PSUs in parallel
    psu_ips = get_psu_ips()
    successes = 0
    failures = 0
    
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(_write_psu_register, ip, reg_addr, reg_value): ip for ip in psu_ips}
        
        for future in as_completed(futures):
            ip = futures[future]
            try:
                if future.result():
                    successes += 1
                else:
                    failures += 1
            except Exception:
                failures += 1
    
    if successes == 0:
        raise ConnectionError("Failed to enable/disable any PSU")
    
    action = "enabled" if enabled else "disabled"
    print(f"MK1: Output {action} ({successes}/{len(psu_ips)} PSUs)")


def _write_psu_register(ip, register, value):
    """Write a single register to one PSU."""
    client = None
    try:
        client = ModbusTcpClient(host=ip, port=502, timeout=0.5)
        if not client.connect():
            return False
        
        response = client.write_register(register, value)
        return not response.isError()
        
    except Exception:
        return False
    finally:
        if client:
            client.close()

