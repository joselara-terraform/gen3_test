#!/usr/bin/env python3

from pymodbus.client import ModbusTcpClient
import struct

client = ModbusTcpClient('192.168.10.21', port=502)
client.connect()

print("Setting AIN0 range to ±10V...")

# Set AIN0_RANGE to 10V (value = 10.0)
# AIN0_RANGE register is at address 40000
range_value = 10.0
bytes = struct.pack('>f', range_value)
regs = [struct.unpack('>H', bytes[0:2])[0], 
        struct.unpack('>H', bytes[2:4])[0]]

client.write_registers(40000, regs)
print("AIN0_RANGE set to ±10V")

# Wait a moment for the setting to take effect
import time
time.sleep(0.1)

# Now read AIN0
result = client.read_input_registers(address=0, count=2)
if hasattr(result, 'registers') and len(result.registers) >= 2:
    bytes = struct.pack('>HH', result.registers[0], result.registers[1])
    voltage = struct.unpack('>f', bytes)[0]
    print(f"\nAIN0 = {voltage:.3f}V")
else:
    print("Error reading AIN0")

client.close()