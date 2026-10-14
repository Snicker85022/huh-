"""PTZ PATROL + OBSERVATION COLLECTOR.

WHY THIS DID NOT EXIST BEFORE (2026-10-08): nothing was scheduled. The sweep
scripts in calibration/ are one-shot, the vision app's capture_loop only keeps
the newest frame in RAM and overwrites it, and world.db held exactly 2
observation rows. Nothing recorded, so nothing could be learned from.

WHY IT IS OPEN-LOOP: this camera reports NO position telemetry (GetStatus is
always 0,0,0) and AbsoluteMove does nothing (both PROVEN, see ptz_control.py
MODEL). The only working control is ONVIF ContinuousMove + Timeout + Stop, so a
patrol is a TIMED pattern rather than a sequence of absolute poses, and it WILL
drift over a long run. That is a known, accepted limitation, not a bug.

Each stop: one clean frame from the H.264 transcode -> YOLOv8n -> JPEG on disk
-> one observations row. Clean means no boxes burned into the pixels, because
these frames are the raw material for a future training set.
"""
import os, sys, time, json, sqlite3, datetime, signal

import cv2
import numpy as np

APP = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(APP)
sys.path.insert(0, APP)

import ptz_control as PTZ                      # the proven control contract
from qc_vision import yolo_detect              # reuse the one detector
import activity                                # hands + human activity

DB = os.path.join(ROOT, 'world', 'world.db')
OUT = os.path.join(ROOT, 'calibration', 'captures', 'patrol')
H264 = PTZ.MODEL['video']['open_with']         # rtsp://127.0.0.1:8554/ptz_h264
RAW = os.environ.get('PATROL_RAW_URL', 'http://127.0.0.1:8090/snapshot/ptz_raw.jpg')
LOCK = '/tmp/taza_ptz.lock'                    # cooperative: another job owns the camera

STEP_S   = float(os.environ.get('PATROL_STEP_S', 2.0))    # pan per stop
STOPS    = int(os.environ.get('PATROL_STOPS', 6))
LEVEL_S  = float(os.environ.get('PATROL_LEVEL_S', 4.0))   # tilt -1 (UP) to get off the bottom
ROW_S    = float(os.environ.get('PATROL_ROW_S', 1.5))     # tilt +1 (DOWN) between rows
ROWS     = int(os.environ.get('PATROL_ROWS', 2))
GAP_S    = float(os.environ.get('PATROL_GAP_S', 90.0))    # idle between patrols
CAPTURE  = int(os.environ.get('PATROL_CAPTURE', 1))       # frames per stop

_running = True


def _stop(sig, frm):
    global _running
    _running = False
    print('[patrol] signal', sig, '- finishing cycle then exiting', flush=True)


def _busy():
    """Yield to anything else that owns the camera (a QC verify, a calibration)."""
    try:
        if os.path.exists(LOCK) and (time.time() - os.path.getmtime(LOCK)) < 60:
            return True
    except Exception:
        pass
    return False


def _try_move(pan, tilt, secs):
    """Move, but never let a dead camera inflate the dead-reckoned estimate."""
    try:
        PTZ.continuous_move(pan, tilt, 0, secs)
        return True
    except Exception as e:
        print('[patrol] move failed:', type(e).__name__, str(e)[:120], flush=True)
        return False


def _fetch_raw(timeout=6):
    """One clean frame from the app. The app already owns the RTSP connection;
    a second reader on the same stream was the cause of the 'no frame' failures."""
    try:
        import urllib.request
        req = urllib.request.Request(RAW, headers={'User-Agent': 'taza-patrol/1.0'})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            b = r.read()
        if not b:
            return None
        return cv2.imdecode(np.frombuffer(b, np.uint8), cv2.IMREAD_COLOR)
    except Exception as e:
        print('[patrol] fetch failed:', type(e).__name__, e, flush=True)
        return None


def _db():
    c = sqlite3.connect(DB, timeout=20)
    try:
        c.execute('PRAGMA busy_timeout=20000')
        c.execute('PRAGMA journal_mode=WAL')
    except Exception:
        pass
    return c


def observe(ts, tag, frame, dets, act, pan_est, tilt_est):
    """One row in observations - the vision stack's existing store. No new tables."""
    labels = [d['label'] for d in dets]
    note = json.dumps({
        'frame': tag, 'detections': dets[:20],
        'pan_est_deg': round(pan_est, 1), 'tilt_est_deg': round(tilt_est, 1),
        'source': 'patrol:v1', 'telemetry': 'none (open-loop timed pattern)',
    })[:4000]
    try:
        c = _db()
        c.execute("""INSERT INTO observations
                     (ts, camera, subject, predicate, value, unit, confidence, method, roi, note)
                     VALUES (?,?,?,?,?,?,?,?,?,?)""",
                  (ts, 'ptz', tag, 'detections', float(len(dets)), 'count', 0.5,
                   'patrol:v1+yolov8n', '', note))
        # second row: what the HANDS are doing
        if act and act.get('hands'):
            c2 = _db()
            c2.execute("""INSERT INTO observations
                         (ts, camera, subject, predicate, value, unit, confidence, method, roi, note)
                         VALUES (?,?,?,?,?,?,?,?,?,?)""",
                      (ts, 'ptz', tag, 'hands', float(len(act['hands'])), 'count', 0.5,
                       'activity:v1+' + str(act.get('hands_source')), '',
                       json.dumps({'hands': act['hands'][:8],
                                   'people': act.get('people_count'),
                                   'pan_est_deg': round(pan_est, 1),
                                   'tilt_est_deg': round(tilt_est, 1)})[:3000]))
            c2.commit(); c2.close()
        c.commit(); c.close()
    except Exception as e:
        print('[patrol] observe failed:', e, flush=True)


def patrol_once(pan_est=0.0, tilt_est=0.0, cap=None):
    """One full pass. Returns updated (pan_est, tilt_est) dead-reckoned guesses."""
    day = datetime.datetime.now().strftime('%Y-%m-%d')
    d = os.path.join(OUT, day)
    os.makedirs(d, exist_ok=True)

    print(f'[patrol] cycle start, pan~{pan_est:.0f} tilt~{tilt_est:.0f}', flush=True)

    # re-reference: drive UP off the bottom limit so rows are repeatable-ish.
    # ONLY integrate the dead-reckon when the camera actually accepted the move.
    if _try_move(0, -1, LEVEL_S):
        tilt_est -= LEVEL_S * 15.0
    else:
        print('[patrol] camera unreachable - skipping cycle', flush=True)
        return pan_est, tilt_est
    time.sleep(0.6)

    for row in range(ROWS):
        direction = 1.0 if row % 2 == 0 else -1.0     # snake back and forth
        for stop in range(STOPS):
            if not _running:
                return pan_est, tilt_est
            if _busy():
                print('[patrol] camera busy elsewhere - yielding 10s', flush=True)
                time.sleep(10); continue

            ts = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            stamp = datetime.datetime.now().strftime('%H%M%S')
            for k in range(max(1, CAPTURE)):
                f = _fetch_raw()
                if f is None:
                    print(f'[patrol] r{row} s{stop}: no frame', flush=True)
                    continue
                tag = f'patrol_{day.replace("-","")}_{stamp}_r{row}s{stop}'
                path = os.path.join(d, tag + '.jpg')
                cv2.imwrite(path, f, [cv2.IMWRITE_JPEG_QUALITY, 92])
                try:
                    dets = yolo_detect(f)
                except Exception as e:
                    dets = []; print('[patrol] yolo failed:', e, flush=True)
                try:
                    act = activity.analyze(f)
                except Exception as e:
                    act = None; print('[patrol] activity failed:', e, flush=True)
                observe(ts, tag, f, dets, act, pan_est, tilt_est)
                hz = [h.get('zone') for h in (act or {}).get('hands', [])][:4]
                print(f'[patrol] r{row} s{stop} -> {len(dets)} det '
                      f'{[d["label"] for d in dets][:4]} | hands {(act or {}).get("hands_source")} {hz}',
                      flush=True)

            if _try_move(direction, 0, STEP_S):            # pan to next stop
                pan_est += direction * STEP_S * 15.0
            time.sleep(0.4)

        if row < ROWS - 1:
            if _try_move(0, 1, ROW_S):                     # tilt DOWN a row
                tilt_est += ROW_S * 15.0
            time.sleep(0.4)

    return pan_est, tilt_est


def main():
    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)
    os.makedirs(OUT, exist_ok=True)
    print(f'[patrol] start  step={STEP_S}s stops={STOPS} rows={ROWS} '
          f'level={LEVEL_S}s gap={GAP_S}s  stream={H264}', flush=True)

    cap = cv2.VideoCapture(H264, cv2.CAP_FFMPEG)
    cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 10000)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    pan_est = tilt_est = 0.0
    while _running:
        try:
            pan_est, tilt_est = patrol_once(pan_est, tilt_est, cap)
        except Exception as e:
            print('[patrol] cycle error:', type(e).__name__, e, flush=True)
        if pan_est > 1440 or pan_est < -1440: pan_est = 0.0
        if tilt_est > 180 or tilt_est < -180: tilt_est = 0.0
        if not _running:
            break
        print(f'[patrol] cycle done, idling {GAP_S:.0f}s', flush=True)
        for _ in range(int(GAP_S)):
            if not _running:
                break
            time.sleep(1)
    try:
        cap.release()
    except Exception:
        pass
    print('[patrol] stopped', flush=True)


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--once':
        cap = cv2.VideoCapture(H264, cv2.CAP_FFMPEG)
        cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 10000)
        print('one cycle:', patrol_once(0.0, 0.0, cap))
        cap.release()
    else:
        main()
