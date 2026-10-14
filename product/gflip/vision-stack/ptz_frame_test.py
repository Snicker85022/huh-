import cv2, time, subprocess
url='rtsp://localhost:8554/ptz_h264'
def grab(tag):
    cap=cv2.VideoCapture(url, cv2.CAP_FFMPEG)
    cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 8000)
    ok, frame=cap.read()
    if ok:
        cv2.imwrite(f'/tmp/ptz_{tag}.jpg', frame)
        print(tag, 'ok', frame.shape)
    else:
        print(tag, 'FAILED')
    cap.release()
    return frame if ok else None

a=grab('before')
# continuous move right for 5s
from onvif import ONVIFCamera
cam=ONVIFCamera('192.168.2.117',80,'admin','admin')
ptz=cam.create_ptz_service(); media=cam.create_media_service(); tok=media.GetProfiles()[0].token
req=ptz.create_type('ContinuousMove'); req.ProfileToken=tok
req.Velocity={'PanTilt':{'x':1.0,'y':0.0},'Zoom':{'x':0.0}}
ptz.ContinuousMove(req); time.sleep(5)
req2=ptz.create_type('Stop'); req2.ProfileToken=tok; req2.PanTilt=True; req2.Zoom=True
ptz.Stop(req2); time.sleep(1)
b=grab('after')
if a is not None and b is not None:
    import numpy as np
    diff=np.abs(a.astype(np.int16)-b.astype(np.int16)).mean()
    print('mean_abs_diff:', diff)
    print('identical' if diff<1 else 'CHANGED')
