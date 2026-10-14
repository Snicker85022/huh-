import json,subprocess,time,csv,re,urllib.request,threading
from datetime import datetime
from pathlib import Path
from flask import Flask,render_template_string
app=Flask(__name__)
LOG=Path("/var/log/taza/health_log.csv")
def run(cmd):
 try:
  r=subprocess.run(cmd,shell=True,capture_output=True,text=True,timeout=5)
  return r.stdout.strip()
 except:return ""
def get_temps():
 t={};raw=run("sensors 2>/dev/null")
 for line in raw.splitlines():
  if "+" in line and "C" in line:
   try:
    label=line.split(":")[0].strip()
    val=float(line.split("+")[1].split("\xb0")[0])
    t[label]=val
   except:pass
 return t
def get_mem():
 o=run("free -b").splitlines()
 if len(o)>1:
  p=o[1].split();tot=int(p[1]);used=int(p[2]);avail=int(p[6]) if len(p)>6 else tot-used
  return{"total":round(tot/1e9,1),"used":round(used/1e9,1),"avail":round(avail/1e9,1),"pct":round(used/tot*100,1)}
 return{"total":0,"used":0,"avail":0,"pct":0}
def get_disk():
 o=run("df -B1 /").splitlines()
 if len(o)>1:
  p=o[1].split();tot=int(p[1]);used=int(p[2]);avail=int(p[3])
  return{"total":round(tot/1e9,1),"used":round(used/1e9,1),"avail":round(avail/1e9,1),"pct":round(used/tot*100,1)}
 return{"total":0,"used":0,"avail":0,"pct":0}
RAM_CFG_JSON=Path("/home/taza/reports/ram-config.json")
_ram_cfg_cache=None
def get_ram_cfg():
 # PART 4A: static RAM config captured once via dmidecode -> cached JSON.
 # Frequency is fixed at boot from SPD, not a live sensor; read file once.
 global _ram_cfg_cache
 if _ram_cfg_cache is None:
  try:_ram_cfg_cache=json.load(open(RAM_CFG_JSON))
  except Exception:_ram_cfg_cache={}
 return _ram_cfg_cache
def get_uptime():
 s=float(open("/proc/uptime").read().split()[0])
 return{"days":int(s//86400),"hours":int(s%86400//3600),"mins":int(s%3600//60)}
def get_load():
 p=open("/proc/loadavg").read().split()
 return{"m1":float(p[0]),"m5":float(p[1]),"m15":float(p[2])}
def svc(n):return run(f"systemctl is-active {n} 2>/dev/null")
def get_docker():
 o=run('docker ps --format "{{.Names}}|{{.Status}}" 2>/dev/null')
 out=[]
 for line in o.splitlines():
  if "|" in line:
   p=line.split("|");out.append({"name":p[0],"status":p[1],"up":"Up" in p[1]})
 return out
# Inventory keyed by MAC (DHCP-drift resistant). "ip" is the last-known hint;
# if the device roams to a new lease we re-resolve its current IP by MAC.
DEVICES=[
 {"name":"ER605 Router","mac":"58:04:4f:37:f0:3a","ip":"192.168.2.1"},
 {"name":"z33 Panel","mac":"20:18:0e:d5:a4:e3","ip":"192.168.2.105"},
 {"name":"MT1 East KDS","mac":"48:5a:67:a0:74:31","ip":"192.168.2.108"},
 {"name":"MT2 West KDS","mac":"48:5a:67:a0:4c:3e","ip":"192.168.2.104"},
 {"name":"Alexa TV","mac":"a8:4a:63:b4:f7:1f","ip":"192.168.2.109"},          # Insignia/TPV, MAC-confirmed
  # Realtek OUI, presumed TCL
 {"name":"TCL TV B (unconf)","mac":"00:e0:4c:58:59:70","ip":"192.168.2.106"}, # Realtek OUI, presumed TCL
]
def alive(ip):
 # 2 probes @0.3s, 2s wait: online if ANY reply (tolerates WiFi jitter/1 drop)
 m=re.search(r"(\d+) received",run(f"ping -c 2 -i 0.3 -W 2 {ip}"))
 return bool(m) and int(m.group(1))>0
def neigh_ip(mac):
 # current IP holding this MAC per kernel neighbor table (survives DHCP drift)
 mac=mac.lower()
 for line in run("ip neigh show").splitlines():
  p=line.split()
  if len(p)>=5 and "lladdr" in p and p[p.index("lladdr")+1].lower()==mac and p[-1] not in("FAILED","INCOMPLETE"):
   return p[0]
 return ""
def check_device(d):
 ip=d["ip"]
 if alive(ip):return{"name":d["name"],"ip":ip,"status":"online"}
 cur=neigh_ip(d["mac"])                       # self-heal: device may have a new lease
 if cur and cur!=ip and alive(cur):
  return{"name":d["name"],"ip":cur,"status":"online"}
 return{"name":d["name"],"ip":ip,"status":"offline"}
def ping(ip):
 return "online" if alive(ip) else "offline"  # kept for compatibility
def get_devices():
 out=[None]*len(DEVICES)                       # parallel checks: keeps page render fast
 def w(i):out[i]=check_device(DEVICES[i])
 ts=[threading.Thread(target=w,args=(i,)) for i in range(len(DEVICES))]
 for t in ts:t.start()
 for t in ts:t.join()
 return out
def get_ai():
 # Report the model(s) actually loaded, not a hardcoded name. This box may host >1 model.
 # /slots gives per-slot busy state but is only present if llama-server was started --slots;
 # otherwise fall back to /props (default-slot is_processing) for the active/idle signal, and
 # always enumerate loaded models via /v1/models.
 base="http://localhost:8081"
 def fetch(p):
  try:return json.loads(urllib.request.urlopen(base+p,timeout=2).read())
  except:return None
 online=fetch("/health") is not None
 busy=False;tps=0.0;pt=0;ct=0;ctx=0
 slots=fetch("/slots")                                   # only if server started with --slots
 if isinstance(slots,list) and slots:
  slot=slots[0];busy=slot.get("state",0)==1
  tm=slot.get("timings",{});tps=round(tm.get("predicted_per_second",0),1)
  pt=int(tm.get("prompt_n",0) or 0);ct=int(tm.get("predicted_n",0) or 0);ctx=int(slot.get("n_ctx",0) or 0)
 else:
  props=fetch("/props")                                  # fallback active/idle signal
  if props:busy=bool(props.get("default_generation_settings",{}).get("is_processing",False))
 models=[]
 md=fetch("/v1/models")                                  # actual loaded model(s)
 if md and isinstance(md.get("data"),list):
  for m in md["data"]:
   nm=(m.get("id") or "unknown").split("/")[-1]
   if nm.endswith(".gguf"):nm=nm[:-5]
   models.append({"name":nm,"state":"ACTIVE" if busy else "IDLE"})
 state="OFFLINE" if not online else("BUSY" if busy else "IDLE")
 return{"online":online,"busy":busy,"tps":tps,"models":models,"state":state,
  "prompt_tokens":pt,"completion_tokens":ct,"total_tokens":pt+ct,"context_used":ctx}
def get_ornith():
 base="http://localhost:8082"
 def fetch(p):
  try:return json.loads(urllib.request.urlopen(base+p,timeout=2).read())
  except:return None
 online=fetch("/health") is not None
 busy=False;tps=0.0;pt=0;ct=0;ctx=0
 if online:
  slots=fetch("/slots")
  if isinstance(slots,list) and slots:
   slot=slots[0];busy=slot.get("state",0)==1
   tm=slot.get("timings",{});tps=round(tm.get("predicted_per_second",0),1)
   pt=int(tm.get("prompt_n",0) or 0);ct=int(tm.get("predicted_n",0) or 0);ctx=int(slot.get("n_ctx",0) or 0)
 state="OFFLINE" if not online else("BUSY" if busy else "IDLE")
 return{"online":online,"busy":busy,"tps":tps,"model":"Ornith-1.0-35B","state":state,
  "prompt_tokens":pt,"completion_tokens":ct,"total_tokens":pt+ct,"context_used":ctx}

def get_gflip():
 # gflip (.107): Qwen3-30B-A3B on :8080 (AMDVLK GPU) + failover state page on :8088
 def fetch(url):
  try:return json.loads(urllib.request.urlopen(url,timeout=2).read())
  except:return None
 ll=fetch("http://192.168.2.107:8080/health")
 st=fetch("http://192.168.2.107:8088/status.json")
 online=ll is not None
 busy=False;tps=0.0
 props=fetch("http://192.168.2.107:8080/props")
 if props:busy=bool(props.get("default_generation_settings",{}).get("is_processing",False))
 md=fetch("http://192.168.2.107:8080/v1/models")
 models=[]
 if md and isinstance(md.get("data"),list):
  for m in md["data"]:
   nm=(m.get("id") or "unknown").split("/")[-1]
   if nm.endswith(".gguf"):nm=nm[:-5]
   models.append(nm)
 mode=(st or {}).get("mode","GPU");reason=(st or {}).get("reason","");since=(st or {}).get("since","")
 state="OFFLINE" if not online else ("BUSY" if busy else "IDLE")
 return {"online":online,"busy":busy,"tps":tps,"models":models,"state":state,
  "mode":mode,"reason":reason,"since":since}
def get_mhz():
 o=run("cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq 2>/dev/null")
 try:return int(o.strip())//1000
 except:return 0
def get_nocodb():
 o=run("curl -s --max-time 3 -o /dev/null -w '%{http_code}' http://localhost:8080 2>/dev/null")
 return "online" if o.strip()=="200" else f"http:{o.strip()}"
def get_printer():
 # Star Micronics TSP143IIIU: (1) USB presence via lsusb (vendor 0519), (2) CUPS queue via lpstat -p
 usb=run("lsusb")
 usb_ok=("Star Micronics" in usb) or ("0519:" in usb)
 lp=run("lpstat -p 2>/dev/null")            # empty if CUPS absent or no queue
 cups_ok=False;state="not configured";name=""
 for line in lp.splitlines():
  if line.startswith("printer"):
   p=line.split();name=p[1] if len(p)>1 else "";low=line.lower();cups_ok=True
   if "disabled" in low or "offline" in low:state="offline"
   elif "printing" in low or "processing" in low:state="processing"
   elif "idle" in low:state="idle"
   elif "enabled" in low:state="ready"
   else:state="unknown"
   break
 return{"usb":usb_ok,"cups":cups_ok,"state":state,"name":name}
def log_health(temps,mem,disk,load,svcs):
 pkg=temps.get("Package id 0",temps.get("temp1",0))
 hdr=not LOG.exists() or LOG.stat().st_size==0
 with open(LOG,"a",newline="") as f:
  import csv as cm;w=cm.writer(f)
  if hdr:w.writerow(["ts","cpu_c","mem_pct","disk_pct","load_1m","llama","pg"])
  w.writerow([datetime.now().isoformat(),round(pkg,1),mem["pct"],disk["pct"],load["m1"],svcs.get("llama-server","?"),svcs.get("postgresql","?")])
def get_dm():
 if not LOG.exists():return{"dm":0,"days":0,"n":0,"avg":0,"mx":0}
 rows=[]
 try:
  import csv as cm
  with open(LOG) as f:
   for row in cm.DictReader(f):
    try:rows.append({"ts":datetime.fromisoformat(row["ts"]),"c":float(row["cpu_c"])})
    except:pass
 except:return{"dm":0,"days":0,"n":0,"avg":0,"mx":0}
 if len(rows)<2:return{"dm":0,"days":0,"n":len(rows),"avg":0,"mx":0}
 dm=sum((rows[i]["c"]+rows[i-1]["c"])/2*(rows[i]["ts"]-rows[i-1]["ts"]).total_seconds()/60 for i in range(1,len(rows)))
 span=(rows[-1]["ts"]-rows[0]["ts"]).total_seconds()/86400
 return{"dm":round(dm),"days":round(span,1),"n":len(rows),"avg":round(sum(r["c"] for r in rows)/len(rows),1),"mx":round(max(r["c"] for r in rows),1)}

# --- UPS (apcaccess) ---
_ups={};_ups_lock=threading.Lock();_ups_min=None;_ups_max=None
def parse_ups():
 raw=run("apcaccess status 2>/dev/null");d={}
 for line in raw.splitlines():
  if ":" in line:
   k,_,v=line.partition(":");d[k.strip()]=v.strip()
 return d
def sample_ups():
 global _ups,_ups_min,_ups_max
 d=parse_ups()
 if not d:return
 try:lv=float(d.get("LINEV","").split()[0])
 except:lv=None
 with _ups_lock:
  if lv is not None:
   _ups_min=lv if _ups_min is None else min(_ups_min,lv)
   _ups_max=lv if _ups_max is None else max(_ups_max,lv)
  _ups=d
def get_ups():
 with _ups_lock:d=dict(_ups);mn=_ups_min;mx=_ups_max
 if not d:
  sample_ups()
  with _ups_lock:d=dict(_ups);mn=_ups_min;mx=_ups_max
 def num(k):
  try:return float(d.get(k,"").split()[0])
  except:return 0
 lv=num("LINEV")
 return{"status":d.get("STATUS","UNKNOWN"),"online":"ONLINE" in d.get("STATUS",""),
  "linev":lv,"lmin":round(mn,1) if mn is not None else lv,"lmax":round(mx,1) if mx is not None else lv,
  "bcharge":num("BCHARGE"),"timeleft":num("TIMELEFT"),"lastxfer":d.get("LASTXFER","N/A"),
  "numxfers":d.get("NUMXFERS","0"),"model":d.get("MODEL","UPS"),"ok":bool(d)}
def _ups_loop():
 while True:
  try:sample_ups()
  except:pass
  time.sleep(7)
threading.Thread(target=_ups_loop,daemon=True).start()

# === PART 1 REBUILD: live CPU metrics engine (rolling in-memory buffers + SVG traces) ===
# Rationale: page uses 30s meta-refresh, so time-series must accumulate server-side.
# A background thread samples every 3s into fixed-length deques; SVG polylines are
# rendered from those buffers each request. No external JS/chart libs (self-contained).
from collections import deque
import glob as _glob
_HIST=90; _CORES=4
CORE_COLORS=["#00e676","#40c4ff","#ffb300","#b388ff"]  # green/blue/amber/purple per core
_temp_hist=[deque(maxlen=_HIST) for _ in range(_CORES)]
_pct_hist=[deque(maxlen=_HIST) for _ in range(_CORES)]
_watt_hist=deque(maxlen=_HIST); _eff_hist=deque(maxlen=_HIST)
_metrics_lock=threading.Lock(); _prev_cpu={}; _thr_prev=[None]; _throttled=[False]
_cur={"temps":[0]*_CORES,"pct":[0.0]*_CORES,"watts":0.0,"eff":0.0,"ptps":0.0,"median":0.0}
def _coretemp_dir():
 for h in _glob.glob("/sys/class/hwmon/hwmon*"):
  try:
   if open(h+"/name").read().strip()=="coretemp":return h
  except:pass
 return None
_CT_DIR=_coretemp_dir()
def read_core_temps():
 out=[None]*_CORES
 if not _CT_DIR:return out
 for lf in _glob.glob(_CT_DIR+"/temp*_label"):
  try:
   lab=open(lf).read().strip()
   if lab.startswith("Core"):
    idx=int(lab.split()[1])
    if 0<=idx<_CORES:out[idx]=int(open(lf.replace("_label","_input")).read().strip())/1000.0
  except:pass
 return out
def read_core_pct():
 out=[0.0]*_CORES
 try:
  for line in open("/proc/stat"):
   if line.startswith("cpu") and len(line)>3 and line[3].isdigit():
    p=line.split();name=p[0]
    try:idx=int(name[3:])
    except:continue
    if idx>=_CORES:continue
    vals=list(map(int,p[1:]))
    idle=vals[3]+(vals[4] if len(vals)>4 else 0);total=sum(vals)
    pv=_prev_cpu.get(name)
    if pv:
     dt=total-pv[0];di=idle-pv[1]
     out[idx]=max(0.0,min(100.0,100.0*(dt-di)/dt)) if dt>0 else 0.0
    _prev_cpu[name]=(total,idle)
 except:pass
 return out
def read_throttle_total():
 # sum of per-core thermal_throttle counters; a rising total => currently throttling
 c=0
 for f in _glob.glob("/sys/devices/system/cpu/cpu*/thermal_throttle/core_throttle_count"):
  try:c+=int(open(f).read())
  except:pass
 return c
def _sample_metrics():
 temps=read_core_temps();pct=read_core_pct();cnt=read_throttle_total()
 avg=sum(pct)/len(pct) if pct else 0.0
 watts=round(6.0+(avg/100.0)*14.0,1)   # ESTIMATE: no intel-rapl on this N100; load-model proxy
 ptps=round(avg*4.5,1)                  # PLACEHOLDER tokens/sec proxy (real token accounting = follow-up)
 eff=round(ptps/watts,2) if watts>0 else 0.0
 valid=[t for t in temps if t is not None];median=0.0
 if valid:
  s=sorted(valid);n=len(s);median=s[n//2] if n%2 else (s[n//2-1]+s[n//2])/2
 with _metrics_lock:
  for i in range(_CORES):
   if temps[i] is not None:_temp_hist[i].append(temps[i])
   _pct_hist[i].append(pct[i])
  _watt_hist.append(watts);_eff_hist.append(eff)
  if _thr_prev[0] is not None:_throttled[0]=cnt>_thr_prev[0]
  _thr_prev[0]=cnt
  _cur.update(temps=[t if t is not None else 0 for t in temps],pct=pct,watts=watts,eff=eff,ptps=ptps,median=round(median,1))
def _metrics_loop():
 read_core_pct()  # prime /proc/stat deltas
 while True:
  try:_sample_metrics()
  except:pass
  time.sleep(3)
threading.Thread(target=_metrics_loop,daemon=True).start()
def _poly(vals,w,h,lo,hi,N):
 span=hi-lo if hi>lo else 1.0;pts=[]
 for i,v in enumerate(vals):
  x=(i/(N-1))*w if N>1 else w/2.0
  y=h-1-((v-lo)/span)*(h-2)
  pts.append("%.1f,%.1f"%(x,y))
 return " ".join(pts)
def svg_thermal(w=320,h=88,lo=30.0,hi=95.0):
 with _metrics_lock:series=[list(_temp_hist[i]) for i in range(_CORES)]
 N=max((len(s) for s in series),default=0)
 head='<svg viewBox="0 0 %d %d" preserveAspectRatio="none" style="width:100%%;height:%dpx">'%(w,h,h)
 if N<1:return head+"</svg>"
 grid=""
 for gy in (50,70,85):
  y=h-1-((gy-lo)/(hi-lo))*(h-2)
  grid+='<line x1="0" y1="%.1f" x2="%d" y2="%.1f" stroke="#16221b" stroke-width="1"/>'%(y,w,y)
 lines=""
 for i in range(_CORES):
  if series[i]:lines+='<polyline fill="none" stroke="%s" stroke-width="1.6" points="%s"/>'%(CORE_COLORS[i],_poly(series[i],w,h,lo,hi,N))
 return head+grid+lines+"</svg>"
def svg_spark(vals,color,w=64,h=18,lo=None,hi=None):
 head='<svg viewBox="0 0 %d %d" preserveAspectRatio="none" style="width:%dpx;height:%dpx">'%(w,h,w,h)
 if not vals:return head+"</svg>"
 lo=min(vals) if lo is None else lo;hi=max(vals) if hi is None else hi
 if hi<=lo:hi=lo+1
 return head+'<polyline fill="none" stroke="%s" stroke-width="1.5" points="%s"/></svg>'%(color,_poly(vals,w,h,lo,hi,len(vals)))
def build_metrics_view():
 thermal=svg_thermal()
 with _metrics_lock:
  cur=dict(_cur);pser=[list(_pct_hist[i]) for i in range(_CORES)];eser=list(_eff_hist);thr=_throttled[0]
 work=[{"i":i,"color":CORE_COLORS[i],"pct":round(cur["pct"][i]),"spark":svg_spark(pser[i],CORE_COLORS[i],lo=0,hi=100)} for i in range(_CORES)]
 return {"thermal_svg":thermal,"work":work,"cur":cur,"throttled":thr,"eff_spark":svg_spark(eser,"#00e676")}

# === PART 2: INFERENCE ECONOMICS + TOTAL SYSTEM COST ===
# Token/throughput/savings series are a CLEARLY-LABELED SAMPLE: no real per-model
# history exists yet (inference_perf_log.csv has 0 rows with tokens_per_sec set;
# the logger only records tps while a slot is actively serving). Wiring real token
# accounting into these traces is a follow-up. The TOTAL SYSTEM COST figures are
# REAL seed numbers from Nick (capital + recurring); forward months project ~$97/mo.
import math as _math
ECON_MONTHS=["May","Jun","Jul","Aug","Sep","Oct"]              # 2026, m0=May (contract start)
_SONNET_BLEND=9.0   # $/M counterfactual: Sonnet ~$3/M in + $15/M out, ~50/50 blend
_TOK={"1.5b":[8,12,15,18,20,22],"7b":[3,5,7,8,9,10],"14b":[1,2,3,3.5,4,4.5]}   # SAMPLE M tokens/mo
_TPS={"1.5b":[42,44,45,45,46,46],"7b":[11,12,12,13,12,13],"14b":[5.5,6,6,6.2,6,6.3],"api":[58,60,62,61,63,62]}  # SAMPLE tok/s
_API_SPEND=[15,22,28,30,32,34]   # SAMPLE metered Claude API $/mo (separate from Pro Max subscription)
CAPITAL=646.87   # N100 365 + cooling 40 + cables 55 + ER605 40 + 2x switch 32 + SG108 28 + UPS 86.87
MONTHLY=97.0     # Pro Max 85 (85% of 100) + electricity ~11 + domains ~1
def _cumsum(a):
 s=0;o=[]
 for v in a:s+=v;o.append(round(s,2))
 return o
def _cum_savings(tier):return [round(v*_SONNET_BLEND,1) for v in _cumsum(_TOK[tier])]
def _cum_cost():return [round(CAPITAL+MONTHLY*(i+1),2) for i in range(len(ECON_MONTHS))]
def _cum_local_savings():
 a=_cum_savings("1.5b");b=_cum_savings("7b");c=_cum_savings("14b")
 return [round(a[i]+b[i]+c[i],1) for i in range(len(ECON_MONTHS))]
def _fmt_ax(v):
 if v>=1000:return "%.1fk"%(v/1000.0)
 return "%.0f"%v if v>=10 else "%.1f"%v
def _dpts(vals,x0,x1,y0,y1,lo,hi):
 span=(hi-lo) or 1.0;N=len(vals);out=[]
 for i,v in enumerate(vals):
  x=x0+(i/(N-1))*(x1-x0) if N>1 else (x0+x1)/2.0
  out.append("%.1f,%.1f"%(x,y1-((v-lo)/span)*(y1-y0)))
 return " ".join(out)
def _interp(a,idx):
 i=int(idx);f=idx-i
 return a[-1] if i>=len(a)-1 else a[i]+(a[i+1]-a[i])*f
def svg_dual(lvals,rvals,lc,rc,W=340,H=84):
 ML,MR,MT,MB=34,42,8,18;x0,x1,y0,y1=ML,W-MR,MT,H-MB
 lhi=max(max(lvals)*1.15,1.0);rhi=max(max(rvals)*1.10,1.0);N=len(ECON_MONTHS)
 s='<svg viewBox="0 0 %d %d" style="width:100%%;height:%dpx">'%(W,H,H)
 for k in (0.5,1.0):
  gy=y1-k*(y1-y0);s+='<line x1="%d" y1="%.1f" x2="%d" y2="%.1f" stroke="#16221b" stroke-width="1"/>'%(x0,gy,x1,gy)
 for i,m in enumerate(ECON_MONTHS):
  x=x0+(i/(N-1))*(x1-x0);s+='<text x="%.1f" y="%d" fill="#a0aec0" font-size="9" text-anchor="middle">%s</text>'%(x,H-5,m)
 s+='<text x="2" y="%d" fill="%s" font-size="9">%s</text>'%(MT+7,lc,_fmt_ax(lhi))
 s+='<text x="2" y="%.1f" fill="%s" font-size="9">0</text>'%(y1,lc)
 s+='<text x="%d" y="%d" fill="%s" font-size="9">%s</text>'%(W-MR+3,MT+7,rc,_fmt_ax(rhi))
 s+='<text x="%d" y="%.1f" fill="%s" font-size="9">0</text>'%(W-MR+3,y1,rc)
 s+='<polyline fill="none" stroke="%s" stroke-width="1.8" points="%s"/>'%(lc,_dpts(lvals,x0,x1,y0,y1,0.0,lhi))
 s+='<polyline fill="none" stroke="%s" stroke-width="1.8" points="%s"/>'%(rc,_dpts(rvals,x0,x1,y0,y1,0.0,rhi))
 return s+'</svg>'
def svg_cost(cost,save,be,W=340,H=96):
 ML,MR,MT,MB=40,10,8,18;x0,x1,y0,y1=ML,W-MR,MT,H-MB
 hi=max(max(cost),max(save))*1.08;N=len(ECON_MONTHS)
 s='<svg viewBox="0 0 %d %d" style="width:100%%;height:%dpx">'%(W,H,H)
 for k in (0.25,0.5,0.75,1.0):
  gy=y1-k*(y1-y0)
  s+='<line x1="%d" y1="%.1f" x2="%d" y2="%.1f" stroke="#16221b" stroke-width="1"/>'%(x0,gy,x1,gy)
  s+='<text x="2" y="%.1f" fill="#a0aec0" font-size="9">$%s</text>'%(gy+3,_fmt_ax(k*hi))
 for i,m in enumerate(ECON_MONTHS):
  x=x0+(i/(N-1))*(x1-x0);s+='<text x="%.1f" y="%d" fill="#a0aec0" font-size="9" text-anchor="middle">%s</text>'%(x,H-5,m)
 s+='<polyline fill="none" stroke="#ffb300" stroke-width="2" points="%s"/>'%_dpts(cost,x0,x1,y0,y1,0.0,hi)
 s+='<polyline fill="none" stroke="#00e676" stroke-width="2" points="%s"/>'%_dpts(save,x0,x1,y0,y1,0.0,hi)
 if be:
  bx=x0+(be["idx"]/(N-1))*(x1-x0);cy=y1-((_interp(save,be["idx"]))/hi)*(y1-y0)
  s+='<line x1="%.1f" y1="%d" x2="%.1f" y2="%.1f" stroke="#ffffff" stroke-width="1" stroke-dasharray="3,2"/>'%(bx,MT,bx,y1)
  s+='<circle cx="%.1f" cy="%.1f" r="3.5" fill="#ffffff"/>'%(bx,cy)
  s+='<text x="%.1f" y="%d" fill="#ffffff" font-size="9" text-anchor="middle">breakeven</text>'%(min(bx,x1-24),MT+6)
 return s+'</svg>'
def build_econ():
 sav={t:_cum_savings(t) for t in ("1.5b","7b","14b")}
 tiers=[
  {"name":"Qwen 1.5b","lname":"tokens/sec","rname":"cost saved $","lc":"#40c4ff","rc":"#00e676","l":_TPS["1.5b"],"r":sav["1.5b"]},
  {"name":"Qwen 7b","lname":"tokens/sec","rname":"cost saved $","lc":"#40c4ff","rc":"#00e676","l":_TPS["7b"],"r":sav["7b"]},
  {"name":"Qwen 14b","lname":"tokens/sec","rname":"cost saved $","lc":"#40c4ff","rc":"#00e676","l":_TPS["14b"],"r":sav["14b"]},
  {"name":"Claude API","lname":"tokens/sec","rname":"cumulative spend $","lc":"#40c4ff","rc":"#ffb300","l":_TPS["api"],"r":_cumsum(_API_SPEND)},
 ]
 for t in tiers:t["svg"]=svg_dual(t["l"],t["r"],t["lc"],t["rc"])
 cost=_cum_cost();save=_cum_local_savings();be=None
 for i in range(len(cost)):
  if save[i]>=cost[i]:
   if i==0:be={"m":ECON_MONTHS[0],"idx":0.0}
   else:
    d0=save[i-1]-cost[i-1];d1=save[i]-cost[i];frac=d0/(d0-d1) if (d0-d1)!=0 else 0
    be={"m":ECON_MONTHS[i-1]+"→"+ECON_MONTHS[i],"idx":i-1+frac}
   break
 return {"tiers":tiers,"months":ECON_MONTHS,"cost_end":cost[-1],"save_end":save[-1],"be":be,"overlay":svg_cost(cost,save,be)}

# === PART 3A: REAL CPU POWER SIGNALS (turbostat RAPL + throttle-reason MSRs) ===
# Ground truth verified on THIS N100 (Alder Lake-N / 4x Gracemont) 2026-07-10:
#   turbostat PkgWatt/PKG_%/Bzy_MHz/Busy% return real values (idle ~0.5W @ ~1.1GHz).
#   MSR_PKG_POWER_LIMIT(0x610): PL1=15.0W (USL), PL2=20.0W.  RAPL unit(0x606)=0.125W.
#   MSR_PKG_POWER_INFO(0x614): TDP spec=6.0W.  MSR_VR_CURRENT_CONFIG(0x601)=0x120 -> ICCMAX 36.0A.
#   MSR_CORE_PERF_LIMIT_REASONS(0x64d)=0 across all cores at idle (no limits logged).
# turbostat+rdmsr need root: scoped NOPASSWD drop-in /etc/sudoers.d/taza-turbostat
# (read-only telemetry binaries) lets the taza-owned service call them non-interactively.
# Sampler mirrors Part 1: fixed-length deques; turbostat's own --interval IS the 4s pacing.
_PHIST=90
_pw_watt=deque(maxlen=_PHIST)    # PkgWatt (real RAPL package power, W)
_pw_pkgpct=deque(maxlen=_PHIST)  # PKG_% (interval fraction RAPL power-limiting was active)
_pw_mhz=deque(maxlen=_PHIST)     # Bzy_MHz (busy frequency)
_pw_busy=deque(maxlen=_PHIST)    # Busy% (isolates sustained-load windows for 3B jitter)
_pw_lock=threading.Lock()
_pw_cur={"watt":0.0,"pkgpct":0.0,"mhz":0,"busy":0.0,"ok":False}
_pw_start=time.time()
_pw_events=deque(maxlen=200)      # {ts, iso, name, meaning, power}
_pw_prev_seen=[0]                 # combined (status|log) reason bitmask, previous poll
_pw_ups_v=deque(maxlen=_PHIST)    # (ts, linev) for 3B cross-correlation with UPS sag
# MSR_CORE_PERF_LIMIT_REASONS(0x64d) bit map (Intel SDM std for Gracemont/ADL-N).
# Register=0 on this chip at build; names are SDM-standard definitions for 0x64d
# (empirical label confirmation would require inducing each limit condition).
# (status_bit, name, plain-language meaning, power_related_for_3B_excursion_count)
_LIMIT_BITS=[
 (0,"PROCHOT","external PROCHOT# asserted",False),
 (1,"Thermal","core thermal limit hit",False),
 (4,"ResidencyState","residency-state regulation",False),
 (5,"RATL","running-avg thermal limit",False),
 (6,"VRThermAlert","VR thermal alert",False),
 (7,"VRTDC","VR thermal design current",False),
 (8,"Amps","electrical/current (EDP) limit hit",True),
 (10,"PkgPwrL1","sustained power limit PL1 hit",True),
 (11,"PkgPwrL2","short-term power limit PL2 hit",True),
 (12,"MultiCoreTurbo","max multi-core turbo limit",False),
 (13,"TurboAtten","turbo transition attenuation",False),
]
def _rd(reg,cpu=None):
 c=("-p %d "%cpu) if cpu is not None else ""
 o=run("sudo -n /usr/sbin/rdmsr %s%s 2>/dev/null"%(c,reg))
 try:return int(o.strip(),16)
 except:return None
def _read_power_config():
 # Static config read once at startup (PL1/PL2/TDP/VR rarely change).
 unit=_rd("0x606");pu=0.125
 if unit is not None:pu=1.0/(1<<(unit & 0xf))
 lim=_rd("0x610");pl1=pl2=None
 if lim is not None:pl1=round((lim & 0x7FFF)*pu,1);pl2=round(((lim>>32)&0x7FFF)*pu,1)
 info=_rd("0x614");tdp=round((info & 0x7FFF)*pu,1) if info is not None else None
 vr=_rd("0x601");icc=round((vr & 0x1FFF)/8.0,1) if vr is not None else None
 return {"pu":pu,"pl1":pl1,"pl2":pl2,"tdp":tdp,"vr_raw":("0x%x"%vr if vr is not None else "n/a"),"icc":icc}
PWR_CFG=_read_power_config()
def _read_limit_reasons():
 # OR status(bits0-15) + sticky-log(bits16-31) across all cores -> combined reason mask
 seen=0
 for c in range(_CORES):
  v=_rd("0x64d",c)
  if v is None:continue
  seen|=((v & 0xFFFF)|((v>>16)&0xFFFF))
 return seen
def _parse_turbostat(raw):
 # header row = first line whose first token is non-numeric; package summary = first
 # numeric row with full column width (per-core rows have fewer columns).
 hdr=None
 for line in raw.splitlines():
  f=line.split()
  if not f:continue
  if not f[0].replace('.','',1).replace('-','',1).isdigit():hdr=f;continue
  if hdr and len(f)==len(hdr):return dict(zip(hdr,f))
 return None
def _sample_power():
 import subprocess
 try:
  r=subprocess.run("sudo -n /usr/bin/turbostat --quiet --interval 4 --num_iterations 1 --show PkgWatt,PKG_%,Bzy_MHz,Busy% 2>/dev/null",
   shell=True,capture_output=True,text=True,timeout=12)
  d=_parse_turbostat(r.stdout)
 except:d=None
 seen=_read_limit_reasons()
 now=time.time();iso=datetime.now().strftime("%H:%M:%S")
 try:lv=float(_ups.get("LINEV","").split()[0])
 except:lv=None
 with _pw_lock:
  if d:
   try:
    w=float(d.get("PkgWatt",0));p=float(d.get("PKG_%",0));m=int(float(d.get("Bzy_MHz",0)));b=float(d.get("Busy%",0))
    _pw_watt.append(w);_pw_pkgpct.append(p);_pw_mhz.append(m);_pw_busy.append(b)
    _pw_cur.update(watt=round(w,2),pkgpct=round(p,2),mhz=m,busy=round(b,1),ok=True)
   except:pass
  if lv is not None:_pw_ups_v.append((now,lv))
  prev=_pw_prev_seen[0];new=seen & ~prev      # rising-edge = a NEW logged event
  if new:
   for bit,name,meaning,ispow in _LIMIT_BITS:
    if new & (1<<bit):_pw_events.append({"ts":now,"iso":iso,"name":name,"meaning":meaning,"power":ispow})
  _pw_prev_seen[0]=seen
def _power_loop():
 while True:
  t0=time.time()
  try:_sample_power()
  except:pass
  dt=time.time()-t0
  if dt<3:time.sleep(3-dt)                     # guard against hot-spin if turbostat errors fast
threading.Thread(target=_power_loop,daemon=True).start()
def svg_power(vals,color,lo,hi,w=320,h=52,grid=None):
 head='<svg viewBox="0 0 %d %d" preserveAspectRatio="none" style="width:100%%;height:%dpx">'%(w,h,h)
 if not vals:return head+'</svg>'
 g=""
 for gv in (grid or []):
  y=h-1-((gv-lo)/((hi-lo) or 1))*(h-2);g+='<line x1="0" y1="%.1f" x2="%d" y2="%.1f" stroke="#16221b" stroke-width="1"/>'%(y,w,y)
 return head+g+'<polyline fill="none" stroke="%s" stroke-width="1.6" points="%s"/></svg>'%(color,_poly(vals,w,h,lo,hi,len(vals)))
def _stats(vals):
 n=len(vals)
 if n==0:return 0.0,0.0
 m=sum(vals)/n;return m,(sum((v-m)**2 for v in vals)/n)**0.5
def _sub_band(s):
 return "g" if (s is not None and s>=85) else ("a" if (s is not None and s>=60) else "r")
# === PART 3B: POWER QUALITY INDEX (PQI) — Ppk/DPMO/CV composite, SPC-flavored ===
# THRESHOLD/MAPPING CHOICES (all documented for Nick to tune):
#  min samples before scoring = 20 (~80s @4s cadence)
#  1) Wattage stability (40%): USL=PL1(15W), LSL=0; Ppk=min[(USL-m)/3s,(m-LSL)/3s];
#     map Ppk>=1.33->100, <=0->0 linear.  NOTE/FLAG: LSL=0 makes the LOWER capability
#     term dominate on an idle box (mean~0.5W), so a perfectly-stable low-power system
#     scores artificially low. Implemented exactly as specified; one-sided upper Cpu
#     (=(USL-m)/3s) is also surfaced in /power detail as the semantically-correct view.
#  2) Excursion rate (35%): power reasons only (Amps/PkgPwrL1/PkgPwrL2) per uptime-hr;
#     0/hr->100, >=10/hr->0 linear.
#  3) Freq jitter under load (25%): CV=stdev/mean of Bzy_MHz over Busy%>=50 samples;
#     CV<=2%->100, >=15%->0 linear. If <10 load samples: N/A, composite reweighted over
#     the remaining 0.75 (flagged in UI), NOT silently dropped.
#  Bands: green>=85, yellow 60-84, red<60.
def build_power_view(main=True):
 with _pw_lock:
  watt=list(_pw_watt);pkgpct=list(_pw_pkgpct);mhz=list(_pw_mhz);busy=list(_pw_busy)
  cur=dict(_pw_cur);events=list(_pw_events);upsv=list(_pw_ups_v)
 cfg=PWR_CFG;n=len(watt);MIN=20
 up_hr=max((time.time()-_pw_start)/3600.0,1e-6)
 # 1) wattage stability (Ppk)
 usl=cfg["pl1"] or 15.0;lsl=0.0;mean_w,sd_w=_stats(watt);ppk=cpu_up=s_watt=None
 if n>=MIN:
  if sd_w>1e-9:
   ppk=min((usl-mean_w)/(3*sd_w),(mean_w-lsl)/(3*sd_w));cpu_up=(usl-mean_w)/(3*sd_w)
   s_watt=max(0.0,min(100.0,(ppk/1.33)*100.0))
  else:ppk=99.9;cpu_up=99.9;s_watt=100.0
 # 2) excursion rate (power reasons only)
 exc=[e for e in events if e["power"]];exc_hr=len(exc)/up_hr
 s_exc=max(0.0,min(100.0,100.0*(1-exc_hr/10.0)))
 # 3) frequency jitter under sustained load
 LOAD=50.0;mhz_load=[mhz[i] for i in range(len(mhz)) if i<len(busy) and busy[i]>=LOAD]
 cv=s_jit=None
 if len(mhz_load)>=10:
  mm,ms=_stats(mhz_load);cv=(ms/mm*100.0) if mm>0 else 0.0
  s_jit=max(0.0,min(100.0,100.0*(1-(cv-2.0)/13.0)))
 # composite (reweight if jitter has no load samples yet)
 pqi=None;wnote=""
 if n>=MIN and s_watt is not None:
  if s_jit is not None:pqi=round(0.40*s_watt+0.35*s_exc+0.25*s_jit)
  else:pqi=round((0.40*s_watt+0.35*s_exc)/0.75);wnote="jitter N/A (no sustained-load samples yet) — PQI reweighted over wattage+excursion"
 band=_sub_band(pqi)
 # correlation flag: power excursion within +/-10s of a UPS line sag (<110V)
 corr=0
 for e in exc:
  for (tt,lv) in upsv:
   if lv<110.0 and abs(tt-e["ts"])<=10.0:corr+=1;break
 def txt(s,extra):return ("%d %s"%(round(s),extra)) if s is not None else "N/A"
 evs=list(reversed(events));evs=evs[:(12 if main else 200)]
 return {
  "n":n,"min":MIN,"cur":cur,"ok":cur.get("ok",False),
  "svg_watt":svg_power(watt,"#00e676",0.0,(cfg["pl2"] or 20.0),grid=[cfg["pl1"] or 15.0]),
  "svg_mhz":svg_power(mhz,"#40c4ff",500.0,3400.0,h=40),
  "svg_pkg":svg_power(pkgpct,"#ffb300",0.0,max(5.0,max(pkgpct) if pkgpct else 5.0),h=40),
  "events":evs,"pqi":pqi,"band":band,"corr":corr,"weights_note":wnote,
  "s_watt":round(s_watt) if s_watt is not None else None,"s_watt_band":_sub_band(s_watt),
  "s_watt_txt":txt(s_watt,("(Ppk %.2f)"%ppk) if ppk is not None else ""),
  "s_exc":round(s_exc),"s_exc_band":_sub_band(s_exc),"s_exc_txt":"%d (%.2f/hr)"%(round(s_exc),exc_hr),
  "s_jit":round(s_jit) if s_jit is not None else None,"s_jit_band":_sub_band(s_jit),
  "s_jit_txt":txt(s_jit,("(CV %.1f%%)"%cv) if cv is not None else ""),
  "ppk":round(ppk,2) if ppk is not None else None,"cpu_up":round(cpu_up,2) if cpu_up is not None else None,
  "cv":round(cv,1) if cv is not None else None,"exc_hr":round(exc_hr,2),"load_n":len(mhz_load),
  "mean_w":round(mean_w,2),"sd_w":round(sd_w,3),"usl":usl,
 }
def ups_volt_spark():
 # Small line-voltage trace for the curated UPS panel. Reuses the (ts,linev) series the
 # power sampler already collects (_pw_ups_v, ~6min @4s) — no new sampling thread needed.
 with _pw_lock:vals=[lv for (_,lv) in list(_pw_ups_v)]
 return svg_spark(vals,"#40c4ff",w=130,h=26,lo=100,hi=130) if len(vals)>=2 else ""

# === PART 4B: RAM BANDWIDTH HEALTH via INFERENCE-THROUGHPUT RESIDUAL ===
# SAME design pattern as Part 3B's PQI wattage residual: compare a PREDICTED figure from
# known physics against a MEASURED one, and track the residual's DRIFT over time as the
# health signal. Here the physics is the memory-bandwidth roofline for (MoE) inference:
#     predicted_tps = bandwidth_GBps / (active_params_B * bytes_per_param)
# DEPENDENCY (flagged): needs Part 4A's periodic STREAM/MLC bandwidth log for the MEASURED
# bandwidth term, AND real inference benchmark runs for the MEASURED tps term. Built to
# populate as those accumulate; shows an honest 'gathering baseline' state until then.
#
# bytes_per_param by quant (dispatch spec = effective bits-per-weight / 8):
BYTES_PER_PARAM={"Q4_K_M":0.5625,"Q5_K_M":0.6875,"Q6_K":0.8125,"Q8_0":1.0}
# active params PER TOKEN in billions. MoE counts ACTIVE experts, NOT total params (the
# whole point of the model): Ornith = Qwen3.5-35B-A3B => "A3B" => ~3.0B active, not 35B.
# Dense models: active == full size. Substring-matched against the reported model name.
MODEL_ACTIVE_B=[("ornith",3.0),("35b-a3b",3.0),("a3b",3.0),("qwen35moe",3.0),
 ("14b",14.0),("7b",7.0),("1.5b",1.5),("1_5b",1.5),("0.5b",0.5)]
# DATA CONTRACT (documented so Part 4A + future benchmark dispatches drop in cleanly):
#  bandwidth log  (Part 4A STREAM/MLC):   /home/taza/reports/ram-bandwidth-log.csv
#     tolerant reader: timestamp col (timestamp|ts|iso|time|date) + a GB/s col
#     (triad_gbps preferred, else any *_gbps / bandwidth); optional latency_ns ignored here.
#  benchmark log  (benchmark dispatches): /home/taza/reports/inference-benchmark-log.csv
#     header: timestamp,model,quant,active_params_b(optional),tokens_per_sec
#  ALSO harvests real tps from the live inference_perf_log.csv (collapsed to one point per
#  model per hour, max tps = representative run) as a fallback source.
#  residual history snapshot persisted to: ram-bandwidth-residual-log.csv (feeds tap-detail).
RAM_BW_LOG=Path("/home/taza/reports/ram-bandwidth-log.csv")
INF_BENCH_LOG=Path("/home/taza/reports/inference-benchmark-log.csv")
INF_PERF_LOG=Path("/home/taza/reports/inference_perf_log.csv")
RESID_LOG=Path("/home/taza/reports/ram-bandwidth-residual-log.csv")
RAM_MIN_POINTS=3          # < this => honest 'gathering baseline' state (dispatch target ~5)
RAM_TARGET_POINTS=5
# Trend is measured on the EFFICIENCY RATIO (actual/predicted), NOT the raw residual: real
# inference NEVER reaches the bandwidth roofline (compute/attention/KV/sampling overhead), so
# the residual is ALWAYS negative and dominated by a ~constant efficiency factor (~0.4-0.7).
# The DRIFT of that factor is the memory-degradation signal (cf. Part 3B's Ppk-LSL caveat).
RAM_STABLE_BAND=0.03      # |least-squares slope of efficiency-ratio per run| <= this => stable (TUNABLE)
def _bytes_per_param(q):
 if not q:return None
 return BYTES_PER_PARAM.get(str(q).strip().upper().replace("-","_"))
def _active_b(model):
 m=(model or "").lower()
 for key,v in MODEL_ACTIVE_B:
  if key in m:return v
 return None
def _guess_quant(model):
 m=(model or "").upper().replace("-","_")
 for q in BYTES_PER_PARAM:
  if q in m:return q
 return None
def _parse_ts(s):
 s=(s or "").strip()
 if not s:return None
 try:return datetime.fromisoformat(s[:26])
 except:pass
 for f in ("%Y-%m-%dT%H:%M:%S","%Y-%m-%d %H:%M:%S","%Y-%m-%d %H:%M"):
  try:return datetime.strptime(s[:19],f)
  except:pass
 return None
def _read_bw_log():
 # -> [(datetime, gbps)] sorted; tolerant of Part 4A's exact column names.
 out=[]
 if not RAM_BW_LOG.exists():return out
 try:
  import csv as cm
  with open(RAM_BW_LOG) as f:
   rd=cm.DictReader(f);cols={c.lower():c for c in (rd.fieldnames or [])}
   tcol=next((cols[c] for c in ("timestamp","ts","iso","time","date") if c in cols),None)
   bwcol=next((cols[c] for c in ("triad_gbps","triad","gbps","bandwidth_gbps","bandwidth","copy_gbps") if c in cols),None)
   if bwcol is None:
    bwcol=next((cols[c] for c in cols if "gbps" in c or "bandwidth" in c),None)
   if not tcol or not bwcol:return out
   for row in rd:
    ts=_parse_ts(row.get(tcol,""))
    try:g=float(str(row.get(bwcol,"")).split()[0])
    except:g=None
    if ts and g:out.append((ts,g))
 except:return out
 out.sort(key=lambda x:x[0]);return out
def _read_bench_points():
 # -> [{ts,model,quant,active_b,tps,source}] sorted by time.
 import csv as cm;pts=[]
 if INF_BENCH_LOG.exists():
  try:
   with open(INF_BENCH_LOG) as f:
    for row in cm.DictReader(f):
     ts=_parse_ts(row.get("timestamp","") or row.get("ts",""))
     try:tps=float(row.get("tokens_per_sec","") or row.get("tps",""))
     except:tps=None
     if not ts or not tps or tps<=0:continue
     model=row.get("model","");quant=row.get("quant","") or _guess_quant(model)
     try:ab=float(row.get("active_params_b",""))
     except:ab=_active_b(model)
     pts.append({"ts":ts,"model":model,"quant":quant,"active_b":ab,"tps":tps,"source":"bench-log"})
  except:pass
 if INF_PERF_LOG.exists():
  # collapse live-log samples to ONE representative point per (model, hour): max tps.
  buckets={}
  try:
   with open(INF_PERF_LOG) as f:
    for row in cm.DictReader(f):
     v=row.get("tokens_per_sec","")
     if not v:continue
     try:tps=float(v)
     except:continue
     if tps<=0:continue
     ts=_parse_ts(row.get("timestamp",""))
     if not ts:continue
     model=row.get("model","") or "";k=(model,ts.strftime("%Y%m%d%H"))
     if k not in buckets or tps>buckets[k][1]:buckets[k]=(ts,tps)
  except:pass
  for (model,_),(ts,tps) in buckets.items():
   pts.append({"ts":ts,"model":model,"quant":_guess_quant(model),"active_b":_active_b(model),"tps":tps,"source":"perf-log"})
 pts.sort(key=lambda x:x["ts"]);return pts
def _nearest_bw(ts,bw):
 return min(bw,key=lambda x:abs((x[0]-ts).total_seconds()))[1] if bw else None
def _compute_residuals():
 bw=_read_bw_log();rows=[]
 for p in _read_bench_points():
  bpp=_bytes_per_param(p["quant"]);ab=p["active_b"];g=_nearest_bw(p["ts"],bw)
  if not (bpp and ab and g):continue          # need all three terms to predict
  pred=g/(ab*bpp)
  if pred<=0:continue
  rows.append({"ts":p["ts"],"model":p["model"] or "?","quant":p["quant"] or "?","active_b":ab,"bpp":bpp,
   "meas_bw":round(g,1),"impl_bw":round(p["tps"]*ab*bpp,1),
   "actual_tps":round(p["tps"],2),"pred_tps":round(pred,2),
   "resid":round(p["tps"]-pred,2),"eff":round(p["tps"]/pred,3),"source":p["source"]})
 rows.sort(key=lambda x:x["ts"]);return rows
def _slope(ys):
 n=len(ys)
 if n<2:return 0.0
 xs=list(range(n));mx=sum(xs)/n;my=sum(ys)/n
 den=sum((x-mx)**2 for x in xs)
 return sum((xs[i]-mx)*(ys[i]-my) for i in range(n))/den if den>1e-12 else 0.0
_resid_persisted=[-1]
def _persist_resid(rows):
 if len(rows)==_resid_persisted[0]:return
 try:
  import csv as cm
  with open(RESID_LOG,"w",newline="") as f:
   w=cm.writer(f)
   w.writerow(["timestamp","model","quant","active_b","bytes_per_param","meas_bw_gbps","implied_bw_gbps","actual_tps","pred_tps","residual_tps","efficiency","source"])
   for r in rows:w.writerow([r["ts"].isoformat(),r["model"],r["quant"],r["active_b"],r["bpp"],r["meas_bw"],r["impl_bw"],r["actual_tps"],r["pred_tps"],r["resid"],r["eff"],r["source"]])
  _resid_persisted[0]=len(rows)
 except:pass
def build_ram_health():
 rows=_compute_residuals();n=len(rows);bw=_read_bw_log()
 res={"n":n,"target":RAM_TARGET_POINTS,"min":RAM_MIN_POINTS,"rows":rows,
  "bw_pts":len(bw),"have_bw":bool(bw),"gathering":n<RAM_MIN_POINTS,"stable_band":RAM_STABLE_BAND}
 if n>0:_persist_resid(rows)
 if n<RAM_MIN_POINTS:
  miss=[]
  if not bw:miss.append("Part 4A bandwidth log (STREAM/MLC)")
  if not rows:miss.append("real inference benchmark runs")
  res["missing"]=miss;return res
 effs=[r["eff"] for r in rows];sl=_slope(effs)
 res["slope"]=round(sl,4);res["cur"]=rows[-1];res["eff_mean"]=round(sum(effs)/n,3)
 if sl<=-RAM_STABLE_BAND:res["trend"]="degrading";res["band"]="r";res["band_word"]="DEGRADING"
 elif sl>=RAM_STABLE_BAND:res["trend"]="improving";res["band"]="g";res["band_word"]="IMPROVING"
 else:res["trend"]="stable";res["band"]="g";res["band_word"]="STABLE"
 return res

# === INFERENCE PERFORMANCE LOGGER ===
INF_PERF_COLS_V2=["timestamp","cpu_util_pct","cpu_freq_mhz","cpu_temp_c","thermal_throttle_flag","line_voltage",
 "tokens_per_sec","prompt_tokens","completion_tokens","total_tokens","context_used","model"]
def _migrate_perf_log():
 if not INF_PERF_LOG.exists():return
 try:
  import csv as cm,shutil
  with open(INF_PERF_LOG) as f:rd=cm.DictReader(f);hdr=list(rd.fieldnames or []);rows=list(rd)
  need_cols=any(c not in hdr for c in ["prompt_tokens","completion_tokens","total_tokens","context_used"])
  need_model=any(not r.get("model") for r in rows)
  if not need_cols and not need_model:return
  bak=str(INF_PERF_LOG)+".bak."+datetime.now().strftime("%Y%m%d_%H%M%S")
  shutil.copy2(str(INF_PERF_LOG),bak)
  with open(INF_PERF_LOG,"w",newline="") as f:
   w=cm.DictWriter(f,fieldnames=INF_PERF_COLS_V2,extrasaction="ignore")
   w.writeheader()
   for r in rows:
    if not r.get("model"):r["model"]="qwen7b"
    for c in ["prompt_tokens","completion_tokens","total_tokens","context_used"]:
     if c not in r:r[c]=""
    w.writerow(r)
 except:pass
_migrate_perf_log()
def _log_infer_row(model,tps,pt,ct,total,ctx):
 if tps<=0:return
 try:
  import csv as cm
  hdr=not INF_PERF_LOG.exists() or INF_PERF_LOG.stat().st_size==0
  with open(INF_PERF_LOG,"a",newline="") as f:
   w=cm.DictWriter(f,fieldnames=INF_PERF_COLS_V2,extrasaction="ignore")
   if hdr:w.writeheader()
   w.writerow({"timestamp":datetime.now().isoformat(),"cpu_util_pct":"","cpu_freq_mhz":"",
    "cpu_temp_c":"","thermal_throttle_flag":"","line_voltage":"",
    "tokens_per_sec":round(tps,2),"prompt_tokens":pt,"completion_tokens":ct,
    "total_tokens":total,"context_used":ctx,"model":model})
 except:pass
def _infer_log_loop():
 while True:
  time.sleep(30)
  try:
   _ai=get_ai();_orn=get_ornith()
   if _ai.get("busy") and _ai.get("tps",0)>0:
    _log_infer_row("qwen7b",_ai["tps"],_ai.get("prompt_tokens",0),_ai.get("completion_tokens",0),_ai.get("total_tokens",0),_ai.get("context_used",0))
   if _orn.get("busy") and _orn.get("tps",0)>0:
    _log_infer_row("ornith-35b",_orn["tps"],_orn.get("prompt_tokens",0),_orn.get("completion_tokens",0),_orn.get("total_tokens",0),_orn.get("context_used",0))
  except:pass
threading.Thread(target=_infer_log_loop,daemon=True).start()

T="""<!DOCTYPE html><html><head><meta charset=UTF-8>
<meta http-equiv=refresh content=30>
<title>Taza OS Health</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=Barlow:wght@400;600;700;900&display=swap');
/* HP HMI palette (ISA-101 / Hollifield): NORMAL = grey. Color is a scarce budget spent
   only on abnormal / action-required states + the PQI stoplight (an alarm-test-passing item). */
:root{--bg:#0a0c0f;--panel:#12151b;--card:#0c0e12;
--green:#00e676;--amber:#ffb300;--red:#ff3b3b;--blue:#5eb8ff;
--white:#e8ecf1;--dim:#8b94a3;--neutral:#5c6675;--line:#242b35;--gold:#C9A84C;
--font-hero:22px;--font-value:16px;--font-label:14px;--font-micro:12px;}
*{box-sizing:border-box;margin:0;padding:0;}
body{background:var(--bg);color:var(--white);font-family:Barlow,sans-serif;padding:12px;}
@keyframes flash{0%,100%{opacity:1}50%{opacity:.25}}
.alarm{animation:flash 1.3s infinite;}
header{display:flex;justify-content:space-between;align-items:baseline;border-bottom:2px solid var(--gold);padding-bottom:8px;margin-bottom:16px;}
.sn{font-size:var(--font-hero);color:var(--white);letter-spacing:.12em;font-weight:900;}
.ts{font-size:var(--font-micro);color:var(--dim);}
.ts a{color:var(--dim);text-decoration:none;font-weight:600;border-bottom:1px dotted var(--neutral);}
/* Panels: calm, low-contrast flat (Tufte data-ink / HP HMI). Neutral border by default. */
.p{background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:14px 16px;margin-bottom:18px;}
.pt{font-size:var(--font-label);letter-spacing:.14em;text-transform:uppercase;color:var(--gold);margin-bottom:10px;padding-bottom:7px;border-bottom:1px solid var(--line);font-weight:700;display:flex;justify-content:space-between;align-items:center;}
.det{color:var(--dim);text-decoration:none;font-size:var(--font-micro);font-weight:600;letter-spacing:.08em;}
.det:after{content:" \\2192";}
.row{display:flex;justify-content:space-between;align-items:center;padding:6px 0;border-bottom:1px solid var(--line);font-size:var(--font-label);}
.row:last-child{border-bottom:0;}
.rl{color:var(--white);font-size:var(--font-label);}
.rv{font-weight:700;font-size:var(--font-value);color:var(--dim);}
/* status colors — used ONLY for abnormal/action states + PQI */
.g{color:var(--green);}.a{color:var(--amber);}.r{color:var(--red);}.b{color:var(--blue);}
.n{color:var(--neutral);}.dim{color:var(--dim);}.w{color:var(--white);}
/* status dot: neutral hollow ring when normal, solid color only when it needs attention */
.dot{display:inline-block;width:12px;height:12px;border-radius:50%;margin-right:9px;vertical-align:middle;border:2px solid var(--neutral);}
.dot.ok{border-color:var(--neutral);background:transparent;}
.dot.warn{border-color:var(--amber);background:var(--amber);}
.dot.bad{border-color:var(--red);background:var(--red);}
.dot.busy{border-color:var(--blue);background:var(--blue);}
/* device presence cells */
.g4{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:8px;}
.dc{background:var(--card);border-radius:6px;padding:9px 6px;text-align:center;border:1px solid var(--line);}
.dc.off{border-color:var(--red);}
.dn{font-size:var(--font-label);font-weight:700;color:var(--dim);}
.di{font-size:var(--font-micro);color:var(--neutral);margin-top:2px;}
.ds{font-size:var(--font-value);font-weight:700;margin-top:4px;}
/* status banner */
.banner{border-radius:8px;padding:13px 16px;margin-bottom:18px;font-size:var(--font-value);font-weight:700;letter-spacing:.04em;display:flex;align-items:center;flex-wrap:wrap;gap:6px 14px;}
.banner.ok{background:var(--card);border:1px solid var(--line);color:var(--dim);}
.banner.warn{background:rgba(255,179,0,.08);border:1px solid var(--amber);color:var(--amber);}
.banner.bad{background:rgba(255,59,59,.10);border:1px solid var(--red);color:var(--red);}
.bchip{font-weight:700;}
.note{text-align:center;font-size:var(--font-micro);color:var(--neutral);margin-top:8px;}
.ts a{color:var(--dim);text-decoration:none;font-weight:600;}
.nav{display:flex;gap:8px;flex-wrap:wrap;margin:0 0 14px;}
.nav a{font-size:var(--font-micro);color:var(--dim);text-decoration:none;border:1px solid #2a3340;border-radius:5px;padding:5px 11px;letter-spacing:.05em;}
.nav a.here{color:var(--gold,#C9A84C);border-color:#C9A84C;font-weight:700;}
</style></head><body>
<header>
<div class=sn>TAZA OS &middot; taza-server &middot; 192.168.2.102</div>
<div class=ts>{{ now }} &middot; 30s &middot; <a href="/system">System</a> &middot; <a href="/diagnostics">Diagnostics</a> &middot; <a href="http://192.168.2.107:8088/" target=_blank rel=noopener>Llama GPU</a></div>
</header>
{% set pkg=temps.get("Package id 0",temps.get("temp1",0)) %}
{% set ma=mem.pct>85 %}
{% set da=disk.pct>80 %}
{% set la=load.m1>4.0 %}
{% set on_dev=devices|selectattr('status','equalto','online')|list|length %}
<!-- ===================================================================== -->
<!-- MAIN SCREEN (LEVEL 1) — HP HMI redesign 2026-07-10                     -->
<!-- ~5 glance groups. NORMAL renders grey; color = action-required only.   -->
<!-- Demoted per ISA-18.2 alarm test: Total System Cost -> /cost;           -->
<!--   Memory & Storage live gauges -> /system (escalate to banner if high) -->
<!-- ===================================================================== -->

<!-- 0. SYSTEM STATUS — the one-glance "is everything OK?" answer -->
{% set ns = namespace(al=[], red=false, amber=false) %}
{% if throttled %}{% set ns.al = ns.al + ["CPU thermally throttled"] %}{% set ns.red = true %}{% endif %}
{% if not ups.online %}{% set ns.al = ns.al + ["UPS on battery"] %}{% set ns.red = true %}{% endif %}
{% if ups.online and ups.bcharge < 40 %}{% set ns.al = ns.al + ["UPS battery " ~ ups.bcharge ~ "%"] %}{% set ns.amber = true %}{% endif %}
{% if cur.median >= 85 %}{% set ns.al = ns.al + ["CPU " ~ cur.median ~ "C"] %}{% set ns.red = true %}{% endif %}
{% if ma %}{% set ns.al = ns.al + ["RAM " ~ mem.pct ~ "%"] %}{% if mem.pct>=90 %}{% set ns.red = true %}{% else %}{% set ns.amber = true %}{% endif %}{% endif %}
{% if da %}{% set ns.al = ns.al + ["Disk " ~ disk.pct ~ "%"] %}{% if disk.pct>=90 %}{% set ns.red = true %}{% else %}{% set ns.amber = true %}{% endif %}{% endif %}
{% if la %}{% set ns.al = ns.al + ["Load " ~ load.m1] %}{% set ns.amber = true %}{% endif %}
{% if not printer.usb %}{% set ns.al = ns.al + ["Printer disconnected"] %}{% set ns.red = true %}{% endif %}
{% if not ai.online %}{% set ns.al = ns.al + ["AI engine down"] %}{% set ns.red = true %}{% endif %}
{% if gflip.mode == "DOWN" %}{% set ns.al = ns.al + ["gflip AI DOWN"] %}{% set ns.red = true %}{% elif gflip.mode == "CPU" %}{% set ns.al = ns.al + ["gflip AI on CPU fallback"] %}{% set ns.amber = true %}{% endif %}
{% if svc_issues %}{% set ns.al = ns.al + [(svc_issues|length|string) ~ " service(s) need attention"] %}{% set ns.red = true %}{% endif %}
{% if not ns.al %}
<div class="banner ok"><span>&#9679;</span> ALL SYSTEMS NORMAL <span class=n style="font-weight:600;">&middot; {{on_dev}}/{{devices|length}} devices online &middot; CPU {{cur.median}}C &middot; UPS {{ups.bcharge}}% &middot; RAM {{mem.pct}}%</span></div>
{% else %}
<div class="banner {{'bad' if ns.red else 'warn'}} {% if ns.red %}alarm{% endif %}"><span>&#9888; ATTENTION</span>{% for a in ns.al %}<span class=bchip>{{a}}</span>{% if not loop.last %}<span class=n>&middot;</span>{% endif %}{% endfor %}</div>
{% endif %}

<!-- 1. NETWORK DEVICE PRESENCE (kept per Nick) — online now calm/neutral, offline = red -->
<div class=p>
<div class=pt><span>Network Device Presence</span><span class=n style="font-weight:600;letter-spacing:.06em;">{{on_dev}}/{{devices|length}} online</span></div>
<div class=g4>
{% for d in devices %}
<div class="dc {% if d.status=='offline' %}off{% endif %}">
<div class=dn>{{d.name}}</div>
<div class=di>{{d.ip}}</div>
<div class="ds {{'r' if d.status=='offline' else 'n'}}">{{d.status.upper()}}</div>
</div>
{% endfor %}
</div>
</div>

<!-- 2. CPU THERMALS — trace kept (critical+variable). Bar/number grey until hot/throttling -->
<div class=p>
<div class=pt><span>CPU Thermals</span><a class=det href="/system">Detail</a></div>
<div style="height:5px;border-radius:3px;margin-bottom:11px;background:{{'var(--red)' if throttled else 'var(--line)'}};" title="{{'THERMALLY THROTTLED' if throttled else 'not throttled'}}"></div>
<div style="display:flex;align-items:center;gap:16px;">
<div style="flex:1;min-width:0;">{{thermal_svg|safe}}</div>
<div style="text-align:center;min-width:88px;">
<div style="font-size:28px;font-weight:900;line-height:1;" class="{{'r' if cur.median>=85 else ('a' if cur.median>=70 else 'n')}}">{{cur.median}}&deg;</div>
<div style="font-size:var(--font-micro);color:var(--neutral);margin-top:4px;">median core<br><span class="{{'r' if throttled else 'n'}}">{{'THROTTLED' if throttled else 'no throttle'}}</span></div>
</div>
</div>
<div style="display:flex;gap:18px;margin-top:9px;font-size:var(--font-micro);color:var(--neutral);">
{% for w in work %}<span>&#9632; <span style="color:{{w.color}};opacity:.75;">Core {{w.i}}</span></span>{% endfor %}
</div>
</div>

<!-- 3. POWER (merged UPS + PQI — same domain, kept co-visible per glass-cockpit) -->
<div class="p {% if not ups.online %}alarm{% endif %}">
<div class=pt><span>Power &mdash; {{ups.model}}</span><a class=det href="/power">Power detail</a></div>
<!-- UPS line -->
<div style="display:flex;align-items:center;gap:16px;padding-bottom:11px;border-bottom:1px solid var(--line);">
<div style="flex:1;">
<div style="font-size:var(--font-value);font-weight:700;" class="{{'n' if ups.online else 'r'}}">{{'ON LINE POWER' if ups.online else ups.status}}</div>
<div style="font-size:var(--font-label);margin-top:5px;color:var(--dim);">Battery <b class="{{'n' if ups.bcharge>=80 else ('a' if ups.bcharge>=40 else 'r')}}">{{ups.bcharge}}%</b> &middot; <b class="{{'n' if ups.timeleft>20 else ('a' if ups.timeleft>10 else 'r')}}">{{ups.timeleft}}m</b> runtime</div>
</div>
<div style="text-align:right;min-width:150px;">
<div style="font-size:var(--font-micro);color:var(--neutral);">Line Voltage</div>
{% if ups_spark %}<div style="line-height:0;">{{ups_spark|safe}}</div>{% endif %}
<div style="font-size:var(--font-value);font-weight:900;" class="{{'n' if 110<=ups.linev<=130 else 'a'}}">{{ups.linev}}V</div>
</div>
</div>
<!-- PQI stoplight (documented color exception: alarm-test-passing composite) -->
<div style="padding-top:11px;">
<div style="display:flex;justify-content:space-between;align-items:baseline;margin-bottom:6px;">
<span style="font-size:var(--font-micro);color:var(--neutral);letter-spacing:.08em;text-transform:uppercase;">Power Quality Index &mdash; SPC composite</span>
</div>
{% if pw.pqi is none %}
<div style="font-size:var(--font-micro);color:var(--neutral);line-height:1.4;">Gathering baseline &mdash; {{pw.n}}/{{pw.min}} RAPL samples (~{{pw.min*4}}s). Score renders once Ppk is stable.</div>
{% else %}
<div style="display:flex;align-items:center;gap:16px;">
<div style="text-align:center;min-width:78px;"><div style="font-size:30px;font-weight:900;line-height:1;" class="{{pw.band}}">{{pw.pqi}}</div><div style="font-size:var(--font-micro);color:var(--neutral);">/ 100 PQI</div></div>
<div style="flex:1;">
<div style="display:flex;justify-content:space-between;padding:2px 0;font-size:var(--font-micro);"><span class=dim>Wattage stability &middot; 40%</span><span class="{{pw.s_watt_band}}" style="font-weight:700;">{{pw.s_watt_txt}}</span></div>
<div style="display:flex;justify-content:space-between;padding:2px 0;font-size:var(--font-micro);"><span class=dim>Excursion rate &middot; 35%</span><span class="{{pw.s_exc_band}}" style="font-weight:700;">{{pw.s_exc_txt}}</span></div>
<div style="display:flex;justify-content:space-between;padding:2px 0;font-size:var(--font-micro);"><span class=dim>Freq jitter &middot; 25%</span><span class="{{pw.s_jit_band}}" style="font-weight:700;">{{pw.s_jit_txt}}</span></div>
</div>
</div>
{% if pw.corr>0 %}<div style="font-size:var(--font-micro);color:var(--amber);margin-top:6px;">&#9888; {{pw.corr}} power excursion(s) correlated with line-voltage sags.</div>{% endif %}
{% endif %}
</div>
</div>

<!-- 4. SERVICES & PERIPHERALS (merged AI Engine + Printer + services rollup) -->
<div class="p {% if not ai.online or not printer.usb or svc_issues %}alarm{% endif %}">
<div class=pt><span>Services &amp; Peripherals</span><a class=det href="/system">Detail</a></div>
<div class=row>
<span class=rl><span class="dot {{'busy' if ai.busy else ('ok' if ai.online else 'bad')}}"></span>Qwen7B :8081{% if ai.models %} &middot; <span class=n>{{ai.models[0].name}}</span>{% endif %}</span>
<span class="rv {{'b' if ai.busy else ('n' if ai.online else 'r')}}">{{ai.state}}{% if ai.busy %} &middot; {{ai.tps}} t/s{% endif %}</span>
</div>
<div class=row>
<span class=rl><span class="dot {{'busy' if ornith.busy else ('ok' if ornith.online else 'bad')}}"></span>Ornith :8082 &middot; <span class=n>{{ornith.model}}</span></span>
<span class="rv {{'b' if ornith.busy else ('n' if ornith.online else 'r')}}">{{ornith.state}}{% if ornith.busy %} &middot; {{ornith.tps}} t/s{% endif %}</span>
</div>
<div class=row>
<span class=rl><span class="dot {{'busy' if gflip.busy else ('ok' if gflip.online else 'bad')}}"></span>gflip 30B :8080{% if gflip.models %} &middot; <span class=n>{{gflip.models[0]}}</span>{% endif %} &middot; <span class="{{'a' if gflip.mode=='CPU' else ('r' if gflip.mode=='DOWN' else 'g')}}">{{gflip.mode}}</span></span>
<span class="rv {{'b' if gflip.busy else ('n' if gflip.online else 'r')}}">{{gflip.state}}{% if gflip.busy %} &middot; {{gflip.tps}} t/s{% endif %}</span>
</div>

<div class=row>
<span class=rl><span class="dot {{'ok' if not svc_issues else 'bad'}}"></span>Services &amp; Containers</span>
<span class="rv {{'n' if not svc_issues else 'r'}}">{% if not svc_issues %}all healthy{% else %}{{svc_issues|length}} need attention{% endif %}</span>
</div>
<div class=row>
<span class=rl><span class="dot {{'ok' if printer.usb else 'bad'}}"></span>Printer USB &middot; {{printer.name or 'Star TSP143IIIU'}}</span>
<span class="rv {{'n' if printer.usb else 'r'}}">{{'CONNECTED' if printer.usb else 'NOT FOUND'}}</span>
</div>
<div class=row>
<span class=rl><span class="dot {{'ok' if printer.state in ['idle','ready','processing'] else ('warn' if not printer.cups else 'bad')}}"></span>Print Queue (CUPS)</span>
<span class="rv {{'n' if printer.state in ['idle','ready','processing'] else ('a' if not printer.cups else 'r')}}">{{printer.state.upper()}}</span>
</div>
</div>

<div class=note>taza-server &middot; Level-1 overview &middot; grey = normal, color = attention &middot; {{ now }}</div>
</body></html>"""

# Diagnostics page shell. Panels are placeholders until inference_perf_log.csv
# accumulates enough data to render Throttle Cause + TPS Distribution charts.
DT="""<!DOCTYPE html><html><head><meta charset=UTF-8>
<title>Taza OS Diagnostics</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Barlow:wght@400;700;900&display=swap');
:root{--bg:#060809;--panel:#0d1117;--green:#00e676;--amber:#ffb300;--red:#ff3333;--blue:#40c4ff;--white:#ffffff;--dim:#a0aec0;
--font-hero:20px;--font-value:15px;--font-label:13px;--font-micro:11px;}
*{box-sizing:border-box;margin:0;padding:0;}
body{background:var(--bg);color:var(--white);font-family:Barlow,sans-serif;padding:5px;}
header{display:flex;justify-content:space-between;align-items:center;border-bottom:2px solid #C9A84C;padding-bottom:6px;margin-bottom:10px;}
.sn{font-size:var(--font-hero);color:var(--white);letter-spacing:.15em;font-weight:700;}
.ts{font-size:var(--font-label);color:var(--white);}
.g2{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:10px;}
.p{background:var(--panel);border:1px solid #1e3a2f;border-radius:6px;padding:5px 8px;}
.pt{font-size:var(--font-label);letter-spacing:.15em;text-transform:uppercase;color:#C9A84C;margin-bottom:4px;padding-bottom:4px;border-bottom:1px solid #1e3a2f;font-weight:700;}
.ph{display:flex;align-items:center;justify-content:center;min-height:220px;color:var(--dim);font-size:var(--font-value);letter-spacing:.05em;border:1px dashed #2a5344;border-radius:4px;background:var(--bg);}
.note{text-align:center;font-size:var(--font-micro);color:var(--white);margin-top:5px;}
.ts a{color:var(--dim);text-decoration:none;font-weight:600;}
.nav{display:flex;gap:8px;flex-wrap:wrap;margin:0 0 14px;}
.nav a{font-size:var(--font-micro);color:var(--dim);text-decoration:none;border:1px solid #2a3340;border-radius:5px;padding:5px 11px;letter-spacing:.05em;}
.nav a.here{color:var(--gold,#C9A84C);border-color:#C9A84C;font-weight:700;}
</style></head><body>
<header>
<div class=sn>TAZA OS &mdash; DIAGNOSTICS</div>
<div class=ts>{{ now }} | <a href="/" style="color:var(--dim);text-decoration:none;font-weight:700;">&larr; Dashboard</a></div>
</header>
<div class=nav><a href="/power">Power</a><a href="/ram">Memory</a><a href="/cost">Cost</a><a href="/system">System</a><a href="/diagnostics" class=here>Diagnostics</a></div>
<div class=g2>
<div class=p>
<div class=pt>Throttle Cause Classifier</div>
<div class=ph>awaiting data</div>
</div>
<div class=p>
<div class=pt>TPS Distribution</div>
<div class=ph>awaiting data</div>
</div>
</div>
<div class=note>taza-server | fed from inference_perf_log.csv | {{ now }}</div>
</body></html>"""

@app.route("/diagnostics")
def diagnostics():
 now=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
 return render_template_string(DT,now=now)

# Power detail page (tap-to-detail target for the PQI / traces / events sections,
# mirroring the /diagnostics <- Dashboard back-link pattern established in Part 1).
PWR="""<!DOCTYPE html><html><head><meta charset=UTF-8>
<meta http-equiv=refresh content=15>
<title>Taza OS Power Detail</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=Barlow:wght@400;700;900&display=swap');
:root{--bg:#060809;--panel:#0d1117;--green:#00e676;--amber:#ffb300;--red:#ff3333;--blue:#40c4ff;--white:#ffffff;--dim:#a0aec0;
--font-hero:20px;--font-value:15px;--font-label:13px;--font-micro:11px;}
*{box-sizing:border-box;margin:0;padding:0;}
body{background:var(--bg);color:var(--white);font-family:Barlow,sans-serif;padding:5px;}
header{display:flex;justify-content:space-between;align-items:center;border-bottom:2px solid #C9A84C;padding-bottom:6px;margin-bottom:10px;}
.sn{font-size:var(--font-hero);color:var(--white);letter-spacing:.12em;font-weight:700;}
.ts{font-size:var(--font-label);}
.p{background:var(--panel);border:1px solid #1e3a2f;border-radius:6px;padding:8px 12px;margin-bottom:12px;}
.pt{font-size:var(--font-label);letter-spacing:.12em;text-transform:uppercase;color:#C9A84C;margin-bottom:6px;padding-bottom:5px;border-bottom:1px solid #1e3a2f;font-weight:700;}
.row{display:flex;justify-content:space-between;padding:3px 0;border-bottom:1px solid #12201a;font-size:var(--font-label);}
.g{color:var(--green);}.a{color:var(--amber);}.r{color:var(--red);}.b{color:var(--blue);}.dim{color:var(--dim);}
.mono{font-family:monospace;}
.note{font-size:var(--font-micro);color:var(--dim);line-height:1.45;margin-top:6px;}
.ts a{color:var(--dim);text-decoration:none;font-weight:600;}
.nav{display:flex;gap:8px;flex-wrap:wrap;margin:0 0 14px;}
.nav a{font-size:var(--font-micro);color:var(--dim);text-decoration:none;border:1px solid #2a3340;border-radius:5px;padding:5px 11px;letter-spacing:.05em;}
.nav a.here{color:var(--gold,#C9A84C);border-color:#C9A84C;font-weight:700;}
</style></head><body>
<header>
<div class=sn>TAZA OS &mdash; POWER DETAIL</div>
<div class=ts><a href="/" style="color:var(--dim);text-decoration:none;font-weight:700;">&larr; Dashboard</a></div>
</header>
<div class=nav><a href="/power" class=here>Power</a><a href="/ram">Memory</a><a href="/cost">Cost</a><a href="/system">System</a><a href="/diagnostics">Diagnostics</a></div>
<div class=p>
<div class=pt>Power Quality Index</div>
{% if pw.pqi is none %}
<div class=dim style="font-size:var(--font-value);">Gathering baseline data &mdash; {{pw.n}}/{{pw.min}} RAPL samples.</div>
{% else %}
<div style="font-size:44px;font-weight:900;line-height:1;" class="{{pw.band}}">{{pw.pqi}}<span style="font-size:var(--font-label);color:var(--dim);"> / 100</span></div>
<div style="margin-top:8px;">
<div class=row><span>Wattage stability (40%) &mdash; sub-score</span><span class="{{pw.s_watt_band}}">{{pw.s_watt_txt}}</span></div>
<div class=row><span class=dim>&nbsp;&nbsp;mean {{pw.mean_w}}W, &sigma; {{pw.sd_w}}W, USL(PL1) {{pw.usl}}W, LSL 0 &rarr; Ppk {{pw.ppk}}</span><span class=dim>1-sided upper Cpu {{pw.cpu_up}}</span></div>
<div class=row><span>Excursion rate (35%) &mdash; sub-score</span><span class="{{pw.s_exc_band}}">{{pw.s_exc_txt}}</span></div>
<div class=row><span class=dim>&nbsp;&nbsp;power reasons (Amps/PkgPwrL1/PkgPwrL2) per uptime-hour</span><span class=dim>{{pw.exc_hr}}/hr</span></div>
<div class=row><span>Freq jitter under load (25%) &mdash; sub-score</span><span class="{{pw.s_jit_band}}">{{pw.s_jit_txt}}</span></div>
<div class=row><span class=dim>&nbsp;&nbsp;CV of Bzy_MHz over Busy%&ge;50 samples ({{pw.load_n}} qualifying)</span><span class=dim>CV {{pw.cv if pw.cv is not none else 'n/a'}}%</span></div>
</div>
{% if pw.weights_note %}<div class=note style="color:var(--amber);">{{pw.weights_note}}</div>{% endif %}
{% if pw.corr>0 %}<div class=note style="color:var(--amber);">&#9888; {{pw.corr}} excursion(s) correlated with UPS line sag &lt;110V within &plusmn;10s.</div>{% endif %}
{% endif %}
<div class=note><b>Ppk LSL=0 caveat:</b> the lower-capability term dominates on an idle low-power box, so a perfectly stable ~0.5W system scores low on the two-sided Ppk as specified. The one-sided upper Cpu (distance to PL1 only) is the semantically-correct power-headroom metric &mdash; both shown above for tuning.</div>
</div>
<div class=p>
<div class=pt>Power Signal Traces &mdash; real RAPL/turbostat</div>
<div style="display:flex;align-items:center;gap:14px;margin-top:4px;">
<div style="min-width:82px;text-align:center;"><div style="font-size:var(--font-hero);font-weight:900;" class=g>{{pw.cur.watt}}<span style="font-size:var(--font-label);">W</span></div><div style="font-size:var(--font-micro);color:var(--dim);">PkgWatt now</div></div>
<div style="flex:1;min-width:0;">{{pw.svg_watt|safe}}<div style="font-size:var(--font-micro);color:var(--dim);margin-top:2px;">RAPL package power &mdash; scale 0..{{pwr.pl2}}W, grid line = PL1 {{pwr.pl1}}W</div></div>
</div>
<div style="display:flex;gap:16px;margin-top:9px;">
<div style="flex:1;min-width:0;"><div style="font-size:var(--font-micro);color:var(--blue);font-weight:700;">Bzy_MHz &mdash; {{pw.cur.mhz}} MHz</div>{{pw.svg_mhz|safe}}</div>
<div style="flex:1;min-width:0;"><div style="font-size:var(--font-micro);color:var(--amber);font-weight:700;">PKG_% throttle-time &mdash; {{pw.cur.pkgpct}}%</div>{{pw.svg_pkg|safe}}</div>
</div>
</div>
<div class=p>
<div class=pt>Static Power Config (MSRs, read once at startup)</div>
<div class=row><span>MSR_PKG_POWER_LIMIT 0x610 &mdash; PL1 (USL) / PL2</span><span class=g>{{pwr.pl1}}W / {{pwr.pl2}}W</span></div>
<div class=row><span>MSR_PKG_POWER_INFO 0x614 &mdash; TDP spec power</span><span class=b>{{pwr.tdp}}W</span></div>
<div class=row><span>MSR_VR_CURRENT_CONFIG 0x601 &mdash; ICCMAX</span><span class=b>{{pwr.icc}}A <span class="mono dim">({{pwr.vr_raw}})</span></span></div>
<div class=row><span>MSR_RAPL_POWER_UNIT 0x606 &mdash; power unit</span><span class=dim>{{pwr.pu}}W/tick</span></div>
</div>
<div class=p>
<div class=pt>Full Event Log ({{pw.events|length}} shown, last 200 retained)</div>
{% if pw.events %}
{% for e in pw.events %}
<div class=row><span>{{e.iso}} &middot; <b class="{{'a' if e.power else 'dim'}}">{{e.name}}</b></span><span class=dim>{{e.meaning}}</span></div>
{% endfor %}
{% else %}
<div class=g style="font-size:var(--font-value);padding:6px 0;">No power-limit events &mdash; MSR 0x64d clear across all cores since start.</div>
{% endif %}
</div>
<div class=note>Real RAPL/turbostat + rdmsr data. Field names confirmed on this N100: PkgWatt, PKG_%, Bzy_MHz, Busy%; limit-reason bits per Intel SDM 0x64d. Refresh 15s.</div>
</body></html>"""

@app.route("/power")
def power_detail():
 now=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
 return render_template_string(PWR,now=now,pw=build_power_view(main=False),pwr=PWR_CFG)

# RAM Bandwidth Health detail (tap-to-detail target; mirrors the /power detail pattern).
RAMT="""<!DOCTYPE html><html><head><meta charset=UTF-8>
<meta http-equiv=refresh content=30>
<title>Taza OS RAM Bandwidth Health</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=Barlow:wght@400;700;900&display=swap');
:root{--bg:#060809;--panel:#0d1117;--green:#00e676;--amber:#ffb300;--red:#ff3333;--blue:#40c4ff;--white:#ffffff;--dim:#a0aec0;
--font-hero:20px;--font-value:15px;--font-label:13px;--font-micro:11px;}
*{box-sizing:border-box;margin:0;padding:0;}
body{background:var(--bg);color:var(--white);font-family:Barlow,sans-serif;padding:5px;}
header{display:flex;justify-content:space-between;align-items:center;border-bottom:2px solid #C9A84C;padding-bottom:6px;margin-bottom:10px;}
.sn{font-size:var(--font-hero);color:var(--white);letter-spacing:.12em;font-weight:700;}
.ts{font-size:var(--font-label);}
.p{background:var(--panel);border:1px solid #1e3a2f;border-radius:6px;padding:8px 12px;margin-bottom:12px;}
.pt{font-size:var(--font-label);letter-spacing:.12em;text-transform:uppercase;color:#C9A84C;margin-bottom:6px;padding-bottom:5px;border-bottom:1px solid #1e3a2f;font-weight:700;}
.row{display:flex;justify-content:space-between;padding:3px 0;border-bottom:1px solid #12201a;font-size:var(--font-label);}
.g{color:var(--green);}.a{color:var(--amber);}.r{color:var(--red);}.b{color:var(--blue);}.dim{color:var(--dim);}
table{width:100%;border-collapse:collapse;font-size:var(--font-micro);}
th,td{text-align:right;padding:4px 6px;border-bottom:1px solid #12201a;}
th{color:#C9A84C;text-transform:uppercase;letter-spacing:.08em;}
th:first-child,td:first-child{text-align:left;}
.note{font-size:var(--font-micro);color:var(--dim);line-height:1.5;margin-top:6px;}
.ts a{color:var(--dim);text-decoration:none;font-weight:600;}
.nav{display:flex;gap:8px;flex-wrap:wrap;margin:0 0 14px;}
.nav a{font-size:var(--font-micro);color:var(--dim);text-decoration:none;border:1px solid #2a3340;border-radius:5px;padding:5px 11px;letter-spacing:.05em;}
.nav a.here{color:var(--gold,#C9A84C);border-color:#C9A84C;font-weight:700;}
</style></head><body>
<header>
<div class=sn>TAZA OS &mdash; MEMORY DETAIL</div>
<div class=ts><a href="/" style="color:var(--dim);text-decoration:none;font-weight:700;">&larr; Dashboard</a></div>
</header>
<div class=nav><a href="/power">Power</a><a href="/ram" class=here>Memory</a><a href="/cost">Cost</a><a href="/system">System</a><a href="/diagnostics">Diagnostics</a></div>
{% if ramcfg.type %}
<div class=p>
<div class=pt>RAM Configuration (Part 4A &mdash; static, from SPD via dmidecode)</div>
<div class=row><span>Size / Type / Form factor</span><span class=b>{{ramcfg.size_gb}}GB {{ramcfg.type}} {{ramcfg.form_factor}}</span></div>
<div class=row><span>Configured speed</span><span class=b>{{ramcfg.configured_mts}} MT/s</span></div>
<div class=row><span>Manufacturer</span><span class=dim>{{ramcfg.manufacturer}}</span></div>
<div class=row><span>Channels populated</span><span class="{{'a' if ramcfg.channels_populated < ramcfg.channels_max else 'g'}}">{{ramcfg.channel_mode}}-channel ({{ramcfg.channels_populated}}/{{ramcfg.channels_max}}){% if ramcfg.configured_equals_max %} &middot; at rated max (no OC margin){% endif %}</span></div>
</div>
{% endif %}
<div class=p>
<div class=pt>RAM Bandwidth Health &mdash; Status</div>
{% if ram.gathering %}
<div class=dim style="font-size:var(--font-value);line-height:1.5;">Gathering baseline &mdash; <b>{{ram.n}} of ~{{ram.target}}</b> benchmark runs collected (need &ge;{{ram.min}} paired points).<br>
Bandwidth points on file (Part 4A): <b>{{ram.bw_pts}}</b>. Computed residual points: <b>{{ram.n}}</b>.
{% if ram.missing %}<br>Blocked on: <span class=a>{{ram.missing|join(' + ')}}</span>.{% endif %}</div>
{% else %}
<div style="display:flex;align-items:center;gap:18px;">
<div style="text-align:center;min-width:120px;"><div style="font-size:38px;font-weight:900;line-height:1;" class="{{ram.band}}">{{ram.band_word}}</div><div class=dim style="font-size:var(--font-micro);margin-top:3px;">{{ram.n}} runs</div></div>
<div style="flex:1;">
<div class=row><span>Efficiency-ratio slope (per run)</span><span class="{{ram.band}}">{{ram.slope}}</span></div>
<div class=row><span class=dim>&nbsp;&nbsp;stable band &plusmn;{{ram.stable_band}}; &le;&minus;band=degrading, &ge;+band=improving</span><span class=dim>mean eff {{ram.eff_mean}}</span></div>
<div class=row><span>Latest measured bandwidth</span><span class=b>{{ram.cur.meas_bw}} GB/s</span></div>
<div class=row><span>Latest implied-by-throughput bandwidth</span><span>{{ram.cur.impl_bw}} GB/s</span></div>
</div>
</div>
{% endif %}
</div>
<div class=p>
<div class=pt>Residual History ({{ram.rows|length}} points)</div>
{% if ram.rows %}
<table>
<tr><th>Timestamp</th><th>Model</th><th>Quant</th><th>Act B</th><th>Meas GB/s</th><th>Impl GB/s</th><th>Actual t/s</th><th>Pred t/s</th><th>Resid</th><th>Eff</th><th>Src</th></tr>
{% for r in ram.rows %}
<tr><td>{{r.ts.strftime('%Y-%m-%d %H:%M')}}</td><td>{{r.model}}</td><td>{{r.quant}}</td><td>{{r.active_b}}</td><td>{{r.meas_bw}}</td><td>{{r.impl_bw}}</td><td>{{r.actual_tps}}</td><td>{{r.pred_tps}}</td><td class="{{'r' if r.resid<0 else 'g'}}">{{r.resid}}</td><td>{{r.eff}}</td><td class=dim>{{r.source}}</td></tr>
{% endfor %}
</table>
{% else %}
<div class=dim style="font-size:var(--font-value);padding:6px 0;">No residual points yet &mdash; awaiting paired bandwidth + inference-benchmark data.</div>
{% endif %}
</div>
<div class=p>
<div class=pt>Model &amp; Formula (tunable by Nick)</div>
<div class=row><span>predicted_tps</span><span class=dim>bandwidth_GBps &#247; (active_params_B &times; bytes_per_param)</span></div>
<div class=row><span>bytes/param Q4_K_M / Q5_K_M / Q6_K / Q8_0</span><span class=dim>0.5625 / 0.6875 / 0.8125 / 1.0</span></div>
<div class=row><span>active params &mdash; Ornith (Qwen3.5-35B-A3B MoE)</span><span class=b>3.0B active (not 35B total)</span></div>
<div class=row><span>active params &mdash; dense 1.5B / 7B / 14B</span><span class=dim>1.5 / 7 / 14 B</span></div>
<div class=row><span>min points to score / target</span><span class=dim>{{ram.min}} / {{ram.target}}</span></div>
<div class=row><span>efficiency-ratio stable band</span><span class=dim>&plusmn;{{ram.stable_band}} slope/run</span></div>
<div class=note><b>Why efficiency-ratio drift, not raw residual:</b> real inference never reaches the bandwidth roofline (compute/attention/KV/sampling overhead), so actual&nbsp;&lt;&nbsp;predicted <i>always</i> &mdash; the residual is dominated by a ~constant efficiency factor (~0.4-0.7). A one-off negative residual is NORMAL, not degradation. What flags a failing memory subsystem is the efficiency ratio <i>drifting down over repeated runs</i> at fixed model/quant. Mirrors Part 3B's Ppk-LSL caveat: report the semantically-correct trend, not the misleading absolute.</div>
</div>
<div class=note>Data contract &mdash; bandwidth: ram-bandwidth-log.csv (Part 4A) &middot; benchmarks: inference-benchmark-log.csv + harvested inference_perf_log.csv &middot; residuals: ram-bandwidth-residual-log.csv. Refresh 30s.</div>
</body></html>"""

@app.route("/ram")
def ram_detail():
 now=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
 return render_template_string(RAMT,now=now,ram=build_ram_health(),ramcfg=get_ram_cfg())

# Total System Cost detail (tap-to-detail target): the full "money story" — cumulative
# cost/savings trace + per-model inference-economics breakdown — collected behind one tap.
COST="""<!DOCTYPE html><html><head><meta charset=UTF-8>
<meta http-equiv=refresh content=30>
<title>Taza OS Cost Detail</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=Barlow:wght@400;700;900&display=swap');
:root{--bg:#060809;--panel:#0d1117;--green:#00e676;--amber:#ffb300;--red:#ff3333;--blue:#40c4ff;--white:#ffffff;--dim:#a0aec0;
--font-hero:20px;--font-value:15px;--font-label:13px;--font-micro:11px;}
*{box-sizing:border-box;margin:0;padding:0;}
body{background:var(--bg);color:var(--white);font-family:Barlow,sans-serif;padding:5px;}
header{display:flex;justify-content:space-between;align-items:center;border-bottom:2px solid #C9A84C;padding-bottom:6px;margin-bottom:10px;}
.sn{font-size:var(--font-hero);color:var(--white);letter-spacing:.12em;font-weight:700;}
.ts{font-size:var(--font-label);}
.p{background:var(--panel);border:1px solid #1e3a2f;border-radius:6px;padding:8px 12px;margin-bottom:12px;}
.pt{font-size:var(--font-label);letter-spacing:.12em;text-transform:uppercase;color:#C9A84C;margin-bottom:6px;padding-bottom:5px;border-bottom:1px solid #1e3a2f;font-weight:700;}
.g{color:var(--green);}.a{color:var(--amber);}.b{color:var(--blue);}.dim{color:var(--dim);}
.dh{display:grid;grid-template-columns:repeat(3,1fr);gap:6px;margin-top:5px;}
.dhc{text-align:center;padding:5px;background:var(--bg);border-radius:4px;border:1px solid #1e3a2f;}
.dhn{font-size:var(--font-value);font-weight:700;}
.dhl{font-size:var(--font-micro);color:var(--white);margin-top:2px;text-transform:uppercase;}
.note{text-align:left;font-size:var(--font-micro);color:var(--dim);margin-top:6px;line-height:1.4;}
.ts a{color:var(--dim);text-decoration:none;font-weight:600;}
.nav{display:flex;gap:8px;flex-wrap:wrap;margin:0 0 14px;}
.nav a{font-size:var(--font-micro);color:var(--dim);text-decoration:none;border:1px solid #2a3340;border-radius:5px;padding:5px 11px;letter-spacing:.05em;}
.nav a.here{color:var(--gold,#C9A84C);border-color:#C9A84C;font-weight:700;}
</style></head><body>
<header>
<div class=sn>TAZA OS &mdash; COST DETAIL</div>
<div class=ts><a href="/" style="color:var(--dim);text-decoration:none;font-weight:700;">&larr; Dashboard</a></div>
</header>
<div class=nav><a href="/power">Power</a><a href="/ram">Memory</a><a href="/cost" class=here>Cost</a><a href="/system">System</a><a href="/diagnostics">Diagnostics</a></div>
<div class=p>
<div class=pt>Total System Cost &mdash; cumulative</div>
<div style="display:flex;justify-content:space-between;font-size:var(--font-micro);margin-bottom:3px;">
<span style="color:var(--amber);">&#9632; Cost &mdash; capital $646.87 + ~$97/mo</span>
<span style="color:var(--green);">&#9632; Savings &mdash; local inference</span>
</div>
{{econ.overlay|safe}}
<div class=dh>
<div class=dhc><div class=dhn style="color:var(--amber);">${{ "%.0f"|format(econ.cost_end) }}</div><div class=dhl>Cost @ {{econ.months[-1]}}</div></div>
<div class=dhc><div class=dhn style="color:var(--green);">${{ "%.0f"|format(econ.save_end) }}</div><div class=dhl>Savings @ {{econ.months[-1]}}</div></div>
<div class=dhc><div class=dhn style="color:var(--blue);">{{econ.be.m if econ.be else 'not yet'}}</div><div class=dhl>Breakeven</div></div>
</div>
<div class=note style="color:var(--amber);">Capital spent to date $646.87 &middot; recurring ~$97/mo (Pro Max 85 + power ~11 + domains ~1). Pending WAP/PoE cam excluded until purchased. Inherited gear (printer, MTs, z33, TVs, tablets, OnePlus 7T) amortized at $0. Savings side is SAMPLE-seeded.</div>
<div class=note>Development labor not tracked &mdash; owner-built.</div>
</div>
<div class=p>
<div class=pt>Inference Economics &mdash; per-model breakdown</div>
{% for t in econ.tiers %}
<div style="margin-bottom:8px;">
<div style="display:flex;justify-content:space-between;align-items:baseline;margin-bottom:1px;">
<span style="font-size:var(--font-label);font-weight:700;color:var(--white);">{{t.name}}</span>
<span style="font-size:var(--font-micro);"><span style="color:{{t.lc}};">&#9632; {{t.lname}}</span>&nbsp;&nbsp;<span style="color:{{t.rc}};">&#9632; {{t.rname}}</span></span>
</div>
{{t.svg|safe}}
</div>
{% endfor %}
<div class=note style="color:var(--amber);">SAMPLE DATA &mdash; no real per-model token history yet (inference_perf_log.csv has 0 populated tps rows). Local savings = counterfactual Sonnet cost ($3/M in + $15/M out, ~$9/M blend). Wiring real token accounting is a follow-up.</div>
</div>
<div class=note style="text-align:center;">Refresh 30s.</div>
</body></html>"""

@app.route("/cost")
def cost_detail():
 now=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
 return render_template_string(COST,now=now,econ=build_econ())

# General "System" detail (tap-to-detail target): the non-critical supporting data pulled
# off the main screen — uptime/load, full service list, per-core CPU workload, CPU
# efficiency, lifetime thermal history, UPS transfer detail, and the AI personality line.
SYS="""<!DOCTYPE html><html><head><meta charset=UTF-8>
<meta http-equiv=refresh content=15>
<title>Taza OS System Detail</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=Barlow:wght@400;700;900&display=swap');
:root{--bg:#060809;--panel:#0d1117;--green:#00e676;--amber:#ffb300;--red:#ff3333;--blue:#40c4ff;--white:#ffffff;--dim:#a0aec0;
--font-hero:20px;--font-value:15px;--font-label:13px;--font-micro:11px;}
*{box-sizing:border-box;margin:0;padding:0;}
body{background:var(--bg);color:var(--white);font-family:Barlow,sans-serif;padding:5px;}
header{display:flex;justify-content:space-between;align-items:center;border-bottom:2px solid #C9A84C;padding-bottom:6px;margin-bottom:10px;}
.sn{font-size:var(--font-hero);color:var(--white);letter-spacing:.12em;font-weight:700;}
.ts{font-size:var(--font-label);}
.p{background:var(--panel);border:1px solid #1e3a2f;border-radius:6px;padding:8px 12px;margin-bottom:12px;}
.pt{font-size:var(--font-label);letter-spacing:.12em;text-transform:uppercase;color:#C9A84C;margin-bottom:6px;padding-bottom:5px;border-bottom:1px solid #1e3a2f;font-weight:700;}
.row{display:flex;justify-content:space-between;align-items:center;padding:3px 0;border-bottom:1px solid #12201a;font-size:var(--font-label);}
.rl{color:var(--white);}.rv{font-weight:700;font-size:var(--font-value);}
.big{font-size:var(--font-hero);font-weight:900;line-height:1;}
.sub{font-size:var(--font-label);color:var(--dim);margin:2px 0 4px;}
.g{color:var(--green);}.a{color:var(--amber);}.r{color:var(--red);}.b{color:var(--blue);}.w{color:var(--white);}
.dot{display:inline-block;width:14px;height:14px;border-radius:50%;margin-right:7px;vertical-align:middle;}
.fg{background:var(--green);}.fa{background:var(--amber);}.fr{background:var(--red);}
.dh{display:grid;grid-template-columns:repeat(4,1fr);gap:6px;margin-top:5px;}
.dhc{text-align:center;padding:5px;background:var(--bg);border-radius:4px;border:1px solid #1e3a2f;}
.dhn{font-size:var(--font-value);font-weight:700;color:var(--blue);}
.dhl{font-size:var(--font-micro);color:var(--white);margin-top:2px;text-transform:uppercase;}
.note{font-size:var(--font-micro);color:var(--dim);line-height:1.4;margin-top:5px;}
.ai-q{font-size:var(--font-micro);color:var(--amber);font-style:italic;margin-top:6px;opacity:.8;}
.ts a{color:var(--dim);text-decoration:none;font-weight:600;}
.nav{display:flex;gap:8px;flex-wrap:wrap;margin:0 0 14px;}
.nav a{font-size:var(--font-micro);color:var(--dim);text-decoration:none;border:1px solid #2a3340;border-radius:5px;padding:5px 11px;letter-spacing:.05em;}
.nav a.here{color:var(--gold,#C9A84C);border-color:#C9A84C;font-weight:700;}
</style></head><body>
<header>
<div class=sn>TAZA OS &mdash; SYSTEM DETAIL</div>
<div class=ts><a href="/" style="color:var(--dim);text-decoration:none;font-weight:700;">&larr; Dashboard</a></div>
</header>
<div class=nav><a href="/power">Power</a><a href="/ram">Memory</a><a href="/cost">Cost</a><a href="/system" class=here>System</a><a href="/diagnostics">Diagnostics</a></div>
<div class=p>
<div class=pt>Uptime &amp; Load</div>
<div class="big b">{{up.days}}d {{up.hours}}h {{up.mins}}m</div>
<div class=sub>Continuous runtime</div>
<div class="row"><span class=rl>Load 1m</span><span class="rv {{("r" if load.m1>4 else("a" if load.m1>2 else "g"))}}">{{load.m1}}</span></div>
<div class=row><span class=rl>Load 5m</span><span class="rv w">{{load.m5}}</span></div>
<div class=row><span class=rl>Load 15m</span><span class="rv w">{{load.m15}}</span></div>
</div>
<div class=p>
<div class=pt>Memory &amp; Storage <span style="font-weight:600;letter-spacing:.04em;font-size:var(--font-micro);color:var(--dim);">(demoted from L1 &mdash; status, not alarm)</span></div>
<div class=row><span class=rl>RAM</span><span class="rv {{'r' if mem.pct>=85 else ('a' if mem.pct>=60 else 'w')}}">{{mem.used}} / {{mem.total}} GB &middot; {{mem.pct}}%</span></div>
<div class=row><span class=rl>Disk</span><span class="rv {{'r' if disk.pct>=80 else ('a' if disk.pct>=70 else 'w')}}">{{disk.used}} / {{disk.total}} GB &middot; {{disk.pct}}%</span></div>
{% if ramcfg.type %}<div class=row><span class=rl>Configuration</span><span class="rv b">{{ramcfg.size_gb}}GB {{ramcfg.type}} &middot; {{ramcfg.configured_mts}} MT/s</span></div>{% endif %}
<div class=note>Escalates to the L1 status banner only when RAM&ge;85% or Disk&ge;80%. Bandwidth-health trend &amp; residual model &rarr; <a href="/ram" style="color:var(--dim);">Memory detail</a>.</div>
</div>
<div class=p>
<div class=pt>Services &amp; Containers</div>
{% for n,s in svcs.items() %}
<div class="row"><span class=rl><span class="dot {{"fg" if s=="active" else "fr"}}"></span>{{n}}</span><span class="rv {{"g" if s=="active" else "r"}}">{{s}}</span></div>
{% endfor %}
{% for c in docker %}
<div class="row"><span class=rl><span class="dot {{"fg" if c.up else "fr"}}"></span>{{c.name}}</span><span class="rv {{"g" if c.up else "r"}}" style="font-size:var(--font-micro);">{{c.status[:16]}}</span></div>
{% endfor %}
<div class=row><span class=rl><span class="dot {{"fg" if nocodb=="online" else "fa"}}"></span>NocoDB</span><span class="rv {{"g" if nocodb=="online" else "a"}}">{{nocodb}}</span></div>
</div>
<div class=p>
<div class=pt>CPU Workload &mdash; per core</div>
{% for w in work %}
<div style="display:flex;align-items:center;gap:9px;margin:4px 0;">
<span style="font-size:var(--font-label);width:52px;color:{{w.color}};font-weight:700;">Core {{w.i}}</span>
<div style="flex:1;height:11px;background:#1a2a1a;border-radius:3px;overflow:hidden;"><div style="height:100%;width:{{w.pct}}%;background:{{w.color}};"></div></div>
<span style="line-height:0;">{{w.spark|safe}}</span>
<span style="font-size:var(--font-value);font-weight:700;width:46px;text-align:right;">{{w.pct}}%</span>
</div>
{% endfor %}
</div>
<div class=p>
<div class=pt>CPU Efficiency &mdash; tokens / watt</div>
<div style="display:flex;align-items:center;gap:14px;">
<div style="min-width:120px;"><span style="font-size:var(--font-hero);font-weight:900;" class=g>{{cur.eff}}</span> <span style="font-size:var(--font-label);color:var(--dim);">tok/W</span><div style="font-size:var(--font-micro);color:var(--dim);">~{{cur.watts}}W est &middot; {{cur.ptps}} tok/s</div></div>
<div style="flex:1;">{{eff_spark|safe}}</div>
</div>
<div class=note style="color:var(--amber);">PLACEHOLDER &mdash; tokens are a load-based proxy &amp; watts estimated (no intel-rapl on this N100). Wiring real token counts + measured power is a follow-up task.</div>
</div>
<div class=p>
<div class=pt>Thermal History (C-Minutes)</div>
<div class=dh>
<div class=dhc><div class=dhn>{{"{:,.0f}".format(dm.dm)}}</div><div class=dhl>Lifetime C-min</div></div>
<div class=dhc><div class=dhn>{{dm.avg}}C</div><div class=dhl>Avg Temp</div></div>
<div class=dhc><div class=dhn>{{dm.mx}}C</div><div class=dhl>Peak</div></div>
<div class=dhc><div class=dhn>{{dm.days}}d/{{dm.n}}</div><div class=dhl>Days/Readings</div></div>
</div>
</div>
<div class=p>
<div class=pt>UPS &mdash; Transfer &amp; Voltage Detail</div>
<div class=dh style="grid-template-columns:repeat(2,1fr);">
<div class=dhc><div class=dhn>{{ups.lmin}} / {{ups.lmax}}V</div><div class=dhl>Line Min / Max</div></div>
<div class=dhc><div class=dhn style="color:{{'var(--green)' if ups.numxfers=='0' else 'var(--amber)'}}">{{ups.numxfers}}</div><div class=dhl>Transfers to Battery</div></div>
</div>
<div class=row style="margin-top:6px;"><span class=rl>Last Transfer</span><span class="rv w">{{ups.lastxfer}}</span></div>
</div>
<div class=p>
<div class=pt>AI Engines &mdash; Loaded Models</div>
{% if ai.models %}
{% for m in ai.models %}
<div class=row><span class=rl><span class="dot {{"fa" if m.state=="ACTIVE" else "fg"}}"></span>{{m.name}} <span style="font-size:var(--font-micro);color:var(--dim);">:8081</span></span><span class="rv {{"a" if m.state=="ACTIVE" else "g"}}">{{m.state}}{% if ai.busy %} &middot; {{ai.tps}} t/s{% endif %}</span></div>
{% endfor %}
{% else %}
<div class=row><span class=rl>:8081 Qwen7B</span><span class="rv r">{{ai.state}}</span></div>
{% endif %}
<div class=row><span class=rl><span class="dot {{"fa" if ornith.busy else ("fg" if ornith.online else "fr")}}"></span>{{ornith.model}} <span style="font-size:var(--font-micro);color:var(--dim);">:8082</span></span><span class="rv {{"a" if ornith.busy else ("g" if ornith.online else "r")}}">{{ornith.state}}{% if ornith.busy %} &middot; {{ornith.tps}} t/s{% endif %}</span></div>
<div class=row><span class=rl><span class="dot {{'busy' if gflip.busy else ('ok' if gflip.online else 'bad')}}"></span>gflip 30B <span style="font-size:var(--font-micro);color:var(--dim);">:8080</span> &middot; <span class="{{'a' if gflip.mode=='CPU' else ('r' if gflip.mode=='DOWN' else 'g')}}">{{gflip.mode}}</span></span><span class="rv {{'b' if gflip.busy else ('n' if gflip.online else 'r')}}">{{gflip.state}}{% if gflip.busy %} &middot; {{gflip.tps}} t/s{% endif %}</span></div>
<div class=ai-q>&ldquo;What should I do now, Boss?&rdquo;</div>
</div>
<div class=note style="text-align:center;">Refresh 15s.</div>
</body></html>"""

@app.route("/system")
def system_detail():
 now=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
 up=get_uptime();load=get_load();docker=get_docker();ai=get_ai();ornith=get_ornith();gflip=get_gflip();nocodb=get_nocodb();dm=get_dm();ups=get_ups()
 mem=get_mem();disk=get_disk();ramcfg=get_ram_cfg()
 svcs={"llama-server":svc("llama-server"),"postgresql":svc("postgresql"),"docker":svc("docker")}
 mv=build_metrics_view()
 return render_template_string(SYS,now=now,up=up,load=load,docker=docker,ai=ai,ornith=ornith,gflip=gflip,nocodb=nocodb,dm=dm,ups=ups,
  mem=mem,disk=disk,ramcfg=ramcfg,svcs=svcs,work=mv["work"],cur=mv["cur"],eff_spark=mv["eff_spark"])

_lt=0
@app.route("/")
def index():
 global _lt
 temps=get_temps();mem=get_mem();disk=get_disk();ramcfg=get_ram_cfg()
 up=get_uptime();load=get_load()
 docker=get_docker();ai=get_ai();ornith=get_ornith();gflip=get_gflip()
 nocodb=get_nocodb();mhz=get_mhz()
 devices=get_devices()
 dm=get_dm();ups=get_ups();printer=get_printer()
 svcs={"llama-server":svc("llama-server"),"postgresql":svc("postgresql"),"docker":svc("docker")}
 now=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
 # Services rollup for the condensed main-screen health line (full list lives on /system).
 svc_issues=[n for n,s in svcs.items() if s!="active"]+[c["name"] for c in docker if not c["up"]]
 if nocodb!="online":svc_issues.append("NocoDB")
 if time.time()-_lt>=300:log_health(temps,mem,disk,load,svcs);_lt=time.time()
 mv=build_metrics_view()  # PART 1: SVG traces + per-core view from rolling buffers
 econ=build_econ()        # PART 2: inference economics + total system cost
 pw=build_power_view()    # PART 3A/3B: real RAPL power signals + PQI composite
 ram=build_ram_health()   # PART 4B: RAM bandwidth health via inference-throughput residual
 return render_template_string(T,temps=temps,mem=mem,disk=disk,ramcfg=ramcfg,up=up,load=load,gflip=gflip,
  docker=docker,ai=ai,ornith=ornith,nocodb=nocodb,mhz=mhz,devices=devices,dm=dm,ups=ups,printer=printer,svcs=svcs,now=now,
  thermal_svg=mv["thermal_svg"],work=mv["work"],cur=mv["cur"],throttled=mv["throttled"],eff_spark=mv["eff_spark"],econ=econ,
  pw=pw,pwr=PWR_CFG,ram=ram,svc_issues=svc_issues,ups_spark=ups_volt_spark())
if __name__=="__main__":
 print("Taza OS Dashboard V2 on :9000")
 app.run(host="0.0.0.0",port=9000,debug=False)
