import serial
import time

# Configuration
PORT = '/dev/tty.usbserial-B0035Q79'  # Change this to your serial port
BAUDRATE = 9600
TIMEOUT = 1.0

# Request frame in hex (modify this)
REQUEST = "01 03 00 0B 00 01 F5 C8"

# Unit scaling factor (0.1 for voltage)
UNIT_SCALE = 0.1

# Convert hex string to bytes
request_bytes = bytes.fromhex(REQUEST.replace(" ", ""))

# Open serial port
ser = serial.Serial(PORT, BAUDRATE, timeout=TIMEOUT)

# Clear buffers
ser.reset_input_buffer()
ser.reset_output_buffer()

# Send request
print(f"TX: {' '.join(f'{b:02X}' for b in request_bytes)}")
ser.write(request_bytes)

# Wait a bit for response
time.sleep(0.1)

# Read all available bytes
response = ser.read(ser.in_waiting or 1)
if ser.in_waiting:
    response += ser.read(ser.in_waiting)

# Print response
if response:
    print(f"RX: {' '.join(f'{b:02X}' for b in response)}")
    
    # Parse register value if valid Modbus response
    if len(response) >= 5 and response[1] == 0x03 and response[2] == 0x02:
        # Extract register value (big-endian)
        register_value = (response[3] << 8) | response[4]
        scaled_value = register_value * UNIT_SCALE
        
        print(f"\nRegister value: 0x{register_value:04X} ({register_value} decimal)")
        print(f"Scaled value: {scaled_value:.1f} V")
    elif len(response) >= 5:
        print("\nWarning: Non-standard response format")
        # Try to decode anyway
        if response[2] <= len(response) - 3:  # If byte count seems valid
            print(f"Byte count: {response[2]}")
            # Show possible register values at different positions
            for i in range(3, min(len(response) - 1, 10), 2):
                value = (response[i] << 8) | response[i + 1]
                scaled = value * UNIT_SCALE
                print(f"  Bytes {i}-{i+1}: 0x{value:04X} ({value} decimal, {scaled:.1f} scaled)")
else:
    print("RX: No response")

# Close port
ser.close()