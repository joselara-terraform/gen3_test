#!/usr/bin/env python3
"""Generate plots from CSV data. Configuration in test_config.py"""

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from pathlib import Path
import os

# Import configuration from single source of truth
from test_config import PLOT_DPI, PLOT_FORMAT, FIGURE_SIZE, SENSOR_CONVERSIONS

# Which test directory to plot (auto-detects latest)
TEST_DIR = None


def find_latest_test_dir():
    """Find the most recent test directory"""
    data_dir = Path(__file__).parent
    test_dirs = [d for d in data_dir.iterdir() if d.is_dir() and not d.name.startswith('.')]
    if not test_dirs:
        raise FileNotFoundError("No test directories found")
    return max(test_dirs, key=lambda d: d.stat().st_mtime)


def convert_mA_to_eng(mA_value, config):
    """Convert 4-20mA signal to engineering units"""
    min_mA = config['min_mA']
    max_mA = config['max_mA']
    min_eng = config['min_eng']
    max_eng = config['max_eng']
    
    # Linear interpolation
    return min_eng + (mA_value - min_mA) * (max_eng - min_eng) / (max_mA - min_mA)


def get_shading_periods(test_dir):
    """Get purge and active periods for plot shading"""
    date_str = test_dir.name.split('_')[0]
    csv_dir = test_dir / 'csv'
    bga_path = csv_dir / f"{date_str}_BGA_BGA01.csv"
    aix_path = csv_dir / f"{date_str}_AIX.csv"
    
    purge_periods = []
    active_periods = []
    
    # Get purge periods (secondary_gas = N2)
    if bga_path.exists():
        df_bga = pd.read_csv(bga_path, parse_dates=['timestamp'])
        if 'secondary_gas' in df_bga.columns:
            df_bga['is_purge'] = df_bga['secondary_gas'] == '7727-37-9'
            purge_changes = df_bga['is_purge'].ne(df_bga['is_purge'].shift())
            purge_groups = purge_changes.cumsum()
            for group_id, group_df in df_bga[df_bga['is_purge']].groupby(purge_groups):
                if not group_df.empty:
                    purge_periods.append((group_df['timestamp'].min(), group_df['timestamp'].max()))
    
    # Get active periods (current > 1A)
    if aix_path.exists() and 'AI03' in SENSOR_CONVERSIONS:
        df_aix = pd.read_csv(aix_path, parse_dates=['timestamp'])
        if 'AI03' in df_aix.columns:
            config = SENSOR_CONVERSIONS['AI03']
            current = df_aix['AI03'].apply(lambda x: convert_mA_to_eng(x, config))
            df_aix['is_active'] = current > 1.0
            active_changes = df_aix['is_active'].ne(df_aix['is_active'].shift())
            active_groups = active_changes.cumsum()
            for group_id, group_df in df_aix[df_aix['is_active']].groupby(active_groups):
                if not group_df.empty:
                    active_periods.append((group_df['timestamp'].min(), group_df['timestamp'].max()))
    
    return purge_periods, active_periods


def add_shading(ax, purge_periods, active_periods):
    """Add purge and active period shading to a plot (no legend labels)"""
    # Purge periods (gray)
    for start, end in purge_periods:
        ax.axvspan(start, end, alpha=0.15, color='gray', zorder=0)
    
    # Active periods (light blue)
    for start, end in active_periods:
        ax.axvspan(start, end, alpha=0.1, color='cyan', zorder=0)


def plot_analog_inputs(test_dir, plots_dir, purge_periods, active_periods):
    """Plot analog input channels with activity > 1mA"""
    csv_path = test_dir / 'csv' / f"{test_dir.name.split('_')[0]}_AIX.csv"
    
    if not csv_path.exists():
        print("  ⚠ AIX.csv not found")
        return
    
    df = pd.read_csv(csv_path, parse_dates=['timestamp'])
    
    fig, ax = plt.subplots(figsize=FIGURE_SIZE)
    
    # Add shading first (background)
    add_shading(ax, purge_periods, active_periods)
    
    # Plot each AI channel if it has activity > 1mA
    plotted_channels = 0
    for i in range(1, 9):
        col = f'AI0{i}'
        if col in df.columns and df[col].max() > 1.0:
            ax.plot(df['timestamp'], df[col], label=col, linewidth=0.8)
            plotted_channels += 1
    
    if plotted_channels == 0:
        print("  ⚠ No active AI channels (all < 1mA)")
        plt.close()
        return
    
    ax.set_xlabel('Time')
    ax.set_ylabel('Current [mA]')
    ax.set_title('Analog Inputs')
    ax.set_ylim(0, 25)
    ax.set_xlim(df['timestamp'].min(), df['timestamp'].max())
    ax.grid(True, alpha=0.3)
    ax.legend(loc='best', ncol=2, fontsize=8)
    
    # Format x-axis
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
    ax.xaxis.set_major_locator(mdates.AutoDateLocator())
    plt.xticks(rotation=45)
    plt.tight_layout()
    
    # Save
    output_path = plots_dir / f"analog_inputs.{PLOT_FORMAT}"
    plt.savefig(output_path, dpi=PLOT_DPI, format=PLOT_FORMAT)
    plt.close()
    
    print(f"  ✓ Analog Inputs → {output_path.name} ({plotted_channels} channels)")


def plot_temperatures(test_dir, plots_dir, purge_periods, active_periods):
    """Plot thermocouples and BGA temperatures (exclude disconnected TCs)"""
    csv_dir = test_dir / 'csv'
    tc_path = csv_dir / f"{test_dir.name.split('_')[0]}_TC.csv"
    bga1_path = csv_dir / f"{test_dir.name.split('_')[0]}_BGA_BGA01.csv"
    bga2_path = csv_dir / f"{test_dir.name.split('_')[0]}_BGA_BGA02.csv"
    
    fig, ax = plt.subplots(figsize=FIGURE_SIZE)
    
    # Add shading first
    add_shading(ax, purge_periods, active_periods)
    
    plotted_channels = 0
    time_range = None
    
    # Plot thermocouples (exclude if all values > 1000C, indicating disconnected sensor)
    if tc_path.exists():
        df_tc = pd.read_csv(tc_path, parse_dates=['timestamp'])
        time_range = (df_tc['timestamp'].min(), df_tc['timestamp'].max())
        
        for i in range(1, 17):
            col = f'TC{i:02d}'
            if col in df_tc.columns and df_tc[col].min() < 1000:
                ax.plot(df_tc['timestamp'], df_tc[col], label=col, linewidth=0.6, alpha=0.7)
                plotted_channels += 1
    
    # Plot BGA temperatures
    if bga1_path.exists():
        df_bga1 = pd.read_csv(bga1_path, parse_dates=['timestamp'])
        if time_range is None:
            time_range = (df_bga1['timestamp'].min(), df_bga1['timestamp'].max())
        if 'temperature' in df_bga1.columns:
            ax.plot(df_bga1['timestamp'], df_bga1['temperature'], 
                    label='BGA01 Temp', linewidth=1.5, color='red', linestyle='--')
            plotted_channels += 1
    
    if bga2_path.exists():
        df_bga2 = pd.read_csv(bga2_path, parse_dates=['timestamp'])
        if time_range is None:
            time_range = (df_bga2['timestamp'].min(), df_bga2['timestamp'].max())
        if 'temperature' in df_bga2.columns:
            ax.plot(df_bga2['timestamp'], df_bga2['temperature'], 
                    label='BGA02 Temp', linewidth=1.5, color='orange', linestyle='--')
            plotted_channels += 1
    
    if plotted_channels == 0:
        print("  ⚠ No temperature data")
        plt.close()
        return
    
    ax.set_xlabel('Time')
    ax.set_ylabel('Temperature [°C]')
    ax.set_title('Temperatures')
    ax.set_ylim(0, 120)
    if time_range:
        ax.set_xlim(time_range[0], time_range[1])
    ax.grid(True, alpha=0.3)
    ax.legend(loc='best', ncol=3, fontsize=7)
    
    # Format x-axis
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
    ax.xaxis.set_major_locator(mdates.AutoDateLocator())
    plt.xticks(rotation=45)
    plt.tight_layout()
    
    # Save
    output_path = plots_dir / f"temperatures.{PLOT_FORMAT}"
    plt.savefig(output_path, dpi=PLOT_DPI, format=PLOT_FORMAT)
    plt.close()
    
    print(f"  ✓ Temperatures → {output_path.name} ({plotted_channels} channels)")


def plot_gas_purity(test_dir, plots_dir, purge_periods, active_periods, ylim=(0, 100), suffix=""):
    """Plot BGA purity with period shading"""
    csv_dir = test_dir / 'csv'
    bga1_path = csv_dir / f"{test_dir.name.split('_')[0]}_BGA_BGA01.csv"
    bga2_path = csv_dir / f"{test_dir.name.split('_')[0]}_BGA_BGA02.csv"
    
    fig, ax = plt.subplots(figsize=FIGURE_SIZE)
    
    # Add shading first
    add_shading(ax, purge_periods, active_periods)
    
    time_range = None
    
    # Plot BGA01 purity
    if bga1_path.exists():
        df_bga1 = pd.read_csv(bga1_path, parse_dates=['timestamp'])
        time_range = (df_bga1['timestamp'].min(), df_bga1['timestamp'].max())
        if 'purity' in df_bga1.columns:
            ax.plot(df_bga1['timestamp'], df_bga1['purity'], 
                    label='BGA01', linewidth=1.5, marker='.', markersize=2)
    
    # Plot BGA02 purity
    if bga2_path.exists():
        df_bga2 = pd.read_csv(bga2_path, parse_dates=['timestamp'])
        if time_range is None:
            time_range = (df_bga2['timestamp'].min(), df_bga2['timestamp'].max())
        if 'purity' in df_bga2.columns:
            ax.plot(df_bga2['timestamp'], df_bga2['purity'], 
                    label='BGA02', linewidth=1.5, marker='.', markersize=2)
    
    ax.set_xlabel('Time')
    ax.set_ylabel('Purity [%]')
    
    # Title based on range
    if ylim == (80, 100):
        ax.set_title('Gas Purity (Detail)')
    else:
        ax.set_title('Gas Purity')
    
    ax.set_ylim(ylim[0], ylim[1])
    if time_range:
        ax.set_xlim(time_range[0], time_range[1])
    ax.grid(True, alpha=0.3)
    ax.legend(loc='best')
    
    # Format x-axis
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
    ax.xaxis.set_major_locator(mdates.AutoDateLocator())
    plt.xticks(rotation=45)
    plt.tight_layout()
    
    # Save
    filename = f"gas_purity{suffix}.{PLOT_FORMAT}"
    output_path = plots_dir / filename
    plt.savefig(output_path, dpi=PLOT_DPI, format=PLOT_FORMAT)
    plt.close()
    
    print(f"  ✓ Gas Purity{' (Detail)' if suffix else ''} → {output_path.name}")


def plot_cell_voltages(test_dir, plots_dir, purge_periods, active_periods):
    """Plot stack voltage (CV001) and average cell voltage"""
    csv_path = test_dir / 'csv' / f"{test_dir.name.split('_')[0]}_CV.csv"
    
    if not csv_path.exists():
        print("  ⚠ CV.csv not found")
        return
    
    df = pd.read_csv(csv_path, parse_dates=['timestamp'])
    
    if 'CV001' not in df.columns:
        print("  ⚠ CV001 not found in data")
        return
    
    fig, ax = plt.subplots(figsize=FIGURE_SIZE)
    
    # Add shading first
    add_shading(ax, purge_periods, active_periods)
    
    # Plot CV001 (stack voltage)
    ax.plot(df['timestamp'], df['CV001'], label='Stack Voltage (CV001)', 
             linewidth=1.5, color='blue')
    
    # Plot average cell voltage (CV001 / 5)
    avg_cell_voltage = df['CV001'] / 5
    ax.plot(df['timestamp'], avg_cell_voltage, label='Average Cell Voltage', 
             linewidth=1.5, color='green', linestyle='--')
    
    # Reference lines
    ax.axhline(y=15, color='red', linestyle='--', linewidth=1, alpha=0.7, label='15V Limit')
    ax.axhline(y=3, color='red', linestyle='--', linewidth=1, alpha=0.7, label='3V Limit')
    
    ax.set_xlabel('Time')
    ax.set_ylabel('Voltage [V]')
    ax.set_title('Voltages')
    ax.set_ylim(0, 20)
    ax.set_xlim(df['timestamp'].min(), df['timestamp'].max())
    ax.grid(True, alpha=0.3)
    ax.legend(loc='best')
    
    # Format x-axis
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
    ax.xaxis.set_major_locator(mdates.AutoDateLocator())
    plt.xticks(rotation=45)
    plt.tight_layout()
    
    # Save
    output_path = plots_dir / f"voltages.{PLOT_FORMAT}"
    plt.savefig(output_path, dpi=PLOT_DPI, format=PLOT_FORMAT)
    plt.close()
    
    print(f"  ✓ Voltages → {output_path.name}")


def plot_pressures(test_dir, plots_dir, purge_periods, active_periods):
    """Plot pressure sensors (AI01, AI02)"""
    csv_path = test_dir / 'csv' / f"{test_dir.name.split('_')[0]}_AIX.csv"
    
    if not csv_path.exists():
        print("  ⚠ AIX.csv not found")
        return
    
    df = pd.read_csv(csv_path, parse_dates=['timestamp'])
    
    fig, ax = plt.subplots(figsize=FIGURE_SIZE)
    add_shading(ax, purge_periods, active_periods)
    
    # Convert and plot AI01, AI02
    for channel in ['AI01', 'AI02']:
        if channel in df.columns and channel in SENSOR_CONVERSIONS:
            config = SENSOR_CONVERSIONS[channel]
            converted = df[channel].apply(lambda x: convert_mA_to_eng(x, config))
            ax.plot(df['timestamp'], converted, label=config['label'], linewidth=1.5)
    
    ax.set_xlabel('Time')
    ax.set_ylabel('Pressure [PSI]')
    ax.set_title('Pressures')
    ax.set_ylim(0, 1)
    ax.set_xlim(df['timestamp'].min(), df['timestamp'].max())
    ax.grid(True, alpha=0.3)
    ax.legend(loc='best')
    
    # Format x-axis
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
    ax.xaxis.set_major_locator(mdates.AutoDateLocator())
    plt.xticks(rotation=45)
    plt.tight_layout()
    
    # Save
    output_path = plots_dir / f"pressures.{PLOT_FORMAT}"
    plt.savefig(output_path, dpi=PLOT_DPI, format=PLOT_FORMAT)
    plt.close()
    
    print(f"  ✓ Pressures → {output_path.name}")


def plot_current(test_dir, plots_dir, purge_periods, active_periods):
    """Plot actual and target current"""
    csv_path = test_dir / 'csv' / f"{test_dir.name.split('_')[0]}_AIX.csv"
    labjack_path = test_dir / 'csv' / f"{test_dir.name.split('_')[0]}_labjack.csv"
    
    if not csv_path.exists():
        print("  ⚠ AIX.csv not found")
        return
    
    df = pd.read_csv(csv_path, parse_dates=['timestamp'])
    
    if 'AI03' not in df.columns or 'AI03' not in SENSOR_CONVERSIONS:
        print("  ⚠ AI03 not configured")
        return
    
    fig, ax = plt.subplots(figsize=FIGURE_SIZE)
    add_shading(ax, purge_periods, active_periods)
    
    # Plot actual current (AI03)
    config = SENSOR_CONVERSIONS['AI03']
    actual_current = df['AI03'].apply(lambda x: convert_mA_to_eng(x, config))
    ax.plot(df['timestamp'], actual_current, label='Actual Current', linewidth=1.5, color='blue')
    
    # Plot target current from LabJack (AIN0: 0-5V → 0-100A)
    if labjack_path.exists():
        df_lj = pd.read_csv(labjack_path, parse_dates=['timestamp'])
        if 'AIN0_voltage' in df_lj.columns:
            target_current = df_lj['AIN0_voltage'] * 20.0  # 0-5V → 0-100A
            ax.plot(df_lj['timestamp'], target_current, label='Target Current', 
                   linewidth=1.5, color='orange', linestyle='--', alpha=0.8)
    
    ax.set_xlabel('Time')
    ax.set_ylabel('Current [A]')
    ax.set_title('Current')
    ax.set_ylim(0, 120)
    ax.set_xlim(df['timestamp'].min(), df['timestamp'].max())
    ax.grid(True, alpha=0.3)
    ax.legend(loc='best')
    
    # Format x-axis
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
    ax.xaxis.set_major_locator(mdates.AutoDateLocator())
    plt.xticks(rotation=45)
    plt.tight_layout()
    
    # Save
    output_path = plots_dir / f"current.{PLOT_FORMAT}"
    plt.savefig(output_path, dpi=PLOT_DPI, format=PLOT_FORMAT)
    plt.close()
    
    print(f"  ✓ Current → {output_path.name}")


def plot_flowrates(test_dir, plots_dir, purge_periods, active_periods):
    """Plot flowrate sensors (AI04, AI05)"""
    csv_path = test_dir / 'csv' / f"{test_dir.name.split('_')[0]}_AIX.csv"
    
    if not csv_path.exists():
        print("  ⚠ AIX.csv not found")
        return
    
    df = pd.read_csv(csv_path, parse_dates=['timestamp'])
    
    fig, ax = plt.subplots(figsize=FIGURE_SIZE)
    add_shading(ax, purge_periods, active_periods)
    
    # Convert and plot AI04, AI05
    for channel in ['AI04', 'AI05']:
        if channel in df.columns and channel in SENSOR_CONVERSIONS:
            config = SENSOR_CONVERSIONS[channel]
            converted = df[channel].apply(lambda x: convert_mA_to_eng(x, config))
            ax.plot(df['timestamp'], converted, label=config['label'], linewidth=1.5)
    
    ax.set_xlabel('Time')
    ax.set_ylabel('Flowrate [L/min]')
    ax.set_title('Flowrates')
    ax.set_ylim(0, 10)
    ax.set_xlim(df['timestamp'].min(), df['timestamp'].max())
    ax.grid(True, alpha=0.3)
    ax.legend(loc='best')
    
    # Format x-axis
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
    ax.xaxis.set_major_locator(mdates.AutoDateLocator())
    plt.xticks(rotation=45)
    plt.tight_layout()
    
    # Save
    output_path = plots_dir / f"flowrates.{PLOT_FORMAT}"
    plt.savefig(output_path, dpi=PLOT_DPI, format=PLOT_FORMAT)
    plt.close()
    
    print(f"  ✓ Flowrates → {output_path.name}")


def generate_plots():
    """Generate all plots from CSV data"""
    
    # Find test directory
    if TEST_DIR:
        test_dir = Path(__file__).parent / TEST_DIR
    else:
        test_dir = find_latest_test_dir()
    
    if not test_dir.exists():
        print(f"Error: Test directory not found: {test_dir}")
        return
    
    # Create plots subdirectory
    plots_dir = test_dir / "plots"
    plots_dir.mkdir(exist_ok=True)
    
    print("=" * 60)
    print(f"MK1_AWE Data Plotting")
    print("=" * 60)
    print(f"Test directory: {test_dir.name}")
    print(f"Output: {plots_dir.relative_to(Path(__file__).parent)}/")
    print()
    
    # Get shading periods once for all plots
    purge_periods, active_periods = get_shading_periods(test_dir)
    
    # Generate plots
    plot_analog_inputs(test_dir, plots_dir, purge_periods, active_periods)
    plot_temperatures(test_dir, plots_dir, purge_periods, active_periods)
    plot_cell_voltages(test_dir, plots_dir, purge_periods, active_periods)
    plot_pressures(test_dir, plots_dir, purge_periods, active_periods)
    plot_current(test_dir, plots_dir, purge_periods, active_periods)
    plot_flowrates(test_dir, plots_dir, purge_periods, active_periods)
    plot_gas_purity(test_dir, plots_dir, purge_periods, active_periods, ylim=(0, 100))
    plot_gas_purity(test_dir, plots_dir, purge_periods, active_periods, ylim=(80, 100), suffix="_detail")
    
    print()
    print("=" * 60)
    print(f"✓ Plots saved to: {plots_dir}")
    print("=" * 60)


if __name__ == "__main__":
    generate_plots()

