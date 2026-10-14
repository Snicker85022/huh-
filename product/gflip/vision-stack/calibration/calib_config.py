"""Room, screen, camera, and fixed-object definitions for the QC vision system.

Coordinate system: X=east, Y=up, Z=north, origin = SW floor corner.
Units: feet for room positions (converted), mm for board squares.
Room: 303" E-W (X), 211.75" N-S (Z), 120" ceiling (Y).
"""
import math

def width_mm(diag_in):
    return diag_in * 25.4 * (16 / math.sqrt(16**2 + 9**2))

PTZ_LENS_BEZEL_OFFSET_MM = 10.0   # PTZ lens -> bezel (user estimate)
MT_LENS_FROM_SCREEN_CENTER_MM = 4.125 * 25.4  # 104.775 mm, along the long (portrait) edge

ROOM = {'x': 303/12, 'y': 120/12, 'z': 211.75/12}  # feet; X=east, Y=up, Z=south, origin NW floor (Z=0 north)

# Screen definitions (fixed in 3D space, orientation fixed)
SCREENS = {
    # MicroTouch Mach M1-156IC-AA2, physically mounted in PORTRAIT.
    # Active area MEASURED with tape 2026-10-07: 7-19/32 in wide x 13.5 in long
    # => diagonal 15.49 in (~15.5). Lens is on the LONG edge, 4.125 in from screen center.
    'mt1': {
        'name': 'MT1 (MicroTouch 15.5")', 'ip': '192.168.2.104',
        'diag_in': 15.5, 'screen_w_in': 7.59375, 'screen_h_in': 13.5,
        'portrait': True, 'lens_offset_mm': 4.125 * 25.4, 'res': (1920, 1080),
        # approximate screen center + normal-facing direction (feet)
        'pos': (25.0, 5.0, 3.0), 'facing': (-1, 0, 0),   # east wall, faces west
    },
    'mt2': {
        'name': 'MT2 (MicroTouch 15.5")', 'ip': '192.168.2.108',
        'diag_in': 15.5, 'screen_w_in': 7.59375, 'screen_h_in': 13.5,
        'portrait': True, 'lens_offset_mm': 4.125 * 25.4, 'res': (1080, 1920),
        'pos': (0.25, 6.0, 6.0), 'facing': (1, 0, 0),    # west wall, faces east
    },
    'fire50': {
        'name': 'Fire TV 50"', 'ip': '192.168.2.122',
        'diag_in': 50.0, 'res': (3840, 2160),
        'pos': (25.0, 5.0, 7.5), 'facing': (-1, 0, 0),   # east wall, faces west
    },
    'tcl75': {
        'name': 'TCL 75"', 'ip': '192.168.2.116',
        'diag_in': 75.0, 'res': (3840, 2160),
        'pos': (25.0, 5.0, 12.0), 'facing': (-1, 0, 0),  # east wall, right of Fire TV
    },
}

# Camera definitions
CAMERAS = {
    'ptz': {
        'name': 'PTZ HD975B-P', 'rtsp': 'rtsp://192.168.2.117:554/stream0',
        'pos': (10.818, 5.4583, 9.875), 'facing': (1, 0, 0),  # on 2x5 NSF rack SE pole (derived: x=69.8125+60in, z=98.25in, y=65.5in)
        'zoom_modes': ['MainStream', 'SubStream'], 'modes': ['1x'],
    },
    'usb': {
        'name': 'Angetube 1080P webcam', 'rtsp': None,  # to be assigned after USB fix
        'pos': (6.0, 6.1, 5.0), 'facing': (1, 0, 1),
        'zoom_modes': ['1x'], 'modes': ['1x'],
    },
    'mt1_cam': {
        'name': 'MT1 built-in 2.5MP', 'rtsp': None,     # via ADB/IP webcam after auth
        'pos': (25.0, 5.0, 3.0), 'facing': (-1, 0, 0),
        'zoom_modes': ['1x'], 'modes': ['1x'],
    },
    'mt2_cam': {
        'name': 'MT2 built-in 2.5MP', 'rtsp': None,
        'pos': (0.25, 6.0, 6.0), 'facing': (1, 0, 0),
        'zoom_modes': ['1x'], 'modes': ['1x'],
    },
}

# Fixed room landmarks (big objects that don't move) for the vision-analysis model.
# Positions are approximate and must be surveyed later.
FIXED_OBJECTS = [
    {'name': 'room_sw_floor', 'type': 'corner', 'pos': (0, 0, 0)},
    {'name': 'room_se_floor', 'type': 'corner', 'pos': (ROOM['x'], 0, 0)},
    {'name': 'room_nw_floor', 'type': 'corner', 'pos': (0, 0, ROOM['z'])},
    {'name': 'room_ne_floor', 'type': 'corner', 'pos': (ROOM['x'], 0, ROOM['z'])},
    {'name': 'room_sw_ceil', 'type': 'corner', 'pos': (0, ROOM['y'], 0)},
    {'name': 'room_se_ceil', 'type': 'corner', 'pos': (ROOM['x'], ROOM['y'], 0)},
    {'name': 'room_nw_ceil', 'type': 'corner', 'pos': (0, ROOM['y'], ROOM['z'])},
    {'name': 'room_ne_ceil', 'type': 'corner', 'pos': (ROOM['x'], ROOM['y'], ROOM['z'])},
    {'name': 'reach_in_refrigerator', 'type': 'box', 'pos': (14.0, 3.0, 16.0), 'size': (3.0, 7.0, 3.0)},
    {'name': 'nsf_rack_3x6', 'type': 'rack', 'pos': (6.0, 3.0, 8.82), 'size': (6.0, 6.1, 3.0)},   # center of room N-S; spans z=7.32..10.32
    {'name': 'nsf_rack_2x5', 'type': 'rack', 'pos': (0.5, 2.5, 8.32), 'size': (5.0, 5.0, 2.0)},   # offset 6in north; north edge z=7.32 collinear with 3x6
    {'name': 'baking_pan_racks', 'type': 'rack', 'pos': (16.0, 4.0, 6.0), 'size': (4.0, 6.0, 1.8)},
    {'name': 'pizza_oven', 'type': 'box', 'pos': (20.0, 3.0, 18.0), 'size': (3.0, 5.0, 3.0)},
    {'name': 'griddle', 'type': 'box', 'pos': (18.0, 3.0, 12.0), 'size': (3.0, 3.5, 2.5)},
    {'name': 'grill', 'type': 'box', 'pos': (18.0, 3.0, 9.0), 'size': (3.0, 3.5, 2.0)},
    {'name': 'fryer', 'type': 'box', 'pos': (2.0, 3.0, 6.0), 'size': (2.0, 3.5, 2.0)},
    {'name': 'dishwasher', 'type': 'box', 'pos': (8.0, 3.0, 17.0), 'size': (2.5, 3.0, 2.5)},
    {'name': 'three_compartment_sink', 'type': 'box', 'pos': (6.0, 3.0, 18.0), 'size': (4.0, 3.0, 2.0)},
    {'name': 'prep_sinks', 'type': 'box', 'pos': (10.0, 3.0, 17.0), 'size': (3.0, 3.0, 2.0)},
    {'name': 'shelves', 'type': 'rack', 'pos': (22.0, 4.0, 6.0), 'size': (4.0, 6.0, 1.5)},
    {'name': 'exit_door', 'type': 'door', 'pos': (12.0, 0, 0), 'size': (3.0, 7.0, 0)},
]

# ChArUco projection sequence (mm square sizes), fixed reference corner pinned on every screen.
SIZES_MM = [30,60,90,120,150,180,210,240,270,300,330,360,390,420,450,470,510,570,630,690,780,870,960,1050]

# NSF chrome wire rack vertical bars: 1 inch diameter (known scale reference).
RACK_BAR_DIAMETER_MM = 25.4
RACK_BAR_DIAMETER_IN = 1.0

# Measured/known in-frame references for the PTZ camera (zoom-in view).
PTZ_VIEW_REFERENCES = {
    'nsf_pole_1in': {'type': 'vertical_cylinder', 'diameter_mm': 25.4, 'note': 'pole behind wire whisk'},
    'mt2_screen': {'type': 'screen', 'diag_in': 15.6, 'orientation': 'portrait',
                   'pose_note': '~15 deg away from camera, ~9 deg down from camera normal'},
    'kirkland_paper_towel': {'type': 'cylinder', 'diameter_mm': None, 'note': 'width NOT verified - web search blocked, pending user confirmation'},
}
