"""BGA Purge control panel widget"""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLabel
from PySide6.QtCore import Qt, Signal

try:
    from ..config_loader import load_config, get_psu_config
    from ..bga_client import set_secondary_gas
except ImportError:
    from config_loader import load_config, get_psu_config
    from bga_client import set_secondary_gas


class BGAPanel(QWidget):
    purge_valves_control = Signal(bool)  # Signal to control purge valves (Gen2 only)
    
    def __init__(self):
        super().__init__()
        
        # Check if Gen2 mode (purge valves needed)
        psu_config = get_psu_config()
        self.is_gen2 = (psu_config['mode'] == 'gen2')
        
        # Load BGA gas configuration
        config = load_config()
        self.bga01_gases = config['modules']['BGA01']['gases']
        self.bga02_gases = config['modules']['BGA02']['gases']
        
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
        """Toggle purge mode for BGAs and valves (Gen2)"""
        # Import set_primary_gas here
        try:
            from ..bga_client import set_primary_gas
        except ImportError:
            from bga_client import set_primary_gas
        
        # Apply to both BGAs using their individual configs
        try:
            import time
            
            # BGA01 - use BGA01 gases
            if checked:
                bga01_primary = self.bga01_gases['primary']
                bga01_secondary = self.bga01_gases['purge']
            else:
                bga01_primary = self.bga01_gases['primary']
                bga01_secondary = self.bga01_gases['secondary']
            
            set_primary_gas('BGA01', bga01_primary)
            time.sleep(0.05)
            set_secondary_gas('BGA01', bga01_secondary)
            time.sleep(0.05)
            
            # BGA02 - use BGA02 gases
            if checked:
                bga02_primary = self.bga02_gases['primary']
                bga02_secondary = self.bga02_gases['purge']
            else:
                bga02_primary = self.bga02_gases['primary']
                bga02_secondary = self.bga02_gases['secondary']
            
            set_primary_gas('BGA02', bga02_primary)
            time.sleep(0.05)
            set_secondary_gas('BGA02', bga02_secondary)
            
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
                from ..bga_client import set_primary_gas
            except ImportError:
                from bga_client import set_primary_gas
            
            # BGA01 - use BGA01 normal gases from config
            bga01_primary = self.bga01_gases['primary']
            bga01_secondary = self.bga01_gases['secondary']
            
            set_primary_gas('BGA01', bga01_primary)
            time.sleep(0.05)
            set_secondary_gas('BGA01', bga01_secondary)
            time.sleep(0.05)
            
            # BGA02 - use BGA02 normal gases from config
            bga02_primary = self.bga02_gases['primary']
            bga02_secondary = self.bga02_gases['secondary']
            
            set_primary_gas('BGA02', bga02_primary)
            time.sleep(0.05)
            set_secondary_gas('BGA02', bga02_secondary)
            
            # Reset button to unchecked
            self.purge_button.setChecked(False)
            
            print("BGAs set to normal mode (safe state)")
        except Exception as e:
            print(f"Error setting BGAs to safe state: {e}")

