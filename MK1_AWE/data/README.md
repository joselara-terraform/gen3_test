# Data Export

This directory contains tools for exporting data from InfluxDB to CSV.

## Quick Start

### 1. Set your InfluxDB token
```bash
export INFLUXDB_ADMIN_TOKEN=your_token_here
```

Find your token in:
- Docker environment when you set up InfluxDB
- InfluxDB UI → Settings → Tokens
- Or check your docker-compose setup files

### 2. Edit export_csv.py configuration

Open `export_csv.py` and modify these variables:

```python
# Time Range
START_TIME = "2024-11-03T10:00:00Z"  # Your start time
STOP_TIME = "2024-11-03T12:00:00Z"   # Your end time

# Downsampling
DOWNSAMPLE_WINDOW = "1s"      # Window size: "10ms", "100ms", "1s", "10s", "1m"
DOWNSAMPLE_FUNCTION = "mean"  # Function: "mean", "median", "max", "min"

# Data Selection
MEASUREMENT = "analog_inputs"  # Measurement name
FIELD = "AI01"                # Field to export

# Output
OUTPUT_FILE = "export.csv"    # Output filename
```

### 3. Run export
```bash
python3 export_csv.py
```

Output appears in this directory.

## Examples

### Export AI01 at full 100Hz resolution (1 hour)
```python
DOWNSAMPLE_WINDOW = "10ms"  # Full resolution
START_TIME = "2024-11-03T10:00:00Z"
STOP_TIME = "2024-11-03T11:00:00Z"
# Result: ~360,000 points, ~15 MB
```

### Export AI01 downsampled to 1Hz (1 day)
```python
DOWNSAMPLE_WINDOW = "1s"
DOWNSAMPLE_FUNCTION = "mean"
START_TIME = "2024-11-03T00:00:00Z"
STOP_TIME = "2024-11-04T00:00:00Z"
# Result: ~86,400 points, ~3 MB
```

### Export TC01 temperature (10 second averages, 1 week)
```python
MEASUREMENT = "modbus"
FIELD = "TC01"
DOWNSAMPLE_WINDOW = "10s"
START_TIME = "2024-11-01T00:00:00Z"
STOP_TIME = "2024-11-08T00:00:00Z"
# Result: ~60,000 points, ~2 MB
```

### Export BGA purity (1 minute max values, 30 days)
```python
MEASUREMENT = "bga"
FIELD = "primary_pct"
DOWNSAMPLE_WINDOW = "1m"
DOWNSAMPLE_FUNCTION = "max"
START_TIME = "2024-10-03T00:00:00Z"
STOP_TIME = "2024-11-03T00:00:00Z"
# Result: ~43,000 points, ~1.5 MB
```

## Available Fields

### analog_inputs
- AI01, AI02, AI03, AI04, AI05, AI06, AI07, AI08

### modbus
- TC01-TC16 (thermocouples)
- RL01-RL30 (relay states)

### bga
- primary_pct, uncertainty, temperature_c, pressure_psi
- primary_gas, secondary_gas (text fields)

## Tips

- **Large exports**: Use larger windows (1s, 10s, 1m)
- **Detailed analysis**: Use smaller windows (10ms, 100ms)
- **Disk space**: Compress with `gzip export.csv` after export
- **Relative times**: Use `timedelta` for "last N hours" queries

