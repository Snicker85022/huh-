# PTZ CAMERA CONTROL — QUICK REFERENCE (superseded by ../PTZ_CONTROL.md — read that first)
**Device:** HD975B-P  ·  ONVIF manufacturer `ONVIF_ICAMERA`  ·  fw `V3.4.6.3 build 2026-04-23`
**Net:** `192.168.2.117:80` admin/admin · profiles `MainStream`,`SubStream` · PTZ node token `ptz0`
**Code:** `app/ptz_control.py` (single source of truth) — imported by `app/main.py`

> Re-derived 7–8 times. This file + `ptz_control.py` + the `ptz_camera` facts in `world.db`
> are the authoritative record. **Do not re-learn from scratch.**

## Moving the camera — the ONLY thing that works
1. **ONVIF `ContinuousMove`** — requires `Timeout` (e.g. `PT6S`) or the camera **ignores** it.
   `Velocity.PanTilt = {x: pan∈[-1,1], y: tilt∈[-1,1]}`, `Zoom={x}`.
   **pan x=+1 → pans RIGHT; x=-1 → LEFT.**  **tilt y=-1 = UP, y=+1 = DOWN** (inverted vs ONVIF);
   the camera parks at the bottom of travel (looking down), so a `+1`(down) command when already
   bottomed out looks like 'no motion' — it is NOT broken. Full tilt travel ~9 s.
2. **ALWAYS follow with `Stop(PanTilt=True, Zoom=True)`** — otherwise the move runs for the full Timeout.

## Things that DO NOT work (stop trying)
| Call | Result |
|---|---|
| `GetStatus` (telemetry) | always returns `(0,0,0)` — broken. **Never trust it.** |
| `AbsoluteMove` | advertised (±1 spaces) but **does not move the camera** |
| `RelativeMove` | advertised; unreliable |
| `GotoHomePosition` | SOAP fault: "Unknown error" |

## Hardware state right now (2026-10-08)
- **PAN works reliably** (x=+1 RIGHT).
- **TILT WORKS — sign is INVERTED from the ONVIF convention:**
  `y = -1 = UP`, `y = +1 = DOWN`. Full tilt travel ≈ **9 s** at |vel|=1.
  The camera *parks at the bottom of its travel* (looking down) — so `+1` appears to
  do nothing when it is already bottomed out. That is what looked like a dead motor.
- ⚠️ **Move-overlap gotcha:** if `Timeout` is longer than the intended move, the camera
  keeps moving past your `Stop` and the *next* command overlaps it → erratic results.
  **Set `Timeout == intended duration`** (e.g. `PT4S` for a 4 s move).

## Imaging / IR mode switching — WORKS via ONVIF Imaging (rare!)
`VideoSourceToken = 'VideoSourceMain'`
- **`IrCutFilter`**: `ON` = IR-cut in = visible/daylight colour · `OFF` = IR-cut out = IR/night (IR LEDs) · `AUTO`
- Brightness, Contrast, ColorSaturation (1–255) · Sharpness (1–255) · Exposure `Mode` AUTO|MANUAL,
  `ExposureTime` 100–100000 µs · BacklightCompensation · WideDynamicRange · WhiteBalance
- App endpoints: `GET /api/ptz/ir?mode=on|off|auto`, `GET /api/ptz/imaging`,
  `GET /api/ptz/imaging/set?IrCutFilter=OFF&Brightness=140&Sharpness=200&ExposureTime=800`

## Video
- **Read the H.264 transcode** `rtsp://127.0.0.1:8554/ptz_h264` in OpenCV (clean).
- `stream0` is HEVC → OpenCV emits `Could not find ref with POC` mid-GOP noise (still usable).
- Direct: `rtsp://192.168.2.117:554/stream0?username=admin&password=E10ADC3949BA59ABBE56E057F20F883E`

## App endpoints
- `GET /api/ptz/move?pan=&tilt=&zoom=&secs=` (also logs to `ptz_log`)
- `GET /api/ptz/stop`
- `GET /api/ptz/state` (dead-reckoned, approximate) · `GET /api/ptz/status` (imaging + raw position)
- `GET /api/ptz/ir?mode=` · `GET /api/ptz/imaging` · `GET /api/ptz/imaging/set?...`
