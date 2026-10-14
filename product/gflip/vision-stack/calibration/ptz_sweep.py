import cv2, os, sys, time, json
import numpy as np
from onvif import ONVIFCamera

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
STREAM = os.environ.get('VISION_STREAM_URL', 'rtsp://192.168.2.117:554/stream0?username=admin&password=E10ADC3949BA59ABBE56E057F20F883E')
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'captures', 'sweep')
os.makedirs(OUT, exist_ok=True)

cam = ONVIFCamera('192.168.2.117', 80, 'admin', 'admin')
ptz = cam.create_ptz_service()
media = cam.create_media_service()
tok = media.GetProfiles()[0].token

def abs_move(pan, tilt, zoom=0.0):
    req = ptz.create_type('AbsoluteMove')
    req.ProfileToken = tok
    req.Position = {'PanTilt': {'x': pan, 'y': tilt}, 'Zoom': {'x': zoom}}
    ptz.AbsoluteMove(req)

def grab(tag):
    cap = cv2.VideoCapture(STREAM, cv2.CAP_FFMPEG)
    cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 10000)
    ok, frame = cap.read()
    cap.release()
    if ok:
        path = os.path.join(OUT, tag + '.jpg')
        cv2.imwrite(path, frame)
        print('saved', path, frame.shape)
    else:
        print('grab failed', tag)
    return ok

def main():
    positions = [(-1,0),(-0.5,0),(0,0),(0.5,0),(1,0),(0,-0.5),(0,0.5),(-0.5,-0.5),(-0.5,0.5),(0.5,-0.5),(0.5,0.5)]
    meta = []
    for pan, tilt in positions:
        print('moving to pan', pan, 'tilt', tilt)
        try:
            abs_move(pan, tilt)
        except Exception as e:
            print('move err', e)
        time.sleep(3)
        tag = f'pan{pan:+0.2f}_tilt{tilt:+0.2f}'
        if grab(tag):
            meta.append({'tag': tag, 'pan': pan, 'tilt': tilt})
    with open(os.path.join(OUT, 'meta.json'), 'w') as f:
        json.dump(meta, f, indent=2)
    print('sweep done,', len(meta), 'frames')

if __name__ == '__main__':
    main()
