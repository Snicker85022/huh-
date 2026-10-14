#!/usr/bin/env python3
"""
One-page customer-facing controls brief, printed from the HP DeskJet.

Every claim on this page is traceable to a LOCKED procedure in the Operations Content KB
(tazaos.rag_operations_content, status='locked'). Nothing here is aspirational.

Deliberately ABSENT: any traceability / 'scan the label to see the batch record' claim.
The label QR currently resolves to 404 (checked 2026-10-09), so claiming it would be false.

Writes a real PDF with base-14 fonts (no deps), then hands it to CUPS.
"""
import subprocess, sys

W, H = 612.0, 792.0
FONTS = {"R": "F1", "B": "F2", "I": "F3"}


def esc(s):
    return s.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")


class Page:
    def __init__(self):
        self.ops = []
        self.y = 54.0

    def _put(self, s):
        self.ops.append(s)

    def text(self, x, y, s, f="R", size=9.5):
        self._put("BT /%s %.2f Tf 1 0 0 1 %.2f %.2f Tm (%s) Tj ET"
                  % (FONTS[f], size, x, H - y, esc(s)))

    def para(self, x, y, s, width_chars, f="R", size=9.5, lead=11.6):
        words, line, yy = s.split(), "", y
        for w in words:
            if len(line) + len(w) + 1 > width_chars:
                self.text(x, yy, line, f, size); yy += lead; line = w
            else:
                line = (line + " " + w).strip()
        if line:
            self.text(x, yy, line, f, size); yy += lead
        return yy

    def rule(self, y, x1=54, x2=558, w=0.6):
        self._put("%.2f w %.2f %.2f m %.2f %.2f l S" % (w, x1, H - y, x2, H - y))

    def band(self, y, h=16.0, x=54, w=504):
        self._put("0.13 g %.2f %.2f %.2f %.2f re f 0 g" % (x, H - y - h + 3, w, h))


p = Page()
X = 54.0

p.text(X, 52, "TAZA CATERING & EVENTS", "B", 15)
p.text(X, 68, "Kitchen Food-Safety & Quality Controls", "B", 11.5)
p.text(X, 82, "Prepared for facility inspection  \u00b7  9 October 2026  \u00b7  Phoenix, Arizona", "I", 8.6)
p.rule(91, w=1.0)

y = 106
SECTIONS = [
 ("1.  Temperature control \u2014 written limits, verified with a probe, never by eye", [
   "Poultry first cook: 165 \u00b0F internal, checked at three to four points.",
   "Reheats and fish: 145 \u00b0F internal.",
   "Hot hold, in service and in transit: above 140 \u00b0F.",
   "Cook to chill: two hours or less.",
   "Make-ahead proteins: ice-bath flash-chill to below 45 \u00b0F before the pan is covered.",
   "Hot transport: 4\u20136 litre water bladders at 95 \u00b0C in an insulated hot box.",
 ]),
 ("2.  Sanitation & facility", [
   "QUAT sanitiser at the dish station.",
   "Leased low-temperature dish machine, serviced under contract.",
   "Chemicals on a dedicated rack at the mop sink, separated from all food.",
   "Pest control under a standing monthly service contract.",
   "Cooking hood to NFPA 96 with UL-listed baffle filters and scheduled cleaning.",
   "Fire suppression, automatic and manual, four nozzles over the cooking line, with a",
   "Class K extinguisher at the line. No unattended or after-hours cooking.",
 ]),
 ("3.  Allergen & dietary control", [
   "Allergen check is mandatory before purchasing, not after delivery.",
   "Separate preparation and explicit labelling for halal and gluten-free splits.",
   "Every container we prep or portion is labelled at the point of work with its dish name,",
   "ingredient line, allergen statement, reheat instruction, pack date and initials.",
 ]),
 ("4.  Staff & accountability", [
   "Two certified food managers on staff; all other staff hold current food-handler cards.",
   "Alcohol is served only by the licensed owners.",
   "Every control on this page is a written, version-controlled procedure with a named",
   "owner \u2014 not a habit passed on by word of mouth.",
 ]),
 ("5.  Cold chain & transport", [
   "Hot, cold and fragile loads travel in three separate vehicle zones; fragile loads last.",
   "Carriers are matched to the item \u2014 nothing travels in a pan it can shift in.",
   "Every job runs one fixed eight-stage pipeline: confirmation, projection, shopping, prep,",
   "production, packing, delivery, follow-up.",
 ]),
]

for head, bullets in SECTIONS:
    p.text(X, y, head, "B", 9.8); y += 13.5
    for b in bullets:
        p.text(X + 12, y, "\u2022", "R", 8.4)
        y = p.para(X + 24, y, b, 88)
    y += 5

p.rule(y, w=1.0); y += 13
p.para(X, y, "Records supporting each control above \u2014 temperature logs, allergen checks, "
             "sanitation and pest-control service records, staff certifications \u2014 are held on "
             "site and available for review at any time.", 92, "I", 8.4)

# ---- minimal PDF -----------------------------------------------------------
content = "\n".join(p.ops).encode()
objs = [
 b"<< /Type /Catalog /Pages 2 0 R >>",
 b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
 ("<< /Type /Page /Parent 2 0 R /MediaBox [0 0 %.0f %.0f] /Resources << /Font << "
  "/F1 5 0 R /F2 6 0 R /F3 7 0 R >> >> /Contents 4 0 R >>" % (W, H)).encode(),
 ("<< /Length %d >>\nstream\n" % len(content)).encode() + content + b"\nendstream",
 b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
 b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>",
 b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Oblique >>",
]
out, off = bytearray(b"%PDF-1.4\n"), []
for i, o in enumerate(objs, 1):
    off.append(len(out))
    out += ("%d 0 obj\n" % i).encode() + o + b"\nendobj\n"
xref = len(out)
out += ("xref\n0 %d\n" % (len(objs) + 1)).encode() + b"0000000000 65535 f \n"
for o in off:
    out += ("%010d 00000 n \n" % o).encode()
out += ("trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objs) + 1, xref)).encode()

path = "/home/taza/checklist-app/out/Taza_Kitchen_Controls.pdf"
open(path, "wb").write(bytes(out))
print("wrote", path, len(out), "bytes")

if "--no-print" not in sys.argv:
    q = "TazaHP"
    if subprocess.run(["lpstat", "-p", q], capture_output=True).returncode:
        q = "DeskJet3720"
    r = subprocess.run(["lp", "-d", q, "-o", "media=na_letter_8.5x11in",
                        "-o", "print-color-mode=monochrome",
                        "-t", "Taza Kitchen Controls Brief", path],
                       capture_output=True, text=True)
    print(">>> PRINT rc=%s %s" % (r.returncode, (r.stdout or r.stderr).strip()))
