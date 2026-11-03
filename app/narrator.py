"""Offline, attribution-safe voice announcements over an always-on PCM stream."""
import json
import os
import subprocess
import time
import urllib.request

RATE = 48000
SECOND = RATE * 2 * 2  # 16-bit stereo
FIFO = '/tmp/electioncast_audio.pcm'

def speech_pcm(text):
    # espeak-ng produces deterministic offline narration; ffmpeg converts to raw stereo PCM.
    t = subprocess.run(['espeak-ng', '-s', '145', '--stdout', text[:450]], capture_output=True, timeout=20, check=True)
    x = subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-i','pipe:0','-f','s16le','-ac','2','-ar',str(RATE),'pipe:1'],
                       input=t.stdout, capture_output=True, timeout=30, check=True)
    return x.stdout

def latest_events():
    with urllib.request.urlopen('http://127.0.0.1:10000/api/narration', timeout=6) as r:
        return json.load(r).get('items', [])

def run():
    # Blocking FIFO open waits until ffmpeg subscribes.
    with open(FIFO, 'wb', buffering=0) as output:
        seen = set()
        audio = b''
        last_announcement = 0
        next_fetch = 0
        while True:
            start = time.monotonic()
            if start >= next_fetch:
                next_fetch = start + 12
                try:
                    items = latest_events()
                    for item in items:
                        if item['id'] in seen:
                            continue
                        seen.add(item['id'])
                        if len(seen) > 500:
                            seen = set(list(seen)[-300:])
                        if not audio and start - last_announcement >= 45:
                            asof = item.get('as_of') or 'the latest state feed update'
                            message = 'Election results update. ' + item['text'] + ' Counts are unofficial and may change. Data from participating state election offices via Open America.'
                            audio = speech_pcm(message)
                            last_announcement = start
                            break
                except Exception as exc:
                    print('Narrator fetch/speech error:', exc, flush=True)
            block = audio[:SECOND]
            audio = audio[SECOND:]
            if len(block) < SECOND:
                block += b'\0' * (SECOND-len(block))
            try:
                output.write(block)
            except BrokenPipeError:
                return
            # Pace ~1 sec so FFmpeg doesn't consume the audio faster than video.
            elapsed = time.monotonic() - start
            if elapsed < 1:
                time.sleep(1-elapsed)

if __name__ == '__main__':
    run()
