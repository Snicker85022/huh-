import sys, time
sys.path.insert(0, '/home/taza/vision-stack/calibration')
from onvif import ONVIFCamera
dirn = float(sys.argv[1]); dur = float(sys.argv[2])
cam = ONVIFCamera('192.168.2.117', 80, 'admin', 'admin')
ptz = cam.create_ptz_service(); media = cam.create_media_service()
tok = media.GetProfiles()[0].token
req = ptz.create_type('ContinuousMove'); req.ProfileToken = tok
req.Velocity = {'PanTilt': {'x': dirn, 'y': 0.0}, 'Zoom': {'x': 0.0}}
req.Timeout = None
ptz.ContinuousMove(req)
print('panning', dirn, 'for', dur, 's')
time.sleep(dur)
req2 = ptz.create_type('Stop'); req2.ProfileToken = tok; req2.PanTilt = True; req2.Zoom = True
ptz.Stop(req2)
print('stopped')
