import cv2, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from charuco_render import render_charuco
from calib_utils import detect_board, detect_board_legacy

# Render a 60mm board for mt15 and detect corners, verifying round-trip.
w, h = 1920, 1080
mm_per_px = 345.44 / w
size = 60
square_px = size / mm_per_px
img = render_charuco(w, h, square_px, anchor=(w//2, h//2))
gray = img
corners, ids = detect_board(gray, size)
print('detect_board -> corners:', None if corners is None else corners.shape, 'ids:', None if ids is None else ids.shape)
if corners is None:
    corners, ids = detect_board_legacy(gray, size)
    print('legacy -> corners:', None if corners is None else corners.shape, 'ids:', None if ids is None else ids.shape)
if corners is not None:
    print('first 5 ids:', ids.flatten()[:5])
    print('first corner:', corners[0])
    # anchor corner should be at (960,540): find corner closest to anchor
    pt = np.float32([[960, 540]])
    # draw detected corners
    out = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    cv2.aruco.drawDetectedCornersCharuco(out, corners, ids, (0,255,0))
    cv2.circle(out, (960,540), 5, (0,0,255), 2)
    cv2.imwrite('/tmp/charuco_detected.png', out)
    print('saved /tmp/charuco_detected.png')
