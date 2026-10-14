import sys, time
from onvif import ONVIFCamera
cam=ONVIFCamera('192.168.2.117',80,'admin','admin')
ptz=cam.create_ptz_service(); media=cam.create_media_service(); tok=media.GetProfiles()[0].token
def nudge(pan,tilt,secs,zoom=0.0,timeout='PT6S'):
    r=ptz.create_type('ContinuousMove'); r.ProfileToken=tok
    r.Velocity={'PanTilt':{'x':float(pan),'y':float(tilt)},'Zoom':{'x':float(zoom)}}
    r.Timeout=timeout
    ptz.ContinuousMove(r); time.sleep(secs)
    ptz.Stop({'ProfileToken':tok,'PanTilt':True,'Zoom':True})
    return True
if __name__=='__main__':
    pan,tilt,secs=float(sys.argv[1]),float(sys.argv[2]),float(sys.argv[3])
    nudge(pan,tilt,secs); print(f"nudged pan={pan} tilt={tilt} for {secs}s")
