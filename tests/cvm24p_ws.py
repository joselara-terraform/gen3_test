#!/usr/bin/env python3
from pymodbus.client import ModbusTcpClient
from struct import pack, unpack
import time

# Configuration
GATEWAY_IP = '192.168.10.15'
PORT = 502
UNITS = [0xA1, 0xA4, 0xA6, 0xA7, 0xA9]
CH1_START = 192
TIMEOUT = 0.5

def f32_wordlittle_bytebig(w0, w1):
    """Convert two Modbus registers to float32 (word-swapped big-endian)"""
    return unpack(">f", pack(">HH", w1, w0))[0]

client = ModbusTcpClient(GATEWAY_IP, port=PORT, timeout=TIMEOUT)

if client.connect():
    print(f"Connected to {GATEWAY_IP}:{PORT}")
    print("Reading channel 1 voltage from all units at 9 Hz (Ctrl+C to stop)")
    print("-" * 50)
    
    try:
        next_read = time.time()
        
        while True:
            voltages = []
            
            for unit in UNITS:
                result = client.read_holding_registers(CH1_START, count=2, device_id=unit)
                
                if hasattr(result, 'registers') and len(result.registers) >= 2:
                    voltage = f32_wordlittle_bytebig(result.registers[0], result.registers[1])
                    voltages.append(f"0x{unit:02X}:{voltage:.3f}V")
                else:
                    voltages.append(f"0x{unit:02X}:ERROR")
            
            print('\r' + ' '.join(voltages), end='', flush=True)
            
            # Maintain 9 Hz rate (111ms per cycle)
            next_read += 0.111
            sleep_time = next_read - time.time()
            if sleep_time > 0:
                time.sleep(sleep_time)
            
    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        client.close()
else:
    print(f"Failed to connect to {GATEWAY_IP}:{PORT}")