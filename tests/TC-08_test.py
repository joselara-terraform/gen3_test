#!/usr/bin/env python3
import ctypes
import time

# ── USER CONFIG ──
DLL_PATH           = r"C:\Program Files\Pico Technology\SDK\lib\usbtc08.dll"
SAMPLE_INTERVAL_MS = 1000    # how frequently the TC‑08 itself samples
PRINT_INTERVAL_S   = 1       # how often Python prints to console
NUM_CHANNELS       = 8       # number of thermocouple inputs
TC_TYPE_K_CHAR     = b'K'    # K‑type thermocouple
# ──────────────────

# load the Pico DLL
tc08 = ctypes.WinDLL(DLL_PATH)

# ── minimal prototypes ──
tc08.usb_tc08_open_unit.restype = ctypes.c_int16

tc08.usb_tc08_set_channel.argtypes = [
    ctypes.c_int16,    # handle
    ctypes.c_int16,    # channel number
    ctypes.c_char      # type char ('C' or 'K', etc)
]
tc08.usb_tc08_set_channel.restype = ctypes.c_int16

tc08.usb_tc08_run.argtypes = [
    ctypes.c_int16,    # handle
    ctypes.c_int32     # sample interval (ms)
]
tc08.usb_tc08_run.restype = ctypes.c_int32

tc08.usb_tc08_get_temp.argtypes = [
    ctypes.c_int16,                                # handle
    ctypes.POINTER(ctypes.c_float),                # temp buffer
    ctypes.POINTER(ctypes.c_int32),                # time buffer
    ctypes.c_int32,                                # number of readings
    ctypes.POINTER(ctypes.c_int16),                # overflow flag
    ctypes.c_int16,                                # channel to read
    ctypes.c_int16,                                # units (0=Celsius)
    ctypes.c_int16                                 # trigger mode (0=none)
]
tc08.usb_tc08_get_temp.restype = ctypes.c_int32

tc08.usb_tc08_stop.argtypes = [ctypes.c_int16]
tc08.usb_tc08_stop.restype  = ctypes.c_int16

tc08.usb_tc08_close_unit.argtypes = [ctypes.c_int16]
tc08.usb_tc08_close_unit.restype  = ctypes.c_int16
# ──────────────────────────

# open the device
handle = tc08.usb_tc08_open_unit()
if handle <= 0:
    raise RuntimeError("Unable to open TC‑08. Check the DLL path and USB connection.")

# configure cold junction (channel 0)
if tc08.usb_tc08_set_channel(handle, 0, ctypes.c_char(b'C')) != 1:
    print("Warning: failed to set cold-junction channel.")

# configure all 8 thermocouple channels to K‑type
for ch in range(1, NUM_CHANNELS+1):
    if tc08.usb_tc08_set_channel(handle, ch, ctypes.c_char(TC_TYPE_K_CHAR)) != 1:
        print(f"Warning: failed to set channel {ch} to K‑type.")

# start streaming at SAMPLE_INTERVAL_MS
actual = tc08.usb_tc08_run(handle, SAMPLE_INTERVAL_MS)
if actual <= 0:
    raise RuntimeError("Failed to start streaming.")

print(f"Streaming at {actual} ms intervals. Press Ctrl+C to stop.\n")

try:
    while True:
        temps = []
        overflow = ctypes.c_int16(0)
        for ch in range(1, NUM_CHANNELS+1):
            tb     = (ctypes.c_float * 1)()
            ttime  = (ctypes.c_int32 * 1)()
            tc08.usb_tc08_get_temp(
                handle,
                tb,
                ttime,
                1,                     # one reading
                ctypes.byref(overflow),
                ctypes.c_int16(ch),
                ctypes.c_int16(0),     # 0 = °C
                ctypes.c_int16(0)      # no trigger
            )
            temps.append(tb[0])
        print("Temps (°C):", ["{:6.2f}".format(t) for t in temps])
        time.sleep(PRINT_INTERVAL_S)

except KeyboardInterrupt:
    print("\nCleanup…")
    tc08.usb_tc08_stop(handle)
    tc08.usb_tc08_close_unit(handle)
    print("Done.")
