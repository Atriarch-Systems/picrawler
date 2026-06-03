# spiderquad-agentd

Local control/sense HTTP API for **atriarch-spider-quad** (SunFounder PiCrawler).

## License boundary (important)

This daemon is **GPLv3** (it ships in the picrawler fork and imports
`picrawler` / `robot_hat` / `picamera2`). Closed-source clients such as **Virali**
talk to it **only over HTTP** and must **never import picrawler** — the process/
network boundary keeps them at arm's length (mere aggregation), so they stay
independently licensed. Commands, sensor readings, audio and image bytes crossing
the wire are just data.

## Run

```bash
# normal user (NO sudo — dp_admin is in gpio/i2c/spi groups; sudo splits the
# offset config to /root). Flask + requests + psutil already present.
python3 agentd.py
```

Or as a service (survives reboot / SSH drops):

```bash
sudo cp spiderquad-agentd.service /etc/systemd/system/
sudo systemctl enable --now spiderquad-agentd
```

Env: `SQ_PORT` (8970), `SQ_MIC` (`plughw:3,0` USB mic),
`SQ_SPK` (`plughw:CARD=sndrpihifiberry,DEV=0` I2S DAC, mono).

Binds `0.0.0.0`, no auth — intended for the trusted LAN/VPN only.

## API

Sense (from robot):
- `GET /health`
- `GET /stats` → battery V/%, Pi cpu/mem/temp/throttle+undervoltage flags, uptime
- `GET /camera/snapshot` → `image/jpeg`
- `GET /sonar` → `{distance_cm}`
- `GET /mic/capture?seconds=N&gain=<dB>` → `audio/wav` (16k mono; `gain` boosts the weak mic)

Act (to robot):
- `POST /move`  `{action, steps, speed, auto_stand?, auto_sit?}` — gaits (forward/backward/turn left/turn right/...)
- `POST /pose`  `{name|coords, speed}` — stand/sit/custom
- `POST /speak` `{text, volume?}` — on-robot TTS (pico2wave/espeak)
- `POST /play`  raw `audio/wav` body, or JSON `{url}`, `?volume=0-100` — play audio out the speaker
- `POST /volume` `{level}`

## Notes / TODO

- No IMU on the base — attitude-blind. Planned: BNO086 (UART-RVC) for roll/pitch/turn behind a `/attitude` endpoint.
- Routine player (declarative animation docs) to be added — keeps paid/closed routine data independently licensed.
- Streaming (MJPEG / audio) can be added later; v1 is request/response.
