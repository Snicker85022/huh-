import cv2, os, sys, glob
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from calib_utils import detect_board

CAP = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'captures')
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'intrinsics')
os.makedirs(OUT, exist_ok=True)
DICT = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_1000)

def detect_anchor_corner(gray, anchor_px, win=80):
    """Detect the pinned reference corner (board coordinate (0,0,0)) near anchor_px."""
    x, y = anchor_px
    x0, x1 = max(0, x-win), min(gray.shape[1], x+win)
    y0, y1 = max(0, y-win), min(gray.shape[0], y+win)
    crop = gray[y0:y1, x0:x1]
    if crop.size == 0:
        return None
    pts = cv2.goodFeaturesToTrack(crop, 50, 0.05, 8)
    if pts is None:
        return None
    # pick corner closest to anchor
    target = np.array([[x-x0, y-y0]], np.float32)
    d = ((pts.reshape(-1,2) - target)**2).sum(1)
    best = pts.reshape(-1,2)[d.argmin()]
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.01)
    refined = cv2.cornerSubPix(crop, np.float32([best]).reshape(1,1,2), (5,5), (-1,-1), criteria)
    return refined.reshape(2) + np.array([x0, y0], np.float32)

def main(pattern='board_*.jpg', anchor=(960,540), screen_profile='mt15'):
    files = sorted(glob.glob(os.path.join(CAP, pattern)))
    if not files:
        print('no captures')
        return
    obj_points, img_points = [], []
    img_size = None
    for f in files:
        base = os.path.basename(f)
        try:
            size_mm = int(base.split('_')[1].replace('mm',''))
        except Exception:
            print('skip (no size)', base); continue
        img = cv2.imread(f)
        if img is None:
            continue
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        if img_size is None:
            img_size = gray.shape[::-1]
        corners, ids = detect_board(gray, size_mm)
        op, ip = [], []
        if corners is not None and ids is not None and len(ids) >= 4:
            board = cv2.aruco.CharucoBoard((5,7), size_mm/1000.0, (size_mm/1000.0)*0.8, DICT)
            all3 = board.getChessboardCorners()
            for cid, c2 in zip(ids.flatten(), corners):
                ci = int(cid)
                if 0 <= ci < len(all3):
                    op.append(all3[ci]); ip.append(c2)
        # anchor corner: board coordinate (0,0,0) pinned at anchor px for every size
        ac = detect_anchor_corner(gray, anchor)
        if ac is not None:
            op.append(np.array([0.0, 0.0, 0.0], np.float32)); ip.append(ac)
        if len(op) >= 4:
            obj_points.append(np.array(op, np.float32)); img_points.append(np.array(ip, np.float32))
            print(f'{base}: {len(op)} pts (chArUco + anchor)')
        else:
            print(f'{base}: skip, only {len(op)} pts')
    if len(obj_points) < 3:
        print('need >=3 views'); return
    K = np.eye(3, np.float64)
    K[0,0] = img_size[0]; K[1,1] = img_size[0]
    K[0,2] = img_size[0]/2; K[1,2] = img_size[1]/2
    flags = cv2.CALIB_FIX_ASPECT_RATIO | cv2.CALIB_ZERO_TANGENT_DIST
    rms, K, D, rvecs, tvecs = cv2.calibrateCamera(obj_points, img_points, img_size, K, None, flags=flags)
    print(f'rms={rms:.3f}px')
    print('K=', K)
    print('D=', D.ravel())
    s = cv2.FileStorage(os.path.join(OUT, f'{screen_profile}_intrinsics.yml'), cv2.FILE_STORAGE_WRITE)
    s.write('camera_matrix', K); s.write('dist_coeffs', D); s.write('rms', rms)
    s.write('image_size_width', img_size[0]); s.write('image_size_height', img_size[1])
    s.release()
    print('saved', os.path.join(OUT, f'{screen_profile}_intrinsics.yml'))

if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('--pattern', default='board_*.jpg')
    ap.add_argument('--anchor', default='960,540')
    ap.add_argument('--profile', default='ptz')
    args = ap.parse_args()
    ax, ay = map(int, args.anchor.split(','))
    main(args.pattern, (ax, ay), args.profile)
