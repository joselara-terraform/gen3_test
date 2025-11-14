# Gen3 AWE Electrolyzer Control System

## Overview

Comprehensive data acquisition, monitoring, and control system for an electrolyzer test station. The system provides:
- **Monitoring**: High-frequency data collection via Telegraf → InfluxDB → Grafana
- **Visualization**: Real-time dashboards for temperatures, pressures, currents, relay states
- **Control**: Python GUI for safe, intuitive hardware control on Windows

This is an adaptation of the MK1_AWE system, migrated from Linux + Waveshare PoE modules to Windows + National Instruments cDAQ hardware.

## System Architecture

### Hardware Platform
- **Host**: Windows 10/11 control computer (brand new setup)
- **Network**: Ethernet for NI cDAQ-9187
- **USB Devices**: Pico TC-08 thermocouple logger, PSU Modbus adapter

### Hardware Components

| Device | Connection | Protocol | Description |
|--------|------------|----------|-------------|
| **NI cDAQ-9187** | Ethernet | NI-DAQmx | Compact DAQ chassis (8 slots) |
| ├─ **NI-9253** (Slot 1) | - | NI-DAQmx | 4-channel analog current input (4-20mA) |
| ├─ **NI-9253** (Slot 2) | - | NI-DAQmx | 4-channel analog current input (4-20mA) |
| ├─ **NI-9485** (Slot 3) | - | NI-DAQmx | 8-channel relay output (24V, 50mA max) |
| └─ **NI-9485** (Slot 4) | - | NI-DAQmx | 8-channel relay output (24V, 50mA max) |
| **Pico TC-08** | USB | Pico SDK | 8-channel thermocouple logger (K, J, T types) |
| **PSU** | USB (RS485) | Modbus RTU | Single power supply unit |

**Total I/O:**
- 8 analog inputs (4-20mA sensors: pressure, flow, current, etc.)
- 16 relay outputs (valves, pumps, contactors)
- 8 thermocouple inputs (K-type or other)
- 1 PSU (voltage, current, power control)

### Software Stack

**Monitoring Pipeline**
```
Hardware → Python Bridges → Telegraf → InfluxDB → Grafana
   ↓            ↓              ↓
NI-DAQmx    HTTP /metrics   (10-100Hz sampling)
Pico SDK
Modbus RTU
```

**Control Layer**
```
Python GUI → NI-DAQmx (relays via nidaqmx library)
          → Modbus RTU (PSU via pymodbus + pyserial)
```

**Configuration**
- Single source of truth: `Gen3_AWE/config/devices.yaml`
- All connection details, channels, sensor scaling, and parameters defined centrally

## Quick Start

### Prerequisites
- Windows 10/11 (fresh install assumed)
- Docker Desktop for Windows installed
- Python 3.11+ installed
- NI-DAQmx drivers installed
- Pico SDK and drivers installed
- Git for Windows

### 1. Setup Environment

**Install Docker Desktop:**
```powershell
# Download from https://www.docker.com/products/docker-desktop
# Enable WSL2 backend during installation
# Verify installation:
docker --version
docker compose version
```

**Install Python:**
```powershell
# Download from https://www.python.org/downloads/
# Check "Add Python to PATH" during installation
python --version
pip --version
```

**Create virtual environment:**
```powershell
cd path\to\gen3_test
python -m venv venv
venv\Scripts\activate
pip install -r Gen3_AWE\gui\requirements.txt
```

### 2. Start Monitoring Stack
```powershell
cd path\to\gen3_test
docker compose up -d
```

### 3. Start Hardware Bridges
```powershell
# Activate virtual environment
venv\Scripts\activate

# Start NI analog input bridge (terminal 1)
python Gen3_AWE\hdw\ni_analog_http.py

# Start Pico TC-08 bridge (terminal 2)
python Gen3_AWE\hdw\pico_tc08_http.py

# Optional: Start PSU monitoring bridge (terminal 3)
python Gen3_AWE\hdw\psu_http.py
```

**Or run as background services using NSSM (recommended for production):**
```powershell
# Install NSSM (Non-Sucking Service Manager)
# Download from https://nssm.cc/

# Install services
nssm install Gen3_NI_Analog "C:\path\to\venv\Scripts\python.exe" "C:\path\to\Gen3_AWE\hdw\ni_analog_http.py"
nssm install Gen3_Pico_TC08 "C:\path\to\venv\Scripts\python.exe" "C:\path\to\Gen3_AWE\hdw\pico_tc08_http.py"

# Start services
nssm start Gen3_NI_Analog
nssm start Gen3_Pico_TC08
```

### 4. Launch Control GUI
```powershell
venv\Scripts\activate
python Gen3_AWE\gui\app.py
```

### 5. Access Dashboards
- **Grafana**: http://localhost:3000 (default login: admin/admin)
- **InfluxDB**: http://localhost:8086

## Control GUI

### Layout
```
┌─────────────────────────────────────────────────────┐
│  Hardware Status      │  PSU Settings               │
│  - NI cDAQ (Analog)   │  V: [____]  V               │
│  - NI cDAQ (Relay)    │  I: [____]  A               │
│  - Pico TC-08         │  P: [____]  W  (read-only)  │
│  - PSU                │                             │
│                       │  [ENTER] [STOP]             │
│                       │  [RAMP]  [PROFILE]          │
├─────────────────────────────────────────────────────┤
│  Relay Controls (16 channels)                       │
│  [Relay 1 ] [Relay 2 ] [Relay 3 ] [Relay 4 ]        │
│  [Relay 5 ] [Relay 6 ] [Relay 7 ] [Relay 8 ]        │
│  [Relay 9 ] [Relay 10] [Relay 11] [Relay 12]        │
│  [Relay 13] [Relay 14] [Relay 15] [Relay 16]        │
└─────────────────────────────────────────────────────┘
```

### Controls

**Hardware Status Indicators**
- Color-coded status (Green=Online, Red=Offline, Gray=Unknown)
- Auto-refresh every 5 seconds
- Shows individual status for:
  - NI cDAQ analog modules (2x NI-9253)
  - NI cDAQ relay modules (2x NI-9485)
  - Pico TC-08 thermocouple logger
  - PSU Modbus connection

**Relay Controls** (16 channels: 2x NI-9485)
- Toggle buttons: Gray=OFF, Green=ON
- Disabled (dashed border) when NI cDAQ offline
- Individual control of each relay
- Custom naming from `devices.yaml` → `modules.NI_cDAQ.relays`
- Can be grouped by function (Valves, Pumps, Contactors, etc.)

**PSU Settings**
- Input fields: **Voltage (V)**, **Current (A)**
- Display field: **Power (W)** - calculated or read from PSU
- Buttons:
  - **Enter**: Apply voltage and current setpoints
  - **Stop**: Disable PSU output (safe state)
  - **Ramp**: Linear ramp to target current over time
  - **Profile**: Execute current profile from CSV file
- Disabled when PSU offline
- Safety limits enforced from `devices.yaml`

### Safety Features

**Auto-Enable/Disable**
- Controls only enabled when required hardware is online
- Automatically disable if hardware disconnects mid-operation
- Disconnect alerts show popup notification

**Safe State Enforcement**
- **Startup**: When hardware first connects
  - All relays → OFF
  - PSU → Disabled, 0V/0A
- **Shutdown**: When closing GUI
  - PSU → Ramp to 0A, wait, then disable
  - All relays → OFF (after PSU safe state)
- **Emergency Stop**: Stop button or profile interrupt
  - PSU → Immediate 0A command, then disable
  - Relays remain in current state (manual control)

**Error Handling**
- Non-blocking operations - UI never freezes
- Graceful degradation on hardware failures
- Console logging for diagnostics
- Timeout handling for all hardware communication

## Dependencies

### Windows Host

**System Software:**
- Windows 10/11 (Pro or Enterprise recommended for Docker)
- Docker Desktop for Windows (with WSL2)
- Python 3.11 or later
- NI-DAQmx drivers (2023 Q3 or later)
- Pico SDK (latest from picotech.com)
- Git for Windows

**Python Libraries:**
```powershell
pip install PySide6 pymodbus pyserial pyyaml influxdb-client nidaqmx picosdk
```

Or install from requirements:
```powershell
pip install -r Gen3_AWE\gui\requirements.txt
```

**Optional:**
- NSSM (Non-Sucking Service Manager) for running bridges as services
- Visual Studio Code or PyCharm for development

## Configuration

### Single Source of Truth: `devices.yaml`

All hardware configuration lives in `Gen3_AWE/config/devices.yaml`:
- NI cDAQ connection details (IP, device name)
- NI module slot assignments (which modules in which slots)
- Analog input channel mappings (4-20mA sensor scaling)
- Relay channel names and groupings
- Pico TC-08 configuration (thermocouple types, channel names)
- PSU connection (COM port, baud rate, register map)
- System parameters (InfluxDB, Grafana)

**Example Gen3 relay configuration:**
```yaml
modules:
  NI_cDAQ:
    relays:
      slot_3:  # First NI-9485
        ch0: {name: "Contactor", type: "safety"}
        ch1: {name: "Valve 1", type: "valve"}
        ch2: {name: "Valve 2", type: "valve"}
        # ... up to ch7
      slot_4:  # Second NI-9485
        ch0: {name: "Pump 1", type: "pump"}
        # ... up to ch7
```

**Example analog input configuration:**
```yaml
modules:
  NI_cDAQ:
    analog_inputs:
      slot_1:  # First NI-9253
        ai0:
          name: "H2 Pressure"
          sensor_type: "pressure"
          range_min: 4.0   # 4mA
          range_max: 20.0  # 20mA
          eng_min: 0.0     # 0 PSI
          eng_max: 100.0   # 100 PSI
          eng_unit: "PSI"
```

## Hardware Bridge Integration

### Architecture
```
Hardware → Python Bridge → HTTP Server → Telegraf → InfluxDB
   ↓            ↓              ↓
NI-DAQmx    Read loop      /metrics
Pico SDK    (10-100Hz)
Modbus RTU
```

### HTTP Bridges

**NI Analog Bridge** (`ni_analog_http.py`):
- Port: `http://localhost:8881`
- Endpoints:
  - `GET /metrics` - Latest analog data in InfluxDB line protocol
  - `GET /health` - Bridge status
- Data: 8 analog inputs with 4-20mA to engineering unit conversion
- Sampling rate: 10-100Hz (configurable)

**Pico TC-08 Bridge** (`pico_tc08_http.py`):
- Port: `http://localhost:8882`
- Endpoints:
  - `GET /metrics` - Latest thermocouple data
  - `GET /health` - Bridge status
- Data: 8 thermocouple channels (K, J, T types)
- Sampling rate: 1Hz (hardware limitation)

**PSU Bridge** (`psu_http.py`, optional):
- Port: `http://localhost:8883`
- Endpoints:
  - `GET /metrics` - PSU V/I/P/status
  - `GET /health` - Bridge status
- Data: Voltage, current, power, status
- Sampling rate: 1Hz

### Running Bridges as Windows Services

**Using NSSM (recommended):**
```powershell
# Install NSSM from https://nssm.cc/

# Install services
nssm install Gen3_NI_Analog "C:\path\to\venv\Scripts\python.exe"
nssm set Gen3_NI_Analog AppDirectory "C:\path\to\Gen3_AWE\hdw"
nssm set Gen3_NI_Analog AppParameters "ni_analog_http.py"

# Configure auto-restart
nssm set Gen3_NI_Analog AppExit Default Restart
nssm set Gen3_NI_Analog AppRestartDelay 1000

# Start service
nssm start Gen3_NI_Analog

# Check status
nssm status Gen3_NI_Analog

# View logs
nssm get Gen3_NI_Analog AppStdout
```

**Using Task Scheduler (alternative):**
- Open Task Scheduler
- Create Basic Task
- Trigger: At system startup
- Action: Start a program
- Program: `C:\path\to\venv\Scripts\python.exe`
- Arguments: `C:\path\to\Gen3_AWE\hdw\ni_analog_http.py`
- Configure "Restart if task fails"

## Common Operations

### Check System Health

**Docker services:**
```powershell
docker compose ps
docker compose logs --tail 50 telegraf
```

**Hardware bridges:**
```powershell
# Check if bridges are responding
curl http://localhost:8881/health   # NI analog
curl http://localhost:8882/health   # Pico TC-08
curl http://localhost:8883/health   # PSU (optional)

# View latest data
curl http://localhost:8881/metrics
curl http://localhost:8882/metrics
```

**NI hardware (using NI MAX):**
- Open NI Measurement & Automation Explorer
- Devices and Interfaces → Network Devices
- Verify cDAQ-9187 is detected
- Test modules in each slot

**Pico TC-08:**
```powershell
# Check Device Manager
devmgmt.msc
# Look under "Universal Serial Bus devices" for "Pico TC-08"
```

**PSU Modbus:**
```python
# Quick test script
python -c "from pymodbus.client import ModbusSerialClient; 
           c = ModbusSerialClient(port='COM3', baudrate=9600); 
           c.connect(); 
           print('Connected' if c.connected else 'Failed'); 
           c.close()"
```

### Restart Services

**Monitoring stack:**
```powershell
docker compose restart telegraf
docker compose restart influxdb
docker compose restart grafana
```

**Hardware bridges (NSSM):**
```powershell
nssm restart Gen3_NI_Analog
nssm restart Gen3_Pico_TC08
nssm restart Gen3_PSU
```

**Hardware bridges (manual):**
```powershell
# Stop: Ctrl+C in terminal running the bridge
# Start:
venv\Scripts\activate
python Gen3_AWE\hdw\ni_analog_http.py
```

**Control GUI:**
```powershell
# Just close and relaunch
venv\Scripts\activate
python Gen3_AWE\gui\app.py
```

### Send Manual Commands

**Relay Control (via NI-DAQmx):**
```python
from Gen3_AWE.gui.ni_relay_client import set_relay
set_relay(slot=3, channel=0, state=True)   # Slot 3, Ch0 ON
set_relay(slot=3, channel=0, state=False)  # Slot 3, Ch0 OFF
```

**PSU Control (via Modbus RTU):**
```python
from Gen3_AWE.gui.psu_rtu_client import PSUClient
psu = PSUClient(port='COM3', baudrate=9600, slave_id=1)
psu.set_voltage(50.0)    # Set 50V
psu.set_current(10.0)    # Set 10A
psu.enable_output()      # Enable output
psu.disable_output()     # Disable output
```

## Troubleshooting

### Docker Desktop Issues
**Problem**: Docker won't start
- Verify WSL2 is installed: `wsl --list --verbose`
- Update WSL2 kernel: `wsl --update`
- Enable virtualization in BIOS (Intel VT-x or AMD-V)
- Restart computer after Docker installation

**Problem**: Docker containers crash
- Increase memory allocation: Docker Desktop → Settings → Resources
- Check Windows Firewall isn't blocking Docker

### NI cDAQ Issues
**Problem**: cDAQ not detected
- Verify Ethernet cable connected
- Check NI MAX (Measurement & Automation Explorer)
- Verify NI-DAQmx drivers installed (run NI Package Manager)
- Try different Ethernet adapter or port
- Reset cDAQ: power cycle the device

**Problem**: "Device not found" error in Python
```python
# List all NI devices
import nidaqmx.system
system = nidaqmx.system.System.local()
for device in system.devices:
    print(device.name)
```
- If empty, check NI MAX first
- Verify device name matches `devices.yaml`

**Problem**: Relay clicks but doesn't stay on
- Check relay module wiring (24V supply, load connections)
- Verify load is within NI-9485 specs (60VDC, 50mA max)
- Check for grounding issues

### Pico TC-08 Issues
**Problem**: TC-08 not detected
- Check Device Manager for "Pico TC-08"
- If missing, reinstall Pico SDK drivers
- Try different USB port (use USB 2.0, not USB 3.0 if issues persist)
- Check USB cable (data cable, not charge-only)

**Problem**: "PicoStatus: PICO_NOT_FOUND"
```python
# Test Pico connection
from picosdk.usbtc08 import usbtc08
handle = usbtc08.usb_tc08_open_unit()
print(f"Handle: {handle}")  # Should be > 0
```

**Problem**: Thermocouple reads -999 or invalid
- Check thermocouple is connected (not open circuit)
- Verify thermocouple type matches configuration (K, J, T, etc.)
- Check cold junction compensation is enabled
- Inspect thermocouple for damage

### PSU Modbus Issues
**Problem**: PSU not responding
- Check COM port in Device Manager
- Verify correct baud rate, parity, stop bits
- Test with Modbus poll software first
- Check RS485 adapter polarity (A/B or +/-)

```python
# List available COM ports
import serial.tools.list_ports
ports = serial.tools.list_ports.comports()
for port in ports:
    print(f"{port.device}: {port.description}")
```

**Problem**: "Modbus Error: Slave device did not respond"
- Verify slave ID matches PSU configuration
- Check cable wiring (RS485 needs twisted pair)
- Reduce baud rate (try 9600 instead of 19200)
- Check for bus termination if multiple devices

### Controls Disabled in GUI
- Controls auto-enable when hardware connects
- Check hardware status indicators in GUI (should be green)
- Wait up to 5 seconds for status refresh
- Verify device in diagnostic tools (NI MAX, Device Manager)

### Telegraf Not Receiving Data
```powershell
# Check Telegraf logs
docker compose logs --tail 100 telegraf

# Verify hardware bridges
curl http://localhost:8881/metrics
curl http://localhost:8882/metrics

# Check Telegraf can reach bridges
docker exec -it telegraf curl http://host.docker.internal:8881/metrics
```

**Problem**: "connection refused" in Telegraf logs
- Verify bridges are running (`curl` commands above)
- Check Windows Firewall allows Docker to access localhost
- Use `host.docker.internal` instead of `localhost` in `telegraf.conf`

### InfluxDB Issues
**Problem**: Data not appearing in Grafana
- Verify bucket name matches in Telegraf and Grafana
- Check InfluxDB token has write permissions
- Query InfluxDB directly via UI: Data Explorer
- Check measurement names: `ni_analog`, `tc08`, `psu`

**Problem**: Type conflicts (e.g., "field type conflict")
- InfluxDB is strict about field types (float vs int vs string)
- Delete and recreate measurement if type changed
- Use different measurement names for incompatible data

### Windows-Specific Issues
**Problem**: Python not found
- Verify Python added to PATH: `python --version` in Command Prompt
- Restart terminal after Python installation
- Use `py` launcher if `python` doesn't work

**Problem**: Virtual environment activation fails
```powershell
# If execution policy error:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
# Then try again:
venv\Scripts\activate
```

**Problem**: Module import errors after pip install
- Verify virtual environment is activated (prompt shows `(venv)`)
- Reinstall: `pip install --force-reinstall <package>`
- Check for conflicting installations: `pip list`

## Architecture Details

See `architecture.md` for:
- Complete system architecture
- Component responsibilities
- Data flow diagrams
- Safety & state management
- Windows-specific considerations
- Future work items

## Development

### Project Structure
```
Gen3_AWE/
├── config/
│   ├── devices.yaml      # Hardware configuration (single source of truth)
│   ├── telegraf.conf     # Telegraf input/output definitions
│   └── grafana.ini       # Grafana overrides
├── grafana/
│   └── queries.flux      # Reference Flux queries
├── hdw/
│   ├── ni_analog_http.py    # NI cDAQ analog input bridge
│   ├── pico_tc08_http.py    # Pico TC-08 thermocouple bridge
│   └── psu_http.py          # PSU monitoring bridge (optional)
├── gui/
│   ├── app.py               # GUI entrypoint
│   ├── main_window.py       # Main window layout
│   ├── config_loader.py     # YAML config parser
│   ├── ni_relay_client.py   # NI-DAQmx relay control
│   ├── psu_rtu_client.py    # PSU Modbus RTU client
│   └── widgets/
│       ├── hw_status.py     # Hardware status indicators
│       ├── relay_panel.py   # Relay controls (16 channels)
│       └── psu_panel.py     # PSU settings (V/I control)
├── data/
│   ├── export_csv.py        # InfluxDB to CSV export
│   ├── plot_data.py         # Generate plots from test data
│   └── process_test.py      # Post-test analysis pipeline
└── profiles/
    ├── solar_profile_1.csv  # Example current profile
    └── README.md            # Profile format documentation
```

### Adding New Sensors or Relays

**Add analog input sensor:**
1. Edit `Gen3_AWE/config/devices.yaml`
2. Add sensor under `modules.NI_cDAQ.analog_inputs.slot_X`:
   ```yaml
   ai4:
     name: "Coolant Temperature"
     sensor_type: "temperature"
     range_min: 4.0
     range_max: 20.0
     eng_min: 0.0
     eng_max: 100.0
     eng_unit: "°C"
   ```
3. Restart NI analog bridge - new sensor auto-discovered

**Add relay:**
1. Edit `Gen3_AWE/config/devices.yaml`
2. Add relay under `modules.NI_cDAQ.relays.slot_X`:
   ```yaml
   ch5:
     name: "My New Valve"
     type: "valve"
   ```
3. Restart GUI - new relay appears automatically

### Key Files
- `devices.yaml` - All hardware config
- `docker-compose.yml` - Container orchestration
- `telegraf.conf` - Data collection pipeline
- `queries.flux` - Dashboard query examples

### Hardware Test Scripts
The `tests/` directory contains validation scripts:
- NI cDAQ connectivity tests
- Pico TC-08 read tests
- PSU Modbus RTU tests
- Run these before integrating into main system

## Migration from MK1

Key differences when porting code from MK1_AWE:
- Replace Modbus TCP with NI-DAQmx for relays
- Replace Modbus TCP with NI-DAQmx for analog inputs
- Replace Modbus TCP thermocouples with Pico SDK
- Replace 10-PSU parallel control with single PSU
- Change service management from systemd to NSSM or Task Scheduler
- Update paths from Unix (`/`) to Windows (`\`)
- Replace `sudo` commands with Administrator privileges

## Future Work

### Hardware Additions
- Add more NI modules to cDAQ chassis (available slots)
- Multiple PSU support (daisy-chain via RS485)
- Add video camera integration for test observation
- Add audio alarms for critical events

### Software Improvements
- Auto-generate `telegraf.conf` from `devices.yaml`
- Web-based GUI (Flask/FastAPI + React)
- Mobile app for remote monitoring
- Automated report generation (PDF with plots)
- Machine learning for anomaly detection

### Safety & Reliability
- Watchdog timer for bridge processes
- Redundant sensor validation (cross-check multiple sensors)
- Automated backup of InfluxDB data
- UPS integration for graceful shutdown on power loss

---

**For detailed architecture, see `architecture.md`**  
**For development tasks and roadmap, see `tasks.md`**
