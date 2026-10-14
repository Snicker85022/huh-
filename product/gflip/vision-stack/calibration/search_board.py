import cv2, os, sys, time, json
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from onvif import ONVIFCamera
from calib_utils import detect_board

log = open('/tmp/search.log','a')
def w(m): log.write(m+'\n'); log.flush(); print(m)

STREAM = 'rtsp://localhost:8554/ptz_h264'
SIZE_MM = int(sys.argv[1]) if len(sys.argv)>1 else 300
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'captures', 'sweep')

cam = ONVIFCamera('192.168.2.117', 80, 'admin', 'admin')
ptz = cam.create_ptz_service(); media = cam.create_media_service()
tok = media.GetProfiles()[0].token

def move(pan, tilt):
    req = ptz.create_type('AbsoluteMove'); req.ProfileToken = tok
    req.Position = {'PanTilt': {'x': pan, 'y': tilt}, 'Zoom': {'x': 0.0}}
    ptz.AbsoluteMove(req)

def grab():
    cap = cv2.VideoCapture(STREAM, cv2.CAP_FFMPEG)
    cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 8000)
    ok, frame = cap.read(); cap.release()
    return frame if ok else None

positions = [(p,t) for p in [0,0.5,1,-0.5,-1] for t in [0,0.3,-0.3]]
for pan, tilt in positions:
    w(f'move pan={pan} tilt={tilt}')
    try: move(pan, tilt)
    except Exception as e: w(f'move err {e}')
    time.sleep(3)
    frame = grab()
    if frame is None:
        w('grab failed'); continue
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    corners, ids = detect_board(gray, SIZE_MM)
    n = 0 if ids is None else len(ids)
    w(f'pan={pan} tilt={tilt} corners={n}')
    if n >= 6:
        path = os.path.join(OUT, f'found_pan{pan}_tilt{tilt}.jpg')
        cv2.imwrite(path, frame)
        w(f'FOUND board at pan={pan} tilt={tilt}, saved {path}')
        sys.exit(0)
w('not found')
sys.exit(1)
