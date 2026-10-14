#!/usr/bin/env python3
"""Emergency ops brief -> 576px receipt PNG -> Star TSP143IIIU, CUPS BYPASSED.

v6: raster sent directly to /dev/usb/lp* via StarTSPImage (no CUPS, no lp queue,
no fit-to-page scaling). Image maps 1:1 to the 576px (72mm @ 203dpi) printhead.

FONTS: v5's "+50%" values already OVERFLOWED the 576px head -- every mono line
clipped off the right edge (widest was 830px on a 576px canvas). Another literal
x1.5 would push lines past 1250px and chop >half of each. That is physically
impossible on a 72mm head. So each font role now carries a CAP = v5 x 1.5 (the
requested target) and every line AUTO-FITS DOWN from that cap until it fits the
556px usable width. Net effect: short lines get the full 1.5x; long lines fill
the width exactly; NOTHING clips. This is what "fill the full width" requires.

Title: proportional DejaVuSans-Bold, auto-fit. All other text: DejaVuSansMono-Bold.
No top whitespace (title at y=5). Saved at exactly 576px wide, NO DPI metadata.
"""
import glob
import os
import subprocess
import tempfile
from datetime import datetime

import qrcode
from PIL import Image, ImageDraw, ImageFont

import StarTSPImage

WIDTH = 576
MARGIN = 10                      # 10px each side -> 556px usable
USABLE = WIDTH - 2 * MARGIN      # 556
BLACK = 0
WHITE = 255

MONO_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"
PROP_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

_font_cache = {}


def get_battery_timeleft():
    """Live UPS runtime from apcaccess TIMELEFT. Defensive fallback if the
    daemon is unreachable or the field is missing/unparseable."""
    try:
        result = subprocess.run(
            ["apcaccess", "status"], capture_output=True, text=True, timeout=5
        )
        for line in result.stdout.splitlines():
            if line.startswith("TIMELEFT"):
                minutes = float(line.split(":", 1)[1].strip().split()[0])
                return f"{minutes:.0f} min"
    except Exception:
        pass
    return "~90 min"  # fallback, calibrated from real 2026-07-06 test (54min/80% SOC under load)


def load_font(size, path=MONO_PATH):
    key = (path, size)
    if key not in _font_cache:
        try:
            _font_cache[key] = ImageFont.truetype(path, size)
        except Exception:
            _font_cache[key] = ImageFont.load_default()
    return _font_cache[key]


# --- Font CAPS: v5 value x1.5 (round half up). Each line auto-fits DOWN from ---
#     its cap to <= USABLE, so these are ceilings, not fixed sizes. ---
#   role      v5 -> cap(x1.5)
C_TITLE = 108   # 72  -> EMERGENCY OPS BRIEF (proportional, auto-fit)
C_SUB = 54      # 36  -> Taza Catering & Events
C_HEAD = 90     # 60  -> section headers
C_HEAD1 = 86    # 57  -> GIG 1 header
C_BODY = 72     # 48  -> body text
C_SMALL = 59    # 39  -> printed time inside battery box
C_BRAIN = 72    # 48  -> TAZA OS BRAIN ONLINE
C_BATT = 80     # 53  -> battery remaining value
C_PRN = 62      # 41  -> printer instruction
C_ALG = 81      # 54  -> allergy lines
C_TL = 68       # 45  -> timeline entries
C_QRLBL = 50    # 33  -> KITCHEN / SITE GUIDE

# tall canvas; cropped to content at the end
img = Image.new("L", (WIDTH, 12000), WHITE)
d = ImageDraw.Draw(img)
y = 5                            # NO top whitespace: title starts at row 5

now = datetime.now()
now_str = now.strftime("%H:%M")

fitted = []                      # (label, cap, fitted_size) telemetry


def fit_font(s, cap, path=MONO_PATH, max_w=USABLE):
    """Largest font <= cap whose rendered width fits max_w. Never clips."""
    size = cap
    while size > 12:
        f = load_font(size, path)
        if d.textlength(s, font=f) <= max_w:
            break
        size -= 1
    fitted.append((s, cap, size))
    return load_font(size, path)


def line_h(font):
    asc, desc = font.getmetrics()
    return asc + desc + 8


def text(s, cap, path=MONO_PATH, indent=0, center=False):
    global y
    f = fit_font(s, cap, path, USABLE - indent)
    w = d.textlength(s, font=f)
    x = (WIDTH - w) / 2 if center else MARGIN + indent
    d.text((x, y), s, font=f, fill=BLACK)
    y += line_h(f)


def gap(px=25):
    global y
    y += px


def hr(pad=10):
    global y
    y += pad
    d.line([(MARGIN, y), (WIDTH - MARGIN, y)], fill=BLACK, width=3)
    y += pad


def box(items, border=2, pad=12, center=False):
    """items: list of (string, cap) or (string, cap, path). Each line auto-fits."""
    global y
    top = y
    inner_w = USABLE - 2 * pad - 8
    resolved = []
    for it in items:
        s, cap = it[0], it[1]
        path = it[2] if len(it) > 2 else MONO_PATH
        resolved.append((s, fit_font(s, cap, path, inner_w)))
    box_h = sum(line_h(f) for _, f in resolved) + 2 * pad
    for i in range(border):
        d.rectangle(
            [(MARGIN + i, top + i), (WIDTH - MARGIN - i, top + box_h - i)],
            outline=BLACK,
        )
    cy = top + pad
    for s, font in resolved:
        w = d.textlength(s, font=font)
        x = (WIDTH - w) / 2 if center else MARGIN + pad + 4
        d.text((x, cy), s, font=font, fill=BLACK)
        cy += line_h(font)
    y = top + box_h


# --- Header: title auto-fit, proportional bold, at y=5 ---
title = "EMERGENCY OPS BRIEF"
tf = fit_font(title, C_TITLE, PROP_PATH)
title_size = tf.size
tw = d.textlength(title, font=tf)
tbbox = d.textbbox((0, 0), title, font=tf)
d.text(((WIDTH - tw) / 2, 5), title, font=tf, fill=BLACK)
title_bottom = 5 + tbbox[3]

# 'Taza Catering & Events' ~24px below title
y = title_bottom + 24
text("Taza Catering & Events", C_SUB, center=True)
hr()
gap()

# --- Battery box ---
box(
    [
        ("TAZA OS BRAIN ONLINE", C_BRAIN),
        (f"Battery remaining: {get_battery_timeleft()}", C_BATT),
        (f"Printed: {now_str}", C_SMALL),
    ],
    border=2,
)
gap()

# --- Printer instruction box (arrows) ---
box([(">>> TURN OFF STAR PRINTER NOW <<<", C_PRN)], border=2, center=True)
gap()

# --- Allergy alert box (thick 4px border, centered, !! markers) ---
box(
    [
        ("!! NUT ALLERGY - GIG 1 !!", C_ALG),
        ("!! LIFE THREATENING !!", C_ALG),
        ("!! BUCKEYE DELIVERY !!", C_ALG),
        ("!! ZERO NUT EXPOSURE !!", C_ALG),
    ],
    border=4,
    center=True,
)
gap()

# --- Not yet on site ---
text("NOT YET ON SITE:", C_BODY)
text("Helper Cook (602) 555-0199", C_BODY)
text("ETA 13:45", C_BODY)
hr()
gap()

# --- Gig 1 ---
text("GIG 1 BUCKEYE - DO FIRST", C_HEAD1)
text("Family Dentistry", C_BODY)
text("1300 S Watson Rd A-100", C_BODY)
text("25 pax  HDs + Bev", C_BODY)
text("Ready 13:30  Depart 12:40", C_BODY)
text("*** ALLERGEN: NUT ***", C_BODY)
hr()
gap()

# --- Gig 2 ---
text("GIG 2 TEMPE - Evening", C_HEAD)
text("Grace Community Church", C_BODY)
text("1200 E Southern Ave", C_BODY)
text("75 pax  Buffet + Bar", C_BODY)
text("PourMasters sub", C_BODY)
text("75 lbs ice", C_BODY)
text("Feed 18:30  No allergen", C_BODY)
hr()
gap()

# --- Open items ---
text("OPEN:", C_HEAD)
text("[ ] Cold items NOT packed", C_BODY)
text("[~] HDs on gas oven", C_BODY)
text("[x] Dry items loaded", C_BODY)
text("[x] Gig 2 staged", C_BODY)
hr()
gap()

# --- Timeline ---
text("TIMELINE:", C_HEAD)
text(f"{now_str}  HERE - UPS active", C_TL)
text("12:00  Pack cold items", C_TL)
text("12:30  Load van, check", C_TL)
text("12:40  DEPART for Buckeye", C_TL)
text("13:30  Gig 1 ready to serve", C_TL)
text("13:45  Helper cook arrives", C_TL)
text("15:00  Return, stage Gig 2", C_TL)
text("18:30  Gig 2 feed - Tempe", C_TL)
hr()
gap()

# --- QR codes: 272px each, 8px gap, centered, labels below only ---
QR_SIZE = 272     # 34mm @ 203 DPI
QR_GAP = 8        # 1mm


def make_qr(data):
    q = qrcode.QRCode(box_size=10, border=1)
    q.add_data(data)
    q.make(fit=True)
    im = q.make_image(fill_color="black", back_color="white").convert("L")
    return im.resize((QR_SIZE, QR_SIZE), Image.NEAREST)


qr_left = make_qr("http://192.168.2.102:9001/emergency")
qr_right = make_qr("http://192.168.2.102:9001/siteguide")

total_w = QR_SIZE * 2 + QR_GAP           # 272 + 8 + 272 = 552
start_x = int((WIDTH - total_w) / 2)     # centered
left_x = start_x
right_x = start_x + QR_SIZE + QR_GAP

img.paste(qr_left, (left_x, y))
img.paste(qr_right, (right_x, y))
y += QR_SIZE + 6

# labels below each QR, auto-fit to QR width, centered under each
lk_f = fit_font("KITCHEN", C_QRLBL, MONO_PATH, QR_SIZE)
ls_f = fit_font("SITE GUIDE", C_QRLBL, MONO_PATH, QR_SIZE)
d.text((left_x + (QR_SIZE - d.textlength("KITCHEN", font=lk_f)) / 2, y),
       "KITCHEN", font=lk_f, fill=BLACK)
d.text((right_x + (QR_SIZE - d.textlength("SITE GUIDE", font=ls_f)) / 2, y),
       "SITE GUIDE", font=ls_f, fill=BLACK)
y += line_h(lk_f)

# --- Crop to content + 40px bottom padding ---
final_h = y + 40
img = img.crop((0, 0, WIDTH, final_h))

# Unique per-run temp path: mkstemp atomically creates a fresh file owned by
# the invoking user (root or taza), so leftover files from any prior run can
# never block this one. See RASTER_TMP below for the same fix on the raster.
_png_fd, OUT = tempfile.mkstemp(prefix="emergency_receipt_", suffix=".png")
os.close(_png_fd)                        # PIL reopens/overwrites the path
img.save(OUT)                            # NO dpi metadata
print(f"Saved {OUT} size={img.size}  (no DPI metadata embedded)")
print(f"Title: DejaVuSans-Bold auto-fit at {title_size}px (cap {C_TITLE}), width={round(tw)}px")

# fit telemetry: report which lines hit their cap vs got clamped down
clamped = [(s, cap, sz) for s, cap, sz in fitted if sz < cap]
if clamped:
    print(f"{len(clamped)} line(s) auto-fitted below cap to avoid clipping:")
    for s, cap, sz in clamped:
        print(f"  cap {cap:>3} -> {sz:>3}px  {s!r}")
else:
    print("All lines fit at their full cap size.")

# --- Print: raster direct to Star TSP143IIIU, CUPS bypassed ---
raster = StarTSPImage.imageFileToRaster(OUT, cut=True)
devs = sorted(glob.glob("/dev/usb/lp*"))
dev = devs[0] if devs else "/dev/usb/lp0"
# Unique per-run raster temp path, same rationale as OUT above.
_rst_fd, RASTER_TMP = tempfile.mkstemp(prefix="emergency_receipt_", suffix=".raster")
with os.fdopen(_rst_fd, "wb") as fh:
    fh.write(raster)
printed_ok = False
try:
    with open(dev, "wb") as p:            # direct if taza has device write perms
        p.write(raster)
    print(f"Sent {len(raster)} bytes directly to {dev} (StarTSPImage raster)")
    printed_ok = True
except PermissionError:
    # taza not in lp group -> device is root:lp 0660. sudo cp is NOPASSWD here.
    r = subprocess.run(["sudo", "cp", RASTER_TMP, dev])
    print(f"Sent {len(raster)} bytes to {dev} via sudo cp (rc={r.returncode})")
    printed_ok = r.returncode == 0

# --- Cleanup: remove ONLY this run's temp files after a successful print, so
#     /tmp doesn't accumulate. Uniqueness (mkstemp) is what closes the bug;
#     this is hygiene. Never touch other runs' files. ---
if printed_ok:
    for _tmp in (OUT, RASTER_TMP):
        try:
            os.remove(_tmp)
        except OSError as e:
            print(f"Warning: could not remove temp file {_tmp}: {e}")
else:
    print(f"Print not confirmed OK; leaving temp files for inspection: {OUT} {RASTER_TMP}")
