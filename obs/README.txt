OBS alternative, on your computer:
1. Add Browser Source: https://YOUR-RENDER-APP.onrender.com/
2. Source dimensions: 1920 x 1080. Set OBS canvas accordingly.
3. Stream: YouTube RTMPS. Enter YouTube stream key only in OBS.
4. Output: H.264, CBR 4000-10000 Kbps, keyframes every 2 seconds.
5. Keep STREAM_ENABLED=false on Render when OBS is broadcasting.
The Render server can alternatively stream directly without OBS.
