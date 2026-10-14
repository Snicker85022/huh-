import cv2, os, sys, glob, json
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from calib_utils import detect_board

CAP = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'captures')
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'intrinsics')
os.makedirs(OUT, exist_ok=True)

def run():
    obj_points, img_points = [], []
    files = sorted(glob.glob(os.path.join(CAP, 'board_*.jpg')))
    if not files:
        print('no captures. run capture_ptz.py first')
        return
    img_size = None
    for f in files:
        base = os.path.basename(f)
        # board_60mm_tag.jpg
        try:
            size_mm = int(base.split('_')[1].replace('mm',''))
        except Exception:
            continue
        img = cv2.imread(f)
        if img is None:
            continue
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        if img_size is None:
            img_size = gray.shape[::-1]
        corners, ids = detect_board(gray, size_mm)
        if corners is None or ids is None or len(ids) < 4:
            print(f'skip {base}: {0 if ids is None else len(ids)} corners')
            continue
        # 3D object points for this board
        board = cv2.aruco.CharucoBoard(
            (5,7), size_mm/1000.0, (size_mm/1000.0)*0.8,
            cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_1000))
        # map charucoIds to 3D chessboard corners
        all_3d = board.getChessboardCorners()
        id_map = {}
        # charuco ids correspond to chessboard corner indices; OpenCV charucoIds are the corner ids
        for cid, c3 in zip(ids.flatten(), all_3d):
            id_map[int(cid)] = c3
        op = []
        ip = []
        for cid, c2 in zip(ids.flatten(), corners):
            if int(cid) in id_map:
                op.append(id_map[int(cid)])
                ip.append(c2)
        if len(op) < 4:
            print(f'skip {base}: only {len(op)} mapped')
            continue
        obj_points.append(np.array(op, np.float32))
        img_points.append(np.array(ip, np.float32))
        print(f'{base}: {len(op)} corners used')
    if len(obj_points) < 3:
        print('need at least 3 views with corners')
        return
    K = np.eye(3, dtype=np.float64)
    K[0,0] = img_size[0]  # initial focal guess = width px
    K[1,1] = img_size[0]
    K[0,2] = img_size[0]/2
    K[1,2] = img_size[1]/2
    flags = cv2.CALIB_FIX_ASPECT_RATIO | cv2.CALIB_ZERO_TANGENT_DIST
    rms, K, D, rvecs, tvecs = cv2.calibrateCamera(obj_points, img_points, img_size, K, None, flags=flags)
    print(f'rms={rms:.3f}px  K={K}  D={D.ravel()}')
    s = cv2.FileStorage(os.path.join(OUT,'ptz_intrinsics.yml'), cv2.FILE_STORAGE_WRITE)
    s.write('camera_matrix', K); s.write('dist_coeffs', D); s.write('rms', rms)
    s.write('image_size_width', img_size[0]); s.write('image_size_height', img_size[1])
    s.release()
    print('saved intrinsics/ptz_intrinsics.yml')

if __name__ == '__main__':
    run()
