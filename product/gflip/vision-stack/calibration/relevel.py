import cv2, time, json, base64, urllib.request, numpy as np
from onvif import ONVIFCamera
CAM='rtsp://192.168.2.117:554/stream0?username=admin&password=E10ADC3949BA59ABBE56E057F20F883E'
cam=ONVIFCamera('192.168.2.117',80,'admin','admin')
ptz=cam.create_ptz_service(); media=cam.create_media_service(); tok=media.GetProfiles()[0].token
cap=cv2.VideoCapture(CAM, cv2.CAP_FFMPEG); cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC,8000)
def frame():
    f=None
    for _ in range(25):
        ok,fr=cap.read()
        if ok: f=fr
    return f
def nudge(pan,tilt,secs):
    r=ptz.create_type('ContinuousMove'); r.ProfileToken=tok
    r.Velocity={'PanTilt':{'x':float(pan),'y':float(tilt)},'Zoom':{'x':0.0}}
    r.Timeout='PT6S'
    ptz.ContinuousMove(r); time.sleep(secs); ptz.Stop({'ProfileToken':tok,'PanTilt':True,'Zoom':True})
def vlm(f):
    ok,buf=cv2.imencode('.jpg',f); b=base64.b64encode(buf.tobytes()).decode()
    q="Indoor commercial kitchen PTZ still. Reply with ONE word first (DOWN/LEVEL/UP) then a few words on what big objects are visible (racks, fridges, ovens, counter, people, ceiling, floor)."
    req=urllib.request.Request('http://127.0.0.1:11434/api/generate',
        data=json.dumps({"model":"llava:7b","prompt":q,"images":[b],"stream":False}).encode(),
        headers={'Content-Type':'application/json'})
    return json.loads(urllib.request.urlopen(req,timeout=180).read().decode()).get('response','').strip().replace('\n',' ')
def g(f): return cv2.resize(cv2.cvtColor(f,cv2.COLOR_BGR2GRAY),(320,180))

# try ONVIF home first
try:
    ptz.GotoHomePosition({'ProfileToken':tok,'Speed':{'PanTilt':{'x':1.0,'y':1.0}}}); print("GotoHomePosition sent"); time.sleep(4)
except Exception as e: print("GotoHome err:",e)

prev=frame()
if prev is None: print("NO FRAME from camera stream"); raise SystemExit
print("start:", vlm(prev))
sign=-1.0
stalls=0
for i in range(10):
    nudge(0,sign,1.5); time.sleep(1.0)
    f=frame()
    if f is None: print(f"step{i+1}: no frame"); continue
    d=float(np.mean(cv2.absdiff(g(prev),g(f))))
    v=vlm(f); cv2.imwrite(f'/tmp/relevel_{i+1}.jpg',f)
    print(f"step {i+1} (tilt {sign:+.0f}) diff {d:5.1f} :: {v}")
    if d<4.0:
        stalls+=1
        if stalls>=2 and sign<0:
            print("-> no movement; flipping direction to +1"); sign=+1.0; stalls=0
        elif stalls>=2:
            print("-> camera not responding to either direction"); break
    else:
        stalls=0
    if 'LEVEL' in v.upper(): print("-> LEVEL reached"); break
    prev=f
cap.release()
