import nidaqmx
import time
import numpy as np

# Configuration
MODULE_1 = "cDAQ9187-23E902CMod1"  # NI 9253 current input module
MODULE_4 = "cDAQ9187-23E902CMod4"  # NI 9253 current input module
SAMPLE_RATE = 2500.0  # Hz - Optimal for 1ms response time sensors (2.5x oversampling)
SAMPLES_PER_CHANNEL = 250  # Read 0.1 seconds of data at a time

def read_continuous():
    """Continuously read from all 16 channels (8 from each NI 9253)"""
    
    with nidaqmx.Task() as task:
        # Add all 8 analog input channels from Module 1
        for channel in range(8):
            task.ai_channels.add_ai_current_chan(
                f"{MODULE_1}/ai{channel}",
                min_val=-0.020,  # -20 mA
                max_val=0.020,   # +20 mA
                name_to_assign_to_channel=f"Mod1_Ch{channel}"
            )
        
        # Add all 8 analog input channels from Module 4
        for channel in range(8):
            task.ai_channels.add_ai_current_chan(
                f"{MODULE_4}/ai{channel}",
                min_val=-0.020,  # -20 mA
                max_val=0.020,   # +20 mA
                name_to_assign_to_channel=f"Mod4_Ch{channel}"
            )
        
        # Configure timing
        task.timing.cfg_samp_clk_timing(
            rate=SAMPLE_RATE,
            sample_mode=nidaqmx.constants.AcquisitionType.CONTINUOUS
        )
        
        # Set a larger input buffer to prevent overruns
        task.in_stream.input_buf_size = int(SAMPLE_RATE * 16 * 10)  # 10 seconds of buffer for 16 channels
        
        # Get the actual sample rate the hardware is using
        actual_hw_rate = task.timing.samp_clk_rate
        print(f"Requested: {SAMPLE_RATE} Hz, Hardware using: {actual_hw_rate} Hz")
        print(f"Reading from both modules (16 channels total) - Press Ctrl+C to stop")
        print("\nChannel readings (mA):")
        
        # Variables for tracking sample rates
        last_time = time.perf_counter()
        
        try:
            while True:
                # Read data from all channels
                data = task.read(number_of_samples_per_channel=SAMPLES_PER_CHANNEL)
                
                # Calculate actual sampling rate
                current_time = time.perf_counter()
                time_diff = current_time - last_time
                if time_diff > 0:
                    actual_rate = SAMPLES_PER_CHANNEL / time_diff
                    last_time = current_time
                else:
                    actual_rate = SAMPLE_RATE
                
                # Display Module 1 values
                print("\r", end="")
                print("Module 1: ", end="")
                for ch in range(8):
                    value = data[ch][-1] * 1000  # Convert to mA
                    print(f"Ch{ch}: {value:+6.2f} ", end="")
                
                # Move to next line for sampling rates
                print("\n", end="")
                print("\r          ", end="")
                for ch in range(8):
                    print(f"     {actual_rate:4.0f} Hz ", end="")
                
                # Display Module 4 values
                print("\n", end="")
                print("\rModule 4: ", end="")
                for ch in range(8):
                    value = data[ch+8][-1] * 1000  # Convert to mA
                    print(f"Ch{ch}: {value:+6.2f} ", end="")
                
                # Move to next line for sampling rates
                print("\n", end="")
                print("\r          ", end="")
                for ch in range(8):
                    print(f"     {actual_rate:4.0f} Hz ", end="")
                
                # Move cursor back up 3 lines for next update
                print("\033[3A", end="", flush=True)
                time.sleep(0.1)  # Small delay for display
                
        except KeyboardInterrupt:
            print("\n\n\n\n\nStopping acquisition...")

if __name__ == "__main__":
    # Check if nidaqmx is installed
    try:
        import nidaqmx
        read_continuous()
    except ImportError:
        print("Error: nidaqmx not installed. Run: pip install nidaqmx")
    except Exception as e:
        print(f"Error: {e}")
        print("\nTroubleshooting:")
        print("1. Verify device name in NI MAX")
        print("2. Ensure NI-DAQmx drivers are installed")
        print("3. Check that cDAQ is connected via Ethernet")