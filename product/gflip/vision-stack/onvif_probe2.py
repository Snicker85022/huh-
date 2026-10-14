from onvif import ONVIFCamera
for host in ['192.168.2.110','192.168.2.118','192.168.2.113']:
    for user,pw in [('admin','admin'),('admin','12345'),('admin','')]:
        try:
            cam = ONVIFCamera(host, 80, user, pw)
            info = cam.devicemgmt.GetDeviceInformation()
            print(host, 'ONVIF OK', user, '/', pw, '->', info.Manufacturer, info.Model)
            break
        except Exception as e:
            print(host, 'fail', user, pw, '->', str(e)[:60])
