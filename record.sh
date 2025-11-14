#!/usr/bin/env bash
# ZowiePTZ 4K@30 HEVC recorder (minimal output)
# Start:  ./record.sh
# Stop:   Ctrl+C

CAMERA_URL="rtsp://192.168.10.23:554/main/av"
OUT_DIR="$HOME/Movies"
LOG_FILE="$OUT_DIR/record_zowie.log"

FONT_PATH="/System/Library/Fonts/Supplemental/Arial.ttf"

# Timestamp overlay
TIMESTAMP_FILTER="drawtext=fontfile='${FONT_PATH}':expansion=strftime:text='%Y-%m-%d %H\\:%M\\:%S':fontcolor=white:fontsize=48:box=1:boxcolor=0x000000AA:borderw=2:bordercolor=black@0.7:x=20:y=20"

mkdir -p "$OUT_DIR"

start_ts="$(date)"
echo "[$start_ts] Recording… Press Ctrl+C to stop. Saving to: $OUT_DIR"

trap 'echo "[`date`] Recording stopped."; exit 0' SIGINT

/opt/homebrew/bin/ffmpeg \
  -hide_banner -loglevel error \
  -rtsp_transport tcp -rtsp_flags prefer_tcp \
  -fflags +genpts -use_wallclock_as_timestamps 1 \
  -rtbufsize 100M -probesize 2M -analyzeduration 2M \
  -i "$CAMERA_URL" \
  -map 0:v:0 -map 0:a:0 \
  -vf "fps=30,scale=3840:2160:flags=bicubic,format=yuv420p,${TIMESTAMP_FILTER}" \
  -c:v hevc_videotoolbox -tag:v hvc1 -b:v 1500k -maxrate 1800k -bufsize 3M -g 60 \
  -c:a aac -b:a 96k -ar 48000 \
  -movflags +faststart \
  -f segment -segment_time 3600 -strftime 1 -reset_timestamps 1 \
  -segment_format_options movflags=+faststart \
  "${OUT_DIR}/%Y-%m-%d_%H-%M-%S_stack_front.mp4" \
  >>"$LOG_FILE" 2>&1
