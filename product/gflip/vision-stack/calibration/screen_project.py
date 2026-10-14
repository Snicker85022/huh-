"""Project a ChArUco board onto a screen.

Backends:
  cast  -> Google Cast (works for TCL / Fire TV once the TV is awake)
  adb   -> Android browser fullscreen (MT1/MT2 once ADB is authorized)
"""
import sys, os, time, argparse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

BOARD_URL = 'http://192.168.2.107:8090/calib/board/{profile}/{size}mm.png'
VIEWER_URL = 'http://192.168.2.107:8090/calib/viewer?profile={profile}&size={size}'

def cast_board(device_name, profile, size, retries=2):
    import pychromecast
    for attempt in range(retries+1):
        casts, _ = pychromecast.get_chromecasts(timeout=8)
        target = None
        for c in casts:
            print('cast found:', c.name, c.cast_info.host)
            if c.name == device_name:
                target = c
        if target is None:
            print('device not found:', device_name)
            return False
        try:
            target.wait(timeout=12)
            mc = target.media_controller
            mc.play_media(BOARD_URL.format(profile=profile, size=size), 'image/png')
            mc.block_until_active(timeout=12)
            print('cast ok:', device_name, size, 'mm')
            return True
        except Exception as e:
            print('cast fail:', repr(e)[:160])
            time.sleep(3)
    return False

def adb_project(serial, profile, size):
    """Open the board viewer fullscreen on an Android device via ADB."""
    url = VIEWER_URL.format(profile=profile, size=size)
    import subprocess
    # Chrome fullscreen on Android (kiosk-ish); requires ADB authorized.
    cmds = [
        ['adb', '-s', serial, 'shell', 'am', 'start', '-a', 'android.intent.action.VIEW', '-d', url],
    ]
    for c in cmds:
        r = subprocess.run(c, capture_output=True, text=True, timeout=20)
        print(c, '->', r.returncode, r.stdout.strip()[:100])
    return True

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--backend', choices=['cast','adb'], default='cast')
    ap.add_argument('--device', default='Tcl1East')
    ap.add_argument('--profile', default='tcl75')
    ap.add_argument('--size', type=int, default=60)
    args = ap.parse_args()
    if args.backend == 'cast':
        cast_board(args.device, args.profile, args.size)
    else:
        adb_project(args.device, args.profile, args.size)
