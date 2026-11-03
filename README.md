# ElectionCast 2026 — Render + YouTube Live

**A working starter system** for continuous U.S. midterm election results coverage on a single Render Docker web service. Includes live results polling, rolling headlines, a public TV dashboard, offline voice commentary, and an FFmpeg RTMPS encoder. All narration is derived from reported vote-count changes and **never announces a projected winner**.

## Important scope and safeguards

- Open America's 2026 public election feed is **partial coverage (22 participating states as of 2026-11-03)**, not a complete national election feed. The UI says so, never treats omitted races as zero, and does not claim control of either chamber.
- House, Senate and Governor feeds refresh every 60 seconds with conditional ETags; Google News RSS headlines refresh every 180 seconds. The news ticker is *headlines only*, not a license to rebroadcast copyrighted video, full articles, or make election calls.
- No race-call or projected winner data is supplied by Open America; *leading* is different from *winning*. No national seat-control projections are inferred.
- Narration is offline English text-to-speech via `espeak-ng`, and triggers only for substantial new vote counts after a baseline fetch. Speech is intentionally silent until a qualifying verified change. All counts are unofficial.
- For professional, comprehensive national coverage, add a properly licensed full-coverage results provider. The bundled connector is usable without API keys but does not cover all 50 states.
- The application is not yet deployed: you must provide a Render account, YouTube live access, and a private stream key.

## Fastest Render deployment

1. Unzip this project and create a **private GitHub repository**. Push the contents (the `render.yaml` must be in its root).
2. Open [Render Blueprints](https://dashboard.render.com/blueprints) > **New Blueprint Instance**, connect your GitHub repo, and accept the Blueprint.
3. The `render.yaml` sets **`plan: pro`** (2 CPU/4 GB RAM, legacy name; use bigger compute if FFmpeg drops frames). This is a *paid* continuously running web service. The Blueprint creates the dashboard at `https://YOUR-SERVICE.onrender.com`.
4. During setup, provide `YOUTUBE_STREAM_KEY` only as a **Render secret environment variable**. The default `STREAM_ENABLED=false` deliberately prevents accidental broadcasting. Keep it off until the dashboard is verified.
5. Check `/api/health` and `/api/results` and open the homepage. Before polls close it is normal to see no vote counts. If a source is offline, `/api/health` lists errors.
6. At [YouTube Live Control Room](https://studio.youtube.com/), enable live streaming if needed, create your stream and obtain the **RTMPS URL and stream key**. YouTube can take up to 24 hours to enable first-time live streaming.
7. On Render > Service > Environment, enter the RTMPS URL from YouTube under `YOUTUBE_RTMPS_URL` (the Blueprint includes YouTube's usual RTMPS URL; use the actual URL shown in your account) and the secret stream key. Set `STREAM_ENABLED=true` and redeploy. The encoder begins pushing video+AAC audio. It retries after disconnects.
8. Verify connection, bitrate and stream health in YouTube Live Control Room; click **Go Live** where YouTube requires manual confirmation.
9. To stop broadcasting, set `STREAM_ENABLED=false` and redeploy, or stop the Render service/YouTube stream. **Never expose your stream key in your repository or logs.**

**Expected compute cost:** the bundled `pro` size corresponds to Render's 2-CPU, 4-GB paid instance; check current Render pricing before launch. Streaming at ~4 Mbps constantly will generate significant outbound transfer charges. This package has not been load-tested on Render.

## Test before broadcasting

On a machine with Docker:

```bash
docker build -t electioncast:2026 .
docker run --rm -p 10000:10000 -e DEMO_MODE=1 -e STREAM_ENABLED=false electioncast:2026
```

Open `http://localhost:10000`: the UI will prominently say **SIMULATED DEMO DATA**. Never enable a public stream while `DEMO_MODE=1` unless you're explicitly presenting a demo.

For live dashboard without streaming:

```bash
docker run --rm -p 10000:10000 -e DEMO_MODE=0 -e STREAM_ENABLED=false electioncast:2026
```

To test the full encoder **without uploading to YouTube**, run a local RTMP server you control and point the configuration there; the bundled startup enforces both stream URL and stream key. Do not share production keys or embed them in commands that get recorded in shell history. For OBS-based streaming, see `obs/README.txt`.

## API

| Route | Purpose |
|---|---|
| `/` | Broadcast-safe dashboard (1920×1080 design; responsive) |
| `/api/results` | Normalized official-source race data, headlines, source diagnostics |
| `/api/narration` | Data-verified vote-change announcements (not breaking-news claims) |
| `/api/health` | Health status and per-feed fetch errors |

## Configuration

| Environment key | Default | Description |
|---|---|---|
| `DEMO_MODE` | `0` | `1` uses **simulated** data, clearly watermarked |
| `STREAM_ENABLED` | `false` | `true` starts Chromium/Xvfb/FFmpeg to YouTube |
| `NARRATION_ENABLED` | `true` | Controls voice announcement API |
| `POLL_SECONDS` | `60` | Polling interval; do not set lower than 60 |
| `YOUTUBE_RTMPS_URL` | YouTube RTMPS | Copy from YouTube Live Control Room |
| `YOUTUBE_STREAM_KEY` | empty | Sensitive! Render secret only |
| `OUTPUT_WIDTH` | `1280` | Encoder output width |
| `OUTPUT_HEIGHT` | `720` | Encoder output height |
| `VIDEO_BITRATE` | `4000k` | H.264 target bitrate |

## Operations

- Render's `/api/health` endpoint can be used for monitoring. Check the **last successful fetch**, not merely HTTP 200; individual upstream feeds can fail while the app remains healthy.
- Re-deploying or changing environment variables interrupts the stream. On single-instance web service deployments, expect reconnects.
- `Xvfb` and Chromium render the dashboard for FFmpeg; the public webpage can also be loaded by OBS from a separate computer.
- The encoder captures a 1920×1080 browser canvas but scales to 1280×720 at 30 fps by default, with H.264/AAC. Set `OUTPUT_WIDTH=1920`, `OUTPUT_HEIGHT=1080`, and adjust `VIDEO_BITRATE` only after load testing on Render. See [YouTube recommended encoder settings](https://support.google.com/youtube/answer/2853702).
- The narrator uses lightweight `espeak-ng`. It is fully offline and requires no AI key or hosted TTS license, but is a robotic voice. Upgrade voice quality using a licensed TTS provider before a commercial broadcast if desired.
- The dashboard is deliberately source-attributed and marks RSS headlines as unverified. Avoid implying that Google News verifies results, or using headlines as narration source.
- Public access to the dashboard is by design. Do not place secrets in query strings or frontend JavaScript.

## Sources

- Open America election API: https://openamerica.io/elections/api/
- Google News RSS search (headlines only): https://news.google.com/rss
- Render Blueprint docs: https://render.com/docs/infrastructure-as-code
- YouTube RTMPS docs: https://support.google.com/youtube/answer/10364924

## Future upgrades

A licensed full-coverage API, independently attributable race calls, an archive of result snapshots, a higher-quality licensed TTS service, broadcast alerts, and stronger encoder supervision would make this suitable for higher-stakes production use. The current deliverable is deployable starter software, **not a guarantee of full national election coverage or nonstop broadcasting**.
