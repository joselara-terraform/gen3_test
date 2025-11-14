#!/usr/bin/env python3
import requests
import time
from datetime import datetime

def check_bga_status(bga_num, timeout=2):
    """Check if a BGA is connected and returning data"""
    port = 8888 if bga_num == 1 else 8889
    
    try:
        response = requests.get(f'http://localhost:{port}/metrics', timeout=timeout)
        
        if response.status_code == 200:
            # Check if data is recent (within last 5 seconds)
            data = response.text
            timestamp = int(data.split()[-1]) / 1e9
            age = time.time() - timestamp
            
            if age < 5:
                return "Connected", age
            else:
                return "Stale Data", age
        else:
            return "No Data", None
            
    except requests.exceptions.RequestException:
        return "Disconnected", None

def monitor_bgas(interval=5):
    """Continuously monitor both BGAs"""
    print("BGA Connection Monitor")
    print("-" * 40)
    
    while True:
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # Check both BGAs
        bga1_status, bga1_age = check_bga_status(1)
        bga2_status, bga2_age = check_bga_status(2)
        
        # Format output
        age1 = f"({bga1_age:.1f}s ago)" if bga1_age is not None else ""
        age2 = f"({bga2_age:.1f}s ago)" if bga2_age is not None else ""
        
        print(f"[{timestamp}] BGA1: {bga1_status} {age1} | BGA2: {bga2_status} {age2}")
        
        time.sleep(interval)

if __name__ == "__main__":
    # One-time check
    print("BGA Status Check:")
    for i in [1, 2]:
        status, age = check_bga_status(i)
        print(f"BGA{i}: {status}")