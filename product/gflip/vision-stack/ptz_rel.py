from onvif import ONVIFCamera
import time
cam=ONVIFCamera('192.168.2.117',80,'admin','admin')
ptz=cam.create_ptz_service()
media=cam.create_media_service()
tok=media.GetProfiles()[0].token
# relative move
req=ptz.create_type('RelativeMove')
req.ProfileToken=tok
req.Translation={'PanTilt':{'x':0.5,'y':0.0},'Zoom':{'x':0.0}}
ptz.RelativeMove(req)
print('RelativeMove ok')
time.sleep(3)
print(ptz.GetStatus({'ProfileToken':tok}))
