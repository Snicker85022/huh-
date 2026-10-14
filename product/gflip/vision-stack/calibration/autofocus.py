"""Software autofocus: sweep the PTZ focus motor to maximize image sharpness.

The camera has a continuous focus motor but no autofocus mode (rejected AUTO).
This script periodically sweeps focus and locks to the sharpest position.
"""
import cv2, time, sys, os
import numpy as np
import urllib.request, base64
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

HOST='192.168.2.117'
AUTH=base64.b64encode(b'admin:admin').decode()
STREAM='rtsp://192.168.2.117:554/stream0?username=admin&password=E10ADC3949BA59ABBE56E057F20F883E'

def raw_soap(body):
    env=f'''<?xml version="1.0" encoding="utf-8"?>
<s:Envelope xmlns:s="http://www.w3.org/2003/05/soap-envelope" xmlns:timg="http://www.onvif.org/ver20/imaging/wsdl">
<s:Body>{body}</s:Body></s:Envelope>'''
    req=urllib.request.Request(f'http://{HOST}/onvif/imaging', data=env.encode(), headers={
        'Content-Type':'application/soap+xml; charset=utf-8','Authorization':'Basic '+AUTH})
    return urllib.request.urlopen(req, timeout=10).read()

def focus_move(speed, dur):
    body=f'<timg:Move><timg:VideoSourceToken>VideoSourceMain</timg:VideoSourceToken><timg:Focus><timg:Continuous><timg:Speed>{speed}</timg:Speed></timg:Continuous></timg:Focus></timg:Move>'
    raw_soap(body); time.sleep(dur)
    raw_soap('<timg:Stop><timg:VideoSourceToken>VideoSourceMain</timg:VideoSourceToken><timg:Focus>true</timg:Focus></timg:Stop>')

def sharpness():
    cap=cv2.VideoCapture(STREAM, cv2.CAP_FFMPEG)
    cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC,6000)
    ok,f=cap.read(); cap.release()
    if not ok: return 0.0
    g=cv2.cvtColor(f, cv2.COLOR_BGR2GRAY)
    return cv2.Laplacian(g, cv2.CV_64F).var()

def autofocus_once():
    base = sharpness()
    print(f'[autofocus] base sharpness {base:.0f}', flush=True)
    best_cum=0.0; best_s=base
    cum=0.0
    # sweep + direction
    for step in [0.3,0.3,0.5,0.5,1.0,1.0,2.0,2.0]:
        cum+=step
        focus_move(1.0, step)
        s=sharpness()
        print(f'  +{cum:>4.1f}s sharpness {s:.0f}', flush=True)
        if s>best_s: best_s=s; best_cum=cum
    # sweep - direction (cross and continue past base)
    cum_neg=0.0
    for step in [0.3,0.3,0.5,0.5,1.0,1.0,2.0,2.0]:
        cum_neg+=step
        focus_move(-1.0, step)
        s=sharpness()
        print(f'  -{cum_neg:>4.1f}s sharpness {s:.0f}', flush=True)
        if s>best_s: best_s=s; best_cum=cum - cum_neg
    # return to best cumulative position
    if best_cum >= 0:
        focus_move(1.0, best_cum)
    else:
        focus_move(-1.0, -best_cum)
    print(f'[autofocus] locked best={best_s:.0f} at cumulative {best_cum:+.1f}s (base was {base:.0f})', flush=True)
    return best_s

if __name__=='__main__':
    interval = int(sys.argv[1]) if len(sys.argv)>1 else 300
    while True:
        try:
            autofocus_once()
        except Exception as e:
            print('[autofocus] error', repr(e)[:150], flush=True)
        time.sleep(interval)
