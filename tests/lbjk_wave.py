#!/usr/bin/env python3
"""
Super Simple Sine Wave Generator
Just change the parameters at the top and run!
"""

from labjack import ljm
import math
import time

# ============================================
# CHANGE THESE PARAMETERS
# ============================================
FREQUENCY = 1.0      # Hz (cycles per second)
MIN_VOLTAGE = 0.0    # Minimum voltage (V)
MAX_VOLTAGE = 5.0    # Maximum voltage (V)
UPDATE_RATE = 100    # Updates per second

# DAC channel: "DAC0" or "DAC1"
DAC_CHANNEL = "DAC1"

# LabJack IP address
IP_ADDRESS = "192.168.10.21"
# ============================================

# Connect to LabJack
handle = ljm.openS("T7", "ETHERNET", IP_ADDRESS)

# Calculate amplitude and offset from min/max
amplitude = (MAX_VOLTAGE - MIN_VOLTAGE) / 2
offset = (MAX_VOLTAGE + MIN_VOLTAGE) / 2

# Display settings
print(f"Sine Wave Generator")
print(f"  Frequency: {FREQUENCY} Hz")
print(f"  Voltage range: {MIN_VOLTAGE}V to {MAX_VOLTAGE}V")
print(f"  Channel: {DAC_CHANNEL}")
print(f"\nPress Ctrl+C to stop")
print("-" * 30)

# Generate sine wave
t = 0
dt = 1.0 / UPDATE_RATE

try:
    while True:
        # Calculate voltage
        voltage = offset + amplitude * math.sin(2 * math.pi * FREQUENCY * t)
        
        # Write to DAC
        ljm.eWriteName(handle, DAC_CHANNEL, voltage)
        
        # Show voltage (update same line)
        print(f"\rVoltage: {voltage:5.2f}V", end='', flush=True)
        
        # Update time and wait
        t += dt
        time.sleep(dt)
        
except KeyboardInterrupt:
    print("\n\nStopping...")
    
# Reset DAC to 0V and close
ljm.eWriteName(handle, DAC_CHANNEL, 0.0)
ljm.close(handle)
print("Done!")