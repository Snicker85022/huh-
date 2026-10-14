"""Metrology core: SAM mask -> tight ROI -> classical CV line extraction.

Per the architecture: run SAM ONCE per camera pose to isolate the NSF poles,
then crop and run Hough/Canny ONLY inside the ROI for fast, precise line math.
"""
import cv2, numpy as np, time, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def encode_sam(image_bgr, checkpoint='/home/taza/vision-stack/models/sam_vit_b.pth'):
    from segment_anything import sam_model_registry, SamPredictor
    sam = sam_model_registry['vit_b'](checkpoint=checkpoint)
    sam.to('cpu')
    pred = SamPredictor(sam)
    rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
    pred.set_image(rgb)
    return pred

def pole_masks(predictor, points, img_shape):
    """Segment pole at each point; returns tight bboxes."""
    rois=[]
    for (x,y) in points:
        pt = np.array([[x,y]])
        masks, scores, _ = predictor.predict(point_coords=pt, point_labels=np.array([1]), multimask_output=False)
        m = masks[0]
        ys,xs = np.where(m)
        if len(xs)==0: continue
        x0,x1,y0,y1 = int(xs.min()), int(xs.max()), int(ys.min()), int(ys.max())
        if (x1-x0)<200 and (y1-y0)>80:
            rois.append((x0,y0,x1,y1, float(scores[0])))
    return rois

def horizontal_line_spacing(gray_roi, min_len=12, thresh=20):
    """Extract near-horizontal line y-positions inside a ROI and return clustered gaps."""
    edges = cv2.Canny(gray_roi, 25, 80)
    lines = cv2.HoughLinesP(edges, 1, np.pi/180, threshold=thresh, minLineLength=min_len, maxLineGap=8)
    if lines is None: return None, 0
    arr = np.array(lines).reshape(-1,4)
    ys=[]
    for x1,y1,x2,y2 in arr:
        ang = abs(np.degrees(np.arctan2(y2-y1, x2-x1)))
        if ang<25 or ang>155:
            if abs(x2-x1)>min_len:
                ys.append((y1+y2)/2)
    ys.sort()
    if len(ys)<3: return ys, 0
    clusters=[]
    for y in ys:
        for c in clusters:
            if abs(c['y']-y)<6:
                c['y']=(c['y']*c['n']+y)/(c['n']+1); c['n']+=1; break
        else:
            clusters.append({'y':y,'n':1})
    ys_c = sorted(c['y'] for c in clusters)
    gaps=[ys_c[i+1]-ys_c[i] for i in range(len(ys_c)-1)]
    gaps=[g for g in gaps if 6<g<250]
    if not gaps: return ys_c, 0
    return ys_c, float(np.median(gaps))

def run(frame_path, points):
    img = cv2.imread(frame_path)
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    t0=time.time()
    pred = encode_sam(img)
    print(f'SAM encoded in {time.time()-t0:.1f}s')
    rois = pole_masks(pred, points, img.shape)
    print(f'pole ROIs: {len(rois)}')
    results=[]
    for i,(x0,y0,x1,y1,score) in enumerate(rois):
        roi = g[y0:y1, x0:x1]
        ys, spacing = horizontal_line_spacing(roi)
        results.append({'roi':(x0,y0,x1,y1),'score':score,'n_lines':len(ys) if ys else 0,'median_spacing_px':spacing,'lines_y':[round(y+y0) for y in (ys or [])]})
        print(f'ROI{i}: x={x0}..{x1} y={y0}..{y1} score={score:.2f} lines={len(ys) if ys else 0} median_gap={spacing:.1f}px')
    return results

if __name__=='__main__':
    # pole center points (from specular bands; adjust with user confirmation)
    pts = [(402, 380), (456, 380)]
    run('/tmp/junction_poles.jpg', pts)
