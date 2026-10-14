import os, sys
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from charuco_render import render_charuco

DPI = 300
PAPER_IN = (11, 17)  # landscape 11x17
PAPER_PX = (int(11*DPI), int(17*DPI))  # 3300 x 5100

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'print')

# Board configs: (name, squaresX, squaresY, square_mm)
CONFIGS = [
    ('charuco_11x17_50mm_5x8', 5, 8, 50.0),
    ('charuco_11x17_30mm_8x13', 8, 13, 30.0),
]

def render_printable(squares_x, squares_y, square_mm):
    square_px = square_mm * DPI / 25.4
    bw = int(round(squares_x * square_px))
    bh = int(round(squares_y * square_px))
    board = render_charuco(bw, bh, square_px, anchor=(0,0))
    # paste onto 11x17 canvas with margins
    canvas = np.full((PAPER_PX[1], PAPER_PX[0]), 255, np.uint8)
    x0 = (PAPER_PX[0] - bw)//2
    y0 = (PAPER_PX[1] - bh)//2
    canvas[y0:y0+bh, x0:x0+bw] = board
    return canvas, x0, y0, bw, bh

def add_text(canvas, text):
    img = Image.fromarray(canvas)
    d = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 60)
    except Exception:
        font = ImageFont.load_default()
    d.text((60, 60), text, fill=0, font=font)
    return img

for name, sx, sy, smm in CONFIGS:
    canvas, x0, y0, bw, bh = render_printable(sx, sy, smm)
    text = (f'ChArUco {sx}x{sy} | {smm:.0f}mm squares | DICT_4X4_1000 | '
            f'print 100% on 11x17 | board {sx*smm:.0f}x{sy*smm:.0f}mm')
    img = add_text(canvas, text)
    png_path = os.path.join(OUT, name + '.png')
    pdf_path = os.path.join(OUT, name + '.pdf')
    img.save(png_path, dpi=(DPI, DPI))
    img.save(pdf_path, resolution=DPI)
    print(f'{name}: {sx}x{sy} squares, {smm}mm, board {sx*smm:.0f}x{sy*smm:.0f}mm -> png/pdf saved')
    print(f'  board px {bw}x{bh}, margins left/top {x0},{y0}')
print('done')
