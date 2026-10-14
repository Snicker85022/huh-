"""HUMAN-ACTIVITY + HAND OBSERVATION LAYER.

WHAT IT DOES
  Given one frame it returns a structured record of what people's HANDS are
  doing: per-person body pose (the wrists drive the hands), optional MediaPipe
  hand landmarks, and which named image zone each wrist occupies. The patrol
  loop calls this per stop and writes the record to world.db observations.

WHAT IT IS NOT
  It does not learn yet. Learning needs a target and labels. What is possible
  without hand-labelling is UNSUPERVISED - cluster wrist tracks over time into
  recurring routines. That is a separate, staged candidate, not something to
  build quietly underneath this one.

HONEST LIMITS
  - The PTZ reports NO position telemetry (GetStatus is always 0,0,0) and
    AbsoluteMove does nothing, so a wrist's IMAGE position cannot be promoted to
    a WORLD position without a solved camera pose. Zones are IMAGE zones today.
  - yolov8n-pose gives 17 body keypoints; wrists are indices 9 and 10. That is
    HAND POSITION, not finger articulation.
  - MediaPipe Hands gives 21 landmarks per hand (finger articulation) but is
    view-dependent and slow on CPU. It is optional and degrades to pose-only.
"""
import os, cv2, numpy as np

KP_NAMES = ['nose', 'left_eye', 'right_eye', 'left_ear', 'right_ear',
            'left_shoulder', 'right_shoulder', 'left_elbow', 'right_elbow',
            'left_wrist', 'right_wrist', 'left_hip', 'right_hip',
            'left_knee', 'right_knee', 'left_ankle', 'right_ankle']
ARMS = {'left_wrist': 9, 'right_wrist': 10, 'left_elbow': 7, 'right_elbow': 8}
HAND_KP = {'left_wrist', 'right_wrist'}

POSE_MODEL = os.environ.get('POSE_MODEL',
                            '/home/taza/vision-stack/models/yolov8n-pose.pt')
HAND_MODEL = os.environ.get('HAND_MODEL',
                            '/home/taza/vision-stack/models/hand_landmarker.task')
POSE_CONF = float(os.environ.get('POSE_CONF', 0.35))
KP_CONF = float(os.environ.get('POSE_KP_CONF', 0.30))
USE_MEDIAPIPE = os.environ.get('ACTIVITY_MEDIAPIPE', '1') == '1'

_pose = None
_mp = None
_mp_tried = False


def _pose_model():
    global _pose
    if _pose is None:
        from ultralytics import YOLO
        _pose = YOLO(POSE_MODEL)
    return _pose


def _hand_landmarker():
    """MediaPipe TASKS HandLandmarker (mediapipe>=1.0 dropped the legacy
    .solutions API). 21 landmarks per hand = finger articulation. Falls back to
    None so the caller runs pose-wrists only."""
    global _mp, _mp_tried
    if not USE_MEDIAPIPE:
        return None
    if _mp is None and not _mp_tried:
        _mp_tried = True
        try:
            from mediapipe.tasks import python as mpp
            from mediapipe.tasks.python import vision
            base = mpp.BaseOptions(model_asset_path=HAND_MODEL)
            opt = vision.HandLandmarkerOptions(
                base_options=base, num_hands=4,
                running_mode=vision.RunningMode.IMAGE,
                min_hand_detection_confidence=0.4)
            _mp = vision.HandLandmarker.create_from_options(opt)
        except Exception as e:
            print('[activity] hand landmarker unavailable, pose-only:', type(e).__name__, e)
            _mp = None
    return _mp


def make_zones(w, h, cols=3, rows=2, labels=None):
    """Image-space zones. Replace with world coordinates once a camera pose is solved."""
    if labels is None:
        labels = [['near_left', 'near_center', 'near_right'],
                  ['far_left', 'far_center', 'far_right']][:rows]
        while len(labels) < rows:
            labels.append([f'row{r}_c{c}' for c in range(cols)])
    zs = {}
    for r in range(rows):
        for c in range(cols):
            x0, x1 = int(w * c / cols), int(w * (c + 1) / cols)
            y0, y1 = int(h * r / rows), int(h * (r + 1) / rows)
            zs[labels[r][c]] = [x0, y0, x1, y1]
    return zs


def zone_of(x, y, zs):
    for name, (x0, y0, x1, y1) in zs.items():
        if x0 <= x < x1 and y0 <= y < y1:
            return name
    return 'off_frame'


def analyze(frame, zonespec=None):
    """One frame in, one activity record out. Never raises on model trouble."""
    h, w = frame.shape[:2]
    zs = zonespec or make_zones(w, h)
    rec = {'frame_wh': [w, h], 'people_count': 0, 'people': [],
           'hands': [], 'hands_source': None, 'zones': zs}

    # ---- pose: wrists give hand position ----
    try:
        res = _pose_model().predict(frame, verbose=False, conf=POSE_CONF)[0]
        kd = res.keypoints.data.cpu().numpy() if (res.keypoints is not None and len(res.keypoints)) else []
        rec['people_count'] = int(len(kd))
        for i, kp in enumerate(kd):
            pts = {}
            for name, idx in ARMS.items():
                x, y, c = kp[idx]
                if float(c) >= KP_CONF:
                    pts[name] = {'xy': [round(float(x), 1), round(float(y), 1)],
                                 'conf': round(float(c), 2),
                                 'zone': zone_of(float(x), float(y), zs)}
            rec['people'].append({'person': i, 'arms': pts})
    except Exception as e:
        rec['pose_error'] = f'{type(e).__name__}: {e}'

    # ---- hands: landmarks, if mediapipe is available ----
    # ---- hands: 21 landmarks per hand, if mediapipe is available ----
    hs = _hand_landmarker()
    if hs is not None:
        try:
            import mediapipe as mp
            mpi = mp.Image(image_format=mp.ImageFormat.SRGB,
                           data=cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            out = hs.detect(mpi)
            for hi, hl in enumerate(out.hand_landmarks or []):
                xs = [lm.x * w for lm in hl]
                ys = [lm.y * h for lm in hl]
                cx, cy = float(np.mean(xs)), float(np.mean(ys))
                rec['hands'].append({
                    'hand': hi,
                    'center_px': [round(cx, 1), round(cy, 1)],
                    'bbox_px': [round(min(xs), 1), round(min(ys), 1),
                                round(max(xs), 1), round(max(ys), 1)],
                    'landmarks': len(hl),
                    'zone': zone_of(cx, cy, zs),
                })
            if rec['hands']:
                rec['hands_source'] = 'mediapipe'
        except Exception as e:
            rec['hands_error'] = f'{type(e).__name__}: {e}'

    if not rec['hands']:
        # no landmark model -> derive pseudo-hands from pose wrists so downstream
        # always sees ONE shape regardless of which detectors are available
        for p in rec['people']:
            for side in ('left_wrist', 'right_wrist'):
                a = p['arms'].get(side)
                if a:
                    rec['hands'].append({'hand': None,
                                         'from': f"person{p['person']}_{side}",
                                         'center_px': a['xy'], 'zone': a['zone'],
                                         'landmarks': 0})
        if rec['hands']:
            rec['hands_source'] = 'pose_wrist'

    return rec


if __name__ == '__main__':
    import sys, json, time
    src = sys.argv[1] if len(sys.argv) > 1 else 'rtsp://127.0.0.1:8554/ptz_h264'
    cap = cv2.VideoCapture(src, cv2.CAP_FFMPEG)
    cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 10000)
    f = None
    for _ in range(25):
        ok, fr = cap.read()
        if ok:
            f = fr
    cap.release()
    if f is None:
        print('no frame'); raise SystemExit(1)
    t = time.time()
    r = analyze(f)
    print(json.dumps({k: v for k, v in r.items() if k != 'zones'}, indent=1)[:1800])
    print('elapsed %.2fs' % (time.time() - t))
