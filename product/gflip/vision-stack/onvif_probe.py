import sys
from onvif import ONVIFCamera

host='192.168.2.117'
creds=[('admin','admin'),('admin','12345'),('admin','123456'),('admin','password'),('admin',''),('Admin','12345'),('root','12345')]

for user,pw in creds:
    try:
        cam = ONVIFCamera(host, 80, user, pw)
        dev = cam.devicemgmt
        info = dev.GetDeviceInformation()
        print('OK creds', user, '/', pw)
        print('  Manufacturer:', info.Manufacturer)
        print('  Model:', info.Model)
        print('  Firmware:', info.FirmwareVersion)
        # media service
        media = cam.create_media_service()
        profiles = media.GetProfiles()
        print('  Profiles:', len(profiles))
        for i,p in enumerate(profiles):
            print('   ', i, 'name=', p.Name, 'token=', p.token)
            try:
                uri = media.GetStreamUri({'StreamSetup':{'Stream':'RTP-Unicast','Transport':{'Protocol':'RTSP'}},'ProfileToken':p.token})
                print('     RTSP:', uri.Uri)
            except Exception as e:
                print('     no stream:', e)
        # PTZ service check
        try:
            ptz = cam.create_ptz_service()
            print('  PTZ service available')
        except Exception as e:
            print('  no ptz:', e)
        break
    except Exception as e:
        print('fail', user, pw, '->', str(e)[:80])
