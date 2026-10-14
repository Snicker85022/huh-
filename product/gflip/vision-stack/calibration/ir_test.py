import cv2, time, numpy as np
from onvif import ONVIFCamera
CAM='rtsp://192.168.2.117:554/stream0?username=admin&password=E10ADC3949BA59ABBE56E057F20F883E'
cam=ONVIFCamera('192.168.2.117',80,'admin','admin')
media=cam.create_media_service(); imaging=cam.create_imaging_service()
st=media.GetVideoSources()[0].token
cap=cv2.VideoCapture(CAM, cv2.CAP_FFMPEG); cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC,8000)
def set_ir(mode):
    r=imaging.create_type('SetImagingSettings')
    r.VideoSourceToken=st; r.ImagingSettings={'IrCutFilter':mode}
    try: r.ForcePersistence=True
    except Exception: pass
    imaging.SetImagingSettings(r)
    return getattr(imaging.GetImagingSettings({'VideoSourceToken':st}),'IrCutFilter',None)
def grab():
    f=None
    for _ in range(25):
        ok,fr=cap.read()
        if ok: f=fr
    return f
def sat(f):
    hsv=cv2.cvtColor(cv2.resize(f,(640,360)),cv2.COLOR_BGR2HSV)
    return float(hsv[:,:,1].mean())
DICT=cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_1000); det=cv2.aruco.ArucoDetector(DICT)
for mode in ['ON','OFF','AUTO']:
    got=set_ir(mode); time.sleep(3)
    f=grab()
    if f is None: print(mode,"no frame"); continue
    g=cv2.cvtColor(f,cv2.COLOR_BGR2GRAY)
    c,ids,_=det.detectMarkers(g); idsl=[] if ids is None else [int(x) for x in ids.flatten()]
    cv2.imwrite(f'/tmp/ir_{mode}.jpg', f)
    print(f"IrCutFilter={got:5s}  meanSaturation={sat(f):6.1f}  markers={idsl}  brightness={g.mean():.1f}")
cap.release()
