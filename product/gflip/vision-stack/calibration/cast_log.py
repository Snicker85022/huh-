import sys, time
log = open('/tmp/cast.log', 'a')
def w(m): log.write(m+'\n'); log.flush(); print(m)
import pychromecast
url = sys.argv[1]; name = sys.argv[2]
w(f'start {url} {name}')
for attempt in range(4):
    try:
        casts, _ = pychromecast.get_chromecasts(timeout=8)
        w(f'attempt {attempt}: found {[(c.name, c.cast_info.host) for c in casts]}')
        target = next((c for c in casts if c.name == name), None)
        if target is None:
            time.sleep(4); continue
        target.wait(timeout=25)
        w(f'socket ok status={target.status}')
        mc = target.media_controller
        mc.play_media(url, 'image/png')
        mc.block_until_active(timeout=25)
        w('CAST OK')
        sys.exit(0)
    except Exception as e:
        w(f'err {repr(e)[:200]}')
        time.sleep(4)
w('CAST FAILED'); sys.exit(1)
