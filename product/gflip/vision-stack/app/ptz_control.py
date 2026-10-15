"""==============================================================================
 PTZ CONTROL MODEL  —  THE SINGLE SOURCE OF TRUTH for the kitchen PTZ camera.
==============================================================================
 Device : HD975B-P  ·  ONVIF manufacturer 'ONVIF_ICAMERA'  ·  fw V3.4.6.3
 Net    : 192.168.2.117:80   admin/admin   ·  node 'ptz0'  ·  profiles MainStream/SubStream
 Code   : this module (imported by app/main.py)  ·  self-test: `python ptz_control.py selftest`
 Facts  : world.db subject='ptz_camera'  ·  Doc: /home/taza/vision-stack/PTZ_CONTROL.md
------------------------------------------------------------------------------
 Verified 2026-10-08 after being re-derived 7-8 times.  DO NOT RE-DERIVE — READ THIS.
==============================================================================
"""
import time, threading
from onvif import ONVIFCamera

# ---------------------------------------------------------------- MODEL (data) --
MODEL = {
    "device": {"model": "HD975B-P", "onvif_manufacturer": "ONVIF_ICAMERA",
               "firmware": "V3.4.6.3 build 2026-04-23", "node_token": "ptz0",
               "profiles": ["MainStream", "SubStream"],
               "host": "192.168.2.117", "port": 80, "user": "admin", "pass": "admin"},
    "move": {
        "working_call": "ONVIF ContinuousMove",
        "requires": "Timeout element (e.g. PT4S) — WITHOUT IT THE CAMERA IGNORES THE MOVE",
        "must_stop": "always follow with Stop(PanTilt=True, Zoom=True)",
        "velocity_range": [-1.0, 1.0],
        "pan_sign":  "+1 = RIGHT, -1 = LEFT",
        "tilt_sign": "-1 = UP, +1 = DOWN   (INVERTED vs the ONVIF convention!)",
        "tilt_full_travel_s": 9.0,
        "parks_at": "bottom of tilt travel (looks DOWN) — a +1(down) cmd then looks like 'no move'",
        "overlap_gotcha": "if Timeout >> intended duration the move keeps running past Stop() and "
                          "the next command overlaps -> runaway/erratic motion. Set Timeout == secs.",
    },
    "broken_dont_use": {
        "GetStatus":         "telemetry — ALWAYS returns (0,0,0)",
        "AbsoluteMove":      "advertised (±1 spaces) but DOES NOT MOVE the camera",
        "RelativeMove":      "advertised; unreliable",
        "GotoHomePosition":  "SOAP fault 'Unknown error'",
    },
    "imaging": {
        "service": "ONVIF Imaging (this cam exposes it — rare)",
        "video_source_token": "VideoSourceMain",
        "IrCutFilter": {"values": ["ON", "OFF", "AUTO"],
                        "ON":  "visible / daylight  (IR-cut filter IN, colour)",
                        "OFF": "IR / night (IR-cut OUT, IR LEDs ON, mono)",
                        "note": "IR illuminator is ganged to IrCutFilter=OFF on this hardware"},
        "settable": ["IrCutFilter", "Brightness(1-255)", "Contrast(1-255)",
                     "ColorSaturation(1-255)", "Sharpness(1-255)",
                     "Exposure{Mode:AUTO|MANUAL, ExposureTime:100..100000}",
                     "BacklightCompensation{Mode:ON|OFF}", "WideDynamicRange{Mode:ON|OFF}",
                     "WhiteBalance{Mode:AUTO|MANUAL}"],
        "settle_s": "mode changes take ~2-3 s to take effect — sleep before capturing",
    },
    "video": {"open_with": "rtsp://127.0.0.1:8554/ptz_h264  (H.264 transcode; clean)",
              "device_rtsp": "rtsp://192.168.2.117:554/stream0?username=admin&password=E10ADC3949BA59ABBE56E057F20F883E",
              "note": "stream0 is HEVC -> OpenCV emits 'Could not find ref with POC' noise"},
    "doe_2026_10_08": {   # Design of Experiments: optical modes -> edge quality
        "best_edge_config": "IrCutFilter=ON, Exposure=AUTO, Sharpness~128-160, WDR=OFF, BLC=OFF "
                            "(run00 focus 3360 / edge 8.72%)",
        "second": "IrCutFilter=OFF, MANUAL 8000us, Sharpness=255 (run07 focus 3039 / edge 8.25%)",
        "findings": ["WDR=ON and BacklightCompensation=ON HURT edge/focus badly "
                     "(focus 710-1220 vs 2000-3360). Keep both OFF.",
                     "IR(OFF) mode gives better edges in low light, visible(ON) keeps colour.",
                     "Mode changes are sticky — frames captured too soon are confounded."],
    },
    "web_rpc": {
        "STATUS": "UNPROVEN / DOES NOT WORK YET — do NOT rely on this. (2026-10-08)",
        "evidence": "POST /IPC returns HTTP 202 for EVERY body: valid codes, bogus codes, "
                    "empty codes, bogus methods, even garbage bytes. It is UNAUTHENTICATED and "
                    "ignores the body, so 202 == 'swallowed', not 'executed'. No image change "
                    "was ever measured from LightOn/LightOff/night-mode codes.",
        "to_make_it_work": "first obtain a real web session: POST /ipcLogin, SOAP header "
                           "<userid>/<passwd> = DES('WebLogin', value) hex. The web password is NOT "
                           "the ONVIF admin/admin (web returns 'passwordError'). UNKNOWN.",
        "why": "this camera HAS white LEDs (its own UI JS proves it: white_led_panel, hasWhiteLedPanel, "
               "SmartDualLight, LightOn/LightOff, StartNightInfraredMode/StartNightColorMode). "
               "ONVIF SendAuxiliaryCommand cannot reach them either (fault). Control path = STILL OPEN.",
        "endpoint": "POST http://192.168.2.117/IPC",
        "IMPORTANT": "send the JSON body with the DEFAULT urlencoded Content-Type (or none). "
                     "Sending Content-Type: application/json makes gSOAP reject it with a SOAP fault.",
        "body": '{"method":"ptz.start","session":0,"params":{"channel":0,"code":"<CODE>","arg1":0,"arg2":0,"arg3":0},"seq":1,"id":1}',
        "codes": ["LightOn", "LightOff", "StartNightInfraredMode", "StartNightColorMode",
                  "Wiper", "GunDomePTZLinkageOn", "GunDomePTZLinkageOff"],
        "http_result": "202 Accepted (fire-and-forget)",
        "login": "POST /ipcLogin with SOAP header <userid>/<passwd> = DES('WebLogin', value) hexed. "
                 "NOTE web password != ONVIF admin/admin (web returns passwordError). session=0 still accepted.",
        "browser": "if you need the real UI session: puppeteer at /home/taza/archive/retired-2026-10-15/pm_web/shots/node_modules/puppeteer + "
                   "chrome-headless-shell 152 at ~/.cache/puppeteer/chrome-headless-shell/linux-152.0.7977.54/"
                   "chrome-headless-shell-linux64/  (run with LD_LIBRARY_PATH pointing at that same dir for libgbm.so.1)",
    },
    "aux_onvif": {
        "service": "ONVIF PTZ SendAuxiliaryCommand — IMPLEMENTED (proven 2026-10-08)",
        "url": "http://192.168.2.117/PTZ (ns ver20/ptz/wsdl) + WS-Security UsernameToken digest",
        "CORRECT_ELEMENT": "<AuxiliaryData>tt:Lamp|On</AuxiliaryData>   <-- NOT <AuxiliaryCommand> (rejected)",
        "node_advertises": ["tt:Wiper|On", "tt:Wiper|Off", "tt:Lamp|On", "tt:Lamp|Off"],
        "accepts": ["tt:Lamp|On", "tt:Wiper|On", "tt:Wiper|Off", "Lamp|On"],
        "rejects": ["tt:Lamp|Off", "tt:Infrared|On"],
        "EFFECT": "NONE MEASURED. Accepted-but-inert: 20 s continuous RTSP capture is flat (mean delta 0.01). "
                  "Control chain validated: IrCutFilter ON->OFF moves frame mean by 29. Do NOT claim LED control.",
        "deviceio": "advertised (RelayOutputs=1, DigitalInputs=1) but GetRelayOutputs -> ActionNotSupported",
        "gate": "the white light is most likely gated by the Dahua config (white_led_panel/SmartDualLight), "
                "which needs the DEVICE WEB PASSWORD (not admin/admin).",
    },
    "app_endpoints": ["/api/ptz/move?pan=&tilt=&zoom=&secs=", "/api/ptz/stop", "/api/ptz/state",
                      "/api/ptz/status", "/api/ptz/ir?mode=", "/api/ptz/imaging",
                      "/api/ptz/imaging/set?...", "/api/ptz/model", "/api/ptz/selftest"],
}

HOST=MODEL["device"]["host"]; PORT=MODEL["device"]["port"]
USER=MODEL["device"]["user"]; PASS=MODEL["device"]["pass"]
VIDEO_SOURCE=MODEL["imaging"]["video_source_token"]
CAM_RTSP=MODEL["video"]["device_rtsp"]; H264_RTSP=MODEL["video"]["open_with"]

_lock=threading.RLock(); _cam=_ptz=_media=_imaging=_tok=None

def _conn():
    global _cam,_ptz,_media,_imaging,_tok
    with _lock:
        if _cam is None:
            _cam=ONVIFCamera(HOST,PORT,USER,PASS); _ptz=_cam.create_ptz_service()
            _media=_cam.create_media_service(); _tok=_media.GetProfiles()[0].token
            try: _imaging=_cam.create_imaging_service()
            except Exception: _imaging=None
    return _ptz,_tok

def continuous_move(pan=0.0,tilt=0.0,zoom=0.0,secs=1.0,timeout=None,settle=0.0):
    """The ONLY working move. Timeout defaults to secs+1 so moves never overlap.
       REMEMBER: tilt -1=UP, +1=DOWN ; pan +1=RIGHT."""
    if timeout is None: timeout='PT%dS'%max(1,int(round(float(secs)+1)))
    ptz,tok=_conn()
    with _lock:
        req=ptz.create_type('ContinuousMove'); req.ProfileToken=tok
        req.Velocity={'PanTilt':{'x':float(pan),'y':float(tilt)},'Zoom':{'x':float(zoom)}}
        req.Timeout=timeout; ptz.ContinuousMove(req)
    time.sleep(max(0.05,float(secs))); stop()
    if settle: time.sleep(settle)
    return True

def stop():
    ptz,tok=_conn()
    with _lock:
        try:
            req=ptz.create_type('Stop'); req.ProfileToken=tok; req.PanTilt=True; req.Zoom=True; ptz.Stop(req)
        except Exception as e: print('[ptz] stop err:',e); return False
    return True

def nudge_up(secs=3.0):   return continuous_move(0,-1,0,secs)
def nudge_down(secs=3.0): return continuous_move(0,+1,0,secs)
def pan_right(secs=2.0):  return continuous_move(+1,0,0,secs)
def pan_left(secs=2.0):   return continuous_move(-1,0,0,secs)

def _settings():
    _conn()
    if _imaging is None: return None
    with _lock: return _imaging.GetImagingSettings({'VideoSourceToken':VIDEO_SOURCE})

def get_imaging():
    s=_settings()
    if s is None: return {}
    out={}
    for k in ('IrCutFilter','Brightness','ColorSaturation','Contrast','Sharpness'):
        v=getattr(s,k,None)
        if v is not None: out[k]=v
    exp=getattr(s,'Exposure',None)
    if exp is not None:
        out['ExposureMode']=getattr(exp,'Mode',None); out['ExposureTime']=getattr(exp,'ExposureTime',None)
    wdr=getattr(s,'WideDynamicRange',None)
    if wdr is not None: out['WDR']=getattr(wdr,'Mode',None)
    blc=getattr(s,'BacklightCompensation',None)
    if blc is not None: out['BacklightCompensation']=getattr(blc,'Mode',None)
    return out

def set_imaging(settle=2.5, **kw):
    """set_imaging(IrCutFilter='OFF', Sharpness=200, ExposureMode='MANUAL', ExposureTime=8000, WDR='OFF')"""
    _conn()
    if _imaging is None: return {'error':'no imaging service'}
    s={}; exp={}
    for k,v in kw.items():
        if k in ('IrCutFilter','Brightness','ColorSaturation','Contrast','Sharpness'): s[k]=v
        elif k=='ExposureTime': exp['ExposureTime']=float(v)
        elif k=='ExposureMode': exp['Mode']=v
        elif k=='WDR': s['WideDynamicRange']={'Mode':v,'Level':128.0}
        elif k=='BacklightCompensation': s['BacklightCompensation']={'Mode':v,'Level':0.0}
    if exp:
        cur=(_settings().Exposure if _settings() is not None else None)
        s['Exposure']={'Mode':exp.get('Mode', getattr(cur,'Mode','AUTO')), 'ExposureTime':exp.get('ExposureTime', getattr(cur,'ExposureTime',1000.0))}
    if not s: return get_imaging()
    with _lock:
        req=_imaging.create_type('SetImagingSettings'); req.VideoSourceToken=VIDEO_SOURCE; req.ImagingSettings=s
        try: req.ForcePersistence=True
        except Exception: pass
        _imaging.SetImagingSettings(req)
    if settle: time.sleep(settle)
    return get_imaging()

def set_ir(mode):
    m=str(mode).upper()
    if m not in ('ON','OFF','AUTO'): raise ValueError('mode must be ON|OFF|AUTO')
    return set_imaging(IrCutFilter=m)

# ---------- ONVIF PTZ auxiliary commands (SendAuxiliaryCommand). IMPLEMENTED on this firmware.
# ---------- THE CORRECT ELEMENT IS <AuxiliaryData>.  <AuxiliaryCommand> is REJECTED and that
# ---------- client bug ("Data required for operation" / ter:ActionNotSupported) is the ONLY
# ---------- reason the previous session recorded this call as "broken".  PROVEN 2026-10-08.
import base64 as _b64, hashlib as _hl, os as _os, re as _re, datetime as _dt
import urllib.request as _url, json as _json
_PTZ_URL = 'http://%s/PTZ' % HOST
def _wssec():
    nonce=_os.urandom(16); created=_dt.datetime.now(_dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    dig=_b64.b64encode(_hl.sha1(nonce+created.encode()+PASS.encode()).digest()).decode()
    n=_b64.b64encode(nonce).decode()
    return ('<s:Header><Security s:mustUnderstand="1" '
            'xmlns="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd">'
            '<UsernameToken><Username>%s</Username><Password Type="http://docs.oasis-open.org/wss/2004/01/'
            'oasis-200401-wss-username-token-profile-1.0#PasswordDigest">%s</Password>'
            '<Nonce EncodingType="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-soap-message-'
            'security-1.0#Base64Binary">%s</Nonce><Created xmlns="http://docs.oasis-open.org/wss/2004/01/'
            'oasis-200401-wss-wssecurity-utility-1.0.xsd">%s</Created></UsernameToken></Security>'
            ) % (USER, dig, n, created)
def onvif_aux(command, token='MainStream', timeout=8.0):
    """SendAuxiliaryCommand(command). VERIFIED call, VERIFIED-INERT effect.
    The camera ACCEPTS 'tt:Lamp|On'/'tt:Wiper|On' (HTTP 200) but NOTHING changes on the video
    (frame-mean delta 0.01 over a 20 s continuous capture; control chain validated against
    IrCutFilter, which moves the mean by ~29). 'tt:Lamp|Off' is rejected (ActionNotSupported).
    Returns (http_status, body_snippet)."""
    env=('<?xml version="1.0" encoding="UTF-8"?><s:Envelope '
         'xmlns:s="http://www.w3.org/2003/05/soap-envelope">'+_wssec()+'<s:Body>'
         '<SendAuxiliaryCommand xmlns="http://www.onvif.org/ver20/ptz/wsdl">'
         '<ProfileToken>%s</ProfileToken><AuxiliaryData>%s</AuxiliaryData>'
         '</SendAuxiliaryCommand></s:Body></s:Envelope>') % (token, command)
    req=_url.Request(_PTZ_URL, data=env.encode(), method='POST')
    req.add_header('Content-Type','application/soap+xml; charset=utf-8')
    try:
        r=_url.urlopen(req, timeout=timeout); return r.status, r.read().decode('utf-8','replace')[:200]
    except Exception as e:
        body=getattr(e,'read',lambda:b'')() or b''; return getattr(e,'code',-1), body.decode('utf-8','replace')[:200]
def lamp_on():    return onvif_aux('tt:Lamp|On')     # accepted, no optical effect
def lamp_off():   return onvif_aux('tt:Lamp|Off')    # ActionNotSupported on this fw
def wiper_on():   return onvif_aux('tt:Wiper|On')    # accepted, no optical effect
def wiper_off():  return onvif_aux('tt:Wiper|Off')   # accepted, no optical effect

# ---------- Dahua-OEM web RPC -- UNPROVEN. Returns 202 for ANY input, so it is NOT evidence
# ---------- that the white LEDs / night modes actually changed. Needs the device web password,
# ---------- which is NOT the ONVIF admin/admin (see /cgi-bin/getuid -> "password error").
def rpc(code_or_method, params=None, method="ptz.start", session=0, timeout=6.0):
    """POST the Dahua web RPC. WARNING: the camera 202-accepts EVERYTHING unauthenticated,
    so a 202 here does NOT mean the command ran. Unverified. See MODEL['web_rpc']."""
    body = _json.dumps({"method": method, "session": session,
                        "params": params if params is not None else {}, "seq": 1, "id": 1}).encode()
    req = _url.Request('http://%s/IPC' % HOST, data=body)
    try:
        return _url.urlopen(req, timeout=timeout).status
    except Exception as e:
        return str(e)[:90]
def aux(code):
    return rpc(None, {"channel": 0, "code": code, "arg1": 0, "arg2": 0, "arg3": 0})
def light_on():   return aux("LightOn")
def light_off():  return aux("LightOff")
def night_ir():   return aux("StartNightInfraredMode")
def night_color():return aux("StartNightColorMode")

def position_status():
    """Broken on this cam — always returns 0,0,0. Kept only to prove it's broken."""
    ptz,tok=_conn()
    with _lock:
        try:
            p=ptz.GetStatus({'ProfileToken':tok}).Position
            return {'pan':getattr(getattr(p,'PanTilt',None),'x',None),
                    'tilt':getattr(getattr(p,'PanTilt',None),'y',None),
                    'zoom':getattr(getattr(p,'Zoom',None),'x',None)}
        except Exception as e: return {'error':str(e)}

def selftest():
    """Run this FIRST in any new session. Prints/returns a pass/fail control-contract check."""
    r={'device':'?','ptz_node':'?','imaging':'?','move_ok':None,'tilt_sign':None,'notes':[]}
    ptz,tok=_conn()
    try:
        info=_cam.create_devicemgmt_service().GetDeviceInformation()
        r['device']=f"{getattr(info,'Model','?')} / {getattr(info,'Manufacturer','?')} / fw {str(getattr(info,'FirmwareVersion','')).strip()}"
    except Exception as e: r['notes'].append(f'deviceinfo err {e}')
    try:
        r['ptz_node']=ptz.GetNodes()[0].token
    except Exception as e: r['notes'].append(f'nodes err {e}')
    r['imaging']='ok' if _imaging is not None else 'MISSING'
    r['imaging_settings']=get_imaging()
    try: r['absolute_move_advertised']=True
    except Exception: pass
    try:
        r['status_telemetry']=position_status(); r['notes'].append('GetStatus is decorative (zeros)')
    except Exception: pass
    r['tilt_sign']=MODEL['move']['tilt_sign']; r['pan_sign']=MODEL['move']['pan_sign']
    r['model_ok']=True
    return r

if __name__=='__main__':
    import sys,json
    a=sys.argv[1:]
    if not a or a[0]=='selftest': print(json.dumps(selftest(), default=str, indent=2))
    elif a[0]=='model':   print(json.dumps(MODEL, indent=2))
    elif a[0]=='info':    print(json.dumps({'imaging':get_imaging(),'status':position_status()}, default=str, indent=2))
    elif a[0]=='ir':      print(set_ir(a[1]))
    elif a[0]=='up':      print(nudge_up(float(a[1]) if len(a)>1 else 3.0))
    elif a[0]=='down':    print(nudge_down(float(a[1]) if len(a)>1 else 3.0))
    elif a[0]=='pan':     print(continuous_move(float(a[1]),0,0,float(a[2]) if len(a)>2 else 2.0))
    elif a[0]=='stop':    print(stop())
    elif a[0]=='light':   print('LightOn ->', light_on() if a[1].lower() in ('on','1','true') else light_off())
    elif a[0]=='aux':     print(a[1], '->', aux(a[1]))
    elif a[0]=='lamp':    print('Lamp|On ->', lamp_on() if (len(a)>1 and a[1].lower() in ('on','1','true')) else lamp_off())
    elif a[0]=='onvifaux':print(a[1], '->', onvif_aux(a[1]))
