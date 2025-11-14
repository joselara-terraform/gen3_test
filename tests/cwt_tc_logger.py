#!/usr/bin/env python3
from pymodbus.client import ModbusTcpClient
import time

client = ModbusTcpClient('192.168.10.13', port=502, timeout=0.5)
client.connect()

try:
    while True:
        result = client.read_holding_registers(0x20, count=16, device_id=1)
        if hasattr(result, 'registers'):
            temps = []
            for i, r in enumerate(result.registers):
                temp = r/10.0
                if r < 10000:
                    temps.append(f'CH{i+1}:{temp:.1f}°C')
                else:
                    temps.append(f'CH{i+1}:NC')  # Not Connected
            print('\r' + ' '.join(temps), end='', flush=True)
except KeyboardInterrupt:
    print("\nStopping...")
finally:
    client.close()