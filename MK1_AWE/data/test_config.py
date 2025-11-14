"""
Test Data Processing Configuration

EDIT THIS FILE to configure test parameters.
Sensor configurations are in MK1_AWE/config/devices.yaml (single source of truth).
Then run: python3 process_test.py
"""

from datetime import datetime
from zoneinfo import ZoneInfo
import sys
import os

# Add path to import config_loader
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'gui'))
from config_loader import get_sensor_conversions

# Test Info
TEST_NAME = "FWS_Test_4"

# Time Range (PST/PDT)
START_TIME = datetime(2025, 11, 5, 16, 0, 0, tzinfo=ZoneInfo('America/Los_Angeles'))
STOP_TIME = datetime(2025, 11, 5, 17, 50, 0, tzinfo=ZoneInfo('America/Los_Angeles'))

# Auto-convert to UTC
START_TIME_UTC = START_TIME.astimezone(ZoneInfo('UTC')).isoformat().replace('+00:00', 'Z')
STOP_TIME_UTC = STOP_TIME.astimezone(ZoneInfo('UTC')).isoformat().replace('+00:00', 'Z')

# Downsampling
DOWNSAMPLE_AIX = "250ms"
DOWNSAMPLE_TC = "1s"
DOWNSAMPLE_BGA = "1s"
DOWNSAMPLE_RL = "1s"
DOWNSAMPLE_CV = "1s"
DOWNSAMPLE_FUNCTION = "mean"  # mean, median, max, min, first, last

# Sensor Conversions (loaded from devices.yaml)
SENSOR_CONVERSIONS = get_sensor_conversions()

# Plots
PLOT_DPI = 300
PLOT_FORMAT = 'jpg'
FIGURE_SIZE = (12, 6)

