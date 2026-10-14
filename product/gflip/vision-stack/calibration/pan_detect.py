import cv2, time, os, json
from onvif import ONVIFCamera
CAM='rtsp://127.0.0.1:8554/ptz_h264'
cam=ONVIFCamera('192.168.2.117',80,'admin','admin'); ptz=cam.create_ptz_service()
media=cam.create_media_service(); tok=media.GetProfiles()[0].token
cap=cv2.VideoCapture(CAM, cv2.CAP_FFMPEG); cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC,8000); cap.set(cv2.CAP_PROP_BUFFERSIZE,1)
DICT=cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_1000)
det=cv2.aruco.ArucoDetector(DICT)
OUT=os.path.join(os.path.dirname(os.path.abspath(__file__)),'captures','pan'); os.makedirs(OUT,exist_ok=True)
def cmove(pan,tilt,secs):
    r=ptz.create_type('ContinuousMove'); r.ProfileToken=tok
    r.Velocity={'PanTilt':{'x':float(pan),'y':float(tilt)},'Zoom':{'x':0.0}}; r.Timeout='PT10S'
    ptz.ContinuousMove(r); time.sleep(secs); ptz.Stop({'ProfileToken':tok,'PanTilt':True,'Zoom':True})
def grab():
    f=None
    for _ in range(12):
        ok,fr=cap.read()
        if ok: f=fr
    return f
hits=[]
for i in range(16):
    cmove(1.0,0.0,1.5); time.sleep(0.7)
    f=grab()
    if f is None: print(f"step {i:02d}: no frame"); continue
    g=cv2.cvtColor(f,cv2.COLOR_BGR2GRAY)
    c,ids,_=det.detectMarkers(g)
    idsl=[] if ids is None else [int(x) for x in ids.flatten()]
    cv2.imwrite(os.path.join(OUT,f'pan_{i:02d}.jpg'), f)
    print(f"  step {i:02d}: {len(idsl):2d} markers {idsl}")
    if idsl: hits.append({'step':i,'ids':idsl})
json.dump(hits, open(os.path.join(OUT,'hits.json'),'w'))
print("HITS:",hits)
cap.release()
