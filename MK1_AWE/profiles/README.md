# Current Profiles

This directory contains current profile CSV files for automated testing.

## Profile Format

CSV with 2 columns (no header):
```
time_seconds,current_amps
0,0
300,10
600,20
900,30
1200,0
```

**Requirements:**
- Time must be monotonically increasing
- Current must be within 0-100A range (Gen2)
- First row should start at time=0
- Time intervals (dt) typically ~300 seconds

## Example Profiles

### Simple Step Test
```csv
0,0
300,25
600,50
900,75
1200,100
1500,0
```
Duration: 25 minutes, 5 steps

### Long Duration Test
```csv
0,0
600,10
3600,20
7200,30
10800,40
14400,0
```
Duration: 4 hours, gradual increase

## Usage

1. Create profile CSV in this directory
2. Edit `MK1_AWE/config/devices.yaml`:
   ```yaml
   psu_control:
     gen2:
       profile_path: "profiles/my_test.csv"
   ```
3. Launch GUI and press PROFILE button

