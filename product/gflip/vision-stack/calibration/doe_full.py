"""FULL-FACTORIAL DOE (2x2x2) — the design matrix Nick specified.
 A Camera state : Vis(IrCutFilter=ON,colour)  vs  IR(IrCutFilter=OFF,mono+IR LEDs)
 B On-axis light: Off vs On   <-- on THIS camera the only on-axis emitter is the IR LED,
                                 which is GANGED to A=IR. No independent white spotlight found.
 C Off-axis aux : Off vs On   <-- requires a separate diffuse light; NOT remote-controllable yet.

 Metrics (per run): Laplacian variance (sub-pixel edge sharpness),
   shadow-zone noise / SNR, Shannon histogram entropy.
"""
import cv2, time, os, json, csv, numpy as np
from onvif import ONVIFCamera
CAM='rtsp://127.0.0.1:8554/ptz_h264'
OUT=os.path.join(os.path.dirname(os.path.abspath(__file__)),'captures','doe_full'); os.makedirs(OUT,exist_ok=True)
cam=ONVIFCamera('192.168.2.117',80,'admin','admin')
media=cam.create_media_service(); imaging=cam.create_imaging_service(); VS=media.GetVideoSources()[0].token
cap=cv2.VideoCapture(CAM, cv2.CAP_FFMPEG); cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC,8000)
DICT=cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_1000); DET=cv2.aruco.ArucoDetector(DICT)
def _sat_of(bgr):
    hsv=cv2.cvtColor(bgr,cv2.COLOR_BGR2HSV); return float(hsv[:,:,1].mean())
def set_cut(cut, verify=True):
    """Set IrCutFilter and WAIT until the frame actually reflects it (mode changes are slow/sticky)."""
    r=imaging.create_type('SetImagingSettings'); r.VideoSourceToken=VS
    r.ImagingSettings={'IrCutFilter':cut,'Sharpness':160.0,
                       'WideDynamicRange':{'Mode':'OFF','Level':128.0},
                       'BacklightCompensation':{'Mode':'OFF','Level':0.0},
                       'Exposure':{'Mode':'AUTO','ExposureTime':1000.0}}
    try: r.ForcePersistence=True
    except Exception: pass
    imaging.SetImagingSettings(r)
    want_mono = (str(cut).upper()=='OFF')
    for attempt in range(8):
        time.sleep(2.0)
        f=grab()
        if f is None: continue
        sat=_sat_of(f)
        mono = sat < 12.0        # IR mode -> near-zero colour saturation
        if (not verify) or (mono==want_mono and (attempt>=1 or not want_mono)):
            return f
    return f
def grab():
    f=None
    for _ in range(28):
        ok,fr=cap.read()
        if ok: f=fr
    return f
def metrics(bgr):
    g=cv2.cvtColor(bgr,cv2.COLOR_BGR2GRAY).astype(np.float32)
    lap=float(cv2.Laplacian(g,cv2.CV_32F).var())
    thr=float(np.percentile(g,25)); shadow=g<thr
    if int(shadow.sum())>200:
        s=g[shadow]; snr=float(s.mean()/(s.std()+1e-6))
        loc=cv2.blur(g,(7,7)); lv=cv2.blur((g-loc)**2,(7,7))
        snews=float(np.sqrt(np.clip(lv[shadow],0,None)).mean())
    else: snr=0.0; snews=0.0
    hist=np.histogram(g,bins=256,range=(0,255))[0].astype(np.float64); p=hist/hist.sum(); p=p[p>0]
    ent=float(-(p*np.log2(p)).sum())
    c,ids,_=DET.detectMarkers(g.astype(np.uint8)); idsl=[] if ids is None else [int(x) for x in ids.flatten()]
    # laplacian variance restricted to the darkest 10% (shadow-bound detail)
    dk=g<=float(np.percentile(g,10)); lap_shadow=float(cv2.Laplacian(g,cv2.CV_32F).var()) if dk.sum()<100 else float(np.var(np.diff(g[dk])))
    hsv=cv2.cvtColor(bgr,cv2.COLOR_BGR2HSV)
    return dict(focus_var=round(lap,1), shadow_noise=round(snews,2), snr=round(snr,2),
                entropy=round(ent,3), bright=round(float(g.mean()),1), sat=round(float(hsv[:,:,1].mean()),1),
                markers=len(idsl), marker_ids=idsl)
# ---- the 8-run matrix; runnable=False where we lack the hardware ----
RUNS=[
 (1,'Vis','Off','Off',True,  'baseline control'),
 (2,'Vis','On','Off', False, 'needs white spotlight (camera has none)'),
 (3,'Vis','Off','On', False, 'needs off-axis diffused VIS light'),
 (4,'Vis','On','On',  False, 'needs both'),
 (5,'IR','Off','Off', True,  'IR ambient'),
 (6,'IR','On','Off',  True,  'IR LEDs (ganged to IR mode on this hw)'),
 (7,'IR','Off','On',  False, 'needs off-axis diffused IR light'),
 (8,'IR','On','On',   False, 'needs both'),
]
REPEATS=3
rows=[]; skipped=[]
for run,state,b,c,runnable,note in RUNS:
    if not runnable:
        skipped.append(dict(run=run,state=state,onaxis=b,offaxis=c,note=note)); continue
    first=set_cut('ON' if state=='Vis' else 'OFF')
    for rep in range(REPEATS):
        f=first if rep==0 and first is not None else grab()
        if f is None: continue
        name=f'run{run}_{state}_B{b}_C{c}_rep{rep}'
        cv2.imwrite(os.path.join(OUT,name+'.jpg'), f, [cv2.IMWRITE_JPEG_QUALITY,95])
        m=metrics(f); m.update(run=run,state=state,onaxis=b,offaxis=c,rep=rep,file=name+'.jpg'); rows.append(m)
        print(f"  run{run} {state:3s} B={b} C={c} rep{rep}: focus {m['focus_var']:9.1f} shadowNoise {m['shadow_noise']:6.2f} SNR {m['snr']:6.2f} entropy {m['entropy']:.3f} sat {m['sat']:5.1f} markers {m['markers']}")
set_cut('AUTO')
json.dump({'rows':rows,'skipped':skipped}, open(os.path.join(OUT,'doe_full.json'),'w'), indent=2)
if rows:
    with open(os.path.join(OUT,'doe_full.csv'),'w',newline='') as fh:
        w=csv.DictWriter(fh,fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
# summary by run
print("\n--- RUN SUMMARY (mean over repeats) ---")
import statistics as st
for run,state,b,c,runnable,note in RUNS:
    rs=[r for r in rows if r['run']==run]
    if not rs: print(f"  run{run}: NOT RUNNABLE - {note}"); continue
    print(f"  run{run} {state:3s} B={b} C={c}: focus {st.mean(r['focus_var'] for r in rs):9.1f} | shadowNoise {st.mean(r['shadow_noise'] for r in rs):6.2f} | SNR {st.mean(r['snr'] for r in rs):6.2f} | entropy {st.mean(r['entropy'] for r in rs):.3f}")
cap.release()
print("\nskipped runs (need hardware):")
for s in skipped: print("  ",s)
