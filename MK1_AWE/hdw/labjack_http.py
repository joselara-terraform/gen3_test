#!/usr/bin/env python3
"""HTTP server for LabJack AIN0 (PSU control voltage feedback) on port 8891"""

from http.server import HTTPServer, BaseHTTPRequestHandler
from pymodbus.client import ModbusTcpClient
import struct
import threading
import time

# LabJack Configuration
HOST = "192.168.10.21"
PORT = 502

# Global variables
latest_voltage = None
data_lock = threading.Lock()


def read_ain0():
    """Read AIN0 as FLOAT32 from LabJack"""
    client = None
    try:
        client = ModbusTcpClient(HOST, port=PORT, timeout=1)
        if not client.connect():
            return None
        
        # Read input registers 0 and 1 (AIN0 as FLOAT32)
        result = client.read_input_registers(address=0, count=2)
        
        if hasattr(result, 'registers') and len(result.registers) >= 2:
            # Convert to float (big-endian word order, big-endian bytes)
            bytes_data = struct.pack('>HH', result.registers[0], result.registers[1])
            voltage = struct.unpack('>f', bytes_data)[0]
            return voltage
        
        return None
        
    except Exception:
        return None
    finally:
        if client:
            client.close()


def poll_labjack():
    """Continuously poll LabJack AIN0"""
    global latest_voltage
    
    while True:
        try:
            voltage = read_ain0()
            
            with data_lock:
                latest_voltage = voltage
            
            time.sleep(0.1)  # 1Hz polling
            
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(1)


class MetricsHandler(BaseHTTPRequestHandler):
    """HTTP request handler for metrics endpoint"""
    
    def do_GET(self):
        if self.path == '/metrics':
            with data_lock:
                voltage = latest_voltage
            
            if voltage is not None:
                # Format for InfluxDB line protocol
                metric_line = f"labjack AIN0_voltage={voltage:.6f} {int(time.time()*1e9)}"
                
                self.send_response(200)
                self.send_header('Content-Type', 'text/plain')
                self.end_headers()
                self.wfile.write(metric_line.encode())
            else:
                self.send_error(503, "No data available")
        else:
            self.send_error(404)
    
    def log_message(self, *args):
        """Suppress request logging"""
        pass


def main():
    """Main entry point"""
    # Start LabJack polling thread
    poll_thread = threading.Thread(target=poll_labjack, daemon=True)
    poll_thread.start()
    
    # Start HTTP server
    server = HTTPServer(('localhost', 8891), MetricsHandler)
    print(f"LabJack HTTP server started on port 8891")
    print(f"Polling AIN0 at {HOST}:{PORT}")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
        server.shutdown()


if __name__ == "__main__":
    main()

