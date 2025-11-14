#!/usr/bin/env python3
import time
from pymodbus.client import ModbusTcpClient

# Configuration
MODULE_IP = '192.168.10.2'
PORT = 502
CHANNEL = 5  # Relay channel (1-30)
ON_TIME = 5  # Seconds

# Control relay
client = ModbusTcpClient(MODULE_IP, port=PORT)
if client.connect():
    client.write_coil(CHANNEL - 1, True)  # ON
    time.sleep(ON_TIME)
    client.write_coil(CHANNEL - 1, False)  # OFF
    client.close()

















# # Configuration
# MODULE_IP = '192.168.10.2'
# ON_TIME = 2  # Seconds per channel
# NUM_CHANNELS = 30

# # Control relays
# client = ModbusTcpClient(MODULE_IP, port=502)
# if client.connect():
#     for ch in range(NUM_CHANNELS):
#         client.write_coil(ch, True)   # ON
#         time.sleep(ON_TIME)
#         client.write_coil(ch, False)  # OFF
#     client.close()

# #!/usr/bin/env python3
# import time
# from pymodbus.client import ModbusTcpClient
