"""Taza Print Service - 'print a label for this thing'.

Any app can call it: Mom's Table kanban (card play -> WIP label), QC pack-out,
future apps. One job: take structured text, put ink on the Zebra.

Printer   Zebra TLP2844-Z @ 192.168.2.113:9100, 203 dpi (8 dots/mm).
Language  ZPL. Chosen because ~HI (a ZPL-only command) answered with the model
          string 'TLP2844-Z,V45.11.7Z,8,8192KB'. Verified 2026-10-08.
Transport raw TCP to port 9100 (JetDirect). No CUPS queue, no driver.

Status    bootstrap (v0.1) - same footing as vision-app.
"""
import os, socket, json, datetime

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse

VERSION = '0.1.0'
PRINTER_HOST = os.environ.get('PRINT_HOST', '192.168.2.113')
PRINTER_PORT = int(os.environ.get('PRINT_PORT', '9100'))
DPI = int(os.environ.get('PRINT_DPI', '203'))
DOTS_PER_IN = DPI
# KB PROD-13: Zebra Z-Ultimate 3000T, 4 in x 1 in, 203 dpi -> 812 x 203 dots.
W_DOTS = int(os.environ.get('PRINT_W_DOTS', '812'))   # 4.0 in
H_DOTS = int(os.environ.get('PRINT_H_DOTS', '203'))   # 1.0 in
MAX_COPIES = int(os.environ.get('PRINT_MAX_COPIES', '10'))
MAX_LINES = int(os.environ.get('PRINT_MAX_LINES', '14'))
LOG_PATH = os.environ.get('PRINT_LOG', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'print_log.jsonl'))

# ---------------- ingredient source: world.db.recipes (mirrored from tazaos.menu_items)
WORLD_DB = os.environ.get('PRINT_WORLD_DB', '/home/taza/vision-stack/world/world.db')


def recipe_ingredients(dish):
    """The label's ingredient list comes from the stored recipe data, not free text."""
    if not dish:
        return [], 'none'
    import sqlite3
    try:
        db = sqlite3.connect('file:%s?mode=ro' % WORLD_DB, uri=True, timeout=5)
    except Exception as e:
        return [], 'recipes-unavailable:%s' % e
    try:
        for pat in (dish, dish.replace('Catering ', ''),
                    '%' + dish.replace('Catering ', '') + '%'):
            r = db.execute("select ingredients from recipes where item=? or item like ? "
                           "order by length(ingredients) desc limit 1", (pat, pat)).fetchone()
            if r and r[0]:
                try:
                    ing = json.loads(r[0])
                    if ing:
                        return ing, 'recipes'
                except Exception:
                    pass
    finally:
        db.close()
    return [], 'none'


app = FastAPI(title='Taza Print Service', version=VERSION)


# ------------------------------------------------------------------ printer
def _clean(s, limit=120):
    """ZPL field data cannot contain ^ or ~ (control) - strip them and non-ascii."""
    s = '' if s is None else str(s)
    s = s.replace('^', ' ').replace('~', ' ').replace('%', 'pct')
    s = ''.join(ch if 32 <= ord(ch) < 127 else '?' for ch in s)
    return s.strip()[:limit]


def zebra_send(zpl, timeout=8.0):
    try:
        s = socket.create_connection((PRINTER_HOST, PRINTER_PORT), timeout=timeout)
    except OSError as e:
        return False, 'connect failed: %s' % e
    try:
        s.sendall(zpl.encode('ascii', 'replace'))
        return True, 'sent %d bytes to %s:%d' % (len(zpl), PRINTER_HOST, PRINTER_PORT)
    finally:
        try: s.close()
        except Exception: pass


def zebra_probe(timeout=5.0):
    """~HI returns the printer model string. Read-only, prints nothing."""
    try:
        s = socket.create_connection((PRINTER_HOST, PRINTER_PORT), timeout=timeout)
    except OSError as e:
        return {'reachable': False, 'error': str(e)}
    try:
        s.sendall(b'~HI')
        try:
            data = s.recv(256)
        except socket.timeout:
            data = b''
        txt = data.decode('ascii', 'replace').strip('\x02\x03\r\n ')
        return {'reachable': True, 'model_line': txt,
                'host': '%s:%d' % (PRINTER_HOST, PRINTER_PORT)}
    finally:
        try: s.close()
        except Exception: pass


def _log(entry):
    entry['ts'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    try:
        with open(LOG_PATH, 'a') as f:
            f.write(json.dumps(entry) + '\n')
    except OSError:
        pass


# ------------------------------------------------------------------ label
def build_zpl(title, lines, copies=1, w_dots=None, h_dots=None, qr=None, qr_caption=''):
    """Fill a 4x1 label (812 x 203 dots @ 203 dpi).

    GEOMETRY FROM THE KB (proven print, LABEL-SAMPLES-01 / 'Taza Smart Label System
    Full Spec V1.x'): QR in its own left block, a vertical rule, then the text zone
    filling the remaining ~3.4 in. Native ZPL ^BQ QR -> no image pipeline, so the
    'threshold-only, never dither' rule is satisfied by construction.

    Nick's readability fix (KB LABEL-REDESIGN-B-01): do not cram everything left, and
    the QR needs a caption saying what it does. Fonts: ^A0 scalable sans, title 34 dots
    (~4.3 mm cap height, readable at ~5 ft), body 26 dots, footnote 22.
    """
    w = int(w_dots or W_DOTS); h = int(h_dots or H_DOTS)
    use_qr = bool(qr)
    tx = 130 if use_qr else 10
    tw = w - tx - 8
    cap = ('Scan for dish details' if not qr_caption else qr_caption)

    z = ['^XA', '^CI28', '^PW%d' % w, '^LL%d' % h,
         '^MD18', '^PR4']
    if use_qr:
        # ^BQN,2,4 = Model 2, magnification 4 -> ~100x100 dots incl. quiet zone.
        z.append('^FO8,46^BQN,2,4^FDQA,%s^FS' % _clean(qr, 90))
        # The caption must stay inside the 100-dot QR column or it collides with the
        # rule at x=121. Wrap to <=11 chars a line at 11 dots per char, up to 3 lines.
        words = _clean(cap, 40).split()
        lines_c, cur = [], ''
        for wd in words:
            if not cur: cur = wd
            elif len(cur) + 1 + len(wd) <= 11: cur += ' ' + wd
            else: lines_c.append(cur); cur = wd
        if cur: lines_c.append(cur)
        cy = 148
        for cl in lines_c[:3]:
            z.append('^FO10,%d^A0N,15,11^FD%s^FS' % (cy, cl)); cy += 17
        z.append('^FO121,3^GB3,197,3^FS')          # vertical rule (KB: x=117)

    tmax = int(tw / 26) if use_qr else int(tw / 24)
    bmax = int(tw / 20) if use_qr else int(tw / 20)
    z.append('^FO%d,4^A0N,34,26^FD%s^FS' % (tx, _clean(title, min(tmax, 28))))
    y = 46
    body = [l for l in (lines or []) if _clean(l)]
    for i, ln in enumerate(body[:4]):
        fh = 26 if i < 3 else 22
        z.append('^FO%d,%d^A0N,%d,%d^FD%s^FS' % (tx, y, fh, fh - 6, _clean(ln, bmax)))
        y += 32 if i < 3 else 26
    z.append('^PQ%d' % max(1, min(int(copies), MAX_COPIES)))
    z.append('^XZ')
    return '\n'.join(z)


def _html(preview):
    css = """
body{font:15px/1.45 system-ui,sans-serif;margin:0;background:#111;color:#eee}
.wrap{max-width:760px;margin:0 auto;padding:24px}
h1{font-size:20px;margin:0 0 4px}.sub{color:#9aa;font-size:13px;margin-bottom:18px}
label{display:block;font-size:12px;text-transform:uppercase;letter-spacing:.06em;color:#9aa;margin:12px 0 4px}
input,textarea{width:100%;box-sizing:border-box;padding:10px;border-radius:8px;border:1px solid #333;background:#1b1b1f;color:#eee;font:inherit}
textarea{height:120px;font-family:ui-monospace,monospace;font-size:13px}
button{margin-top:16px;width:100%;padding:14px;border:0;border-radius:10px;background:#3ddc84;color:#04220f;font-size:17px;font-weight:700;cursor:pointer}
button:active{transform:translateY(1px)}
.row{display:flex;gap:12px}.row>div{flex:1}
pre{background:#1b1b1f;border:1px solid #333;border-radius:8px;padding:12px;overflow:auto;font-size:12px;color:#8fd}
.out{margin-top:14px;padding:12px;border-radius:8px;background:#1b1b1f;border:1px solid #333;white-space:pre-wrap;font-size:13px}
code{background:#1b1b1f;padding:1px 5px;border-radius:4px;font-size:12px}
"""
    return """<!doctype html><html><head><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1">
<title>Taza Print</title><style>%s</style></head><body><div class=wrap>
<h1>Print a label</h1>
<div class=sub>Zebra TLP2844-Z &middot; %s &middot; v%s &middot;
<a style="color:#3ddc84" href="/api/print/status">printer status</a></div>
<label>Title (dish / thing)</label><input id=title value="Charcuterie Board">
<label>Lines (one per line)</label>
<textarea id=lines>Card charcuterie_01   10-08 08:35
cheese / salami / grapes / crackers / nuts</textarea>
<div class=row><div><label>Copies</label><input id=copies type=number value=1 min=1 max=10></div></div>
<button onclick=go()>Print label</button>
<div class=out id=out>Press the button. Nothing prints until you do.</div>
<label style="margin-top:24px">ZPL preview (what goes to the printer)</label>
<pre id=pv></pre>
<div class=sub style="margin-top:22px">Other apps: <code>POST /api/print/label</code>
<code>{"title":..., "lines":[...], "copies":1}</code><br>
Kanban: <code>POST /api/print/wip</code> <code>{"card_id":...,"dish":...,"ingredients":[...]}</code></div>
</div><script>
function payload(){return {title:document.getElementById('title').value,
 lines:document.getElementById('lines').value.split('\\n'),
 copies:parseInt(document.getElementById('copies').value||'1')}}
async function preview(){let r=await fetch('/api/print/preview',{method:'POST',
 headers:{'Content-Type':'application/json'},body:JSON.stringify(payload())});
 let j=await r.json();document.getElementById('pv').textContent=j.zpl||j.error}
async function go(){let o=document.getElementById('out');o.textContent='printing...';
 let r=await fetch('/api/print/label',{method:'POST',
 headers:{'Content-Type':'application/json'},body:JSON.stringify(payload())});
 let j=await r.json();o.textContent=JSON.stringify(j,null,1)}
document.getElementById('lines').addEventListener('input',preview);
document.getElementById('title').addEventListener('input',preview);
preview();
</script></body></html>""" % (css, PRINTER_HOST, VERSION)


@app.get('/', response_class=HTMLResponse)
def home():
    return HTMLResponse(_html(None))


@app.get('/api/version')
def version():
    return {'app': 'print-app', 'version': VERSION, 'status': 'bootstrap',
            'printer': {'host': PRINTER_HOST, 'port': PRINTER_PORT, 'dpi': DPI,
                        'language': 'ZPL', 'model': 'Zebra TLP2844-Z'},
            'label_defaults': {'w_dots': W_DOTS, 'h_dots': H_DOTS, 'size_in': '4 x 1', 'dpi': DPI,
                           'stock': 'Zebra Z-Ultimate 3000T 4x1 + 5095 resin ribbon (KB PROD-13)'},
            'endpoints': ['/', '/api/print/label', '/api/print/wip', '/api/print/preview',
                          '/api/print/raw', '/api/print/status', '/api/print/log', '/api/version']}


@app.get('/api/print/status')
def status():
    p = zebra_probe()
    p['ok'] = True
    p['configured'] = {'host': PRINTER_HOST, 'port': PRINTER_PORT, 'dpi': DPI,
                       'w_dots': W_DOTS, 'h_dots': H_DOTS}
    return p


@app.post('/api/print/preview')
async def preview(req: Request):
    b = await req.json()
    return {'zpl': build_zpl(b.get('title', ''), b.get('lines', []), b.get('copies', 1),
                             b.get('w_dots'), b.get('h_dots'), qr=b.get('qr'),
                             qr_caption=b.get('qr_caption', ''))}


@app.post('/api/print/label')
async def print_label(req: Request):
    b = await req.json()
    title = _clean(b.get('title', ''), 40)
    if not title:
        return JSONResponse({'ok': False, 'error': 'title required'}, status_code=400)
    zpl = build_zpl(title, b.get('lines', []), b.get('copies', 1), b.get('w_dots'),
                    b.get('h_dots'), qr=b.get('qr'), qr_caption=b.get('qr_caption', ''))
    ok, detail = zebra_send(zpl)
    _log({'kind': 'label', 'title': title, 'copies': b.get('copies', 1), 'ok': ok,
          'detail': detail, 'label': '%dx%d' % (W_DOTS, H_DOTS)})
    return {'ok': ok, 'detail': detail, 'zpl': zpl}


@app.post('/api/print/wip')
async def print_wip(req: Request):
    """The kanban play path: a card is played -> its WIP label prints."""
    b = await req.json()
    card_id = _clean(b.get('card_id', ''), 40)
    dish = _clean(b.get('dish', ''), 40) or card_id or 'WIP'
    ing = b.get('ingredients') or []
    if isinstance(ing, str):
        ing = [x.strip() for x in ing.replace(';', ',').split(',') if x.strip()]
    ing_source = 'explicit' if ing else 'none'
    if not ing:
        ing, ing_source = recipe_ingredients(dish)   # label list <- stored recipe data
    lines = []
    if card_id:
        lines.append('Card %s     %s' % (card_id, datetime.datetime.now().strftime('%m-%d %H:%M')))
    if ing:
        lines.append(' / '.join(_clean(i, 24) for i in ing[:8]))
    zpl = build_zpl(dish, lines, b.get('copies', 1), b.get('w_dots'), b.get('h_dots'),
                    qr=b.get('qr', card_id or None),
                    qr_caption=b.get('qr_caption', 'Scan for dish details'))
    ok, detail = zebra_send(zpl)
    _log({'kind': 'wip', 'card_id': card_id, 'dish': dish, 'n_ingredients': len(ing),
          'ok': ok, 'detail': detail})
    return {'ok': ok, 'detail': detail, 'cards': [card_id], 'zpl': zpl,
            'ingredients': ing, 'ingredient_source': ing_source}


@app.post('/api/print/raw')
async def print_raw(req: Request):
    b = await req.json()
    zpl = b.get('zpl', '')
    if not zpl.strip().startswith('^XA'):
        return JSONResponse({'ok': False, 'error': 'refusing: raw ZPL must start with ^XA'},
                            status_code=400)
    ok, detail = zebra_send(zpl)
    _log({'kind': 'raw', 'ok': ok, 'detail': detail, 'bytes': len(zpl)})
    return {'ok': ok, 'detail': detail}


@app.get('/api/print/log')
def print_log(n: int = 20):
    try:
        with open(LOG_PATH) as f:
            rows = [json.loads(l) for l in f if l.strip()]
    except OSError:
        rows = []
    return {'count': len(rows), 'last': rows[-int(n):]}
