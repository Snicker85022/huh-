import os, sys, time, threading, asyncio
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'calibration'))
import ptz_telemetry
import cv2, numpy as np
import onnxruntime as ort
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, StreamingResponse, Response, JSONResponse

APP_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(APP_DIR)
MODEL = os.path.join(ROOT, 'models', 'yolov8n.onnx')
STREAM_URL = os.environ.get('VISION_STREAM_URL', 'rtsp://localhost:8554/ptz_h264')

CLASSES = [
    'person','bicycle','car','motorcycle','airplane','bus','train','truck','boat',
    'traffic light','fire hydrant','stop sign','parking meter','bench','bird','cat',
    'dog','horse','sheep','cow','elephant','bear','zebra','giraffe','backpack','umbrella',
    'handbag','tie','suitcase','frisbee','skis','snowboard','sports ball','kite',
    'baseball bat','baseball glove','skateboard','surfboard','tennis racket','bottle',
    'wine glass','cup','fork','knife','spoon','bowl','banana','apple','sandwich','orange',
    'broccoli','carrot','hot dog','pizza','donut','cake','chair','couch','potted plant',
    'bed','dining table','toilet','tv','laptop','mouse','remote','keyboard','cell phone',
    'microwave','oven','toaster','sink','refrigerator','book','clock','vase','scissors',
    'teddy bear','hair drier','toothbrush'
]
COLORS = [(np.random.default_rng(i).integers(80,255,3).tolist()) for i in range(len(CLASSES))]

sess = ort.InferenceSession(MODEL, providers=['CPUExecutionProvider'])
INP = sess.get_inputs()[0].name
print(f'[vision] model={MODEL} input={INP}')

cap = cv2.VideoCapture(STREAM_URL, cv2.CAP_FFMPEG)
cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 8000)
cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

lock = threading.Lock()
latest = None
running = True

def capture_loop():
    global latest
    while running:
        ok, frame = cap.read()
        if ok:
            with lock:
                latest = frame.copy()
        else:
            time.sleep(0.5)

threading.Thread(target=capture_loop, daemon=True).start()

def letterbox(img, new=(640,640), color=(114,114,114)):
    h, w = img.shape[:2]
    r = min(new[0]/h, new[1]/w)
    nw, nh = int(round(w*r)), int(round(h*r))
    resized = cv2.resize(img, (nw, nh))
    dw = (new[1]-nw)/2
    dh = (new[0]-nh)/2
    top, bottom = int(round(dh-0.1)), int(round(dh+0.1))
    left, right = int(round(dw-0.1)), int(round(dw+0.1))
    return cv2.copyMakeBorder(resized, top, bottom, left, right, cv2.BORDER_CONSTANT, value=color), r, dw, dh

def detect(frame, conf_th=0.45):
    h, w = frame.shape[:2]
    img, r, dw, dh = letterbox(frame)
    blob = cv2.cvtColor(img, cv2.COLOR_BGR2RGB).transpose(2,0,1)[None].astype(np.float32)/255.0
    out = sess.run(None, {INP: blob})[0][0].T   # 8400x84
    boxes = []
    for row in out:
        scores = row[4:]
        conf = float(scores.max())
        if conf < conf_th:
            continue
        cls = int(scores.argmax())
        cx, cy, bw, bh = row[:4]
        x1 = cx - bw/2; y1 = cy - bh/2; x2 = cx + bw/2; y2 = cy + bh/2
        # denormalize to letterbox pixels then to original
        x1 = (x1 - dw) / r; y1 = (y1 - dh) / r
        x2 = (x2 - dw) / r; y2 = (y2 - dh) / r
        x1 = max(0, min(w, x1)); y1 = max(0, min(h, y1))
        x2 = max(0, min(w, x2)); y2 = max(0, min(h, y2))
        boxes.append([x1, y1, x2, y2, conf, cls])
    if boxes:
        boxes = np.array(boxes, dtype=np.float32)
        idx = cv2.dnn.NMSBoxes(boxes[:,:4].tolist(), boxes[:,4].tolist(), conf_th, 0.45)
        if len(idx):
            return boxes[idx.flatten()]
    return np.array([])

def draw(frame):
    import datetime as _dt
    ts = _dt.datetime.now().strftime('%H:%M:%S.%f')[:-3]
    cv2.putText(frame, ts, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0,255,255), 2)
    dets = detect(frame)
    for x1, y1, x2, y2, conf, cls in dets:
        color = COLORS[int(cls) % len(COLORS)]
        cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), color, 2)
        label = f'{CLASSES[int(cls)]} {conf:.2f}'
        cv2.putText(frame, label, (int(x1), max(20,int(y1)-6)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
    return frame, dets

def latest_frame():
    with lock:
        return None if latest is None else latest.copy()


# ---- PTZ control: CANONICAL module (ptz_control.py) — the single source of truth ----
import ptz_control as PTZ

def ptz_move(pan=0.0,tilt=0.0,zoom=0.0,secs=1.0):
    try: return PTZ.continuous_move(pan,tilt,zoom,secs=secs)
    except Exception as e:
        print('[vision] ptz_move err:',e); return False

def ptz_stop():
    try: return PTZ.stop()
    except Exception as e:
        print('[vision] ptz_stop err:',e); return False

app = FastAPI(title='Vision QC')
from calib_routes import register as register_calib
register_calib(app)

# ---- QC presence/absence vision (qc_vision.py) ----
from qc_vision import register as register_qc
register_qc(app)

# ---- QC bootstrap capture: picture-required photo + .gif clip (qc_capture.py) ----
from qc_capture import register as register_capture
register_capture(app)



VERSION = "0.1.0"
RELEASE_STATUS = "bootstrapping"   # Nick 2026-10-08: v0.1 now, target v0.8 before this stops being the priority
TARGET_VERSION = "0.8"

@app.get('/api/version')
def api_version():
    """Self-report. A cold agent should hit this before trusting anything else here."""
    return {
        "app": "vision-app",
        "version": VERSION,
        "status": RELEASE_STATUS,
        "target_version": TARGET_VERSION,
        "scope": "Mom's Table QC + PTZ bootstrap (gflip, 192.168.2.107)",
        "warning": ("QC verdicts are ADVISORY ONLY. C-2026-10-08-002 (labelled accuracy "
                    "harness) has not reported a precision number, so no verdict may gate "
                    "shipping product."),
        "endpoints": ["/qc", "/api/qc/verify", "/api/qc/status", "/api/qc/cards",
                      "/api/ptz/model", "/api/ptz/selftest", "/api/version"],
    }

@app.get('/calib/annotated2.jpg')
def calib_annotated2():
    import pathlib
    p = pathlib.Path(APP_DIR) / 'annotated2.jpg'
    if not p.exists():
        return Response(b'not found', status_code=404)
    return Response(p.read_bytes(), media_type='image/jpeg')

@app.get('/calib/annotated.jpg')
def calib_annotated():
    import pathlib
    p = pathlib.Path(APP_DIR) / 'annotated.jpg'
    if not p.exists():
        return Response(b'not found', status_code=404)
    return Response(p.read_bytes(), media_type='image/jpeg')

@app.get('/api/calib/status')
def calib_status():
    import json
    p = os.path.join(ROOT, 'calibration', 'status.json')
    try:
        return JSONResponse(json.load(open(p)))
    except Exception:
        return JSONResponse({'state':'unknown'})


@app.get('/api/ptz/state')
def ptz_state_ep():
    return JSONResponse(ptz_telemetry.get_state())

@app.get('/api/ptz/move')
def ptz_move_ep(pan: float=0.0, tilt: float=0.0, zoom: float=0.0, secs: float=1.0):
    ptz_telemetry.record_move(pan,tilt,zoom)
    ok = ptz_move(pan,tilt,zoom,secs)
    st = ptz_telemetry.record_stop()
    return JSONResponse({'ok': ok, 'secs': secs})

@app.get('/api/ptz/stop')
def ptz_stop_ep():
    st = ptz_telemetry.record_stop()
    return JSONResponse({'ok': ptz_stop(), 'state': st})

# ---- PTZ imaging / IR mode switching (see app/ptz_control.py) ----
@app.get('/api/ptz/ir')
def ptz_ir_ep(mode: str='auto'):
    return JSONResponse(PTZ.set_ir(mode))

@app.get('/api/ptz/imaging')
def ptz_imaging_get_ep():
    return JSONResponse(PTZ.get_imaging())

@app.get('/api/ptz/imaging/set')
def ptz_imaging_set_ep(IrCutFilter: str=None, Brightness: int=None, Contrast: int=None,
                       ColorSaturation: int=None, Sharpness: int=None,
                       ExposureTime: float=None, ExposureMode: str=None):
    kw={}
    if IrCutFilter: kw['IrCutFilter']=IrCutFilter.upper()
    for k,v in (('Brightness',Brightness),('Contrast',Contrast),('ColorSaturation',ColorSaturation),('Sharpness',Sharpness)):
        if v is not None: kw[k]=float(v)
    if ExposureTime is not None: kw['ExposureTime']=ExposureTime
    if ExposureMode: kw['ExposureMode']=ExposureMode.upper()
    return JSONResponse(PTZ.set_imaging(**kw))

@app.get('/api/ptz/status')
def ptz_status_ep():
    return JSONResponse({'imaging': PTZ.get_imaging(), 'position': PTZ.position_status()})

@app.get('/api/ptz/light')
def ptz_light_ep(on: int=1):
    return JSONResponse({'LightOn' if on else 'LightOff': PTZ.light_on() if on else PTZ.light_off()})

@app.get('/api/ptz/night')
def ptz_night_ep(mode: str='color'):
    m=str(mode).lower()
    return JSONResponse({m: PTZ.night_ir() if m in ('ir','bw','mono') else PTZ.night_color()})

@app.get('/api/ptz/aux')
def ptz_aux_ep(code: str):
    return JSONResponse({code: PTZ.aux(code)})

@app.get('/api/ptz/model')
def ptz_model_ep():
    return JSONResponse(PTZ.MODEL)

@app.get('/api/ptz/selftest')
def ptz_selftest_ep():
    return JSONResponse(PTZ.selftest())

@app.get('/api/cameras')
def cameras():
    return JSONResponse([
        {'id':'ptz','name':'PTZ HD975B-P','stream_hls':'/hls/ptz_h264/index.m3u8','mjpeg':'/streams/ptz.mjpg','ai':True},
        {'id':'usb','name':'USB webcam (pending driver)','ai':False},
        {'id':'mt1','name':'MT1 (pending ADB auth)','ai':False},
        {'id':'mt2','name':'MT2 (pending ADB auth)','ai':False},
    ])

@app.get('/snapshot/ptz_raw.jpg')
def snapshot_raw():
    """Clean frame, NO detection boxes burned in - this is the training-data feed."""
    frame = latest_frame()
    if frame is None:
        return Response(b'', status_code=503)
    ok, buf = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 92])
    return Response(buf.tobytes(), media_type='image/jpeg')

@app.get('/snapshot/ptz.jpg')
def snapshot():
    frame = latest_frame()
    if frame is None:
        return Response(b'', status_code=503)
    frame, dets = draw(frame)
    ok, buf = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
    return Response(buf.tobytes(), media_type='image/jpeg')

@app.get('/streams/ptz.mjpg')
def stream():
    def gen():
        while True:
            frame = latest_frame()
            if frame is not None:
                frame, _ = draw(frame)
                ok, buf = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
                if ok:
                    yield b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + buf.tobytes() + b'\r\n'
            time.sleep(0.08)
    return StreamingResponse(gen(), media_type='multipart/x-mixed-replace; boundary=frame')

@app.get('/', response_class=HTMLResponse)
def index():
    return HTMLResponse(open(os.path.join(APP_DIR, 'index.html')).read())

# ---------------- z33 browser-camera ingest (added this session) ----------------
latest_z33 = None
_z33_lock = threading.Lock()

@app.get('/z33', response_class=HTMLResponse)
def z33_page():
    return HTMLResponse(open(os.path.join(APP_DIR, 'z33cam.html')).read())

@app.post('/z33/frame')
async def z33_frame(request: Request):
    global latest_z33
    body = await request.body()
    if body[:2] == b'\xff\xd8':            # valid JPEG SOI
        with _z33_lock:
            latest_z33 = body
        return JSONResponse({'ok': True, 'bytes': len(body)})
    return JSONResponse({'ok': False, 'bytes': len(body)}, status_code=400)

@app.get('/streams/z33.mjpg')
def z33_mjpg():
    def gen():
        while True:
            with _z33_lock:
                b = latest_z33
            if b:
                yield b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + b + b'\r\n'
            time.sleep(0.1)
    return StreamingResponse(gen(), media_type='multipart/x-mixed-replace; boundary=frame')

@app.get('/api/z33/status')
def z33_status():
    with _z33_lock:
        n = len(latest_z33) if latest_z33 else 0
    return JSONResponse({'receiving': n > 0, 'last_frame_bytes': n})
