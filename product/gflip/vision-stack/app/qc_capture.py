"""QC bootstrap capture - "require a picture of each item".

Nick 2026-10-08, bootstrap scope (spirit per D50 / decisions.bootstrap_debt):
  - presence / absence ONLY
  - a PICTURE OF EACH ITEM is REQUIRED before a card can be judged
  - the camera image FLOATS OVER the kanban game while the system takes photo + video
  - a compressed clip (.gif) is saved next to the still
  - the ingredient list is the one ON THE LABEL, which comes from the recipe store

Hard rule: no capture OR no known ingredient list -> NO VERDICT. Never a silent pass.
Ingredient resolution order (one source of truth = world.db.recipes):
  1. explicit `ingredients` argument
  2. world.db.recipes for the dish name        <- mirrored from tazaos.menu_items
  3. world.db.wip_cards for the card
"""
import os, json, time, sqlite3, datetime

import cv2
from PIL import Image
from fastapi import Request
from fastapi.responses import HTMLResponse, Response, JSONResponse

import qc_vision as Q

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, 'world', 'world.db')
CAPS = os.path.join(ROOT, 'calibration', 'captures', 'qc_items')
os.makedirs(CAPS, exist_ok=True)
RTSP = os.environ.get('QC_RTSP', 'rtsp://127.0.0.1:8554/ptz_h264')



# --------------------------------------------------------------------------
# WHAT SHOULD BE PRESENT *AND* WHAT SHOULD BE ABSENT.
# Driven by the gig. Three sources, in order:
#   1. explicit arguments
#   2. world.db.gig_rules  (kind='required'|'forbidden') - a human or the
#      Orders API can write these; this is the bootstrap path
#   3. world.db.recipes / recipe_facts for the dish (auto-answer)
# The forbidden side expands an allergen token to its family, because a
# "nut-free" gig is breached by almonds and cashews, not only by "nuts".
# --------------------------------------------------------------------------
ALLERGEN_FAMILY = {
    'nut':      ['nuts', 'peanuts', 'almonds', 'cashews', 'walnuts', 'pecans',
                 'pistachios', 'hazelnuts', 'macadamia', 'pine nuts'],
    'peanut':   ['peanuts', 'peanut butter'],
    'gluten':   ['wheat', 'bread', 'pasta', 'flour', 'croutons', 'pita', 'crackers'],
    'dairy':    ['cheese', 'butter', 'cream', 'milk', 'yogurt', 'feta'],
    'shellfish':['shrimp', 'crab', 'lobster', 'scallops', 'clams', 'mussels'],
    'egg':      ['egg', 'mayonnaise', 'aioli'],
    'soy':      ['soy', 'tofu', 'edamame', 'soy sauce'],
    'sesame':   ['sesame', 'tahini', 'hummus'],
    'fish':     ['salmon', 'tuna', 'sea bass', 'anchovy'],
}


def expand_forbidden(tokens):
    out = []
    for t in tokens or []:
        t = (t or '').strip().lower()
        if not t:
            continue
        key = t.replace('free', '').replace('-', ' ').strip().split(' ')[0]
        fam = ALLERGEN_FAMILY.get(key)
        out.extend(fam if fam else [t])
    seen, uniq = set(), []
    for x in out:
        if x not in seen:
            seen.add(x); uniq.append(x)
    return uniq


def gig_rules(gig_key):
    """(required, forbidden, sources) for a gig."""
    if not gig_key:
        return [], [], {}
    db = _db(); cur = db.cursor()
    req, forb = [], []
    try:
        for kind, item, note in cur.execute(
                "select kind, item, note from gig_rules where gig_key=?", (gig_key,)):
            if kind == 'required':
                req.append(item)
            elif kind == 'forbidden':
                forb.append(item)
    finally:
        db.close()
    return req, forb, {'gig_rules': gig_key}


def resolve_for_gig(gig_key='', dish='', card_id='', ingredients=None, forbidden=None):
    """Required + forbidden, with the source of each recorded."""
    req, forb, src = [], [], []
    if ingredients:
        if isinstance(ingredients, str):
            ingredients = [x.strip() for x in ingredients.replace(';', ',').split(',') if x.strip()]
        req, _ = ingredients, src.append('explicit-required')
    if forbidden:
        if isinstance(forbidden, str):
            forbidden = [x.strip() for x in forbidden.replace(';', ',').split(',') if x.strip()]
        forb, _ = list(forbidden), src.append('explicit-forbidden')
    gr, gf, _ = gig_rules(gig_key)
    if gr and not req:
        req, _ = gr, src.append('gig_rules:required')
    if gf:
        forb, _ = forb + gf, src.append('gig_rules:forbidden')
    if not req:
        r, s2 = resolve_ingredients(dish, card_id, None)
        if r:
            req, _ = r, src.append(s2)
    # a dish whose own text says "no nuts" / "gluten-free" carries the ban itself
    if not forb and dish:
        db = _db()
        try:
            row = db.execute("select description from recipes where item=? or item like ? limit 1",
                             (dish, '%' + dish.replace('Catering ', '') + '%')).fetchone()
        except Exception:
            row = None
        finally:
            db.close()
        if row and row[0]:
            t = row[0].lower()
            for cue in ('no nuts', 'nut free', 'nut-free', 'gluten free', 'gluten-free', 'no gluten'):
                if cue in t:
                    forb = expand_forbidden([cue.split()[-1]])
                    src.append('dish-text:' + cue)
                    break
    return req, expand_forbidden(forb), ','.join(src)


def _db():
    c = sqlite3.connect(DB, timeout=10)
    c.execute("""create table if not exists captures(
        id integer primary key autoincrement, ts text, card_id text, dish text,
        photo text, clip text, frames integer, ingredient_source text,
        ingredients text, verdict text, missing text, notes text)""")
    return c


def resolve_ingredients(dish='', card_id='', explicit=None):
    """Return (list, source). Empty list means we refuse to judge."""
    if explicit:
        if isinstance(explicit, str):
            explicit = [s.strip() for s in explicit.replace(';', ',').split(',') if s.strip()]
        if explicit:
            return explicit, 'explicit'
    db = _db(); cur = db.cursor()
    try:
        if card_id:
            r = cur.execute("select ingredients from wip_cards where card_id=?", (card_id,)).fetchone()
            if r and r[0]:
                try:
                    ing = json.loads(r[0])
                    if ing:
                        return ing, 'wip_cards'
                except Exception:
                    pass
        if dish:
            for pat in (dish, dish.replace('Catering ', ''), '%' + dish.replace('Catering ', '') + '%'):
                r = cur.execute("""select ingredients from recipes where item=?
                                   or item like ? order by length(ingredients) desc limit 1""",
                                (pat, '%' + pat.strip('%') + '%')).fetchone()
                if r and r[0]:
                    try:
                        ing = json.loads(r[0])
                        if ing:
                            return ing, 'recipes:' + dish
                    except Exception:
                        pass
    finally:
        db.close()
    return [], 'none'


def grab_clip(secs=3.0, fps=10):
    """~secs of live frames. RTSP first (smooth), else the MT1 photo burst."""
    frames = []
    try:
        cap = cv2.VideoCapture(RTSP)
        t0 = time.time()
        while time.time() - t0 < secs and len(frames) < int(secs * fps):
            ok, f = cap.read()
            if ok:
                frames.append(f)
            else:
                time.sleep(0.02)
        cap.release()
    except Exception:
        frames = []
    if not frames:
        frames = Q.burst(n=12)
    return frames


def save_gif(frames, path, width=320, ms=110, colors=96):
    ims = []
    for f in frames:
        h, w = f.shape[:2]
        im = cv2.resize(f, (width, max(1, int(h * width / w))))
        im = cv2.cvtColor(im, cv2.COLOR_BGR2RGB)
        ims.append(Image.fromarray(im).convert('P', palette=Image.ADAPTIVE, colors=colors))
    if not ims:
        return False
    ims[0].save(path, save_all=True, append_images=ims[1:], duration=ms, loop=0, optimize=True)
    return True


def capture(card_id='', dish='', ingredients=None, secs=3.0, judge=True,
            forbidden=None, gig_key=''):
    rec = {'ok': True, 'ts': datetime.datetime.now(datetime.timezone.utc).isoformat(),
           'card_id': card_id, 'dish': dish}
    ing, forb, src = resolve_for_gig(gig_key, dish, card_id, ingredients, forbidden)
    rec['ingredient_source'] = src
    rec['ingredients'] = ing
    rec['forbidden'] = forb

    frames = grab_clip(secs)
    if not frames:
        rec.update(ok=False, error='no frames - camera unreachable')
        return rec
    img, lap = Q.sharpest(frames)
    stamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    base = '%s_%s' % ((card_id or dish or 'item').replace(' ', '_')[:40], stamp)
    photo = os.path.join(CAPS, base + '.jpg')
    clip = os.path.join(CAPS, base + '.gif')
    cv2.imwrite(photo, img, [cv2.IMWRITE_JPEG_QUALITY, 82])
    save_gif(frames, clip)
    rec.update(photo=os.path.basename(photo), clip=os.path.basename(clip),
               frames=len(frames), sharpness=round(float(lap), 1))

    if not ing:
        # REQUIRED PICTURE RULE: we have the picture, but we cannot judge without a list.
        rec.update(verdict='BLOCKED', missing=[], notes='no ingredient list for this dish - '
                   'add it to world.db.recipes (mirrored from tazaos.menu_items)')
    elif judge:
        v = Q.verify(card_id or 'capture', dish, ing, frames=3, save=False, route=None,
                     forbidden=forb)
        rec['verdict'] = v.get('verdict')
        rec['missing'] = v.get('missing', [])
        rec['violations'] = v.get('violations', [])
        rec['present'] = v.get('present', [])
        rec['vlm'] = (v.get('vlm') or {}).get('route') or v.get('vlm_model')
    else:
        rec['verdict'] = 'CAPTURED'

    db = _db()
    db.execute("""insert into captures(ts,card_id,dish,photo,clip,frames,ingredient_source,
                                       ingredients,verdict,missing,notes)
                  values(?,?,?,?,?,?,?,?,?,?,?)""",
               (rec['ts'], card_id, dish, rec.get('photo'), rec.get('clip'), rec.get('frames'),
                src, json.dumps(ing), rec.get('verdict'),
                json.dumps(rec.get('missing', [])), rec.get('notes', '')))
    db.commit(); db.close()
    return rec


OVERLAY_CSS = """
html,body{margin:0;background:transparent;font:13px/1.4 system-ui,sans-serif;color:#e8f0ea}
.card{background:rgba(14,32,24,.92);border:1px solid rgba(120,220,160,.35);border-radius:14px;
      overflow:hidden;backdrop-filter:blur(6px);box-shadow:0 12px 40px rgba(0,0,0,.45)}
.bar{display:flex;align-items:center;gap:8px;padding:8px 10px;background:rgba(9,22,16,.9)}
.bar b{font-size:13px;letter-spacing:.02em}
.bar .sp{flex:1}
.x{cursor:pointer;opacity:.7;padding:0 4px}
img.live{display:block;width:100%;background:#000}
.row{display:flex;gap:8px;padding:10px}
button{flex:1;padding:11px;border:0;border-radius:10px;background:#3ddc84;color:#04220f;
       font-weight:700;font-size:14px;cursor:pointer}
button.alt{background:#2b6b4d;color:#dff7e9}
.out{padding:0 10px 12px;font-size:12.5px;white-space:pre-wrap}
.miss{color:#ff9a76;font-weight:600}.ok{color:#8ee6b0;font-weight:600}
img.clip{width:100%;display:block;background:#000}
"""


def register(app):
    @app.get('/qc/capture', response_class=HTMLResponse)
    def qc_capture_page(card_id: str = '', dish: str = ''):
        return HTMLResponse("""<!doctype html><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1">
<style>%s</style>
<div class=card>
  <div class=bar><b>QC &middot; picture required</b><span class=sp></span>
    <span class=x onclick="document.getElementById('qc-ov').style.display='none'">hide</span></div>
  <img class=live id=live src="/streams/ptz.mjpg">
  <div class=row><button onclick="cap()">TAKE PICTURE</button>
    <button class=alt onclick="document.getElementById('live').src='/streams/ptz.mjpg?'+Date.now()">reload</button></div>
  <div class=out id=out>Spin the item slowly, then take the picture.</div>
  <img class=clip id=clip style="display:none">
</div>
<script>
var CARD=%s, DISH=%s;
async function cap(){
  var o=document.getElementById('out'); o.textContent='capturing 3s of video + photo...';
  var r=await(await fetch('/api/qc/capture',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({card_id:CARD,dish:DISH,secs:3})})).json();
  var t='VERDICT: '+(r.verdict||r.error||'?')+'\\n';
  if(r.ingredients&&r.ingredients.length) t+='label says: '+r.ingredients.join(', ')+'\\n';
  t+='source: '+(r.ingredient_source||'-')+'  frames: '+(r.frames||0)+'\\n';
  if(r.missing&&r.missing.length) t+='MISSING: '+r.missing.join(', ')+'\\n';
  if(r.notes) t+=r.notes+'\\n';
  o.innerHTML=t.replace(/MISSING:/,'<span class=miss>MISSING:</span>')
                .replace(/VERDICT: (PASS|CAPTURED)/,'<span class=ok>VERDICT: $1</span>');
  if(r.clip){var c=document.getElementById('clip'); c.style.display='block'; c.src='/api/qc/captures/clip/'+r.clip+'?t='+Date.now();}
}
</script>""" % (OVERLAY_CSS, json.dumps(card_id), json.dumps(dish)))

    @app.get('/qc/embed.js')
    def qc_embed():
        """One line to float the camera over the kanban game:
           <script src="http://192.168.2.107:8090/qc/embed.js?card_id=X&dish=Y"></script>"""
        js = """(function(){
  var q=new URLSearchParams(location.search);
  var f=document.createElement('iframe'); f.id='qc-ov';
  f.src='http://'+location.hostname+':8090/qc/capture?card_id='+encodeURIComponent(q.get('card_id')||'')
        +'&dish='+encodeURIComponent(q.get('dish')||'');
  f.style.cssText='position:fixed;right:16px;bottom:16px;width:380px;height:520px;border:0;'
                 +'z-index:2147483647;background:transparent';
  document.body.appendChild(f);
})();"""
        return Response(js, media_type='application/javascript')

    @app.post('/api/qc/capture')
    async def api_capture(req: Request):
        b = await req.json()
        return JSONResponse(capture(b.get('card_id', ''), b.get('dish', ''),
                                    b.get('ingredients'), float(b.get('secs', 3.0)),
                                    forbidden=b.get('forbidden'),
                                    gig_key=b.get('gig_key', '')))

    @app.get('/api/gigs')
    def api_gigs():
        """Live gigs, each with what must be PRESENT and what must be ABSENT."""
        db = _db()
        rows = db.execute("""select gig_key, invoice_number, customer, event_date, days_out,
                                    service_code, status, balance_cents, menu_state
                             from gigs order by event_date, invoice_number""").fetchall()
        db.close()
        out = []
        for r in rows:
            req, forb, src = resolve_for_gig(r[0])
            out.append({'gig_key': r[0], 'invoice_number': r[1], 'customer': r[2],
                        'event_date': r[3], 'days_out': r[4], 'service_code': r[5],
                        'status': r[6], 'balance_cents': r[7], 'menu_state': r[8],
                        'required': req, 'forbidden': forb, 'rule_source': src})
        return JSONResponse({'ok': True, 'count': len(out), 'gigs': out})

    @app.post('/api/gigs/rules')
    async def api_gig_rules(req: Request):
        """Attach a required or forbidden item to a gig. Bootstrap path until the
        Orders API fills the dish list and dietary_flags on its own."""
        b = await req.json()
        gk = b.get('gig_key', '')
        kind = b.get('kind', '')
        if not gk or kind not in ('required', 'forbidden'):
            return JSONResponse({'ok': False, 'error': "gig_key and kind='required'|'forbidden' required"},
                                status_code=400)
        items = b.get('items') or []
        if isinstance(items, str):
            items = [x.strip() for x in items.replace(';', ',').split(',') if x.strip()]
        db = _db()
        for it in items:
            db.execute("""insert into gig_rules(gig_key,kind,item,note,source) values(?,?,?,?,?)
                          on conflict(gig_key,kind,item,source) do update set note=excluded.note""",
                       (gk, kind, it, b.get('note', ''), b.get('source', 'api')))
        db.commit(); db.close()
        req_, forb_, src = resolve_for_gig(gk)
        return JSONResponse({'ok': True, 'gig_key': gk, 'required': req_,
                             'forbidden': forb_, 'rule_source': src})

    @app.get('/api/qc/recipes')
    def api_recipes(dish: str = '', card_id: str = ''):
        ing, src = resolve_ingredients(dish, card_id)
        return JSONResponse({'ok': True, 'dish': dish, 'card_id': card_id,
                             'ingredients': ing, 'source': src})

    @app.get('/api/qc/captures')
    def api_captures(n: int = 20):
        db = _db()
        rows = db.execute("""select id,ts,card_id,dish,photo,clip,frames,ingredient_source,
                                    verdict,missing from captures order by id desc limit ?""",
                          (int(n),)).fetchall()
        db.close()
        out = [{'id': r[0], 'ts': r[1], 'card_id': r[2], 'dish': r[3], 'photo': r[4], 'clip': r[5],
                'frames': r[6], 'source': r[7], 'verdict': r[8],
                'missing': json.loads(r[9] or '[]')} for r in rows]
        return JSONResponse({'ok': True, 'count': len(out), 'captures': out})

    @app.get('/api/qc/captures/clip/{name}')
    def api_clip(name: str):
        p = os.path.join(CAPS, os.path.basename(name))
        if not os.path.exists(p):
            return Response(b'', status_code=404)
        return Response(open(p, 'rb').read(), media_type='image/gif')

    @app.get('/api/qc/captures/photo/{name}')
    def api_photo(name: str):
        p = os.path.join(CAPS, os.path.basename(name))
        if not os.path.exists(p):
            return Response(b'', status_code=404)
        return Response(open(p, 'rb').read(), media_type='image/jpeg')
