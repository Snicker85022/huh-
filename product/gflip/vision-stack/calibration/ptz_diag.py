import cv2, time, json
from onvif import ONVIFCamera
CAM='rtsp://192.168.2.117:554/stream0?username=admin&password=E10ADC3949BA59ABBE56E057F20F883E'
cam=ONVIFCamera('192.168.2.117',80,'admin','admin')
dev=cam.create_devicemgmt_service(); ptz=cam.create_ptz_service()
media=cam.create_media_service()
print("="*70); print("DEVICE INFO"); print("="*70)
try: print(dev.GetDeviceInformation())
except Exception as e: print("err",e)
print("="*70); print("PTZ GetServiceCapabilities"); print("="*70)
try: print(json.dumps(ptz.GetServiceCapabilities(), default=str)[:1500])
except Exception as e: print("err",e)
print("="*70); print("PTZ GetNodes"); print("="*70)
nodes=[]
try:
    nodes=ptz.GetNodes()
    for n in nodes:
        print(" node token:", n.token, "| name:", getattr(n,'Name',None))
        print("   MaxPresets:", getattr(n,'MaximumNumberOfPresets',None), "HomeSupported:", getattr(n,'HomeSupported',None))
        print("   SupportedPTZSpaces keys:", list((n.SupportedPTZSpaces or {}).keys()) if getattr(n,'SupportedPTZSpaces',None) else None)
except Exception as e: print("err",e)
print("="*70); print("PTZ GetConfigurations"); print("="*70)
cfgs=[]
try:
    cfgs=ptz.GetConfigurations()
    for c in cfgs:
        print(" cfg token:",c.token,"| name:",getattr(c,'Name',None),"| UseCount:",getattr(c,'UseCount',None))
        print("   NodeToken:",getattr(c,'NodeToken',None))
except Exception as e: print("err",e)
print("="*70); print("PTZ GetConfigurationOptions"); print("="*70)
try:
    if cfgs: print(json.dumps(ptz.GetConfigurationOptions({'ConfigurationToken':cfgs[0].token}), default=str)[:1500])
except Exception as e: print("err",e)
print("="*70); print("MEDIA PROFILES"); print("="*70)
try:
    for p in media.GetProfiles():
        pt=getattr(p,'PTZConfiguration',None)
        print(" profile token:",p.token,"| name:",getattr(p,'Name',None),"| PTZcfg:",getattr(pt,'token',None) if pt else None)
except Exception as e: print("err",e)
