"""Export data dialog widget"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QLineEdit, QPushButton, QFormLayout, QMessageBox,
    QDateEdit, QTimeEdit
)
from PySide6.QtCore import Qt, Signal, QDate, QTime
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from pathlib import Path


class ExportDialog(QDialog):
    """Dialog for configuring and triggering data export"""
    
    export_requested = Signal()  # Signal when export should run
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.setWindowTitle("Export Test Data")
        self.setMinimumWidth(500)
        self.setModal(True)
        
        # Layout
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Title
        title = QLabel("Export Data to CSV")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #e0e0e0;")
        layout.addWidget(title)
        
        # Input form
        form_layout = QFormLayout()
        form_layout.setSpacing(15)
        
        # Test name input
        self.test_name_input = QLineEdit()
        self.test_name_input.setPlaceholderText("e.g., Gen3_Test_1")
        self.test_name_input.setText("Gen3_Test_1")
        form_layout.addRow("Test Name:", self.test_name_input)
        
        # Start date/time inputs
        default_start = datetime.now(ZoneInfo('America/Los_Angeles')) - timedelta(hours=1)
        
        start_layout = QHBoxLayout()
        self.start_date = QDateEdit()
        self.start_date.setCalendarPopup(True)
        self.start_date.setDate(QDate(default_start.year, default_start.month, default_start.day))
        self.start_date.setDisplayFormat("yyyy-MM-dd")
        start_layout.addWidget(self.start_date)
        
        self.start_time = QTimeEdit()
        self.start_time.setTime(QTime(default_start.hour, default_start.minute, default_start.second))
        self.start_time.setDisplayFormat("HH:mm:ss")
        start_layout.addWidget(self.start_time)
        
        form_layout.addRow("Start (PT):", start_layout)
        
        # End date/time inputs
        default_end = datetime.now(ZoneInfo('America/Los_Angeles'))
        
        end_layout = QHBoxLayout()
        self.end_date = QDateEdit()
        self.end_date.setCalendarPopup(True)
        self.end_date.setDate(QDate(default_end.year, default_end.month, default_end.day))
        self.end_date.setDisplayFormat("yyyy-MM-dd")
        end_layout.addWidget(self.end_date)
        
        self.end_time = QTimeEdit()
        self.end_time.setTime(QTime(default_end.hour, default_end.minute, default_end.second))
        self.end_time.setDisplayFormat("HH:mm:ss")
        end_layout.addWidget(self.end_time)
        
        form_layout.addRow("End (PT):", end_layout)
        
        layout.addLayout(form_layout)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        
        self.export_button = QPushButton("EXPORT")
        self.export_button.setMinimumHeight(50)
        self.export_button.clicked.connect(self._on_export_clicked)
        button_layout.addWidget(self.export_button)
        
        self.cancel_button = QPushButton("CANCEL")
        self.cancel_button.setMinimumHeight(50)
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)
        
        layout.addLayout(button_layout)
        
        # Apply styling
        self.setStyleSheet("""
            QDialog {
                background-color: #2b2b2b;
            }
            QLabel {
                color: #e0e0e0;
                font-size: 14px;
            }
            QLineEdit {
                background-color: #4a4a4a;
                color: #e0e0e0;
                border: 2px solid #555555;
                border-radius: 6px;
                padding: 10px;
                font-size: 14px;
            }
            QLineEdit:focus {
                border: 2px solid #2196F3;
            }
            QDateEdit, QTimeEdit {
                background-color: #4a4a4a;
                color: #e0e0e0;
                border: 2px solid #555555;
                border-radius: 6px;
                padding: 8px;
                font-size: 14px;
                min-width: 140px;
            }
            QDateEdit:focus, QTimeEdit:focus {
                border: 2px solid #2196F3;
            }
            QDateEdit::drop-down, QTimeEdit::up-button, QTimeEdit::down-button {
                background-color: #555555;
                border: none;
                width: 20px;
            }
            QDateEdit::drop-down:hover, QTimeEdit::up-button:hover, QTimeEdit::down-button:hover {
                background-color: #666666;
            }
            QPushButton {
                border: none;
                border-radius: 6px;
                font-size: 16px;
                font-weight: bold;
                color: #ffffff;
            }
            QPushButton#export_button {
                background-color: #2196F3;
            }
            QPushButton#export_button:hover {
                background-color: #1976D2;
            }
            QPushButton#cancel_button {
                background-color: #555555;
            }
            QPushButton#cancel_button:hover {
                background-color: #666666;
            }
        """)
        
        self.export_button.setObjectName("export_button")
        self.cancel_button.setObjectName("cancel_button")
    
    def _on_export_clicked(self):
        """Validate inputs and update test_config.py"""
        # Get test name
        test_name = self.test_name_input.text().strip()
        
        # Validate test name
        if not test_name:
            self._show_error("Invalid Input", "Test name cannot be empty")
            return
        
        # Get start datetime from pickers
        start_qdate = self.start_date.date()
        start_qtime = self.start_time.time()
        start_time = datetime(
            start_qdate.year(), start_qdate.month(), start_qdate.day(),
            start_qtime.hour(), start_qtime.minute(), start_qtime.second(),
            tzinfo=ZoneInfo('America/Los_Angeles')
        )
        
        # Get end datetime from pickers
        end_qdate = self.end_date.date()
        end_qtime = self.end_time.time()
        end_time = datetime(
            end_qdate.year(), end_qdate.month(), end_qdate.day(),
            end_qtime.hour(), end_qtime.minute(), end_qtime.second(),
            tzinfo=ZoneInfo('America/Los_Angeles')
        )
        
        # Validate start < end
        if start_time >= end_time:
            self._show_error("Invalid Time Range", 
                           "Start time must be before end time")
            return
        
        # Update test_config.py
        try:
            self._update_test_config(test_name, start_time, end_time)
        except Exception as e:
            self._show_error("Error Updating Config", 
                           f"Failed to update test_config.py:\n{e}")
            return
        
        # Emit signal and close
        self.export_requested.emit()
        self.accept()
    
    def _update_test_config(self, test_name, start_time, end_time):
        """Update test_config.py with new values"""
        # Path: widgets/ -> gui/ -> MK1_AWE/ -> data/test_config.py
        config_path = Path(__file__).parent.parent.parent / "data" / "test_config.py"
        
        # Read current file
        with open(config_path, 'r') as f:
            lines = f.readlines()
        
        # Find and update lines
        for i, line in enumerate(lines):
            if line.strip().startswith('TEST_NAME ='):
                lines[i] = f'TEST_NAME = "{test_name}"\n'
            elif line.strip().startswith('START_TIME = datetime('):
                # Format: datetime(2025, 11, 17, 12, 41, 30, tzinfo=ZoneInfo('America/Los_Angeles'))
                lines[i] = (f'START_TIME = datetime({start_time.year}, {start_time.month}, '
                          f'{start_time.day}, {start_time.hour}, {start_time.minute}, '
                          f'{start_time.second}, tzinfo=ZoneInfo(\'America/Los_Angeles\'))\n')
            elif line.strip().startswith('STOP_TIME = datetime('):
                lines[i] = (f'STOP_TIME = datetime({end_time.year}, {end_time.month}, '
                          f'{end_time.day}, {end_time.hour}, {end_time.minute}, '
                          f'{end_time.second}, tzinfo=ZoneInfo(\'America/Los_Angeles\'))\n')
        
        # Write back
        with open(config_path, 'w') as f:
            f.writelines(lines)
        
        print(f"Updated test_config.py:")
        print(f"  Test: {test_name}")
        print(f"  Start: {start_time.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        print(f"  End: {end_time.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    
    def _show_error(self, title, message):
        """Show styled error dialog"""
        msg = QMessageBox(self)
        msg.setWindowTitle(title)
        msg.setText(message)
        msg.setIcon(QMessageBox.Warning)
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

