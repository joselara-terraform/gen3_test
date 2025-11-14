#!/usr/bin/env python3

import minimalmodbus, time, os

# Connect
psu = minimalmodbus.Instrument("/dev/tty.usbmodem57590316981", 1)
psu.serial.baudrate = 9600
psu.mode = minimalmodbus.MODE_RTU
psu.serial.timeout = 0.5  # Essential for reliability
psu.close_port_after_each_call = True  # Essential for USB adapters

# Get settings
v = float(input("Voltage (V): "))
i = float(input("Current (A): "))
s = input("Start? (1/0): ")

# Write with minimal delays
try:
    psu.write_register(0x0101, int(v/0.1))
    time.sleep(0.1)  # Essential delay
    psu.write_register(0x0102, int(i/0.1))
    time.sleep(0.1)  # Essential delay
    if s in ['0','1']: 
        psu.write_register(0x0103, int(s))
    print("✓ Set")
except:
    print("✗ Write failed")

# Monitor
labels = ["Voltage", "Current", "Power", "Capacity", "Time", "Battery", 
          "SysFault", "ModFault", "Temp", "Status", "SetV", "SetI", "Start"]
scales = [0.1, 0.1, 0.1, 0.1, 1, 0.1, 1, 1, 1, 1, 0.1, 0.1, 1]

while True:
    try:
        vals = psu.read_registers(0x0001, 13)
        os.system('clear')
        print(f"PSU Monitor - {time.strftime('%H:%M:%S')}\n")
        
        for n, (v, s, l) in enumerate(zip(vals, scales, labels)):
            if n in [6,7]: print(f"{l:>8}: 0x{v:04X}")
            elif n in [9,12]: print(f"{l:>8}: {'ON' if v else 'OFF'}")
            else: print(f"{l:>8}: {v*s:7.1f}" if s<1 else f"{l:>8}: {v:7.0f}")
        
        time.sleep(1)
    except KeyboardInterrupt:
        break
    except: pass