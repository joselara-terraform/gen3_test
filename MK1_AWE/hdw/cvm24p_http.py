#!/usr/bin/env python3
from http.server import HTTPServer, BaseHTTPRequestHandler
from pymodbus.client import ModbusTcpClient
from struct import pack, unpack
import threading, time, json

# Configuration
GATEWAY_IP = '192.168.10.15'
PORT = 502
UNITS = [0xA1, 0xA4, 0xA6, 0xA7, 0xA9]
TIMEOUT = 0.5

class CVM:
    def __init__(self):
        self.data = None
        self.lock = threading.Lock()
        self.client = None
        
    def f32_wordlittle_bytebig(self, w0, w1):
        """Convert two Modbus registers to float32 (word-swapped big-endian)"""
        return unpack(">f", pack(">HH", w1, w0))[0]
    
    def run(self):
        while True:
            try:
                self.client = ModbusTcpClient(GATEWAY_IP, port=PORT, timeout=TIMEOUT)
                if self.client.connect():
                    print(f"Connected to CVM at {GATEWAY_IP}:{PORT}")
                    
                    while True:
                        readings = {}
                        channel = 1
                        
                        for unit in UNITS:
                            # Read all 24 channels for this unit (48 registers)
                            result = self.client.read_holding_registers(192, count=48, device_id=unit)  # device_id like in test script
                            
                            if hasattr(result, 'registers') and len(result.registers) == 48:
                                # Process 24 channels
                                for ch in range(24):
                                    reg_idx = ch * 2
                                    voltage = self.f32_wordlittle_bytebig(
                                        result.registers[reg_idx], 
                                        result.registers[reg_idx + 1]
                                    )
                                    readings[f"CV{channel:03d}"] = voltage
                                    channel += 1
                        
                        # Format for InfluxDB
                        if readings:
                            fields = ','.join(f'{k}={v}' for k, v in readings.items())
                            with self.lock:
                                self.data = f"cell_voltages {fields} {int(time.time()*1e9)}"
                        
                        time.sleep(0.1)  # 10Hz update rate
                        
            except Exception as e:
                print(f"Error: {e}")
                if self.client:
                    self.client.close()
                time.sleep(1)

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/metrics':
            with cvm.lock:
                data = cvm.data
            if data:
                self.send_response(200)
                self.end_headers()
                self.wfile.write(data.encode())
            else:
                self.send_error(503)
                
    def log_message(self, *args): pass

cvm = CVM()
threading.Thread(target=cvm.run, daemon=True).start()
HTTPServer(('0.0.0.0', 8890), Handler).serve_forever()