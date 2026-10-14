import sys, re, urllib.request

def get(url):
    req = urllib.request.Request(url, headers={'User-Agent':'gflip-vision'})
    return urllib.request.urlopen(req, timeout=10).read()

def soap(control_url, action, body_inner):
    envelope = ('<?xml version="1.0"?><s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/" '
                's:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">'
                '<s:Body><u:%s xmlns:u="urn:schemas-upnp-org:service:AVTransport:1">%s</u:%s></s:Body></s:Envelope>') % (action, body_inner, action)
    req = urllib.request.Request(control_url, data=envelope.encode(), headers={
        'Content-Type': 'text/xml; charset="utf-8"',
        'SOAPACTION': '"urn:schemas-upnp-org:service:AVTransport:1#%s"' % action,
        'User-Agent': 'gflip-vision',
    })
    return urllib.request.urlopen(req, timeout=15).read()

def cast_image(desc_url, image_url):
    xml = get(desc_url).decode(errors='replace')
    m = re.search(r'<URLBase>(.*?)</URLBase>', xml, re.S)
    urlbase = m.group(1).strip() if m else ''
    # find AVTransport controlURL within service blocks
    blocks = re.findall(r'<service>(.*?)</service>', xml, re.S)
    control = None
    for b in blocks:
        if 'AVTransport' in b:
            cm = re.search(r'<controlURL>(.*?)</controlURL>', b, re.S)
            if cm:
                control = cm.group(1).strip()
                break
    if not control:
        print('no AVTransport controlURL'); return False
    control_url = (urlbase.rstrip('/') + '/' + control.lstrip('/')) if urlbase else control
    print('control_url:', control_url)
    import urllib.parse
    meta = ('<DIDL-Lite xmlns="urn:schemas-upnp-org:metadata-1-0/DIDL-Lite/" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:upnp="urn:schemas-upnp-org:metadata-1-0/upnp/">'
            '<item id="0" parentID="-1" restricted="1">'
            '<dc:title>ChArUco Board</dc:title>'
            '<upnp:class>object.item.imageItem.photo</upnp:class>'
            '<res protocolInfo="http-get:*:image/jpeg:DLNA.ORG_OP=01;DLNA.ORG_CI=1">%s</res>'
            '</item></DIDL-Lite>') % image_url
    soap(control_url, 'SetAVTransportURI',
         '<InstanceID>0</InstanceID><CurrentURI>%s</CurrentURI><CurrentURIMetaData>%s</CurrentURIMetaData>' % (image_url, urllib.parse.quote(meta)))
    soap(control_url, 'Play', '<InstanceID>0</InstanceID><Speed>1</Speed>')
    print('cast ok:', image_url)
    return True

if __name__ == '__main__':
    cast_image(sys.argv[1], sys.argv[2])
