import os, sys
import cv2
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from charuco_render import render_charuco

# Screen profiles: resolution + physical width (mm) used to convert mm -> px.
PROFILES = {
    'mt15':   {'w': 1920, 'h': 1080, 'width_mm': 345.4},    # MicroTouch 15.6" FHD landscape
    'mt15p':  {'w': 1080, 'h': 1920, 'width_mm': 345.4},    # MicroTouch 15.6" FHD portrait
    'fire50': {'w': 3840, 'h': 2160, 'width_mm': 1107.4},   # Fire TV 50" 4K (east wall)
    'tcl75':  {'w': 3840, 'h': 2160, 'width_mm': 1660.9},   # TCL 75" 4K
}

SIZES_MM = [30, 60, 90, 120, 150, 180, 210, 240, 270, 300, 330, 360, 390, 420,
            450, 470, 510, 570, 630, 690, 780, 870, 960, 1050]

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'boards')

def main():
    os.makedirs(OUT, exist_ok=True)
    for name, prof in PROFILES.items():
        w, h = prof['w'], prof['h']
        mm_per_px = prof['width_mm'] / w
        anchor = (w // 2, h // 2)   # reference square (0,0) top-left corner pinned here
        prof_dir = os.path.join(OUT, name)
        os.makedirs(prof_dir, exist_ok=True)
        for size in SIZES_MM:
            square_px = size / mm_per_px
            img = render_charuco(w, h, square_px, anchor=anchor)
            path = os.path.join(prof_dir, f'{size}mm.png')
            cv2.imwrite(path, img)
            print(f'{name:5s} {size:5d}mm  square={square_px:7.1f}px  -> {path}')
    print('done')

if __name__ == '__main__':
    main()
