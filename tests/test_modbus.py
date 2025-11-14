import serial
import time

# Configuration
PORT = '/dev/tty.usbserial-B0035Q79'
BAUDRATE = 9600
TIMEOUT = 1.0

def calc_crc16(data):
    crc = 0xFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 0x0001:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1
        return crc

ser = serial.Serial(PORT, BAUDRATE, timeout=TIMEOUT)
print("Testing communication...\n")

# Test the exact same request that worked before
print("=== Sending the exact request that worked in Test 3 ===")
# 01 03 00 00 00 0D 84 0F
request = bytes.fromhex("01 03 00 00 00 0D 84 0F")
print(f"TX: {' '.join(f'{b:02X}' for b in request)}")

ser.reset_input_buffer()
ser.write(request)

# Wait and collect response
time.sleep(0.5)  # Longer wait
response = bytearray()

# Read everything available
timeout_counter = 0
while timeout_counter < 10:  # Try for up to 1 second
    if ser.in_waiting > 0:
        chunk = ser.read(ser.in_waiting)
        response.extend(chunk)
        print(f"Received {len(chunk)} bytes")
        timeout_counter = 0  # Reset counter when data received
    else:
        timeout_counter += 1
        time.sleep(0.1)

if response:
    print(f"\nTotal response: {len(response)} bytes")
    print(f"RX: {' '.join(f'{b:02X}' for b in response)}")
    
    # Decode the response
    if len(response) > 3 and response[0] == 0x01 and response[1] == 0x03:
        byte_count = response[2]
        print(f"\nByte count: 0x{byte_count:02X} ({byte_count} decimal)")
        
        # Look for patterns
        if byte_count > 26:  # More than expected for 13 registers
            print("Non-standard response with extra data")
            
            # Try to find where the actual register data might start
            # Look for reasonable values
            print("\nSearching for register data patterns:")
            for i in range(3, min(len(response)-1, 50), 2):
                value = (response[i] << 8) | response[i+1]
                if value < 1000:  # Reasonable value range
                    print(f"  Position {i}: 0x{value:04X} ({value}, {value/10.0:.1f})")
else:
    print("No response received!")

# Try single register one more time
print("\n=== Testing single register again ===")
request = bytes.fromhex("01 03 00 0B 00 01 F5 C8")
print(f"TX: {' '.join(f'{b:02X}' for b in request)}")

ser.reset_input_buffer()
ser.write(request)
time.sleep(0.3)

response = ser.read(ser.in_waiting or 100)
if response:
    print(f"RX: {' '.join(f'{b:02X}' for b in response)}")
else:
    print("No response")

ser.close()

# Sanity check on CRC
print("\n=== CRC Verification ===")
test_data = bytes([0x01, 0x03, 0x00, 0x00, 0x00, 0x0D])
crc = calc_crc16(test_data)
print(f"Data: {' '.join(f'{b:02X}' for b in test_data)}")
print(f"CRC: {crc:04X} -> {crc & 0xFF:02X} {(crc >> 8) & 0xFF:02X}")
print(f"Full frame: {' '.join(f'{b:02X}' for b in test_data)} {crc & 0xFF:02X} {(crc >> 8) & 0xFF:02X}")