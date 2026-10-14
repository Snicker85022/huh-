import sys, time, argparse
import pychromecast

BOARD_URL = 'http://192.168.2.107:8090/calib/board/{profile}/{size}mm.png'

def find_cast(name=None):
    casts, browser = pychromecast.get_chromecasts(timeout=8)
    if not casts:
        print('no cast devices')
        return None
    for c in casts:
        print('found:', c.name, c.cast_info.host, c.cast_info.model_name)
    if name:
        for c in casts:
            if c.name == name:
                return c
        print('name', name, 'not found')
        return None
    return casts[0]

def cast(c, url):
    try:
        c.wait()
        mc = c.media_controller
        mc.play_media(url, 'image/png')
        mc.block_until_active(timeout=15)
        print('cast ok:', url)
        return True
    except Exception as e:
        print('cast error:', e)
        return False

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--name', default='Tcl1East')
    ap.add_argument('--profile', default='tcl75')
    ap.add_argument('--size', type=int, default=60)
    args = ap.parse_args()
    c = find_cast(args.name)
    if c:
        url = BOARD_URL.format(profile=args.profile, size=args.size)
        cast(c, url)
