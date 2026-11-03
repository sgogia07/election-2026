#!/usr/bin/env bash
set -euo pipefail
export PORT="${PORT:-10000}"
export DISPLAY=:99
uvicorn app.main:app --host 0.0.0.0 --port "$PORT" &
WEBPID=$!
trap 'kill $WEBPID 2>/dev/null || true; jobs -pr | xargs -r kill || true' EXIT
if [[ "${STREAM_ENABLED:-false}" != "true" ]]; then
  echo 'Dashboard running; STREAM_ENABLED=false. No YouTube transmission will start.'
  wait "$WEBPID"
  exit $?
fi
if [[ -z "${YOUTUBE_STREAM_KEY:-}" || -z "${YOUTUBE_RTMPS_URL:-}" ]]; then
  echo 'STREAM_ENABLED=true requires YOUTUBE_STREAM_KEY and YOUTUBE_RTMPS_URL' >&2
  exit 2
fi
# Security: never print stream key or full FFmpeg command in logs.
Xvfb :99 -screen 0 1920x1080x24 -nolisten tcp &
sleep 3
chromium --no-sandbox --disable-dev-shm-usage --disable-gpu --disable-infobars \
  --no-first-run --kiosk --window-size=1920,1080 --window-position=0,0 \
  --app="http://127.0.0.1:${PORT}/" >/tmp/chromium.log 2>&1 &
for i in $(seq 1 30); do
  if curl -fsS "http://127.0.0.1:${PORT}/api/health" >/dev/null; then break; fi
  sleep 1
done
if [[ ! -p /tmp/electioncast_audio.pcm ]]; then mkfifo /tmp/electioncast_audio.pcm; fi

# 720p30 default is intentionally economical on Render; optional 1080p via output size.
# All FFmpeg streams include AAC audio; silence is transmitted between narration events.
while kill -0 "$WEBPID" 2>/dev/null; do
  python -m app.narrator >/tmp/narrator.log 2>&1 &
  NARRPID=$!
  echo 'Starting YouTube encoder (RTMPS).'
  ffmpeg -hide_banner -loglevel warning -nostdin \
    -thread_queue_size 256 -f x11grab -framerate 30 -video_size 1920x1080 -i :99.0 \
    -thread_queue_size 512 -f s16le -ar 48000 -ac 2 -i /tmp/electioncast_audio.pcm \
    -map 0:v:0 -map 1:a:0 -vf "scale=${OUTPUT_WIDTH:-1280}:${OUTPUT_HEIGHT:-720}" \
    -c:v libx264 -preset ultrafast -tune zerolatency -pix_fmt yuv420p -r 30 \
    -g 60 -keyint_min 60 -sc_threshold 0 -b:v "${VIDEO_BITRATE:-4000k}" \
    -maxrate "${VIDEO_BITRATE:-4000k}" -bufsize 8000k \
    -c:a aac -b:a 128k -ar 48000 -f flv \
    "${YOUTUBE_RTMPS_URL%/}/${YOUTUBE_STREAM_KEY}" || true
  kill "$NARRPID" 2>/dev/null || true
  wait "$NARRPID" 2>/dev/null || true
  echo 'Encoder disconnected; retrying in 10 seconds.'
  sleep 10
done
