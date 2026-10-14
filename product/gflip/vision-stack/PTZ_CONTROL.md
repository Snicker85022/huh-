# PTZ CONTROL MODEL — READ THIS BEFORE TOUCHING THE CAMERA
> The PTZ control contract was re-derived **7–8 times**. This file, `app/ptz_control.py`
> (`MODEL` dict + `selftest()`), the `/api/ptz/model` endpoint, and the `ptz_camera` facts
> in `world.db` are the **one** source of truth. **Do not re-learn — read this.**

**Device** HD975B-P · ONVIF mfr `ONVIF_ICAMERA` · fw `V3.4.6.3` · `192.168.2.117:80` admin/admin · node `ptz0`
**Quick check any session:** `venv/bin/python3 app/ptz_control.py selftest`  (or `GET /api/ptz/model`)

## Move — the ONLY thing that works
- **ONVIF `ContinuousMove`** with `Velocity.PanTilt={x,y}` in `[-1,1]`.
- **`Timeout` is MANDATORY** (e.g. `PT4S`) — without it the camera **ignores** the move.
- **Set `Timeout == the duration you want`**, then **`Stop(PanTilt=True,Zoom=True)`**.
  A long Timeout keeps moving past your Stop and the next command **overlaps → runaway**.
- **Signs:** `pan +1 = RIGHT`, `pan -1 = LEFT` · **`tilt -1 = UP`, `tilt +1 = DOWN`** (inverted!).
- Full tilt travel ≈ **9 s**. The camera **parks at the bottom of travel (looking down)** — so a
  `+1`(down) command when it's already bottomed out looks like *"no movement"*. It is NOT broken.

## Broken — never use
| Call | Reality |
|---|---|
| `GetStatus` | telemetry is fake: always `(0,0,0)` |
| `AbsoluteMove` | advertised (±1) but **does not move the camera** |
| `RelativeMove` | unreliable |
| `GotoHomePosition` | SOAP fault "Unknown error" |

## Imaging (WORKS — rare on a cam this cheap)
`VideoSourceToken = 'VideoSourceMain'`
- **`IrCutFilter`: `ON`** = visible/colour (IR-cut in) · **`OFF`** = IR/night (IR-cut out, **IR LEDs on**, mono) · `AUTO`
- Brightness, Contrast, ColorSaturation, Sharpness (1–255) · Exposure `Mode` AUTO|MANUAL `ExposureTime` 100–100000 µs · WDR · BacklightCompensation · WhiteBalance
- **~2–3 s settle** after a change — sleep before you grab a frame, or your data is confounded.

## Video
Read the H.264 transcode in OpenCV: `rtsp://127.0.0.1:8554/ptz_h264` (stream0 is HEVC → POC noise).

## DOE result (2026-10-08) — best optical config for edges
- **Best:** `IrCutFilter=ON`, `Exposure=AUTO`, `Sharpness≈128–160`, **`WDR=OFF`, `BLC=OFF`**
- **WDR ON and BacklightCompensation ON HURT** (focus 710–1220 vs 2000–3360, edge% ~2.7 vs ~8.7). Keep OFF.
- IR(`OFF`) wins in low light; visible(`ON`) keeps colour. Scripts: `calibration/doe_ptz.py`, `calibration/ai_dsp.py`

## App endpoints
`/api/ptz/move?pan=&tilt=&zoom=&secs=` · `/api/ptz/stop` · `/api/ptz/state` · `/api/ptz/status`
`/api/ptz/ir?mode=on|off|auto` · `/api/ptz/imaging` · `/api/ptz/imaging/set?...` · `/api/ptz/model` · `/api/ptz/selftest`



## WHITE LEDs / ILLUMINATION — camera HAS them; control still UNPROVEN (updated 2026-10-08)
**Existence: CONFIRMED.** Nick (2026-10-08) has the camera manual (the file is corrupted and would
not OCR — needs a fresh copy). Independent proof: the ONVIF PTZ node `ptz0` advertises auxiliary
commands `tt:Lamp|On`, `tt:Lamp|Off`, `tt:Wiper|On`, `tt:Wiper|Off`. The Dahua UI JS additionally
names `white_led_panel`, `hasDoubleLedPanel`, `SmartDualLight`, `LightOn`/`LightOff`,
`StartNightInfraredMode`/`StartNightColorMode`.

**CORRECTION — `SendAuxiliaryCommand` is NOT broken.** The previous session recorded it as a fault.
The fault was OUR client bug: the request element must be `<AuxiliaryData>`, **not** `<AuxiliaryCommand>`.
Working call (`app/ptz_control.py -> onvif_aux()`): `POST http://192.168.2.117/PTZ`
(ns `http://www.onvif.org/ver20/ptz/wsdl`) with WS-Security UsernameToken digest, body
`<SendAuxiliaryCommand><ProfileToken>MainStream</ProfileToken><AuxiliaryData>tt:Lamp|On</AuxiliaryData></SendAuxiliaryCommand>`.

**Result: accepted, but INERT.** `tt:Lamp|On` -> HTTP 200; `tt:Wiper|On|Off` -> 200;
`tt:Lamp|Off` -> `ActionNotSupported`. **No optical change measured:** a 20 s continuous RTSP frame
series is flat (frame-mean delta 0.01) across Lamp|On and Lamp|Off, in both day and IR/night. The
measurement chain is validated — `IrCutFilter` ON->OFF moves the frame mean by 29.3.
`DeviceIO` (`/DeviceIO`) is advertised with `RelayOutputs=1`, but `GetRelayOutputs` ->
`ActionNotSupported` (advertised-but-not-implemented, same class as `AbsoluteMove`).

**The remaining gate is the DEVICE WEB PASSWORD.** `/cgi-bin/getuid?username=admin&password=admin`
answers `password error` — the Dahua web/CGI API is alive, but the password is NOT the ONVIF
`admin/admin`. `POST /IPC` still 202-accepts every body (unauthenticated), so it proves nothing.
The white light is most likely gated behind the Dahua config (`white_led_panel` / `SmartDualLight`),
reachable only with that password. **Unknown — needs Nick.**

Code: `app/ptz_control.py -> onvif_aux()/lamp_on()/lamp_off()/wiper_on()/wiper_off()` (correct form,
inert effect), plus the legacy `rpc()/aux()/light_*()` (unverified; needs a real web session).

### PROVEN vs UNPROVEN (as of 2026-10-08)
| PROVEN | UNPROVEN |
|---|---|
| ContinuousMove + Timeout + Stop | white LED / spotlight control (accepted-but-inert via ONVIF) |
| pan +1=RIGHT | night-mode switching via Dahua web RPC (needs the web password) |
| tilt -1=UP, +1=DOWN (~9 s travel) | DeviceIO relay output (advertised, not implemented) |
| ONVIF Imaging (IrCutFilter/brightness/…/exposure) | |
| GetStatus=zeros, AbsoluteMove inert, GotoHome faults | |
| SendAuxiliaryCommand IS implemented — needs `<AuxiliaryData>`, effect inert | |
| read H.264 transcode `rtsp://127.0.0.1:8554/ptz_h264` | |
