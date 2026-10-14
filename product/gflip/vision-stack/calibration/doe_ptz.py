"""DOE: PTZ optical-mode factorial. Factors controllable via ONVIF Imaging.
   F1 IrCutFilter  : ON  (visible/colour, IR-cut IN)  vs OFF (IR/night, IR LEDs, mono)
   F2 ExposureMode : AUTO vs MANUAL (ExposureTime set)
   F3 Sharpness    : 128 vs 255
   F4 WDR          : OFF vs ON
   F5 BacklightCmp : OFF vs ON
   Responses: brightness, saturation, focus(Laplacian var), edge%, mean gradient,
              local contrast, + ArUco marker count.
   NOTE: 'IR illuminator' is physically ganged to F1=OFF on this camera (its own IR LEDs).
"""
import cv2, time, os, json, csv, itertools, numpy as np
from onvif import ONVIFCamera
CAM='rtsp://127.0.0.1:8554/ptz_h264'
OUT=os.path.join(os.path.dirname(os.path.abspath(__file__)),'captures','doe'); os.makedirs(OUT,exist_ok=True)
cam=ONVIFCamera('192.168.2.117',80,'admin','admin')
media=cam.create_media_service(); imaging=cam.create_imaging_service()
VS=media.GetVideoSources()[0].token
cap=cv2.VideoCapture(CAM, cv2.CAP_FFMPEG); cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC,8000); cap.set(cv2.CAP_PROP_BUFFERSIZE,1)
DICT=cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_1000); DET=cv2.aruco.ArucoDetector(DICT)
def setmode(cut,expmode,exptime,sharp,wdr,blc):
    s={'IrCutFilter':cut,'Sharpness':float(sharp),
       'WideDynamicRange':{'Mode':wdr,'Level':128.0},
       'BacklightCompensation':{'Mode':blc,'Level':0.0},
       'Exposure':{'Mode':expmode,'ExposureTime':float(exptime)}}
    r=imaging.create_type('SetImagingSettings'); r.VideoSourceToken=VS; r.ImagingSettings=s
    try: r.ForcePersistence=True
    except Exception: pass
    imaging.SetImagingSettings(r)
def grab():
    f=None
    for _ in range(28):
        ok,fr=cap.read()
        if ok: f=fr
    return f
def metrics(bgr):
    g=cv2.cvtColor(bgr,cv2.COLOR_BGR2GRAY)
    lap=cv2.Laplacian(g,cv2.CV_64F).var()
    gx=cv2.Sobel(g,cv2.CV_32F,1,0,ksize=3); gy=cv2.Sobel(g,cv2.CV_32F,0,1,ksize=3)
    mag=cv2.magnitude(gx,gy)
    canny=cv2.Canny(cv2.GaussianBlur(g,(3,3),0),60,160)
    blur=cv2.blur(g,(9,9)); lc=float(np.std(g.astype(np.float32)-blur.astype(np.float32)))
    hsv=cv2.cvtColor(bgr,cv2.COLOR_BGR2HSV)
    c,ids,_=DET.detectMarkers(g); idsl=[] if ids is None else [int(x) for x in ids.flatten()]
    return dict(bright=round(float(g.mean()),1), sat=round(float(hsv[:,:,1].mean()),1),
                focus=round(float(lap),1), edge_pct=round(float((canny>0).mean()*100),2),
                grad_mean=round(float(mag.mean()),2), local_contrast=round(lc,2),
                markers=len(idsl), marker_ids=idsl)
runs=[]
plan=[]
for cut in ['ON','OFF']:
    for expmode,exptime in [('AUTO',1000),('MANUAL',8000)]:
        for sharp in [128,255]:
            plan.append(dict(cut=cut,expmode=expmode,exptime=exptime,sharp=sharp,wdr='OFF',blc='OFF'))
for cut in ['ON','OFF']:
    plan.append(dict(cut=cut,expmode='AUTO',exptime=1000,sharp=160,wdr='ON',blc='OFF'))
    plan.append(dict(cut=cut,expmode='AUTO',exptime=1000,sharp=160,wdr='OFF',blc='ON'))
print(f"DOE: {len(plan)} runs")
for i,p in enumerate(plan):
    setmode(p['cut'],p['expmode'],p['exptime'],p['sharp'],p['wdr'],p['blc']); time.sleep(2.6)
    f=grab()
    if f is None: print(f"  run {i:02d} NO FRAME"); continue
    name=f"{i:02d}_cut{p['cut']}_exp{p['expmode']}{p['exptime']}_sh{p['sharp']}_wdr{p['wdr']}_blc{p['blc']}".replace(' ','')
    cv2.imwrite(os.path.join(OUT,name+'.jpg'), f, [cv2.IMWRITE_JPEG_QUALITY,95])
    m=metrics(f); m.update(p); m['run']=i; m['file']=name+'.jpg'; runs.append(m)
    print(f"  run {i:02d}: {p['cut']:3s} exp={p['expmode']:6s}{p['exptime']:<6d} sh={p['sharp']} wdr={p['wdr']} blc={p['blc']} -> focus {m['focus']:8.1f} edge% {m['edge_pct']:5.2f} grad {m['grad_mean']:6.2f} lc {m['local_contrast']:6.2f} sat {m['sat']:5.1f}")
# restore
setmode('AUTO','AUTO',1000,160,'OFF','OFF')
json.dump(runs, open(os.path.join(OUT,'doe.json'),'w'), indent=2)
with open(os.path.join(OUT,'doe.csv'),'w',newline='') as fh:
    w=csv.DictWriter(fh, fieldnames=list(runs[0].keys())); w.writeheader(); w.writerows(runs)
print("saved doe.json + doe.csv; restored AUTO")
cap.release()
