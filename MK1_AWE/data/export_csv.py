#!/usr/bin/env python3
"""Export InfluxDB data to CSV. Configuration in test_config.py"""

from influxdb_client import InfluxDBClient
from datetime import datetime
import sys
import os
import warnings
from influxdb_client.client.warnings import MissingPivotFunction

# Suppress influxdb_client warnings about pivot function
warnings.simplefilter("ignore", MissingPivotFunction)

# Import configuration from single source of truth
from test_config import (
    TEST_NAME, START_TIME, STOP_TIME, START_TIME_UTC, STOP_TIME_UTC,
    DOWNSAMPLE_AIX, DOWNSAMPLE_TC, DOWNSAMPLE_BGA, DOWNSAMPLE_RL, DOWNSAMPLE_CV,
    DOWNSAMPLE_FUNCTION, SENSOR_CONVERSIONS
)
import pandas as pd

# InfluxDB Connection (reads from parent config/devices.yaml)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'gui'))
from config_loader import get_influx_params


def convert_mA_to_eng(mA_value, config):
    """Convert 4-20mA to engineering units"""
    min_mA = config['min_mA']
    max_mA = config['max_mA']
    min_eng = config['min_eng']
    max_eng = config['max_eng']
    return min_eng + (mA_value - min_mA) * (max_eng - min_eng) / (max_mA - min_mA)


def export_sensor_group(client, influx_params, output_dir, date_str, 
                        measurement, fields, downsample_window, filename_suffix):
    """Export a group of related sensors to a single CSV"""
    
    # Build query for multiple fields
    field_filter = ' or '.join([f'r._field == "{f}"' for f in fields])
    
    query = f'''
from(bucket: "{influx_params['bucket']}")
  |> range(start: {START_TIME_UTC}, stop: {STOP_TIME_UTC})
  |> filter(fn: (r) => r._measurement == "{measurement}")
  |> filter(fn: (r) => {field_filter})
  |> aggregateWindow(every: {downsample_window}, fn: {DOWNSAMPLE_FUNCTION})
  |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
'''
    
    print(f"\nExporting {filename_suffix}...")
    
    try:
        df = client.query_api().query_data_frame(query)
        
        if df.empty:
            print(f"  ⚠ No data found")
            return None
        
        # Keep only timestamp and field columns
        keep_cols = ['_time'] + [col for col in df.columns if col in fields]
        df = df[keep_cols]
        
        # Convert timestamps from UTC to local timezone and format as string
        df['_time'] = df['_time'].dt.tz_convert('America/Los_Angeles')
        df['_time'] = df['_time'].dt.strftime('%Y-%m-%d %H:%M:%S.%f').str[:-3]  # Remove last 3 digits (keep milliseconds)
        df.rename(columns={'_time': 'timestamp'}, inplace=True)
        
        # Save to CSV with proper float formatting
        output_file = f"{date_str}_{filename_suffix}.csv"
        output_path = os.path.join(output_dir, output_file)
        df.to_csv(output_path, index=False, float_format='%.6f')
        
        print(f"  ✓ {len(df)} points, {len(keep_cols)-1} channels")
        print(f"    File: {output_file} ({os.path.getsize(output_path) / 1024:.1f} KB)")
        
        return df  # Return for conversion
        
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return None


def export_converted_sensors(df_aix, output_dir, date_str, sensor_type, unit_name):
    """Export converted engineering units for specific sensor type"""
    if df_aix is None or df_aix.empty:
        return
    
    converted_df = pd.DataFrame({'timestamp': df_aix['timestamp']})
    
    # Convert matching sensors
    for channel_id, config in SENSOR_CONVERSIONS.items():
        if config['unit'] == unit_name and channel_id in df_aix.columns:
            converted_df[config['label']] = df_aix[channel_id].apply(
                lambda x: convert_mA_to_eng(x, config)
            )
    
    if len(converted_df.columns) <= 1:  # Only timestamp, no data
        return
    
    # Save converted CSV
    output_file = f"{date_str}_{sensor_type}.csv"
    output_path = os.path.join(output_dir, output_file)
    converted_df.to_csv(output_path, index=False, float_format='%.6f')
    
    print(f"  ✓ Converted {sensor_type}: {len(converted_df.columns)-1} channels")
    print(f"    File: {output_file} ({os.path.getsize(output_path) / 1024:.1f} KB)")


def export_bga_data(client, influx_params, output_dir, date_str, downsample_window):
    """Export BGA data with multiple fields per device"""
    
    print(f"\nExporting BGA data...")
    
    try:
        # Export each BGA separately to avoid duplicate rows
        for bga_id in ['BGA01', 'BGA02']:
            query = f'''
from(bucket: "{influx_params['bucket']}")
  |> range(start: {START_TIME_UTC}, stop: {STOP_TIME_UTC})
  |> filter(fn: (r) => r._measurement == "bga_metrics")
  |> filter(fn: (r) => r.bga_id == "{bga_id}")
  |> filter(fn: (r) => r._field == "purity" or 
                       r._field == "uncertainty" or
                       r._field == "temperature" or
                       r._field == "pressure")
  |> aggregateWindow(every: {downsample_window}, fn: {DOWNSAMPLE_FUNCTION}, createEmpty: false)
  |> keep(columns: ["_time", "_field", "_value", "primary_gas", "secondary_gas"])
'''
            
            df = client.query_api().query_data_frame(query)
            
            if df.empty:
                print(f"  ⚠ {bga_id}: No data found")
                continue
            
            # Pivot manually using pandas (more reliable than Flux pivot with tags)
            df_pivot = df.pivot_table(
                index='_time',
                columns='_field',
                values='_value',
                aggfunc='first'  # Take first value if duplicates
            ).reset_index()
            
            # Add gas info from the original df (take most common value per timestamp)
            if 'primary_gas' in df.columns and 'secondary_gas' in df.columns:
                gas_info = df.groupby('_time')[['primary_gas', 'secondary_gas']].first().reset_index()
                df_pivot = df_pivot.merge(gas_info, on='_time', how='left')
            
            # Convert timestamps from UTC to local timezone and format as string
            df_pivot['_time'] = df_pivot['_time'].dt.tz_convert('America/Los_Angeles')
            df_pivot['_time'] = df_pivot['_time'].dt.strftime('%Y-%m-%d %H:%M:%S.%f').str[:-3]
            df_pivot.rename(columns={'_time': 'timestamp'}, inplace=True)
            
            # Save to CSV with proper float formatting
            output_file = f"{date_str}_BGA_{bga_id}.csv"
            output_path = os.path.join(output_dir, output_file)
            df_pivot.to_csv(output_path, index=False, float_format='%.6f')
            
            print(f"  ✓ {bga_id}: {len(df_pivot)} points")
            print(f"    File: {output_file} ({os.path.getsize(output_path) / 1024:.1f} KB)")
            
    except Exception as e:
        print(f"  ✗ Error: {e}")


def export_data():
    """Export all sensor data with configured parameters"""
    
    # Use local time for folder naming (consistent with process_test.py)
    date_str = START_TIME.strftime('%Y-%m-%d')
    
    # Create output directory: YYYY-MM-DD_TEST_NAME/csv/
    test_dir = os.path.join(os.path.dirname(__file__), f"{date_str}_{TEST_NAME}")
    output_dir = os.path.join(test_dir, 'csv')
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"=" * 60)
    print(f"MK1_AWE Data Export")
    print(f"=" * 60)
    print(f"Test: {TEST_NAME}")
    print(f"Time range: {START_TIME.strftime('%Y-%m-%d %H:%M:%S %Z')} to {STOP_TIME.strftime('%H:%M:%S %Z')}")
    print(f"Output directory: {os.path.basename(output_dir)}/")
    
    # Get InfluxDB credentials
    influx_params = get_influx_params()
    
    # For token, check environment or docker-compose.yml
    token = os.getenv('INFLUXDB_ADMIN_TOKEN')
    if not token:
        print("\nError: INFLUXDB_ADMIN_TOKEN environment variable not set")
        print("Get it from docker-compose.yml or set it:")
        print("  export INFLUXDB_ADMIN_TOKEN=your_token_here")
        sys.exit(1)
    
    # Connect to InfluxDB
    client = InfluxDBClient(
        url=influx_params['url'],
        token=token,
        org=influx_params['org']
    )
    
    try:
        # Export analog inputs (AI01-AI08) - raw mA values
        ai_fields = [f"AI0{i}" for i in range(1, 9)]
        df_aix = export_sensor_group(client, influx_params, output_dir, date_str,
                                     "analog_inputs", ai_fields, DOWNSAMPLE_AIX, "AIX")
        
        # Export converted engineering units
        if df_aix is not None:
            print("\nExporting converted sensors...")
            export_converted_sensors(df_aix, output_dir, date_str, "pressures", "PSI")
            export_converted_sensors(df_aix, output_dir, date_str, "current", "A")
            export_converted_sensors(df_aix, output_dir, date_str, "flowrates", "L/min")
        
        # Export thermocouples (TC01-TC16)
        tc_fields = [f"TC{i:02d}" for i in range(1, 17)]
        export_sensor_group(client, influx_params, output_dir, date_str,
                          "modbus", tc_fields, DOWNSAMPLE_TC, "TC")
        
        # Export relays (RL01-RL30)
        rl_fields = [f"RL{i:02d}" for i in range(1, 31)]
        export_sensor_group(client, influx_params, output_dir, date_str,
                          "modbus", rl_fields, DOWNSAMPLE_RL, "RL")
        
        # Export cell voltages (CV001 only)
        cv_fields = ["CV001"]
        export_sensor_group(client, influx_params, output_dir, date_str,
                          "cell_voltages", cv_fields, DOWNSAMPLE_CV, "CV")
        
        # Export LabJack PSU control voltage
        export_sensor_group(client, influx_params, output_dir, date_str,
                          "labjack", ["AIN0_voltage"], DOWNSAMPLE_CV, "labjack")
        
        # Export BGA data (separate per device)
        export_bga_data(client, influx_params, output_dir, date_str, DOWNSAMPLE_BGA)
        
        print(f"\n{'=' * 60}")
        print(f"✓ Export complete: {output_dir}")
        print(f"{'=' * 60}")
        
    except Exception as e:
        print(f"\nError: {e}")
        sys.exit(1)
    finally:
        client.close()


if __name__ == "__main__":
    export_data()
