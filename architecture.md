## Gen3 AWE System Architecture

### Purpose
Logging, visualization, and control for an electrolyzer test station using National Instruments cDAQ hardware on Windows. This is an adaptation of the MK1_AWE system (Linux + Waveshare modules) to Windows + NI hardware platform. The monitoring pipeline (Telegraf → InfluxDB → Grafana) remains the same, but hardware interfaces are completely redesigned for NI-DAQmx, Pico SDK, and Modbus RTU.

### High-Level Diagram
```
Hardware Layer:
  - NI cDAQ-9187 (Ethernet) → NI-DAQmx drivers
    - 2x NI-9253 (analog current input, 4-20mA)
    - 2x NI-9485 (relay outputs)
  - Pico TC-08 (USB) → Pico SDK
  - PSU (USB RS485) → Modbus RTU

Bridge Layer (Python):
  - ni_analog_http.py → HTTP server (port 8881)
  - pico_tc08_http.py → HTTP server (port 8882)
  - psu_http.py → HTTP server (port 8883, optional)

Monitoring Pipeline:
  - HTTP Bridges → Telegraf (HTTP inputs) → InfluxDB → Grafana

Control Layer (Python GUI):
  - NI-DAQmx library (direct relay control)
  - pymodbus + pyserial (direct PSU control via Modbus RTU)

Configuration:
  - Single source of truth: Gen3_AWE/config/devices.yaml
```

### Repository Structure
- `docker-compose.yml`
  - Orchestrates InfluxDB, Telegraf, Grafana containers on Windows (Docker Desktop with WSL2).
  - Binds Telegraf and Grafana configs from the repo into containers.
- `Gen3_AWE/`
  - `config/`
    - `devices.yaml`: Canonical hardware and system configuration. All NI cDAQ settings, Pico TC-08 config, PSU parameters, sensor scaling, relay naming.
    - `telegraf.conf`: Telegraf pipeline definition for HTTP inputs (NI analog, Pico TC-08, PSU); outputs to InfluxDB.
    - `grafana.ini`: Optional Grafana overrides.
  - `grafana/`
    - `queries.flux`: Reference Flux queries for Gen3 measurements.
  - `hdw/`
    - `ni_analog_http.py`: HTTP bridge for NI-9253 analog inputs (8 channels, 4-20mA sensors).
    - `pico_tc08_http.py`: HTTP bridge for Pico TC-08 thermocouples (8 channels).
    - `psu_http.py`: HTTP bridge for PSU monitoring (optional, V/I/P/status).
  - `gui/`
    - `app.py`: GUI entrypoint.
    - `main_window.py`: Main window layout.
    - `config_loader.py`: YAML parser for devices.yaml.
    - `ni_relay_client.py`: NI-DAQmx relay control client.
    - `psu_rtu_client.py`: Modbus RTU PSU control client.
    - `widgets/`: GUI components (hardware status, relay panel, PSU panel).
  - `data/`
    - `export_csv.py`: Export data from InfluxDB to CSV.
    - `plot_data.py`: Generate plots from test data.
    - `process_test.py`: Post-test analysis pipeline.
  - `profiles/`
    - Current profile CSV files for PSU control.
- `tests/`
  - Hardware validation scripts (NI cDAQ, Pico TC-08, PSU Modbus).
- `README.md`
  - Project overview, Windows setup, hardware table, quick start, troubleshooting.
- `architecture.md` (this document)
- `tasks.md`
  - Development roadmap and task tracking.

### Services and Responsibilities

**InfluxDB (Docker)**
- Storage for all telemetry in bucket `electrolyzer_data` (org `electrolyzer`).
- Accessible at `http://localhost:8086`
- Runs in WSL2 backend via Docker Desktop for Windows

**Telegraf (Docker)**
- Inputs:
  - HTTP: NI analog via `http://host.docker.internal:8881/metrics` (or `localhost:8881` on host)
  - HTTP: Pico TC-08 via `http://host.docker.internal:8882/metrics`
  - HTTP: PSU (optional) via `http://host.docker.internal:8883/metrics`
  - System: CPU/MEM/Disk metrics from Windows host
- Processing: Parse InfluxDB line protocol from HTTP bridges
- Output: Writes to InfluxDB v2 using admin token
- Note: Use `host.docker.internal` in `telegraf.conf` to access host services from Docker container on Windows

**Grafana (Docker)**
- Dashboards and panels reading directly from InfluxDB
- Accessible at `http://localhost:3000`
- Default login: admin/admin (change on first login)

**Hardware Bridges (Windows Services via NSSM or Task Scheduler)**

*NI Analog Bridge* (`ni_analog_http.py`):
- Port: 8881
- Reads 8 analog inputs (4-20mA) from 2x NI-9253 modules
- Sample rate: 10-100Hz (configurable)
- Sensor scaling: 4-20mA → engineering units via `devices.yaml`
- Endpoints:
  - `GET /metrics` - Latest data in InfluxDB line protocol
  - `GET /health` - Bridge status

*Pico TC-08 Bridge* (`pico_tc08_http.py`):
- Port: 8882
- Reads 8 thermocouple channels from Pico TC-08 USB device
- Sample rate: 1Hz (hardware limitation)
- Thermocouple types: K, J, T, E, R, S, B, N (configurable per channel)
- Endpoints:
  - `GET /metrics` - Latest data in InfluxDB line protocol
  - `GET /health` - Bridge status

*PSU Bridge* (`psu_http.py`, optional):
- Port: 8883
- Reads PSU V/I/P/status via Modbus RTU (USB RS485 adapter)
- Sample rate: 1Hz
- Endpoints:
  - `GET /metrics` - Latest data in InfluxDB line protocol
  - `GET /health` - Bridge status

**Control GUI (Windows application)**
- Direct hardware control (no bridge required):
  - NI relays: via `nidaqmx` library (Python wrapper for NI-DAQmx)
  - PSU: via `pymodbus` + `pyserial` (Modbus RTU over USB)
- Safe state management (startup, shutdown, emergency stop)
- Profile execution (CSV-based current profiles)
- Hardware status monitoring

### Single Source of Truth: `devices.yaml`

**`devices` section: Hardware connection details**
- `NI_cDAQ`:
  - Device name (e.g., "cDAQ1")
  - IP address or connection string
  - Module slot assignments (Slot 1-8)
- `Pico_TC08`:
  - USB device serial number (for consistent COM port mapping)
  - Thermocouple types per channel (K, J, T, etc.)
- `PSU`:
  - COM port (e.g., "COM3")
  - Baud rate, parity, stop bits
  - Modbus slave ID
  - Register map (voltage, current, enable, status)

**`modules` section: Logical channel mappings**
- `NI_cDAQ.analog_inputs`:
  - Slot and channel assignments (e.g., slot_1/ai0, slot_1/ai1, ...)
  - Per-channel sensor configuration:
    - Sensor name (e.g., "H2 Pressure")
    - Sensor type (pressure, flow, current, etc.)
    - 4-20mA range mapping to engineering units
    - Engineering unit label (PSI, L/min, A, etc.)
- `NI_cDAQ.relays`:
  - Slot and channel assignments (e.g., slot_3/ch0, slot_3/ch1, ...)
  - Per-relay configuration:
    - Relay name (e.g., "Contactor", "Valve 1")
    - Relay type (safety, valve, pump)
- `Pico_TC08.channels`:
  - Channel 1-8 assignments
  - Thermocouple names (e.g., "Stack Temperature", "Ambient")
  - Thermocouple types (K, J, T)

**`system` section: Infrastructure**
- InfluxDB and Grafana URLs
- Organization and bucket names
- Bridge HTTP ports

**`telegraf.agent` section: Monitoring parameters**
- Global sampling intervals
- Buffering and batching settings

### Data Model and Measurements

**NI Analog Inputs**
- Measurement: `ni_analog`
- Tags:
  - `device` = "cDAQ1" (or configured device name)
  - `slot` = slot number (1, 2, etc.)
- Fields: `ai0`, `ai1`, ..., `ai7` (engineering units, e.g., PSI, L/min, A)
- Type: Float (post-conversion from 4-20mA)
- Sample rate: 10-100Hz (configurable)

**Pico TC-08 Thermocouples**
- Measurement: `tc08`
- Tags:
  - `device` = "TC08" or serial number
- Fields: `ch1`, `ch2`, ..., `ch8` (temperatures in °C)
- Type: Float
- Sample rate: 1Hz (hardware limitation)

**PSU (optional monitoring)**
- Measurement: `psu`
- Tags:
  - `device` = "PSU1" or configured name
- Fields:
  - `voltage` (V, float)
  - `current` (A, float)
  - `power` (W, float)
  - `status` (integer status code)
  - `enabled` (boolean)
- Type: Mixed (float for V/I/P, int for status, bool for enabled)
- Sample rate: 1Hz

**NI Relay States (optional monitoring)**
- Measurement: `ni_relays`
- Tags:
  - `device` = "cDAQ1"
  - `slot` = slot number
- Fields: `ch0`, `ch1`, ..., `ch7` (boolean, true=ON, false=OFF)
- Type: Boolean
- Note: Typically not monitored (write-only control), but can be polled if needed

### Connectivity and Failure Modes

**Hardware Bridges:**
- Bridges auto-reconnect to hardware on disconnection with exponential backoff
- `GET /metrics` returns 503 if hardware unavailable
- Bridge continues running even if hardware offline (waits for reconnection)

**Telegraf:**
- Resilient to bridge outages; missing endpoints yield data gaps without crashing
- HTTP input timeout: 5 seconds
- Retry on connection refused: No (just logs error and continues)

**Grafana:**
- Remains operational regardless of hardware/bridge connectivity
- Shows "No data" for missing time ranges

**Control GUI:**
- Must initialize without live hardware (show all controls as disabled)
- Degrade gracefully if devices disconnect mid-run
- Background health checks every 5 seconds
- Auto-enable controls when hardware comes online
- Disable controls and show alert if hardware lost during operation

**Windows-Specific Considerations:**
- Docker Desktop must be running for InfluxDB/Telegraf/Grafana
- WSL2 backend provides near-native Linux container performance
- Use `host.docker.internal` in container configs to reach Windows host services
- USB devices (Pico TC-08, PSU) may change COM ports on reboot; use device serial numbers or fixed port assignment
- Windows Firewall may block Docker → host communication; add exceptions
- NSSM or Task Scheduler for running bridges as services (no systemd on Windows)

### Control GUI Architecture

**Goals:**
- Single-window view (no tabs) showing all controls simultaneously
- Relay control: 16 relays (2x NI-9485) with labeled ON/OFF toggle buttons
- PSU control: Voltage/Current input + Enter/Stop/Ramp/Profile buttons
- Hardware status indicators: NI cDAQ (Analog), NI cDAQ (Relay), Pico TC-08, PSU
- Windows native application (no SSH/X11 required)

**Layout (top to bottom):**
- Top row (left to right):
  - Left: Hardware status indicators (vertical list)
    - NI cDAQ (Analog): Green=Online, Red=Offline
    - NI cDAQ (Relay): Green=Online, Red=Offline
    - Pico TC-08: Green=Online, Red=Offline
    - PSU: Green=Online, Red=Offline
  - Right: PSU panel
    - Voltage (V) input field
    - Current (A) input field
    - Power (W) display field (read-only)
    - Enter/Stop/Ramp/Profile buttons
- Bottom: Relay panel
  - 16 relay toggle buttons in 4x4 grid (or custom grouping)
  - Labels from `devices.yaml` (e.g., "Contactor", "Valve 1", "Pump 1")
  - Color: Gray=OFF, Green=ON, Dashed border=Disabled

**Components:**
- `Gen3_AWE/gui/`
  - `app.py`: GUI entrypoint
  - `main_window.py`: Main window layout manager (PySide6)
  - `config_loader.py`: YAML parser for `devices.yaml`
  - `ni_relay_client.py`: NI-DAQmx relay control client
  - `psu_rtu_client.py`: Modbus RTU PSU control client
  - `widgets/`
    - `hw_status.py`: Hardware status indicators
    - `relay_panel.py`: Relay toggle buttons (16 channels)
    - `psu_panel.py`: PSU control panel (V/I/P, Enter/Stop/Ramp/Profile)

**State Management:**
- Configuration: Parsed from `devices.yaml` at startup, immutable
- Hardware state: Only tracked for enable/disable logic (not displayed in GUI)
- Monitoring: All real-time data visualization happens in Grafana, not GUI
- GUI is primarily write-only (send commands to hardware)

**Data Flows:**
- NI relays: GUI → `nidaqmx.Task` → NI-DAQmx driver → cDAQ-9187 → NI-9485
- PSU: GUI → `pymodbus.ModbusSerialClient` → USB RS485 adapter → PSU

**Safety & State Management:**
- **Hardware-dependent enabling**: Controls disabled until hardware online
- **Safe startup**: All relays OFF, PSU disabled (0V/0A)
- **Safe shutdown**: PSU → 0A (ramp down), wait, disable; then relays OFF
- **Emergency stop**: PSU → immediate 0A + disable; relays unchanged
- **Profile execution**: Non-blocking, timer-based, interruptible
- **Disconnect monitoring**: Background worker checks hardware every 5s

**Resilience:**
- All hardware operations wrapped with timeouts (5-10 seconds)
- UI thread separated from I/O via QThreads (PySide6)
- Exceptions caught and logged, controls disabled on error
- Controls remain disabled until hardware reconnects and safe state verified

### How Components Connect

**Docker Compose:**
- `docker-compose.yml` binds:
  - `Gen3_AWE/config/telegraf.conf` → Telegraf container
  - `Gen3_AWE/config/devices.yaml` → (Reference only, not directly used by Telegraf)
  - `Gen3_AWE/config/grafana.ini` → Grafana container
- Containers run in WSL2 via Docker Desktop for Windows
- Containers access host via `host.docker.internal` (Windows-specific hostname)

**Telegraf:**
- Connects to hardware bridges on Windows host:
  - `http://host.docker.internal:8881/metrics` (NI analog)
  - `http://host.docker.internal:8882/metrics` (Pico TC-08)
  - `http://host.docker.internal:8883/metrics` (PSU, optional)
- Writes to InfluxDB container via Docker internal network

**Grafana:**
- Connects to InfluxDB container via Docker internal network
- Accessible from Windows host at `http://localhost:3000`

**GUI:**
- Connects directly to hardware:
  - NI cDAQ: via NI-DAQmx library (Ethernet or USB, as configured)
  - PSU: via pymodbus + pyserial (USB RS485 adapter, e.g., COM3)
- Does NOT connect to hardware bridges (direct control only)
- Reads configuration from `Gen3_AWE/config/devices.yaml`

**Hardware Bridges:**
- Connect to hardware:
  - NI analog bridge: via `nidaqmx` library
  - Pico TC-08 bridge: via `picosdk` library (USB)
  - PSU bridge: via `pymodbus` + `pyserial` (USB)
- Expose HTTP endpoints on localhost (8881, 8882, 8883)
- Run as Windows services (NSSM) or manually in terminals

### Operational Notes

**System Bring-Up:**
1. Start Docker Desktop (auto-start on Windows boot recommended)
2. Launch Docker stack: `docker compose up -d`
3. Start hardware bridges (NSSM services or manual)
4. Launch Control GUI: `venv\Scripts\activate && python Gen3_AWE\gui\app.py`
5. Access Grafana: `http://localhost:3000`

**GUI Usage:**
- Controls auto-enable when hardware detected (green status indicators)
- Safe state enforced on startup (all OFF/disabled)
- Safe shutdown sequence on close (PSU → 0A, wait, disable; relays → OFF)
- Disconnect alerts if hardware lost during operation
- All monitoring via Grafana dashboards (GUI is control-only)

**Troubleshooting:**
- Check Docker Desktop is running: System tray icon
- Check Telegraf logs: `docker compose logs --tail 100 telegraf`
- Verify bridge endpoints: `curl http://localhost:8881/metrics`
- Check NI hardware: Open NI MAX, verify cDAQ-9187 detected
- Check Pico TC-08: Device Manager → Universal Serial Bus devices
- Check PSU COM port: Device Manager → Ports (COM & LPT)
- GUI console shows all control commands, errors, and hardware status

**Data Export:**
- Export CSV: `python Gen3_AWE\data\export_csv.py` (edit time range and fields)
- Generate plots: `python Gen3_AWE\data\plot_data.py`
- Full post-processing: `python Gen3_AWE\data\process_test.py`

### Future Work Items

**Phase 1 (Near-term):**
- Complete hardware bridge implementations (NI, Pico, PSU)
- Complete GUI implementation (relay panel, PSU panel, status indicators)
- Create Grafana dashboards for Gen3 measurements
- Test end-to-end: hardware → bridge → Telegraf → InfluxDB → Grafana

**Phase 2 (Medium-term):**
- Auto-generate `telegraf.conf` from `devices.yaml` to eliminate duplication
- Advanced safety interlocks (prevent dangerous relay/PSU combinations)
- Profile library (multiple profiles, profile editor GUI)
- Automated test sequencing (run multiple profiles back-to-back)
- Email/SMS alerts on critical events (overtemp, overpressure, PSU fault)

**Phase 3 (Long-term):**
- Web-based GUI (replace PySide6 with Flask/FastAPI + React)
- Mobile app for remote monitoring (iOS/Android)
- Automated report generation (PDF with plots, pass/fail criteria)
- Machine learning for anomaly detection (predict failures)
- Multi-site deployment (central monitoring for multiple test rigs)

**Hardware Expansion:**
- Add more NI modules to cDAQ chassis (slots 5-8 available)
- Multiple PSU support (RS485 daisy-chain, multiple slaves)
- Add video camera integration (USB or IP camera for visual test logs)
- Add audio alarms (PC speaker or external buzzer for critical alerts)
- UPS integration (monitor battery status, trigger safe shutdown on power loss)

**Software Quality:**
- Unit tests for all clients (mocked hardware)
- Integration tests with hardware simulator
- Automated acceptance tests (test profile execution, safe state enforcement)
- CI/CD pipeline (GitHub Actions for linting, testing, building)
- Code coverage reporting (pytest-cov)


