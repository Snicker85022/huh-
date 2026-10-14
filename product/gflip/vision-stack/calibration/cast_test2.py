import pychromecast, time, sys
casts, browser = pychromecast.get_chromecasts(timeout=10)
print('found', [(c.name, c.cast_info.host) for c in casts])
for c in casts:
    print('trying', c.name, c.cast_info.host)
    try:
        c.wait(timeout=10)
        print(' status:', c.status)
        mc = c.media_controller
        mc.play_media('http://192.168.2.107:8090/calib/board/tcl75/60mm.png', 'image/png')
        mc.block_until_active(timeout=10)
        print(' cast OK on', c.name)
    except Exception as e:
        print(' fail:', repr(e)[:200])
