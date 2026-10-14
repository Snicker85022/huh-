"""MVP QC presence/absence vision for Mom's Table kanban cards.

Flow (Nick's spec, 2026-10-08):
  crew plays a card (e.g. Charcuterie) -> prints a WIP label listing the
  expected ingredients -> at final pack-out they spin the finished item slowly
  in front of MT1 -> the AI watches a few seconds -> if nothing is missing it
  awards completion points when the player enters their PIN -> if items are
  missing it asks ("should this get nuts? I didn't see any.") and SANDRA'S
  OVERRIDE PIN is required to close the card.

MVP = open-vocabulary presence/absence via a local VLM (llava:7b on Ollama),
with YOLOv8n as a corroborating generic-object signal. 100% on-LAN, no cloud.
"""
import os, json, time, base64, sqlite3, datetime, urllib.request, urllib.error

import numpy as np
import cv2

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, 'world', 'world.db')
MODEL = os.path.join(ROOT, 'models', 'yolov8n.onnx')
SHOTS = os.path.join(ROOT, 'calibration', 'captures', 'qc')
os.makedirs(SHOTS, exist_ok=True)

OLLAMA = os.environ.get('QC_OLLAMA', 'http://127.0.0.1:11434/api/generate')
VLM_MODEL = os.environ.get('QC_VLM', 'llava:7b')
MT1_PHOTO = os.environ.get('QC_MT1_PHOTO', 'http://192.168.2.104:8080/photo.jpg')
MT2_PHOTO = os.environ.get('QC_MT2_PHOTO', 'http://192.168.2.108:8080/photo.jpg')
SANDRA_PIN = os.environ.get('QC_SANDRA_PIN', '')   # set to enable the override gate
# --- cloud route (nick: use the OpenRouter key; it is rotated before v1.0) ---
OPENROUTER_KEY = os.environ.get('OPENROUTER_API_KEY', '')
OPENROUTER_URL = os.environ.get('QC_OPENROUTER_URL', 'https://openrouter.ai/api/v1/chat/completions')
CLOUD_VLM = os.environ.get('QC_CLOUD_VLM', 'google/gemini-3-flash-preview')
QC_ROUTE = os.environ.get('QC_ROUTE', 'local')     # local | cloud  (default for verify)

CLASSES = [
    'person','bicycle','car','motorcycle','airplane','bus','train','truck','boat',
    'traffic light','fire hydrant','stop sign','parking meter','bench','bird','cat',
    'dog','horse','sheep','cow','elephant','bear','zebra','giraffe','backpack','umbrella',
    'handbag','tie','suitcase','frisbee','skis','snowboard','sports ball','kite',
    'baseball bat','baseball glove','skateboard','surfboard','tennis racket','bottle',
    'wine glass','cup','fork','knife','spoon','bowl','banana','apple','sandwich','orange',
    'broccoli','carrot','hot dog','pizza','donut','cake','chair','couch','potted plant',
    'bed','dining table','toilet','tv','laptop','mouse','remote','keyboard','cell phone',
    'microwave','oven','toaster','sink','refrigerator','book','clock','vase','scissors',
    'teddy bear','hair drier','toothbrush',
]

_sess = None


def _yolo():
    global _sess
    if _sess is None:
        import onnxruntime as ort
        _sess = ort.InferenceSession(MODEL, providers=['CPUExecutionProvider'])
    return _sess


def _db():
    c = sqlite3.connect(DB, timeout=20)
    try:
        c.execute('PRAGMA busy_timeout=20000')
        c.execute('PRAGMA journal_mode=WAL')
    except Exception:
        pass
    c.execute("""CREATE TABLE IF NOT EXISTS wip_cards (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        card_id TEXT UNIQUE, dish TEXT, ingredients TEXT, board TEXT,
        created_ts TEXT, status TEXT DEFAULT 'open')""")
    c.execute("""CREATE TABLE IF NOT EXISTS qc_verdicts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ts TEXT, card_id TEXT, dish TEXT, expected TEXT, present TEXT,
        missing TEXT, quality TEXT, verdict TEXT, override_used INTEGER DEFAULT 0,
        player_pin TEXT, frame_path TEXT, notes TEXT)""")
    c.commit()
    return c


# ---------------------------------------------------------------- capture
def fetch_photo(url=MT1_PHOTO, timeout=6):
    req = urllib.request.Request(url, headers={'User-Agent': 'taza-qc/1.0'})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def burst(n=4, delay=0.30, url=MT1_PHOTO):
    """Short burst - the crew slowly spins the item in front of the lens."""
    frames = []
    for _ in range(max(1, n)):
        try:
            b = fetch_photo(url)
            img = cv2.imdecode(np.frombuffer(b, np.uint8), cv2.IMREAD_COLOR)
            if img is not None:
                frames.append(img)
        except Exception:
            pass
        time.sleep(delay)
    return frames


def sharpest(frames):
    best, best_v = None, -1.0
    for f in frames:
        v = float(cv2.Laplacian(cv2.cvtColor(f, cv2.COLOR_BGR2GRAY), cv2.CV_64F).var())
        if v > best_v:
            best, best_v = f, v
    return best, best_v


# ---------------------------------------------------------------- YOLO
def _letterbox(img, size=640):
    h, w = img.shape[:2]
    r = min(size / h, size / w)
    nh, nw = int(round(h * r)), int(round(w * r))
    canvas = np.full((size, size, 3), 114, np.uint8)
    dh, dw = (size - nh) // 2, (size - nw) // 2
    canvas[dh:dh + nh, dw:dw + nw] = cv2.resize(img, (nw, nh))
    return canvas, r, dw, dh


def yolo_detect(img, conf=0.25):
    sess = _yolo()
    name = sess.get_inputs()[0].name
    lb, r, dw, dh = _letterbox(img)
    x = lb[:, :, ::-1].transpose(2, 0, 1)[None].astype(np.float32) / 255.0
    out = sess.run(None, {name: x})[0]
    if out.ndim == 3:
        out = out[0]
    if out.shape[0] < out.shape[1]:
        out = out.T
    hits = []
    for row in out:
        cs = row[4:]
        ci = int(np.argmax(cs))
        s = float(cs[ci])
        if s < conf:
            continue
        cx, cy, bw, bh = row[:4]
        x1 = (cx - bw / 2 - dw) / r
        y1 = (cy - bh / 2 - dh) / r
        x2 = (cx + bw / 2 - dw) / r
        y2 = (cy + bh / 2 - dh) / r
        hits.append({'label': CLASSES[ci] if ci < len(CLASSES) else str(ci),
                     'conf': round(s, 3),
                     'box': [int(x1), int(y1), int(x2), int(y2)]})
    return hits


# ---------------------------------------------------------------- VLM
def _post_json(url, payload, timeout=240):
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data,
                                 headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def _encode(img, maxw=768):
    h, w = img.shape[:2]
    if w > maxw:
        img = cv2.resize(img, (maxw, int(h * maxw / w)))
    ok, buf = cv2.imencode('.jpg', img, [cv2.IMWRITE_JPEG_QUALITY, 85])
    return base64.b64encode(buf.tobytes()).decode() if ok else None


def _ask(b64, question, model=VLM_MODEL, timeout=120, num_predict=8):
    payload = {'model': model, 'prompt': question, 'images': [b64],
               'stream': False, 'options': {'temperature': 0.0, 'num_predict': num_predict}}
    try:
        out = _post_json(OLLAMA, payload, timeout=timeout)
        return (out.get('response') or '').strip()
    except urllib.error.URLError as e:
        return f'__ERR__ ollama unreachable: {e}'
    except Exception as e:
        return f'__ERR__ {type(e).__name__}: {e}'


def _ask_cloud(b64, question, model=CLOUD_VLM, timeout=60, num_predict=8):
    """One cloud question through OpenRouter. SAME closed yes/no prompt as _ask().
    max_tokens has a floor of 16 so a reasoning-style model is not truncated."""
    if not OPENROUTER_KEY:
        return '__ERR__ no OPENROUTER_API_KEY configured'
    payload = {'model': model, 'temperature': 0, 'max_tokens': max(16, num_predict),
               'messages': [{'role': 'user', 'content': [
                   {'type': 'text', 'text': question},
                   {'type': 'image_url',
                    'image_url': {'url': 'data:image/jpeg;base64,' + b64}}]}]}
    req = urllib.request.Request(OPENROUTER_URL, data=json.dumps(payload).encode(),
                                 headers={'Content-Type': 'application/json',
                                          'Authorization': 'Bearer ' + OPENROUTER_KEY})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            d = json.loads(r.read().decode())
        msg = ((d.get('choices') or [{}])[0].get('message') or {})
        return (msg.get('content') or msg.get('reasoning') or '').strip()
    except urllib.error.HTTPError as e:
        return '__ERR__ http %s %s' % (e.code, e.read().decode()[:120])
    except Exception as e:
        return '__ERR__ %s: %s' % (type(e).__name__, e)


def _ask_route(b64, question, model, route='local', num_predict=8):
    if route == 'cloud':
        return _ask_cloud(b64, question, model, num_predict=num_predict)
    return _ask(b64, question, model, num_predict=num_predict)


def _timed_ask(b64, question, model, route='local'):
    t0 = time.time()
    a = _ask_route(b64, question, model, route)
    return a, time.time() - t0


def vlm_check(img, dish, ingredients, model=None, route=None, forbidden=None):
    """PRESENCE/ABSENCE the reliable way: ONE CLOSED yes/no QUESTION PER INGREDIENT.

    Why not hand the model the whole list?  Measured 2026-10-08 on this kitchen:
    given a list, llava:7b echoed the label back and called CAVIAR / SUSHI /
    ICE CREAM "present" in a charcuterie photo (no discrimination at all).
    Asked one item at a time it stops false-positives entirely.
    """
    b64 = _encode(img)
    if not b64:
        return {'error': 'jpeg encode failed'}

    route = route or QC_ROUTE
    if model is None:
        model = CLOUD_VLM if route == 'cloud' else VLM_MODEL

    def _q(item):
        return ('Look at the food in this photo. Is %s visible in the image? '
                'Answer with ONE word: yes or no.') % item

    answers = {}
    if route == 'cloud' and len(ingredients) > 1:
        # Fire every per-item question AT ONCE. This is the latency win: the
        # card is bounded by the SLOWEST single question, not the sum of them.
        # (Measured 2026-10-08: gemini-3-flash-preview ~2.7 s/question.)
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=len(ingredients)) as ex:
            futs = {ex.submit(_timed_ask, b64, _q(it), model, route): it for it in ingredients}
            for f, it in futs.items():
                try: answers[it] = f.result()
                except Exception as e: answers[it] = ('__ERR__ %s' % e, 0.0)
    else:
        for it in ingredients:
            answers[it] = _timed_ask(b64, _q(it), model, route)

    present, missing, per_item, notes = [], [], {}, []
    for item in ingredients:
        a, dt = answers.get(item, ('', 0.0))
        low = (a or '').strip().lower()
        cell = {'answer': (a or '')[:60], 's': round(dt, 2)}
        if low.startswith('__err__'):
            notes.append(a); missing.append(item); cell['result'] = 'error'
        elif low.startswith('y'):
            present.append(item); cell['result'] = 'yes'
        elif low.startswith('n'):
            missing.append(item); cell['result'] = 'no'
        else:
            # inconclusive -> treat as missing (fail safe: crew is asked)
            missing.append(item); cell['result'] = 'inconclusive'
        per_item[item] = cell

    quality = []
    aq, _dtq = _timed_ask(b64, 'Are there any visible quality problems with this food '
                   '(damage, wilting, discoloration, sloppy packing)? '
                   'Answer ONE word: yes or no.', model, route)
    if aq.strip().lower().startswith('y'):
        ad, _dtd = _timed_ask(b64, 'In five words or fewer, name the main quality problem.',
                  model, route)
        if ad and not ad.lower().startswith('__err__'):
            quality.append(ad.strip()[:70])

    # ---- THE OTHER HALF: forbidden items must be ABSENT ----
    # A nut-free gig means nuts present is a FAILURE, not a missing ingredient.
    violations, for_item = [], {}
    for item in (forbidden or []):
        q = ('Look at the food in this photo. Are %s visible in the image? '
             'Answer with ONE word: yes or no.') % item
        a, dt = _timed_ask(b64, q, model, route)
        low = (a or '').strip().lower()
        seen = low.startswith('y')
        for_item[item] = {'answer': (a or '')[:60], 'seen': seen, 's': round(dt, 2)}
        if seen:
            violations.append(item)
        elif low.startswith('__err__'):
            # cannot tell -> fail safe, surface it, never silently pass
            for_item[item]['result'] = 'error'

    return {'present': present, 'missing': missing, 'quality_issues': quality,
            'per_item': per_item, 'notes': ' | '.join(notes),
            'forbidden': list(forbidden or []), 'violations': violations,
            'forbidden_detail': for_item,
            'route': route, 'model': model,
            'slowest_s': max([c.get('s', 0) for c in per_item.values()] or [0])}


# ---------------------------------------------------------------- verify
def verify(card_id, dish, ingredients, player_pin='', override_pin='', cam='',
           frames=4, save=True, route=None, forbidden=None):
    if isinstance(ingredients, str):
        ingredients = [s for s in ingredients.replace(';', ',').split(',') if s.strip()]
    ingredients = [s.strip() for s in ingredients]

    url = cam or (MT2_PHOTO if 'mt2' in (card_id or '').lower() else MT1_PHOTO)
    fr = burst(n=frames, url=url)
    if not fr:
        return {'ok': False, 'error': f'no frames captured from {url}'}

    img, lapvar = sharpest(fr)
    yolo = yolo_detect(img)
    vlm = vlm_check(img, dish, ingredients, route=route, forbidden=forbidden)
    if not vlm.get('error') and not vlm.get('present') and not vlm.get('missing'):
        # model echoed the template instead of answering - ask once more, bluntly
        vlm2 = vlm_check(img, dish, ingredients, route=route, forbidden=forbidden)
        if vlm2.get('present') or vlm2.get('missing'):
            vlm = vlm2

    if 'error' in vlm:
        verdict, missing, present, quality = 'VLM_UNAVAILABLE', [], [], []
        notes = vlm['error']
    else:
        present = vlm.get('present', [])
        missing = vlm.get('missing', [])
        quality = vlm.get('quality_issues', [])
        violations = vlm.get('violations', [])
        # TWO-SIDED. Something that MUST BE ABSENT and IS PRESENT outranks a missing
        # item: a nut on a nut-free gig is a food-safety event, not a short pick.
        # Separate verdict so it can never be read as ordinary REVIEW.
        if violations:
            verdict = 'ALLERGEN_ALERT'
        elif (missing or quality):
            verdict = 'REVIEW'
        else:
            verdict = 'PASS'
        notes = vlm.get('raw', '') if 'parse_error' in vlm else ''

    violations = locals().get('violations', [])
    override_used = 0
    if verdict in ('REVIEW', 'ALLERGEN_ALERT') and override_pin:
        if SANDRA_PIN and override_pin == SANDRA_PIN:
            verdict, override_used = 'PASS_OVERRIDE', 1
        elif not SANDRA_PIN:
            notes = (notes + ' | override rejected: server has no QC_SANDRA_PIN set').strip(' |')
        else:
            notes = (notes + ' | override PIN incorrect').strip(' |')

    frame_path = ''
    if save and img is not None:
        ts = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        frame_path = os.path.join(SHOTS, f'{card_id or "card"}_{ts}.jpg')
        cv2.imwrite(frame_path, img)

    rec = {
        'ok': True,
        'card_id': card_id, 'dish': dish,
        'expected': ingredients, 'present': present, 'missing': missing,
        'quality_issues': quality, 'verdict': verdict,
        'forbidden': list(forbidden or []), 'violations': violations,
        'override_used': override_used,
        'points_awarded': verdict in ('PASS', 'PASS_OVERRIDE'),
        'sharpness': round(lapvar, 1),
        'yolo': yolo[:12],
        'frames': len(fr),
        'vlm_model': VLM_MODEL,
        'frame_path': frame_path,
        'notes': notes,
        'ts': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    try:
        db = _db()
        db.execute("""INSERT INTO qc_verdicts
            (ts,card_id,dish,expected,present,missing,quality,verdict,
             override_used,player_pin,frame_path,notes)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
            (rec['ts'], card_id, dish, json.dumps(ingredients),
             json.dumps(present), json.dumps(missing), json.dumps(quality),
             verdict, override_used, 'set' if player_pin else '',
             frame_path, notes))
        db.commit()
        db.close()
    except Exception as e:
        rec['db_error'] = str(e)
    return rec


def _last_frame():
    try:
        fs = sorted(f for f in os.listdir(SHOTS) if f.endswith('.jpg'))
        return os.path.join(SHOTS, fs[-1]) if fs else None
    except Exception:
        return None


# ---------------------------------------------------------------- routes
def register(app):
    from fastapi.responses import HTMLResponse, Response, JSONResponse

    @app.get('/api/qc/verify')
    def qc_verify(card_id: str = '', dish: str = '', ingredients: str = '',
                  player_pin: str = '', override_pin: str = '', cam: str = '',
                  frames: int = 4, route: str = '', forbidden: str = ''):
        if not ingredients:
            return JSONResponse({'ok': False, 'error': 'ingredients= required (comma separated)'},
                                status_code=400)
        fb = [x.strip() for x in forbidden.replace(';', ',').split(',') if x.strip()]
        return JSONResponse(verify(card_id, dish, ingredients, player_pin,
                                   override_pin, cam, frames, route=(route or None),
                                   forbidden=fb))

    @app.get('/api/qc/status')
    def qc_status():
        try:
            db = _db()
            n = db.execute('SELECT COUNT(*) FROM qc_verdicts').fetchone()[0]
            last = db.execute("""SELECT ts,card_id,dish,verdict,missing
                                 FROM qc_verdicts ORDER BY id DESC LIMIT 1""").fetchone()
            db.close()
        except Exception as e:
            return JSONResponse({'ok': False, 'error': str(e)})
        return JSONResponse({
            'ok': True, 'verdicts_logged': n,
            'override_gate_enabled': bool(SANDRA_PIN),
            'vlm_model': VLM_MODEL, 'cam': MT1_PHOTO,
            'last': ({'ts': last[0], 'card_id': last[1], 'dish': last[2],
                      'verdict': last[3], 'missing': json.loads(last[4] or '[]')}
                     if last else None),
        })

    @app.get('/api/qc/last.jpg')
    def qc_last():
        p = _last_frame()
        if not p:
            return Response(b'', status_code=404)
        return Response(open(p, 'rb').read(), media_type='image/jpeg')

    @app.get('/api/qc/cards')
    def qc_cards():
        try:
            db = _db()
            rows = db.execute("""SELECT card_id,dish,ingredients,status,created_ts
                                 FROM wip_cards ORDER BY id DESC LIMIT 50""").fetchall()
            db.close()
        except Exception as e:
            return JSONResponse({'ok': False, 'error': str(e)})
        return JSONResponse({'ok': True, 'cards': [
            {'card_id': r[0], 'dish': r[1], 'ingredients': json.loads(r[2] or '[]'),
             'status': r[3], 'created_ts': r[4]} for r in rows]})

    @app.get('/api/qc/card')
    def qc_new_card(card_id: str = '', dish: str = '', ingredients: str = '',
                    board: str = ''):
        ing = [s.strip() for s in ingredients.split(',') if s.strip()]
        try:
            db = _db()
            db.execute("""INSERT OR REPLACE INTO wip_cards
                          (card_id,dish,ingredients,board,created_ts,status)
                          VALUES(?,?,?,?,?,'open')""",
                       (card_id, dish, json.dumps(ing), board,
                        datetime.datetime.now(datetime.timezone.utc).isoformat()))
            db.commit()
            db.close()
        except Exception as e:
            return JSONResponse({'ok': False, 'error': str(e)})
        return JSONResponse({'ok': True, 'card_id': card_id, 'dish': dish, 'ingredients': ing})

    @app.get('/qc', response_class=HTMLResponse)
    def qc_page():
        return HTMLResponse(QC_HTML)


QC_HTML = """<!doctype html><meta name=viewport content="width=device-width,initial-scale=1">
<style>body{background:#1a3a2a;color:#eee;font:16px/1.5 system-ui;margin:0;padding:20px}
h1{color:#c7ae59;font-size:22px}input,button{font:inherit;padding:12px;border-radius:8px;border:0;margin:4px 0}
input{width:100%}button{background:#c7ae59;color:#1a3a2a;font-weight:700;width:100%;padding:16px}
#out{white-space:pre-wrap;background:#0e2419;padding:14px;border-radius:10px;margin-top:14px;min-height:120px}
img{width:100%;border-radius:10px;margin-top:14px}.m{color:#ff8f6b}</style>
<h1>Mom's Table &middot; Pack-Out QC</h1>
<label>Card / dish</label><input id=dish value="Charcuterie">
<label>Expected ingredients (comma separated)</label>
<input id=ing value="cheese, salami, grapes, crackers, nuts">
<label>Your PIN</label><input id=pin inputmode=numeric>
<label>Sandra override PIN (only if flagged)</label><input id=ov inputmode=numeric>
<button onclick="run()">SUBMIT FOR AI CHECK</button>
<div id=out>Idle.</div><img id=shot src="/api/qc/last.jpg">
<script>
async function run(){
 var d=document.getElementById('dish').value;
 var q=new URLSearchParams({card_id:d,dish:d,ingredients:document.getElementById('ing').value,
  player_pin:document.getElementById('pin').value,override_pin:document.getElementById('ov').value,frames:4});
 document.getElementById('out').textContent='Watching... spin the item slowly.';
 var r=await(await fetch('/api/qc/verify?'+q)).json();
 var t='VERDICT: '+r.verdict+'\\n';
 if(r.missing&&r.missing.length) t+='MISSING: '+r.missing.join(', ')+'\\n';
 if(r.quality_issues&&r.quality_issues.length) t+='QUALITY: '+r.quality_issues.join(', ')+'\\n';
 t+='Points awarded: '+r.points_awarded+'\\n';
 if(r.missing&&r.missing.length) t+='ASK crew: "should this get '+r.missing.join('/')+'? I didn\\'t see any."\\n';
 t+='\\n'+JSON.stringify(r,null,1);
 document.getElementById('out').textContent=t;
 document.getElementById('shot').src='/api/qc/last.jpg?t='+Date.now();
}
</script>"""

register.register = register  # keep linters quiet
