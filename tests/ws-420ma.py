from pymodbus.client import ModbusTcpClient
import time

IP = "192.168.10.14"
PORT = 502
TIMEOUT = 0.2

c = ModbusTcpClient(IP, port=PORT, timeout=TIMEOUT)
c.connect()
n, t0 = 0, time.time()
try:
    while True:
        r = c.read_input_registers(address=0, count=8)
        n += 1
        if n % 200 == 0:
            print([x/1000 for x in r.registers], "|", f"{n/(time.time()-t0):.1f} sps")
except KeyboardInterrupt:
    print("\nStopped by user.")
finally:
    c.close()