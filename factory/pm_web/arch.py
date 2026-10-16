"""Server-rendered architecture diagram (SVG), generated purely from JSON.

Layout contract (never overlap, always fill width, readable):
  * NCOLS wide cards chosen from the data; SVG viewBox fills the full page
    width (svg width:100%).
  * status chip on its OWN row below the title (never beside it),
  * every text block wrapped to the card inner width with a conservative
    char-width estimate; only max_lines are shown (ellipsized),
  * explicit line-height budget per block so rows can never collide,
  * the expandable "what's needed" panel reserves its own space BELOW the
    card so it never overlaps the card underneath.
Deterministic: same JSON => same SVG, byte for byte.
"""
import html
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "architecture.json")

STYLES = {
    "done":               {"label": "done",               "fg": "#15803d", "bg": "#dcfce7", "line": "#86efac"},
    "partial":            {"label": "in progress",        "fg": "#b45309", "bg": "#fef3c7", "line": "#fcd34d"},
    "not_started":        {"label": "not started",        "fg": "#475569", "bg": "#f1f5f9", "line": "#cbd5e1"},
    "resolved":           {"label": "resolved no code",   "fg": "#1d4ed8", "bg": "#dbeafe", "line": "#93c5fd"},
    "unknown":            {"label": "unknown",            "fg": "#475569", "bg": "#e2e8f0", "line": "#94a3b8", "dashed": True},
    "needs_confirmation": {"label": "needs confirm",      "fg": "#6d28d9", "bg": "#ede9fe", "line": "#c4b5fd"},
    "fork":               {"label": "needs a decision",   "fg": "#b91c1c", "bg": "#fee2e2", "line": "#fca5a5"},
    "decided":            {"label": "ALREADY DECIDED",    "fg": "#92400e", "bg": "#fef3c7", "line": "#fcd34d"},
}
FALLBACK = STYLES["not_started"]

# ---- roles: colour = what the thing IS (roles.json) ---------------------
try:
    _ROLESJ = json.load(open(os.path.join(HERE, "roles.json")))
except Exception:                                            # noqa: BLE001
    _ROLESJ = {"roles": {}}
ROLES = _ROLESJ.get("roles", {})
ROLE_ORDER = _ROLESJ.get("order", ["product", "factory", "frozen", "third-party",
                                    "host", "repo", "unlabelled"])
ROLE_FALLBACK = {"label": "WHAT IS THIS?", "fg": "#c2410c", "bg": "#ffedd5", "line": "#fdba74"}


def role_of_card(c):
    return ROLES.get(c.get("role") or "unlabelled", ROLE_FALLBACK)


def rolechip(x, y, r, align="left"):
    """Small pill for the role. x is the left edge, or the right edge if align=right."""
    tw = len(r["label"]) * 7.2 + 24
    left = x - tw if align == "right" else x
    out = (f'<rect x="{left:.0f}" y="{y}" width="{tw:.0f}" height="23" rx="11.5" '
           f'fill="{r["bg"]}" stroke="{r["fg"]}" stroke-width="1"/>')
    out += (f'<text x="{left+tw/2:.0f}" y="{y+16}" text-anchor="middle" font-family="{FONT}" '
            f'font-size="11.5" font-weight="700" fill="{r["fg"]}">{esc(r["label"])}</text>')
    return out


FONT = "Inter,-apple-system,&quot;Segoe UI&quot;,Roboto,Helvetica,Arial,sans-serif"

# ---- geometry (bigger fonts, full width) -------------------------------
NCOLS = 5
CARD_W = 308
# --- print mode: fewer, wider columns so the page is NOT shrunk below legibility ---
PRINT_COLS = 3
# on paper only the physical truth earns ink; the repo-hygiene scans stay on the screen page
PRINT_SECTIONS = ("topology", "er605", "machines", "equipment", "equipcfg",
                  "ports", "canonical", "decided", "rules", "notfound")
GAP = 16
PAD = 14
LEFT = 80
RIGHT = 44

# conservative px-per-char and line-height per font size (never overflow)
CHW = {22: 11.6, 18: 9.6, 16: 8.6, 15: 8.1, 14: 7.6, 13: 7.1, 12.5: 6.8, 12: 6.6, 11.5: 6.3, 11: 6.0, 10.5: 5.75}
LINE = {22: 30, 18: 26, 16: 23, 15: 21, 14: 20, 13: 18, 12.5: 17, 12: 17, 11.5: 16, 11: 15, 10.5: 14}


def esc(s):
    return html.escape(str(s), quote=True)


def wrap(text, width_px, size):
    m = max(6, int(width_px / CHW[size]))
    words = str(text).split()
    lines, cur = [], ""
    for w in words:
        if not cur:
            cur = w
        elif len(cur) + 1 + len(w) <= m:
            cur += " " + w
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def clipped(text, width_px, max_lines, size):
    """Wrap and ellipsize to at most max_lines."""
    lines = wrap(text, width_px, size)
    if len(lines) <= max_lines:
        return lines
    return lines[:max_lines - 1] + [lines[max_lines - 1][:-1] + "\u2026"]


def txt(x, y, s, size, fill, weight=500, anchor="start", italic=False):
    it = ' font-style="italic"' if italic else ""
    return (f'<text x="{x:.0f}" y="{y:.0f}" font-size="{size}" font-family="{FONT}" '
            f'font-weight="{weight}" fill="{fill}" text-anchor="{anchor}"{it}>{esc(s)}</text>')


SHADOW = (
    '<defs><filter id="soft" x="-10%" y="-8%" width="130%" height="140%">'
    '<feDropShadow dx="0" dy="2" stdDeviation="3" flood-color="#0f172a" flood-opacity="0.10"/>'
    '</filter></defs>'
)


def chip(x, y, label, st):
    tw = len(label) * 7.6 + 30
    dash = ' stroke-dasharray="4 3"' if st.get("dashed") else ""
    out = (f'<rect x="{x}" y="{y}" width="{tw}" height="24" rx="12" '
           f'fill="{st["bg"]}" stroke="{st["fg"]}"{dash}/>')
    out += (f'<text x="{x+tw/2}" y="{y+16.5}" text-anchor="middle" font-family="{FONT}" '
            f'font-size="13" font-weight="700" fill="{st["fg"]}">{esc(label)}</text>')
    return out


def render_card(c, x, y):
    st = STYLES.get(c.get("status", ""), FALLBACK)
    inner = CARD_W - 2 * PAD

    title = clipped(c.get("name", "?"), inner, 2, 16)
    desc_raw = (c.get("desc") or "").strip()
    desc = clipped(desc_raw, inner, 2, 13) if desc_raw else []
    note_raw = (c.get("note") or "").strip()
    note = clipped(note_raw, inner, 2, 12.5) if note_raw else []
    deps_raw = (c.get("deps") or "").strip()
    deps = clipped(deps_raw, inner, 1, 11.5) if deps_raw else []
    needed = c.get("needed") or []
    interactive = bool(needed) or bool(note_raw)

    # ---- explicit vertical budget ---------------------------------------
    ty = y + 30                          # first title baseline
    title_top = ty
    ty += len(title) * 23 + 6
    chip_top = ty + 4                    # chip on its own row
    ty += 40
    desc_top = ty
    ty += len(desc) * 18 + (8 if desc else 0)
    note_top = ty
    ty += len(note) * 17
    deps_top = ty
    ty += len(deps) * 16
    hint_top = ty
    ty += (21 if interactive else 0)
    card_h = ty - y + 14

    f = []
    f.append(f'<rect x="{x}" y="{y}" width="{CARD_W}" height="{card_h}" rx="10" '
             f'fill="#fff" stroke="#e2e8f0" stroke-width="1.3" filter="url(#soft)"/>')
    f.append(f'<rect x="{x+1}" y="{y+1}" width="{CARD_W-2}" height="6" rx="12" fill="{st["fg"]}" opacity="0.9"/>')
    for i, ln in enumerate(title):
        f.append(txt(x + PAD, title_top + i * 23, ln, 16, "#0f172a", 700))
    f.append(chip(x + PAD, chip_top, st["label"], st))
    rr = role_of_card(c)
    f.append(rolechip(x + CARD_W - PAD, chip_top, rr, align="right"))
    for i, ln in enumerate(desc):
        f.append(txt(x + PAD, desc_top + i * 18, ln, 13, "#475569", 400))
    for i, ln in enumerate(note):
        f.append(txt(x + PAD, note_top + i * 17, ln, 12.5, st["fg"], 550))
    for i, ln in enumerate(deps):
        f.append(txt(x + PAD, deps_top + i * 16, ln, 11.5, "#8b9ab3", 500, italic=True))
    if interactive:
        f.append(txt(x + CARD_W - PAD, hint_top, "\u25b8 details" if needed else "\u25b8 note",
                     13, "#0f766e", 700, anchor="end"))
    tip_lines = ["ROLE: " + rr["label"] + " - " + rr.get("why", "")]
    tip_lines += needed if needed else note
    tip = "\n".join(tip_lines)
    if tip:
        f.append(f'<title>{esc(tip)}</title>')
    body = "\n".join(f)

    detail_h = 0
    detail = ""
    if interactive:
        tips = ([wl for n in needed for wl in wrap(n, CARD_W - 2 * PAD, 13)]
                or note or [note_raw])[:8]
        dh = 30 + len(tips) * 19 + 12
        dy = y + card_h + 14
        d = [f'<g class="details" display="none">']
        d.append(f'<rect x="{x}" y="{dy}" width="{CARD_W}" height="{dh}" rx="9" '
                 f'fill="{st["bg"]}" stroke="{st["line"]}"/>')
        d.append(txt(x + PAD, dy + 26, "Details", 13, st["fg"], 700))
        t = dy + 50
        for wl in tips:
            d.append(txt(x + PAD + 8, t, "\u2022  " + wl, 13, "#334155", 400))
            t += 19
        d.append("</g>")
        detail = "\n".join(d)
        detail_h = dh

    cls = "card clickable" if interactive else "card static"
    out = ('<g class="%s" data-id="%s" data-role="%s">\n%s\n%s\n</g>'
           % (cls, esc(c.get("name","")), esc(rr["label"]), body, detail))
    reserve = card_h + (14 + detail_h if interactive else 0)
    return out, reserve


ROW_NOTE = ("A row is the same thing as a card, at a glance: name, state chip, role pill, one "
            "line of detail. Hover for everything the card used to print.")


def render_row(c, x, y):
    """One glanceable row. Same facts as render_card, none of the sprawl."""
    st = STYLES.get(c.get("status", ""), FALLBACK)
    rr = role_of_card(c)
    inner = CARD_W - 2 * PAD
    name = clipped(c.get("name", "?"), inner, 2, 12)
    dra = (c.get("desc") or c.get("note") or "").strip()
    desc = clipped(dra, inner, 1, 11.5) if dra else []
    h = 8 + len(name) * 16 + 4 + 24 + (19 if desc else 0) + 8
    f = [f'<rect x="{x}" y="{y}" width="{CARD_W}" height="{h}" rx="8" fill="#fff" '
         f'stroke="#e2e8f0" stroke-width="1.1"/>',
         f'<rect x="{x}" y="{y}" width="5" height="{h}" rx="2.5" fill="{st["fg"]}" opacity="0.85"/>']
    for i, ln in enumerate(name):
        f.append(txt(x + PAD, y + 16 + i * 16, ln, 12, "#0f172a", 700))
    cy = y + 8 + len(name) * 16 + 4
    f.append(chip(x + PAD, cy, st["label"], st))
    f.append(rolechip(x + CARD_W - PAD, cy + 1, rr, align="right"))
    if desc:
        f.append(txt(x + PAD, cy + 30, desc[0], 11.5, "#64748b", 400))
    tip = ["ROLE: " + rr["label"] + " - " + rr.get("why", ""), "state: " + st["label"]]
    tip += [c[k] for k in ("desc", "note", "deps") if c.get(k)]
    tip += list(c.get("needed") or [])
    f.append('<title>' + esc("\n".join(tip)) + '</title>')
    body = "\n".join(f)
    out = ('<g class="card static" data-id="%s" data-role="%s">\n%s\n</g>'
           % (esc(c.get("name", "")), esc(rr["label"]), body))
    return out, h + 10


def chunks(items, n):
    return [items[i:i + n] for i in range(0, len(items), n)]


def _load_devices():
    p = os.path.join(HERE, "..", "arch", "devices.json")
    try:
        with open(p) as fh:
            return json.load(fh)
    except Exception:
        return {"devices": [], "config": []}


def _load_er605():
    p = os.path.join(HERE, "..", "arch", "er605_live.json")
    try:
        with open(p) as fh:
            return json.load(fh)
    except Exception:
        return {}


def _live_status(rt):
    out = {}
    for ip, h in (rt.get("hosts") or {}).items():
        s = h.get("state")
        if s in ("up", "stale", "down"):
            out[ip] = s
    return out


def _inject(sections):
    """Kill the double-listings, then put the two equipment tables under Machines."""
    seen, out = set(), []
    for s in sections:
        if s.get("id") in ("decide", "decided"):
            out.append(s)
            continue
        comps = []
        for c in s.get("components", []):
            k = c.get("name", "")
            if k in seen:
                continue
            seen.add(k)
            comps.append(c)
        s = dict(s)
        s["components"] = comps
        out.append(s)
    dev = _load_devices()
    if dev.get("devices"):
        eq = {"id": "equipment",
              "name": "Equipment -- full inventory (%d devices)" % len(dev["devices"]),
              "tagline": "Every physical thing in the estate, in one place.",
              "layout": "table",
              "columns": [["id", "Device", 0.30], ["type", "Type", 0.08],
                          ["model", "Model / spec", 0.23], ["ip", "IP", 0.15],
                          ["link", "Link", 0.15], ["state", "State", 0.09]],
              "sub": "note",
              "components": dev["devices"]}
        cfg = {"id": "equipcfg",
               "name": "Equipment configuration -- who talks to what",
               "tagline": "Per device: what talks to it, what it serves, what runs on it.",
               "layout": "config",
               "components": dev["config"]}
        extra = [eq, cfg]
        nf = dev.get("not_found") or []
        if nf:
            extra.append({"id": "notfound",
                          "name": "Named in the spec but NOT FOUND in the building (%d)" % len(nf),
                          "tagline": "No probe can see these. Do not put them on a list again until someone has eyes on them.",
                          "layout": "table",
                          "columns": [["id", "Spec says this exists", 1.0]],
                          "components": [{"id": s} for s in nf]})
        pos = next((i for i, x in enumerate(out) if x.get("id") == "machines"), 0)
        out[pos + 1:pos + 1] = extra
    rt = _load_er605()
    topo = dev.get("topology")
    if topo:
        out.insert(0, {"id": "topology",
                       "name": "Network topology -- what plugs into what",
                       "tagline": "Gateway at the top, then the physical path down to every screen, printer and camera. "
                                  "The dot on each node is its LIVE state, read off the ER605 and a ping sweep.",
                       "layout": "topology", "topology": topo,
                       "status": _live_status(rt), "components": []})
    if rt and rt.get("ok"):
        names = [("dhcp_clients", "DHCP Client List -- who holds a lease right now"),
                 ("reservations", "Address Reservations -- the fixed map"),
                 ("mac_binding", "IP-MAC Binding"),
                 ("port_forward", "NAT / Port Forwarding"),
                 ("access_control", "Firewall -- Access Control"),
                 ("ip_groups", "IP Groups")]
        tbls = []
        for k, label in names:
            rows = (rt.get("tables") or {}).get(k) or []
            rows = [r for r in rows
                    if len(r) >= 2 and any((c or "").strip(" -") for c in r)]
            if rows:
                tbls.append([label, rows])
        if tbls:
            out.insert(1, {"id": "er605",
                           "name": "ER605 router at 192.168.2.1 -- LIVE read (%s)" % rt.get("iso", ""),
                           "tagline": "Read straight off the router by er605_live.py, refreshed every 5 minutes. "
                                      "%d hosts answering on the LAN right now. Read-only." % rt.get("online", 0),
                           "layout": "rawtables", "tables": tbls, "cols": 2, "components": []})
    return out


def render_config(sec, y, svg_w):
    """Per device: IP, what talks to it, what it serves, what runs on it. Wraps, never clips."""
    x0, W = LEFT, svg_w - LEFT - RIGHT
    out = []
    for i, c in enumerate(sec["components"]):
        bg = "#ffffff" if i % 2 == 0 else "#f1f5f9"
        rows = []
        for key, hdr in (("talks_to", "talked to by"), ("serves", "serves"),
                         ("runs", "runs")):
            v = c.get(key)
            if v:
                rows.append((hdr, clipped(str(v), W - 190, 2, 11.5)))
        rh = 18 + sum(15 * len(r) for _, r in rows) + 6
        out.append(f'<rect x="{x0}" y="{y}" width="{W:.0f}" height="{rh}" fill="{bg}"/>')
        out.append(txt(x0 + 6, y + 14, str(c.get("device", "")), 12, "#0f172a", 750))
        out.append(txt(x0 + 6 + 260, y + 14, str(c.get("ip", "")), 11.5, "#475569", 700))
        yy = y + 28
        for hdr, lines in rows:
            out.append(txt(x0 + 16, yy, hdr, 11, "#94a3b8", 700))
            for j, ln in enumerate(lines):
                out.append(txt(x0 + 176, yy + j * 15, ln, 11.5, "#334155", 400))
            yy += 15 * len(lines)
        out.append(f'<line x1="{x0}" y1="{y+rh}" x2="{x0+W:.0f}" y2="{y+rh}" stroke="#e2e8f0"/>')
        y += rh
    return out, y


def render_topology(sec, y, svg_w):
    """Layered physical topology: gateway on top, leaves below, live dot on every node."""
    t = sec.get("topology") or {}
    st = sec.get("status") or {}
    x0, W = LEFT, svg_w - LEFT - RIGHT
    out = []
    NW, NH, GX = 236, 46, 14
    per = max(1, int((W + GX) // (NW + GX)))
    wan = t.get("wan") or {}
    out.append(f'<rect x="{x0}" y="{y}" width="{W:.0f}" height="30" rx="9" fill="#0f172a"/>')
    out.append(txt(x0 + 12, y + 20, (wan.get("label") or "WAN")[:120], 13, "#f8fafc", 800))
    y += 38
    spine = x0 - 26
    ys = []
    for tier in t.get("tiers", []):
        ys.append(y + 11)
        out.append(f'<rect x="{x0}" y="{y}" width="{W:.0f}" height="22" rx="7" fill="#e9eef5" stroke="#cbd5e1"/>')
        out.append(txt(x0 + 12, y + 16, tier.get("label", ""), 12.5, "#334155", 800))
        y += 28
        for row in chunks(tier.get("nodes", []), per):
            for j, n in enumerate(row):
                nx = x0 + j * (NW + GX)
                s = n.get("state") or st.get(n.get("ip", ""), "unknown")
                col = {"up": "#15803d", "down": "#b91c1c", "stale": "#b45309"}.get(s, "#94a3b8")
                out.append(f'<rect x="{nx}" y="{y}" width="{NW}" height="{NH}" rx="9" fill="#ffffff" '
                           f'stroke="#cbd5e1" stroke-width="1.3"/>')
                out.append(f'<rect x="{nx}" y="{y}" width="5" height="{NH}" rx="2.5" fill="{col}"/>')
                out.append(f'<circle cx="{nx+NW-15}" cy="{y+14}" r="5" fill="{col}"/>')
                out.append(txt(nx + 14, y + 18, clipped(n.get("id", ""), NW - 44, 1, 12.5)[0],
                               12.5, "#0f172a", 700))
                sub = (n.get("ip", "") or "")
                if n.get("sub"):
                    sub = (sub + "  " + n["sub"]).strip()
                out.append(txt(nx + 14, y + 34, clipped(sub, NW - 24, 1, 10.5)[0], 10.5, "#475569", 400))
            y += NH + 12
        y += 5
    if ys:
        out.append(f'<line x1="{spine}" y1="{ys[0]}" x2="{spine}" y2="{ys[-1]}" stroke="#94a3b8" stroke-width="2"/>')
        for yy in ys:
            out.append(f'<line x1="{spine}" y1="{yy}" x2="{x0}" y2="{yy}" stroke="#94a3b8" stroke-width="1.5"/>')
            out.append(f'<circle cx="{spine}" cy="{yy}" r="4" fill="#64748b"/>')
    return out, y


def render_rawtables(sec, y, svg_w):
    """The router's own tables, verbatim. cols=2 lays the rows in two side-by-side columns
    (halves the section height); a long row wraps to a 2nd line instead of being cut."""
    x0, W = LEFT, svg_w - LEFT - RIGHT
    ncol = 2 if sec.get("cols") == 2 else 1
    gutter = 14 if ncol == 2 else 0
    cw = (W - gutter * (ncol - 1)) / ncol
    out = []

    def block(rows, x, yy):
        for i, r in enumerate(rows):
            bg = "#ffffff" if i % 2 == 0 else "#f1f5f9"
            line = "   ".join(str(c) for c in r)
            lines = clipped(line, cw - 12, 2, 10.5)
            rh = 17 if len(lines) <= 1 else 30
            out.append('<rect x="%.0f" y="%d" width="%.0f" height="%d" fill="%s"/>' % (x, yy, cw, rh, bg))
            for j, ln in enumerate(lines or [""]):
                out.append(txt(x + 6, yy + 12 + 13 * j, ln, 10.5,
                               "#0f172a" if i == 0 else "#334155", 700 if i == 0 else 400))
            yy += rh
        return yy

    for name, rows in sec.get("tables", []):
        if not rows:
            continue
        out.append(txt(x0, y + 13, "%s  (%d rows)" % (name, max(0, len(rows) - 1)),
                       12.5, "#0f172a", 800))
        y += 20
        if ncol == 1:
            y = block(rows, x0, y)
        else:
            half = (len(rows) + 1) // 2
            yl = block(rows[:half], x0, y)
            block(rows[half:], x0 + cw + gutter, y)
            y = yl
        y += 10
    return out, y


def render_table(sec, y, svg_w):
    """Dense two-line table: one row per device, detail line underneath, no cards."""
    cols = sec["columns"]
    subkey = sec.get("sub")
    x0, W = LEFT, svg_w - LEFT - RIGHT
    out = []
    out.append(f'<rect x="{x0}" y="{y}" width="{W:.0f}" height="22" rx="6" fill="#0f172a"/>')
    cx = x0
    for key, hdr, frac in cols:
        out.append(txt(cx + 7, y + 15, hdr, 11.5, "#f8fafc", 700))
        cx += W * frac
    y += 25
    for i, c in enumerate(sec["components"]):
        bg = "#ffffff" if i % 2 == 0 else "#f1f5f9"
        rh = 32 if (subkey and c.get(subkey)) else 19
        tip = "\n".join("%s: %s" % (hdr, c.get(key, "")) for key, hdr, frac in cols if c.get(key))
        out.append("<g><title>" + esc(tip) + "</title>")
        out.append(f'<rect x="{x0}" y="{y}" width="{W:.0f}" height="{rh}" fill="{bg}"/>')
        cx = x0
        for j, (key, hdr, frac) in enumerate(cols):
            cw = W * frac
            val = "" if c.get(key) in (None, "") else str(c.get(key))
            lines = clipped(val, cw - 14, 1, 11.5)
            if lines:
                out.append(txt(cx + 6, y + 14, lines[0], 11.5,
                               "#0f172a" if j == 0 else "#475569",
                               700 if j == 0 else 400))
            cx += cw
        if subkey and c.get(subkey):
            out.append(txt(x0 + 6, y + 27, clipped(str(c[subkey]), W - 16, 1, 11)[0],
                           11, "#64748b", 400))
        out.append(f'<line x1="{x0}" y1="{y+rh}" x2="{x0+W:.0f}" y2="{y+rh}" stroke="#e2e8f0"/>')
        out.append("</g>")
        y += rh
    return out, y


def render(print_mode=False):
    d = json.load(open(DATA))
    d["sections"] = _inject(d["sections"])
    if print_mode:
        d["sections"] = [sec for sec in d["sections"] if sec.get("id") in PRINT_SECTIONS]
    ncols = PRINT_COLS if print_mode else NCOLS
    svg_w = LEFT + ncols * CARD_W + (ncols - 1) * GAP + RIGHT
    y = 64 if print_mode else 44   # leave room for the paper header
    out = [SHADOW]
    meta = json.dumps(dict(kind="role-legend",
                           roles={k: v["label"] + " = " + v.get("why", "") for k, v in ROLES.items()},
                           unlabelled="WHAT IS THIS? = nobody has said what it belongs to",
                           order=ROLE_ORDER),
                      separators=(",", ":"))
    out.append("<metadata>" + html.escape(meta) + "</metadata>")

    # ---- legend ----
    out.append("<g>")
    lx = LEFT
    for st in STYLES.values():
        tw = len(st["label"]) * 7.8 + 34
        dash = ' stroke-dasharray="4 3"' if st.get("dashed") else ""
        out.append(f'<rect x="{lx}" y="{y}" width="{tw}" height="22" rx="11" fill="{st["bg"]}" stroke="{st["fg"]}"{dash}/>')
        out.append(f'<text x="{lx+tw/2}" y="{y+15.5}" text-anchor="middle" font-family="{FONT}" font-size="12.5" '
                   f'font-weight="700" fill="{st["fg"]}">{esc(st["label"])}</text>')
        lx += tw + 24
    out.append("</g>")
    # ---- role legend: colour = what the thing IS ----
    y += 26
    out.append(txt(LEFT, y + 15, "role:", 13, "#64748b", 700))
    lx = LEFT + 46
    for r in list(ROLES.values()) + [ROLE_FALLBACK]:
        tw = len(r["label"]) * 7.2 + 26
        out.append(f'<rect x="{lx:.0f}" y="{y}" width="{tw:.0f}" height="22" rx="11" '
                   f'fill="{r["bg"]}" stroke="{r["fg"]}"/>')
        out.append(f'<text x="{lx+tw/2:.0f}" y="{y+15.5}" text-anchor="middle" font-family="{FONT}" '
                   f'font-size="11.5" font-weight="700" fill="{r["fg"]}">{esc(r["label"])}</text>')
        lx += tw + 16
    y += 56

    # ---- FRONT DOOR: one screen, read before anything else ------------------
    counts = (d.get("roles") or {}).get("counts", {})
    dec = next((s for s in d["sections"] if s["id"] == "decide"), None)
    don = next((s for s in d["sections"] if s["id"] == "decided"), None)
    items = [(c.get("name", ""), (c.get("note") or "").replace("decide: ", ""))
             for c in (dec["components"] if dec else [])
             if c.get("status") == "fork"]
    ruled = [(c.get("name", ""), (c.get("note") or ""))
             for c in (don["components"] if don else [])]
    tally = " \u00b7 ".join("%s %d" % (ROLES[k]["label"], counts.get(k, 0))
                            for k in ROLE_ORDER if counts.get(k))
    import re as _re
    def _nm(x):
        return x["name"] if _re.search(r"\(\d", x["name"]) else \
            "%s (%d)" % (x["name"], len(x["components"]))
    nav = ("Jump to: " + " \u00b7 ".join(_nm(x) for x in d["sections"])
           + "     |     Rules, and where to put things: README-FIRST.md in the repo root")
    if items:
        needline = ("%d item(s) need YOUR decision -- red, below, each with the action that closes "
                    "it." % len(items), 13, "#b91c1c", 700)
    else:
        needline = ("Nothing is waiting on your decision. Every item the scan has flagged has "
                    "already been ruled on.", 13, "#15803d", 700)
    ruledline = ("%d already decided -- the action is still outstanding, in amber below." % len(ruled),
                 13, "#92400e", 700)
    front = [
        ("READ THIS FIRST", 18, "#0f172a", 800),
        ("Everything here was read off the two machines by arch_scan.py, hourly. Nothing is "
         "hand-written, so it cannot drift from reality. It is read-only.", 13, "#475569", 400),
        ("Colour = what a thing IS; chip on the left = its state.   " + tally, 13, "#475569", 600),
        ("Where things go: the one repo holds product/ (what runs - markdown and any file type are "
         "fine there) and factory/ (what builds and operates it - README-FIRST.md is the ONLY .md "
         "allowed in the factory). Prototypes live on gflip and move to n100 once wired and "
         "automated. Everything below is grouped by what it IS.", 13, "#475569", 400),
        ("The rules door, read-only, whitelist:  LAN http://192.168.2.107:8099/   |   tailnet "
         "http://100.65.71.49:8099/  --  README-FIRST.md, roles.json, architecture.json  (tailnet only; the public name was deleted 2026-10-15, D137)",
         12.5, "#0f766e", 600),
        needline,
        ruledline,
        (nav[:300], 12, "#0f766e", 600),
    ]
    FRONT_W = 1300
    flines = [(ln, sz, col, wt) for line, sz, col, wt in front
              for ln in wrap(line, FRONT_W, sz)]
    ph = 16 + sum(19 + (3 if sz > 15 else 0) for _t, sz, _c, _w in flines) \
         + 8 + (len(items) + len(ruled)) * 17 + 14
    out.append(f'<rect x="{LEFT-8}" y="{y-10}" width="{svg_w-LEFT-RIGHT+16}" height="{ph}" rx="12" '
               f'fill="#f8fafc" stroke="#94a3b8" stroke-width="1.4"/>')
    ty = y + 12
    for line, sz, col, wt in flines:
        out.append(txt(LEFT + 8, ty, line, sz, col, wt))
        ty += 19 + (3 if sz > 15 else 0)
    ty += 8
    for nm, act in items + ruled:
        red = (nm, act) in items
        out.append(txt(LEFT + 10, ty, "\u2022 " + nm[:64], 12.5,
                       "#b91c1c" if red else "#92400e", 700))
        out.append(txt(LEFT + 450, ty, (act or "")[:138], 12.5,
                       "#7f1d1d" if red else "#78350f", 400))
        ty += 17
    y += ph + 30

    for sec in d["sections"]:
        out.append(f'<g id="sec-{esc(sec["id"])}">')
        out.append(txt(LEFT, y + 17, sec["name"], 19, "#0f172a", 750))
        y += 27
        out.append(f'<line x1="{LEFT}" y1="{y}" x2="{svg_w-RIGHT}" y2="{y}" stroke="#e2e8f0" stroke-width="2"/>')
        y += 16
        if sec.get("layout") == "topology":
            frags, y = render_topology(sec, y + 6, svg_w)
            out.extend(frags)
            y += 14
            out.append("</g>")
            y += 16
        if sec.get("layout") == "rawtables":
            frags, y = render_rawtables(sec, y + 6, svg_w)
            out.extend(frags)
            y += 14
            out.append("</g>")
            y += 16
        if sec.get("layout") == "config":
            frags, y = render_config(sec, y + 6, svg_w)
            out.extend(frags)
            y += 14
            out.append("</g>")
            y += 16
            continue
        if sec.get("layout") == "table":
            frags, y = render_table(sec, y + 6, svg_w)
            out.extend(frags)
            y += 14
            out.append("</g>")
            y += 16
            continue
        dense = sec["id"] not in ("decide", "decided")
        groups = []
        for comp in sec["components"]:
            g = comp.get("group") or comp.get("role") or "unlabelled"
            if not groups or groups[-1][0] != g:
                groups.append([g, []])
            groups[-1][1].append(comp)
        for g, comps in groups:
            rr = ROLES.get(g, ROLE_FALLBACK)
            out.append(f'<rect x="{LEFT}" y="{y}" width="{svg_w-LEFT-RIGHT}" height="20" rx="7" '
                       f'fill="{rr["bg"]}" stroke="{rr["fg"]}" stroke-width="1.5"/>')
            out.append(txt(LEFT + 16, y + 17, "%s   \u00b7   %d" % (rr["label"], len(comps)),
                           12.5, rr["fg"], 800))
            y += 27
            for row in chunks(comps, ncols):
                row_h = 0
                frags = []
                for j, comp in enumerate(row):
                    x = LEFT + j * (CARD_W + GAP)
                    fr, rh = (render_row if dense else render_card)(comp, x, y)
                    frags.append(fr)
                    row_h = max(row_h, rh)
                out.extend(frags)
                y += row_h + (3 if dense else 14)
            y += 4
        out.append("</g>")
        y += 16

    svg_h = y + 12
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {svg_w:.0f} {svg_h:.0f}" '
           f'role="img" preserveAspectRatio="xMidYMid meet" '
           f'style="width:100%;height:auto;font-family:{FONT};display:block">\n'
           + "\n".join(out) + "\n</svg>")
    return d, svg
