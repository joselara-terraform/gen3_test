"""Hardware status indicators widget"""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Qt, QThread, Signal
from pymodbus.client import ModbusTcpClient
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    from ..config_loader import get_rlm_endpoint, get_bga_ports, get_psu_ips, get_psu_config, load_config
    from ..bga_client import is_bridge_available
except ImportError:
    from config_loader import get_rlm_endpoint, get_bga_ports, get_psu_ips, get_psu_config, load_config
    from bga_client import is_bridge_available


class StatusWorker(QThread):
    """Background worker for checking hardware status"""
    status_updated = Signal(dict)
    
    def run(self):
        """Check all devices in parallel and emit results"""
        results = {}
        
        # Define all checks as tasks
        tasks = []
        
        # Build task list
        try:
            host, port = get_rlm_endpoint()
            tasks.append(('RLM', lambda: self._check_modbus_device(host, 1, "coil", 0)))
        except Exception:
            results['RLM'] = False
        
        tasks.append(('TCM', lambda: self._check_modbus_device("192.168.10.13", 1, "holding", 32)))
        tasks.append(('AIM', lambda: self._check_modbus_device("192.168.10.14", 1, "input", 0)))
        tasks.append(('CVM', lambda: self._check_modbus_device("192.168.10.15", 1, "input", 0)))
        
        try:
            ports = get_bga_ports()
            tasks.append(('BGA01', lambda p=ports['BGA01']: is_bridge_available(p, timeout=0.5)))
            tasks.append(('BGA02', lambda p=ports['BGA02']: is_bridge_available(p, timeout=0.5)))
        except Exception:
            results['BGA01'] = False
            results['BGA02'] = False
        
        # Execute all checks in parallel
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = {executor.submit(task_fn): name for name, task_fn in tasks}
            
            for future in as_completed(futures):
                name = futures[future]
                try:
                    results[name] = future.result()
                except Exception:
                    results[name] = False
        
        # PSUs - mode-aware check
        try:
            psu_config = get_psu_config()
            mode = psu_config['mode']
            
            if mode == 'gen2':
                # Gen2: Check LabJack connectivity
                config = load_config()
                lbjk = config['devices']['LBJK']
                lbjk_online = self._check_modbus_device(lbjk['ip'], 1, "holding", 0)
                results['PSUs'] = ('gen2', lbjk_online)
            elif mode == 'mk1':
                # MK1: Check all 10 PSUs
                psu_ips = get_psu_ips()
                with ThreadPoolExecutor(max_workers=10) as executor:
                    psu_futures = {executor.submit(self._check_modbus_device, ip, 1, "input", 0): ip for ip in psu_ips}
                    online_count = sum(1 for future in as_completed(psu_futures) if future.result())
                results['PSUs'] = ('mk1', (online_count, len(psu_ips)))
            else:
                results['PSUs'] = ('unknown', False)
        except Exception:
            results['PSUs'] = ('unknown', False)
        
        self.status_updated.emit(results)
    
    def _check_modbus_device(self, ip, slave_id, register_type, address):
        """Verify Modbus device responds by reading a register/coil"""
        client = None
        try:
            client = ModbusTcpClient(host=ip, port=502, timeout=0.5)
            if not client.connect():
                return False
            
            if register_type == "coil":
                response = client.read_coils(address, count=1)
            elif register_type == "holding":
                response = client.read_holding_registers(address, count=1)
            elif register_type == "input":
                response = client.read_input_registers(address, count=1)
            else:
                return False
            
            return hasattr(response, 'registers') or hasattr(response, 'bits')
        except Exception:
            return False
        finally:
            if client:
                client.close()


class HardwareStatusWidget(QWidget):
    hardware_status_changed = Signal(dict)
    
    def __init__(self):
        super().__init__()
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)
        
        # Create status indicators
        self.status_labels = {}
        device_names = ['RLM', 'TCM', 'AIM', 'CVM', 'BGA01', 'BGA02', 'PSUs']
        
        for name in device_names:
            indicator = self._create_status_indicator(name)
            self.status_labels[name] = indicator
            layout.addWidget(indicator)
        
        layout.addStretch()
        
        # Apply styling
        self.setStyleSheet("""
            QLabel {
                font-size: 13px;
                color: #e0e0e0;
                padding: 5px 10px;
                border-radius: 4px;
                background-color: #4a4a4a;
            }
        """)
        
        # Background worker
        self.worker = None
    
    def _create_status_indicator(self, name):
        """Create a single status indicator label"""
        label = QLabel(f"● {name}: Unknown")
        label.setProperty("device", name)
        label.setProperty("status", "unknown")
        self._update_indicator_style(label, "unknown")
        return label
    
    def _update_indicator_style(self, label, status):
        """Update indicator color based on status"""
        colors = {
            "online": "#4CAF50",   # Green
            "offline": "#F44336",  # Red
            "unknown": "#9E9E9E"   # Gray
        }
        color = colors.get(status, colors["unknown"])
        
        label.setStyleSheet(f"""
            QLabel {{
                font-size: 13px;
                color: {color};
                padding: 5px 10px;
                border-radius: 4px;
                background-color: #4a4a4a;
                font-weight: bold;
            }}
        """)
    
    def update_status(self):
        """Start background check of hardware status (non-blocking)"""
        # Don't start new check if one is already running
        if self.worker and self.worker.isRunning():
            return
        
        self.worker = StatusWorker()
        self.worker.status_updated.connect(self._apply_status_results)
        self.worker.start()
    
    def _apply_status_results(self, results):
        """Apply status results to UI (runs in main thread)"""
        # RLM
        status = "online" if results.get('RLM', False) else "offline"
        self.status_labels['RLM'].setText(f"● RLM: {'Online' if status == 'online' else 'Offline'}")
        self._update_indicator_style(self.status_labels['RLM'], status)
        
        # TCM
        status = "online" if results.get('TCM', False) else "offline"
        self.status_labels['TCM'].setText(f"● TCM: {'Online' if status == 'online' else 'Offline'}")
        self._update_indicator_style(self.status_labels['TCM'], status)
        
        # AIM
        status = "online" if results.get('AIM', False) else "offline"
        self.status_labels['AIM'].setText(f"● AIM: {'Online' if status == 'online' else 'Offline'}")
        self._update_indicator_style(self.status_labels['AIM'], status)
        
        # CVM
        status = "online" if results.get('CVM', False) else "offline"
        self.status_labels['CVM'].setText(f"● CVM: {'Online' if status == 'online' else 'Offline'}")
        self._update_indicator_style(self.status_labels['CVM'], status)
        
        # BGA01
        status = "online" if results.get('BGA01', False) else "offline"
        self.status_labels['BGA01'].setText(f"● BGA01: {'Online' if status == 'online' else 'Offline'}")
        self._update_indicator_style(self.status_labels['BGA01'], status)
        
        # BGA02
        status = "online" if results.get('BGA02', False) else "offline"
        self.status_labels['BGA02'].setText(f"● BGA02: {'Online' if status == 'online' else 'Offline'}")
        self._update_indicator_style(self.status_labels['BGA02'], status)
        
        # PSUs - mode-aware display
        psu_data = results.get('PSUs', ('unknown', False))
        if isinstance(psu_data, tuple) and len(psu_data) == 2:
            mode, status_info = psu_data
            
            if mode == 'gen2':
                # Gen2: Single PSU via LabJack
                is_online = status_info
                psu_status = "online" if is_online else "offline"
                self.status_labels['PSUs'].setText(f"● PSU: {'Online' if is_online else 'Offline'}")
                self._update_indicator_style(self.status_labels['PSUs'], psu_status)
            elif mode == 'mk1':
                # MK1: Multiple PSUs
                online_count, total = status_info if isinstance(status_info, tuple) else (0, 10)
                psu_status = "online" if online_count == total else ("offline" if online_count == 0 else "unknown")
                self.status_labels['PSUs'].setText(f"● PSUs: {online_count}/{total}")
                self._update_indicator_style(self.status_labels['PSUs'], psu_status)
            else:
                self.status_labels['PSUs'].setText(f"● PSU: Unknown")
                self._update_indicator_style(self.status_labels['PSUs'], "unknown")
        else:
            self.status_labels['PSUs'].setText(f"● PSU: Error")
            self._update_indicator_style(self.status_labels['PSUs'], "offline")
        
        # Emit signal for hardware availability changes
        self.hardware_status_changed.emit(results)

