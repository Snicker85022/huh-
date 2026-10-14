from onvif import ONVIFCamera
import time
cam=ONVIFCamera('192.168.2.117',80,'admin','admin')
media=cam.create_media_service()
profiles=media.GetProfiles()
tok=profiles[0].token
print('profile:', tok)
ptz=cam.create_ptz_service()
try:
    cfg=ptz.GetConfigurations()
    print('configs:', cfg)
except Exception as e:
    print('GetConfigurations err:', e)
try:
    st=ptz.GetStatus({'ProfileToken':tok})
    print('status:', st)
except Exception as e:
    print('GetStatus err:', e)
try:
    nodes=ptz.GetNodes()
    print('nodes:', nodes)
except Exception as e:
    print('GetNodes err:', e)

def move(pan,tilt,zoom):
    try:
        req=ptz.create_type('ContinuousMove')
        req.ProfileToken=tok
        req.Velocity={'PanTilt':{'x':pan,'y':tilt},'Zoom':{'x':zoom}}
        ptz.ContinuousMove(req)
        print('ContinuousMove ok', pan, tilt, zoom)
    except Exception as e:
        print('ContinuousMove err:', e)

def stop():
    try:
        req=ptz.create_type('Stop')
        req.ProfileToken=tok; req.PanTilt=True; req.Zoom=True
        ptz.Stop(req); print('Stop ok')
    except Exception as e:
        print('Stop err:', e)

print('--- moving left 1.0 for 2s ---')
move(-1.0,0,0); time.sleep(2); stop(); time.sleep(1)
try:
    print('status after:', ptz.GetStatus({'ProfileToken':tok}))
except Exception as e: print(e)
print('--- moving up 1.0 for 2s ---')
move(0,1.0,0); time.sleep(2); stop(); time.sleep(1)
try:
    print('status after:', ptz.GetStatus({'ProfileToken':tok}))
except Exception as e: print(e)
