"""AI-DSP: register + fuse the multi-modal PTZ captures (visible/IR x exposure x sharpness)
into a single edge-enhanced result, and quantify the gain.  No external AI needed for the
core fusion; optional LLM commentary at the end.
"""
import cv2, os, json, glob, numpy as np
DOE=os.path.join(os.path.dirname(os.path.abspath(__file__)),'captures','doe')
OUT=os.path.join(os.path.dirname(os.path.abspath(__file__)),'captures','fused'); os.makedirs(OUT,exist_ok=True)
files=sorted(glob.glob(os.path.join(DOE,'*.jpg')))
if not files: print("no DOE frames"); raise SystemExit
imgs=[cv2.imread(f) for f in files]
H,W=imgs[0].shape[:2]
ref=cv2.cvtColor(imgs[0],cv2.COLOR_BGR2GRAY).astype(np.float32)
def align(im):
    g=cv2.cvtColor(im,cv2.COLOR_BGR2GRAY).astype(np.float32)
    warp=np.eye(2,3,dtype=np.float32)
    try:
        cc,warp=cv2.findTransformECC(ref,g,warp,cv2.MOTION_TRANSLATION,
              (cv2.TERM_CRITERIA_EPS|cv2.TERM_CRITERIA_COUNT,60,1e-5),None,3)
    except Exception: pass
    return cv2.warpAffine(im,warp,(W,H),flags=cv2.INTER_LINEAR|cv2.WARP_INVERSE_MAP), cc
def grads(im):
    g=cv2.GaussianBlur(cv2.cvtColor(im,cv2.COLOR_BGR2GRAY),(3,3),0)
    gx=cv2.Sobel(g,cv2.CV_32F,1,0,ksize=3); gy=cv2.Sobel(g,cv2.CV_32F,0,1,ksize=3)
    return gx,gy,cv2.magnitude(gx,gy)
def edgepct(m): return float((cv2.Canny((m/np.percentile(m,99.5)*255).clip(0,255).astype(np.uint8),40,120)>0).mean()*100)
aligned=[]; mags=[]; lumas=[]
for im in imgs:
    a,cc=align(im); aligned.append(a)
    _,_,m=grads(a); mags.append(m); lumas.append(cv2.cvtColor(a,cv2.COLOR_BGR2GRAY).astype(np.float32))
# ---- fusion 1: gradient max (illumination-invariant edges) ----
mag_stack=np.stack(mags,0)
mag_max=mag_stack.max(0)
mag_rms=np.sqrt((mag_stack**2).mean(0))
# ---- fusion 2: Laplacian-pyramid luminance fusion (contrast saliency) ----
def lap_fuse(lums):
    levels=4; pyr=[]; 
    for L in lums:
        g=L.copy(); gp=[]
        for _ in range(levels): gp.append(cv2.pyrDown(g)); g=gp[-1]
        pyr.append(gp)
    out=pyr[0][-1]
    for lvl in range(levels-1,-1,-1):
        acc=np.zeros_like(pyr[0][lvl])
        for p in pyr:
            acc+=cv2.pyrUp(p[lvl+1],dstsize=(p[lvl].shape[1],p[lvl].shape[0])) if lvl+1<levels else p[lvl]
        out=acc/len(pyr)
    return out
try:
    luma_fused=lap_fuse(lumas)
except Exception as e:
    luma_fused=np.mean(lumas,0); print("pyramid fuse fallback:",e)
luma_fused=cv2.resize(luma_fused,(W,H)); luma_fused=cv2.normalize(luma_fused,None,0,255,cv2.NORM_MINMAX).astype(np.uint8)
edge_fused=cv2.normalize(mag_max,None,0,255,cv2.NORM_MINMAX).astype(np.uint8)
# ---- report ----
report={'frames':len(files),'per_frame_edge%':[round(edgepct(m),2) for m in mags],
        'fused_max_edge%':round(edgepct(mag_max),2),'fused_rms_edge%':round(edgepct(mag_rms),2)}
best_single=max(report['per_frame_edge%'])
report['gain_vs_best_single_%']=round(report['fused_max_edge%']-best_single,2)
cv2.imwrite(os.path.join(OUT,'fused_edges.png'), edge_fused)
cv2.imwrite(os.path.join(OUT,'fused_luma.png'), luma_fused)
over=cv2.addWeighted(cv2.cvtColor(luma_fused,cv2.COLOR_GRAY2BGR),0.6,
                     cv2.cvtColor(edge_fused,cv2.COLOR_GRAY2BGR),0.6,0)
cv2.imwrite(os.path.join(OUT,'fused_overlay.png'), over)
json.dump(report, open(os.path.join(OUT,'report.json'),'w'), indent=2)
print(json.dumps(report, indent=2))
print("saved:", OUT)
