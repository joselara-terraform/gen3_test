#!/usr/bin/env python3

from pymodbus.client import ModbusTcpClient
import struct

client = ModbusTcpClient('192.168.10.21', port=502)
client.connect()

voltage = float(input("DAC1 Voltage (0-5V): "))
voltage = max(0.0, min(5.0, voltage))

# Convert float to registers
bytes = struct.pack('>f', voltage)
regs = [struct.unpack('>H', bytes[0:2])[0], 
        struct.unpack('>H', bytes[2:4])[0]]

# DAC1 address is 1002 (vs TDAC0 at 30000)
client.write_registers(1002, regs)
print(f"DAC1 = {voltage}V")

client.close()