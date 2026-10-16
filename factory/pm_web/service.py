"""PM OS - one tiny service, two apps, one bookmark family.

  /architecture  data-driven architecture portal (from architecture.json)
  /sprinttracker the sprint tracker (Nick's PM board; SQLite)
  /kanban        308 -> /sprinttracker (old bookmark)

Same FastAPI + SQLite stack as the scheduler (job_runner/scheduler).
"""
import json
import os
import sqlite3
import threading
import time
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

import arch

HERE = os.path.dirname(os.path.abspath(__file__))
ARCH_JSON = os.path.join(HERE, "architecture.json")
DB_PATH = os.environ.get("PM_DB_PATH", os.path.join(HERE, "data", "kanban.db"))

app = FastAPI(title="PM OS", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

CSS = """
:root{--ink:#0f172a;--muted:#64748b;--line:#e2e8f0;--bg:#f5f6f8;--panel:#fff;--brand:#0f766e}
*{box-sizing:border-box}
body{margin:0;font-family:Inter,-apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
     background:var(--bg);color:var(--ink);-webkit-font-smoothing:antialiased}
header{background:var(--panel);border-bottom:1px solid var(--line);position:sticky;top:0;z-index:50}
.inn{max-width:1320px;margin:0 auto;padding:12px 22px;display:flex;align-items:center;gap:26px}
.brand{font-weight:800;font-size:16px;display:flex;gap:9px;align-items:center}
.brand .d{width:11px;height:11px;border-radius:50%;background:linear-gradient(135deg,#0f766e,#0ea5e9)}
nav a{color:var(--muted);text-decoration:none;font-weight:600;font-size:14px;padding:7px 12px;border-radius:8px}
nav a.active,nav a:hover{color:var(--ink);background:#eef2f7}
main{max-width:100%;margin:0 auto;padding:26px 22px 40px}
.muted{color:var(--muted)}.small{font-size:12.5px}
code{background:#eef2f7;padding:1px 5px;border-radius:5px;font-size:12px}
svg text{font-family:Inter,-apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
.card{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:16px;
      box-shadow:0 1px 3px rgba(15,23,42,.05)}
svg .card.clickable{cursor:pointer}
svg .card .details{pointer-events:auto}
@keyframes archflash{0%,100%{box-shadow:0 0 0 0 rgba(220,38,38,.45)}50%{box-shadow:0 0 0 16px rgba(220,38,38,0)}}
.alert{background:#fff1f2;border:1px solid #fca5a5;border-left:6px solid #dc2626;border-radius:12px;
       padding:14px 18px;margin:0 0 18px;animation:archflash 1.7s ease-out infinite}
.alert h2{margin:0 0 6px;font-size:17px;color:#b91c1c}
.alert .it{border-top:1px solid #fecdd3;padding:9px 0}
.alert .t{font-weight:700;color:#7f1d1d}
.alert code{background:#fee2e2}
.alert details summary{cursor:pointer}
.live{display:inline-block;background:#dcfce7;color:#15803d;font-weight:700;font-size:11.5px;
      padding:3px 9px;border-radius:999px;margin-right:8px;letter-spacing:.4px}
@media print{
  @page{size:letter portrait;margin:0.32in}
  header{display:none!important}
  body{background:#fff}
  main{padding:0;max-width:100%}
  .alert{animation:none;break-inside:avoid}
  svg{width:100%;height:auto;display:block}
  a{color:inherit;text-decoration:none}
  .card{box-shadow:none}
}
"""

def nav(active):
    a1 = ' class="active"' if active == "architecture" else ""
    a2 = ' class="active"' if active == "sprinttracker" else ""
    return ('<header class="top"><div class="inn"><div class="brand"><span class="d"></span>PM&nbsp;OS</div>'
            '<nav><a href="/architecture"%s>Architecture</a>'
            '<a href="/sprinttracker"%s>Sprint Tracker</a></nav>'
            '<span class="muted small" style="margin-left:auto">gflip · :8095</span></div></header>') % (a1, a2)

def page(title, active, body, extra=''):
    return ("<!doctype html><html lang='en'><head><meta charset='utf-8'>"
            "<meta name='viewport' content='width=device-width,initial-scale=1'>"
            "<title>%s · PM OS</title><style>%s</style></head><body>%s<main>%s</main></body></html>"
            ) % (title, CSS, _nav(active, extra), body)

def _nav(active, extra=''):
    a1 = ' class="active"' if active == "architecture" else ""
    a2 = ' class="active"' if active == "sprinttracker" else ""
    return ('<header class="top"><div class="inn"><div class="brand"><span class="d"></span>PM&nbsp;OS</div>'
            '<nav><a href="/architecture"%s>Architecture</a>'
            '<a href="/sprinttracker"%s>Sprint Tracker</a></nav>'
            '<div style="margin-left:auto;display:flex;gap:8px;align-items:center;flex-wrap:wrap">' + extra + '</div>'
            '<span class="muted small">gflip · :8095</span></div></header>') % (a1, a2)

# ============================ /architecture ================================
@app.get("/", response_class=HTMLResponse)
def home():
    return RedirectResponse("/architecture")

LIVE_JSON = os.path.join(HERE, "data", "arch_live.json")

try:
    _ROLES = json.load(open(os.path.join(HERE, "roles.json"))).get("roles", {})
except Exception:                                            # noqa: BLE001
    _ROLES = {}
ROLE_FALLBACK = {"label": "WHAT IS THIS?", "fg": "#c2410c", "bg": "#ffedd5"}


def _role_chip(key):
    r = _ROLES.get(key or "unlabelled") or ROLE_FALLBACK
    return ('<span style="display:inline-block;padding:2px 9px;border-radius:11px;font-size:11px;'
            'font-weight:700;background:%s;color:%s;border:1px solid %s;margin-right:8px">%s</span>'
            % (r["bg"], r["fg"], r["fg"], _e(r["label"])))

def _e(x):
    """Escape anything that came off a machine before it reaches HTML."""
    return (str(x).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace('"', "&quot;"))

@app.get("/architecture.json")
def architecture_json():
    """The same facts the diagram is drawn from, raw JSON. For scripts and for AI readers."""
    try:
        with open(LIVE_JSON) as fh:
            return JSONResponse(json.load(fh))
    except Exception as e:
        raise HTTPException(status_code=503, detail="no scan yet: %s" % e)

@app.get("/architecture", response_class=HTMLResponse)
def architecture(print: int = 0):
    pmode = print in (2, 3)
    if pmode:
        arch.PRINT_COLS = print
    d, svg = arch.render(print_mode=pmode)
    if pmode:
        d["subtitle"] = ("PAPER COPY - %d-column print layout of the physical inventory. "
                         "The hourly repo-hygiene scans stay on the screen page." % print)
    try:
        with open(LIVE_JSON) as fh:
            live = json.load(fh)
    except Exception:
        live = {}
    dec = live.get("decisions") or []

    legend = ('<div class="small" style="margin-top:10px">colour = role &nbsp;'
              + " ".join(_role_chip(k) for k in list(_ROLES) + ["unlabelled"])
              + '&nbsp; change a label by editing <code>roles.json</code></div>')

    if dec:
        rows = []
        for i in dec:
            ev = "".join("<li><code>%s</code></li>" % _e(x) for x in (i.get("ev") or []))
            rows.append(
                '<div class="it">%s<div class="t">%s</div>'
                '<div class="small muted">%s</div>'
                '<div class="small" style="margin-top:3px"><b>do:</b> %s</div>'
                '%s</div>'
                % (_role_chip(i.get("role")), _e(i.get("title")), _e(i.get("why")), _e(i.get("action")),
                   ('<details><summary class="small muted">evidence</summary>'
                    '<ul class="small">%s</ul></details>' % ev) if ev else ""))
        alert = ('<div class="alert"><h2>&#9888;&nbsp; %d thing(s) need a decision</h2>%s'
                 '<div class="small muted" style="margin-top:10px">Pushed to ntfy.sh/taza-ops '
                 'whenever this list changes. Nothing on this page moves, deletes or restarts '
                 'anything &mdash; it only tells you.</div>%s</div>') % (len(dec), "".join(rows), legend)
    elif live:
        alert = ('<div class="card" style="border-left:6px solid #16a34a;margin:0 0 18px">'
                 '<b style="color:#15803d">No forks, no duplicate clones, no shadowed files.</b> '
                 '<span class="muted small">Every checkout on both boxes has one owner.</span></div>')
    else:
        alert = ('<div class="card" style="border-left:6px solid #f59e0b;margin:0 0 18px">'
                 '<b>No scan yet.</b> <span class="muted small">Run <code>python3 '
                 'arch_scan.py</code> on gflip, or wait for the hourly cron.</span></div>')

    stamp = _e(live.get("generated_at") or "never")
    nxt = _e(live.get("next_run") or "hourly")
    secs = live.get("scan_seconds")
    errs = live.get("errors") or []
    hosts = len(live.get("hosts") or [])
    err = ('<span class="small" style="color:#b91c1c"> scan errors: %s</span>'
           % _e("; ".join(errs))) if errs else ""

    body = (
        '<div style="max-width:100%%">'
        '<h1 style="margin:6px 0 10px;font-size:27px">%s</h1>'
        '<div style="margin:0 0 8px"><span class="live">&#9679; LIVE</span>'
        '<span class="muted small">scanned off %d machines at <b>%s</b> &middot; next scan %s'
        ' &middot; took %ss%s &middot; raw data '
        '<a href="/architecture.json">/architecture.json</a></span></div>'
        '<p class="muted" style="margin:0 0 18px;max-width:1000px">%s</p>'
        '%s'
        '<div class="card" style="padding:20px 14px">%s</div>'
        '<p class="muted small" style="margin-top:16px;max-width:1000px">'
        'Read off the live boxes by <code>arch_scan.py</code> + <code>arch_collect.sh</code> '
        '(gflip local, n100 over ssh) and rewritten every hour by cron at :05. '
        'The page follows the machines; nobody edits it. Click any card for its details.'
        '</p></div>'
        '<script>'
        "document.querySelectorAll('g.card.clickable').forEach(function(c){"
        "  c.addEventListener('click',function(){var dd=c.querySelector('.details');"
        "    if(!dd)return; var open=dd.getAttribute('display')!=='block';"
        "    dd.setAttribute('display',open?'block':'none');"
        "    c.setAttribute('aria-expanded',open?'true':'false');});"
        "  c.addEventListener('keydown',function(e){if(e.key==='Enter'||e.key===' '){e.preventDefault();c.click();}});"
        "});"
        "setTimeout(function(){location.reload();},300000);"
        "</script>"
    ) % (d["title"], hosts, stamp, nxt, secs, err, d["subtitle"], alert, svg)
    if pmode:
        # PAPER: the SVG is the whole body. A giant SVG always starts a fresh sheet, so any
        # HTML above it just burns page 1 -- so the title goes INSIDE the SVG instead.
        hdr = ('<g id="paperhead">'
               '<text x="24" y="20" font-size="16.5" font-weight="800" fill="#0f172a">%s &#8212; PAPER COPY (%d columns)</text>'
               '<text x="24" y="36" font-size="11" font-weight="400" fill="#64748b">%s  &#183;  read off the machines, nothing hand-written, nobody edits it</text>'
               '</g>') % (_e(d["title"]), print, _e(stamp))
        svg = svg.replace(">\n", ">\n" + hdr + "\n", 1)
        body = svg
    return page("Architecture", "architecture", body)

# ================================ kanban db =================================
_DB_LOCK = threading.Lock()

def db():
    con = sqlite3.connect(DB_PATH, check_same_thread=False)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys=ON")
    with con:
        con.execute("""CREATE TABLE IF NOT EXISTS columns(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL, position INTEGER NOT NULL)""")
        con.execute("""CREATE TABLE IF NOT EXISTS cards(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            column_id INTEGER NOT NULL REFERENCES columns(id),
            title TEXT NOT NULL,
            description TEXT NOT NULL DEFAULT '',
            priority TEXT NOT NULL DEFAULT 'medium',
            position INTEGER NOT NULL DEFAULT 0,
            deps TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL, updated_at TEXT NOT NULL)""")
        cols = [r["name"] for r in con.execute("PRAGMA table_info(cards)").fetchall()]
        if "position" not in cols:
            con.execute("ALTER TABLE cards ADD COLUMN position INTEGER NOT NULL DEFAULT 0")
        if "deps" not in cols:
            con.execute("ALTER TABLE cards ADD COLUMN deps TEXT NOT NULL DEFAULT ''")
        if con.execute("SELECT COUNT(*) c FROM columns").fetchone()["c"] == 0:
            for i, nm in enumerate(["Backlog", "In Progress", "Blocked", "Done"]):
                con.execute("INSERT INTO columns(name,position) VALUES(?,?)", (nm, i))
        con.commit()
    return con

def board():
    con = db()
    cols = con.execute("SELECT * FROM columns ORDER BY position, id").fetchall()
    out = []
    for c in cols:
        cards = con.execute(
            "SELECT * FROM cards WHERE column_id=? ORDER BY position, id",
            (c["id"],)).fetchall()
        out.append({"id": c["id"], "name": c["name"],
                    "cards": [dict(x) for x in cards]})
    con.close()
    return out

class CardIn(BaseModel):
    column_id: int
    title: str = Field(..., min_length=1, max_length=300)
    description: str = ""
    priority: str = "medium"
    deps: str = ""

class CardPatch(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[str] = None
    column_id: Optional[int] = None
    position: Optional[int] = None
    deps: Optional[str] = None

class ColumnIn(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=120)
    position: Optional[int] = None

@app.get("/api/sprinttracker/board")
@app.get("/api/kanban/board", include_in_schema=False)
def get_board():
    with _DB_LOCK:
        return board()

@app.post("/api/sprinttracker/cards", status_code=201)
@app.post("/api/kanban/cards", status_code=201, include_in_schema=False)
def create_card(c: CardIn):
    with _DB_LOCK:
        con = db()
        now = time.strftime("%Y-%m-%d %H:%M:%S")
        pos = con.execute("SELECT COALESCE(MIN(position),0)-1 p FROM cards WHERE column_id=?",
                          (c.column_id,)).fetchone()["p"]
        cur = con.execute(
            "INSERT INTO cards(column_id,title,description,priority,position,deps,created_at,updated_at) "
            "VALUES(?,?,?,?,?,?,?,?)",
            (c.column_id, c.title, c.description, c.priority, pos, c.deps, now, now))
        con.commit()
        row = con.execute("SELECT * FROM cards WHERE id=?", (cur.lastrowid,)).fetchone()
        con.close()
        return dict(row)

@app.patch("/api/sprinttracker/cards/{card_id}")
@app.patch("/api/kanban/cards/{card_id}", include_in_schema=False)
def update_card(card_id: int, c: CardPatch):
    with _DB_LOCK:
        con = db()
        row = con.execute("SELECT * FROM cards WHERE id=?", (card_id,)).fetchone()
        if row is None:
            raise HTTPException(404, "card not found")
        now = time.strftime("%Y-%m-%d %H:%M:%S")
        con.execute(
            "UPDATE cards SET title=?,description=?,priority=?,column_id=?,position=?,deps=?,updated_at=? WHERE id=?",
            (c.title if c.title is not None else row["title"],
             c.description if c.description is not None else row["description"],
             c.priority if c.priority is not None else row["priority"],
             c.column_id if c.column_id is not None else row["column_id"],
             c.position if c.position is not None else row["position"],
             c.deps if c.deps is not None else row["deps"],
             now, card_id))
        con.commit()
        row = con.execute("SELECT * FROM cards WHERE id=?", (card_id,)).fetchone()
        con.close()
        return dict(row)

@app.delete("/api/sprinttracker/cards/{card_id}")
@app.delete("/api/kanban/cards/{card_id}", include_in_schema=False)
def delete_card(card_id: int):
    with _DB_LOCK:
        con = db()
        con.execute("DELETE FROM cards WHERE id=?", (card_id,))
        con.commit()
        con.close()
        return {"ok": True}

class ReorderIn(BaseModel):
    columns: list

@app.post("/api/sprinttracker/reorder")
@app.post("/api/kanban/reorder", include_in_schema=False)
def reorder_cards(r: ReorderIn):
    with _DB_LOCK:
        con = db()
        now = time.strftime("%Y-%m-%d %H:%M:%S")
        for col in r.columns:
            for idx, cid in enumerate(col.get("card_ids", [])):
                con.execute("UPDATE cards SET column_id=?, position=?, updated_at=? WHERE id=?",
                            (col["column_id"], idx, now, cid))
        con.commit()
        con.close()
        return {"ok": True}

@app.post("/api/sprinttracker/columns", status_code=201)
@app.post("/api/kanban/columns", status_code=201, include_in_schema=False)
def create_column(c: ColumnIn):
    with _DB_LOCK:
        con = db()
        pos = con.execute("SELECT COALESCE(MAX(position),-1)+1 p FROM columns").fetchone()["p"]
        cur = con.execute("INSERT INTO columns(name,position) VALUES(?,?)", (c.name, pos))
        con.commit()
        con.close()
        return {"id": cur.lastrowid, "name": c.name}

@app.patch("/api/sprinttracker/columns/{cid}")
@app.patch("/api/kanban/columns/{cid}", include_in_schema=False)
def update_column(cid: int, c: ColumnIn):
    """Rename a column and/or reorder it (position = target slot in the column order)."""
    with _DB_LOCK:
        con = db()
        if con.execute("SELECT id FROM columns WHERE id=?", (cid,)).fetchone() is None:
            raise HTTPException(404, "column not found")
        if c.name is not None:
            con.execute("UPDATE columns SET name=? WHERE id=?", (c.name, cid))
        if c.position is not None:
            order = [r["id"] for r in con.execute(
                "SELECT id FROM columns ORDER BY position, id").fetchall()]
            if cid in order:
                order.remove(cid)
                target = max(0, min(int(c.position), len(order)))
                order.insert(target, cid)
                for i, col_id in enumerate(order):
                    con.execute("UPDATE columns SET position=? WHERE id=?", (i, col_id))
        con.commit()
        con.close()
        return {"id": cid, "name": c.name, "position": c.position}

@app.delete("/api/sprinttracker/columns/{cid}")
@app.delete("/api/kanban/columns/{cid}", include_in_schema=False)
def delete_column(cid: int):
    with _DB_LOCK:
        con = db()
        if con.execute("SELECT id FROM columns WHERE id=?", (cid,)).fetchone() is None:
            raise HTTPException(404, "column not found")
        fb = con.execute("SELECT id FROM columns ORDER BY id LIMIT 1").fetchone()
        fb = fb["id"] if fb else None
        with con:
            con.execute("UPDATE cards SET column_id=? WHERE column_id=?", (fb, cid))
            con.execute("DELETE FROM columns WHERE id=?", (cid,))
        con.close()
        return {"ok": True, "moved_cards_to": fb}

# ============================= /sprinttracker ===============================
@app.get("/kanban", include_in_schema=False)
def kanban_redirect():
    """Old bookmark / old admin-panel link. Keep it alive, point it at the new name."""
    return RedirectResponse("/sprinttracker", status_code=308)

@app.get("/sprinttracker", response_class=HTMLResponse)
def sprinttracker_page():
    body = open(os.path.join(HERE, "templates", "kanban.html")).read()
    extra = ('<input id="new-col" placeholder="New column" style="padding:6px 9px;border:1px solid var(--line);border-radius:8px;font:inherit;width:110px">'
             '<button onclick="addColumn()" style="padding:6px 12px;border:none;border-radius:8px;background:#0f766e;color:#fff;font-weight:600;cursor:pointer">+ Column</button>'
             '<button onclick="openModal(null)" style="padding:6px 12px;border:none;border-radius:8px;background:#0ea5e9;color:#fff;font-weight:600;cursor:pointer">+ Card</button>')
    return page("Sprint Tracker", "sprinttracker", body, extra)
