@echo off
set VLC="C:\Program Files\VideoLAN\VLC\vlc.exe"

:: Window size for 2x3 grid on 3440x1440
set WIDTH=1720
set HEIGHT=480

:: Row 1
start "" %VLC% --video-x=0    --video-y=0   --width=%WIDTH% --height=%HEIGHT% "rtsp://192.168.0.180:554/main/av"
start "" %VLC% --video-x=1720 --video-y=0   --width=%WIDTH% --height=%HEIGHT% "rtsp://192.168.0.181:554/main/av"

:: Row 2
start "" %VLC% --video-x=0    --video-y=480 --width=%WIDTH% --height=%HEIGHT% "rtsp://192.168.0.182:554/main/av"
start "" %VLC% --video-x=1720 --video-y=480 --width=%WIDTH% --height=%HEIGHT% "rtsp://admin:Carbonneutral1!@192.168.0.100:554/h264Preview_01_main"

:: Row 3
start "" %VLC% --video-x=0    --video-y=960 --width=%WIDTH% --height=%HEIGHT% "rtsp://admin:Carbonneutral1!@192.168.0.101:554/h264Preview_01_main"
start "" %VLC% --video-x=1720 --video-y=960 --width=%WIDTH% --height=%HEIGHT% "rtsp://admin:Carbonneutral1!@192.168.0.3:554/h264Preview_01_main"
Add-Type @"
using System;
using System.Runtime.InteropServices;
public class Window {
    [DllImport("user32.dll")]
    public static extern bool MoveWindow(IntPtr hWnd, int X, int Y, int nWidth, int nHeight, bool bRepaint);
}
"@

$VLC = "C:\Program Files\VideoLAN\VLC\vlc.exe"

$streams = @(
    "rtsp://192.168.0.180:554/main/av",
    "rtsp://192.168.0.181:554/main/av",
    "rtsp://192.168.0.182:554/main/av",
    "rtsp://admin:Carbonneutral1!@192.168.0.100:554/h264Preview_01_main",
    "rtsp://admin:Carbonneutral1!@192.168.0.101:554/h264Preview_01_main",
    "rtsp://admin:Carbonneutral1!@192.168.0.3:554/h264Preview_01_main"
)

# Grid positions for 3440x1440 (2 columns x 3 rows)
$positions = @(
    @{X=0;    Y=0;   W=1720; H=480},
    @{X=1720; Y=0;   W=1720; H=480},
    @{X=0;    Y=480; W=1720; H=480},
    @{X=1720; Y=480; W=1720; H=480},
    @{X=0;    Y=960; W=1720; H=480},
    @{X=1720; Y=960; W=1720; H=480}
)

# Launch all VLC instances and collect process objects
$processes = @()
for ($i = 0; $i -lt $streams.Count; $i++) {
    $processes += Start-Process -FilePath $VLC -ArgumentList $streams[$i] -PassThru
}

# Wait for windows to open
Start-Sleep -Seconds 3

# Move and resize each window
for ($i = 0; $i -lt $processes.Count; $i++) {
    $hwnd = $processes[$i].MainWindowHandle
    $pos = $positions[$i]
    [Window]::MoveWindow($hwnd, $pos.X, $pos.Y, $pos.W, $pos.H, $true)
}