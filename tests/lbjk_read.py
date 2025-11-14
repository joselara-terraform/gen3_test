#!/usr/bin/env python3

from pymodbus.client import ModbusTcpClient
import struct

client = ModbusTcpClient('192.168.10.21', port=502)
client.connect()

# Read AIN0 (no scaling needed now)
result = client.read_input_registers(address=0, count=2)

if hasattr(result, 'registers') and len(result.registers) >= 2:
    bytes = struct.pack('>HH', result.registers[0], result.registers[1])
    voltage = struct.unpack('>f', bytes)[0]
    print(f"AIN0 = {voltage:.3f}V")
else:
    print("Error reading AIN0")

client.close()