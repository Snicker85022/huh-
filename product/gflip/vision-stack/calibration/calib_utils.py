import cv2
import numpy as np

DICT = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_1000)

def detect_board(gray, square_mm, squares_x=5, squares_y=7):
    """Detect ChArUco corners in a screen-projected board image."""
    board = cv2.aruco.CharucoBoard(
        (squares_x, squares_y),
        float(square_mm) / 1000.0,
        (float(square_mm) / 1000.0) * 0.8,
        DICT,
    )
    det = cv2.aruco.CharucoDetector(board)
    try:
        charucoCorners, charucoIds, markerCorners, markerIds = det.detectBoard(gray)
        if charucoIds is None or len(charucoIds) == 0:
            return None, None
        return charucoCorners, charucoIds
    except Exception as e:
        print('detectBoard error:', e)
        return None, None

def detect_board_legacy(gray, square_mm, squares_x=5, squares_y=7):
    """Fallback: detect Aruco markers then interpolate Charuco corners manually."""
    board = cv2.aruco.CharucoBoard(
        (squares_x, squares_y),
        float(square_mm) / 1000.0,
        (float(square_mm) / 1000.0) * 0.8,
        DICT,
    )
    aruco_det = cv2.aruco.ArucoDetector(DICT)
    corners, ids, _ = aruco_det.detectMarkers(gray)
    if ids is None or len(ids) == 0:
        return None, None
    # Use CharucoDetector with pre-detected markers
    det = cv2.aruco.CharucoDetector(board)
    try:
        charucoCorners, charucoIds, _, _ = det.detectBoard(gray, markerCorners=corners, markerIds=ids)
        if charucoIds is None or len(charucoIds) == 0:
            return None, None
        return charucoCorners, charucoIds
    except Exception as e:
        print('legacy detect error:', e)
        return None, None

def detect_room_corners(gray):
    """Detect candidate room corners via Harris/Shi-Tomasi + line intersection."""
    corners = cv2.goodFeaturesToTrack(gray, 200, 0.05, 10)
    return corners

def load_calib(path):
    s = cv2.FileStorage(path, cv2.FILE_STORAGE_READ)
    K = s.getNode('camera_matrix').mat()
    D = s.getNode('dist_coeffs').mat()
    s.release()
    return K, D

def save_calib(path, K, D, rms, image_size):
    s = cv2.FileStorage(path, cv2.FILE_STORAGE_WRITE)
    s.write('camera_matrix', K)
    s.write('dist_coeffs', D)
    s.write('rms', rms)
    s.write('image_size_width', image_size[0])
    s.write('image_size_height', image_size[1])
    s.release()
