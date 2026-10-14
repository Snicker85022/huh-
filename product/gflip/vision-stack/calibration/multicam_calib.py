"""Multi-camera ChArUco calibration.
   Cameras: ptz (h264), webcam (n100), mt1, mt2 (IP Webcam :8080).
   Strategy: DOE-optimal PTZ optics (IrCutFilter=ON, AUTO exp, sharp160, WDR/BLC off).
   Off-axis trick: PTZ can ILLUMINATE (IR LEDs / white LED) while the webcam WATCHES.
"""
import cv2, time, os, json, numpy as np
OUT=os.path.join(os.path.dirname(os.path.abspath(__file__)),'captures','multicam'); os.makedirs(OUT,exist_ok=True)
DICT=cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_1000); DET=cv2.aruco.ArucoDetector(DICT)
CAMS={'ptz':'rtsp://127.0.0.1:8554/ptz_h264','webcam':'rtsp://127.0.0.1:8554/webcam',
      'mt1':'http://192.168.2.104:8080/photo.jpg','mt2':'http://192.168.2.108:8080/photo.jpg'}
def grab(name,url,n=22):
    if url.endswith('.jpg'):
        import urllib.request
        try:
            d=urllib.request.urlopen(url,timeout=6).read()
            return cv2.imdecode(np.frombuffer(d,np.uint8),cv2.IMREAD_COLOR)
        except Exception as e: print(f"  {name}: {e}"); return None
    cap=cv2.VideoCapture(url, cv2.CAP_FFMPEG); cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC,8000)
    f=None
    for _ in range(n):
        ok,fr=cap.read()
        if ok: f=fr
    cap.release(); return f
def detect(img):
    g=cv2.cvtColor(img,cv2.COLOR_BGR2GRAY)
    c,ids,_=DET.detectMarkers(g); idsl=[] if ids is None else [int(x) for x in ids.flatten()]
    boards={}
    for (sx,sy,sq,tag) in [(5,7,12,'small5x7_12mm'),(2,6,34,'L2x6_34mm')]:
        b=cv2.aruco.CharucoBoard((sx,sy),sq/1000.0,(sq/1000.0)*0.8,DICT); cd=cv2.aruco.CharucoDetector(b)
        try:
            cc,ci,mc,mi=cd.detectBoard(g); boards[tag]=0 if ci is None else len(ci)
        except Exception: boards[tag]=0
    return {'raw':idsl,'boards':boards,'shape':img.shape[:2]}
res={}
for name,url in CAMS.items():
    f=grab(name,url)
    if f is None: print(f"  {name:7s} DEAD"); res[name]={'alive':False}; continue
    cv2.imwrite(f'{OUT}/{name}.jpg', f); d=detect(f); d['alive']=True; res[name]=d
    print(f"  {name:7s} OK {d['shape']} raw={d['raw']} boards={d['boards']}")
json.dump(res, open(f'{OUT}/multicam_detect.json','w'), indent=2)
print("saved", OUT)
