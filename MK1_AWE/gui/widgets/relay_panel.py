"""Relay control panel widget"""

from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QGroupBox, QPushButton, QGridLayout, QMessageBox
from PySide6.QtCore import Qt, Signal

try:
    from ..config_loader import load_config, get_rlm_endpoint
    from ..modbus_client import write_coil
except ImportError:
    from config_loader import load_config, get_rlm_endpoint
    from modbus_client import write_coil


class RelayPanel(QWidget):
    contactor_state_changed = Signal(bool)  # Signal when RL01 (contactor) state changes
    
    def __init__(self):
        super().__init__()
        
        # Store all buttons for enable/disable
        self.all_buttons = []
        self.contactor_button = None
        self.current_setpoint = 0.0  # Track PSU current for interlock
        
        # Track purge valve buttons (RL02, RL03)
        self.purge_valve_buttons = []  # Will store RL02 and RL03 buttons
        
        # Load relay configuration
        config = load_config()
        rlm_config = config['modules']['RLM_30ch']
        
        # Separate valves and pumps
        valves = {k: v for k, v in rlm_config.items() if v.get('type') == 'valve'}
        pumps = {k: v for k, v in rlm_config.items() if v.get('type') == 'pump'}
        
        # Main layout
        main_layout = QHBoxLayout(self)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Valves group
        valve_group = self._create_relay_group("Valves", valves)
        main_layout.addWidget(valve_group)
        
        # Pumps group
        pump_group = self._create_relay_group("Pumps", pumps)
        main_layout.addWidget(pump_group)
        
        # Apply styling
        self.setStyleSheet("""
            QGroupBox {
                font-size: 16px;
                font-weight: bold;
                color: #e0e0e0;
                border: 2px solid #555555;
                border-radius: 8px;
                margin-top: 10px;
                padding: 15px;
                background-color: #3c3c3c;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 5px 10px;
                background-color: #2b2b2b;
                border-radius: 4px;
            }
            QPushButton {
                background-color: #555555;
                color: #e0e0e0;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 13px;
                min-width: 120px;
            }
            QPushButton:hover {
                background-color: #666666;
            }
            QPushButton:checked {
                background-color: #4CAF50;
                font-weight: bold;
            }
            QPushButton:disabled {
                background-color: #2a2a2a;
                color: #555555;
                border: 2px dashed #444444;
            }
        """)
    
    def _create_relay_group(self, title, relays):
        """Create a group box with relay buttons"""
        group = QGroupBox(title)
        layout = QGridLayout()
        layout.setSpacing(10)
        
        # Sort relays by address
        sorted_relays = sorted(relays.items(), key=lambda x: x[1]['address'])
        
        # Create buttons in grid (2 columns)
        for idx, (relay_id, relay_info) in enumerate(sorted_relays):
            row = idx // 2
            col = idx % 2
            
            button = QPushButton(relay_info['name'])
            button.setCheckable(True)
            button.setEnabled(False)  # Disabled until RLM connects
            button.setProperty("relay_id", relay_id)
            button.setProperty("address", relay_info['address'])
            
            # Check if this is the safety contactor
            is_contactor = relay_info.get('safety_contactor', False)
            if is_contactor:
                self.contactor_button = button
                # Connect with interlock check
                button.clicked.connect(lambda checked, addr=relay_info['address']: self._toggle_contactor(addr, checked))
            else:
                # Normal relay
                button.clicked.connect(lambda checked, addr=relay_info['address']: self._toggle_relay(addr, checked))
            
            # Track purge valves (RL02, RL03) for Gen2 purge control
            if relay_id in ['RL02', 'RL03']:
                self.purge_valve_buttons.append(button)
            
            layout.addWidget(button, row, col)
            self.all_buttons.append(button)
        
        group.setLayout(layout)
        return group
    
    def set_hardware_available(self, available):
        """Enable/disable relay controls based on RLM availability"""
        for button in self.all_buttons:
            button.setEnabled(available)
    
    def set_all_off(self):
        """Turn all relays OFF (safe state)"""
        try:
            host, port = get_rlm_endpoint()
            for button in self.all_buttons:
                address = button.property("address")
                write_coil(host, address, False, port=port)
                button.setChecked(False)
            print("All relays set to OFF (safe state)")
        except Exception as e:
            print(f"Error setting relays to safe state: {e}")
    
    def set_psu_current(self, amps):
        """Update PSU current setpoint for interlock logic"""
        self.current_setpoint = amps
    
    def set_purge_valves(self, purge_active):
        """Control purge valves RL02 and RL03 (Gen2 mode only)"""
        try:
            host, port = get_rlm_endpoint()
            for button in self.purge_valve_buttons:
                address = button.property("address")
                write_coil(host, address, purge_active, port=port)
                button.setChecked(purge_active)
        except Exception as e:
            print(f"Error controlling purge valves: {e}")
    
    def _toggle_contactor(self, address, state):
        """Toggle safety contactor (RL01) with interlock check"""
        # Interlock: Can't turn OFF if current > 0A
        if not state and self.current_setpoint > 0.01:
            # Prevent turning OFF - revert button
            if self.contactor_button:
                self.contactor_button.setChecked(True)
            
            # Show warning
            self._show_interlock_warning(
                "Cannot open contactor",
                f"Current must be 0A before opening contactor.\nCurrent setpoint: {self.current_setpoint:.1f}A"
            )
            return
        
        # Allowed - proceed with toggle
        try:
            host, port = get_rlm_endpoint()
            write_coil(host, address, state, port=port)
            # Emit state change signal
            self.contactor_state_changed.emit(state)
        except Exception as e:
            print(f"Error toggling contactor: {e}")
            if self.contactor_button:
                self.contactor_button.setChecked(not state)
    
    def _toggle_relay(self, address, state):
        """Toggle a normal relay via Modbus"""
        try:
            host, port = get_rlm_endpoint()
            write_coil(host, address, state, port=port)
        except Exception as e:
            print(f"Error toggling relay {address}: {e}")
    
    def _show_interlock_warning(self, title, message):
        """Show styled interlock warning dialog"""
        msg = QMessageBox(self)
        msg.setWindowTitle(title)
        msg.setText(message)
        msg.setStandardButtons(QMessageBox.Ok)
        msg.setStyleSheet("""
            QMessageBox {
                background-color: #2b2b2b;
            }
            QLabel {
                color: #e0e0e0;
                font-size: 14px;
            }
            QPushButton {
                background-color: #555555;
                color: #e0e0e0;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 14px;
            }
        """)
        msg.exec()

