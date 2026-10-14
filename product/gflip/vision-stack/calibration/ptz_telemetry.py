"""Command-history telemetry for the PTZ camera (no real telemetry available).

Dead-reckons pan/tilt degrees and zoom from move commands.
Speed constants are APPROXIMATE and must be re-anchored against visual references.
"""
import sqlite3, os, time, json, datetime

DB = os.path.expanduser('~/vision-stack/world/world.db')
STATE = os.path.expanduser('~/vision-stack/world/ptz_state.json')

PAN_DEG_PER_S = 15.0    # measured ~90 deg in 6s at vel 1.0 (one zoom level)
TILT_DEG_PER_S = 15.0   # assumed
ZOOM_PER_S = 1.0/15.0   # full zoom range in ~15s at vel 1.0 (assumed)
PAN_SIGN = -1           # +1 pan = camera RIGHT; -1 = LEFT (user-confirmed)

def _load():
    if os.path.exists(STATE):
        return json.load(open(STATE))
    return {'pan_deg':0.0,'tilt_deg':0.0,'zoom':0.0}

def _save(st):
    st['ts'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    json.dump(st, open(STATE,'w'))

def get_state():
    return _load()

def apply_move(pan_vel, tilt_vel, zoom_vel, duration_s):
    st = _load()
    st['pan_deg'] += PAN_SIGN * pan_vel * duration_s * PAN_DEG_PER_S
    st['tilt_deg'] += tilt_vel * duration_s * TILT_DEG_PER_S
    st['zoom'] = max(0.0, min(1.0, st['zoom'] + zoom_vel * duration_s * ZOOM_PER_S))
    _save(st)
    db = sqlite3.connect(DB)
    db.execute('INSERT INTO ptz_log(pan_vel,tilt_vel,zoom_vel,duration_s,est_pan_deg,est_tilt_deg,est_zoom,note) VALUES(?,?,?,?,?,?,?,?)',
               (pan_vel,tilt_vel,zoom_vel,duration_s,st['pan_deg'],st['tilt_deg'],st['zoom'],'dead-reckoned'))
    db.commit(); db.close()
    return st

def record_move(pan, tilt, zoom):
    """Call when a move starts."""
    json.dump({'start_ts': time.time(), 'pan': pan, 'tilt': tilt, 'zoom': zoom},
              open('/tmp/ptz_move_start.json','w'))

def record_stop():
    """Call when a move stops; computes duration and applies dead-reckoning."""
    try:
        m = json.load(open('/tmp/ptz_move_start.json'))
        dur = time.time() - m['start_ts']
        if dur < 0.05: dur = 0.05
        if dur > 3600: dur = 0
        return apply_move(m['pan'], m['tilt'], m['zoom'], dur)
    except Exception:
        return get_state()

if __name__ == '__main__':
    import sys
    if sys.argv[1] == 'state':
        print(get_state())
