import cv2, os, sys, time, json
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from calib_utils import detect_board

STREAM = os.environ.get('VISION_STREAM_URL', 'rtsp://localhost:8554/ptz_h264')
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'captures')
os.makedirs(OUT, exist_ok=True)

def grab():
    cap = cv2.VideoCapture(STREAM, cv2.CAP_FFMPEG)
    cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 8000)
    ok, frame = cap.read()
    cap.release()
    return frame if ok else None

def capture_board(size_mm, tag='auto'):
    frame = grab()
    if frame is None:
        print('no frame')
        return None
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    corners, ids = detect_board(gray, size_mm)
    path = os.path.join(OUT, f'board_{size_mm}mm_{tag}.jpg')
    cv2.imwrite(path, frame)
    n = 0 if ids is None else len(ids)
    print(f'size={size_mm}mm tag={tag} corners={n} -> {path}')
    return {'path': path, 'size_mm': size_mm, 'corners': n}

if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('--size', type=int, default=60)
    ap.add_argument('--tag', default='auto')
    args = ap.parse_args()
    capture_board(args.size, args.tag)
