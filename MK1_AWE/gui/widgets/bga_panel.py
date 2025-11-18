"""BGA Purge control panel widget"""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLabel
from PySide6.QtCore import Qt, Signal

try:
    from ..config_loader import load_config, get_psu_config, load_sensor_labels
    from ..bga_client import set_secondary_gas
except ImportError:
    from config_loader import load_config, get_psu_config, load_sensor_labels
    from bga_client import set_secondary_gas


class BGAPanel(QWidget):
    purge_valves_control = Signal(bool)  # Signal to control purge valves (Gen2 only)
    
    def __init__(self):
        super().__init__()
        
        # Check if Gen2 mode (purge valves needed)
        psu_config = get_psu_config()
        self.is_gen2 = (psu_config.get('mode') == 'gen2')
        
        # Load BGA gas configuration from sensor_labels.yaml
        labels = load_sensor_labels()
        bgas = labels.get('bgas', {})
        self.bga01_gases = bgas.get('BGA01', {}).get('gases', {'primary': '1333-74-0', 'secondary': '7782-44-7', 'purge': '7727-37-9'})
        self.bga02_gases = bgas.get('BGA02', {}).get('gases', {'primary': '7782-44-7', 'secondary': '1333-74-0', 'purge': '7727-37-9'})
        self.bga03_gases = bgas.get('BGA03', {}).get('gases', self.bga01_gases)
        
        # Layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)
        
        # Purge button
        self.purge_button = QPushButton("PURGE")
        self.purge_button.setCheckable(True)
        self.purge_button.setEnabled(False)  # Disabled until at least 1 BGA connects
        self.purge_button.setMinimumHeight(100)
        self.purge_button.clicked.connect(self._toggle_purge)
        layout.addWidget(self.purge_button)
        
        layout.addStretch()
        
        # Apply styling
        self.setStyleSheet("""
            QPushButton {
                background-color: #555555;
                color: #e0e0e0;
                border: none;
                border-radius: 8px;
                font-size: 18px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #666666;
            }
            QPushButton:checked {
                background-color: #FF9800;
                color: #000000;
            }
            QPushButton:disabled {
                background-color: #333333;
                color: #666666;
                border: 2px dashed #444444;
            }
        """)
    
    def _toggle_purge(self, checked):
        """Toggle purge mode for all BGAs"""
        # Import BGA client functions
        try:
            from ..bga_client import set_primary_gas, set_secondary_gas
        except ImportError:
            from bga_client import set_primary_gas, set_secondary_gas
        
        # Apply to all 3 BGAs
        try:
            import time
            
            # BGA01
            secondary = self.bga01_gases['purge'] if checked else self.bga01_gases['secondary']
            set_primary_gas('BGA01', self.bga01_gases['primary'])
            time.sleep(0.05)
            set_secondary_gas('BGA01', secondary)
            time.sleep(0.05)
            
            # BGA02
            secondary = self.bga02_gases['purge'] if checked else self.bga02_gases['secondary']
            set_primary_gas('BGA02', self.bga02_gases['primary'])
            time.sleep(0.05)
            set_secondary_gas('BGA02', secondary)
            time.sleep(0.05)
            
            # BGA03
            secondary = self.bga03_gases['purge'] if checked else self.bga03_gases['secondary']
            set_primary_gas('BGA03', self.bga03_gases['primary'])
            time.sleep(0.05)
            set_secondary_gas('BGA03', secondary)
            
            # Gen2 mode: Also control purge valves (RL02, RL03)
            if self.is_gen2:
                time.sleep(0.05)
                self.purge_valves_control.emit(checked)
                
        except Exception as e:
            print(f"Error setting BGA gases: {e}")
            # Revert button state on error
            self.purge_button.setChecked(not checked)
    
    def set_hardware_available(self, bga1_online, bga2_online):
        """Enable/disable purge button based on BGA availability"""
        # Enable if at least one BGA is online
        self.purge_button.setEnabled(bga1_online or bga2_online)
    
    def set_normal_mode(self):
        """Set BGAs to normal operation mode (safe state)"""
        try:
            import time
            
            # Import here to avoid circular dependency
            try:
                from ..bga_client import set_primary_gas, set_secondary_gas
            except ImportError:
                from bga_client import set_primary_gas, set_secondary_gas
            
            # BGA01
            set_primary_gas('BGA01', self.bga01_gases['primary'])
            time.sleep(0.05)
            set_secondary_gas('BGA01', self.bga01_gases['secondary'])
            time.sleep(0.05)
            
            # BGA02
            set_primary_gas('BGA02', self.bga02_gases['primary'])
            time.sleep(0.05)
            set_secondary_gas('BGA02', self.bga02_gases['secondary'])
            time.sleep(0.05)
            
            # BGA03
            set_primary_gas('BGA03', self.bga03_gases['primary'])
            time.sleep(0.05)
            set_secondary_gas('BGA03', self.bga03_gases['secondary'])
            
            # Reset button to unchecked
            self.purge_button.setChecked(False)
            
            print("BGAs set to normal mode (safe state)")
        except Exception as e:
            print(f"Error setting BGAs to safe state: {e}")

