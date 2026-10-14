import cv2, os, sys, time, json
from onvif import ONVIFCamera
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'captures', 'abs')
os.makedirs(OUT, exist_ok=True)
CAM='rtsp://192.168.2.117:554/stream0?username=admin&password=E10ADC3949BA59ABBE56E057F20F883E'
DICT=cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_1000)
det=cv2.aruco.ArucoDetector(DICT)
cam=ONVIFCamera('192.168.2.117',80,'admin','admin')
ptz=cam.create_ptz_service(); media=cam.create_media_service(); tok=media.GetProfiles()[0].token
cap=cv2.VideoCapture(CAM, cv2.CAP_FFMPEG); cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC,8000); cap.set(cv2.CAP_PROP_BUFFERSIZE,1)
def absmove(x,y,z=0.0):
    req=ptz.create_type('AbsoluteMove'); req.ProfileToken=tok
    req.Position={'PanTilt':{'x':float(x),'y':float(y)},'Zoom':{'x':float(z)}}
    ptz.AbsoluteMove(req)
def grab():
    f=None
    for _ in range(30):
        ok,fr=cap.read()
        if ok: f=fr
    return f
def known(ids):
    ks=[]
    for i in ids:
        if 300<=i<=365: ks.append(f'L-series({i})')
        elif 0<=i<=257: ks.append(f'small({i})')
        else: ks.append(f'unknown({i})')
    return ks
res=[]
tilts=[0.6,0.3,0.0,-0.3,-0.6]
pans=[-1.0,-0.5,0.0,0.5,1.0]
for t in tilts:
    for p in pans:
        absmove(p,t); time.sleep(1.8)
        f=grab()
        if f is None:
            print(f'pan{p:+.2f} tilt{t:+.2f}: NO FRAME'); continue
        g=cv2.cvtColor(f,cv2.COLOR_BGR2GRAY)
        corners,ids,_=det.detectMarkers(g)
        idsl=[] if ids is None else [int(i) for i in ids.flatten()]
        tag=f'pan{p:+.2f}_tilt{t:+.2f}'.replace('+','p').replace('-','m')
        cv2.imwrite(os.path.join(OUT,tag+'.jpg'), f)
        res.append({'pan':p,'tilt':t,'ids':idsl,'n':len(idsl)})
        print(f'  pan{p:+.2f} tilt{t:+.2f}: {len(idsl)} markers {known(idsl) if idsl else ""}')
json.dump(res, open(os.path.join(OUT,'markers.json'),'w'), indent=2)
got=[r for r in res if r['n']>0]
print(f"\nDONE: {len(res)} positions, {len(got)} had markers")
for r in got: print("   HIT", r['pan'], r['tilt'], r['ids'])
cap.release()
