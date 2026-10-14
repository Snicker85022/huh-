import cv2
import numpy as np

DICT = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_1000)
SQUARES_X, SQUARES_Y = 5, 7
MARKER_RATIO = 0.8


def paste(img, marker, cx, cy):
    """Paste marker centered at float (cx, cy), clipping to image bounds."""
    h, w = img.shape
    mh, mw = marker.shape
    x0 = int(round(cx - mw / 2.0))
    y0 = int(round(cy - mh / 2.0))
    x1, y1 = x0 + mw, y0 + mh
    # clip source
    sx0, sy0 = 0, 0
    sx1, sy1 = mw, mh
    if x0 < 0:
        sx0 = -x0; x0 = 0
    if y0 < 0:
        sy0 = -y0; y0 = 0
    if x1 > w:
        sx1 -= x1 - w; x1 = w
    if y1 > h:
        sy1 -= y1 - h; y1 = h
    if x0 < x1 and y0 < y1:
        img[y0:y1, x0:x1] = marker[sy0:sy1, sx0:sx1]


def render_charuco(width_px, height_px, square_px, anchor=(0, 0),
                   marker_ratio=MARKER_RATIO, squares_x=SQUARES_X, squares_y=SQUARES_Y):
    """Procedurally render a ChArUco board, clipped to the screen.

    square (0,0)'s TOP-LEFT corner is pinned exactly at `anchor`.
    Odd-parity squares are white and carry ArUco markers (row-major id order);
    even-parity squares are black. Background is white.
    """
    img = np.full((height_px, width_px), 255, np.uint8)
    marker_side = max(1, int(round(square_px * marker_ratio)))
    mid = 0
    for row in range(squares_y):
        for col in range(squares_x):
            x0 = anchor[0] + col * square_px
            y0 = anchor[1] + row * square_px
            x1 = x0 + square_px
            y1 = y0 + square_px
            if x1 < 0 or y1 < 0 or x0 >= width_px or y0 >= height_px:
                continue
            ix0, iy0 = int(round(x0)), int(round(y0))
            ix1, iy1 = int(round(x1)), int(round(y1))
            if ix1 <= ix0 or iy1 <= iy0:
                continue
            if (row + col) % 2 == 0:
                img[iy0:iy1, ix0:ix1] = 0
            else:
                img[iy0:iy1, ix0:ix1] = 255
                marker = cv2.aruco.generateImageMarker(DICT, mid, marker_side)
                cx = (x0 + x1) / 2.0
                cy = (y0 + y1) / 2.0
                paste(img, marker, cx, cy)
                mid += 1
    return img


def make_board(square_mm):
    """Return a CharucoBoard object matching render_charuco for detection."""
    return cv2.aruco.CharucoBoard(
        (SQUARES_X, SQUARES_Y),
        float(square_mm) / 1000.0,
        (float(square_mm) / 1000.0) * MARKER_RATIO,
        DICT,
    )
