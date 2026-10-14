#!/usr/bin/env python3
"""
Renders the checklist in the layout of Nick's "Catering Orders checklist" sheet.

That sheet is a GRID, not prose:
  header fields across the top (customer / address / phone / drive time / leave at /
  guests / event date+time / arrival time / service choice), then ONE table whose first
  column is FOODS and whose remaining eight columns are the prep states:
      Purchased | Par-prepped | Fully prepped | Par-cooked | Cooked |
      Transit container | Temp @ K9 | Temp onsite
  Equipment and utensil lines are ordinary rows in that same table, with "Yes" in the
  Purchased column when the kit is needed. Foods follow underneath.

READABILITY (Nick, 2026-10-09): this is a paper sheet that gets written on by hand in a
kitchen, so it is tuned for legibility over density --
  * 21pt rows, tall enough for a pen tick
  * 10pt food names, 9.2pt kit lines, section rows in bold on grey
  * zebra striping on the food rows so the eye tracks across all eight columns
  * headers centred in their columns and wrapping onto two lines
  * margin ruled off, so the food column never touches the tick boxes
Landscape US Letter, base-14 fonts, no dependencies.
"""
W, H = 792.0, 612.0
M = 26.0

# column widths (points). FOODS carries the words; the rest are tick boxes.
COLS = [("FOODS", 306.0),
        ("Purch-\nased", 54.0),
        ("Par-\nprepped", 58.0),
        ("Fully\nprepped", 62.0),
        ("Par-\ncooked", 54.0),
        ("Cooked", 52.0),
        ("Transit\ncontainer", 62.0),
        ("Temp\n@ K9", 44.0),
        ("Temp\nonsite", 48.0)]

RH = {"sec": 20.0, "yes": 22.0, "item": 21.0, "food": 22.0}

SECT = 0.87      # section fill
ZEBRA = 0.955    # alternating food-row fill
BODY = 9.2       # kit-line type
FOOD = 10.2      # food-name type
HEAD = 7.9       # column header type


def esc(s):
    return str(s).replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")


def tw(s, size, bold=False):
    """Approximate Helvetica advance width, good enough for centring."""
    per = 0.556 if bold else 0.5
    wide = sum(1 for c in s if c in "MWmw@%")
    return size * (per * len(s) + 0.06 * wide)


class Sheet:
    def __init__(self):
        self.ops = []

    def text(self, x, y, s, bold=False, size=9.0, gray=0.0):
        self.ops.append("BT /%s %.2f Tf %.2f g 1 0 0 1 %.2f %.2f Tm (%s) Tj ET"
                        % ("F2" if bold else "F1", size, gray, x, H - y, esc(s)))

    def text_c(self, x, w, y, s, bold=False, size=9.0, gray=0.0):
        self.text(x + max(2.0, (w - tw(s, size, bold)) / 2.0), y, s, bold, size, gray)

    def text_r(self, x, w, y, s, bold=False, size=9.0, gray=0.0):
        self.text(x + w - 3.0 - tw(s, size, bold), y, s, bold, size, gray)

    def line(self, x1, y1, x2, y2, w=0.5, gray=0.0):
        self.ops.append("%.2f g %.2f w %.2f %.2f m %.2f %.2f l S"
                        % (gray, w, x1, H - y1, x2, H - y2))

    def cell(self, x, y, w, h, fill=None, rule=0.45, gray=0.0):
        if fill is not None:
            self.ops.append("%.3f g %.2f %.2f %.2f %.2f re f %.2f g"
                            % (fill, x, H - y - h, w, h, gray))
        self.ops.append("%.2f g %.2f w %.2f %.2f %.2f %.2f re S"
                        % (gray, rule, x, H - y - h, w, h))

    def band(self, x, y, w, h, fill):
        self.ops.append("%.3f g %.2f %.2f %.2f %.2f re f 0 g"
                        % (fill, x, H - y - h, w, h))


def header_block(sh, ev, y):
    d = ev["date"]
    dt = "%s %d/%d" % (d.strftime("%a"), d.month, d.day)
    sh.text(M, y, "CATERING ORDER CHECKLIST", bold=True, size=11.5)
    sh.text_r(M, 306.0, y, "printed %s" % ev.get("printed", ""), size=7.2, gray=0.45)
    y += 16
    sh.text(M, y, "Customer Name:  %s" % ev["customer"], bold=True, size=11)
    sh.text(410, y, "Phone:  %s" % (ev["phone"] or "____________"), size=9.6)
    sh.text_r(430, W - M - 430, y, "Drive time in min: __________", size=9.6)
    y += 19
    sh.text(M, y, "Customer Address:  %s" % (ev["f"].get("address") or "____________________"),
            bold=True, size=11)
    g = (ev.get("f") or {}).get("guests") or ""
    if not g:
        gt = str(ev.get("guests_txt") or "")
        g = gt.split()[0] if gt and not gt.upper().startswith("FLAG") else ""
    sh.text_r(430, W - M - 430, y, "# guests:  %s" % (g or "______"), bold=True, size=11)
    y += 19
    sh.text(M, y, "EVENT DATE & TIME:  %s @ %s" % (dt, ev["f"].get("start") or "--"),
            bold=True, size=11)
    sh.text(330, y, "ARRIVAL TIME:  %s" % (ev["f"].get("arrival") or "--"), bold=True, size=11)
    sh.text_r(560, W - M - 560, y, "Leave at: __________", size=9.6)
    y += 19
    sh.text(M, y, "Service:     (   )  Drop off        (   )  Setup        (   )  Full Serve"
                  "                    circle one", size=10)
    y += 7
    sh.line(M, y, W - M, y, 1.0)
    return y + 9


def table_header(sh, y):
    rh = 24.0
    x = M
    for label, w in COLS:
        sh.cell(x, y, w, rh, fill=0.87)
        lines = label.split("\n")
        ty = y + (rh - len(lines) * 9.2) / 2 + 8.0
        for ln in lines:
            sh.text_c(x, w, ty, ln, bold=True, size=HEAD)
            ty += 9.2
        x += w
    return y + rh


def row(sh, y, kind, label):
    rh = RH[kind]
    if kind == "sec":
        fill, size, bold = SECT, 9.6, True
    elif kind == "food":
        fill, size, bold = ZEBRA, FOOD, False
    else:
        fill, size, bold = None, BODY, False
    x = M
    for i, (_, w) in enumerate(COLS):
        sh.cell(x, y, w, rh, fill=fill if i == 0 or kind == "food" else None)
        if i == 0:
            sh.text(x + 6, y + rh / 2 + size * 0.36, label, bold=bold, size=size)
        elif i == 1 and kind == "yes":
            sh.text_c(x, w, y + rh / 2 + size * 0.36, "Yes", bold=True, size=size)
        x += w
    return y + rh


def build_rows(ev):
    """Row list in Nick's sheet order: equipment, serving kit, then FOODS."""
    note = (ev["notes"] or "").lower()
    hot = ev["hot_service"]
    rows = [("sec", "EQUIPMENT NEEDED:")]
    if hot:
        rows.append(("item", "Hot box + rubber bladders 4-6L near-boiling (95C)"))
    if "heating pad" in note or "flameless" in note:
        rows.append(("item", "Flameless heating pads (water-activated)  ____________"))
    elif hot:
        rows.append(("item", "Sternos  ____________"))
        rows.append(("item", "Chafing 1 big w/_____ pans for  __________________"))
        rows.append(("item", "Chafing 1 big w/_____ pans for  __________________"))
    if "linen" in note and "host" in note:
        rows.append(("item", "Display on host's table / countertop / 6' buffet  (linen by host)"))
    else:
        rows.append(("item", "Buffet tables (_____),  Fitted linens (_____)"))
    rows.append(("yes", "SERVING UTENSILS NEEDED: REAL"))
    rows.append(("item", "LG tongs: ______      SM tongs: ______"))
    rows.append(("item", "LG spoons: ______     SM spoons: ______"))
    rows.append(("yes", "ROLLED PLASTICWARE NEEDED: ____________"))
    rows.append(("item", "PLATES NEEDED:   ______ SM        ______ LG"))
    rows.append(("yes", "______ BAR NAPKINS         ______ BUFFET NAPKINS"))
    rows.append(("yes", "Signs __PRINTED___"))
    rows.append(("sec", "FOODS   (SUPPLIES ON NEXT PAGE)"))
    for it in ev["items"]:
        if it.get("food"):
            rows.append(("food", it["name"].replace("Catering ", "")))
    return rows


def render(ev, footer_lines=()):
    pages = []
    sh = Sheet()
    y = header_block(sh, ev, 36)
    y = table_header(sh, y)
    for kind, label in build_rows(ev):
        rh = RH[kind]
        if y + rh > H - 44:                       # start a fresh sheet
            pages.append(sh)
            sh = Sheet()
            y = header_block(sh, ev, 36)
            y = table_header(sh, y)
        y = row(sh, y, kind, label)
        if kind == "sec":
            sh.line(M, y, W - M, y, 0.9)

    fy = H - 32
    sh.line(M, fy - 10, W - M, fy - 10, 0.7, gray=0.5)
    sh.text(M, fy, "Notes, flags and sources are on sheet 2.", size=8.4, gray=0.3)
    n = len(pages) + 1
    sh.text_r(M, W - 2 * M, fy, "Sheet %d of %d" % (n, n + 1), size=8.4, gray=0.3)
    pages.append(sh)
    pages.append(notes_sheet(ev))
    return _pdf(pages)


# ---------------------------------------------------------------- prose
def wrap_pt(text, width_pt, size, bold=False):
    """Wrap to a measured width (points), not a character count."""
    words, lines, cur = str(text).split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if tw(t, size, bold) <= width_pt:
            cur = t
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def para(sh, x, y, text, size=10.2, leading=15.4, width=None, bold=False,
         bullet=None, gray=0.05):
    """A hanging-indent paragraph. Returns the next y."""
    width = width or (W - 2 * M)
    bx = x
    if bullet:
        sh.text(x, y, bullet, bold=True, size=size)
        bx = x + 13.0
        width -= 13.0
    for ln in wrap_pt(text, width, size, bold):
        sh.text(bx, y, ln, bold=bold, size=size, gray=gray)
        y += leading
    return y


def notes_sheet(ev):
    """Page 2: the prose. Deliberately roomy - 10.2pt, wide leading, plain words."""
    sh = Sheet()
    y = 46
    sh.text(M, y, "NOTES", bold=True, size=15)
    y += 8
    sh.line(M, y, W - M, y, 1.2)
    y += 20

    g = (ev.get("f") or {}).get("guests") or ev.get("guests_txt") or ""
    dd = ev.get("date")
    when = dd.strftime("%a %d %b %Y") if hasattr(dd, "strftime") else str(dd)
    sub = "%s   -   %s   -   %s guests   -   %s" % (
        ev.get("customer", ""), when, g if str(g)[:1].isdigit() else "",
        ev.get("service", "").split("[")[0].strip())
    sh.text(M, y, sub, size=10.5, gray=0.2)
    y += 26

    for title, lines in ev.get("flag_groups", []):
        if not lines:
            continue
        sh.text(M, y, title, bold=True, size=11.5)
        y += 5
        sh.line(M, y, W - M, y, 0.6, gray=0.55)
        y += 16
        for ln in lines:
            y = para(sh, M + 6, y, ln, size=10.2, leading=15.4,
                     width=W - 2 * M - 20, bullet="-")
            y += 5
        y += 14
        if y > H - 150:                      # start a fresh notes page if needed
            sh.line(M, y, W - M, y, 0.4, gray=0.7)
            y += 18

    sh.text(M, y, "HOW THIS SHEET WAS MADE", bold=True, size=11.5)
    y += 5
    sh.line(M, y, W - M, y, 0.6, gray=0.55)
    y += 16
    y = para(sh, M + 6, y, "Built from the Square order for this job plus the written procedures "
             "in the Taza kitchen knowledge base. Only locked procedures were used - nothing was "
             "invented and no quantity was guessed.", size=10.2, leading=15.4, width=W - 2 * M - 20)
    y += 10
    y = para(sh, M + 6, y, "Procedures applied: " + ", ".join(ev.get("rules", [])) + ".",
             size=10.2, leading=15.4, width=W - 2 * M - 20)
    y += 10
    y = para(sh, M + 6, y, "Generated " + str(ev.get("printed", "")) +
             " by checklist_bootstrap.py. Questions: Nick or Sandra.", size=10.2, leading=15.4,
             width=W - 2 * M - 20)
    sh.text_r(M, W - 2 * M, H - 34, "Sheet 2", size=8.2, gray=0.42)
    return sh


# ------------------------------------------------------------------ minimal PDF
def _pdf(pages):
    n = len(pages)
    f1, f2 = 3 + n * 2, 4 + n * 2
    objs, kids = [], []
    for i, p in enumerate(pages):
        pg, ct = 3 + i * 2, 4 + i * 2
        kids.append(pg)
        c = "\n".join(p.ops).encode()
        objs.append((pg, ("<< /Type /Page /Parent 2 0 R /MediaBox [0 0 %.0f %.0f] "
                          "/Resources << /Font << /F1 %d 0 R /F2 %d 0 R >> >> /Contents %d 0 R >>"
                          % (W, H, f1, f2, ct)).encode()))
        objs.append((ct, ("<< /Length %d >>\nstream\n" % len(c)).encode() + c + b"\nendstream"))
    objs.insert(0, (2, ("<< /Type /Pages /Kids [%s] /Count %d >>"
                        % (" ".join("%d 0 R" % k for k in kids), n)).encode()))
    objs.insert(0, (1, b"<< /Type /Catalog /Pages 2 0 R >>"))
    objs.append((f1, b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"))
    objs.append((f2, b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>"))
    objs.sort(key=lambda kv: kv[0])
    out, off = bytearray(b"%PDF-1.4\n"), {}
    for num, body in objs:
        off[num] = len(out)
        out += ("%d 0 obj\n" % num).encode() + body + b"\nendobj\n"
    top = max(off) + 1
    xref = len(out)
    out += ("xref\n0 %d\n" % top).encode() + b"0000000000 65535 f \n"
    for i in range(1, top):
        out += (("%010d 00000 n \n" % off[i]) if i in off else "0000000000 65535 f \n").encode()
    out += ("trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (top, xref)).encode()
    return bytes(out)
